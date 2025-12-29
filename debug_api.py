import requests
import json
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://localhost:5443/api/build"
payload = {
    "description": "Build a task management app",
    "name": "test-app",
    "requirements": []
}

try:
    print(f"Sending POST to {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    response = requests.post(url, json=payload, verify=False, timeout=5)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
except Exception as e:
    print(f"Error: {e}")

# Test with null name just in case
payload_null = {
    "description": "Build a task management app",
    "name": None,
    "requirements": []
}

try:
    print("\nSending POST with null name")
    response = requests.post(url, json=payload_null, verify=False, timeout=5)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
except Exception as e:
    print(f"Error: {e}")
