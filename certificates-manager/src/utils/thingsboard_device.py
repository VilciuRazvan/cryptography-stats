import requests
import json
import os
from typing import Optional

class ThingsboardDeviceManager:
    def __init__(self, host: str = "localhost", port: int = 8081):  # Updated port to 8081
        self.base_url = f"http://{host}:{port}/api"
        self.auth_token = None
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def login(self, username: str = "tenant@thingsboard.org", password: str = "tenant") -> bool:
        """Login to ThingsBoard and get JWT token"""
        login_url = f"{self.base_url}/auth/login"
        credentials = {"username": username, "password": password}
        
        try:
            response = requests.post(login_url, json=credentials)
            if response.status_code == 401:
                print("Authentication failed. Please check your credentials.")
                print(f"Response: {response.text}")
                return False
                
            response.raise_for_status()
            self.auth_token = response.json()['token']
            self.headers["X-Authorization"] = f"Bearer {self.auth_token}"
            print("Successfully logged in to ThingsBoard")
            return True
            
        except requests.exceptions.ConnectionError:
            print(f"Failed to connect to ThingsBoard server at {self.base_url}")
            print("Please ensure the server is running and the port is correct")
            return False
        except requests.exceptions.RequestException as e:
            print(f"Login failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            return False

    def create_device_with_certificate(self, device_name: str, cert_path: str) -> bool:
        """Create a device and assign X.509 certificate credentials"""
        if not self.auth_token:
            print("Not logged in. Please login first.")
            return False

        try:
            # 1. Read certificate content
            if not os.path.exists(cert_path):
                print(f"Certificate file not found: {cert_path}")
                return False

            with open(cert_path, 'r') as cert_file:
                cert_content = cert_file.read().strip()

            # 2. Create device
            create_device_url = f"{self.base_url}/device"
            device_data = {
                "name": device_name,
                "type": "default"
            }

            response = requests.post(
                create_device_url, 
                headers=self.headers, 
                json=device_data
            )
            response.raise_for_status()
            device_id = response.json()['id']['id']

            # 3. Update device credentials to use X.509 certificate
            cert_content_url = f"{self.base_url}/device/credentials"
            cert_content_data = {
                "deviceId": {
                    "entityType": "DEVICE",
                    "id": device_id
                },
                "credentialsType": "X509_CERTIFICATE",
                "credentialsValue": cert_content
            }

            cert_response = requests.post(
                cert_content_url, 
                headers=self.headers, 
                json=cert_content_data
            )
            cert_response.raise_for_status()
            print(cert_response.json())
            
            print(f"Successfully created device '{device_name}' with X.509 certificate")
            print(f"Device ID: {device_id}")
            print("Certificate content length:", len(cert_content))
            return True

        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('message', str(e))
                except:
                    error_msg = e.response.text
            print(f"Failed to create device: {error_msg}")
            return False
