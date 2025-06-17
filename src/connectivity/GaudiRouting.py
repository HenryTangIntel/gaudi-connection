#!/usr/bin/env python3
"""
Gaudi2 Connectivity Parser

This script extracts connectivity information from the Gaudi2 connectivity CSV file.
"""

import os
from typing import List, Dict, Tuple, Any, Optional
import csv 

class GaudiRouting:
    """
    Class for handling Gaudi2 routing and connectivity information.
    Provides utilities to parse connectivity files and analyze connection patterns.
    """
    
    def __init__(self, connectivity_file: Optional[str] = None):
        """
        Initialize the GaudiRouting class and parse the connectivity file.
        
        Args:
            connectivity_file: Path to the connectivity CSV file. If None, will use the default path.
        """
        self.default_path = "/opt/habanalabs/perf-test/scale_up_tool/internal_data/connectivity_HLS2.csv"
        # Fallback to local file if the system file is not available
        if not os.path.exists(self.default_path):
            self.default_path = "./connectivity_HLS2.csv"
        self.connectivity_file = connectivity_file or self.default_path
        self.connections = []
        
        # Parse the connectivity file during initialization
        self.parse_connectivity_file()
    
    def parse_connectivity_file(self, csv_path: Optional[str] = None) -> List[Dict[str, int]]:
        """
        Parse the Gaudi2 connectivity CSV file and return a list of connections.
        
        Args:
            csv_path: Path to the connectivity CSV file. If None, uses the path provided during initialization.
            
        Returns:
            List of dictionaries, each containing:
                - source_module_id: ID of the source module
                - source_port: Port number on the source module
                - destination_module_id: ID of the destination module
                - destination_port: Port number on the destination module
        """
        csv_path = csv_path or self.connectivity_file
        
        if not os.path.exists(csv_path):
            print(f"Warning: Connectivity file '{csv_path}' does not exist.")
            return []
        
        connections = []
        valid_connections = 0
        total_lines = 0
        
        try:
            with open(csv_path, 'r') as f:
                csv_reader = csv.reader(f, delimiter='\t', skipinitialspace=True)
                
                # Process each row in the CSV file
                for row_idx, row in enumerate(csv_reader, 1):
                    total_lines += 1
                    
                    # Skip empty rows and comments
                    if not row or (len(row) > 0 and row[0].startswith('#')):
                        continue
                    
                    # Filter out empty strings that might appear due to extra spaces
                    row = [item for item in row if item]
                    
                    if len(row) >= 4:
                        try:
                            connection = {
                                "source": {
                                   "module_id": int(row[0]),
                                   "port": int(row[1])
                                },
                                "destination": {
                                   "module_id": int(row[2]),
                                   "port": int(row[3])
                                },
                            }
                            connections.append(connection)
                            valid_connections += 1
                        except (ValueError, IndexError) as e:
                            print(f"Warning: Invalid connection format at line {row_idx}: {row} - {str(e)}")
                            continue
                    else:
                        print(f"Warning: Skipping line {row_idx} with insufficient data: {row}")
        except Exception as e:
            print(f"Error reading connectivity file '{csv_path}': {e}")
        
        if valid_connections > 0:
            print(f"Successfully parsed {valid_connections} connections from {total_lines} lines in '{csv_path}'")
        else:
            print(f"No valid connections found in '{csv_path}'")
        
        self.connections = connections
        return connections
    
    def get_module_connections(self, connections: Optional[List[Dict[str, int]]] = None, 
                              module_id: Optional[int] = None) -> Dict[int, Dict[str, List[Tuple[int, int, int]]]]:
        """
        Organize connections by module.
        
        Args:
            connections: List of connection dictionaries. If None, uses the connections parsed previously.
            module_id: Optional module ID to filter by
            
        Returns:
            Dictionary with module IDs as keys, and dictionaries with 'outgoing' and 'incoming'
            lists as values.
        """
        connections = connections or self.connections
        modules = {}
        
        for conn in connections:
            src_module = conn["source"]["module_id"]
            src_port = conn["source"]["port"]
            dst_module = conn["destination"]["module_id"]
            dst_port = conn["destination"]["port"]
            
            # Filter by module ID if specified
            if module_id is not None and src_module != module_id and dst_module != module_id:
                continue
            
            # Initialize module entries if they don't exist
            if src_module not in modules:
                modules[src_module] = {"outgoing": [], "incoming": []}
            if dst_module not in modules:
                modules[dst_module] = {"outgoing": [], "incoming": []}
            
            # Add to outgoing and incoming lists
            modules[src_module]["outgoing"].append((dst_module, src_port, dst_port))
            modules[dst_module]["incoming"].append((src_module, dst_port, src_port))
        
        return modules
    
    def match_devices_to_connections(self, devices: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Match the actual devices to the connectivity information.
        
        This function takes the available devices (with module IDs) and matches them
        with the connections defined in the connectivity file, ensuring that only
        connections with both devices available are included.
        
        Args:
            devices: Dictionary of devices keyed by bus ID with device information
                    Each device should have a 'module_id' field
        
        Returns:
            List of dictionaries containing:
                - source: Dictionary with module_id and port
                - destination: Dictionary with module_id and port
                - source_device_id: Bus ID of the source device
                - dest_device_id: Bus ID of the destination device
        """
        if not self.connections:
            print("No connections defined. Call parse_connectivity_file() first.")
            return []
        
        # Create a mapping from module ID to device bus ID
        module_to_bus_id = {}
        for bus_id, device in devices.items():
            if 'module_id' in device and device['module_id'] is not None:
                module_to_bus_id[device['module_id']] = bus_id
        
        # Match connections to actual devices
        matched_connections = []
        for conn in self.connections:
            src_module_id = conn['source']['module_id']
            src_port = conn['source']['port']
            dst_module_id = conn['destination']['module_id']
            dst_port = conn['destination']['port']
            
            # Skip connections between same module
            if src_module_id == dst_module_id:
                continue
            
            # Check if we have both source and destination devices
            if src_module_id in module_to_bus_id and dst_module_id in module_to_bus_id:
                matched_conn = {
                    'source': {
                        'module_id': src_module_id,
                        'port': src_port
                    },
                    'destination': {
                        'module_id': dst_module_id,
                        'port': dst_port
                    },
                    'source_device_id': module_to_bus_id[src_module_id],
                    'dest_device_id': module_to_bus_id[dst_module_id]
                }
                matched_connections.append(matched_conn)
        
        return matched_connections
