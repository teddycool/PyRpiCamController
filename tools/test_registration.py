#!/usr/bin/env python3
"""
Test the device registration system with sample data
"""

import subprocess
import sys

def test_registration():
    """Test different registration modes"""
    
    print("🧪 Testing PyRpiCamController Device Registration")
    print("=" * 50)
    
    # Test 1: Single device registration
    print("\n1️⃣ Testing single device registration:")
    try:
        result = subprocess.run([
            sys.executable, "register_device.py",
            "--cpu-id", "b827eb123456789a",
            "--name", "Test Single Camera",
            "--location", "Test Location",
            "--update-group", "development"
        ], capture_output=True, text=True, timeout=30)
        
        print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        print("Return code:", result.returncode)
    except subprocess.TimeoutExpired:
        print("❌ Test timed out")
    except Exception as e:
        print(f"❌ Test error: {e}")
    
    # Test 2: Batch registration from command line
    print("\n2️⃣ Testing batch registration from command line:")
    try:
        result = subprocess.run([
            sys.executable, "register_device.py", 
            "--cpu-ids", "11111111aaaaaaaa,22222222bbbbbbbb,33333333cccccccc",
            "--update-group", "development"
        ], capture_output=True, text=True, timeout=30)
        
        print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        print("Return code:", result.returncode)
    except subprocess.TimeoutExpired:
        print("❌ Test timed out")
    except Exception as e:
        print(f"❌ Test error: {e}")
    
    # Test 3: Batch registration from file
    print("\n3️⃣ Testing batch registration from file:")
    try:
        result = subprocess.run([
            sys.executable, "register_device.py",
            "--file", "sample_devices.json",
            "--test"  # Use development update group
        ], capture_output=True, text=True, timeout=60)
        
        print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        print("Return code:", result.returncode)
    except subprocess.TimeoutExpired:
        print("❌ Test timed out")
    except Exception as e:
        print(f"❌ Test error: {e}")
    
    print("\n🏁 Testing completed!")

if __name__ == "__main__":
    test_registration()