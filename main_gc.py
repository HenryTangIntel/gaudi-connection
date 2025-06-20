import os
import json
import argparse
import sys
import asyncio
import time
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))
from connection import GaudiDevices, GaudiRouting, connection, print_connection_pairs, print_gaudi_device_mapping, verify_connections_vs_csv
from runner.AsyncPerfRunner import AsyncPerfRunner, PerfTestRequest, run_connection_tests_async


def RealRunConnectionAsync(connections):
    """
    Executes performance tests asynchronously on all the provided connections.
    
    Args:
        connections: List of (src_device, src_port, dst_device, dst_port) tuples
        
    Returns:
        Dict with summary and detailed results for each connection
    """
    print(f"\nRunning asynchronous performance tests on {len(connections)} connections...")
    
    # Run the async function
    results = asyncio.run(
        run_connection_tests_async(
            connections,
            max_concurrent=5,  # Adjust based on system capacity
            test_params={
                'test_type': 'pp',
                'size': 4096,
                'iterations': 1000,
                'timeout': 300
            }
        )
    )
    
    # Print summary
    print("\n" + "="*50)
    print("PERFORMANCE TEST SUMMARY")
    print("="*50)
    print(f"Total connections: {results['summary']['total']}")
    print(f"Tests submitted: {results['summary']['submitted']}")
    print(f"Tests completed: {results['summary']['completed']}")
    print(f"Successful tests: {results['summary']['success']}")
    print(f"Failed tests: {results['summary']['failed']}")
    print(f"Timeout tests: {results['summary']['timeout']}")
    print(f"Error tests: {results['summary']['error']}")
    print("="*50)
    
    return results


def RealRunConnectionDryRun(connections):
    """
    Performs a dry run - prints the commands that would be executed without actually running them.
    
    Args:
        connections: List of (src_device, src_port, dst_device, dst_port) tuples
        
    Returns:
        Dict with dry run information
    """
    print(f"\nDRY RUN: Performance test commands for {len(connections)} connections")
    print("="*70)
    
    commands = []
    perf_test = "/opt/habanalabs/perf-test/perf_test"
    
    for i, (src, src_port, dst, dst_port) in enumerate(connections):
        print(f"\nConnection {i+1}/{len(connections)}")
        
        if not src or not dst:
            print("Error: Connection missing source or destination device")
            continue
            
        src_ib_name = getattr(src, 'ib_name', 'Unknown')
        dst_ib_name = getattr(dst, 'ib_name', 'Unknown')
        
        # Get GID information
        def get_gid(device, port):
            if hasattr(device, 'ports') and isinstance(device.ports, dict):
                port_info = device.ports.get(port)
                if port_info:
                    return port_info.get('gid')
            return None
        
        src_gid = get_gid(src, src_port)
        dst_gid = get_gid(dst, dst_port)
        
        print(f"  Source: {src_ib_name}:port{src_port} (GID: {src_gid or 'N/A'})")
        print(f"  Destination: {dst_ib_name}:port{dst_port} (GID: {dst_gid or 'N/A'})")
        
        # Build server command
        server_cmd = [
            perf_test,
            "-d", src_ib_name,
            "-i", str(src_port),
            "-g", "0",
            "-t", "pp",
            "-s", "4096",
            "-n", "1000"
        ]
        
        # Build client command
        client_cmd = [
            perf_test,
            "-d", dst_ib_name,
            "-i", str(dst_port),
            "-g", "0",
            "-t", "pp",
            "-s", "4096",
            "-n", "1000",
            "127.0.0.1"
        ]
        
        print(f"  Server command: {' '.join(server_cmd)}")
        print(f"  Client command: {' '.join(client_cmd)}")
        
        commands.append({
            'connection': i + 1,
            'source': f"{src_ib_name}:port{src_port}",
            'destination': f"{dst_ib_name}:port{dst_port}",
            'server_cmd': ' '.join(server_cmd),
            'client_cmd': ' '.join(client_cmd)
        })
    
    print("\n" + "="*70)
    print(f"Total commands to execute: {len(commands) * 2} ({len(commands)} server + {len(commands)} client)")
    
    return {
        'total_connections': len(connections),
        'valid_commands': len(commands),
        'commands': commands
    }


def main():
    """
    Main entry point for the Gaudi Connection Tool with async performance testing.
    """
    parser = argparse.ArgumentParser(description="Gaudi Connection Tool with Async Performance Testing")
    parser.add_argument("-c", "--connectivity", default="/opt/habanalabs/perf-test/scale_up_tool/internal_data/connectivity_HLS2.csv", 
                       help="Path to connectivity CSV file")
    parser.add_argument("-d", "--devices", action="store_true", help="Show device summary")
    parser.add_argument("-r", "--routes", action="store_true", help="Show routing connections")
    parser.add_argument("-j", "--json", action="store_true", help="Output connection pairs in JSON format")
    parser.add_argument("-v", "--verify", action="store_true", help="Verify connections vs CSV")
    parser.add_argument("-o", "--output", help="Output file for connection data (JSON format)")
    parser.add_argument("-p", "--perf", action="store_true", help="Run performance tests on connections")
    parser.add_argument("--dry-run", action="store_true", help="Show commands without executing (dry run)")
    parser.add_argument("--max-concurrent", type=int, default=5, help="Maximum concurrent tests (default: 5)")
    
    args = parser.parse_args()

    # Check if local CSV should be used as fallback
    if not os.path.exists(args.connectivity):
        local_csv = "./connectivity_HLS2.csv"
        if os.path.exists(local_csv):
            print(f"Warning: {args.connectivity} not found, using local file: {local_csv}")
            args.connectivity = local_csv
        else:
            print(f"Error: Connectivity file not found: {args.connectivity}")
            sys.exit(1)

    gaudidevices = GaudiDevices()
    connectivity = GaudiRouting(args.connectivity)

    # Show device summary if requested or if no specific action is requested
    if args.devices or not (args.routes or args.json):
        print_gaudi_device_mapping(gaudidevices)

    # Show routing information if requested
    if args.routes or args.json:
        con = connection(gaudidevices, connectivity)
        
        if args.json:
            # Output connection pairs as JSON
            json_pairs = [
                {
                    "src": {
                        "module_id": src.module_id if src else None,
                        "device_id": src.device_id if src else None,
                        "ib_name": src.ib_name if src else None,
                        "port": src_port,
                        "gid": src.ports.get(src_port, {}).get('gid') if src and hasattr(src, 'ports') else None
                    },
                    "dst": {
                        "module_id": dst.module_id if dst else None,
                        "device_id": dst.device_id if dst else None,
                        "ib_name": dst.ib_name if dst else None,
                        "port": dst_port,
                        "gid": dst.ports.get(dst_port, {}).get('gid') if dst and hasattr(dst, 'ports') else None
                    }
                }
                for src, src_port, dst, dst_port in con
            ]
            
            if args.output and not args.perf:
                with open(args.output, 'w') as f:
                    json.dump(json_pairs, f, indent=2)
                print(f"Connection pairs saved to {args.output}")
            else:
                print(json.dumps(json_pairs, indent=2))
        else:
            # Print connection pairs in a readable way
            print("\nConnection pairs established:")
            for i, (src, src_port, dst, dst_port) in enumerate(con):
                if src and dst:
                    src_gid = src.ports.get(src_port, {}).get('gid', 'N/A') if hasattr(src, 'ports') else 'N/A'
                    dst_gid = dst.ports.get(dst_port, {}).get('gid', 'N/A') if hasattr