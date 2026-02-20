import base64
import sys

token = "PKDRGGN4ILLYPNMPB4AQFU24X5"
print("Token:", token)
try:
    decoded = base64.b64decode(token)
    print("Decoded:", decoded)
except Exception as e:
    print("Not base64")
    # maybe url safe
    try:
        decoded = base64.urlsafe_b64decode(token + '=' * (4 - len(token) % 4))
        print("URL safe decoded:", decoded)
    except Exception as e2:
        print("Also not URL safe")
        pass

# Check if token contains underscore or dot
if '_' in token:
    parts = token.split('_')
    print("Parts by underscore:", parts)
if '.' in token:
    parts = token.split('.')
    print("Parts by dot:", parts)