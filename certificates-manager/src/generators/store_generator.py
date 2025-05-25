from ..utils.command_runner import run_command
import os

def generate_pkcs12_file(server_cert_filename, server_key_filename, ca_cert_filename, p12_filename, p12_alias, p12_password, output_dir):
    """Generates a PKCS12 (.p12) file."""
    print(f"\n--- Generating PKCS12 File: {p12_filename} ---")
    command = [
        'pkcs12', '-export',
        '-in', server_cert_filename,
        '-inkey', server_key_filename,
        '-certfile', ca_cert_filename,
        '-name', p12_alias,
        '-out', p12_filename,
        '-passout', f'pass:{p12_password}' # Pass password directly
    ]
    stdout, stderr = run_command(command, working_dir=output_dir, tool_name="openssl")
    if stderr:
        print(f"Error generating PKCS12 file {p12_filename}: {stderr}")
        return False
    print(f"Successfully generated PKCS12 file: {os.path.join(output_dir, p12_filename)}")
    return True

def create_server_keystore(p12_filename, keystore_filename, p12_password, keystore_password, alias, output_dir):
    """Creates a JKS server keystore from a PKCS12 file."""
    print(f"\n--- Creating Server Keystore (JKS): {keystore_filename} ---")
    command = [
        '-importkeystore',
        '-destkeystore', keystore_filename,
        '-srckeystore', p12_filename,
        '-srcstoretype', 'PKCS12',
        '-alias', alias, # This is the alias of the entry within the p12, which becomes the alias in the JKS
        '-srcstorepass', p12_password,
        '-deststorepass', keystore_password,
        '-noprompt' # Suppress interactive prompts
    ]
    stdout, stderr = run_command(command, working_dir=output_dir, tool_name="keytool")
    if stderr:
        print(f"Error creating server keystore {keystore_filename}: {stderr}")
        return False
    print(f"Successfully created server keystore: {os.path.join(output_dir, keystore_filename)}")
    return True

def create_truststore(ca_cert_filename, truststore_filename, truststore_password, alias, output_dir):
    """Creates a JKS truststore by importing the CA certificate."""
    print(f"\n--- Creating Truststore (JKS): {truststore_filename} ---")
    command = [
        '-importcert', # Using -importcert explicitly
        '-trustcacerts',
        '-alias', alias,
        '-file', ca_cert_filename,
        '-keystore', truststore_filename,
        '-storepass', truststore_password,
        '-noprompt' # Suppress interactive prompts
    ]
    stdout, stderr = run_command(command, working_dir=output_dir, tool_name="keytool")
    if stderr:
        print(f"Error creating truststore {truststore_filename}: {stderr}")
        return False
    print(f"Successfully created truststore: {os.path.join(output_dir, truststore_filename)}")
    return True
