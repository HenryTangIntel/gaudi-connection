#!/usr/bin/env python3
"""
Debug script to analyze InfiniBand port states
"""
import os
import glob

def debug_port_state(device_name):
    """Debug the state of InfiniBand ports for a specific device"""
    device_path = f"/sys/class/infiniband/{device_name}"
    print(f"Device: {device_name}")
    print(f"Device path: {device_path}")
    
    if not os.path.exists(device_path):
        print(f"  Device path does not exist!")
        return
        
    ports_path = os.path.join(device_path, "ports")
    print(f"Ports path: {ports_path}")
    
    if not os.path.exists(ports_path):
        print(f"  Ports path does not exist!")
        return
        
    port_paths = glob.glob(os.path.join(ports_path, "*"))
    print(f"Found {len(port_paths)} ports")
    
    for port_path in port_paths:
        port_num = os.path.basename(port_path)
        print(f"\nPort {port_num}:")
        
        # Check state
        state_path = os.path.join(port_path, "state")
        if os.path.exists(state_path):
            try:
                with open(state_path, 'r') as f:
                    state = f.read().strip()
                print(f"  State: '{state}'")
                # Analyze what determines active status
                if "ACTIVE" in state:
                    print(f"  Would be marked ACTIVE (contains 'ACTIVE')")
                else:
                    print(f"  Would be marked INACTIVE (doesn't contain 'ACTIVE')")
            except Exception as e:
                print(f"  Error reading state: {e}")
        else:
            print(f"  State file does not exist: {state_path}")
            
        # Check link layer
        link_layer_path = os.path.join(port_path, "link_layer")
        if os.path.exists(link_layer_path):
            try:
                with open(link_layer_path, 'r') as f:
                    link_layer = f.read().strip()
                print(f"  Link layer: {link_layer}")
            except Exception as e:
                print(f"  Error reading link_layer: {e}")
        else:
            print(f"  Link layer file does not exist")
            
        # Check phys_state
        phys_state_path = os.path.join(port_path, "phys_state")
        if os.path.exists(phys_state_path):
            try:
                with open(phys_state_path, 'r') as f:
                    phys_state = f.read().strip()
                print(f"  Physical state: {phys_state}")
            except Exception as e:
                print(f"  Error reading phys_state: {e}")
                
        # List all files in the port directory to find additional information
        print("  Available files in port directory:")
        try:
            files = os.listdir(port_path)
            for file in files:
                print(f"    - {file}")
        except Exception as e:
            print(f"  Error listing port directory: {e}")

def main():
    print("Debugging InfiniBand port states")
    
    # List all InfiniBand devices
    ib_path = "/sys/class/infiniband"
    if not os.path.exists(ib_path):
        print(f"InfiniBand path {ib_path} does not exist")
        return
        
    devices = os.listdir(ib_path)
    print(f"Found {len(devices)} InfiniBand devices: {', '.join(devices)}")
    
    # Debug each device
    for device in devices:
        print("\n" + "="*50)
        debug_port_state(device)
        print("="*50)

if __name__ == "__main__":
    main()
