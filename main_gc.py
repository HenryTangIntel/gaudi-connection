import os
import json
import argparse

from src.devices.GaudiDeviceFactory import GaudiDeviceFactory
from src.connectivity.RunConnection import RunConnection





def connection_perftest(source, destination):
    """
    Run performance test between source and destination Gaudi devices using perf_test.
    
    Args:
        source: Dict containing source device connection information
        destination: Dict containing destination device connection information
        
    Returns:
        Dict with test results or None if test could not be performed
    """
    import subprocess
    import os
    
    # Extract GIDs from source and destination
    src_gid = source.get('gid')
    dst_gid = destination.get('gid')
    
    # Extract interface names
    src_ib_name = source.get('ib_name')
    dst_ib_name = destination.get('ib_name')
    
    # Extract ports
    src_port = source.get('port')
    dst_port = destination.get('port')
    
    print(f"Testing connection from {src_ib_name}:port{src_port} to {dst_ib_name}:port{dst_port}")
    
    # Skip test if GIDs are not available
    if not src_gid or not dst_gid:
        print(f"Warning: Missing GIDs for connection. Source GID: {src_gid}, Destination GID: {dst_gid}")
        return None
    
    # Prepare the command with appropriate parameters
    # Using first source as server, second as client
    # We'll run server in background, then client, and collect results
    
    # Path to perf_test tool
    perf_test = "/opt/habanalabs/perf-test/perf_test"
    
    # Check if perf_test exists and is executable
    if not os.path.exists(perf_test) or not os.access(perf_test, os.X_OK):
        print(f"Error: perf_test utility not found at {perf_test} or not executable")
        return None
        
    try:
        # Run perf_test as server (in background)
        server_cmd = [
            perf_test,
            "-d", src_ib_name,
            "-i", str(src_port),
            "-g", "0",  # Using index 0 as default
            #"--test-type", "pp"  # Ping-Pong test
        ]
        
        print(f"Starting server: {' '.join(server_cmd)}")
        server_process = subprocess.Popen(server_cmd, 
                                         stdout=subprocess.PIPE, 
                                         stderr=subprocess.PIPE)
        
        # Give the server a moment to start
        import time
        time.sleep(5)
        
        # Run perf_test as client
        client_cmd = [
            perf_test,
            "-d", dst_ib_name,
            "-i", str(dst_port),
            "-g", "0",  # Using index 0 as default
            "127.0.0.1"
            #"--test-type", "pp",  # Ping-Pong test
            #src_gid  # Using source GID as the server address
        ]
        
        print(f"Starting client: {' '.join(client_cmd)}")
        client_process = subprocess.Popen(client_cmd,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
        
        # Let both processes run for 5 seconds
        import time
        print(f"Letting the performance test run for 5 seconds...")
        time.sleep(5)
        
        # Collect client output (non-blocking)
        client_output = ""
        client_error = ""
        
        # Try to read output without waiting for completion
        if client_process.poll() is None:  # If process is still running
            try:
                client_process.terminate()
                stdout, stderr = client_process.communicate(timeout=2)
                client_output = stdout.decode() if stdout else ""
                client_error = stderr.decode() if stderr else ""
            except Exception as e:
                print(f"Error collecting client output: {str(e)}")
        
        # Terminate the server
        if server_process.poll() is None:  # If process is still running
            try:
                server_process.terminate()
                server_stdout, server_stderr = server_process.communicate(timeout=2)
                server_output = server_stdout.decode() if server_stdout else ""
                # Can add server output to results if needed
            except Exception as e:
                print(f"Error terminating server: {str(e)}")
                # Force kill if terminate fails
                try:
                    server_process.kill()
                except:
                    pass
        
        # Process results
        # Since we manually terminate after 5 seconds, we shouldn't rely on the returncode
        # Instead, check if there was any meaningful output
        
        # Check output for success indicators or error messages
        has_error = False
        if client_error and "error" in client_error.lower():
            print(f"Error in performance test: {client_error}")
            has_error = True
            
        # Basic result parsing (can be enhanced for more detailed results)
        result = {
            'status': 'failed' if has_error else 'success',
            'output': client_output,
            'error': client_error,
            'duration': "5 seconds",
            'source': f"{src_ib_name}:port{src_port} (GID: {src_gid})",
            'destination': f"{dst_ib_name}:port{dst_port} (GID: {dst_gid})"
        }
        
        # Print a summary
        print(f"Performance test completed with status: {result['status']}")
        return result
        
    except Exception as e:
        print(f"Exception during performance test: {str(e)}")
        return {
            'status': 'error',
            'error': str(e),
            'source': f"{src_ib_name}:port{src_port}",
            'destination': f"{dst_ib_name}:port{dst_port}"
        }


def RealRunConnection(connections):
    """
    Executes performance tests on all the provided connections and collects results.
    
    Args:
        connections: List of connection dictionaries with source and destination info
        
    Returns:
        Dict with summary and detailed results for each connection
    """
    results = []
    success_count = 0
    failure_count = 0
    error_count = 0
    
    print(f"\nRunning performance tests on {len(connections)} connections...")
    
    for i, connection in enumerate(connections):
        print(f"\nConnection {i+1}/{len(connections)}")
        
        if not connection.get('source') or not connection.get('destination'):
            print("Error: Connection missing source or destination information")
            error_count += 1
            continue
            
        result = connection_perftest(connection['source'], connection['destination'])
        
        if result:
            results.append(result)
            if result['status'] == 'success':
                success_count += 1
            else:
                failure_count += 1
        else:
            error_count += 1
    
    # Print summary
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gaudi Connection Tool")
    parser.add_argument("-c", "--connectivity", help="Path to connectivity CSV file")
    parser.add_argument("-d", "--devices", action="store_true", help="Show device summary")
    parser.add_argument("-r", "--routes", action="store_true", help="Show routing connections")
    parser.add_argument("-j", "--json", action="store_true", help="Output in JSON format")
    parser.add_argument("-v", "--verify", action="store_true", help="Verify connections have active ports")
    parser.add_argument("-o", "--output", help="Output file for connection data (JSON format)")
    parser.add_argument("-p", "--perf", action="store_true", help="Run performance tests on connections")
    parser.add_argument("--perf-output", help="Output file for performance test results (JSON format)")
    
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
        
        # Run performance tests if --perf flag is provided
        if args.perf:
            test_results = RealRunConnection(connections)
            
            # Save performance results to a separate file if requested
            if args.perf_output:
                with open(args.perf_output, 'w') as f:
                    json.dump(test_results, f, indent=2)
                print(f"\nPerformance test results saved to {args.perf_output}")
        
        # Output as JSON if requested
        if args.json:
            if args.output:
                runner.save_to_json(args.output)
            else:
                print(json.dumps(connections, indent=2))
    
    