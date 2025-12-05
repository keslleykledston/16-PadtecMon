import asyncio
import json
import urllib.request
import urllib.error

# Configuration
EXTERNAL_IP = "108.165.140.144"
PORT = "8181"
BASE_URL = f"http://{EXTERNAL_IP}:{PORT}/nms-api"
CURRENT_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJwYWR0ZWNtb24iLCJpYXQiOjE3NjQ4OTYwMjN9.v0yRXGDXBLeWTfJPhVIEQhpyYvSCgCkHDTE4xLGVA_M"

def test_token():
    print(f"--- Testing Current Token against {BASE_URL} ---")
    url = f"{BASE_URL}/v1/inventory/state"
    headers = {
        "Authorization": f"Token {CURRENT_TOKEN}",
        "Content-Type": "application/json"
    }
    
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            print(f"Status: {response.status}")
            if response.status == 200:
                print("SUCCESS: Current token is valid!")
                data = json.loads(response.read().decode())
                print(f"Data received: {len(data)} items")
            else:
                print(f"FAILED: {response.status}")
    except urllib.error.HTTPError as e:
        print(f"FAILED: {e.code} - {e.reason}")
        print(e.read().decode())
    except Exception as e:
        print(f"ERROR testing token: {e}")

if __name__ == "__main__":
    test_token()
