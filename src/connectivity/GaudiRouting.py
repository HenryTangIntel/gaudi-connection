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
        
        if self.connections:
            print("Connectivity already parsed. Returning cached connections.")
            return self.connections
        
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
    
    def get_connections(self) -> List[Dict[str, int]]:
        """
        Get the parsed connections.
        
        Returns:
            List of dictionaries containing connection information.
        """
        if not self.connections:
            print("No connections parsed yet. Parsing connectivity file...")
            self.parse_connectivity_file()
        return self.connections

if __name__ == "__main__":
    # Test program for GaudiRouting
    print("Testing GaudiRouting connectivity parser...")
    routing = GaudiRouting()
    connections = routing.parse_connectivity_file()
    print(f"Total connections parsed: {len(connections)}")
    # Print first 3 connections as a sample
    for idx, conn in enumerate(connections[:3]):
        print(f"Connection {idx+1}: {conn}")

