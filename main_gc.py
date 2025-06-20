import os
import json
import argparse
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))
from connection import GaudiDevices, GaudiRouting, connection, print_connection_pairs, print_gaudi_device_mapping, verify_connections_vs_csv
from runner.PerfRunner import PerfRunner


def connection_perftest(src_device, dst_device):
    """
    Run performance test between source and destination Gaudi devices using perf_test.
    Args:
        src_device: GaudiDevice object (source)
        dst_device: GaudiDevice object (destination)
        src_port: Port number for source device
        dst_port: Port number for destination device
    Returns:
        Dict with test results or None if test could not be performed
    """
    import subprocess
    import os
    def get_gid(device, port):
        # Try to get GID from device.ports dict if available
        if hasattr(device, 'ports') and isinstance(device.ports, dict):
            port_info = device.ports.get(port)
            if port_info:
                return port_info.get('gid')
        return getattr(device, 'gid', None)

    # These will be passed in as arguments in the new RealRunConnection
    return None  # Placeholder, see RealRunConnection for new logic


def RealRunConnection(connections):
    """
    Executes performance tests on all the provided (src_device, src_port, dst_device, dst_port) tuples and collects results.
    Args:
        connections: List of (src_device, src_port, dst_device, dst_port) tuples
    Returns:
        Dict with summary and detailed results for each connection
    """
    results = []
    success_count = 0
    failure_count = 0
    error_count = 0
    print(f"\nRunning performance tests on {len(connections)} connections...")
    
    # Create a single PerfRunner instance that will be reused for all connections
    perf_runner = PerfRunner(log_dir="connection_test_logs")
    
    for i, (src, src_port, dst, dst_port) in enumerate(connections):
        print(f"\nConnection {i+1}/{len(connections)}")
        if not src or not dst:
            print("Error: Connection missing source or destination device")
            error_count += 1
            continue
        
        src_ib_name = getattr(src, 'ib_name', None)
        dst_ib_name = getattr(dst, 'ib_name', None)
        
        # Try to get GID from device.ports dict if available
        def get_gid(device, port):
            if hasattr(device, 'ports') and isinstance(device.ports, dict):
                port_info = device.ports.get(port)
                if port_info:
                    return port_info.get('gid')
            return getattr(device, 'gid', None)
        
        src_gid = get_gid(src, src_port)
        dst_gid = get_gid(dst, dst_port)
        
        print(f"Testing connection from {src_ib_name}:port{src_port} to {dst_ib_name}:port{dst_port}")
        
        if not src_gid or not dst_gid:
            print(f"Warning: Missing GIDs for connection. Source GID: {src_gid}, Destination GID: {dst_gid}")
        
        # Check if perf_test exists
        perf_test = "/opt/habanalabs/perf-test/perf_test"
        if not os.path.exists(perf_test) or not os.access(perf_test, os.X_OK):
            print(f"Error: perf_test utility not found at {perf_test} or not executable")
            error_count += 1
            continue
        
        # Configure PerfRunner for this specific connection
        perf_runner.server_ib_dev = src_ib_name
        perf_runner.server_ib_port = src_port
        perf_runner.server_gid_idx = 0  # Always use GID index 0
        perf_runner.client_ib_dev = dst_ib_name
        perf_runner.client_ib_port = dst_port
        perf_runner.client_gid_idx = 0  # Always use GID index 0
        
        # Use localhost IP for testing, in a real scenario this might be a remote host
        perf_runner.server_host = '127.0.0.1'
        
        # Generate a unique log filename based on the connection
        log_name = f"test_{src_ib_name}_p{src_port}_to_{dst_ib_name}_p{dst_port}_{perf_runner.get_timestamp()}"
        perf_runner.log_dir = os.path.join("connection_test_logs")
        
        try:
            # Log the commands that will be executed (similar to dry run but now we'll actually run them)
            server_cmd = perf_runner.build_command_args(is_server=True)
            client_cmd = perf_runner.build_command_args(is_server=False)
            print(f"Server command: {' '.join(server_cmd)}")
            print(f"Client command: {' '.join(client_cmd)}")
            
            # Run the actual test
            test_success = perf_runner.run()
            
            # Record results
            status = 'success' if test_success else 'failed'
            if test_success:
                success_count += 1
            else:
                failure_count += 1
                
            result = {
                'status': status,
                'source': f"{src_ib_name}:port{src_port} (GID: {src_gid})",
                'destination': f"{dst_ib_name}:port{dst_port} (GID: {dst_gid})"
            }
            results.append(result)
            
        except Exception as e:
            print(f"Exception during performance test: {str(e)}")
            error_count += 1
            results.append({
                'status': 'error',
                'error': str(e),
                'source': f"{src_ib_name}:port{src_port}",
                'destination': f"{dst_ib_name}:port{dst_port}"
            })
    
    print("\n" + "="*50)
    print("PERFORMANCE TEST SUMMARY")
    print("="*50)
    print(f"Total connections tested: {len(connections)}")
    print(f"Successful tests: {success_count}")
    print(f"Failed tests: {failure_count}")
    print(f"Errors/skipped: {error_count}")
    print("="*50)
    return {
        'summary': {
            'total': len(connections),
            'success': success_count,
            'failure': failure_count,
            'error': error_count
        },
        'details': results
    }


def main():
    """
    Main entry point for the Gaudi Connection Tool (new implementation).
    Parses command line arguments and executes appropriate actions.
    """
    parser = argparse.ArgumentParser(description="Gaudi Connection Tool (new)")
    parser.add_argument("-c", "--connectivity", default="connectivity_HLS2.csv", help="Path to connectivity CSV file")
    parser.add_argument("-d", "--devices", action="store_true", help="Show device summary")
    parser.add_argument("-r", "--routes", action="store_true", help="Show routing connections")
    parser.add_argument("-j", "--json", action="store_true", help="Output connection pairs in JSON format")
    parser.add_argument("-v", "--verify", action="store_true", help="Verify connections vs CSV")
    parser.add_argument("-o", "--output", help="Output file for connection data (JSON format)")
    parser.add_argument("-p", "--perf", action="store_true", help="Run performance tests on connections")
    args = parser.parse_args()

    gaudidevices = GaudiDevices()
    connectivity = GaudiRouting(args.connectivity)

    # Show device summary if requested or if no specific action is requested
    if args.devices or not (args.routes or args.json):
        print_gaudi_device_mapping(gaudidevices)

    # Show routing information if requested
    if args.routes or args.json:
        con = connection(gaudidevices, connectivity)
        # con is now a list of (src, src_port, dst, dst_port)
        if args.json:
            # Output connection pairs as JSON (module_id, device_id, ib_name, port for src/dst)
            json_pairs = [
                {
                    "src": {
                        "module_id": src.module_id if src else None,
                        "device_id": src.device_id if src else None,
                        "ib_name": src.ib_name if src else None,
                        "port": src_port
                    },
                    "dst": {
                        "module_id": dst.module_id if dst else None,
                        "device_id": dst.device_id if dst else None,
                        "ib_name": dst.ib_name if dst else None,
                        "port": dst_port
                    }
                }
                for src, src_port, dst, dst_port in con
            ]
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(json_pairs, f, indent=2)
                print(f"Connection pairs saved to {args.output}")
            else:
                print(json.dumps(json_pairs, indent=2))
        else:
            # Print connection pairs in a readable way
            print("Connection pairs established:")
            for src, src_port, dst, dst_port in con:
                if src and dst:
                    print(f"  {src} (port {src_port}) <-> {dst} (port {dst_port})")
                else:
                    print("  Incomplete connection due to missing device information.")
            print(f"All connections {len(con)} processed.")
            
    # Run performance tests if --perf is specified
    if args.perf:
        if not args.routes:
            print("Warning: --perf requires --routes to be specified for performance testing.")
        else:
            results = RealRunConnection(con)
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(results, f, indent=2)
                print(f"Performance test results saved to {args.output}")
            else:
                print(json.dumps(results, indent=2))

    # Verification if requested
    if args.verify:
        modid_to_info = print_gaudi_device_mapping(gaudidevices)
        verify_connections_vs_csv(modid_to_info, args.connectivity)


if __name__ == "__main__":
    main()