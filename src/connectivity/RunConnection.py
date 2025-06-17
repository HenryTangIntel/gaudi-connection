import os
import json
import argparse
from typing import Dict, List, Tuple, Any, Optional

from src.connectivity.GaudiRouting import GaudiRouting
from src.devices.GaudiDevices import GaudiDevices 
from src.devices.GaudiDeviceFactory import GaudiDeviceFactory
from src.devices.InfinibandDevices import InfinibandDevices


class RunConnection:
    """
    Class for handling and displaying connection information between Gaudi devices.
    """
    
    def __init__(self, connectivity_file: Optional[str] = None):
        """
        Initialize RunConnection with optional connectivity file.
        
        Args:
            connectivity_file: Path to the connectivity CSV file. If None, uses the default path.
        """
        self.connectivity_file = connectivity_file
        self.factory = GaudiDeviceFactory()
        self.routing = GaudiRouting(connectivity_file)
        self.connections = []

    def make_connections(self, display_output: bool = True, 
                        verify_connections: bool = True) -> List[Dict[str, Any]]:
        """
        Establishes connections between Gaudi devices based on routing information.
        
        Args:
            display_output: Whether to print connection details to console.
            verify_connections: Whether to verify that the connections are valid.
            
        Returns:
            List of dictionaries containing connection details.
        """
        # Get all devices by module ID and parse connectivity file
        devices_by_module = self.factory.get_devices_by_module_id()
        
        # Get active ports for each device
        active_ports = self.factory.get_active_ports()
        
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
        matched_connections = self.routing.match_devices_to_connections(device_dicts)
        
        # Process and validate each connection
        for matched in matched_connections:
            src_module_id = matched['source']['module_id']
            src_port = matched['source']['port']
            dst_module_id = matched['destination']['module_id']
            dst_port = matched['destination']['port']
            
            src_bus_id = matched['source_device_id']
            dst_bus_id = matched['dest_device_id']
            
            # Get the actual device objects
            src_device = self.factory.get_device_by_bus_id(src_bus_id)
            dst_device = self.factory.get_device_by_bus_id(dst_bus_id)
            
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
        
        self.connections = connections
        return connections

    def display_connections(self, connections: List[Dict[str, Any]] = None) -> None:
        """
        Display formatted output for the specified connections.
        
        Args:
            connections: List of connection dictionaries. If None, uses stored connections.
        """
        if connections is None:
            connections = self.connections
            
        if not connections:
            print("No connections to display. Run make_connections() first.")
            return
            
        for conn in connections:
            print(f"Connection: {conn['source']['ib_name']}:port{conn['source']['port']} -> {conn['destination']['ib_name']}:port{conn['destination']['port']}")
            print(f"  Source: Module {conn['source']['module_id']}, Bus ID {conn['source']['bus_id']}")
            if conn['source']['gid']:
                print(f"    GID: {conn['source']['gid']}")
            print(f"  Destination: Module {conn['destination']['module_id']}, Bus ID {conn['destination']['bus_id']}")
            if conn['destination']['gid']:
                print(f"    GID: {conn['destination']['gid']}")
            print()
    
    def filter_by_module_id(self, module_id: int, as_source: bool = True, as_destination: bool = True) -> List[Dict[str, Any]]:
        """
        Filter connections by module ID as source, destination, or both.
        
        Args:
            module_id: The module ID to filter by
            as_source: Include connections where the module is the source
            as_destination: Include connections where the module is the destination
            
        Returns:
            List of filtered connections
        """
        if not self.connections:
            self.make_connections(display_output=False)
            
        filtered = []
        for conn in self.connections:
            if as_source and conn['source']['module_id'] == module_id:
                filtered.append(conn)
            elif as_destination and conn['destination']['module_id'] == module_id:
                filtered.append(conn)
                
        return filtered
    
    def filter_by_port(self, port: int, as_source: bool = True, as_destination: bool = True) -> List[Dict[str, Any]]:
        """
        Filter connections by port number as source, destination, or both.
        
        Args:
            port: The port number to filter by
            as_source: Include connections where the port is the source
            as_destination: Include connections where the port is the destination
            
        Returns:
            List of filtered connections
        """
        if not self.connections:
            self.make_connections(display_output=False)
            
        filtered = []
        for conn in self.connections:
            if as_source and conn['source']['port'] == port:
                filtered.append(conn)
            elif as_destination and conn['destination']['port'] == port:
                filtered.append(conn)
                
        return filtered
    
    def get_connections_between(self, src_module_id: int, dst_module_id: int) -> List[Dict[str, Any]]:
        """
        Get connections between two specific modules.
        
        Args:
            src_module_id: Source module ID
            dst_module_id: Destination module ID
            
        Returns:
            List of connections between the specified modules
        """
        if not self.connections:
            self.make_connections(display_output=False)
            
        return [conn for conn in self.connections if 
                (conn['source']['module_id'] == src_module_id and conn['destination']['module_id'] == dst_module_id) or
                (conn['source']['module_id'] == dst_module_id and conn['destination']['module_id'] == src_module_id)]
    
    def save_to_json(self, filename: str) -> None:
        """
        Save the connections to a JSON file.
        
        Args:
            filename: The name of the file to save to
        """
        if not self.connections:
            print("No connections to save. Run make_connections() first.")
            return
            
        with open(filename, 'w') as f:
            json.dump(self.connections, f, indent=2)
            
        print(f"Saved {len(self.connections)} connections to {filename}")


# Example usage when run as a script
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Gaudi Connections")
    parser.add_argument("-c", "--connectivity", help="Path to connectivity CSV file")
    parser.add_argument("-m", "--module", type=int, help="Filter by module ID")
    parser.add_argument("-p", "--port", type=int, help="Filter by port number")
    parser.add_argument("-o", "--output", help="Output file for JSON results")
    
    args = parser.parse_args()
    
    runner = RunConnection(args.connectivity)
    connections = runner.make_connections(display_output=True)
    
    if args.output:
        runner.save_to_json(args.output)