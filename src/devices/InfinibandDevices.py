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
    
    def __init__(self, gaudi_vendor_id: str = '1da3'):
        """Initialize the InfinibandDevices class."""
        # Cache for device information
        self._other_devices = {}  # Other devices
        self._gaudi_devices = {}  # Gaudi devices

        self._gaudi_vendor_id = gaudi_vendor_id.lower()  # Ensure vendor ID is lowercase
        # Base path for InfiniBand devices
        self.ib_path = "/sys/class/infiniband"

    def get_infiniband_devices(self, gaudi_devices):

        if not os.path.exists(self.ib_path):
            print(f"InfiniBand path {self.ib_path} does not exist")
            return {"gaudi": {}, "other": {}}
    
        
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
            is_gaudi = vendor_id == self._gaudi_vendor_id

            # Gather port info
            ports = self._gather_port_info(device_path)
    
            device_info = {
                "ib_name": device_name,
                "pci_bus_id": pci_bus_id,
                "vendor_id": vendor_id,
                "ports": ports
            }
            
            if is_gaudi:
                # If it's a Gaudi device, check if it exists in the GaudiDevices cache
                gaudidevice = gaudi_devices.get_device_by_bus_id(pci_bus_id)
                if gaudidevice:
                    gaudidevice.update_device_info(device_info)
                self._gaudi_devices[pci_bus_id] = gaudidevice
            else:
                from .GaudiDevices import MlxDevice
                self._other_devices[pci_bus_id] = MlxDevice(pci_bus_id, device_info)

        print(f"Found {len(self._gaudi_devices)} Gaudi devices and {len(self._other_devices)} other devices")
        return {"gaudi": self._gaudi_devices, "other": self._other_devices}

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
        
    def _gather_port_info(self, device_path: str) -> List[Dict[str, Any]]:
        """
        Gather information about ports for an InfiniBand device.
        
        Args:
            device_path: The path to the device
            
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
                    # More precise state detection - check for proper IB port states
                    # Per the InfiniBand spec, valid states are: 
                    # 1: Down, 2: Initializing, 3: Armed, 4: Active, 5: ActiveDefer
                    if state.startswith("4:") or state.startswith("5:") or "ACTIVE" in state:
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
            
           
            ports.append(port_info)
            
        return ports


if __name__ == "__main__":
    # Example usage
    from .GaudiDevices import GaudiDevices
    gaudi_devices = GaudiDevices()
    infiniband_devices = InfinibandDevices()
    
    # Scan for InfiniBand devices
    devices_info = infiniband_devices.get_infiniband_devices(gaudi_devices)
    
    print("Gaudi Devices:")
    for bus_id, device in devices_info["gaudi"].items():
        print(f"Bus ID: {bus_id}, Info: {device.get_device_info()}")
    
    print("\nOther InfiniBand Devices:")
    for bus_id, device in devices_info["other"].items():
        print(f"Bus ID: {bus_id}, Info: {device.get_device_info()}")

    # --- Test functions ---
    def test_scan_devices():
        print("\nRunning test_scan_devices...")
        from .GaudiDevices import GaudiDevices
        gaudi_devices = GaudiDevices()
        infiniband_devices = InfinibandDevices()
        devices_info = infiniband_devices.get_infiniband_devices(gaudi_devices)
        assert isinstance(devices_info, dict)
        print("test_scan_devices passed.")

    def test_gather_port_info():
        print("\nRunning test_gather_port_info...")
        infiniband_devices = InfinibandDevices()
        # Use a dummy device path if available
        if os.path.exists(infiniband_devices.ib_path):
            device_dirs = glob.glob(os.path.join(infiniband_devices.ib_path, "*"))
            if device_dirs:
                ports = infiniband_devices._gather_port_info(device_dirs[0])
                assert isinstance(ports, list)
                print("test_gather_port_info passed.")
            else:
                print("No InfiniBand devices found for port info test.")
        else:
            print("InfiniBand path does not exist for port info test.")


if __name__ == "__main__":
    # Example usage
    gaudi_devices = GaudiDevices()
    infiniband_devices = InfinibandDevices()
    
    # Scan for InfiniBand devices
    devices_info = infiniband_devices.get_infiniband_devices(gaudi_devices)
    
    print("Gaudi Devices:")
    for bus_id, device in devices_info["gaudi"].items():
        print(f"Bus ID: {bus_id}, Info: {device.get_device_info()}")
    
    print("\nOther InfiniBand Devices:")
    for bus_id, device in devices_info["other"].items():
        print(f"Bus ID: {bus_id}, Info: {device.get_device_info()}")
