#!/usr/bin/env python3
"""
Gaudi Device Information Utility

This module provides functions to retrieve information about Habana Gaudi devices
using the hl-smi command-line tool.
"""

import subprocess
import csv
import os
from typing import List, Dict, Any, Optional


def get_gaudi_devices() -> Dict[str, Dict[str, Any]]:
    """
    Get information about all available Gaudi devices using hl-smi.
    
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
                devices[bus_id] = device
            
        return devices
        
    except FileNotFoundError:
        raise FileNotFoundError("hl-smi command not found. Make sure Habana software is installed and in PATH.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error running hl-smi command: {e}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error: {e}")


def get_device_by_bus_id(bus_id: str) -> Optional[Dict[str, Any]]:
    """
    Get Gaudi device information for the specified PCI bus ID.
    
    Args:
        bus_id: The PCI bus ID to look for (e.g., "0000:b4:00.0")
        
    Returns:
        Optional[Dict[str, Any]]: Device information if found, None otherwise
    """
    devices = get_gaudi_devices()
    return devices.get(bus_id)


def get_device_by_index(index: int) -> Optional[Dict[str, Any]]:
    """
    Get Gaudi device information for the specified device index.
    
    Args:
        index: The device index (0, 1, 2, etc.)
        
    Returns:
        Optional[Dict[str, Any]]: Device information if found, None otherwise
    """
    devices = get_gaudi_devices()
    for bus_id, device in devices.items():
        if device.get('index') == index:
            return device
    return None


def get_device_by_module_id(module_id: int) -> Optional[Dict[str, Any]]:
    """
    Get Gaudi device information for the specified module ID.
    
    Args:
        module_id: The module ID to look for
        
    Returns:
        Optional[Dict[str, Any]]: Device information if found, None otherwise
    """
    devices = get_gaudi_devices()
    for bus_id, device in devices.items():
        if device.get('module_id') == module_id:
            return device
    return None


def get_detailed_gaudi_info() -> Dict[str, Dict[str, Any]]:
    """
    Get detailed information about all available Gaudi devices.
    
    Returns:
        Dict[str, Dict[str, Any]]: A dictionary mapping PCI bus IDs to detailed device information
    """
    try:
        # Run the hl-smi command with all fields
        cmd = ["hl-smi", "-f", "csv"]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
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
                devices[bus_id] = device
            
        return devices
        
    except FileNotFoundError:
        raise FileNotFoundError("hl-smi command not found. Make sure Habana software is installed and in PATH.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error running hl-smi command: {e}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error: {e}")


def print_gaudi_devices(detailed: bool = False, json_output: bool = False):
    """
    Print information about all available Gaudi devices.
    
    Args:
        detailed: Whether to print detailed device information
        json_output: Whether to print the output in JSON format
    """
    devices = get_detailed_gaudi_info() if detailed else get_gaudi_devices()
    
    if json_output:
        import json
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
    
    print_gaudi_devices(detailed=args.detailed, json_output=args.json)
