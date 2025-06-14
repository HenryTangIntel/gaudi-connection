#!/usr/bin/env python3
"""
Gaudi Device Information Utility

This module provides functions to retrieve information about Habana Gaudi devices
using the hl-smi command-line tool.
"""

import subprocess
import csv
from typing import List, Dict, Any, Optional
import os


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
    Get more detailed information about all Gaudi devices.
    
    This function runs hl-smi with more query parameters to get more detailed information.
    
    Returns:
        Dict[str, Dict[str, Any]]: A dictionary mapping PCI bus IDs to device information dictionaries
                                  with detailed device information
    """
    try:
        # Query more parameters for detailed information
        query_params = [
            "index", "module_id", "bus_id", "name", "serial", "power.draw",
            "pcie.link.gen.current", "pcie.link.width.current", "temperature.aip", 
            "memory.used", "memory.total", "utilization.aip"
        ]
        
        cmd = ["hl-smi", "-Q", ",".join(query_params), "-f", "csv"]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        # Parse the CSV output
        devices = {}
        reader = csv.DictReader(result.stdout.strip().split('\n'))
        
        for row in reader:
            # Clean up the keys and values by stripping whitespace
            device = {k.strip(): v.strip() for k, v in row.items()}
            
            # Convert numeric fields to appropriate types
            numeric_fields = ['index', 'module_id', 'pcie.link.gen.current', 'pcie.link.width.current']
            for field in numeric_fields:
                if field in device and device[field] and device[field] != 'N/A':
                    try:
                        # Extract numeric part if there are units
                        value = device[field].split()[0] if ' ' in device[field] else device[field]
                        device[field] = int(value)
                    except ValueError:
                        pass  # Keep as string if conversion fails
                        
            # Convert floating point fields
            float_fields = ['power.draw', 'temperature.aip', 'memory.used', 'memory.total', 'utilization.aip']
            for field in float_fields:
                if field in device and device[field] and device[field] != 'N/A':
                    try:
                        # Extract numeric part if there are units
                        value = device[field].split()[0] if ' ' in device[field] else device[field]
                        device[field] = float(value)
                    except ValueError:
                        pass  # Keep as string if conversion fails
            
            # Use bus_id as the key in the returned dictionary
            if 'bus_id' in device:
                bus_id = device['bus_id']
                devices[bus_id] = device
            
        return devices
        
    except Exception as e:
        raise RuntimeError(f"Error getting detailed Gaudi information: {e}")


def print_gaudi_devices(detailed: bool = False):
    """
    Print information about all detected Gaudi devices in a formatted table.
    
    Args:
        detailed: If True, show detailed information including temperature, 
                 utilization, memory, etc.
    """
    try:
        if detailed:
            devices_dict = get_detailed_gaudi_info()
        else:
            devices_dict = get_gaudi_devices()
        
        if not devices_dict:
            print("No Gaudi devices found.")
            return
        
        if detailed:
            # Print detailed header
            print("\nGaudi Devices (Detailed):")
            print("=" * 100)
            print(f"{'Index':<6} {'Module ID':<10} {'PCI Bus ID':<12} {'Temp(°C)':<10} {'Util(%)':<8} {'Memory Used':<15} {'PCIe Link':<12} {'Power(W)':<10}")
            print("-" * 100)
            
            # Print each device with detailed info
            for bus_id, device in sorted(devices_dict.items(), key=lambda x: x[1].get('index', 999)):
                index = device.get('index', 'N/A')
                module_id = device.get('module_id', 'N/A')
                bus_id = device.get('bus_id', 'N/A')
                
                # Get temperature, removing units if present
                temp = device.get('temperature.aip', 'N/A')
                if isinstance(temp, str) and ' ' in temp:
                    temp = temp.split(' ')[0]
                
                # Get utilization
                util = device.get('utilization.aip', 'N/A')
                if isinstance(util, str) and ' ' in util:
                    util = util.split(' ')[0]
                
                # Get memory usage
                mem_used = device.get('memory.used', 'N/A')
                mem_total = device.get('memory.total', 'N/A')
                memory = f"{mem_used}/{mem_total}"
                
                # Get PCIe link information
                pcie_gen = device.get('pcie.link.gen.current', '')
                pcie_width = device.get('pcie.link.width.current', '')
                pcie_link = f"Gen{pcie_gen}x{pcie_width}" if pcie_gen and pcie_width else 'N/A'
                
                # Get power usage
                power = device.get('power.draw', 'N/A')
                
                # Print the row
                print(f"{index:<6} {module_id:<10} {bus_id:<12} {temp:<10} {util:<8} {memory:<15} {pcie_link:<12} {power:<10}")
        else:
            # Print basic header
            print("\nGaudi Devices:")
            print("=" * 50)
            print(f"{'Index':<6} {'Module ID':<10} {'PCI Bus ID':<12}")
            print("-" * 50)
            
            # Print each device with basic info
            for bus_id, device in sorted(devices_dict.items(), key=lambda x: x[1].get('index', 999)):
                print(f"{device.get('index', 'N/A'):<6} {device.get('module_id', 'N/A'):<10} {device.get('bus_id', 'N/A'):<12}")
            
        print("=" * (100 if detailed else 50))
        print(f"Total devices found: {len(devices_dict)}")
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Gaudi Device Information Utility")
    parser.add_argument("-d", "--detailed", action="store_true", 
                        help="Show detailed device information")
    parser.add_argument("-j", "--json", action="store_true",
                        help="Output in JSON format")
    args = parser.parse_args()
    
    if args.json:
        import json
        if args.detailed:
            devices_dict = get_detailed_gaudi_info()
        else:
            devices_dict = get_gaudi_devices()
        print(json.dumps(devices_dict, indent=2))
    else:
        print_gaudi_devices(detailed=args.detailed)
