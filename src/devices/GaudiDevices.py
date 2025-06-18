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
from typing import  Dict, Any, Optional
from abc import ABC, abstractmethod




class PCIeDevice(ABC):
    """
    Abstract base class for PCIe devices.
    Provides a common interface for device properties and methods.
    """
    
    @abstractmethod
    def get_device_info(self) -> Dict[str, Any]:
        """
        Get the device information as a dictionary.
        
        Returns:
            Dict[str, Any]: Device information
        """
        pass
    @abstractmethod
    def update_device_info(self, device_info: Dict[str, Any]) -> None:
        """
        Update the device information with new data.
        
        Args:
            device_info: Dictionary containing updated device information
        """
        pass
class MlxDevice(PCIeDevice):
    """
    Class representing an individual Mellanox device with its properties.
    """
    
    def __init__(self, bus_id: str, device_info: Dict[str, Any] = None):
        """
        Initialize a MlxDevice with its bus ID and optional device information.
        
        Args:
            bus_id: The PCI bus ID of the Mellanox device (e.g., "0000:4d:00.0")
            device_info: Optional dictionary with Mellanox device information
        """
        self.bus_id = bus_id
        self.device_info = device_info or {}
        
    def get_device_info(self) -> Dict[str, Any]:
        """
        Get the device information as a dictionary.
        
        Returns:
            Dict[str, Any]: Device information including bus ID and other properties
        """
        return {
            'bus_id': self.bus_id,
            **self.device_info
        }
        
    def update_device_info(self, device_info: Dict[str, Any]) -> None:
        """
        Update the device information with new data.
        
        Args:
            device_info: Dictionary containing updated device information
        """
        self.device_info.update(device_info)
    


class GaudiDevice(PCIeDevice):
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
        self.module_id = device_info.get('module_id') if device_info else None 
        self.device_id = device_info.get('index') if device_info else None
        
        # InfiniBand related information
        self.ib_name = None       # InfiniBand device name (e.g., mlx5_0)
        self.node_guid = None     # InfiniBand node GUID
        self.node_type = None     # InfiniBand node type
        self.ports = ()           # Tuple of ports indexed by port number

    def get_device_info(self) -> Dict[str, Any]:
        """
        Get the device information as a dictionary.
        
        Returns:
            Dict[str, Any]: Device information including bus ID, module ID, and device ID
        """
        return {
            'bus_id': self.bus_id,
            'module_id': self.module_id,
            'device_id': self.device_id,
            'ib_name': self.ib_name,
            'node_guid': self.node_guid,
            'node_type': self.node_type,
            'ports': self.ports
        }
        
    def update_device_info(self, device_info: Dict[str, Any]) -> None:
        """
        Update the device information with new data.
        
        Args:
            device_info: Dictionary containing updated device information
        """
        if 'module_id' in device_info:
            self.module_id = device_info['module_id']
        if 'index' in device_info:
            self.device_id = device_info['index']
        if 'bus_id' in device_info:
            self.bus_id = device_info['bus_id']
        
        # Update InfiniBand related information
        if 'ib_name' in device_info:
            self.ib_name = device_info['ib_name']
        if 'node_guid' in device_info:
            self.node_guid = device_info['node_guid']
        if 'node_type' in device_info:
            self.node_type = device_info['node_type']
        if 'ports' in device_info:
            self.ports = {port['port_num']: port for port in device_info['ports']}
            
    def __str__(self):
        """
        String representation of the GaudiDevice object.
        
        Returns:
            str: A string representation of the Gaudi device including its bus ID and module ID
        """
        return f"GaudiDevice(bus_id={self.bus_id}, module_id={self.module_id}, device_id={self.device_id}, ib_name={self.ib_name}, node_guid={self.node_guid})"
        
class GaudiDevices:
    """
    Class for interacting with Habana Gaudi devices.
    Provides methods to discover, query, and display information about Gaudi devices.
    """
    
    def __init__(self):
        """Initialize the GaudiDevices class."""
        self._devices = {}  # Cache for device information
        self._parse_gaudi_devices()  # Initialize device objects
        from . import InfinibandDevices
        self._infiniband_devices = InfinibandDevices.InfinibandDevices()  # Initialize InfiniBand devices handler
        self._infiniband_devices.get_infiniband_devices(self)  # Populate InfiniBand device information

    def _parse_gaudi_devices(self) -> Dict[str, GaudiDevice]:
        """
        Get information about all available Gaudi devices using hl-smi.
            
        Returns:
            Dict[str, GaudiDevice]: A dictionary mapping PCI bus IDs to GaudiDevice objects
        
        Raises:
            RuntimeError: If hl-smi command fails or returns unexpected output
            FileNotFoundError: If hl-smi command is not found
        """
        if self._devices:
            return self._devices
        
        try:
            # Run the hl-smi command to get device information in CSV format
            cmd = ["hl-smi", "-Q", "index,module_id,bus_id", "-f", "csv"]
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            # Parse the CSV output
            reader = csv.DictReader(result.stdout.strip().split('\n'))
            
            for row in reader:
                # Clean up the keys and values by stripping whitespace
                device = {k.strip(): v.strip() for k, v in row.items()}
                
                # Convert numeric fields to integers
                if 'index' in device:
                    device['index'] = int(device['index'])
                if 'module_id' in device:
                    device['module_id'] = int(device['module_id'])
                if 'bus_id' in device:
                    busid = device['bus_id'].strip()
                    device['bus_id'] = busid
                self._devices[device['bus_id']] = GaudiDevice(busid, device)
                
            return self._devices

        except FileNotFoundError:
            raise FileNotFoundError("hl-smi command not found. Make sure Habana software is installed and in PATH.")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Error running hl-smi command: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error: {e}")
        
    def get_device_by_bus_id(self, bus_id: str) -> Optional[GaudiDevice]:
        """
        Get a Gaudi device by its PCI bus ID.
        
        Args:
            bus_id: The PCI bus ID of the Gaudi device (e.g., "0000:4d:00.0")
        
        Returns:
            GaudiDevice: The GaudiDevice object if found, else None
        """
        return self._devices.get(bus_id)
    
    def get_device_by_module_id(self, module_id: int) -> Optional[GaudiDevice]:
        """
        Get a Gaudi device by its module ID.
        
        Args:
            module_id: The module ID of the Gaudi device (e.g., 0)
        
        Returns:
            GaudiDevice: The GaudiDevice object if found, else None
        """
        for device in self._devices.values():
            if device.module_id == module_id:
                return device
        return None 
        
    
    def get_devices(self) -> Dict[str, GaudiDevice]:
        """
        Get all Gaudi devices.
        
        Returns:
            Dict[str, GaudiDevice]: A dictionary mapping PCI bus IDs to GaudiDevice objects
        """
        return self._devices
    
    def __str__(self):
        """
        String representation of the GaudiDevices object.
        
        Returns:
            str: A string listing all Gaudi devices and their properties
        """
        return "\n".join(f"{bus_id}: {device.get_device_info()}" for bus_id, device in self._devices.items())
        
        
if __name__ == "__main__":
    gaudi_devices = GaudiDevices()
    devices = gaudi_devices.get_gaudi_devices()

    for bus_id, device in devices.items():
        print(f"Bus ID: {bus_id}, Device Info: {device.__dict__}")

    # You can also access specific properties like:
    # print(devices['0000:4d:00.0'].module_id)
    # print(devices['0000:4d:00.0'].device_id)
