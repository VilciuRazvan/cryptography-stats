import subprocess

def run_command(command_list, working_dir=None, tool_name="openssl"):
    """
    Executes a command (openssl or keytool) and returns its output.
    Command_list should be a list of arguments, not including the tool itself.
    tool_name should be 'openssl' or 'keytool'.
    """
    try:
        # Prepend the tool name to the command list
        command_to_run = [tool_name] + command_list

        print(f"Executing: {' '.join(command_to_run)}") # Log the command being run
        # For commands requiring password input like keytool, Popen might need special handling
        # if we weren't passing passwords via command line args.
        # Here, we assume passwords are part of command_list for keytool where appropriate.
        process = subprocess.Popen(command_to_run, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=working_dir)
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            error_message = f"Error executing command: {' '.join(command_to_run)}\n"
            if stderr:
                error_message += f"STDERR: {stderr.strip()}\n"
            if stdout: # Some tools might output errors to stdout
                error_message += f"STDOUT: {stdout.strip()}\n"
            print(error_message)
            return None, stderr # Return None for stdout, and the stderr
        return stdout, None # Return stdout and None for stderr
    except FileNotFoundError:
        print(f"Error: {tool_name} command not found. Please ensure {tool_name} is installed and in your system's PATH.")
        return None, f"{tool_name} not found."
    except Exception as e:
        print(f"An unexpected error occurred while running {' '.join(command_to_run)}: {e}")
        return None, str(e)

def check_tool_version(tool_name):
    """Checks if a tool (openssl or keytool) is available and prints its version."""
    print(f"\n--- Checking {tool_name.capitalize()} Version ---")
    
    if tool_name == "keytool":
        # For keytool, use -help to check availability
        command = ['-help']
    else:
        command = ['version']  # For openssl
    
    version_stdout, version_stderr = run_command(command, tool_name=tool_name)
    
    if tool_name == "keytool":
        # For keytool, check if we can execute it at all
        if version_stdout is not None or version_stderr is not None:
            print(f"{tool_name.capitalize()} is available")
            return True
        # If both stdout and stderr are None, it means run_command failed
        return False
    else:
        # For openssl, check actual version output
        if version_stdout:
            print(version_stdout.strip())
            return True
    
    print(f"Could not find {tool_name}. Please ensure it is installed and in your system's PATH.")
    return False