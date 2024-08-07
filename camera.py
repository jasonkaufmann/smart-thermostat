import time
import os
import cv2
from picamera2 import Picamera2
from paramiko import SSHClient, AutoAddPolicy
from scp import SCPClient

# Configuration
remote_host = "10.0.0.213"    # IP address of the target Linux machine
remote_user = "jason"         # Username on the target machine
remote_path = "/home/jason/smart-thermostat/"  # Directory on the target machine
remote_filename = "latest_photo.jpg"  # Filename to use on the remote machine

# Initialize the camera
picam2 = Picamera2()
config = picam2.create_still_configuration(main={"size": (1000, 1000), "format": "RGB888"})  # Max resolution
picam2.configure(config)
picam2.start()

# Function to create an SSH client
def create_ssh_client(server, user, password=None):
    client = SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(AutoAddPolicy())
    client.connect(server, username=user, password=password)
    return client

# Capture and transfer photos
def capture_and_transfer():
    transfer_count = 0  # Initialize transfer counter

    while True:
        # Capture photo
        local_filename = "/tmp/latest_photo.jpg"  # Use a fixed filename

        # Capture the image and save it using OpenCV
        frame = picam2.capture_array()
        cv2.imwrite(local_filename, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))

        # Transfer the photo using SCP
        ssh_client = None
        try:
            ssh_client = create_ssh_client(remote_host, remote_user)
            with SCPClient(ssh_client.get_transport()) as scp:
                # Overwrite the image on the remote machine
                scp.put(local_filename, os.path.join(remote_path, remote_filename))
            transfer_count += 1  # Increment transfer counter
            print(f"Transferred {local_filename} to {remote_host}:{remote_path}{remote_filename}")
            print(f"Transfer count: {transfer_count}")  # Print transfer count
        except Exception as e:
            print(f"Failed to transfer {local_filename}: {e}")
        finally:
            if ssh_client is not None:
                ssh_client.close()
        
        # Wait for 15 seconds before capturing the next photo
        time.sleep(15)

if __name__ == "__main__":
    try:
        capture_and_transfer()
    except KeyboardInterrupt:
        print("Stopping capture.")
    finally:
        picam2.stop()
