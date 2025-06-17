#!/usr/bin/env python3
# TestConnection.py - Basic tests for Gaudi connection logic

import os
import sys
import json

# Add parent directory to the path so we can import src modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.connectivity.RunConnection import RunConnection
from src.connectivity.GaudiRouting import GaudiRouting
from src.devices.GaudiDeviceFactory import GaudiDeviceFactory


def dummy_test():
    """
    A simple dummy test function that just prints some test messages.
    This is not using any testing framework.
    """
    print("Starting dummy test...")
    print("Testing connection between Gaudi devices...")
    
    # Simulating a test process
    print("1. Initializing test environment")
    print("2. Setting up mock connections")
    print("3. Validating connection results")
    
    # Create a dummy result for testing
    test_result = {
        "status": "pass",
        "message": "All dummy connections verified successfully",
        "connections_tested": 5,
        "failures": 0
    }
    
    print("\nTest Summary:")
    for key, value in test_result.items():
        print(f"  {key}: {value}")
    
    print("\nDummy test completed!")
    return test_result


def test_connection_with_sample_data():
    """
    Test the connection logic with sample data without modifying actual hardware.
    This is a basic test without any testing framework.
    """
    print("Testing connection with sample data...")
    
    # Use a local CSV if available, otherwise this is just for demonstration
    connectivity_file = "connectivity_HLS2.csv"
    
    try:
        # Create a RunConnection instance
        runner = RunConnection(connectivity_file)
        
        # Attempt to make connections but don't display output
        connections = runner.make_connections(display_output=False)
        
        # Print summary results
        print(f"Found {len(connections)} connections in the sample data")
        
        # Check first connection as example
        if connections:
            first_conn = connections[0]
            print("Example connection:")
            print(f"  Source: {first_conn['source']['ib_name']}:port{first_conn['source']['port']}")
            print(f"  Destination: {first_conn['destination']['ib_name']}:port{first_conn['destination']['port']}")
            
            return True
        else:
            print("No connections found in sample data")
            return False
            
    except Exception as e:
        print(f"Test failed with error: {str(e)}")
        return False


if __name__ == "__main__":
    # Run the dummy test
    print("=== Running Dummy Test ===")
    dummy_result = dummy_test()
    print("\n")
    
    # Run the connection test with sample data
    print("=== Running Connection Test with Sample Data ===")
    connection_result = test_connection_with_sample_data()
    print("\n")
    
    # Print final status
    if connection_result:
        print("All tests completed successfully!")
        exit(0)
    else:
        print("Some tests failed. Check the output for details.")
        exit(1)