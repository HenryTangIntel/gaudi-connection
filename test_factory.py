#!/usr/bin/env python3
"""
Gaudi Device Factory Test Script

This script demonstrates how to use the GaudiDeviceFactory class.
"""

from gaudi_connect.devices.GaudiDeviceFactory import GaudiDeviceFactory

def main():
    """Main demonstration function."""
    print("Creating GaudiDeviceFactory instance...")
    factory = GaudiDeviceFactory()
    
    # Get all devices
    print("\nGetting all Gaudi devices...")
    devices = factory.get_all_devices()
    print(f"Found {len(devices)} devices.")
    
    # Print device summary
    print("\nDevice Summary:")
    factory.print_device_summary()
    
    # Get devices by different indexes
    print("\nDevices by module ID:")
    devices_by_module = factory.get_devices_by_module_id()
    for module_id, device in sorted(devices_by_module.items()):
        print(f"Module {module_id}: {device.bus_id} (Index {device.index})")
    
    print("\nDevices by index:")
    devices_by_index = factory.get_devices_by_index()
    for index, device in sorted(devices_by_index.items()):
        print(f"Index {index}: {device.bus_id} (Module {device.module_id})")
    
    # Get active ports
    print("\nActive ports by device:")
    active_ports = factory.get_active_ports()
    for bus_id, ports in sorted(active_ports.items()):
        if ports:
            print(f"{bus_id}: {', '.join(map(str, sorted(ports)))}")
        else:
            print(f"{bus_id}: No active ports")

if __name__ == "__main__":
    main()
