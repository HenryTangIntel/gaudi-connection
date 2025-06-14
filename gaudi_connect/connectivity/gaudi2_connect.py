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
from typing import List, Dict, Tuple, Any

def parse_connectivity_file(csv_path: str) -> List[Dict[str, int]]:
    """
    Parse the Gaudi2 connectivity CSV file and return a list of connections.
    
    Args:
        csv_path: Path to the connectivity CSV file
        
    Returns:
        List of dictionaries, each containing:
            - source_module_id: ID of the source module
            - source_port: Port number on the source module
            - destination_module_id: ID of the destination module
            - destination_port: Port number on the destination module
    """
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
        
    return connections

def get_module_connections(connections: List[Dict[str, int]], module_id: int = None) -> Dict[int, Dict[str, List[Tuple[int, int, int]]]]:
    """
    Organize connections by module.
    
    Args:
        connections: List of connection dictionaries
        module_id: Optional module ID to filter by
        
    Returns:
        Dictionary with module IDs as keys, and dictionaries with 'outgoing' and 'incoming'
        lists as values.
    """
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

def main():
    # Default path for the connectivity file
    default_path = "/opt/habanalabs/perf-test/scale_up_tool/internal_data/connectivity_HLS2.csv"
    
    parser = argparse.ArgumentParser(description="Gaudi2 Connectivity Information Tool")
    parser.add_argument("-f", "--file", default=default_path,
                        help="Path to the connectivity CSV file")
    parser.add_argument("-m", "--module", type=int, 
                        help="Show connections for a specific module ID")
    parser.add_argument("-j", "--json", action="store_true",
                        help="Output in JSON format")
    parser.add_argument("-d", "--detailed", action="store_true",
                        help="Show detailed connection information")
    
    args = parser.parse_args()
    
    # Parse the connectivity file
    connections = parse_connectivity_file(args.file)
    
    if not connections:
        print("No connections found in the specified file.")
        return 1
    
    # Output in JSON if requested
    if args.json:
        print(json.dumps(connections, indent=2))
    else:
        # Print a simple summary
        if args.module is not None:
            connections = [c for c in connections if 
                        c["source_module_id"] == args.module or 
                        c["destination_module_id"] == args.module]
            print(f"Connections for module {args.module}:")
        else:
            print("All connections:")
            
        print(f"{'Source Module':<15} {'Source Port':<15} {'Destination Module':<15} {'Destination Port':<15}")
        print("-" * 60)
        
        for conn in connections:
            print(f"{conn['source_module_id']:<15} {conn['source_port']:<15} "
                f"{conn['destination_module_id']:<15} {conn['destination_port']:<15}")
        
        print(f"Total: {len(connections)} connections")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
