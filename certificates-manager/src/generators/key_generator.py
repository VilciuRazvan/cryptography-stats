from ..utils.command_runner import run_command
import os
import re

def generate_key(alg_choice, curve_choice, rsa_bits_choice, key_filename, output_dir):
    """Generates a private key. key_filename is just the name, not path."""
    print(f"\n--- Generating Private Key: {key_filename} ---")
    command = ['genpkey', '-algorithm', alg_choice]
    if alg_choice == 'EC':
        command.extend(['-pkeyopt', f'ec_paramgen_curve:{curve_choice}'])
    elif alg_choice == 'RSA':
        command.extend(['-pkeyopt', f'rsa_keygen_bits:{rsa_bits_choice}'])
    command.extend(['-out', key_filename]) # Use filename directly
    
    stdout, stderr = run_command(command, working_dir=output_dir, tool_name="openssl")
    if stderr:
        print(f"Error generating key {key_filename}: {stderr}")
        return False
    print(f"Successfully generated key: {os.path.join(output_dir, key_filename)}")
    return True

def parse_curves(output):
    """
    Parses the output of 'openssl ecparam -list_curves'.
    """
    curves = []
    if not output:
        return curves
    lines = output.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line or ':' not in line:
            continue
        
        match = re.match(r"\s*([a-zA-Z0-9_-]+)\s*:(.*)", line)
        if match:
            name = match.group(1).strip()
            description = match.group(2).strip()
            curves.append({"name": name, "description": description})
        elif re.match(r"^\s*[a-zA-Z0-9_-]+\s*$", line) and "ECDSA" not in line and "curve" not in line.lower():
             curves.append({"name": line, "description": "N/A (no description found in output)"})
    return curves

