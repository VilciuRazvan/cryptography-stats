from ..utils.command_runner import run_command, check_tool_version
from ..utils.user_input import get_user_choice, get_password_with_confirmation
from ..generators.key_generator import generate_key, parse_curves
from ..generators.cert_generator import generate_ca_certificate, generate_signed_certificate
from ..generators.store_generator import generate_pkcs12_file, create_server_keystore, create_truststore
import os
import shutil

def cli_main():
    """
    Main CLI function to guide user through certificate generation.
    """
    print("--- OpenSSL & Keytool Certificate Generation Utility ---")

    if not check_tool_version("openssl"): return
    if not check_tool_version("keytool"): return


    alg_options = ["EC", "RSA"]
    alg_choice = get_user_choice("\nChoose certificate generation algorithm:", alg_options)
    if not alg_choice: return
    print(f"Algorithm chosen: {alg_choice}")

    curve_choice = None
    rsa_bits_choice = None

    if alg_choice == 'EC':
        print("\n--- Fetching Elliptic Curves ---")
        curves_stdout, curves_stderr = run_command(['ecparam', '-list_curves'], tool_name="openssl")
        if curves_stderr:
            print(f"Error fetching curves: {curves_stderr}")
            return
        
        available_curves = parse_curves(curves_stdout)
        if not available_curves:
            print("No elliptic curves found or output could not be parsed.")
            return
        
        curve_choice = get_user_choice("Choose an elliptic curve:", available_curves)
        if not curve_choice: return
        print(f"Curve chosen: {curve_choice}")

    elif alg_choice == 'RSA':
        rsa_bits_options = [2048, 3072, 4096]
        rsa_bits_choice = get_user_choice("\nChoose RSA key bit length:", rsa_bits_options)
        if not rsa_bits_choice: return
        print(f"RSA key bits chosen: {rsa_bits_choice}")

    while True:
        output_dir_name = get_user_choice("\nEnter the name for the new directory to save certificates (e.g., my_certs)", [], allow_manual_entry=True)
        if not output_dir_name:
            print("Directory name cannot be empty.")
            continue
        if os.path.exists(output_dir_name):
            overwrite = input(f"Directory '{output_dir_name}' already exists. Overwrite? (yes/no): ").lower()
            if overwrite == 'yes':
                try:
                    shutil.rmtree(output_dir_name)
                    print(f"Removed existing directory: {output_dir_name}")
                except Exception as e:
                    print(f"Error removing existing directory '{output_dir_name}': {e}")
                    continue 
            else:
                print("Please choose a different directory name.")
                continue
        try:
            os.makedirs(output_dir_name, exist_ok=True)
            print(f"Certificates will be saved in: {os.path.abspath(output_dir_name)}")
            break
        except Exception as e:
            print(f"Error creating directory '{output_dir_name}': {e}")

    ca_subj_cn = get_user_choice("\nEnter Common Name (CN) for Root CA (e.g., My Test CA)", [], allow_manual_entry=True)
    ca_subj = f"/CN={ca_subj_cn if ca_subj_cn else 'My Test CA'}"

    server_subj_cn = get_user_choice("\nEnter Common Name (CN) for Server (e.g., localhost)", [], allow_manual_entry=True)
    server_subj = f"/CN={server_subj_cn if server_subj_cn else 'localhost'}"

    device_subj_cn = get_user_choice("\nEnter Common Name (CN) for Device (e.g., device001)", [], allow_manual_entry=True)
    device_subj = f"/CN={device_subj_cn if device_subj_cn else 'device001'}"

    # Filenames (used consistently)
    ca_key_fn = "ca.key"
    ca_cert_fn = "ca.crt"
    ca_srl_fn = "ca.srl"
    server_key_fn = "server.key"
    server_cert_fn = "server.crt"
    device_key_fn = "device1.key" # Assuming one device for now
    device_cert_fn = "device1.crt"
    
    server_p12_fn = "server.p12"
    server_keystore_fn = "server_keystore.jks"
    truststore_fn = "server_truststore.jks"


    if not generate_ca_certificate(alg_choice, curve_choice, rsa_bits_choice, output_dir_name, ca_subj):
        print("\nFailed to generate Root CA certificate. Aborting.")
        return

    if not generate_signed_certificate("server", ca_key_fn, ca_cert_fn, ca_srl_fn, alg_choice, curve_choice, rsa_bits_choice, output_dir_name, server_subj):
        print("\nFailed to generate Server certificate. Aborting.")
        return
        
    if not generate_signed_certificate("device1", ca_key_fn, ca_cert_fn, ca_srl_fn, alg_choice, curve_choice, rsa_bits_choice, output_dir_name, device_subj):
        print("\nFailed to generate Device certificate. Aborting.") # Corrected message
        return

    # --- PKCS12 and JKS Generation ---
    generate_pkcs12_and_jks = get_user_choice("\nDo you want to generate PKCS12 and JKS files for the server? (yes/no)", ["yes", "no"])
    
    p12_password = None
    keystore_password = None
    truststore_password = None

    if generate_pkcs12_and_jks == "yes":
        print("\n--- PKCS12 and JKS Password Setup ---")
        while True:
            p12_password = get_user_choice("Enter password for PKCS12 (server.p12) export", [], allow_manual_entry=True, is_password=True)
            p12_password_confirm = get_user_choice("Confirm password for PKCS12 export", [], allow_manual_entry=True, is_password=True)
            if p12_password == p12_password_confirm:
                if not p12_password: print("Password cannot be empty.")
                else: break
            print("Passwords do not match. Please try again.")
        
        while True:
            keystore_password = get_user_choice("Enter password for Server Keystore (server_keystore.jks)", [], allow_manual_entry=True, is_password=True)
            keystore_password_confirm = get_user_choice("Confirm password for Server Keystore", [], allow_manual_entry=True, is_password=True)
            if keystore_password == keystore_password_confirm:
                if not keystore_password: print("Password cannot be empty.")
                else: break
            print("Passwords do not match. Please try again.")

        while True:
            truststore_password = get_user_choice("Enter password for Truststore (server_truststore.jks)", [], allow_manual_entry=True, is_password=True)
            truststore_password_confirm = get_user_choice("Confirm password for Truststore", [], allow_manual_entry=True, is_password=True)
            if truststore_password == truststore_password_confirm:
                if not truststore_password: print("Password cannot be empty.")
                else: break
            print("Passwords do not match. Please try again.")

        # Generate PKCS12
        if not generate_pkcs12_file(server_cert_fn, server_key_fn, ca_cert_fn, server_p12_fn, "server", p12_password, output_dir_name):
            print("\nFailed to generate PKCS12 file. Skipping JKS generation.")
        else:
            # Create Server Keystore from PKCS12
            if not create_server_keystore(server_p12_fn, server_keystore_fn, p12_password, keystore_password, "server", output_dir_name):
                print("\nFailed to create server keystore JKS.")
            
            # Create Truststore with CA certificate
            if not create_truststore(ca_cert_fn, truststore_fn, truststore_password, "root-ca", output_dir_name):
                print("\nFailed to create truststore JKS.")


    print(f"\n--- All Operations Complete ---")
    print(f"All files saved in directory: {os.path.abspath(output_dir_name)}")
    print("  Root CA: ca.key, ca.crt")
    if os.path.exists(os.path.join(output_dir_name, ca_srl_fn)):
        print(f"  CA Serial file: {ca_srl_fn}")
    print(f"  Server: {server_key_fn}, {server_cert_fn}")
    print(f"  Device: {device_key_fn}, {device_cert_fn}")

    if generate_pkcs12_and_jks == "yes":
        if os.path.exists(os.path.join(output_dir_name, server_p12_fn)):
            print(f"  Server PKCS12: {server_p12_fn}")
        if os.path.exists(os.path.join(output_dir_name, server_keystore_fn)):
            print(f"  Server Keystore JKS: {server_keystore_fn}")
        if os.path.exists(os.path.join(output_dir_name, truststore_fn)):
            print(f"  Server Truststore JKS: {truststore_fn}")

