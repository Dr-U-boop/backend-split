
import sys
import os

try:
    import scipy.io
except ImportError:
    print("scipy is not installed. Please install it using 'pip install scipy'")
    sys.exit(1)

try:
    mat_data = scipy.io.loadmat('Multibolus.mat')
    print("Keys in Multibolus.mat:", mat_data.keys())
    
    for key in mat_data:
        if key.startswith('__'):
            continue
        val = mat_data[key]
        print(f"\nKey: {key}")
        print(f"Type: {type(val)}")
        if hasattr(val, 'shape'):
            print(f"Shape: {val.shape}")
        # Print a small sample if it's an array
        if hasattr(val, 'flat'):
            print(f"Sample data (first 5 elements): {val.flat[:5]}")
            
except Exception as e:
    print(f"Error loading .mat file: {e}")
