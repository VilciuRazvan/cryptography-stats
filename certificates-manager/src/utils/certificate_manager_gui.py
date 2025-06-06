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
        ttk.Radiobutton(alg_frame, text="EC", variable=self.alg_var, 
                       value="EC", command=self.update_key_options).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(alg_frame, text="RSA", variable=self.alg_var, 
                       value="RSA", command=self.update_key_options).pack(side=tk.LEFT, padx=5)
        
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
        
        # Create instance of PerformanceTest for configuration
        self.perf_tester = PerformanceTest()
        
        # Add all the performance test configuration widgets
        # ... (rest of the performance test GUI code as shown earlier)

    def update_key_options(self):
        """Update key options based on selected algorithm"""
        # Clear existing options
        for widget in self.key_options_frame.winfo_children():
            widget.destroy()
        
        if self.alg_var.get() == "EC":
            # Get available curves
            curves_stdout, _ = run_command(['ecparam', '-list_curves'], tool_name="openssl")
            available_curves = parse_curves(curves_stdout)
            
            # Create list of curve names for display
            curve_names = [curve['name'] for curve in available_curves]
            curve_descriptions = {curve['name']: curve['description'] for curve in available_curves}
            
            self.curve_var = tk.StringVar(value=curve_names[0])
            ttk.Label(self.key_options_frame, text="Curve:").pack(side=tk.LEFT, padx=5)
            
            # Create combobox with curve names only
            curve_combo = ttk.Combobox(
                self.key_options_frame, 
                textvariable=self.curve_var,
                values=curve_names,
                width=40
            )
            curve_combo.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
            
            # Add tooltip or description label
            self.curve_desc_var = tk.StringVar()
            ttk.Label(
                self.key_options_frame, 
                textvariable=self.curve_desc_var
            ).pack(side=tk.LEFT, padx=5)
            
            # Update description when curve changes
            def on_curve_select(event):
                selected = curve_combo.get()
                if selected in curve_descriptions:
                    self.curve_desc_var.set(f"({curve_descriptions[selected]})")
            
            curve_combo.bind('<<ComboboxSelected>>', on_curve_select)
            # Show initial description
            self.curve_desc_var.set(f"({curve_descriptions[curve_names[0]]})")
        else:
            # RSA options remain the same
            self.rsa_bits_var = tk.StringVar(value="2048")
            ttk.Label(self.key_options_frame, text="RSA Bits:").pack(side=tk.LEFT, padx=5)
            bits_combo = ttk.Combobox(
                self.key_options_frame, 
                textvariable=self.rsa_bits_var,
                values=["2048", "3072", "4096"]
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
        """Handle applying certificates"""
        # Add certificate application logic here
        pass

    def create_device(self):
        """Handle device creation"""
        # Add device creation logic here
        pass