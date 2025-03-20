import socket
import json
import tempfile
import os


def test_codelistener_with_file(host="127.0.0.1", port=614):
    """Test CodeListener by creating a temporary file and sending its path."""
    try:
        # Create a temporary Python file
        fd, temp_path = tempfile.mkstemp(suffix=".py")
        try:
            # Write Python code to the file
            with os.fdopen(fd, "w") as f:
                f.write(
                    """
import Rhino
import scriptcontext as sc

# Get Rhino version
version = Rhino.RhinoApp.Version
print("Hello from CodeListener!")
print("Rhino version: ", version)

# Access the active document
doc = sc.doc
if doc is not None:
    print("Active document: ", doc.Name)
else:
    print("No active document")
"""
                )

            # Create JSON message object
            msg_obj = {"filename": temp_path, "run": True, "reset": False, "temp": True}

            # Convert to JSON
            json_msg = json.dumps(msg_obj)

            # Connect to CodeListener
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((host, port))

            # Send the JSON message
            print(f"Sending request to execute file: {temp_path}")
            sock.sendall(json_msg.encode("utf-8"))

            # Receive response
            print("Waiting for response...")
            response = sock.recv(4096).decode("utf-8")
            print(f"Response received: {response}")

            sock.close()
            return True

        finally:
            # Clean up - remove temporary file
            try:
                os.unlink(temp_path)
            except:
                pass

    except Exception as e:
        print(f"Error: {e}")
        return False


# Run the test
if __name__ == "__main__":
    test_codelistener_with_file()
