#!/usr/bin/env python3
"""Test if thermostat service can access Claude CLI"""
import subprocess
import os

print("Testing Claude CLI access for thermostat service")
print("="*50)

# Test 1: Check if claude path exists
claude_path = '/home/jason/.nvm/versions/node/v18.20.8/bin/claude'
print(f"\n1. Checking if Claude exists at: {claude_path}")
if os.path.exists(claude_path):
    print("✓ Claude binary found")
else:
    print("✗ Claude binary NOT found")

# Test 2: Try to run claude
print("\n2. Testing Claude execution...")
try:
    result = subprocess.run([claude_path, '--version'], capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        print("✓ Claude executed successfully")
        print(f"  Output: {result.stdout.strip()}")
    else:
        print("✗ Claude execution failed")
        print(f"  Error: {result.stderr}")
except Exception as e:
    print(f"✗ Exception: {e}")

# Test 3: Check environment
print("\n3. Environment info:")
print(f"  Current user: {os.environ.get('USER', 'unknown')}")
print(f"  Home directory: {os.environ.get('HOME', 'unknown')}")
print(f"  PATH: {os.environ.get('PATH', 'not set')}")

# Test 4: Try vision integration
print("\n4. Testing vision integration module...")
try:
    from vision_integration import get_claude_temperature
    print("✓ Vision integration module loaded")
    
    # Try to get a temperature (will use cached if recent)
    test_image = "/home/jason/smart-thermostat/experimental/current_display_20250628_192003.jpg"
    if os.path.exists(test_image):
        temp = get_claude_temperature(test_image)
        print(f"✓ Temperature reading: {temp}°F")
    else:
        print("  No test image available")
except Exception as e:
    print(f"✗ Vision integration error: {e}")

print("\n" + "="*50)
print("Run this script to diagnose Claude access issues")
print("You can also run it via the service to test:")
print("  sudo -u jason python3 /home/jason/smart-thermostat/test_claude_access.py")