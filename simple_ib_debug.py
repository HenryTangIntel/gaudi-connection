#!/usr/bin/env python3
"""
Simplified debug script for InfiniBand ports
"""
import os
import subprocess

def main():
    print("Checking InfiniBand devices and ports")
    
    # Use shell commands to check for InfiniBand devices
    print("Devices in /sys/class/infiniband:")
    subprocess.run("ls -la /sys/class/infiniband", shell=True)
    
    # Get list of directories in /sys/class/infiniband
    if os.path.exists("/sys/class/infiniband"):
        devices = os.listdir("/sys/class/infiniband")
        for device in devices:
            print(f"\nAnalyzing device: {device}")
            ports_path = f"/sys/class/infiniband/{device}/ports"
            
            # Check if ports directory exists
            if os.path.exists(ports_path):
                print(f"Ports directory exists for {device}")
                # List port directories
                if os.path.exists(ports_path):
                    ports = os.listdir(ports_path)
                    print(f"Ports: {ports}")
                    
                    for port in ports:
                        port_path = f"{ports_path}/{port}"
                        print(f"\nPort {port}:")
                        
                        # Check state file
                        state_path = f"{port_path}/state"
                        if os.path.exists(state_path):
                            with open(state_path, 'r') as f:
                                state = f.read().strip()
                            print(f"  State: {state}")
                            print(f"  'ACTIVE' in state: {'ACTIVE' in state}")
                        else:
                            print(f"  No state file found")
                            
                        # Check physical state
                        phys_path = f"{port_path}/phys_state"
                        if os.path.exists(phys_path):
                            with open(phys_path, 'r') as f:
                                phys = f.read().strip()
                            print(f"  Phys state: {phys}")
            else:
                print(f"No ports directory for {device}")
    else:
        print("/sys/class/infiniband directory does not exist")

if __name__ == "__main__":
    main()
