#!/usr/bin/env python3
"""
InfiniBand device scanner
This script scans the /sys filesystem to find InfiniBand devices and their active ports.
"""

import os
import glob
import json
from typing import Dict, List, Tuple, Any, Optional

class InfinibandDevices:
    """
    Class for detecting and managing InfiniBand devices.
    Provides methods to scan the system for InfiniBand devices and retrieve information about them.
    """
    
    def __init__(self):
        """Initialize the InfinibandDevices class."""
        # Cache for device information
        self._devices_cache = None
        # Base path for InfiniBand devices
        self.ib_path = "/sys/class/infiniband"
        # Gaudi vendor ID
        self.gaudi_vendor_id = '1da3'
    
    def get_infiniband_devices(self, include_details: bool = False, use_cache: bool = False) -> Dict[str, Any]:
        """
        Scan the /sys filesystem to find all InfiniBand devices and detect active ports.
        
        Args:
            include_details: If True, return detailed information about each port, otherwise just return port numbers
            use_cache: If True, use cached device information if available
        
        Returns:
            Dict: Dictionary with "gaudi" and "other" categories, each containing a list of devices.
            Each device entry contains device name, PCI bus ID, and port information.
        """
        # Return cached devices if available and cache usage is enabled
        if use_cache and self._devices_cache is not None:
            return self._devices_cache
            
        if not os.path.exists(self.ib_path):
            print(f"InfiniBand path {self.ib_path} does not exist")
            return {"gaudi": [], "other": []}
    
        gaudi_devices = []
        other_devices = []
    
        for device_path in glob.glob(os.path.join(self.ib_path, "*")):
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
                vendor_id = self._get_vendor_id(pci_path)
            is_gaudi = vendor_id == self.gaudi_vendor_id
    
            # Gather port info
            ports = self._gather_port_info(device_path, include_details)
    
            device_info = {
                "name": device_name,
                "pci_bus_id": pci_bus_id,
                "vendor_id": vendor_id,
                "ports": ports
            }
            
            if include_details:
                self._add_device_details(device_path, device_info)
    
            if is_gaudi:
                gaudi_devices.append(device_info)
            else:
                other_devices.append(device_info)
                
        result = {"gaudi": gaudi_devices, "other": other_devices}
        print(f"Found {len(gaudi_devices)} Gaudi devices and {len(other_devices)} other devices")
        
        # Update cache
        if use_cache:
            self._devices_cache = result
            
        return result
    
    def check_port_status(self, device_bus_id: str, port_num: int, ib_devices: Optional[Dict[str, Dict[str, Any]]] = None) -> Tuple[bool, str]:
        """
        Check if an InfiniBand port is active.
        
        Args:
            device_bus_id: PCI bus ID of the device
            port_num: Port number to check
            ib_devices: Dictionary of InfiniBand devices with port information. If None, will get devices
            
        Returns:
            Tuple of (is_active, status_message)
        """
        if ib_devices is None:
            # Get all IB devices, flattening the gaudi and other categories into a single dict by bus ID
            all_devices = self.get_infiniband_devices(include_details=True)
            ib_devices = {}
            
            # Process Gaudi devices
            for device in all_devices.get("gaudi", []):
                if "pci_bus_id" in device and device["pci_bus_id"] != "Unknown":
                    ib_devices[device["pci_bus_id"]] = device
                    
            # Process other devices
            for device in all_devices.get("other", []):
                if "pci_bus_id" in device and device["pci_bus_id"] != "Unknown":
                    ib_devices[device["pci_bus_id"]] = device
        
        if not ib_devices or device_bus_id not in ib_devices:
            return False, f"Device with bus ID {device_bus_id} not found in InfiniBand devices"
        
        device_info = ib_devices[device_bus_id]
        
        # Handle list of ports format
        if "ports" in device_info:  
            # Find the port with the matching port number
            for port_info in device_info["ports"]:
                if port_info.get("port_num") == port_num:
                    is_active = port_info.get("is_active", False)
                    state = port_info.get("state", "Unknown")
                    
                    if is_active:
                        return True, f"Port {port_num} is ACTIVE with state: {state}"
                    else:
                        return False, f"Port {port_num} is INACTIVE with state: {state}"
                        
            return False, f"Port {port_num} not found on device {device_bus_id}"
        else:  # Basic information (legacy format)
            active_ports = device_info.get("active_ports", [])
            if port_num in active_ports:
                return True, f"Port {port_num} is in the list of active ports"
            else:
                return False, f"Port {port_num} is not in the list of active ports: {active_ports}"
    
    def _get_vendor_id(self, pci_path: str) -> Optional[str]:
        """
        Extract the vendor ID from a PCI device path.
        
        Args:
            pci_path: The path to the PCI device
            
        Returns:
            str: The vendor ID if found, None otherwise
        """
        current_path = pci_path
        for _ in range(10):  # limit to 10 parent traversals
            vendor_file = os.path.join(current_path, 'vendor')
            if os.path.exists(vendor_file):
                try:
                    with open(vendor_file, 'r') as f:
                        vendor_id = f.read().strip().lower()
                        if vendor_id.startswith('0x'):
                            vendor_id = vendor_id[2:]
                    return vendor_id
                except Exception:
                    pass
            parent = os.path.dirname(current_path)
            if parent == current_path:
                break
            current_path = parent
        return None
        
    def _gather_port_info(self, device_path: str, include_details: bool) -> List[Dict[str, Any]]:
        """
        Gather information about ports for an InfiniBand device.
        
        Args:
            device_path: The path to the device
            include_details: Whether to include detailed information
            
        Returns:
            List[Dict[str, Any]]: List of port information dictionaries
        """
        ports = []
        port_paths = glob.glob(os.path.join(device_path, "ports", "*"))
        for port_path in port_paths:
            port_num = int(os.path.basename(port_path))
            state = "Unknown"
            is_active = False
            
            # Get port state
            state_path = os.path.join(port_path, "state")
            if os.path.exists(state_path):
                with open(state_path, 'r') as f:
                    state = f.read().strip()
                    if "ACTIVE" in state:
                        is_active = True
                        
            # Get link layer
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
                self._add_port_details(port_path, port_info)
                
            ports.append(port_info)
            
        return ports
    
    def _add_port_details(self, port_path: str, port_info: Dict[str, Any]):
        """
        Add detailed information about a port to the port_info dictionary.
        
        Args:
            port_path: The path to the port
            port_info: The dictionary to add information to
        """
        # Get GID information
        gid_path = os.path.join(port_path, "gids", "0")
        if os.path.exists(gid_path):
            with open(gid_path, 'r') as f:
                port_info["gid"] = f.read().strip()
                
        # Get LID information
        lid_path = os.path.join(port_path, "lid")
        if os.path.exists(lid_path):
            with open(lid_path, 'r') as f:
                port_info["lid"] = f.read().strip()
                
        # Get rate information
        rate_path = os.path.join(port_path, "rate")
        if os.path.exists(rate_path):
            with open(rate_path, 'r') as f:
                port_info["rate"] = f.read().strip()
    
    def _add_device_details(self, device_path: str, device_info: Dict[str, Any]):
        """
        Add detailed information about a device to the device_info dictionary.
        
        Args:
            device_path: The path to the device
            device_info: The dictionary to add information to
        """
        # Get node GUID
        node_guid_path = os.path.join(device_path, "node_guid")
        if os.path.exists(node_guid_path):
            with open(node_guid_path, 'r') as f:
                device_info["node_guid"] = f.read().strip()
                
        # Get device type
        device_type_path = os.path.join(device_path, "node_type")
        if os.path.exists(device_type_path):
            with open(device_type_path, 'r') as f:
                device_info["type"] = f.read().strip()
    
    def clear_cache(self):
        """
        Clear the device information cache.
        Call this method when you want to ensure fresh device data.
        """
        self._devices_cache = None
        
    def print_infiniband_info(self, detailed: bool = False):
        """
        Print information about discovered InfiniBand devices and their active ports.
        
        Args:
            detailed: If True, print detailed information about each port
        """
        devices = self.get_infiniband_devices(include_details=detailed)
        
        if not devices["gaudi"] and not devices["other"]:
            print("No InfiniBand devices found")
            return
        
        print("InfiniBand Devices:")
        print("===================")
        
        total_devices = len(devices["gaudi"]) + len(devices["other"])
        total_active_ports = 0
        
        # Print Gaudi devices first, then other devices
        for device_category in ["gaudi", "other"]:
            for device_info in devices[device_category]:
                device_name = device_info.get("name", "Unknown")
                pci_bus_id = device_info.get("pci_bus_id", "Unknown")
                
                print(f"Device: {device_name}")
                print(f"  PCI Bus ID: {pci_bus_id}")
                print(f"  Category: {'Gaudi' if device_category == 'gaudi' else 'Other'}")
                
                if detailed:
                    if "node_guid" in device_info:
                        print(f"  Node GUID: {device_info['node_guid']}")
                    if "type" in device_info:
                        print(f"  Node Type: {device_info['type']}")
                    
                    print("  Ports:")
                    ports = device_info.get("ports", [])
                    for port_info in sorted(ports, key=lambda p: p["port_num"]):
                        port_num = port_info.get("port_num", "Unknown")
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
                    active_ports = [p["port_num"] for p in device_info.get("ports", []) if p.get("is_active", False)]
                    if active_ports:
                        print(f"  Active ports: {', '.join(map(str, active_ports))}")
                        total_active_ports += len(active_ports)
                    else:
                        print("  No active ports")
                
                print()
        
        print("\nTotal devices found:", total_devices)
        print("Total active ports:", total_active_ports)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="InfiniBand device scanner")
    parser.add_argument("-d", "--detailed", action="store_true", help="Show detailed port information")
    parser.add_argument("-j", "--json", action="store_true", help="Output in JSON format")
    args = parser.parse_args()
    
    # Create an instance of InfinibandDevices
    infiniband_devices = InfinibandDevices()
    
    if args.json:
        devices = infiniband_devices.get_infiniband_devices(include_details=args.detailed)
        print(json.dumps(devices, indent=2))
    else:
        infiniband_devices.print_infiniband_info(detailed=args.detailed)
