#!/usr/bin/env python3
"""
InfiniBand device scanner
This script scans the /sys filesystem to find InfiniBand devices and their active ports.
"""

import os
import glob
from typing import Dict, List, Tuple, Any

def get_infiniband_devices(include_details: bool = False) -> Dict[str, Any]:
    """
    Scan the /sys filesystem to find all InfiniBand devices and detect active ports.
    
    Args:
        include_details: If True, return detailed information about each port, otherwise just return port numbers
    
    Returns:
        Dict: Dictionary with PCI bus IDs as keys and device information as values.
        Each value contains the device name and port information.
        If include_details is False, port information is a list of active port numbers.
        If include_details is True, port information is a dict with detailed port data.
    """
    # Base path for InfiniBand devices
    ib_path = "/sys/class/infiniband"
    
    # Check if the path exists
    if not os.path.exists(ib_path):
        print(f"InfiniBand path {ib_path} does not exist")
        return {}
    
    result = {}
    
    # Find all InfiniBand devices
    for device_path in glob.glob(os.path.join(ib_path, "*")):
        device_name = os.path.basename(device_path)
        
        # Extract PCI bus ID from the device path (symlink) for both detailed and simple modes
        pci_bus_id = "Unknown"
        try:
            real_path = os.path.realpath(device_path)
            # The PCI path is typically in format: .../devices/pci0000:xx/0000:xx:xx.x/...
            # We want to extract the 0000:xx:xx.x part which is the PCI bus ID
            pci_parts = [p for p in real_path.split('/') if p.startswith('0000:')]
            if pci_parts:
                pci_bus_id = pci_parts[0]
        except Exception as e:
            # In case there's any issue resolving the symlink or parsing the path
            pass
            
        if include_details:
            device_info = {}
            # Get device node GUID if available
            node_guid_path = os.path.join(device_path, "node_guid")
            if os.path.exists(node_guid_path):
                with open(node_guid_path, 'r') as f:
                    device_info["node_guid"] = f.read().strip()
            
            # Get device type if available
            device_type_path = os.path.join(device_path, "node_type")
            if os.path.exists(device_type_path):
                with open(device_type_path, 'r') as f:
                    device_info["type"] = f.read().strip()
                    
            # Add PCI bus ID
            device_info["pci_bus_id"] = pci_bus_id
            
            ports_info = {}
        else:
            # For simple mode, store as a dict with pci_bus_id and active_ports
            device_info = {
                "pci_bus_id": pci_bus_id,
                "active_ports": []
            }
        
        # Find all ports for this device
        port_paths = glob.glob(os.path.join(device_path, "ports", "*"))
        
        for port_path in port_paths:
            port_num = int(os.path.basename(port_path))
            is_active = False
            port_info = {} if include_details else None
            
            # Check if the port is active by reading the state file
            state_path = os.path.join(port_path, "state")
            state = "Unknown"
            if os.path.exists(state_path):
                with open(state_path, 'r') as f:
                    state = f.read().strip()
                    # Port states: DOWN, INIT, ARM, ACTIVE
                    if "ACTIVE" in state:
                        is_active = True
            
            if include_details:
                port_info["state"] = state
            
            # Get link layer
            link_layer = "Unknown"
            link_layer_path = os.path.join(port_path, "link_layer")
            if os.path.exists(link_layer_path):
                with open(link_layer_path, 'r') as f:
                    link_layer = f.read().strip()
                    if link_layer != "Unknown" and not is_active:
                        is_active = True
            
            if include_details:
                port_info["link_layer"] = link_layer
                
                # Get port GID
                gid_path = os.path.join(port_path, "gids", "0")
                if os.path.exists(gid_path):
                    with open(gid_path, 'r') as f:
                        port_info["gid"] = f.read().strip()
                
                # Get port LID
                lid_path = os.path.join(port_path, "lid")
                if os.path.exists(lid_path):
                    with open(lid_path, 'r') as f:
                        port_info["lid"] = f.read().strip()
                
                # Get rate
                rate_path = os.path.join(port_path, "rate")
                if os.path.exists(rate_path):
                    with open(rate_path, 'r') as f:
                        port_info["rate"] = f.read().strip()
                
                # Record if port is active
                port_info["is_active"] = is_active
                ports_info[port_num] = port_info
            elif is_active:
                device_info["active_ports"].append(port_num)
        
        if include_details:
            device_info["ports"] = ports_info
            device_info["name"] = device_name  # Include the device name as part of the information
            result[pci_bus_id] = device_info
        else:
            # Sort the active ports before returning
            device_info["active_ports"] = sorted(device_info["active_ports"])
            device_info["name"] = device_name  # Include the device name as part of the information
            result[pci_bus_id] = device_info
    
    return result

def print_infiniband_info(detailed: bool = False):
    """
    Print information about discovered InfiniBand devices and their active ports.
    
    Args:
        detailed: If True, print detailed information about each port
    """
    devices = get_infiniband_devices(include_details=detailed)
    
    if not devices:
        print("No InfiniBand devices found")
        return
    
    print("InfiniBand Devices:")
    print("===================")
    
    total_active_ports = 0
    
    for bus_id, info in sorted(devices.items()):
        device_name = info.get("name", "Unknown")
        print(f"Device: {device_name}")
        print(f"  PCI Bus ID: {bus_id}")
        
        if detailed:
            if "node_guid" in info:
                print(f"  Node GUID: {info['node_guid']}")
            if "type" in info:
                print(f"  Node Type: {info['type']}")
            
            print("  Ports:")
            for port_num, port_info in sorted(info["ports"].items()):
                is_active = port_info.get("is_active", False)
                if is_active:
                    total_active_ports += 1
                    
                state = port_info.get("state", "Unknown")
                link_layer = port_info.get("link_layer", "Unknown")
                rate = port_info.get("rate", "Unknown")
                
                status = "ACTIVE" if is_active else "INACTIVE"
                print(f"    Port {port_num}: {status}, State: {state}, Link: {link_layer}, Rate: {rate}")
                
                if "lid" in port_info:
                    print(f"      LID: {port_info['lid']}")
                if "gid" in port_info and port_info["gid"] != "0000:0000:0000:0000:0000:0000:0000:0000":
                    print(f"      GID: {port_info['gid']}")
        else:
            active_ports = info.get("active_ports", [])
            if active_ports:
                print(f"  Active ports: {', '.join(map(str, active_ports))}")
                total_active_ports += len(active_ports)
            else:
                print("  No active ports")
    
    print("\nTotal devices found:", len(devices))
    print("Total active ports:", total_active_ports)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="InfiniBand device scanner")
    parser.add_argument("-d", "--detailed", action="store_true", help="Show detailed port information")
    parser.add_argument("-j", "--json", action="store_true", help="Output in JSON format")
    args = parser.parse_args()
    
    if args.json:
        import json
        devices = get_infiniband_devices(include_details=args.detailed)
        print(json.dumps(devices, indent=2))
    else:
        print_infiniband_info(detailed=args.detailed)
