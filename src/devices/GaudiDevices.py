#!/usr/bin/env python3
"""
Gaudi Device Information Utility

This module provides classes to retrieve and represent information about Habana Gaudi devices
using the hl-smi command-line tool.
"""

import subprocess
import csv
import os
import json
from typing import List, Dict, Any, Optional, Set


class GaudiDevice:
    """
    Class representing an individual Gaudi device with its properties and associated InfiniBand information.
    """
    
    def __init__(self, bus_id: str, device_info: Dict[str, Any] = None, infiniband_info: Dict[str, Any] = None):
        """
        Initialize a GaudiDevice with its bus ID and optional device and InfiniBand information.
        
        Args:
            bus_id: The PCI bus ID of the Gaudi device (e.g., "0000:4d:00.0")
            device_info: Optional dictionary with Gaudi device information
            infiniband_info: Optional dictionary with InfiniBand device information
        """
        self.bus_id = bus_id
        self.module_id = None
        self.device_id = None  # Device ID in PCI format (vendor:device)
        self.index = None      # hl-smi device index
        self.name = None
        self.vendor_id = None
        self.serial = None
        self.temperature = None
        self.power = None
        self.max_power = None
        self.status = None
        self.driver = None
        
        # InfiniBand related information
        self.ib_name = None       # InfiniBand device name (e.g., mlx5_0)
        self.node_guid = None     # InfiniBand node GUID
        self.node_type = None     # InfiniBand node type
        self.ports = {}           # Dictionary of port number to port information
        
        # Initialize from device_info if provided
        if device_info:
            self._update_from_device_info(device_info)
        
        # Initialize from infiniband_info if provided
        if infiniband_info:
            self._update_from_infiniband_info(infiniband_info)
    
    def _update_from_device_info(self, info: Dict[str, Any]) -> None:
        """
        Update device properties from Gaudi device information.
        
        Args:
            info: Dictionary with Gaudi device information from hl-smi
        """
        # Map device_info fields to class attributes
        field_mappings = {
            'module_id': 'module_id',
            'index': 'index',
            'name': 'name',
            'vendor_id': 'vendor_id',
            'serial': 'serial',
            'temperature': 'temperature',
            'power': 'power',
            'max_power': 'max_power',
            'status': 'status',
            'driver': 'driver',
        }
        
        for info_field, attr_name in field_mappings.items():
            if info_field in info and info[info_field] is not None:
                setattr(self, attr_name, info[info_field])
        
        # Convert numeric fields to appropriate types
        if self.module_id is not None and isinstance(self.module_id, str):
            try:
                self.module_id = int(self.module_id)
            except (ValueError, TypeError):
                pass
                
        if self.index is not None and isinstance(self.index, str):
            try:
                self.index = int(self.index)
            except (ValueError, TypeError):
                pass
        
        if self.vendor_id is not None and self.vendor_id == '1da3':
            self.device_id = f"{self.vendor_id}:1724"  # Gaudi device ID is typically 1724
    
    def _update_from_infiniband_info(self, info: Dict[str, Any]) -> None:
        """
        Update device properties from InfiniBand device information.
        
        Args:
            info: Dictionary with InfiniBand device information
        """
        # Set InfiniBand basic information
        if 'name' in info:
            self.ib_name = info['name']
        if 'node_guid' in info:
            self.node_guid = info['node_guid']
        if 'type' in info:
            self.node_type = info['type']
        
        # Process ports
        if 'ports' in info and isinstance(info['ports'], list):
            for port_info in info['ports']:
                if 'port_num' in port_info and port_info['port_num'] is not None:
                    port_num = port_info['port_num']
                    if isinstance(port_num, str):
                        try:
                            port_num = int(port_num)
                        except (ValueError, TypeError):
                            continue
                            
                    self.ports[port_num] = {
                        'is_active': port_info.get('is_active', False),
                        'state': port_info.get('state', 'Unknown'),
                        'link_layer': port_info.get('link_layer', 'Unknown'),
                        'rate': port_info.get('rate', 'Unknown'),
                        'lid': port_info.get('lid'),
                        'gid': port_info.get('gid')
                    }
    
    def is_port_active(self, port_num: int) -> bool:
        """
        Check if a specific port is active.
        
        Args:
            port_num: The port number to check
            
        Returns:
            bool: True if the port is active, False otherwise
        """
        if port_num in self.ports:
            return self.ports[port_num].get('is_active', False)
        return False
    
    def get_port_status(self, port_num: int) -> str:
        """
        Get the status string for a specific port.
        
        Args:
            port_num: The port number to check
            
        Returns:
            str: Status string for the port, or "Port not found" if the port is not present
        """
        if port_num in self.ports:
            port = self.ports[port_num]
            status = "ACTIVE" if port.get('is_active', False) else "INACTIVE"
            state = port.get('state', 'Unknown')
            return f"Port {port_num} is {status} with state: {state}"
        return f"Port {port_num} not found on device {self.bus_id}"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the device information to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the device
        """
        return {
            'bus_id': self.bus_id,
            'module_id': self.module_id,
            'device_id': self.device_id,
            'index': self.index,
            'name': self.name,
            'vendor_id': self.vendor_id,
            'serial': self.serial,
            'temperature': self.temperature,
            'power': self.power,
            'max_power': self.max_power,
            'status': self.status,
            'driver': self.driver,
            'infiniband': {
                'name': self.ib_name,
                'node_guid': self.node_guid,
                'node_type': self.node_type,
                'ports': self.ports
            }
        }
    
    def __str__(self) -> str:
        """
        Get a string representation of the device.
        
        Returns:
            str: Human-readable representation of the device
        """
        active_ports = [port_num for port_num, info in self.ports.items() if info.get('is_active', False)]
        active_ports_str = ', '.join(map(str, sorted(active_ports))) if active_ports else "None"
        
        return (f"GaudiDevice {self.index} (Module {self.module_id})\n"
                f"  Bus ID: {self.bus_id}\n"
                f"  Device ID: {self.device_id}\n"
                f"  Status: {self.status}\n"
                f"  IB Name: {self.ib_name}\n"
                f"  Active Ports: {active_ports_str}")

    def _get_vendor_id_from_sys(self, bus_id: str) -> Optional[str]:
        """
        Get vendor ID from the /sys filesystem for a given PCI bus ID.
        
        Args:
            bus_id: The PCI bus ID (e.g., "0000:4d:00.0")
            
        Returns:
            str: Vendor ID if found, None otherwise
        """
        if not bus_id:
            return None
            
        # Construct path to the PCI device in sys filesystem
        pci_path = f"/sys/bus/pci/devices/{bus_id}"
        
        # Check if the path exists
        if not os.path.exists(pci_path):
            return None
        
        # Read the vendor file
        vendor_file = os.path.join(pci_path, 'vendor')
        if os.path.exists(vendor_file):
            try:
                with open(vendor_file, 'r') as f:
                    vendor_id = f.read().strip().lower()
                    if vendor_id.startswith('0x'):
                        vendor_id = vendor_id[2:]
                return vendor_id
            except Exception as e:
                print(f"Error reading vendor file for {bus_id}: {e}")
                
        return None


class GaudiDevices:
    """
    Class for interacting with Habana Gaudi devices.
    Provides methods to discover, query, and display information about Gaudi devices.
    """
    
    def __init__(self):
        """Initialize the GaudiDevices class."""
        # Cache for device information
        self._devices_cache = None
        self._detailed_devices_cache = None
        self._gaudi_device_objects = {}  # Cache for GaudiDevice objects
    
    def _get_vendor_id_from_sys(self, bus_id: str) -> Optional[str]:
        """
        Get vendor ID from the /sys filesystem for a given PCI bus ID.
        
        Args:
            bus_id: The PCI bus ID (e.g., "0000:4d:00.0")
            
        Returns:
            str: Vendor ID if found, None otherwise
        """
        if not bus_id:
            return None
            
        # Construct path to the PCI device in sys filesystem
        pci_path = f"/sys/bus/pci/devices/{bus_id}"
        
        # Check if the path exists
        if not os.path.exists(pci_path):
            return None
        
        # Read the vendor file
        vendor_file = os.path.join(pci_path, 'vendor')
        if os.path.exists(vendor_file):
            try:
                with open(vendor_file, 'r') as f:
                    vendor_id = f.read().strip().lower()
                    if vendor_id.startswith('0x'):
                        vendor_id = vendor_id[2:]
                return vendor_id
            except Exception as e:
                print(f"Error reading vendor file for {bus_id}: {e}")
                
        return None
    
    def get_gaudi_devices(self, use_cache: bool = True) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all available Gaudi devices using hl-smi.
        
        Args:
            use_cache: Whether to use cached device information if available
            
        Returns:
            Dict[str, Dict[str, Any]]: A dictionary mapping PCI bus IDs to device information dictionaries,
                                      each containing:
                                      - index: The device index (integer)
                                      - module_id: The module ID (integer)
                                      - bus_id: The PCI bus ID (string)
        
        Raises:
            RuntimeError: If hl-smi command fails or returns unexpected output
            FileNotFoundError: If hl-smi command is not found
        """
        # Return cached devices if available and cache usage is enabled
        if use_cache and self._devices_cache is not None:
            return self._devices_cache
            
        try:
            # Run the hl-smi command to get device information in CSV format
            cmd = ["hl-smi", "-Q", "index,module_id,bus_id", "-f", "csv"]
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            # Parse the CSV output
            devices = {}
            reader = csv.DictReader(result.stdout.strip().split('\n'))
            
            for row in reader:
                # Clean up the keys and values by stripping whitespace
                device = {k.strip(): v.strip() for k, v in row.items()}
                
                # Convert numeric fields to integers
                if 'index' in device:
                    device['index'] = int(device['index'])
                if 'module_id' in device:
                    device['module_id'] = int(device['module_id'])
                
                # Use bus_id as the key in the returned dictionary
                if 'bus_id' in device:
                    bus_id = device['bus_id']
                    
                    # Get vendor_id from /sys filesystem
                    vendor_id = self._get_vendor_id_from_sys(bus_id)
                    if vendor_id:
                        device['vendor_id'] = vendor_id
                    else:
                        # Set the default Habana Labs vendor ID for Gaudi devices
                        device['vendor_id'] = '1da3'
                    
                    devices[bus_id] = device
            
            # Update cache
            self._devices_cache = devices
            return devices
            
        except FileNotFoundError:
            raise FileNotFoundError("hl-smi command not found. Make sure Habana software is installed and in PATH.")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Error running hl-smi command: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error: {e}")

    def clear_cache(self):
        """
        Clear the device information cache.
        Call this method when you want to ensure fresh device data.
        """
        self._devices_cache = None
        self._detailed_devices_cache = None
        self._gaudi_device_objects = {}
        
    def get_device_objects(self, use_cache: bool = True, include_infiniband: bool = False) -> Dict[str, GaudiDevice]:
        """
        Get all Gaudi devices as GaudiDevice objects.
        
        Args:
            use_cache: Whether to use cached device objects if available
            include_infiniband: Whether to include InfiniBand information from IB filesystem
            
        Returns:
            Dict[str, GaudiDevice]: Dictionary of GaudiDevice objects keyed by bus ID
        """
        # Return cached objects if available and cache usage is enabled
        if use_cache and self._gaudi_device_objects and not include_infiniband:
            return self._gaudi_device_objects
            
        # Try to get detailed device information from hl-smi
        detailed_devices = self.get_detailed_gaudi_info(use_cache=use_cache)
        
        # If detailed information isn't available, use basic device info instead
        if not detailed_devices:
            print("Falling back to basic device information (detailed info not available)")
            detailed_devices = self.get_gaudi_devices(use_cache=use_cache)
        
        # Get InfiniBand information if requested
        infiniband_devices = {}
        if include_infiniband:
            try:
                from gaudi_connect.devices.InfinibandDevices import InfinibandDevices
                ib_obj = InfinibandDevices()
                ib_info = ib_obj.get_infiniband_devices(include_details=True)
                
                # Create a mapping from PCI bus ID to InfiniBand device info
                for device_type in ['gaudi', 'other']:
                    for device in ib_info.get(device_type, []):
                        if 'pci_bus_id' in device:
                            infiniband_devices[device['pci_bus_id']] = device
            except Exception as e:
                print(f"Warning: Failed to get InfiniBand information: {e}")
        
        # Create GaudiDevice objects
        device_objects = {}
        print(f"Creating GaudiDevice objects from {len(detailed_devices)} detailed devices")
        print(f"Available InfiniBand devices: {list(infiniband_devices.keys())}")
        for bus_id, device_info in detailed_devices.items():
            print(f"Processing device with bus ID: {bus_id}")
            ib_info = infiniband_devices.get(bus_id)
            if ib_info:
                print(f"Found matching InfiniBand info for {bus_id}")
            device_objects[bus_id] = GaudiDevice(bus_id, device_info, ib_info)
        
        # Cache the objects if we're not including InfiniBand info (which can change)
        if not include_infiniband:
            self._gaudi_device_objects = device_objects
            
        return device_objects

    def get_device_by_bus_id(self, bus_id: str) -> Optional[Dict[str, Any]]:
        """
        Get Gaudi device information for the specified PCI bus ID.
        
        Args:
            bus_id: The PCI bus ID to look for (e.g., "0000:b4:00.0")
            
        Returns:
            Optional[Dict[str, Any]]: Device information if found, None otherwise
        """
        devices = self.get_gaudi_devices()
        return devices.get(bus_id)
    
    def get_device_object_by_bus_id(self, bus_id: str, include_infiniband: bool = False) -> Optional[GaudiDevice]:
        """
        Get a GaudiDevice object for the specified PCI bus ID.
        
        Args:
            bus_id: The PCI bus ID to look for (e.g., "0000:b4:00.0")
            include_infiniband: Whether to include InfiniBand information
            
        Returns:
            Optional[GaudiDevice]: GaudiDevice object if found, None otherwise
        """
        device_objects = self.get_device_objects(include_infiniband=include_infiniband)
        return device_objects.get(bus_id)

    def get_device_by_index(self, index: int) -> Optional[Dict[str, Any]]:
        """
        Get Gaudi device information for the specified device index.
        
        Args:
            index: The device index (0, 1, 2, etc.)
            
        Returns:
            Optional[Dict[str, Any]]: Device information if found, None otherwise
        """
        devices = self.get_gaudi_devices()
        for bus_id, device in devices.items():
            if device.get('index') == index:
                return device
        return None
    
    def get_device_object_by_index(self, index: int, include_infiniband: bool = False) -> Optional[GaudiDevice]:
        """
        Get a GaudiDevice object for the specified device index.
        
        Args:
            index: The device index (0, 1, 2, etc.)
            include_infiniband: Whether to include InfiniBand information
            
        Returns:
            Optional[GaudiDevice]: GaudiDevice object if found, None otherwise
        """
        device_objects = self.get_device_objects(include_infiniband=include_infiniband)
        for bus_id, device in device_objects.items():
            if device.index == index:
                return device
        return None

    def get_device_by_module_id(self, module_id: int) -> Optional[Dict[str, Any]]:
        """
        Get Gaudi device information for the specified module ID.
        
        Args:
            module_id: The module ID to look for
            
        Returns:
            Optional[Dict[str, Any]]: Device information if found, None otherwise
        """
        devices = self.get_gaudi_devices()
        for bus_id, device in devices.items():
            if device.get('module_id') == module_id:
                return device
        return None
    
    def get_device_object_by_module_id(self, module_id: int, include_infiniband: bool = False) -> Optional[GaudiDevice]:
        """
        Get a GaudiDevice object for the specified module ID.
        
        Args:
            module_id: The module ID to look for
            include_infiniband: Whether to include InfiniBand information
            
        Returns:
            Optional[GaudiDevice]: GaudiDevice object if found, None otherwise
        """
        device_objects = self.get_device_objects(include_infiniband=include_infiniband)
        for bus_id, device in device_objects.items():
            if device.module_id == module_id:
                return device
        return None

    def get_detailed_gaudi_info(self, use_cache: bool = True) -> Dict[str, Dict[str, Any]]:
        """
        Get detailed information about all available Gaudi devices.
        
        Args:
            use_cache: Whether to use cached device information if available
            
        Returns:
            Dict[str, Dict[str, Any]]: A dictionary mapping PCI bus IDs to detailed device information
        """
        # Return cached detailed devices if available and cache usage is enabled
        if use_cache and self._detailed_devices_cache is not None:
            return self._detailed_devices_cache
            
        try:
            # Run the hl-smi command with all fields
            cmd = ["hl-smi", "-f", "csv"]
            print(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"Command output (first 200 chars): {result.stdout[:200]}")
            
            # Parse the CSV output
            devices = {}
            lines = result.stdout.strip().split('\n')
            
            if len(lines) <= 1:  # Header only or empty
                return {}
                
            reader = csv.DictReader(lines)
            
            for row in reader:
                # Clean up the keys and values by stripping whitespace
                device = {k.strip(): v.strip() for k, v in row.items()}
                
                # Convert numeric fields to appropriate types
                for field in ['index', 'module_id', 'temperature', 'power', 'max_power']:
                    if field in device and device[field]:
                        try:
                            device[field] = int(float(device[field]))
                        except (ValueError, TypeError):
                            pass
                
                # Use bus_id as the key in the returned dictionary
                if 'bus_id' in device:
                    bus_id = device['bus_id']
                    
                    # Get vendor_id from /sys filesystem
                    vendor_id = self._get_vendor_id_from_sys(bus_id)
                    if vendor_id:
                        device['vendor_id'] = vendor_id
                    else:
                        # Set the default Habana Labs vendor ID for Gaudi devices
                        device['vendor_id'] = '1da3'
                    
                    devices[bus_id] = device
            
            # Update cache
            self._detailed_devices_cache = devices
            return devices
            
        except FileNotFoundError:
            raise FileNotFoundError("hl-smi command not found. Make sure Habana software is installed and in PATH.")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Error running hl-smi command: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error: {e}")

    def print_gaudi_devices(self, detailed: bool = False, json_output: bool = False, use_objects: bool = True):
        """
        Print information about all available Gaudi devices.
        
        Args:
            detailed: Whether to print detailed device information
            json_output: Whether to print the output in JSON format
            use_objects: Whether to use GaudiDevice objects for output
        """
        if use_objects:
            # Get device objects
            devices = self.get_device_objects(include_infiniband=detailed)
            
            if json_output:
                # Convert device objects to dictionaries
                output = {bus_id: device.to_dict() for bus_id, device in devices.items()}
                print(json.dumps(output, indent=2))
                return
            
            if not devices:
                print("No Gaudi devices found.")
                return
            
            print("Gaudi Devices:")
            print("==============")
            
            for bus_id, device in sorted(devices.items(), key=lambda x: x[1].index if x[1].index is not None else 999):
                print(device)  # Use the __str__ method for output
                print()
        else:
            # Use traditional dictionary output
            devices = self.get_detailed_gaudi_info() if detailed else self.get_gaudi_devices()
            
            if json_output:
                print(json.dumps(devices, indent=2))
                return
            
            if not devices:
                print("No Gaudi devices found.")
                return
            
            print("Gaudi Devices:")
            print("==============")
            
            for bus_id, device in sorted(devices.items(), key=lambda x: x[1].get('index', 0)):
                print(f"Device {device.get('index', 'Unknown')}")
                print(f"  Bus ID:        {bus_id}")
                print(f"  Module ID:     {device.get('module_id', 'Unknown')}")
                
                if detailed:
                    print(f"  Name:          {device.get('name', 'Unknown')}")
                    print(f"  Serial Number: {device.get('serial', 'Unknown')}")
                    print(f"  Temperature:   {device.get('temperature', 'Unknown')} °C")
                    print(f"  Power:         {device.get('power', 'Unknown')} W")
                    print(f"  Max Power:     {device.get('max_power', 'Unknown')} W")
                    print(f"  Status:        {device.get('status', 'Unknown')}")
                    print(f"  Driver:        {device.get('driver', 'Unknown')}")
                
                print()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Gaudi Device Information Utility")
    parser.add_argument("-d", "--detailed", action="store_true", help="Show detailed device information")
    parser.add_argument("-j", "--json", action="store_true", help="Output in JSON format")
    
    args = parser.parse_args()
    
    # Create an instance of GaudiDevices
    gaudi_devices = GaudiDevices()
    
    # Print device information based on command line arguments
    gaudi_devices.print_gaudi_devices(detailed=args.detailed, json_output=args.json)

