import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
from .performance_tester import PerformanceTest
from .thingsboard_device import ThingsboardDeviceManager
from ..generators.key_generator import generate_key, parse_curves
from ..generators.cert_generator import generate_ca_certificate, generate_signed_certificate
from ..generators.store_generator import generate_pkcs12_file, create_server_keystore, create_truststore
from ..utils.command_runner import run_command
import os
import shutil
import ctypes

THINGSBOARD_CONF_PATH = "C:\\Program Files\\Thingsboard\\thingsboard\\conf\\certs\\test"

SUPPORTED_ALGORITHMS = {
    "RSA": {
        "name": "RSA",
        "key_options": {
            "type": "bits",
            "values": ["2048", "3072", "4096", "8192"],
            "default": "2048"
        }
    },
    "EC": {
        "name": "EC",
        "key_options": {
            "type": "curve",
            "values": None,  # Will be populated from OpenSSL
            "default": None  # Will be set after getting curves
        }
    },
    "Ed25519": {
        "name": "Ed25519",
        "key_options": {
            "type": "none",
            "values": None,
            "default": None
        }
    },
    "Ed448": {
        "name": "Ed448",
        "key_options": {
            "type": "none",
            "values": None,
            "default": None
        }
    }
}

class CertificateManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Certificate Management Utility")
        self.root.geometry("1024x768")
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill='both', padx=5, pady=5)
        
        # Create tabs
        self.create_certificate_tab()
        self.create_apply_certificates_tab()
        self.create_device_tab()
        self.create_performance_tab()
        
        # Create status bar
        self.create_status_bar()
        
        # Start connection checker
        self.check_connection_thread = threading.Thread(
            target=self.check_connection_periodically, 
            daemon=True
        )
        self.check_connection_thread.start()

    def create_status_bar(self):
        """Create status bar with ThingsBoard connection indicator"""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=5)
        
        # Left side - general status
        self.status_label = ttk.Label(status_frame, text="Ready")
        self.status_label.pack(side=tk.LEFT)
        
        # Right side - ThingsBoard connection status
        connection_frame = ttk.Frame(status_frame)
        connection_frame.pack(side=tk.RIGHT)
        
        self.status_canvas = tk.Canvas(connection_frame, width=15, height=15)
        self.status_circle = self.status_canvas.create_oval(2, 2, 13, 13, fill='gray')
        self.status_canvas.pack(side=tk.LEFT, padx=5)
        
        self.connection_label = ttk.Label(connection_frame, text="ThingsBoard: Unknown")
        self.connection_label.pack(side=tk.LEFT)
        
        # Add connection details label
        self.connection_details = ttk.Label(connection_frame, text="")
        self.connection_details.pack(side=tk.LEFT, padx=5)

    def create_certificate_tab(self):
        """Create certificate generation tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Generate Certificates")
        
        # Algorithm selection
        alg_frame = ttk.LabelFrame(tab, text="Certificate Algorithm")
        alg_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.alg_var = tk.StringVar(value="EC")
        for alg in SUPPORTED_ALGORITHMS.keys():
            ttk.Radiobutton(
                alg_frame, 
                text=alg, 
                variable=self.alg_var,
                value=alg, 
                command=self.update_key_options
            ).pack(side=tk.LEFT, padx=5)
        
        # Key options frame
        self.key_options_frame = ttk.LabelFrame(tab, text="Key Options")
        self.key_options_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Initialize key options based on default selection
        self.update_key_options()  # Add this line here
        
        # Common Names frame
        names_frame = ttk.LabelFrame(tab, text="Certificate Names")
        names_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(names_frame, text="CA Common Name:").grid(row=0, column=0, padx=5, pady=5)
        self.ca_cn = tk.StringVar(value="My Test CA")
        ttk.Entry(names_frame, textvariable=self.ca_cn).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(names_frame, text="Server Common Name:").grid(row=1, column=0, padx=5, pady=5)
        self.server_cn = tk.StringVar(value="localhost")
        ttk.Entry(names_frame, textvariable=self.server_cn).grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(names_frame, text="Device Common Name:").grid(row=2, column=0, padx=5, pady=5)
        self.device_cn = tk.StringVar(value="device001")
        ttk.Entry(names_frame, textvariable=self.device_cn).grid(row=2, column=1, padx=5, pady=5)
        
        # Output directory
        dir_frame = ttk.Frame(tab)
        dir_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(dir_frame, text="Output Directory:").pack(side=tk.LEFT)
        self.output_dir = tk.StringVar(value="certificates")
        ttk.Entry(dir_frame, textvariable=self.output_dir).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(dir_frame, text="Browse", command=self.browse_output_dir).pack(side=tk.RIGHT)
        
        # Generate button
        ttk.Button(tab, text="Generate Certificates", 
                  command=self.generate_certificates).pack(pady=20)
        
        # Progress
        self.cert_progress_var = tk.StringVar(value="Ready")
        ttk.Label(tab, textvariable=self.cert_progress_var).pack()
        self.cert_progress = ttk.Progressbar(tab, mode='determinate')
        self.cert_progress.pack(fill=tk.X, padx=5, pady=5)

    def create_apply_certificates_tab(self):
        """Create tab for applying certificates"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Apply Certificates")
        
        # Warning label
        ttk.Label(tab, text="This operation requires administrator privileges",
                 foreground='red').pack(pady=10)
        
        # Certificate directory selection
        dir_frame = ttk.Frame(tab)
        dir_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.cert_dir = tk.StringVar()
        ttk.Label(dir_frame, text="Certificate Directory:").pack(side=tk.LEFT)
        ttk.Entry(dir_frame, textvariable=self.cert_dir).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(dir_frame, text="Browse", 
                  command=lambda: self.browse_directory(self.cert_dir)).pack(side=tk.RIGHT)
        
        # Apply button
        ttk.Button(tab, text="Apply Certificates", 
                  command=self.apply_certificates).pack(pady=20)
        
        # Progress
        self.apply_progress_var = tk.StringVar(value="Ready")
        ttk.Label(tab, textvariable=self.apply_progress_var).pack()

    def create_device_tab(self):
        """Create tab for device management"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Device Management")
        
        # Device configuration
        config_frame = ttk.LabelFrame(tab, text="Device Configuration")
        config_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(config_frame, text="Device Name:").grid(row=0, column=0, padx=5, pady=5)
        self.device_name = tk.StringVar(value="device001")
        ttk.Entry(config_frame, textvariable=self.device_name).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(config_frame, text="Certificate Directory:").grid(row=1, column=0, padx=5, pady=5)
        self.device_cert_dir = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.device_cert_dir).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(config_frame, text="Browse", 
                  command=lambda: self.browse_directory(self.device_cert_dir)).grid(row=1, column=2, padx=5)
        
        # Create device button
        ttk.Button(tab, text="Create Device", 
                  command=self.create_device).pack(pady=20)
        
        # Progress
        self.device_progress_var = tk.StringVar(value="Ready")
        ttk.Label(tab, textvariable=self.device_progress_var).pack()

    def create_performance_tab(self):
        """Create performance testing tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Performance Testing")
        
        # Test configuration
        config_frame = ttk.LabelFrame(tab, text="Test Configuration")
        config_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Certificate Directory Selection
        dir_frame = ttk.Frame(config_frame)
        dir_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(dir_frame, text="Certificate Directory:").pack(side=tk.LEFT)
        self.perf_cert_dir = tk.StringVar()
        ttk.Entry(dir_frame, textvariable=self.perf_cert_dir).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(dir_frame, text="Browse", 
                  command=lambda: self.browse_directory(self.perf_cert_dir)).pack(side=tk.RIGHT)

        # Test Parameters
        param_frame = ttk.LabelFrame(config_frame, text="Test Parameters")
        param_frame.pack(fill=tk.X, pady=5)
        
        # Iterations
        iter_frame = ttk.Frame(param_frame)
        iter_frame.pack(fill=tk.X, pady=2)
        ttk.Label(iter_frame, text="Number of iterations:").pack(side=tk.LEFT)
        self.iterations_var = tk.StringVar(value="100")
        ttk.Entry(iter_frame, textvariable=self.iterations_var, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Label(iter_frame, text="(1-10000)").pack(side=tk.LEFT)
        
        # Delay
        delay_frame = ttk.Frame(param_frame)
        delay_frame.pack(fill=tk.X, pady=2)
        ttk.Label(delay_frame, text="Delay between iterations (seconds):").pack(side=tk.LEFT)
        self.delay_var = tk.StringVar(value="2")
        ttk.Entry(delay_frame, textvariable=self.delay_var, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Label(delay_frame, text="(0-3600)").pack(side=tk.LEFT)
        
        # Cipher Selection
        cipher_frame = ttk.LabelFrame(tab, text="Cipher Suites")
        cipher_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Create checkboxes for each cipher
        self.cipher_vars = {}
        for cipher, description in PerformanceTest.AVAILABLE_CIPHERS.items():
            var = tk.BooleanVar(value=True)
            self.cipher_vars[cipher] = var
            tk.Checkbutton(
                cipher_frame, 
                text=f"{cipher}\n({description})", 
                variable=var,
                wraplength=400
            ).pack(anchor=tk.W, padx=5, pady=2)
        
        # Output File
        output_frame = ttk.Frame(tab)
        output_frame.pack(fill=tk.X, pady=5)
        ttk.Label(output_frame, text="Output Excel File:").pack(side=tk.LEFT)
        self.perf_output_var = tk.StringVar(value="performance_results.xlsx")
        ttk.Entry(output_frame, textvariable=self.perf_output_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Control buttons
        button_frame = ttk.Frame(tab)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Start Test", 
                   command=self.run_performance_test).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel Test", 
                   command=self.cancel_performance_test).pack(side=tk.LEFT, padx=5)
        
        # Progress
        self.perf_progress_var = tk.StringVar(value="Ready")
        ttk.Label(tab, textvariable=self.perf_progress_var).pack()
        self.perf_progress = ttk.Progressbar(tab, mode='determinate')
        self.perf_progress.pack(fill=tk.X, padx=5, pady=5)

    def update_key_options(self):
        """Update key options based on selected algorithm"""
        # Clear existing options
        for widget in self.key_options_frame.winfo_children():
            widget.destroy()
        
        selected_alg = self.alg_var.get()
        alg_config = SUPPORTED_ALGORITHMS[selected_alg]
        
        if alg_config["key_options"]["type"] == "none":
            # No options needed for this algorithm
            ttk.Label(
                self.key_options_frame, 
                text="No additional options required"
            ).pack(side=tk.LEFT, padx=5)
            return
            
        if alg_config["key_options"]["type"] == "curve":
            # Get available curves if not already populated
            if alg_config["key_options"]["values"] is None:
                curves_stdout, _ = run_command(['ecparam', '-list_curves'], tool_name="openssl")
                available_curves = parse_curves(curves_stdout)
                alg_config["key_options"]["values"] = [curve['name'] for curve in available_curves]
                alg_config["key_options"]["descriptions"] = {
                    curve['name']: curve['description'] for curve in available_curves
                }
                alg_config["key_options"]["default"] = alg_config["key_options"]["values"][0]
            
            self.curve_var = tk.StringVar(value=alg_config["key_options"]["default"])
            ttk.Label(self.key_options_frame, text="Curve:").pack(side=tk.LEFT, padx=5)
            
            curve_combo = ttk.Combobox(
                self.key_options_frame,
                textvariable=self.curve_var,
                values=alg_config["key_options"]["values"],
                width=40
            )
            curve_combo.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
            
            # Add curve description
            self.curve_desc_var = tk.StringVar()
            ttk.Label(
                self.key_options_frame,
                textvariable=self.curve_desc_var
            ).pack(side=tk.LEFT, padx=5)
            
            def on_curve_select(event):
                selected = curve_combo.get()
                if selected in alg_config["key_options"]["descriptions"]:
                    self.curve_desc_var.set(
                        f"({alg_config['key_options']['descriptions'][selected]})"
                    )
            
            curve_combo.bind('<<ComboboxSelected>>', on_curve_select)
            # Show initial description
            self.curve_desc_var.set(
                f"({alg_config['key_options']['descriptions'][alg_config['key_options']['default']]}"
            )
            
        elif alg_config["key_options"]["type"] == "bits":
            self.rsa_bits_var = tk.StringVar(value=alg_config["key_options"]["default"])
            ttk.Label(self.key_options_frame, text="Key Size:").pack(side=tk.LEFT, padx=5)
            bits_combo = ttk.Combobox(
                self.key_options_frame,
                textvariable=self.rsa_bits_var,
                values=alg_config["key_options"]["values"]
            )
            bits_combo.pack(side=tk.LEFT, padx=5)

    def browse_output_dir(self):
        """Handle browsing for output directory"""
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.output_dir.set(dir_path)

    def browse_directory(self, string_var):
        """Generic directory browser that updates a StringVar"""
        dir_path = filedialog.askdirectory()
        if dir_path:
            string_var.set(dir_path)

    def check_connection_periodically(self):
        """Periodically check ThingsBoard connection"""
        while True:
            tb_manager = ThingsboardDeviceManager()
            is_connected = tb_manager.check_connection()
            
            self.root.after(0, self.update_connection_status, is_connected)
            time.sleep(5)  # Check every 5 seconds

    def update_connection_status(self, is_connected):
        """Update the connection status indicator"""
        color = 'green' if is_connected else 'red'
        status_text = "ONLINE" if is_connected else "OFFLINE"
        
        self.status_canvas.itemconfig(self.status_circle, fill=color)
        self.connection_label.config(text=f"ThingsBoard: {status_text}")
        
        # Update connection details
        if is_connected:
            self.connection_details.config(
                text="(tenant@thingsboard.org)",
                foreground='green'
            )
        else:
            self.connection_details.config(
                text="(Not Connected)",
                foreground='red'
            )

    def generate_certificates(self):
        """Handle certificate generation workflow"""
        # Validate inputs first
        if not self.validate_inputs():
            return

        # Start progress
        self.cert_progress_var.set("Starting certificate generation...")
        self.cert_progress['value'] = 0
        self.root.update()

        try:
            # Create output directory
            output_dir = self.output_dir.get()
            if os.path.exists(output_dir):
                if not messagebox.askyesno("Directory exists", 
                    f"Directory '{output_dir}' already exists. Overwrite?"):
                    return
                try:
                    shutil.rmtree(output_dir)
                except Exception as e:
                    messagebox.showerror("Error", f"Could not remove existing directory: {e}")
                    return

            os.makedirs(output_dir, exist_ok=True)

            # Setup filenames
            ca_key_fn = "ca.key"
            ca_cert_fn = "ca.crt"
            ca_srl_fn = "ca.srl"
            server_key_fn = "server.key"
            server_cert_fn = "server.crt"
            device_key_fn = "device1.key"
            device_cert_fn = "device1.crt"
            server_p12_fn = "server.p12"
            server_keystore_fn = "server_keystore.jks"
            truststore_fn = "server_truststore.jks"

            # Generate CA Certificate (20%)
            self.cert_progress_var.set("Generating CA certificate...")
            self.cert_progress['value'] = 20
            self.root.update()

            ca_subj = f"/CN={self.ca_cn.get()}"
            if not generate_ca_certificate(
                self.alg_var.get(),
                self.curve_var.get() if self.alg_var.get() == 'EC' else None,
                int(self.rsa_bits_var.get()) if self.alg_var.get() == 'RSA' else None,
                output_dir,
                ca_subj
            ):
                raise Exception("Failed to generate CA certificate")

            # Generate Server Certificate (40%)
            self.cert_progress_var.set("Generating server certificate...")
            self.cert_progress['value'] = 40
            self.root.update()

            server_subj = f"/CN={self.server_cn.get()}"
            if not generate_signed_certificate(
                "server",
                ca_key_fn,
                ca_cert_fn,
                ca_srl_fn,
                self.alg_var.get(),
                self.curve_var.get() if self.alg_var.get() == 'EC' else None,
                int(self.rsa_bits_var.get()) if self.alg_var.get() == 'RSA' else None,
                output_dir,
                server_subj
            ):
                raise Exception("Failed to generate server certificate")

            # Generate Device Certificate (60%)
            self.cert_progress_var.set("Generating device certificate...")
            self.cert_progress['value'] = 60
            self.root.update()

            device_subj = f"/CN={self.device_cn.get()}"
            if not generate_signed_certificate(
                "device1",
                ca_key_fn,
                ca_cert_fn,
                ca_srl_fn,
                self.alg_var.get(),
                self.curve_var.get() if self.alg_var.get() == 'EC' else None,
                int(self.rsa_bits_var.get()) if self.alg_var.get() == 'RSA' else None,
                output_dir,
                device_subj
            ):
                raise Exception("Failed to generate device certificate")

            # Generate PKCS12 and JKS (80%)
            self.cert_progress_var.set("Generating PKCS12 and JKS files...")
            self.cert_progress['value'] = 80
            self.root.update()

            # Use default "changeit" password for all stores
            p12_password = "changeit"
            keystore_password = "changeit"
            truststore_password = "changeit"

            if not generate_pkcs12_file(
                server_cert_fn,
                server_key_fn,
                ca_cert_fn,
                server_p12_fn,
                "server",
                p12_password,
                output_dir
            ):
                raise Exception("Failed to generate PKCS12 file")

            if not create_server_keystore(
                server_p12_fn,
                server_keystore_fn,
                p12_password,
                keystore_password,
                "server",
                output_dir
            ):
                raise Exception("Failed to create server keystore")

            if not create_truststore(
                ca_cert_fn,
                truststore_fn,
                truststore_password,
                "root-ca",
                output_dir
            ):
                raise Exception("Failed to create truststore")

            # Complete (100%)
            self.cert_progress['value'] = 100
            self.cert_progress_var.set("Certificate generation complete!")
            
            # Show success message with file list
            messagebox.showinfo("Success", 
                f"Certificates generated successfully in:\n{os.path.abspath(output_dir)}\n\n"
                f"Files generated:\n"
                f"- CA: {ca_key_fn}, {ca_cert_fn}\n"
                f"- Server: {server_key_fn}, {server_cert_fn}\n"
                f"- Device: {device_key_fn}, {device_cert_fn}\n"
                f"- Keystores: {server_p12_fn}, {server_keystore_fn}, {truststore_fn}"
            )

        except Exception as e:
            self.cert_progress['value'] = 0
            self.cert_progress_var.set("Certificate generation failed!")
            messagebox.showerror("Error", str(e))

    def validate_inputs(self) -> bool:
        """Validate all inputs before starting certificate generation"""
        if not self.output_dir.get():
            messagebox.showerror("Error", "Please specify an output directory")
            return False

        if not self.ca_cn.get():
            messagebox.showerror("Error", "Please specify a CA Common Name")
            return False

        if not self.server_cn.get():
            messagebox.showerror("Error", "Please specify a Server Common Name")
            return False

        if not self.device_cn.get():
            messagebox.showerror("Error", "Please specify a Device Common Name")
            return False

        return True

    def apply_certificates(self):
        """Handle applying certificates to services"""
        # Check admin rights
        if not ctypes.windll.shell32.IsUserAnAdmin():
            messagebox.showerror(
                "Administrator Rights Required", 
                "This operation requires administrator privileges.\nPlease run the application as administrator."
            )
            return

        # Validate certificate directory
        cert_dir = self.cert_dir.get()
        if not cert_dir:
            messagebox.showerror("Error", "Please select a certificate directory")
            return

        # Check required files
        keystore_path = os.path.join(cert_dir, "server_keystore.jks")
        truststore_path = os.path.join(cert_dir, "server_truststore.jks")
        
        if not os.path.exists(keystore_path) or not os.path.exists(truststore_path):
            messagebox.showerror(
                "Files Not Found", 
                f"Required JKS files not found in selected directory:\n"
                f"  {keystore_path}\n"
                f"  {truststore_path}"
            )
            return

        try:
            # Update progress
            self.apply_progress_var.set("Stopping ThingsBoard service...")
            self.root.update()

            # Stop ThingsBoard
            stop_result = os.system('net stop thingsboard')
            if stop_result != 0:
                if not messagebox.askyesno(
                    "Service Stop Failed",
                    "Failed to stop ThingsBoard service. Continue anyway?\n"
                    "Files might still be copyable if service is not running."
                ):
                    return

            # Copy files
            self.apply_progress_var.set("Copying certificate files...")
            self.root.update()

            try:
                # Ensure target directory exists
                os.makedirs(THINGSBOARD_CONF_PATH, exist_ok=True)
                
                # Copy files with overwrite
                shutil.copy2(keystore_path, os.path.join(THINGSBOARD_CONF_PATH, "server_keystore.jks"))
                shutil.copy2(truststore_path, os.path.join(THINGSBOARD_CONF_PATH, "server_truststore.jks"))
                
            except Exception as e:
                messagebox.showerror("Copy Error", f"Error copying files: {str(e)}")
                return

            # Start ThingsBoard
            self.apply_progress_var.set("Starting ThingsBoard service...")
            self.root.update()

            start_result = os.system('net start thingsboard')
            if start_result != 0:
                messagebox.showerror(
                    "Service Start Failed",
                    "Failed to start ThingsBoard service.\n"
                    "Please start it manually from Services."
                )
                return

            # Success
            self.apply_progress_var.set("Certificates applied successfully!")
            messagebox.showinfo(
                "Success", 
                "Certificates applied successfully!\nThingsBoard service restarted. Please wait up to a minute for it to come online."
            )

        except Exception as e:
            messagebox.showerror("Error", f"Error applying certificates: {str(e)}")
            self.apply_progress_var.set("Operation failed!")

    def create_device(self):
        """Handle device creation workflow"""
        # 1. Validate inputs
        cert_dir = self.device_cert_dir.get()
        if not cert_dir:
            messagebox.showerror("Error", "Please select a certificate directory")
            return

        # Check required files
        ca_cert_path = os.path.join(cert_dir, "ca.crt")
        device_cert_path = os.path.join(cert_dir, "device1.crt")
        
        if not os.path.exists(device_cert_path) or not os.path.exists(ca_cert_path):
            messagebox.showerror(
                "Files Not Found",
                f"Required certificate files not found in selected directory:\n"
                f"  {ca_cert_path}\n"
                f"  {device_cert_path}"
            )
            return

        # 2. Get device name
        device_name = self.device_name.get()
        if not device_name:
            device_name = "device001"  # Default name if empty
        
        # 3. Start device creation process
        self.device_progress_var.set("Connecting to ThingsBoard...")
        self.root.update()

        try:
            tb_manager = ThingsboardDeviceManager()
            if not tb_manager.login():
                messagebox.showerror(
                    "Connection Error",
                    "Failed to connect to ThingsBoard.\nPlease ensure the server is running."
                )
                self.device_progress_var.set("Connection failed")
                return

            # Create device profile
            self.device_progress_var.set("Creating device profile...")
            self.root.update()
            
            profile_name = f"Profile_{device_name}"
            profile = tb_manager.create_profile_with_certificate(profile_name, ca_cert_path)
            if not profile:
                raise Exception("Failed to create device profile")

            # Create device
            self.device_progress_var.set("Creating device...")
            self.root.update()
            
            device_id = tb_manager.create_device_with_profile(
                device_name=device_name,
                profile_name=profile_name
            )
            if not device_id:
                raise Exception("Failed to create device")

            # Update device credentials
            self.device_progress_var.set("Updating device credentials...")
            self.root.update()
            
            device_credentials = tb_manager.get_device_credentials(device_id=device_id)
            if not device_credentials:
                raise Exception("Failed to get device credentials")

            if not tb_manager.post_modify_device_credentials(
                credentials=device_credentials,
                device_id=device_id,
                cert_path=device_cert_path
            ):
                raise Exception("Failed to update device credentials")

            # Success
            self.device_progress_var.set("Device created successfully!")
            messagebox.showinfo(
                "Success",
                f"Successfully created and configured device '{device_name}'\n\n"
                f"Profile: {profile_name}\n"
                f"Device ID: {device_id}\n"
                f"Certificate: {os.path.basename(device_cert_path)}"
            )

        except Exception as e:
            self.device_progress_var.set("Device creation failed!")
            messagebox.showerror("Error", str(e))

    def run_performance_test(self):
        """Start performance test execution"""
        # Validate inputs
        try:
            iterations = int(self.iterations_var.get())
            delay = int(self.delay_var.get())
            if not (1 <= iterations <= 10000):
                raise ValueError("Iterations must be between 1 and 10000")
            if not (0 <= delay <= 3600):
                raise ValueError("Delay must be between 0 and 3600 seconds")
        except ValueError as e:
            messagebox.showerror("Invalid Input", str(e))
            return

        # Check certificate directory
        cert_dir = self.perf_cert_dir.get()
        if not cert_dir:
            messagebox.showerror("Error", "Please select a certificate directory")
            return

        # Check required files
        required_files = ["ca.crt", "device1.crt", "device1.key"]
        for file in required_files:
            if not os.path.exists(os.path.join(cert_dir, file)):
                messagebox.showerror(
                    "Files Not Found",
                    f"Missing required file: {file}\n"
                    f"Please select a directory containing the device certificates."
                )
                return

        # Get selected ciphers
        selected_ciphers = [
            cipher for cipher, var in self.cipher_vars.items() 
            if var.get()
        ]
        if not selected_ciphers:
            messagebox.showerror("Error", "Please select at least one cipher suite")
            return

        # Add cancellation flag
        self.test_cancelled = False
        
        # Configure test
        tester = PerformanceTest()
        tester.cert_dir = cert_dir
        tester.iterations = iterations
        tester.delay = delay
        tester.selected_ciphers = selected_ciphers
        tester.output_file = self.perf_output_var.get()

        # Calculate total number of tests
        total_tests = len(selected_ciphers) * iterations
        self.total_tests = total_tests
        self.completed_tests = 0

        # Reset and configure progress bar
        self.perf_progress.stop()
        self.perf_progress['value'] = 0
        self.perf_progress['maximum'] = total_tests

        # Start test in separate thread
        self.perf_progress_var.set(f"Test running... (0/{total_tests} tests completed)")
        self.test_thread = threading.Thread(
            target=self._run_performance_test_thread,
            args=(tester,),
            daemon=True
        )
        self.test_thread.start()

    def _run_performance_test_thread(self, tester):
        """Run performance test in separate thread"""
        try:
            from .mqtt.test_runner import run_mqtt_test, calculate_statistics, MqttTestConfig
            from .mqtt.excel_handler import export_results_to_excel

            all_run_data = {}
            
            # Create test configurations
            test_configs = {}
            for cipher in tester.selected_ciphers:
                config_name = f"Test_{cipher}"
                config = MqttTestConfig(
                    host="localhost",
                    port=8883,
                    tls=True,
                    ca_certs=os.path.join(tester.cert_dir, "ca.crt"),
                    certfile=os.path.join(tester.cert_dir, "device1.crt"),
                    keyfile=os.path.join(tester.cert_dir, "device1.key"),
                    ciphers=cipher
                )
                test_configs[config_name] = config

            # Run tests for each configuration
            for config_name, config in test_configs.items():
                # Check if cancelled
                if self.test_cancelled:
                    self.root.after(0, self._performance_test_cancelled)
                    return
                
                iteration_results = []
                
                for i in range(1, tester.iterations + 1):
                    # Check if cancelled
                    if self.test_cancelled:
                        self.root.after(0, self._performance_test_cancelled)
                        return
                    
                    # Update progress
                    self.completed_tests += 1
                    self.root.after(0, self._update_progress)
                    
                    # Run test iteration
                    run_state = run_mqtt_test(i, config_name, config.__dict__)
                    iteration_data = run_state.get_results_dict()
                    iteration_results.append(iteration_data)

                    if tester.delay > 0 and i < tester.iterations:
                        time.sleep(tester.delay)

                all_run_data[config_name] = iteration_results

            # Export results if not cancelled
            if not self.test_cancelled:
                export_results_to_excel(
                    all_run_data=all_run_data,
                    excel_filename=tester.output_file,
                    calculate_statistics=calculate_statistics
                )
                self.root.after(0, self._performance_test_completed, tester.output_file)
            else:
                self.root.after(0, self._performance_test_cancelled)
                
        except Exception as e:
            if not self.test_cancelled:
                self.root.after(0, self._performance_test_failed, str(e))

    def _update_progress(self):
        """Update the progress bar and status text"""
        self.perf_progress['value'] = self.completed_tests
        self.perf_progress_var.set(
            f"Test running... ({self.completed_tests}/{self.total_tests} tests completed)"
        )

    def cancel_performance_test(self):
        """Cancel running performance test"""
        if hasattr(self, 'test_thread') and self.test_thread.is_alive():
            self.test_cancelled = True
            self.perf_progress.stop()
            self.perf_progress_var.set("Cancelling test...")

    def _performance_test_cancelled(self):
        """Called when test is cancelled"""
        self.perf_progress.stop()
        self.perf_progress_var.set("Test cancelled")
        messagebox.showinfo(
            "Cancelled", 
            "Performance test cancelled.\nPartial results were not saved."
        )

    def _performance_test_completed(self, output_file):
        """Called when performance test completes successfully"""
        self.perf_progress['value'] = self.total_tests
        self.perf_progress_var.set("Test completed!")
        messagebox.showinfo(
            "Test Complete", 
            f"Performance test completed successfully!\nResults saved to: {output_file}"
        )

    def _performance_test_failed(self, error_msg):
        """Called when performance test fails"""
        self.perf_progress.stop()
        self.perf_progress_var.set("Test failed!")
        messagebox.showerror(
            "Test Failed", 
            f"Performance test failed with error:\n{error_msg}"
        )