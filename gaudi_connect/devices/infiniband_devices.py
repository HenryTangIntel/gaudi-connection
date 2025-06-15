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
    if not os.path.exists(ib_path):
        print(f"InfiniBand path {ib_path} does not exist")
        return {"gaudi": [], "other": []}

    gaudi_devices = []
    other_devices = []

    for device_path in glob.glob(os.path.join(ib_path, "*")):
        device_name = os.path.basename(device_path)
        # Extract PCI bus ID from the device path (symlink) - use the LAST one in the path
        pci_bus_id = "Unknown"
        pci_path = None
        try:
            real_path = os.path.realpath(device_path)
            pci_parts = [p for p in real_path.split('/') if p.startswith('0000:')]
            if pci_parts:
                pci_bus_id = pci_parts[-1]  # Use the last PCI bus ID
                idx = real_path.rfind(pci_bus_id)
                if idx != -1:
                    pci_path = real_path[:idx + len(pci_bus_id)]
        except Exception:
            pass

        # Identify vendor by walking up the directory tree to find a vendor file
        vendor_id = None
        if pci_path:
            current_path = pci_path
            for _ in range(10):  # limit to 10 parent traversals
                vendor_file = os.path.join(current_path, 'vendor')
                if os.path.exists(vendor_file):
                    try:
                        with open(vendor_file, 'r') as f:
                            vendor_id = f.read().strip().lower()
                            if vendor_id.startswith('0x'):
                                vendor_id = vendor_id[2:]
                        break
                    except Exception:
                        pass
                parent = os.path.dirname(current_path)
                if parent == current_path:
                    break
                current_path = parent
        is_gaudi = vendor_id == '1da3'

        # Gather port info
        ports = []
        port_paths = glob.glob(os.path.join(device_path, "ports", "*"))
        for port_path in port_paths:
            port_num = int(os.path.basename(port_path))
            state = "Unknown"
            is_active = False
            state_path = os.path.join(port_path, "state")
            if os.path.exists(state_path):
                with open(state_path, 'r') as f:
                    state = f.read().strip()
                    if "ACTIVE" in state:
                        is_active = True
            link_layer = "Unknown"
            link_layer_path = os.path.join(port_path, "link_layer")
            if os.path.exists(link_layer_path):
                with open(link_layer_path, 'r') as f:
                    link_layer = f.read().strip()
            port_info = {
                "port_num": port_num,
                "state": state,
                "is_active": is_active,
                "link_layer": link_layer
            }
            # Optionally add more details
            if include_details:
                gid_path = os.path.join(port_path, "gids", "0")
                if os.path.exists(gid_path):
                    with open(gid_path, 'r') as f:
                        port_info["gid"] = f.read().strip()
                lid_path = os.path.join(port_path, "lid")
                if os.path.exists(lid_path):
                    with open(lid_path, 'r') as f:
                        port_info["lid"] = f.read().strip()
                rate_path = os.path.join(port_path, "rate")
                if os.path.exists(rate_path):
                    with open(rate_path, 'r') as f:
                        port_info["rate"] = f.read().strip()
            ports.append(port_info)

        device_info = {
            "name": device_name,
            "pci_bus_id": pci_bus_id,
            "ports": ports
        }
        if include_details:
            node_guid_path = os.path.join(device_path, "node_guid")
            if os.path.exists(node_guid_path):
                with open(node_guid_path, 'r') as f:
                    device_info["node_guid"] = f.read().strip()
            device_type_path = os.path.join(device_path, "node_type")
            if os.path.exists(device_type_path):
                with open(device_type_path, 'r') as f:
                    device_info["type"] = f.read().strip()

        if is_gaudi:
            gaudi_devices.append(device_info)
        else:
            other_devices.append(device_info)
    print(f"Found {len(gaudi_devices)} Gaudi devices and {len(other_devices)} other devices")
    return {"gaudi": gaudi_devices, "other": other_devices}

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
