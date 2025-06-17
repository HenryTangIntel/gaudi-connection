#!/usr/bin/env python3
"""
Gaudi Device Factory

This module provides a factory class for creating and managing GaudiDevice objects
by incorporating data from both GaudiDevices and InfinibandDevices classes.
"""

from typing import Dict, List,  Optional,  Set
from src.devices.GaudiDevices import GaudiDevices, GaudiDevice
from src.devices.InfinibandDevices import InfinibandDevices


class GaudiDeviceFactory:
    """
    Factory class for creating and managing GaudiDevice objects.
    
    This class combines information from GaudiDevices and InfinibandDevices
    to create fully populated GaudiDevice objects with all relevant information.
    """
    
    def __init__(self):
        """Initialize the GaudiDeviceFactory."""
        self._gaudi_devices = GaudiDevices()
        self._infiniband_devices = InfinibandDevices()
        
        # Caches for device objects
        self._devices_by_bus_id = None
        self._devices_by_module_id = None
        self._devices_by_index = None
        self._device_id_mapping = None
        
    def clear_cache(self):
        """
        Clear all device caches.
        Call this method when you want to ensure fresh device data.
        """
        self._devices_by_bus_id = None
        self._devices_by_module_id = None
        self._devices_by_index = None
        self._device_id_mapping = None
        self._gaudi_devices.clear_cache()
        self._infiniband_devices.clear_cache()
    
    def get_device_mapping(self, use_cache: bool = True) -> Dict[str, str]:
        """
        Get a mapping of device IDs to bus IDs.
        
        Args:
            use_cache: Whether to use cached mapping if available
            
        Returns:
            Dict[str, str]: Dictionary mapping device IDs (e.g., "1da3:1724") to PCI bus IDs
        """
        if use_cache and self._device_id_mapping is not None:
            return self._device_id_mapping
            
        result = {}
        devices = self._gaudi_devices.get_detailed_gaudi_info(use_cache=use_cache)
        
        for bus_id, device_info in devices.items():
            vendor_id = device_info.get('vendor_id')
            if vendor_id:
                # Gaudi devices typically have device ID 1724
                if vendor_id == '1da3':
                    device_id = f"{vendor_id}:1724"
                else:
                    # Use a placeholder for unknown device IDs
                    device_id = f"{vendor_id}:0000"
                result[device_id] = bus_id
        
        self._device_id_mapping = result
        return result
    
    def get_all_devices(self, refresh: bool = False) -> Dict[str, GaudiDevice]:
        """
        Get all Gaudi devices as GaudiDevice objects indexed by PCI bus ID.
        
        Args:
            refresh: Whether to refresh the device cache
            
        Returns:
            Dict[str, GaudiDevice]: Dictionary of GaudiDevice objects keyed by PCI bus ID
        """
        if refresh:
            self.clear_cache()
            
        if self._devices_by_bus_id is not None:
            return self._devices_by_bus_id
            
        # Get the basic Gaudi devices info
        gaudi_devices = self._gaudi_devices.get_gaudi_devices()
        
        # Get detailed Gaudi info if available
        detailed_devices = self._gaudi_devices.get_detailed_gaudi_info() or {}
        
        # Get InfiniBand device information
        ib_devices = {}
        ib_result = self._infiniband_devices.get_infiniband_devices(include_details=True)
        
        # Create a mapping from PCI bus ID to InfiniBand device info
        for device_type in ['gaudi', 'other']:
            for device in ib_result.get(device_type, []):
                if 'pci_bus_id' in device and device['pci_bus_id'] != 'Unknown':
                    ib_devices[device['pci_bus_id']] = device
        
        # Create GaudiDevice objects
        result = {}
        for bus_id, basic_info in gaudi_devices.items():
            # Get detailed info if available
            detailed_info = detailed_devices.get(bus_id, basic_info)
            
            # Merge basic and detailed info
            merged_info = {**basic_info, **detailed_info}
            
            # Get InfiniBand info if available
            ib_info = ib_devices.get(bus_id)
            
            # Create and store the GaudiDevice object
            device = GaudiDevice(bus_id, merged_info, ib_info)
            result[bus_id] = device
        
        self._devices_by_bus_id = result
        return result
    
    def get_devices_by_module_id(self, refresh: bool = False) -> Dict[int, GaudiDevice]:
        """
        Get all Gaudi devices indexed by module ID.
        
        Args:
            refresh: Whether to refresh the device cache
            
        Returns:
            Dict[int, GaudiDevice]: Dictionary of GaudiDevice objects keyed by module ID
        """
        if refresh:
            self.clear_cache()
            
        if self._devices_by_module_id is not None:
            return self._devices_by_module_id
            
        # Get all devices by bus ID first
        devices_by_bus_id = self.get_all_devices()
        
        # Create a mapping from module ID to device
        result = {}
        for bus_id, device in devices_by_bus_id.items():
            if device.module_id is not None:
                result[device.module_id] = device
        
        self._devices_by_module_id = result
        return result
    
    def get_devices_by_index(self, refresh: bool = False) -> Dict[int, GaudiDevice]:
        """
        Get all Gaudi devices indexed by device index.
        
        Args:
            refresh: Whether to refresh the device cache
            
        Returns:
            Dict[int, GaudiDevice]: Dictionary of GaudiDevice objects keyed by device index
        """
        if refresh:
            self.clear_cache()
            
        if self._devices_by_index is not None:
            return self._devices_by_index
            
        # Get all devices by bus ID first
        devices_by_bus_id = self.get_all_devices()
        
        # Create a mapping from device index to device
        result = {}
        for bus_id, device in devices_by_bus_id.items():
            if device.index is not None:
                result[device.index] = device
        
        self._devices_by_index = result
        return result
    
    def get_device_by_bus_id(self, bus_id: str) -> Optional[GaudiDevice]:
        """
        Get a specific device by its PCI bus ID.
        
        Args:
            bus_id: The PCI bus ID of the device
            
        Returns:
            Optional[GaudiDevice]: The GaudiDevice if found, None otherwise
        """
        devices = self.get_all_devices()
        return devices.get(bus_id)
    
    def get_device_by_module_id(self, module_id: int) -> Optional[GaudiDevice]:
        """
        Get a specific device by its module ID.
        
        Args:
            module_id: The module ID of the device
            
        Returns:
            Optional[GaudiDevice]: The GaudiDevice if found, None otherwise
        """
        devices = self.get_devices_by_module_id()
        return devices.get(module_id)
    
    def get_device_by_index(self, index: int) -> Optional[GaudiDevice]:
        """
        Get a specific device by its device index.
        
        Args:
            index: The device index (from hl-smi)
            
        Returns:
            Optional[GaudiDevice]: The GaudiDevice if found, None otherwise
        """
        devices = self.get_devices_by_index()
        return devices.get(index)
    
    def get_devices_by_device_id(self, device_id: str) -> List[GaudiDevice]:
        """
        Get all devices with a specific device ID (vendor:device format).
        
        Args:
            device_id: The device ID in vendor:device format (e.g., "1da3:1724")
            
        Returns:
            List[GaudiDevice]: List of GaudiDevice objects with the specified device ID
        """
        devices = self.get_all_devices()
        return [device for device in devices.values() if device.device_id == device_id]
    
    def get_active_ports(self) -> Dict[str, Set[int]]:
        """
        Get a dictionary of active ports for each device by bus ID.
        
        Returns:
            Dict[str, Set[int]]: Dictionary mapping bus IDs to sets of active port numbers
        """
        devices = self.get_all_devices()
        result = {}
        
        for bus_id, device in devices.items():
            active_ports = set()
            for port_num, port_info in device.ports.items():
                if port_info.get('is_active', False):
                    active_ports.add(port_num)
            result[bus_id] = active_ports
        
        return result
    
    def print_device_summary(self):
        """Print a summary of all available Gaudi devices."""
        devices = self.get_all_devices()
        
        if not devices:
            print("No Gaudi devices found.")
            return
            
        print(f"Found {len(devices)} Gaudi devices:")
        print("==================================")
        
        for bus_id, device in sorted(devices.items(), key=lambda x: x[1].index if x[1].index is not None else 999):
            active_ports = [port_num for port_num, info in device.ports.items() if info.get('is_active', False)]
            active_ports_str = ', '.join(map(str, sorted(active_ports))) if active_ports else "None"
            
            print(f"Device {device.index} (Module {device.module_id}):")
            print(f"  Bus ID:      {device.bus_id}")
            print(f"  Device ID:   {device.device_id}")
            print(f"  Status:      {device.status}")
            print(f"  IB Name:     {device.ib_name}")
            print(f"  Active Ports: {active_ports_str}")
            print()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Gaudi Device Factory")
    parser.add_argument("-d", "--detailed", action="store_true", help="Show detailed device information")
    parser.add_argument("-j", "--json", action="store_true", help="Output in JSON format")
    
    args = parser.parse_args()
    
    # Create an instance of GaudiDeviceFactory
    factory = GaudiDeviceFactory()
    
    if args.json:
        import json
        devices = factory.get_all_devices()
        device_dict = {bus_id: device.to_dict() for bus_id, device in devices.items()}
        print(json.dumps(device_dict, indent=2))
    else:
        factory.print_device_summary()
