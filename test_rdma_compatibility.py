#!/usr/bin/env python3
"""
Script to test RDMA protocol compatibility between devices
"""

from gaudi_connect.devices.InfinibandDevices import InfinibandDevices

def main():
    # Create an InfinibandDevices instance
    ib_devices = InfinibandDevices()
    
    # Get all InfiniBand devices with details
    devices = ib_devices.get_infiniband_devices(include_details=True)
    
    # Get a flattened map of devices by bus ID
    device_map = {}
    
    # Process Gaudi devices
    for device in devices.get("gaudi", []):
        if "pci_bus_id" in device and device["pci_bus_id"] != "Unknown":
            device_map[device["pci_bus_id"]] = device
    
    # Process other devices
    for device in devices.get("other", []):
        if "pci_bus_id" in device and device["pci_bus_id"] != "Unknown":
            device_map[device["pci_bus_id"]] = device
    
    # Print device information with RDMA protocol version
    print("Device information:")
    print("==================")
    for bus_id, device in device_map.items():
        name = device.get("name", "Unknown")
        rdma_version = device.get("rdma_protocol_version", "unknown")
        print(f"Device {name} (Bus ID: {bus_id}), RDMA Protocol: {rdma_version}")
    print()
    
    # Check compatibility between all pairs of devices
    print("Compatibility matrix:")
    print("====================")
    
    # Get list of bus IDs
    bus_ids = list(device_map.keys())
    
    # Create a matrix header
    header = "         |"
    for bus_id in bus_ids[:5]:  # Just show first 5 devices for compactness
        header += f" {device_map[bus_id]['name']:7} |"
    print(header)
    
    for src_id in bus_ids[:5]:  # Just show first 5 devices for compactness
        row = f" {device_map[src_id]['name']:7} |"
        for dst_id in bus_ids[:5]:  # Just show first 5 devices for compactness
            compatible, message = ib_devices.check_rdma_compatibility(src_id, dst_id)
            status = "   ✓   " if compatible else "   ✗   "
            row += f" {status} |"
        print(row)
    
    # Check specific device pairs with detailed messages
    print("\nSpecific compatibility checks:")
    print("============================")
    
    # If we have at least 2 devices, check compatibility between first two
    if len(bus_ids) >= 2:
        src_id, dst_id = bus_ids[0], bus_ids[1]
        src_name = device_map[src_id]['name']
        dst_name = device_map[dst_id]['name']
        
        compatible, message = ib_devices.check_rdma_compatibility(src_id, dst_id)
        print(f"Compatibility between {src_name} and {dst_name}:")
        print(f"  Result: {'Compatible' if compatible else 'Incompatible'}")
        print(f"  Message: {message}")
    
    # If we have a hbl_ and mlx_ device, check between them
    hbl_ids = [bus_id for bus_id, dev in device_map.items() if dev['name'].startswith('hbl_')]
    mlx_ids = [bus_id for bus_id, dev in device_map.items() if dev['name'].startswith('mlx')]
    
    if hbl_ids and mlx_ids:
        src_id, dst_id = hbl_ids[0], mlx_ids[0]
        src_name = device_map[src_id]['name']
        dst_name = device_map[dst_id]['name']
        
        compatible, message = ib_devices.check_rdma_compatibility(src_id, dst_id)
        print(f"\nCompatibility between {src_name} and {dst_name}:")
        print(f"  Result: {'Compatible' if compatible else 'Incompatible'}")
        print(f"  Message: {message}")

if __name__ == "__main__":
    main()
