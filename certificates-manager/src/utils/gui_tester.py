import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
from .performance_tester import PerformanceTest
from .thingsboard_device import ThingsboardDeviceManager

class PerformanceTestGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("MQTT Performance Tester")
        self.root.geometry("800x600")
        
        # Performance test instance
        self.tester = PerformanceTest()
        
        # Create main containers
        self.create_status_frame()
        self.create_main_frame()
        
        # Start connection checker
        self.check_connection_thread = threading.Thread(target=self.check_connection_periodically, daemon=True)
        self.check_connection_thread.start()

    def create_status_frame(self):
        """Create the status indicator frame"""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Connection status
        self.connection_label = ttk.Label(status_frame, text="ThingsBoard: ")
        self.connection_label.pack(side=tk.RIGHT)
        
        self.status_canvas = tk.Canvas(status_frame, width=15, height=15)
        self.status_circle = self.status_canvas.create_oval(2, 2, 13, 13, fill='gray')
        self.status_canvas.pack(side=tk.RIGHT, padx=5)

    def create_main_frame(self):
        """Create the main content frame"""
        main_frame = ttk.Frame(self.root)
        main_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=5)
        
        # Certificate Directory Selection
        ttk.Label(main_frame, text="Certificate Directory:").pack(anchor=tk.W)
        dir_frame = ttk.Frame(main_frame)
        dir_frame.pack(fill=tk.X, pady=5)
        
        self.dir_var = tk.StringVar()
        self.dir_entry = ttk.Entry(dir_frame, textvariable=self.dir_var)
        self.dir_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        ttk.Button(dir_frame, text="Browse", command=self.browse_directory).pack(side=tk.RIGHT, padx=5)
        
        # Test Parameters
        param_frame = ttk.LabelFrame(main_frame, text="Test Parameters")
        param_frame.pack(fill=tk.X, pady=10)
        
        # Iterations
        ttk.Label(param_frame, text="Iterations (1-10000):").grid(row=0, column=0, padx=5, pady=5)
        self.iterations_var = tk.StringVar(value="100")
        ttk.Entry(param_frame, textvariable=self.iterations_var, width=10).grid(row=0, column=1, padx=5)
        
        # Delay
        ttk.Label(param_frame, text="Delay (0-3600s):").grid(row=1, column=0, padx=5, pady=5)
        self.delay_var = tk.StringVar(value="2")
        ttk.Entry(param_frame, textvariable=self.delay_var, width=10).grid(row=1, column=1, padx=5)
        
        # Cipher Selection
        cipher_frame = ttk.LabelFrame(main_frame, text="Cipher Suites")
        cipher_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.cipher_vars = {}
        for i, (cipher, desc) in enumerate(self.tester.AVAILABLE_CIPHERS.items()):
            var = tk.BooleanVar(value=True)
            self.cipher_vars[cipher] = var
            ttk.Checkbutton(cipher_frame, text=f"{cipher}\n({desc})", 
                           variable=var, wraplength=300).pack(anchor=tk.W, padx=5, pady=2)
        
        # Output File
        ttk.Label(main_frame, text="Output Excel File:").pack(anchor=tk.W, pady=5)
        self.output_var = tk.StringVar(value="performance_results.xlsx")
        ttk.Entry(main_frame, textvariable=self.output_var).pack(fill=tk.X)
        
        # Control Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Start Test", command=self.start_test).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel_test).pack(side=tk.LEFT, padx=5)
        
        # Progress
        self.progress_var = tk.StringVar(value="Ready")
        ttk.Label(main_frame, textvariable=self.progress_var).pack(anchor=tk.W, pady=5)
        self.progress = ttk.Progressbar(main_frame, mode='determinate')
        self.progress.pack(fill=tk.X, pady=5)

    def browse_directory(self):
        """Open directory browser dialog"""
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.dir_var.set(dir_path)

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
        self.status_canvas.itemconfig(self.status_circle, fill=color)
        status_text = "ONLINE" if is_connected else "OFFLINE"
        self.connection_label.config(text=f"ThingsBoard: {status_text}")

    def start_test(self):
        """Start the performance test"""
        # Validate inputs
        try:
            iterations = int(self.iterations_var.get())
            delay = int(self.delay_var.get())
            if not (1 <= iterations <= 10000 and 0 <= delay <= 3600):
                raise ValueError("Invalid iterations or delay value")
        except ValueError as e:
            messagebox.showerror("Invalid Input", str(e))
            return

        # Configure test parameters
        self.tester.cert_dir = self.dir_var.get()
        self.tester.iterations = iterations
        self.tester.delay = delay
        self.tester.output_file = self.output_var.get()
        self.tester.selected_ciphers = [
            cipher for cipher, var in self.cipher_vars.items() 
            if var.get()
        ]

        # Start test in separate thread
        self.progress_var.set("Test running...")
        self.progress.start()
        threading.Thread(target=self.run_test_thread, daemon=True).start()

    def run_test_thread(self):
        """Run the test in a separate thread"""
        try:
            self.tester.run_test()
            self.root.after(0, self.test_completed)
        except Exception as e:
            self.root.after(0, self.test_failed, str(e))

    def test_completed(self):
        """Called when test completes successfully"""
        self.progress.stop()
        self.progress_var.set("Test completed!")
        messagebox.showinfo("Success", f"Test completed! Results saved to {self.tester.output_file}")

    def test_failed(self, error_msg):
        """Called when test fails"""
        self.progress.stop()
        self.progress_var.set("Test failed!")
        messagebox.showerror("Error", f"Test failed: {error_msg}")

    def cancel_test(self):
        """Cancel the running test"""
        # Implement test cancellation logic here
        self.progress.stop()
        self.progress_var.set("Test cancelled")