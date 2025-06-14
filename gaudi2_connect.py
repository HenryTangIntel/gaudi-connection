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

def print_summary(connections: List[Dict[str, int]], module_id: int = None):
    """Print a summary of connections."""
    if module_id is not None:
        filtered = [c for c in connections if 
                   c["source_module_id"] == module_id or 
                   c["destination_module_id"] == module_id]
        print(f"\nGaudi2 Connections for Module {module_id}:")
        connections = filtered
    else:
        print("\nGaudi2 Connections:")
    
    if not connections:
        print("No connections found.")
        return
    
    print("=" * 75)
    print(f"{'Source Module':<15} {'Source Port':<15} {'Destination Module':<20} {'Destination Port':<15}")
    print("-" * 75)
    
    for conn in connections:
        print(f"{conn['source_module_id']:<15} {conn['source_port']:<15} "
              f"{conn['destination_module_id']:<20} {conn['destination_port']:<15}")
    
    print("=" * 75)
    print(f"Total connections: {len(connections)}")

def print_detailed_module_info(connections: List[Dict[str, int]], module_id: int):
    """Print detailed information for a specific module."""
    modules = get_module_connections(connections, module_id)
    
    if module_id not in modules:
        print(f"No connections found for module {module_id}.")
        return
    
    module = modules[module_id]
    
    print(f"\nGaudi2 Module {module_id} Connection Details:")
    print("=" * 75)
    
    # Print outgoing connections
    print(f"\nOutgoing Connections (Module {module_id} → Other Modules):")
    print(f"{'Destination Module':<20} {'Source Port':<15} {'Destination Port':<15}")
    print("-" * 75)
    
    if not module["outgoing"]:
        print("No outgoing connections.")
    else:
        for dst_module, src_port, dst_port in sorted(module["outgoing"]):
            print(f"{dst_module:<20} {src_port:<15} {dst_port:<15}")
    
    # Print incoming connections
    print(f"\nIncoming Connections (Other Modules → Module {module_id}):")
    print(f"{'Source Module':<20} {'Destination Port':<15} {'Source Port':<15}")
    print("-" * 75)
    
    if not module["incoming"]:
        print("No incoming connections.")
    else:
        for src_module, dst_port, src_port in sorted(module["incoming"]):
            print(f"{src_module:<20} {dst_port:<15} {src_port:<15}")

def main():
    # Default path for the connectivity file
    default_path = "/opt/habanalabs/perf-test/scale_up_tool/internal_data/connectivity_HLS2.csv"
    fallback_path = "/workspace/py/test_connectivity.csv"
    
    if not os.path.exists(default_path) and os.path.exists(fallback_path):
        default_path = fallback_path
    
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
    
    # Output based on arguments
    if args.json:
        if args.module is not None and args.detailed:
            modules = get_module_connections(connections, args.module)
            print(json.dumps(modules, indent=2))
        else:
            print(json.dumps(connections, indent=2))
    elif args.detailed and args.module is not None:
        print_detailed_module_info(connections, args.module)
    else:
        print_summary(connections, args.module)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
