#!/usr/bin/env python3
"""
Example Usage of GaudiDeviceFactory in Connection Test

This script demonstrates how the GaudiDeviceFactory could be used
in the connection_test_main.py file.
"""

import sys
import os
from gaudi_connect.devices.GaudiDeviceFactory import GaudiDeviceFactory
from gaudi_connect.connectivity.GaudiRouting import GaudiRouting

def main():
    # Parse command-line arguments (simplified for example)
    connectivity_file = "/opt/habanalabs/perf-test/scale_up_tool/internal_data/connectivity_HLS2.csv"
    
    # Check if the connectivity file exists
    if not os.path.exists(connectivity_file):
        print(f"Connectivity file {connectivity_file} does not exist.")
        # Use a local example file if available
        if os.path.exists("examples/connectivity_HLS2.csv"):
            connectivity_file = "examples/connectivity_HLS2.csv"
            print(f"Using local file: {connectivity_file}")
        else:
            print("No connectivity file available. Exiting.")
            return 1
    
    # Create a GaudiDeviceFactory to manage device objects
    factory = GaudiDeviceFactory()
    
    # Get all GaudiDevice objects
    devices = factory.get_all_devices()
    print(f"Found {len(devices)} Gaudi devices.")
    
    if not devices:
        print("No Gaudi devices found or device information not available.")
        return 1
    
    # Get devices by module ID for easier access
    devices_by_module = factory.get_devices_by_module_id()
    
    # Parse connectivity information
    print(f"Parsing connectivity information from {connectivity_file}...")
    router = GaudiRouting(connectivity_file)
    connections = router.parse_connectivity_file()
    
    if not connections:
        print(f"No connectivity information found in {connectivity_file}.")
        return 1
        
    print(f"Found {len(connections)} connections in the connectivity file.")
    
    # Process connections
    valid_connections = 0
    
    for conn in connections:
        src_module_id = conn["source_module_id"]
        dst_module_id = conn["destination_module_id"]
        
        # Skip connections to the same module
        if src_module_id == dst_module_id:
            continue
            
        # Get devices by module ID
        src_device = factory.get_device_by_module_id(src_module_id)
        dst_device = factory.get_device_by_module_id(dst_module_id)
        
        if not src_device:
            print(f"Source device with module ID {src_module_id} not found.")
            continue
            
        if not dst_device:
            print(f"Destination device with module ID {dst_module_id} not found.")
            continue
            
        # Check ports directly from GaudiDevice objects
        src_port = conn["source_port"]
        dst_port = conn["destination_port"]
        
        src_active = src_device.is_port_active(src_port)
        dst_active = dst_device.is_port_active(dst_port)
        
        if not src_active:
            print(f"Source port {src_port} on module {src_module_id} is not active.")
            continue
            
        if not dst_active:
            print(f"Destination port {dst_port} on module {dst_module_id} is not active.")
            continue
            
        # Connection is valid and ports are active
        print(f"Connection from module {src_module_id}:{src_port} to {dst_module_id}:{dst_port} is valid.")
        print(f"  Bus IDs: {src_device.bus_id} -> {dst_device.bus_id}")
        
        # Example info from GaudiDevice
        print(f"  Source: {src_device.bus_id} (Index {src_device.index}, IB: {src_device.ib_name})")
        print(f"  Source port status: {src_device.get_port_status(src_port)}")
        print(f"  Dest: {dst_device.bus_id} (Index {dst_device.index}, IB: {dst_device.ib_name})")
        print(f"  Dest port status: {dst_device.get_port_status(dst_port)}")
        print()
        
        valid_connections += 1
    
    print(f"Total valid connections with active ports: {valid_connections}/{len(connections)}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
