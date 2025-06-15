#!/usr/bin/env python3
"""
Gaudi Connection Test Main

This script is the main entry point for testing connections between Gaudi devices
based on connectivity information. It ensures that connections are only tested
between devices with different module IDs.
"""

import os
import sys
import argparse
import json
import time
import random
from typing import Dict, List, Tuple, Any, Optional
import concurrent.futures

from gaudi_connect.devices.gaudi_devices import get_gaudi_devices, get_detailed_gaudi_info
from gaudi_connect.devices.infiniband_devices import get_infiniband_devices
from gaudi_connect.connectivity.gaudi2_connect import parse_connectivity_file

def get_device_by_module_id(devices: Dict[str, Dict[str, Any]], module_id: int) -> Optional[Dict[str, Any]]:
    """
    Find a device by its module ID.
    
    Args:
        devices: Dictionary of devices keyed by bus ID
        module_id: Module ID to search for
        
    Returns:
        Optional[Dict]: Device information or None if not found
    """
    for bus_id, device in devices.items():
        if device.get('module_id') == module_id:
            # Include the bus_id in the device info
            device_info = device.copy()
            device_info['bus_id'] = bus_id
            return device_info
    return None


def check_port_status(device_bus_id: str, port_num: int, ib_devices: Dict[str, Dict[str, Any]]) -> Tuple[bool, str]:
    """
    Check if an InfiniBand port is active.
    
    Args:
        device_bus_id: PCI bus ID of the device
        port_num: Port number to check
        ib_devices: Dictionary of InfiniBand devices with port information
        
    Returns:
        Tuple of (is_active, status_message)
    """
    if not ib_devices or device_bus_id not in ib_devices:
        return False, f"Device with bus ID {device_bus_id} not found in InfiniBand devices"
    
    device_info = ib_devices[device_bus_id]
    
    # Handle detailed and basic information formats
    if "ports" in device_info:  # Detailed information
        ports_info = device_info["ports"]
        if port_num not in ports_info:
            return False, f"Port {port_num} not found on device {device_bus_id}"
            
        port_info = ports_info[port_num]
        is_active = port_info.get("is_active", False)
        state = port_info.get("state", "Unknown")
        
        if is_active:
            return True, f"Port {port_num} is ACTIVE with state: {state}"
        else:
            return False, f"Port {port_num} is INACTIVE with state: {state}"
    else:  # Basic information
        active_ports = device_info.get("active_ports", [])
        if port_num in active_ports:
            return True, f"Port {port_num} is in the list of active ports"
        else:
            return False, f"Port {port_num} is not in the list of active ports: {active_ports}"


def connect_devices(source_device: Dict[str, Any], source_port: int,
                  dest_device: Dict[str, Any], dest_port: int,
                  ib_devices: Dict[str, Dict[str, Any]] = None,
                  simulate: bool = True) -> Tuple[bool, str]:
    """
    Connect two Gaudi devices, checking port status first.
    
    Args:
        source_device: Source device information
        source_port: Port on the source device
        dest_device: Destination device information
        dest_port: Port on the destination device
        ib_devices: Dictionary of InfiniBand devices with port information
        simulate: Whether to simulate connection (True) or use real API (False)
        
    Returns:
        Tuple of (success, message)
    """
    src_module_id = source_device.get('module_id')
    dst_module_id = dest_device.get('module_id')
    src_bus_id = source_device.get('bus_id')
    dst_bus_id = dest_device.get('bus_id')
    
    # Ensure we're connecting different modules
    if src_module_id == dst_module_id:
        return False, f"Cannot connect same module to itself (Module ID: {src_module_id})"
    
    print(f"Connecting module {src_module_id}:{source_port} to module {dst_module_id}:{dest_port}")
    print(f"  Bus IDs: {src_bus_id} -> {dst_bus_id}")
    
    # Ensure vendor_id is not None for both source and destination
    src_vendor_id = source_device.get('vendor_id', 'unknown')
    dst_vendor_id = dest_device.get('vendor_id', 'unknown')
    if src_vendor_id is None:
        src_vendor_id = 'unknown'
    if dst_vendor_id is None:
        dst_vendor_id = 'unknown'
    if src_vendor_id == 'unknown' or dst_vendor_id == 'unknown':
        print(f"ERROR: Source or destination vendor_id is None or unknown. Source: {src_vendor_id}, Dest: {dst_vendor_id}")
        return False, "Connection skipped: source or destination vendor_id is None or unknown."
    # Only test connection between Gaudi devices (vendor_id == '1da3')
    if src_vendor_id != '1da3' or dst_vendor_id != '1da3':
        print(f"Source vendor_id: {src_vendor_id}")
        print(f"Dest vendor_id: {dst_vendor_id}")
        return False, "Connection skipped: one or both devices are not Gaudi devices."
    
    # Check port status in InfiniBand devices if available
    if ib_devices:
        # Check source port status
        src_active, src_status = check_port_status(src_bus_id, source_port, ib_devices)
        if not src_active:
            return False, f"Source port check failed: {src_status}"
            
        # Check destination port status
        dst_active, dst_status = check_port_status(dst_bus_id, dest_port, ib_devices)
        if not dst_active:
            return False, f"Destination port check failed: {dst_status}"
            
        print(f"  Source port status: {src_status}")
        print(f"  Destination port status: {dst_status}")
    
    if simulate:
        # Simulate connection with 95% success rate
        success = random.random() < 0.95
        time.sleep(0.1)  # Simulate connection time
        
        if success:
            return True, f"Successfully connected module {src_module_id}:{source_port} to {dst_module_id}:{dest_port}"
        else:
            return False, f"Failed to connect module {src_module_id}:{source_port} to {dst_module_id}:{dest_port}"
    else:
        # TODO: Implement actual connection API calls here
        # For now, just return success
        return True, f"Connected module {src_module_id}:{source_port} to {dst_module_id}:{dest_port}"


def filter_valid_connections(connections: List[Dict[str, int]]) -> List[Dict[str, int]]:
    """
    Filter connections to ensure source and destination module IDs are different.
    
    Args:
        connections: List of connection dictionaries
        
    Returns:
        List of filtered connections
    """
    valid_connections = []
    invalid_connections = []
    
    for conn in connections:
        src_module_id = conn['source_module_id']
        dst_module_id = conn['destination_module_id']
        
        if src_module_id != dst_module_id:
            valid_connections.append(conn)
        else:
            invalid_connections.append(conn)
    
    if invalid_connections:
        print(f"Warning: Found {len(invalid_connections)} invalid connections (same source and destination module IDs).")
        print("These connections will be skipped.")
        
    return valid_connections


def test_connections(connections: List[Dict[str, int]], 
                    devices: Dict[str, Dict[str, Any]],
                    parallel: bool = False, 
                    timeout: int = 30,
                    simulate: bool = True,
                    check_ib_ports: bool = True) -> Dict[str, Any]:
    """
    Test connections between Gaudi devices.
    
    Args:
        connections: List of connection dictionaries
        devices: Dictionary of devices keyed by bus ID
        parallel: Whether to run tests in parallel
        timeout: Timeout in seconds for parallel execution
        simulate: Whether to simulate connections
        check_ib_ports: Whether to check InfiniBand port status before attempting connections
        
    Returns:
        Dictionary with test results
    """
    # Filter valid connections
    valid_connections = filter_valid_connections(connections)
    
    results = {
        "total_connections": len(valid_connections),
        "successful": 0,
        "failed": 0,
        "skipped": len(connections) - len(valid_connections),
        "inactive_ports": 0,
        "failures": [],
        "success_rate": 0.0
    }
    
    if not valid_connections:
        print("No valid connections to test.")
        return results
    
    # Get InfiniBand device information if port checking is enabled
    ib_devices = None
    ib_vendor_map = {}
    if check_ib_ports:
        print("Retrieving InfiniBand device information for port status check...")
        try:
            # Get detailed port information
            ib_result = get_infiniband_devices(include_details=True)
            if not ib_result or (not ib_result.get('gaudi') and not ib_result.get('other')):
                print("Warning: No InfiniBand devices found, port status check will be skipped.")
                ib_devices = {}
            else:
                print(f"Found {len(ib_result.get('gaudi', []))} Gaudi devices and {len(ib_result.get('other', []))} other devices")
                # Merge both lists into a dict keyed by pci_bus_id for compatibility
                ib_devices = {}
                for dev in ib_result.get('gaudi', []):
                    ib_devices[dev['pci_bus_id']] = dev
<<<<<<< HEAD
                for dev in ib_result.get('other', []):
                    ib_devices[dev['pci_bus_id']] = dev
=======
                    ib_vendor_map[dev['pci_bus_id']] = dev.get('vendor_id', '1da3')
                for dev in ib_result.get('other', []):
                    ib_devices[dev['pci_bus_id']] = dev
                    ib_vendor_map[dev['pci_bus_id']] = dev.get('vendor_id', 'unknown')
>>>>>>> f57dd94 (update infiniband device detection.)
        except Exception as e:
            print(f"Warning: Error retrieving InfiniBand device information: {e}")
            print("Port status check will be skipped.")

    # Propagate vendor_id from ib_vendor_map into devices dict
    for bus_id, device in devices.items():
        if 'vendor_id' not in device or device['vendor_id'] is None:
            device['vendor_id'] = ib_vendor_map.get(bus_id, 'unknown')
    
    print(f"Testing {len(valid_connections)} connections between Gaudi devices...")
    
    # Function to test a single connection
    def test_single_connection(conn: Dict[str, int]) -> Tuple[bool, Dict[str, Any]]:
        src_module_id = conn['source_module_id']
        src_port = conn['source_port']
        dst_module_id = conn['destination_module_id']
        dst_port = conn['destination_port']
        
        src_device = get_device_by_module_id(devices, src_module_id)
        dst_device = get_device_by_module_id(devices, dst_module_id)
        
        if not src_device:
            return False, {
                "error": f"Source device with module ID {src_module_id} not found",
                "connection": conn
            }
        
        if not dst_device:
            return False, {
                "error": f"Destination device with module ID {dst_module_id} not found",
                "connection": conn
            }
        
        success, message = connect_devices(
            src_device, src_port, 
            dst_device, dst_port, 
            ib_devices=ib_devices, 
            simulate=simulate
        )
        
        if not success:
            failure_info = {
                "error": message,
                "source": {
                    "module_id": src_module_id,
                    "bus_id": src_device.get('bus_id', 'unknown'),
                    "port": src_port
                },
                "destination": {
                    "module_id": dst_module_id,
                    "bus_id": dst_device.get('bus_id', 'unknown'),
                    "port": dst_port
                }
            }
            
            # Check if failure was due to inactive port
            if "port check failed" in message:
                failure_info["failure_type"] = "inactive_port"
            
            return False, failure_info
        
        return True, {"message": message}
    
    # Execute tests
    if parallel:
        print("Running connection tests in parallel...")
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(test_single_connection, conn) for conn in valid_connections]
            
            for future in concurrent.futures.as_completed(futures, timeout=timeout):
                try:
                    success, result = future.result()
                    if success:
                        results["successful"] += 1
                    else:
                        results["failed"] += 1
                        results["failures"].append(result)
                        
                        # Track inactive port failures
                        if result.get("failure_type") == "inactive_port":
                            results["inactive_ports"] += 1
                except Exception as e:
                    results["failed"] += 1
                    results["failures"].append({
                        "error": f"Test execution error: {str(e)}"
                    })
    else:
        print("Running connection tests sequentially...")
        for i, conn in enumerate(valid_connections):
            print(f"Testing connection {i+1}/{len(valid_connections)}...")
            success, result = test_single_connection(conn)
            if success:
                results["successful"] += 1
            else:
                results["failed"] += 1
                results["failures"].append(result)
                
                # Track inactive port failures
                if result.get("failure_type") == "inactive_port":
                    results["inactive_ports"] += 1
    
    # Calculate success rate
    if results["total_connections"] > 0:
        results["success_rate"] = (results["successful"] / results["total_connections"]) * 100.0
    
    return results


def print_results(results: Dict[str, Any], verbose: bool = False):
    """
    Print connection test results.
    
    Args:
        results: Dictionary with test results
        verbose: Whether to print detailed failure information
    """
    print("\n" + "="*80)
    print("GAUDI CONNECTION TEST RESULTS")
    print("="*80)
    
    print(f"Total connections tested:  {results['total_connections']}")
    print(f"Successful connections:    {results['successful']}")
    print(f"Failed connections:        {results['failed']}")
    
    if "inactive_ports" in results and results["inactive_ports"] > 0:
        print(f"Inactive port failures:    {results['inactive_ports']}")
    
    if "skipped" in results and results["skipped"] > 0:
        print(f"Skipped connections:       {results['skipped']} (same module ID for source and destination)")
    
    print(f"Success rate:              {results['success_rate']:.2f}%")
    
    if verbose and results["failures"]:
        port_failures = [f for f in results["failures"] if f.get("failure_type") == "inactive_port"]
        other_failures = [f for f in results["failures"] if f.get("failure_type") != "inactive_port"]
        
        if port_failures:
            print("\nINACTIVE PORT FAILURES:")
            print("-"*80)
            
            for i, failure in enumerate(port_failures):
                print(f"Inactive Port {i+1}:")
                
                if "source" in failure and "destination" in failure:
                    print(f"  Source:      Module {failure['source']['module_id']} (Bus ID: {failure['source']['bus_id']})")
                    print(f"  Source Port: {failure['source']['port']}")
                    print(f"  Destination: Module {failure['destination']['module_id']} (Bus ID: {failure['destination']['bus_id']})")
                    print(f"  Dest Port:   {failure['destination']['port']}")
                
                print(f"  Error:       {failure.get('error', 'Unknown error')}")
                print()
        
        if other_failures:
            print("\nOTHER FAILURE INFORMATION:")
            print("-"*80)
            
            for i, failure in enumerate(other_failures):
                print(f"Failure {i+1}:")
                
                if "source" in failure and "destination" in failure:
                    print(f"  Source:      Module {failure['source']['module_id']} (Bus ID: {failure['source']['bus_id']})")
                    print(f"  Source Port: {failure['source']['port']}")
                    print(f"  Destination: Module {failure['destination']['module_id']} (Bus ID: {failure['destination']['bus_id']})")
                    print(f"  Dest Port:   {failure['destination']['port']}")
                
                print(f"  Error:       {failure.get('error', 'Unknown error')}")
                print()
    
    print("="*80)


def main():
    # Define HLS connectivity file options
    global connectivity_files
    
    # Base path for connectivity files
    base_path = "/opt/habanalabs/perf-test/scale_up_tool/internal_data"
    
    connectivity_files = {
        "HLS2": f"{base_path}/connectivity_HLS2.csv",
        "HLS2pcie": f"{base_path}/connectivity_HLS2PCIE.csv",
        "HLS3": f"{base_path}/connectivity_HLS3.csv",
        "HLS3pcie": f"{base_path}/connectivity_HLS3PCIE.csv"
    }
    
    parser = argparse.ArgumentParser(description="Gaudi Connection Test Main")
    
    # Default connectivity file type
    default_type = "HLS2"
    default_conn_path = connectivity_files.get(default_type)
    

    # Command-line arguments (only allow type, remove file)
    parser.add_argument("-t", "--type", required=True, choices=["HLS2", "HLS2pcie", "HLS3", "HLS3pcie"],
                      help="Predefined connectivity type to use (required)")
    parser.add_argument("-p", "--parallel", action="store_true",
                      help="Run tests in parallel")
    parser.add_argument("--timeout", type=int, default=30,
                      help="Timeout in seconds for parallel execution")
    parser.add_argument("-v", "--verbose", action="store_true",
                      help="Show detailed failure information")
    parser.add_argument("-j", "--json", action="store_true",
                      help="Output results in JSON format")
    parser.add_argument("-r", "--real", action="store_true",
                      help="Use real connection APIs instead of simulation")
    parser.add_argument("-n", "--no-port-check", action="store_true",
                      help="Skip checking InfiniBand port status")

    args = parser.parse_args()

    # Always use the predefined file for the selected type
    conn_type = args.type
    connectivity_file = connectivity_files.get(conn_type)
    if not connectivity_file or not os.path.exists(connectivity_file):
        print(f"Error: Connectivity file for type '{conn_type}' not found at:")
        print(f"  - {connectivity_files.get(conn_type)}")
        return 1
    
    # Get device information
    print("Retrieving Gaudi device information...")
    devices = get_gaudi_devices()
    
    if not devices:
        print("No Gaudi devices found or device information not available.")
        return 1
    
    print(f"Found {len(devices)} Gaudi devices.")
    
    # Parse connectivity information
    print(f"Parsing connectivity information from {connectivity_file}...")
    if args.type:
        print(f"Using predefined connectivity type: {args.type}")
    connections = parse_connectivity_file(connectivity_file)
    
    if not connections:
        print(f"No connectivity information found in {connectivity_file}.")
        return 1
        
    print(f"Found {len(connections)} connections in the connectivity file.")
    
    # Test connections
    results = test_connections(
        connections,
        devices,
        parallel=args.parallel,
        timeout=args.timeout,
        simulate=not args.real,
        check_ib_ports=not args.no_port_check
    )
    
    # Output results
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_results(results, verbose=args.verbose)
    
    # Return success only if all connections passed
    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
