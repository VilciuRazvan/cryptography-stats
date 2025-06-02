from ..utils.command_runner import run_command, check_tool_version
from ..utils.user_input import get_user_choice, get_password_with_confirmation
from ..generators.key_generator import generate_key, parse_curves
from ..generators.cert_generator import generate_ca_certificate, generate_signed_certificate
from ..generators.store_generator import generate_pkcs12_file, create_server_keystore, create_truststore
from ..utils.thingsboard_device import ThingsboardDeviceManager
import os
import shutil
import sys

THINGSBOARD_CONF_PATH = "C:\\Program Files\\Thingsboard\\thingsboard\\conf\\certs\\test"

def generate_certificates():
    """Handle the certificate generation workflow"""
    print("\n=== Certificate Generation ===")
    
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
        print("Using default password 'changeit' for all keystores")
        
        # Use default "changeit" password for all stores
        p12_password = "changeit"
        keystore_password = "changeit"
        truststore_password = "changeit"

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


def apply_certificates():
    """Handle applying certificates to services"""
    print("\n=== Apply Certificates ===")
    
    try:
        # Check if we have admin rights
        import ctypes
        if not ctypes.windll.shell32.IsUserAnAdmin():
            print("Error: This operation requires administrator privileges.")
            print("Please run the application as administrator.")
            return

        # 1. Select the certificates directory
        print("\nLooking for certificate directories...")
        cert_dirs = [d for d in os.listdir('.') if os.path.isdir(d)]
        if not cert_dirs:
            print("No certificate directories found in current location.")
            return
            
        cert_dir = get_user_choice("\nSelect certificate directory:", cert_dirs)
        if not cert_dir:
            return

        # Check if required files exist
        keystore_path = os.path.join(cert_dir, "server_keystore.jks")
        truststore_path = os.path.join(cert_dir, "server_truststore.jks")
        
        if not os.path.exists(keystore_path) or not os.path.exists(truststore_path):
            print("Error: Required JKS files not found in selected directory.")
            print(f"Looking for:\n  {keystore_path}\n  {truststore_path}")
            return

        # 2. Stop ThingsBoard service
        print("\nStopping ThingsBoard service...")
        stop_result = os.system('net stop thingsboard')
        if stop_result != 0:
            print("Failed to stop ThingsBoard service. Is it running?")
            # Continue anyway as files might be copyable

        # 3. Copy files
        print("\nCopying certificate files...")
        try:
            # Ensure target directory exists
            os.makedirs(THINGSBOARD_CONF_PATH, exist_ok=True)
            
            # Copy files with overwrite
            shutil.copy2(keystore_path, os.path.join(THINGSBOARD_CONF_PATH, "server_keystore.jks"))
            shutil.copy2(truststore_path, os.path.join(THINGSBOARD_CONF_PATH, "server_truststore.jks"))
            print("Certificate files copied successfully.")
        except Exception as e:
            print(f"Error copying files: {str(e)}")
            return

        # 4. Start ThingsBoard service
        print("\nStarting ThingsBoard service...")
        start_result = os.system('net start thingsboard')
        if start_result != 0:
            print("Failed to start ThingsBoard service.")
            return

        print("\nCertificates applied successfully!")
        print("ThingsBoard service restarted.")

    except Exception as e:
        print(f"\nError applying certificates: {str(e)}")

def create_thingsboard_device():
    """Handle ThingsBoard device creation with existing certificates"""
    print("\n=== ThingsBoard Device Creation ===")
    
    # 1. Find certificate directories
    print("\nLooking for certificate directories...")
    cert_dirs = [d for d in os.listdir('.') if os.path.isdir(d)]
    if not cert_dirs:
        print("No certificate directories found in current location.")
        return
        
    cert_dir = get_user_choice("\nSelect certificate directory:", cert_dirs)
    if not cert_dir:
        return

    # 2. Check if required files exist
    ca_cert_path = os.path.join(cert_dir, "ca.crt")
    device_cert_path = os.path.join(cert_dir, "device1.crt")
    
    if not os.path.exists(device_cert_path) or not os.path.exists(ca_cert_path):
        print("Error: Required certificate files not found in selected directory.")
        print(f"Looking for:\n  {ca_cert_path}\n  {device_cert_path}")
        return

    # 3. Get device name from user
    device_name = get_user_choice("\nEnter device name (e.g., device001):", [], allow_manual_entry=True)
    if not device_name:
        device_name = "device001"  # Default name if none provided

    # 4. Create device in ThingsBoard
    print("\nAttempting to connect to ThingsBoard...")
    tb_manager = ThingsboardDeviceManager()
    if tb_manager.login():
        print("\n--- Creating Device Profile ---")
        profile_name = f"Profile_{device_name}"
        tb_manager.create_profile_with_certificate(profile_name, ca_cert_path)

        print(f"\n--- Creating Device: {device_name} ---")
        device_id = tb_manager.create_device_with_profile(
            device_name=device_name,
            profile_name=profile_name
        )

        if device_id:
            print("\n--- Updating Device Credentials ---")
            device_credentials = tb_manager.get_device_credentials(device_id=device_id)
            if device_credentials:
                if tb_manager.post_modify_device_credentials(
                    credentials=device_credentials,
                    device_id=device_id,
                    cert_path=device_cert_path
                ):
                    print(f"\nSuccessfully created and configured device '{device_name}'")
                else:
                    print("Failed to update device credentials")
            else:
                print("Failed to get device credentials")
    else:
        print("Failed to connect to ThingsBoard. Please ensure the server is running.")

def check_thingsboard_connection():
    """Check if ThingsBoard server is accessible"""
    print("\n=== ThingsBoard Connection Check ===")
    
    tb_manager = ThingsboardDeviceManager()
    if tb_manager.check_connection():
        print("ThingsBoard server is up and running")
    else:
        print("Could not connect to ThingsBoard server")

def run_performance_tests():
    """Handle performance testing"""
    from ..utils.performance_tester import PerformanceTest
    
    tester = PerformanceTest()
    if tester.setup_test():
        tester.run_test()
    else:
        print("Performance test setup failed.")

def cli_main():
    """
    Main CLI function with menu-driven interface.
    """
    while True:
        print("\n=== Certificate Management Utility ===")
        print("Note: Some operations require administrator privileges.")
        options = [
            "Generate certificates",
            "Apply generated certificates (requires admin rights)",
            "Check ThingsBoard connection",
            "Create ThingsBoard device with generated certificate",
            "Run performance tests",
            "Exit"
        ]
        
        print("\nChoose your next action:")
        for i, option in enumerate(options, 1):
            print(f"{i}. {option}")
        
        choice = get_user_choice("", [], allow_manual_entry=True)
        
        if not choice:
            continue
            
        try:
            choice_num = int(choice)
            if choice_num == 1:
                generate_certificates()
            elif choice_num == 2:
                apply_certificates()
            elif choice_num == 3:
                check_thingsboard_connection()
            elif choice_num == 4:
                create_thingsboard_device()
            elif choice_num == 5:
                run_performance_tests()
            elif choice_num == 6:
                print("\nExiting...")
                sys.exit(0)
            else:
                print("\nInvalid choice. Please enter a number between 1 and 6.")
        except ValueError:
            print("\nInvalid input. Please enter a number.")

