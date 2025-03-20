import requests


def test_codelistener_connection(port=8080):
    try:
        response = requests.post(
            f"http://localhost:{port}/execute", json={"code": "print('Hello from Rhino')"}
        )
        print(f"Response: {response.text}")
        return True
    except Exception as e:
        print(f"Error connecting to port {port}: {e}")
        return False


# Try common ports
for port in [8080, 8081, 5000, 8000]:
    print(f"Testing port {port}...")
    if test_codelistener_connection(port):
        print(f"Success! CodeListener is using port {port}")
        break
