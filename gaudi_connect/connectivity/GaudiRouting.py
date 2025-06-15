#!/usr/bin/env python3
"""
Gaudi2 Connectivity Parser

This script extracts connectivity information from the Gaudi2 connectivity CSV file.
"""

import os
import sys
import csv
import json
import argparse
from typing import List, Dict, Tuple, Any, Optional

class GaudiRouting:
    """
    Class for handling Gaudi2 routing and connectivity information.
    Provides utilities to parse connectivity files and analyze connection patterns.
    """
    
    def __init__(self, connectivity_file: Optional[str] = None):
        """
        Initialize the GaudiRouting class.
        
        Args:
            connectivity_file: Path to the connectivity CSV file. If None, will use the default path.
        """
        self.default_path = "/opt/habanalabs/perf-test/scale_up_tool/internal_data/connectivity_HLS2.csv"
        self.connectivity_file = connectivity_file or self.default_path
        self.connections = []
    
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
            print(f"Error: File '{csv_path}' does not exist.")
            return []
        
        connections = []
        
        try:
            with open(csv_path, 'r') as f:
                # Skip comment lines
                lines = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
                
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 4:
                        try:
                            connection = {
                                "source_module_id": int(parts[0]),
                                "source_port": int(parts[1]),
                                "destination_module_id": int(parts[2]),
                                "destination_port": int(parts[3])
                            }
                            connections.append(connection)
                        except (ValueError, IndexError):
                            continue
        except Exception as e:
            print(f"Error reading file: {e}")
        
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
            src_module = conn["source_module_id"]
            src_port = conn["source_port"]
            dst_module = conn["destination_module_id"]
            dst_port = conn["destination_port"]
            
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
