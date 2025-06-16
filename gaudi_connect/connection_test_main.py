from typing import Dict, List, Tuple, Any, Optional
def test_single_mapped_connection(mapped_conn: Dict[str, Any], devices: Dict[str, Dict[str, Any]], device_objects: Optional[Dict[str, 'GaudiDevice']], use_device_objects: bool, check_ib_ports: bool, simulate: bool, ib_devices: Optional[Dict[str, Any]]) -> Tuple[bool, Dict[str, Any]]:
    conn = mapped_conn['connection']
    src_bus_id = mapped_conn['source_device_id']
    dst_bus_id = mapped_conn['dest_device_id']
    src_port = conn['source_port']
    dst_port = conn['destination_port']
    src_module_id = conn['source_module_id']
    dst_module_id = conn['destination_module_id']
    if use_device_objects and device_objects is not None:
        src_device = device_objects.get(src_bus_id)
        dst_device = device_objects.get(dst_bus_id)
    else:
        src_device = devices.get(src_bus_id)
        dst_device = devices.get(dst_bus_id)
        if src_device:
            src_device = src_device.copy()
            src_device['bus_id'] = src_bus_id
        if dst_device:
            dst_device = dst_device.copy()
            dst_device['bus_id'] = dst_bus_id
    if not src_device:
        return False, {
            "error": f"Source device with bus ID {src_bus_id} (module ID {src_module_id}) not found",
            "connection": conn
        }
    if not dst_device:
        return False, {
            "error": f"Destination device with bus ID {dst_bus_id} (module ID {dst_module_id}) not found",
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
                "bus_id": src_bus_id,
                "port": src_port
            },
            "destination": {
                "module_id": dst_module_id,
                "bus_id": dst_bus_id,
                "port": dst_port
            }
        }
        if "port check failed" in message:
            failure_info["failure_type"] = "inactive_port"
        return False, failure_info
    return True, {"message": message}
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
import concurrent.futures
from typing import Dict, List, Tuple, Any, Optional

from gaudi_connect.devices.GaudiDevices import GaudiDevices, GaudiDevice
from gaudi_connect.devices.InfinibandDevices import InfinibandDevices
from gaudi_connect.connectivity.GaudiRouting import GaudiRouting












def connect_devices(source_device: Dict[str, Any], source_port: int,
                  dest_device: Dict[str, Any], dest_port: int,
                  ib_devices: Dict[str, Dict[str, Any]] = None,
                  simulate: bool = True) -> Tuple[bool, str]:
    """
    Connect two Gaudi devices, checking port status first.
    This function handles both GaudiDevice objects and dictionaries.
    
    Args:
        source_device: Source device information (dict or GaudiDevice)
        source_port: Port on the source device
        dest_device: Destination device information (dict or GaudiDevice)
        dest_port: Port on the destination device
        ib_devices: Dictionary of InfiniBand devices with port information
        simulate: Whether to simulate connection (True) or use real API (False)
        
    Returns:
        Tuple of (success, message)
    """
    # Convert GaudiDevice objects to dictionaries if needed
    if isinstance(source_device, GaudiDevice):
        src_module_id = source_device.module_id
        src_bus_id = source_device.bus_id
        src_vendor_id = source_device.vendor_id
        # Check port status directly through GaudiDevice
        src_active = source_device.is_port_active(source_port)
        src_status = source_device.get_port_status(source_port)
    else:  # Dictionary
        src_module_id = source_device.get('module_id')
        src_bus_id = source_device.get('bus_id')
        src_vendor_id = source_device.get('vendor_id', 'unknown')
        if src_vendor_id is None:
            src_vendor_id = 'unknown'
        src_active = None  # Will check later if needed
        src_status = None
        
    if isinstance(dest_device, GaudiDevice):
        dst_module_id = dest_device.module_id
        dst_bus_id = dest_device.bus_id
        dst_vendor_id = dest_device.vendor_id
        # Check port status directly through GaudiDevice
        dst_active = dest_device.is_port_active(dest_port)
        dst_status = dest_device.get_port_status(dest_port)
    else:  # Dictionary
        dst_module_id = dest_device.get('module_id')
        dst_bus_id = dest_device.get('bus_id')
        dst_vendor_id = dest_device.get('vendor_id', 'unknown')
        if dst_vendor_id is None:
            dst_vendor_id = 'unknown'
        dst_active = None  # Will check later if needed
        dst_status = None
    
    print(f"Connecting module {src_module_id}:{source_port} to module {dst_module_id}:{dest_port}")
    print(f"  Bus IDs: {src_bus_id} -> {dst_bus_id}")

    # Only check port status if ib_devices is provided
    if ib_devices:
        if src_active is None:
            ib_device = InfinibandDevices()
            src_active, src_status = ib_device.check_port_status(src_bus_id, source_port, ib_devices)
        if dst_active is None:
            ib_device = InfinibandDevices() if not 'ib_device' in locals() else ib_device
            dst_active, dst_status = ib_device.check_port_status(dst_bus_id, dest_port, ib_devices)
        if not src_active:
            return False, f"Source port check failed: {src_status}"
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



def test_mapped_connections(mapped_connections: List[Dict[str, Any]],
                     devices: Dict[str, Dict[str, Any]],
                     parallel: bool = False,
                     timeout: int = 30,
                     simulate: bool = True,
                     check_ib_ports: bool = True,
                     use_device_objects: bool = True,
                     device_objects: Optional[Dict[str, 'GaudiDevice']] = None) -> Dict[str, Any]:
    """
    Test connections that have been pre-mapped to devices by GaudiRouting.
    """
    results = {
        "total_connections": len(mapped_connections),
        "successful": 0,
        "failed": 0,
        "skipped": 0,
        "inactive_ports": 0,
        "failures": [],
        "success_rate": 0.0
    }
    if not mapped_connections:
        print("No valid connections to test.")
        return results
    ib_devices = None
    if check_ib_ports:
        print("Retrieving InfiniBand device information for port status check...")
        try:
            ib_device = InfinibandDevices()
            ib_result = ib_device.get_infiniband_devices(include_details=True)
            if not ib_result or (not ib_result.get('gaudi') and not ib_result.get('other')):
                print("Warning: No InfiniBand devices found, port status check will be skipped.")
                ib_devices = {}
            else:
                print(f"Found {len(ib_result.get('gaudi', []))} Gaudi devices and {len(ib_result.get('other', []))} other devices")
                ib_devices = {}
                for dev in ib_result.get('gaudi', []):
                    ib_devices[dev['pci_bus_id']] = dev
                for dev in ib_result.get('other', []):
                    ib_devices[dev['pci_bus_id']] = dev
        except Exception as e:
            print(f"Warning: Error retrieving InfiniBand device information: {e}")
            print("Port status check will be skipped.")
    print(f"Testing {len(mapped_connections)} connections between Gaudi devices...")
    if parallel:
        print("Running connection tests in parallel...")
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(test_single_mapped_connection, conn, devices, device_objects, use_device_objects, check_ib_ports, simulate, ib_devices) for conn in mapped_connections]
            for future in concurrent.futures.as_completed(futures, timeout=timeout):
                try:
                    success, result = future.result()
                    if success:
                        results["successful"] += 1
                    else:
                        results["failed"] += 1
                        results["failures"].append(result)
                        if result.get("failure_type") == "inactive_port":
                            results["inactive_ports"] += 1
                except Exception as e:
                    results["failed"] += 1
                    results["failures"].append({
                        "error": f"Test execution error: {str(e)}"
                    })
    else:
        print("Running connection tests sequentially...")
        for i, conn in enumerate(mapped_connections):
            print(f"Testing connection {i+1}/{len(mapped_connections)}...")
            success, result = test_single_mapped_connection(conn, devices, device_objects, use_device_objects, check_ib_ports, simulate, ib_devices)
            if success:
                results["successful"] += 1
            else:
                results["failed"] += 1
                results["failures"].append(result)
                if result.get("failure_type") == "inactive_port":
                    results["inactive_ports"] += 1
    if results["total_connections"] > 0:
        results["success_rate"] = (results["successful"] / results["total_connections"]) * 100.0
    return results



def main():
    """
    Redesigned main entry point for Gaudi Connection Test.
    Loads device and connectivity info, maps connections, and tests only valid connections.
    """
    base_path = "/opt/habanalabs/perf-test/scale_up_tool/internal_data"
    connectivity_files = {
        "HLS2": f"{base_path}/connectivity_HLS2.csv",
        "HLS2pcie": f"{base_path}/connectivity_HLS2PCIE.csv",
        "HLS3": f"{base_path}/connectivity_HLS3.csv",
        "HLS3pcie": f"{base_path}/connectivity_HLS3PCIE.csv"
    }

    parser = argparse.ArgumentParser(description="Test Gaudi device connections as defined in a connectivity file.")
    parser.add_argument("-t", "--type", required=True, choices=list(connectivity_files.keys()), help="Connectivity type to use (required)")
    parser.add_argument("-p", "--parallel", action="store_true", help="Run tests in parallel")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds for parallel execution")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed failure information")
    parser.add_argument("-j", "--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("-r", "--real", action="store_true", help="Use real connection APIs instead of simulation")
    parser.add_argument("-n", "--no-port-check", action="store_true", help="Skip checking InfiniBand port status")

    args = parser.parse_args()
    conn_type = args.type
    connectivity_file = connectivity_files.get(conn_type)
    if not connectivity_file or not os.path.exists(connectivity_file):
        print(f"[ERROR] Connectivity file for type '{conn_type}' not found at: {connectivity_file}")
        return 1

    print("[INFO] Loading Gaudi device information...")
    gaudi_device = GaudiDevices()
    devices = gaudi_device.get_gaudi_devices()
    if not devices:
        print("[ERROR] No Gaudi devices found or device information not available.")
        return 1
    print(f"[INFO] Found {len(devices)} Gaudi devices.")

    print(f"[INFO] Loading connectivity info from {connectivity_file}...")
    router = GaudiRouting(connectivity_file)
    connections = router.parse_connectivity_file()
    if not connections:
        print(f"[ERROR] No connectivity information found in {connectivity_file}.")
        return 1
    print(f"[INFO] Found {len(connections)} connections in the connectivity file.")

    print("[INFO] Mapping connections to available devices...")
    mapped_connections = router.match_devices_to_connections(devices)
    print(f"[INFO] {len(mapped_connections)} valid mapped connections will be tested.")

    print("[INFO] Creating GaudiDevice objects (with InfiniBand info if enabled)...")
    device_objects = gaudi_device.get_device_objects(include_infiniband=not args.no_port_check)

    print("[INFO] Starting connection tests...")
    results = test_mapped_connections(
        mapped_connections,
        devices,
        parallel=args.parallel,
        timeout=args.timeout,
        simulate=not args.real,
        check_ib_ports=not args.no_port_check,
        use_device_objects=True,
        device_objects=device_objects
    )

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_results(results, verbose=args.verbose)

    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    print("Starting Gaudi Connection Test")
    try:
        exit_code = main()
        print(f"Exiting with code {exit_code}")
        sys.exit(exit_code)
    except Exception as e:
        import traceback
        print(f"Error in main: {e}")
        traceback.print_exc()
        sys.exit(1)
