import paho.mqtt.client as mqtt
import ssl
import time
import json
import threading
import numpy as np
import pandas as pd
import warnings
import os
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class MqttTestConfig:
    """Configuration for MQTT test"""
    host: str
    port: int
    tls: bool
    ca_certs: str
    certfile: str
    keyfile: str
    ciphers: Optional[str] = None
    clientId: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None

warnings.filterwarnings('ignore', category=DeprecationWarning)

# --- Test State Class ---
class MqttTestState:
    """Holds state and timing data for a single MQTT test run."""
    def __init__(self, iteration, config_name):
        self.iteration = iteration
        self.config_name = config_name
        self.connect_sent_time = 0
        self.connect_ack_time = 0
        self.publish_sent_time = 0
        self.publish_ack_time = 0
        self.error = None
        self.connect_event = threading.Event()
        self.publish_event = threading.Event()
        self.message_id = None

    def record_connect_sent(self):
        self.connect_sent_time = time.perf_counter() # Use high-resolution timer

    def record_connect_ack(self):
        self.connect_ack_time = time.perf_counter()
        self.connect_event.set() # Signal that connection is complete

    def record_publish_sent(self):
        self.publish_sent_time = time.perf_counter()

    def record_publish_ack(self):
        self.publish_ack_time = time.perf_counter()
        self.publish_event.set() # Signal that publish is acknowledged

    def record_error(self, err_msg):
        self.error = err_msg
        # Ensure events are set even on error to prevent hangs
        if not self.connect_event.is_set():
            self.connect_event.set()
        if not self.publish_event.is_set():
            self.publish_event.set()


    def get_results_dict(self):
        """Returns timing results as a dictionary."""
        if self.error:
            return {
                "iteration": self.iteration,
                "handshake": None,
                "puback": None,
                "total": None,
                "error": self.error
            }
        # Check if all necessary timestamps were recorded
        # Allow calculation even if publish failed, handshake might be valid
        handshake_time = None
        puback_time = None
        total_time = None
        final_error = None

        if self.connect_sent_time > 0 and self.connect_ack_time > 0:
             handshake_time = self.connect_ack_time - self.connect_sent_time
             if self.publish_sent_time > 0 and self.publish_ack_time > 0:
                  puback_time = self.publish_ack_time - self.publish_sent_time
                  total_time = self.publish_ack_time - self.connect_sent_time
             elif self.publish_sent_time > 0: # Publish started but didn't finish
                 final_error = self.error if self.error else "PUBACK Incomplete/Timeout"
             else: # Connect finished but publish didn't start (e.g. error before publish)
                 final_error = self.error if self.error else "Publish Phase Not Reached"

        elif self.connect_sent_time > 0: # Connect started but didn't finish
            final_error = self.error if self.error else "Connect Incomplete/Timeout"
        else: # Connect never started
            final_error = self.error if self.error else "Run Not Started"


        # Check if essential timings for calculation are missing even if no error was explicitly recorded
        if handshake_time is None and final_error is None:
            final_error = "Incomplete run (missing connect timestamps)"
        elif puback_time is None and total_time is None and final_error is None and self.publish_sent_time > 0:
             # This case might occur if publish started but puback event was missed or timed out
            final_error = "Incomplete run (missing puback timestamp)"


        return {
            "iteration": self.iteration,
            "handshake": handshake_time,
            "puback": puback_time,
            "total": total_time,
            "error": final_error
        }

# --- MQTT Callbacks ---
# (on_connect, on_disconnect, on_publish remain the same as before)
def on_connect(client, userdata, flags, reason_code, properties=None):
    """Callback when CONNACK is received."""
    state: MqttTestState = userdata
    if reason_code == 0:
        state.record_connect_ack()
        # Add TLS version verification
        ssl_socket = client.socket()
        if ssl_socket and hasattr(ssl_socket, 'version'):
            print(f"  TLS Version: {ssl_socket.version()}")
        if ssl_socket and hasattr(ssl_socket, 'cipher'):
            negotiated_cipher = ssl_socket.cipher()
            print(f"  Negotiated Cipher: {negotiated_cipher}")
    else:
        error_msg = f"Iter {state.iteration} ({state.config_name}): Connection Failed! Reason code: {reason_code}"
        print(error_msg)
        # Record error but allow get_results_dict to determine final state
        state.error = f"Connect RC: {reason_code}"
        state.connect_event.set() # Ensure connect phase finishes on error

def on_disconnect(client, userdata, reason_code, properties=None):
    """Callback when disconnected."""
    state: MqttTestState = userdata
    # Can be useful for debugging unexpected disconnects
    if reason_code != 0 and not state.error:
         # Only log if it wasn't an expected disconnect or already errored
        current_time = time.perf_counter()
        # Check if disconnect happened after expected completion
        disconnect_error = True
        if state.publish_ack_time > 0 and current_time - state.publish_ack_time < 1.0: # Allow 1s for clean disconnect
             disconnect_error = False
        elif state.connect_ack_time > 0 and state.publish_sent_time == 0 and current_time - state.connect_ack_time < 1.0: # If publish never started
             disconnect_error = False


        if disconnect_error:
            print(f"Iter {state.iteration} ({state.config_name}): Unexpected disconnect! Reason code: {reason_code}")
            state.record_error(f"Unexpected disconnect: {reason_code}")


def on_publish(client, userdata, mid):
    """Callback when PUBACK is received for QoS 1/2."""
    state: MqttTestState = userdata
    # Check if this is the MID we are waiting for
    if state.message_id == mid:
        # print(f"Iter {state.iteration} ({state.config_name}): PUBACK received for mid {mid}.")
        state.record_publish_ack()
    # else:
    #     print(f"Iter {state.iteration} ({state.config_name}): Received PUBACK for unexpected mid {mid}")


# --- Test Execution Function ---
def run_mqtt_test(iteration, config_name, client_config):
    """Runs a single connect, publish, disconnect test."""

    state = MqttTestState(iteration, config_name)
    # Create a new client instance for each iteration to avoid client-side caching
    client = mqtt.Client(
        client_id=client_config.get("clientId", f"perf-tester-{config_name}-{iteration}-{time.time_ns()}"),
        protocol=mqtt.MQTTv5,
        userdata=state
    )

    # Assign callbacks
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_publish = on_publish
    

    # Apply configuration
    if client_config.get("tls", False):
        try:
            client.tls_set(
                ca_certs=client_config.get("ca_certs"),
                certfile=client_config.get("certfile"),
                keyfile=client_config.get("keyfile"),
                cert_reqs=ssl.CERT_REQUIRED,
                # tls_version=ssl.PROTOCOL_TLS_CLIENT,  # This is the default
                tls_version=ssl.PROTOCOL_TLSv1_2,  # This is the default
                ciphers=client_config.get("ciphers"), # Pass None to negotiate
            )

        except ValueError as e:
             # Catch potential errors from set_ciphers if suite is invalid/unsupported
             error_msg = f"Iter {state.iteration} ({state.config_name}): TLS Setup Error (Invalid Cipher?): {e}"
             print(error_msg)
             state.record_error(error_msg)
             return state
        except Exception as e:
            error_msg = f"Iter {state.iteration} ({state.config_name}): TLS Setup Error: {e}"
            print(error_msg)
            state.record_error(error_msg)
            return state # Return early if TLS setup fails

    if client_config.get("username"):
        client.username_pw_set(client_config["username"], client_config.get("password"))

    # --- Connect Phase ---
    state.record_connect_sent()
    try:
        client.connect(
            client_config["host"],
            client_config["port"],
            keepalive=60
        )
        client.loop_start() # Start network loop in background thread
    except Exception as e:
        error_msg = f"Iter {state.iteration} ({state.config_name}): Connect Error: {e}"
        print(error_msg)
        state.record_error(error_msg)
        # Ensure loop stops if connect fails immediately
        try:
             client.loop_stop(force=True) # Force stop if connect threw exception
        except: pass # Ignore errors during cleanup on failure
        return state # Return early

    # Wait for connection to complete (or fail)
    connected = state.connect_event.wait(timeout=15) # Increased timeout slightly

    if not connected and not state.error:
        state.record_error("Connect timeout")
        print(f"Iter {state.iteration} ({state.config_name}): Connect Timeout!")
    # Error might have been set in on_connect callback
    elif state.error and state.connect_sent_time > 0 and state.connect_ack_time == 0:
         print(f"Iter {state.iteration} ({state.config_name}): Connect failed: {state.error}")


    # --- Publish Phase (only if connected successfully) ---
    if connected and not state.error:
        try:
            large_string = "X" * 60000 # Create a string of 'X' characters
            # large_string = "X" * 1 # Create a string of 'X' characters
            message_content = {
                "data": large_string,
                "status": "Testing large payload"
                }
            payload = json.dumps(message_content)
            print(f"  Payload size: {len(payload)} bytes") # Optional: print size

            state.record_publish_sent()
            msg_info = client.publish(
                topic="v1/devices/me/telemetry",
                payload=payload,
                qos=1
            )
            if msg_info.rc != mqtt.MQTT_ERR_SUCCESS:
                 raise Exception(f"Publish failed with rc: {msg_info.rc}")

            state.message_id = msg_info.mid # Store the message ID we are waiting for
            # print(f"Iter {state.iteration} ({state.config_name}): Publishing mid {state.message_id}")

            # Wait for PUBACK via on_publish callback
            puback_received = state.publish_event.wait(timeout=15) # Increased timeout slightly

            if not puback_received and not state.error:
                 # Check if publish_ack_time was set by the callback just before timeout
                 if state.publish_ack_time == 0:
                      state.record_error("PUBACK timeout")
                      print(f"Iter {state.iteration} ({state.config_name}): PUBACK Timeout!")

        except Exception as e:
            error_msg = f"Iter {state.iteration} ({state.config_name}): Publish Error: {e}"
            print(error_msg)
            # Avoid overwriting a more specific error if one was already set
            if not state.error:
                state.record_error(error_msg)

    # --- Disconnect Phase ---
    # Ensure disconnect happens even if publish failed, but only if connect was attempted
    if state.connect_sent_time > 0:
        try:
            # print(f"Iter {state.iteration} ({state.config_name}): Disconnecting...")
            client.disconnect()
            # Give a brief moment for disconnect packet to send before stopping loop
            time.sleep(0.1)
        except Exception as e:
            # Log disconnect error but don't overwrite primary error
            print(f"Iter {state.iteration} ({state.config_name}): Disconnect Error: {e}")
        finally:
             # Always try to stop the network loop
             try:
                  client.loop_stop()
             except:
                  pass # Ignore errors during final cleanup


    return state

# --- Statistics Function ---
def calculate_statistics(data_list):
    """Calculates statistics for a list of timings, returns a dictionary."""
    # Filter out None values which indicate errors or incomplete runs
    valid_data = [d for d in data_list if d is not None and isinstance(d, (int, float))]
    stats = {
        'Mean': None, 'Median': None, 'StdDev': None,
        'Min': None, 'Max': None, '95th percentile': None,
        'Count': len(valid_data)
    }
    if not valid_data:
        return stats

    data = np.array(valid_data)
    stats['Mean'] = np.mean(data)
    stats['Median'] = np.median(data)
    stats['StdDev'] = np.std(data)
    stats['Min'] = np.min(data)
    stats['Max'] = np.max(data)
    stats['95th percentile'] = np.percentile(data, 95)
    return stats


# # --- Main Execution ---
# if __name__ == "__main__":
#     all_run_data = {} # Store detailed results per iteration for each config

#     # --- Run Test Batches ---
#     for config_name, config_params in test_configs.items():
#         print(f"\n===== Starting Batch: {config_name} =====")
#         iteration_results = [] # Store dicts from get_results_dict for this batch

#         for i in range(1, NUM_ITERATIONS + 1):
#             print(f"--- Iteration {i}/{NUM_ITERATIONS} ({config_name}) ---")
#             run_state = run_mqtt_test(i, config_name, run_config)
#             iteration_data = run_state.get_results_dict()
#             iteration_results.append(iteration_data)

#             if iteration_data.get("error"):
#                  print(f"  Iteration {i} failed or incomplete. Error: {iteration_data['error']}")
#             else:
#                  # Optional: print iteration timing immediately
#                  print(f"  Iter {i} OK: Handshake={iteration_data['handshake']:.4f}s, PubAck={iteration_data['puback']:.4f}s, Total={iteration_data['total']:.4f}s")


#             # Add delay between iterations if testing full handshakes
#             if DELAY_BETWEEN_ITERATIONS > 0 and i < NUM_ITERATIONS: # No delay after last iteration
#                 time.sleep(DELAY_BETWEEN_ITERATIONS)

#         # Store collected iteration results for this batch
#         all_run_data[config_name] = iteration_results
#         print(f"===== Finished Batch: {config_name} =====")
#         # Optional: Add delay/restart prompt between batches
#         # input("Press Enter to start next batch...")

#     all_stats_summary = export_results_to_excel(
#         all_run_data=all_run_data,
#         excel_filename=EXCEL_FILENAME,
#         calculate_statistics=calculate_statistics
#     )

#     print("\n========= Testing Complete =========")

