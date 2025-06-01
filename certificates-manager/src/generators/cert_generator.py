from ..utils.command_runner import run_command
from .key_generator import generate_key
import os

def generate_csr(key_filename, csr_filename, subject, output_dir):
    """Generates a Certificate Signing Request (CSR). Filenames are not paths."""
    print(f"\n--- Generating CSR: {csr_filename} ---")
    command = ['req', '-new', '-key', key_filename, '-out', csr_filename, '-subj', subject]
    
    stdout, stderr = run_command(command, working_dir=output_dir, tool_name="openssl")
    if stderr:
        print(f"Error generating CSR {csr_filename}: {stderr}")
        return False
    print(f"Successfully generated CSR: {os.path.join(output_dir, csr_filename)}")
    return True

def generate_ca_certificate(alg_choice, curve_choice, rsa_bits_choice, output_dir, ca_subj, validity_days=1825):
    """Generates a Root CA key and self-signed certificate with explicit extensions."""
    print("\n--- Generating Root CA Certificate with Explicit Extensions ---")
    ca_key_filename = "ca.key"
    ca_cert_filename = "ca.crt"
    
    # Ensure output_dir exists
    # This should ideally be handled by the calling function (cli_main.py makes sure it exists)
    # but a check here doesn't hurt.
    os.makedirs(output_dir, exist_ok=True)


    if not generate_key(alg_choice, curve_choice, rsa_bits_choice, ca_key_filename, output_dir):
        return False

    # Extract the CN value from ca_subj for the temporary config.
    # Assumes ca_subj is in the format "/CN=My CA Name"
    # A more robust parsing might be needed if ca_subj format varies.
    cn_value = "Temporary CA Name" # Default
    if "/CN=" in ca_subj:
        parts = ca_subj.split('/CN=')
        if len(parts) > 1:
            # Further split by '/' if other RDNs are present, e.g. /CN=X/O=Y
            cn_part = parts[1].split('/')[0]
            if cn_part:
                cn_value = cn_part
        
        print(f"\n--- Generating self-signed CA certificate: {ca_cert_filename} ---")
        command = [
            'req', '-x509', '-new', '-nodes',
            '-key', ca_key_filename,      # Relative to working_dir (output_dir)
            '-sha256',
            '-days', str(validity_days),
            '-out', ca_cert_filename,     # Relative to working_dir (output_dir)
            '-subj', ca_subj,             # This provides the subject directly
        ]
        
        stdout, stderr = run_command(command, working_dir=output_dir, tool_name="openssl")
        
        if stderr:
            print(f"Error generating CA certificate: {stderr}")
            if stdout: # Sometimes OpenSSL req errors go to stdout
                print(f"STDOUT from failed CA generation: {stdout}")
            return False
            
        print(f"Successfully generated CA certificate: {os.path.join(output_dir, ca_cert_filename)}")
        return True

def generate_signed_certificate(entity_name, ca_key_filename, ca_cert_filename, ca_srl_filename, alg_choice, curve_choice, rsa_bits_choice, output_dir, entity_subj, validity_days=365):
    """Generates a key, CSR, and a certificate signed by the CA for an entity (server/device). Filenames are not paths."""
    print(f"\n--- Generating Certificate for {entity_name} ---")
    entity_key_filename = f"{entity_name}.key"
    entity_csr_filename = f"{entity_name}.csr"
    entity_cert_filename = f"{entity_name}.crt"

    if not generate_key(alg_choice, curve_choice, rsa_bits_choice, entity_key_filename, output_dir):
        return False
    
    if not generate_csr(entity_key_filename, entity_csr_filename, entity_subj, output_dir):
        return False

    print(f"\n--- Signing {entity_name} certificate with CA: {entity_cert_filename} ---")
    command = ['x509', '-req', '-in', entity_csr_filename, '-CA', ca_cert_filename, '-CAkey', ca_key_filename]
    
    # Use absolute path for checking srl existence, but relative for command
    srl_full_path = os.path.join(output_dir, ca_srl_filename)
    if not os.path.exists(srl_full_path):
        command.append('-CAcreateserial')
    command.extend(['-CAserial', ca_srl_filename])
    
    command.extend(['-out', entity_cert_filename, '-days', str(validity_days), '-sha256'])

    stdout, stderr = run_command(command, working_dir=output_dir, tool_name="openssl")
    if stderr:
        print(f"Error signing {entity_name} certificate: {stderr}")
        return False
    print(f"Successfully generated and signed {entity_name} certificate: {os.path.join(output_dir, entity_cert_filename)}")
    
    try:
        os.remove(os.path.join(output_dir, entity_csr_filename))
        print(f"Cleaned up CSR: {os.path.join(output_dir, entity_csr_filename)}")
    except OSError as e:
        print(f"Warning: Could not remove CSR {entity_csr_filename}: {e}")
    return True
