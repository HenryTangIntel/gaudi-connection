#!/usr/bin/env python3
"""
Minimal script to test vendor ID retrieval
"""
import os

def get_vendor_id(bus_id):
    """Get vendor ID from /sys filesystem"""
    if not bus_id:
        return None
    
    pci_path = f"/sys/bus/pci/devices/{bus_id}"
    if not os.path.exists(pci_path):
        print(f"Path {pci_path} does not exist")
        return None
    
    vendor_file = os.path.join(pci_path, 'vendor')
    if os.path.exists(vendor_file):
        try:
            with open(vendor_file, 'r') as f:
                vendor_id = f.read().strip().lower()
                if vendor_id.startswith('0x'):
                    vendor_id = vendor_id[2:]
            return vendor_id
        except Exception as e:
            print(f"Error reading vendor file: {e}")
    else:
        print(f"Vendor file {vendor_file} does not exist")
    
    return None

def main():
    # List some PCI devices
    try:
        pci_devices = os.listdir('/sys/bus/pci/devices')
        print(f"Found {len(pci_devices)} PCI devices")
        
        # Check the first 5 devices
        for i, bus_id in enumerate(pci_devices[:5]):
            vendor_id = get_vendor_id(bus_id)
            print(f"Device {i}: {bus_id}")
            print(f"  Vendor ID: {vendor_id}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
