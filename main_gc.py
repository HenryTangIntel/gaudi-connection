import os
import json
import argparse
from typing import Dict, List, Tuple, Any, Optional

from src.connectivity.GaudiRouting import GaudiRouting
from src.devices.GaudiDevices import GaudiDevices 
from src.devices.GaudiDeviceFactory import GaudiDeviceFactory
from src.devices.InfinibandDevices import InfinibandDevices
from src.connectivity.RunConnection import RunConnection



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
        runner = RunConnection(args.connectivity)
        connections = runner.make_connections(
            display_output=not args.json,
            verify_connections=args.verify
        )
        
        print("\nTotal connections found:", len(connections))
        
        # Output as JSON if requested
        if args.json:
            if args.output:
                runner.save_to_json(args.output)
            else:
                print(json.dumps(connections, indent=2))
    
    