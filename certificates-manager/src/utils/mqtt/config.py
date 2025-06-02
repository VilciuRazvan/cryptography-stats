# MQTT server settings
MQTT_HOST = "localhost"
MQTT_PORT_MTLS = 8883
MQTT_PORT_PLAIN = 1884

# Test parameters
NUM_ITERATIONS = 1
DELAY_BETWEEN_ITERATIONS = 2
EXCEL_FILENAME = "Without Certificates.xlsx"

# Certificate paths
CA_CERT_ECC_P256 = "certificates/ECC_P256/ca.crt"
CLIENT_CERT_ECC_P256 = "certificates/ECC_P256/device1.crt"
CLIENT_KEY_ECC_P256 = "certificates/ECC_P256/device1.key"

CA_CERT_ECC_P384 = "certificates/ECC_P384/ca.crt"
CLIENT_CERT_ECC_P384 = "certificates/ECC_P384/device1.crt"
CLIENT_KEY_ECC_P384 = "certificates/ECC_P384/device1.key"

CA_CERT_EDDSA_ED25519 = "certificates/EdDSA_Ed25519/ca.crt"
CLIENT_CERT_EDDSA_ED25519 = "certificates/EdDSA_Ed25519/device1.crt"
CLIENT_KEY_EDDSA_ED25519 = "certificates/EdDSA_Ed25519/device1.key"

CA_CERT_RSA_2048 = "certificates/RSA_2048/ca.crt"
CLIENT_CERT_RSA_2048 = "certificates/RSA_2048/device1.crt"
CLIENT_KEY_RSA_2048 = "certificates/RSA_2048/device1.key"

# Authentication credentials
ACCESS_TOKEN = "6ck81numxq7qljraejvg"
BASIC_USER = "mqtt-user"
BASIC_PASS = "mqtt-pass"

# Test configurations
# Modify Thingsboard.yml to set the correct certificate paths and authentication methods
# Uncomment the desired test configurations to run them
test_configs = {
    # ECC P256
    # "ECC_P256_AES128GCM_SHA256": {
    #     "host": MQTT_HOST,
    #     "port": MQTT_PORT_MTLS,
    #     "tls": True,
    #     "ca_certs": CA_CERT_ECC_P256,
    #     "certfile": CLIENT_CERT_ECC_P256,
    #     "keyfile": CLIENT_KEY_ECC_P256,
    #     "ciphers": "ECDHE-ECDSA-AES128-GCM-SHA256"
    # },
    # "ECC_P256_AES256GCM_SHA384": {
    #     "host": MQTT_HOST,
    #     "port": MQTT_PORT_MTLS,
    #     "tls": True,
    #     "ca_certs": CA_CERT_ECC_P256,
    #     "certfile": CLIENT_CERT_ECC_P256,
    #     "keyfile": CLIENT_KEY_ECC_P256,
    #     "ciphers": "ECDHE-ECDSA-AES256-GCM-SHA384"
    # },
    # "ECC_P256_CHACHA20_POLY1305": {
    #     "host": MQTT_HOST,
    #     "port": MQTT_PORT_MTLS,
    #     "tls": True,
    #     "ca_certs": CA_CERT_ECC_P256,
    #     "certfile": CLIENT_CERT_ECC_P256,
    #     "keyfile": CLIENT_KEY_ECC_P256,
    #     "ciphers": "ECDHE-ECDSA-CHACHA20-POLY1305"
    # },

    # # ECC P384
    # "ECC_P384_AES128GCM_SHA256": {
    #     "host": MQTT_HOST,
    #     "port": MQTT_PORT_MTLS,
    #     "tls": True,
    #     "ca_certs": CA_CERT_ECC_P384,
    #     "certfile": CLIENT_CERT_ECC_P384,
    #     "keyfile": CLIENT_KEY_ECC_P384,
    #     "ciphers": "ECDHE-ECDSA-AES128-GCM-SHA256"
    # },
    # "ECC_P384_AES256GCM_SHA384": {
    #     "host": MQTT_HOST,
    #     "port": MQTT_PORT_MTLS,
    #     "tls": True,
    #     "ca_certs": CA_CERT_ECC_P384,
    #     "certfile": CLIENT_CERT_ECC_P384,
    #     "keyfile": CLIENT_KEY_ECC_P384,
    #     "ciphers": "ECDHE-ECDSA-AES256-GCM-SHA384"
    # },
    # "ECC_P384_CHACHA20_POLY1305": {
    #     "host": MQTT_HOST,
    #     "port": MQTT_PORT_MTLS,
    #     "tls": True,
    #     "ca_certs": CA_CERT_ECC_P384,
    #     "certfile": CLIENT_CERT_ECC_P384,
    #     "keyfile": CLIENT_KEY_ECC_P384,
    #     "ciphers": "ECDHE-ECDSA-CHACHA20-POLY1305"
    # },

    # # EdDSA Ed25519
    "EdDSA_AES128GCM_SHA256": {
        "host": MQTT_HOST,
        "port": MQTT_PORT_MTLS,
        "tls": True,
        "ca_certs": CA_CERT_EDDSA_ED25519,
        "certfile": CLIENT_CERT_EDDSA_ED25519,
        "keyfile": CLIENT_KEY_EDDSA_ED25519,
        "ciphers": "ECDHE-ECDSA-AES128-GCM-SHA256"
    },
    # "EdDSA_AES256GCM_SHA384": {
    #     "host": MQTT_HOST,
    #     "port": MQTT_PORT_MTLS,
    #     "tls": True,
    #     "ca_certs": CA_CERT_EDDSA_ED25519,
    #     "certfile": CLIENT_CERT_EDDSA_ED25519,
    #     "keyfile": CLIENT_KEY_EDDSA_ED25519,
    #     "ciphers": "ECDHE-ECDSA-AES256-GCM-SHA384"
    # },
    # "EdDSA_CHACHA20_POLY1305": {
    #     "host": MQTT_HOST,
    #     "port": MQTT_PORT_MTLS,
    #     "tls": True,
    #     "ca_certs": CA_CERT_EDDSA_ED25519,
    #     "certfile": CLIENT_CERT_EDDSA_ED25519,
    #     "keyfile": CLIENT_KEY_EDDSA_ED25519,
    #     "ciphers": "ECDHE-ECDSA-CHACHA20-POLY1305"
    # },

    # # RSA 2048
    # "RSA_2048_ECDHE-RSA-AES256-GCM-SHA384": {
    #     "host": MQTT_HOST,
    #     "port": MQTT_PORT_MTLS,
    #     "tls": True,
    #     "ca_certs": CA_CERT_RSA_2048,
    #     "certfile": CLIENT_CERT_RSA_2048,
    #     "keyfile": CLIENT_KEY_RSA_2048,
    #     "ciphers": "ECDHE-RSA-AES256-GCM-SHA384"
    # },
    # "RSA_2048_ECDHE-RSA-AES128-GCM-SHA256": {
    #     "host": MQTT_HOST,
    #     "port": MQTT_PORT_MTLS,
    #     "tls": True,
    #     "ca_certs": CA_CERT_RSA_2048,
    #     "certfile": CLIENT_CERT_RSA_2048,
    #     "keyfile": CLIENT_KEY_RSA_2048,
    #     "ciphers": "ECDHE-RSA-AES128-GCM-SHA256"
    # },
    # "RSA_2048_ECDHE-RSA-CHACHA20-POLY1305": {
    #     "host": MQTT_HOST,
    #     "port": MQTT_PORT_MTLS,
    #     "tls": True,
    #     "ca_certs": CA_CERT_RSA_2048,
    #     "certfile": CLIENT_CERT_RSA_2048,
    #     "keyfile": CLIENT_KEY_RSA_2048,
    #     "ciphers": "ECDHE-RSA-CHACHA20-POLY1305"
    # },

    # # Access Token
    # "Token_Plain": {
    #     "host": MQTT_HOST,
    #     "port": MQTT_PORT_PLAIN,
    #     "tls": False,
    #     "username": ACCESS_TOKEN,
    #     "password": None
    # },

    # # Basic Auth
    # "Basic_Plain": {
    #     "host": MQTT_HOST,
    #     "port": MQTT_PORT_PLAIN,
    #     "tls": False,
    #     "clientId": "mqtt",
    #     "username": BASIC_USER,
    #     "password": BASIC_PASS
    # },
}