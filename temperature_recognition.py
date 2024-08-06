import cv2
import pytesseract

# Set the URL of the video stream
stream_url = 'http://10.0.0.54:5000/video_feed'

# Initialize video capture with the stream URL
cap = cv2.VideoCapture(stream_url)

# Check if the stream opened successfully
if not cap.isOpened():
    print("Error: Unable to open video stream")
    exit()

while True:
    # Capture frame-by-frame
    ret, frame = cap.read()

    # If frame is read correctly, ret is True
    if not ret:
        print("Failed to grab frame")
        break

    # Convert the frame to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Apply thresholding to preprocess the image for better OCR results
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)

    # Use Tesseract to do OCR on the frame
    text = pytesseract.image_to_string(thresh, config='--psm 6')

    # Print extracted text
    print("Detected text:", text)

    # Display the resulting frame (optional)
    cv2.imshow('Frame', frame)

    # Press 'q' to exit the loop
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# When everything is done, release the capture
cap.release()
cv2.destroyAllWindows()
