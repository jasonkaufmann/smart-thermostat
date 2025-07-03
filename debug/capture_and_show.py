import requests
from datetime import datetime

# Capture current
response = requests.get('http://blade:5000/video_feed', stream=True, timeout=10)
if response.status_code == 200:
    bytes_data = bytes()
    for chunk in response.iter_content(chunk_size=1024):
        bytes_data += chunk
        a = bytes_data.find(b'\xff\xd8')
        b = bytes_data.find(b'\xff\xd9')
        if a != -1 and b != -1:
            jpg_data = bytes_data[a:b+2]
            filename = f'test_capture_{datetime.now().strftime("%H%M%S")}.jpg'
            with open(filename, 'wb') as f:
                f.write(jpg_data)
            print(f"Saved: {filename}")
            break