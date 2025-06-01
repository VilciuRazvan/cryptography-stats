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

    def create_profile_with_certificate(self, profile_name, cert_path: str) -> any:
        """Create a device profile and assign X.509 certificate credentials"""
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

            # 2. Create device profile
            create_profile_url = f"{self.base_url}/deviceProfile"
            profile_data = {
                "name": profile_name,
                "type": "DEFAULT",
                "transportType": "MQTT",
                "provisionType": "X509_CERTIFICATE_CHAIN",
                "profileData": {
                    "transportConfiguration": {
                        "type": "MQTT",
                        "@type": "MqttDeviceProfileTransportConfiguration"
                    },
                    "provisionConfiguration": {
                        "type": "X509_CERTIFICATE_CHAIN",
                        "@type": "X509CertificateChainProvisionConfiguration",
                        "provisionDeviceSecret": cert_content,
                        "certificateRegExPattern": "CN=(.*?)(?:,|$)",
                        "allowCreateNewDevicesByX509Certificate": True
                    }
                }
            }
            print(f"Attempting to create device profile '{profile_name}'...")
            response = requests.post(
                create_profile_url,
                headers=self.headers,
                json=profile_data
            )
            response.raise_for_status()  # Will raise an error for HTTP errors

            profile = response.json()
            print(f"Device profile '{profile_name}' created with ID: {profile['id']['id']}")
            return profile

        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('message', str(e))
                except json.JSONDecodeError:
                    error_msg = e.response.text
            print(f"Failed to create device profile: {error_msg}")
            return False

    def create_device_with_profile(self, device_name: str, profile_name: str = "default") -> str:
        if not self.auth_token:
            print("Not logged in. Please login first.")
            return False

        try:
            create_device_url = f"{self.base_url}/device"
            device_data = {
                "name": device_name,
                "type": profile_name
            }
            print(f"Attempting to create device '{device_name}'...")
            response = requests.post(
                create_device_url,
                headers=self.headers,
                json=device_data
            )

            response.raise_for_status() # Will raise an error if device creation itself failed (e.g. duplicate name)
            device_id = response.json()['id']['id']
            print(f"Device '{device_name}' created/retrieved with ID: {device_id}")

            return device_id
        except requests.exceptions.RequestException as e:
            print(f"Failed to create device: {str(e)}")
            return False
        
    def get_device_credentials(self, device_id: str) -> Optional[dict]:
        """Retrieve device credentials by ID, returning only id.id and credentialsValue"""
        if not self.auth_token:
            print("Not logged in. Please login first.")
            return None

        try:
            credentials_url = f"{self.base_url}/device/{device_id}/credentials"
            response = requests.get(credentials_url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            return {
                "id": data.get("id", {}).get("id"),
                "credentialsId": data.get("credentialsId")
            }

        except requests.exceptions.RequestException as e:
            print(f"Failed to retrieve device credentials: {str(e)}")
            return None

    def post_modify_device_credentials(self, credentials: dict, device_id: str, cert_path: str) -> bool:
        """Modify device credentials by ID to use device certificate"""
        if not self.auth_token:
            print("Not logged in. Please login first.")
            return False
        
        if not os.path.exists(cert_path):
            print(f"Certificate file not found: {cert_path}")
            return False
        
        cert_content = None
        try:
            with open(cert_path, 'r') as cert_file:
                cert_content = cert_file.read().strip()
        except Exception as e:
            print(f"Failed to read certificate file: {str(e)}")
            return False
        
        print(f"Attempting to modify device credentials for device ID {device_id}...")
        request_body = {
            "id": {
                "id": credentials.get("id")
            },
            "deviceId": {
                "entityType": "DEVICE",
                "id": device_id
            },
            "credentialsType": "X509_CERTIFICATE",
            "credentialsId": credentials.get("credentialsId"),
            "credentialsValue": cert_content
        }

        try:
            modify_url = f"{self.base_url}/device/credentials"
            response = requests.post(modify_url, headers=self.headers, json=request_body)
            response.raise_for_status()
            print(f"Device credentials for ID {device_id} modified successfully.")
            return True
        except requests.exceptions.RequestException as e:
            print(f"Failed to modify device credentials: {str(e)}")
            return False