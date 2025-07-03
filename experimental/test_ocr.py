#!/usr/bin/env python3
"""
Quick test to see if OCR temperature detection is feasible
"""
import os
import sys

def check_dependencies():
    """Check if required packages are installed"""
    missing = []
    
    try:
        import cv2
    except ImportError:
        missing.append("opencv-python")
    
    try:
        import pytesseract
    except ImportError:
        missing.append("pytesseract")
    
    try:
        import PIL
    except ImportError:
        missing.append("Pillow")
    
    try:
        import numpy
    except ImportError:
        missing.append("numpy")
    
    try:
        import requests
    except ImportError:
        missing.append("requests")
    
    if missing:
        print("Missing dependencies:")
        for pkg in missing:
            print(f"  - {pkg}")
        print(f"\nInstall with: pip install {' '.join(missing)}")
        return False
    
    # Check if tesseract binary is installed
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
    except pytesseract.TesseractNotFoundError:
        print("Tesseract OCR is not installed!")
        print("Install with:")
        print("  Ubuntu/Debian: sudo apt-get install tesseract-ocr")
        print("  macOS: brew install tesseract")
        return False
    
    return True

def main():
    print("Checking dependencies...")
    if not check_dependencies():
        sys.exit(1)
    
    print("All dependencies are installed!\n")
    
    # Import modules
    from capture_frame import capture_frame_from_feed, get_latest_image_from_endpoint
    from ocr_temperature import analyze_temperature_display
    
    # Step 1: Capture frames
    print("Step 1: Capturing frames from thermostat...")
    print("-" * 50)
    
    filename1, frame1 = capture_frame_from_feed()
    filename2, frame2 = get_latest_image_from_endpoint()
    
    if filename1 is None and filename2 is None:
        print("Failed to capture any frames. Is the thermostat server running?")
        sys.exit(1)
    
    # Step 2: Analyze captured frames
    print("\nStep 2: Analyzing captured frames with OCR...")
    print("-" * 50)
    
    if filename1:
        analyze_temperature_display(filename1)
    
    if filename2:
        analyze_temperature_display(filename2)
    
    print("\n" + "="*50)
    print("Test complete!")
    print("Check the 'experimental/debug_images' folder for preprocessed images.")
    print("This will help determine which preprocessing method works best for your thermostat display.")

if __name__ == "__main__":
    main()