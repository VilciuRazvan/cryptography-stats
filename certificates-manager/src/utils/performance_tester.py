import paho.mqtt.client as mqtt
import ssl
import time
import json
import os
from typing import Dict, List, Optional
from ..utils.user_input import get_user_choice
from ..utils.thingsboard_device import ThingsboardDeviceManager

class PerformanceTest:
    AVAILABLE_CIPHERS = {
        "ECDHE-ECDSA-AES128-GCM-SHA256": "ECC with AES-128-GCM",
        "ECDHE-ECDSA-AES256-GCM-SHA384": "ECC with AES-256-GCM",
        "ECDHE-ECDSA-CHACHA20-POLY1305": "ECC with ChaCha20-Poly1305",
        "ECDHE-RSA-AES128-GCM-SHA256": "RSA with AES-128-GCM",
        "ECDHE-RSA-AES256-GCM-SHA384": "RSA with AES-256-GCM",
        "ECDHE-RSA-CHACHA20-POLY1305": "RSA with ChaCha20-Poly1305"
    }

    def __init__(self):
        self.cert_dir = None
        self.iterations = 1
        self.delay = 2
        self.selected_ciphers = []
        self.output_file = "performance_results.xlsx"

    def setup_test(self) -> bool:
        """Configure test parameters"""
        print("\n=== Performance Test Setup ===")

        # 1. Check ThingsBoard connection
        tb_manager = ThingsboardDeviceManager()
        if not tb_manager.check_connection():
            print("ThingsBoard must be running to perform tests.")
            return False

        # 2. Select certificate directory
        print("\nLooking for certificate directories...")
        cert_dirs = [d for d in os.listdir('.') if os.path.isdir(d)]
        if not cert_dirs:
            print("No certificate directories found.")
            return False

        self.cert_dir = get_user_choice("\nSelect certificate directory:", cert_dirs)
        if not self.cert_dir:
            return False

        # 3. Verify required files
        required_files = ["ca.crt", "device1.crt", "device1.key"]
        for file in required_files:
            if not os.path.exists(os.path.join(self.cert_dir, file)):
                print(f"Missing required file: {file}")
                return False

        # 4. Get test parameters
        iterations = get_user_choice(
            "\nEnter number of iterations (1-10000):", 
            [], 
            allow_manual_entry=True
        )
        try:
            self.iterations = int(iterations)
            if not 1 <= self.iterations <= 10000:
                raise ValueError
        except ValueError:
            print("Invalid iteration count. Using default: 1")
            self.iterations = 1

        delay = get_user_choice(
            "\nEnter delay between iterations in seconds (0-3600):", 
            [], 
            allow_manual_entry=True
        )
        try:
            self.delay = int(delay)
            if not 0 <= self.delay <= 3600:
                raise ValueError
        except ValueError:
            print("Invalid delay. Using default: 2")
            self.delay = 2

        # 5. Select ciphers to test
        print("\nAvailable cipher suites:")
        for i, (cipher, description) in enumerate(self.AVAILABLE_CIPHERS.items(), 1):
            print(f"{i}. {cipher} ({description})")

        while True:
            cipher_choice = get_user_choice(
                "\nSelect cipher numbers (comma-separated, or 'all'):", 
                [], 
                allow_manual_entry=True
            )
            if cipher_choice.lower() == 'all':
                self.selected_ciphers = list(self.AVAILABLE_CIPHERS.keys())
                break
            try:
                choices = [int(x.strip()) for x in cipher_choice.split(',')]
                self.selected_ciphers = [list(self.AVAILABLE_CIPHERS.keys())[i-1] for i in choices]
                break
            except (ValueError, IndexError):
                print("Invalid selection. Try again or type 'all'")

        # 6. Get output filename
        output_file = get_user_choice(
            "\nEnter output Excel filename (default: performance_results.xlsx):", 
            [], 
            allow_manual_entry=True
        )
        if output_file:
            self.output_file = output_file if output_file.endswith('.xlsx') else f"{output_file}.xlsx"

        print("\nTest configuration complete!")
        print(f"Certificates directory: {self.cert_dir}")
        print(f"Iterations: {self.iterations}")
        print(f"Delay: {self.delay} seconds")
        print(f"Selected ciphers: {len(self.selected_ciphers)}")
        print(f"Output file: {self.output_file}")

        return True

    def run_test(self) -> None:
        """Execute the performance test"""
        from .mqtt.test_runner import run_mqtt_test, calculate_statistics, MqttTestConfig
        from .mqtt.excel_handler import export_results_to_excel

        all_run_data = {}

        # Create test configurations
        test_configs = {}
        for cipher in self.selected_ciphers:
            config_name = f"Test_{cipher}"
            config = MqttTestConfig(
                host="localhost",
                port=8883,
                tls=True,
                ca_certs=os.path.join(self.cert_dir, "ca.crt"),
                certfile=os.path.join(self.cert_dir, "device1.crt"),
                keyfile=os.path.join(self.cert_dir, "device1.key"),
                ciphers=cipher
            )
            test_configs[config_name] = config

        # Run tests for each configuration
        for config_name, config in test_configs.items():
            print(f"\n===== Starting Test: {config_name} =====")
            iteration_results = []

            for i in range(1, self.iterations + 1):
                print(f"--- Iteration {i}/{self.iterations} ---")
                run_state = run_mqtt_test(i, config_name, config.__dict__)
                iteration_data = run_state.get_results_dict()
                iteration_results.append(iteration_data)

                if iteration_data.get("error"):
                    print(f"  Iteration {i} failed: {iteration_data['error']}")
                else:
                    print(f"  Iteration {i} completed successfully")

                if self.delay > 0 and i < self.iterations:
                    time.sleep(self.delay)

            all_run_data[config_name] = iteration_results

        # Export results
        export_results_to_excel(
            all_run_data=all_run_data,
            excel_filename=self.output_file,
            calculate_statistics=calculate_statistics
        )

        print(f"\nPerformance test complete! Results saved to: {self.output_file}")