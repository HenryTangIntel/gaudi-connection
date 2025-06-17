import os
import json
import argparse
from typing import Dict, List, Tuple, Any, Optional

from src.connectivity.GaudiRouting import GaudiRouting
from src.devices.GaudiDevices import GaudiDevices 
from src.devices.GaudiDeviceFactory import GaudiDeviceFactory
from src.devices.InfinibandDevices import InfinibandDevices


def make_connections(connectivity_file: Optional[str] = None, 
                    display_output: bool = True, 
                    verify_connections: bool = True) -> List[Dict[str, Any]]:
    """
    Establishes connections between Gaudi devices based on routing information.
    
    Args:
        connectivity_file: Path to the connectivity CSV file. If None, uses the default path.
        display_output: Whether to print connection details to console.
        verify_connections: Whether to verify that the connections are valid.
        
    Returns:
        List of dictionaries containing connection details.
    """
    # Initialize the device factory and routing
    factory = GaudiDeviceFactory()
    routing = GaudiRouting(connectivity_file)
    
    # Get all devices by module ID and parse connectivity file
    devices_by_module = factory.get_devices_by_module_id()
    
    # Get active ports for each device
    active_ports = factory.get_active_ports()
    
    # Match devices to connections from the connectivity file
    connections = []
    
    # Convert GaudiDevice objects to dictionaries for matching
    device_dicts = {}
    for module_id, device in devices_by_module.items():
        device_dicts[device.bus_id] = {
            'module_id': module_id,
            'bus_id': device.bus_id,
            'ib_name': device.ib_name,
            'device_id': device.device_id
        }
    
    # Get matched connections
    matched_connections = routing.match_devices_to_connections(device_dicts)
    
    # Process and validate each connection
    for matched in matched_connections:
        src_module_id = matched['source']['module_id']
        src_port = matched['source']['port']
        dst_module_id = matched['destination']['module_id']
        dst_port = matched['destination']['port']
        
        src_bus_id = matched['source_device_id']
        dst_bus_id = matched['dest_device_id']
        
        # Get the actual device objects
        src_device = factory.get_device_by_bus_id(src_bus_id)
        dst_device = factory.get_device_by_bus_id(dst_bus_id)
        
        if not src_device or not dst_device:
            continue
        
        # Check if the required ports are active if verification is enabled
        if verify_connections:
            if src_bus_id not in active_ports or dst_bus_id not in active_ports:
                continue
                
            if src_port not in active_ports[src_bus_id] or dst_port not in active_ports[dst_bus_id]:
                continue
        
        # Create connection record with GID information
        # Get source port GID
        src_port_gid = None
        if src_port in src_device.ports:
            src_port_gid = src_device.ports[src_port].get('gid')
        
        # Get destination port GID
        dst_port_gid = None
        if dst_port in dst_device.ports:
            dst_port_gid = dst_device.ports[dst_port].get('gid')
            
        connection_record = {
            'source': {
                'module_id': src_module_id,
                'port': src_port,
                'bus_id': src_bus_id,
                'ib_name': src_device.ib_name,
                'gid': src_port_gid
            },
            'destination': {
                'module_id': dst_module_id,
                'port': dst_port,
                'bus_id': dst_bus_id,
                'ib_name': dst_device.ib_name,
                'gid': dst_port_gid
            }
        }
        
        connections.append(connection_record)
        
        # Display connection information if requested
        if display_output:
            print(f"Connection: {src_device.ib_name}:port{src_port} -> {dst_device.ib_name}:port{dst_port}")
            print(f"  Source: Module {src_module_id}, Bus ID {src_bus_id}")
            if src_port_gid:
                print(f"    GID: {src_port_gid}")
            print(f"  Destination: Module {dst_module_id}, Bus ID {dst_bus_id}")
            if dst_port_gid:
                print(f"    GID: {dst_port_gid}")
            print()
    
    return connections


# Create device factory instance and print device summary
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gaudi Connection Tool")
    parser.add_argument("-c", "--connectivity", help="Path to connectivity CSV file")
    parser.add_argument("-d", "--devices", action="store_true", help="Show device summary")
    parser.add_argument("-r", "--routes", action="store_true", help="Show routing connections")
    parser.add_argument("-j", "--json", action="store_true", help="Output in JSON format")
    parser.add_argument("-v", "--verify", action="store_true", help="Verify connections have active ports")
    parser.add_argument("-o", "--output", help="Output file for connection data (JSON format)")
    
    args = parser.parse_args()
    
    factory = GaudiDeviceFactory()
    
    # Show device summary if requested or if no specific action is requested
    if args.devices or not (args.routes or args.json):
        factory.print_device_summary()
    
    # Show routing information if requested
    if args.routes:
        connections = make_connections(
            connectivity_file=args.connectivity,
            display_output=not args.json,
            verify_connections=args.verify
        )
        
        # Output as JSON if requested
        if args.json:
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(connections, f, indent=2)
            else:
                print(json.dumps(connections, indent=2))
    
    