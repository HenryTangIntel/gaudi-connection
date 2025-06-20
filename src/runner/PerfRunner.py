#!/usr/bin/env python3
"""
Performance Test Runner

This module provides functionality to run performance tests between two hosts.
It handles the setup, execution, and logging of perf_test commands.

Note: 
- This implementation always sets GID index to 0 for both server and client,
  regardless of any other provided values.
- Server and client use their own separate IB device and port configurations
  as specified in the connectivity file, ensuring proper routing paths.
"""

import subprocess
import threading
import time
import argparse
import sys
import os
import signal
import re
from datetime import datetime


class PerfRunner:
    """
    Runner for performance tests between two hosts
    """
    
    def __init__(self, server_host='localhost', port=18515, test_type='pp',
                 size=4096, iterations=1000, timeout=300,
                 server_ib_dev=None, server_ib_port=1, server_gid_idx=None,
                 client_ib_dev=None, client_ib_port=1, client_gid_idx=None,
                 extra_args=None, log_dir="perf_test_logs"):
        """
        Initialize a performance test runner
        
        Args:
            server_host: Server hostname or IP address
            client_host: Client hostname or IP address
            server_ib_dev: Server IB device name
            server_ib_port: Server IB port number
            server_gid_idx: Server GID index (will be forced to 0)
            client_ib_dev: Client IB device name
            client_ib_port: Client IB port number
            client_gid_idx: Client GID index (will be forced to 0)
            perf_test_path: Path to the perf_test binary
            port: TCP/UDP port number
            test_type: Performance test type
            size: Message size in bytes
            iterations: Number of iterations
            timeout: Timeout in seconds
            extra_args: Extra arguments to pass to perf_test
        """
        self.server_host = server_host
        self.port = port
        self.test_type = test_type
        self.size = size
        self.iterations = iterations
        
        # Server IB settings
        self.server_ib_dev = server_ib_dev
        self.server_ib_port = server_ib_port
        # Always use gid_idx=0 regardless of the input value
        self.server_gid_idx = 0
        
        # Client IB settings
        self.client_ib_dev = client_ib_dev
        self.client_ib_port = client_ib_port
        # Always use gid_idx=0 regardless of the input value
        self.client_gid_idx = 0
        
        self.extra_args = extra_args or []
        self.timeout = timeout
        self.log_dir = log_dir
        
        self.server_process = None
        self.client_process = None
        self.server_output = []
        self.client_output = []
        self.server_thread = None
        self.client_thread = None
        self.test_success = False
        
        self.perf_test_path = '/opt/habanalabs/perf-test/perf_test'
        
    def build_command_args(self, is_server=True):
        """Build command arguments for server or client"""
        args = [self.perf_test_path]
        
        # Common arguments
        if self.port:
            args.extend(['-p', str(self.port)])
        if self.test_type:
            args.extend(['-t', self.test_type])
        if self.size:
            args.extend(['-s', str(self.size)])
        if self.iterations:
            args.extend(['-n', str(self.iterations)])
        
        if is_server:
            # Server-specific IB settings
            if self.server_ib_dev:
                args.extend(['-d', self.server_ib_dev])
            if self.server_ib_port:
                args.extend(['-i', str(self.server_ib_port)])
            # Always use gid_idx=0 regardless of input value
            args.extend(['-g', '0'])
        else:
            # Client-specific IB settings
            if self.client_ib_dev:
                args.extend(['-d', self.client_ib_dev])
            if self.client_ib_port:
                args.extend(['-i', str(self.client_ib_port)])
            # Always use gid_idx=0 regardless of input value
            args.extend(['-g', '0'])
            
        # Add any extra arguments
        if self.extra_args:
            args.extend(self.extra_args)
        
        # Client needs to specify the server host
        if not is_server and self.server_host:
            args.append(self.server_host)
            
        return args
    
    def capture_output(self, process, output_list, name):
        """Capture output from a process"""
        try:
            for line in iter(process.stdout.readline, b''):
                if line:
                    decoded_line = line.decode('utf-8').strip()
                    output_list.append(decoded_line)
                    print(f"[{name}] {decoded_line}")
        except Exception as e:
            print(f"[{name}] Error capturing output: {e}")
    
    def start_server(self):
        """Start the server process"""
        print(f"\n[{datetime.now()}] Starting server...")
        cmd = self.build_command_args(is_server=True)
        print(f"Server command: {' '.join(cmd)}")
        
        try:
            self.server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid
            )
            
            self.server_thread = threading.Thread(
                target=self.capture_output,
                args=(self.server_process, self.server_output, "SERVER")
            )
            self.server_thread.daemon = True
            self.server_thread.start()
            
            # Give server time to start listening
            time.sleep(5)
            return True
            
        except Exception as e:
            print(f"Failed to start server: {e}")
            return False
    
    def start_client(self):
        """Start the client process"""
        print(f"\n[{datetime.now()}] Starting client...")
        cmd = self.build_command_args(is_server=False)
        print(f"Client command: {' '.join(cmd)}")
        
        try:
            self.client_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid
            )
            
            self.client_thread = threading.Thread(
                target=self.capture_output,
                args=(self.client_process, self.client_output, "CLIENT")
            )
            self.client_thread.daemon = True
            self.client_thread.start()
            return True
            
        except Exception as e:
            print(f"Failed to start client: {e}")
            return False
    
    def wait_for_completion(self, timeout=None):
        """Wait for test completion with timeout"""
        if timeout is None:
            timeout = self.timeout
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check if client process has completed
            if self.client_process and self.client_process.poll() is not None:
                print(f"\n[{datetime.now()}] Client process completed with return code: {self.client_process.returncode}")
                # Give server a moment to complete
                time.sleep(5)
                break
                
            time.sleep(1)
        else:
            print(f"\n[{datetime.now()}] Test timeout reached ({timeout}s)")
            return False
            
        return True
    
    def analyze_results(self):
        """Analyze test outputs to determine success/failure"""
        print(f"\n[{datetime.now()}] Analyzing results...")
        
        # Check process return codes
        client_rc = self.client_process.returncode if self.client_process else -1
        server_rc = self.server_process.returncode if self.server_process else -1
        
        print(f"Client return code: {client_rc}")
        print(f"Server return code: {server_rc}")
        
        # Look for error patterns in output
        error_patterns = [
            r"error",
            r"failed",
            r"cannot",
            r"unable",
            r"timeout",
            r"refused"
        ]
        
        success_patterns = [
            r"bandwidth",
            r"latency",
            r"completed",
            r"success",
            r"mbps",
            r"gbps",
            r"usec"
        ]
        
        errors_found = []
        success_indicators = []
        
        # Check both outputs for errors and success indicators
        for output_list, name in [(self.server_output, "SERVER"), (self.client_output, "CLIENT")]:
            for line in output_list:
                line_lower = line.lower()
                
                # Check for errors
                for pattern in error_patterns:
                    if re.search(pattern, line_lower):
                        errors_found.append(f"[{name}] {line}")
                        
                # Check for success indicators
                for pattern in success_patterns:
                    if re.search(pattern, line_lower):
                        success_indicators.append(f"[{name}] {line}")
        
        # Determine overall success
        if client_rc == 0 and not errors_found and success_indicators:
            self.test_success = True
            print("\n✓ Test completed successfully!")
            
            # Print performance metrics found
            print("\nPerformance metrics:")
            for indicator in success_indicators:
                if any(metric in indicator.lower() for metric in ['mbps', 'gbps', 'usec', 'bandwidth', 'latency']):
                    print(f"  {indicator}")
        else:
            self.test_success = False
            print("\n✗ Test failed!")
            
            if errors_found:
                print("\nErrors found:")
                for error in errors_found:
                    print(f"  {error}")
                    
            if client_rc != 0:
                print(f"\nClient exited with non-zero return code: {client_rc}")
    
    def cleanup(self):
        """Clean up processes"""
        print(f"\n[{datetime.now()}] Cleaning up...")
        
        for process, name in [(self.server_process, "server"), (self.client_process, "client")]:
            if process and process.poll() is None:
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    process.wait(timeout=5)
                except Exception as e:
                    print(f"Error terminating {name}: {e}")
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    except:
                        pass
    
    def run(self):
        """Run the complete test"""
        try:
            # Check if perf_test exists
            if not os.path.exists(self.perf_test_path):
                print(f"Error: perf_test not found at {self.perf_test_path}")
                return False
            
            # Start server
            if not self.start_server():
                return False
            
            # Start client
            if not self.start_client():
                self.cleanup()
                return False
            
            # Wait for completion
            if not self.wait_for_completion():
                self.cleanup()
                return False
            
            # Analyze results
            self.analyze_results()
            
            # Save logs
            self.save_logs()
            
            return self.test_success
            
        except KeyboardInterrupt:
            print("\n\nTest interrupted by user")
            return False
        finally:
            self.cleanup()
    
    def save_logs(self, log_dir=None):
        """Save outputs to log files"""
        if log_dir is None:
            log_dir = self.log_dir
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save server log
        server_log = os.path.join(log_dir, f"server_{timestamp}.log")
        with open(server_log, 'w') as f:
            f.write('\n'.join(self.server_output))
        print(f"Server log saved to: {server_log}")
        
        # Save client log
        client_log = os.path.join(log_dir, f"client_{timestamp}.log")
        with open(client_log, 'w') as f:
            f.write('\n'.join(self.client_output))
        print(f"Client log saved to: {client_log}")
    
    @staticmethod
    def get_timestamp():
        """Get current timestamp as string"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def run_multiple_tests(self, connections):
        """
        Run performance tests on multiple connections.
        
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
            
            # Configure for this specific connection
            src = connection['source']
            dst = connection['destination']
            
            # Update IB settings for this connection
            self.server_ib_dev = src.get('ib_name')
            self.server_ib_port = src.get('port')
            self.client_ib_dev = dst.get('ib_name')
            self.client_ib_port = dst.get('port')
            
            # Always ensure GID index is 0 for both server and client
            self.server_gid_idx = 0
            self.client_gid_idx = 0
            
            # The server host is set to the source GID
            # Skip connections without valid GID information
            if 'gid' not in src or not src.get('gid'):
                print("Skipping connection due to missing source GID")
                error_count += 1
                continue
                
            self.server_host = src.get('gid')
            
            # Run the test
            result = self.run()
            
            if result:
                # Enhance result with connection info
                test_result = {
                    'status': 'success' if result else 'failed',
                    'source': f"{src.get('ib_name')}:port{src.get('port')} (GID: {src.get('gid')})",
                    'destination': f"{dst.get('ib_name')}:port{dst.get('port')} (GID: {dst.get('gid')})"
                }
                results.append(test_result)
                if result:
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
