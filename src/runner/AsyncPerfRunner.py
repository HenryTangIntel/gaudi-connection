#!/usr/bin/env python3
"""
Asynchronous Performance Test Runner with Request Queue

This module provides functionality to run performance tests asynchronously
using a request queue system. It handles parallel test execution with
proper resource management and result collection.
"""

import asyncio
import subprocess
import os
import time
import json
import signal
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from queue import Queue
from concurrent.futures import ThreadPoolExecutor, Future
import threading
import logging
import re

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class PerfTestRequest:
    """Data class representing a performance test request"""
    request_id: str
    source_device: Any  # GaudiDevice object
    source_port: int
    dest_device: Any    # GaudiDevice object
    dest_port: int
    test_type: str = 'pp'
    size: int = 4096
    iterations: int = 1000
    timeout: int = 300
    priority: int = 0  # Lower number = higher priority
    
    def __lt__(self, other):
        """Enable priority queue sorting"""
        return self.priority < other.priority


@dataclass
class PerfTestResult:
    """Data class representing a performance test result"""
    request_id: str
    status: str  # 'success', 'failed', 'error', 'timeout'
    start_time: datetime
    end_time: datetime
    duration: float
    source_info: str
    dest_info: str
    metrics: Dict[str, Any] = None
    error_message: str = None
    server_output: List[str] = None
    client_output: List[str] = None


class AsyncPerfRunner:
    """
    Asynchronous performance test runner using request queue
    """
    
    def __init__(self, max_concurrent_tests: int = 5, 
                 perf_test_path: str = '/opt/habanalabs/perf-test/perf_test',
                 log_dir: str = "async_perf_logs"):
        """
        Initialize the async performance test runner
        
        Args:
            max_concurrent_tests: Maximum number of concurrent tests
            perf_test_path: Path to perf_test binary
            log_dir: Directory for storing logs
        """
        self.max_concurrent_tests = max_concurrent_tests
        self.perf_test_path = perf_test_path
        self.log_dir = log_dir
        
        # Create log directory
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Request queue and executor
        self.request_queue = asyncio.PriorityQueue()
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_tests)
        
        # Active tests tracking
        self.active_tests: Dict[str, Future] = {}
        self.results: Dict[str, PerfTestResult] = {}
        
        # Control flags
        self.running = False
        self.shutdown_event = asyncio.Event()
        
    async def start(self):
        """Start the async runner"""
        self.running = True
        logger.info(f"AsyncPerfRunner started with {self.max_concurrent_tests} concurrent test slots")
        
        # Start worker tasks
        workers = []
        for i in range(self.max_concurrent_tests):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            workers.append(worker)
        
        # Wait for shutdown
        await self.shutdown_event.wait()
        
        # Cancel workers
        for worker in workers:
            worker.cancel()
        
        # Wait for all workers to finish
        await asyncio.gather(*workers, return_exceptions=True)
        
        logger.info("AsyncPerfRunner stopped")
        
    async def stop(self):
        """Stop the async runner"""
        self.running = False
        self.shutdown_event.set()
        
        # Cancel all active tests
        for request_id, future in self.active_tests.items():
            if not future.done():
                future.cancel()
                
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
    async def submit_test(self, request: PerfTestRequest) -> str:
        """
        Submit a test request to the queue
        
        Args:
            request: PerfTestRequest object
            
        Returns:
            Request ID for tracking
        """
        await self.request_queue.put((request.priority, request))
        logger.info(f"Test request {request.request_id} submitted to queue")
        return request.request_id
        
    async def get_result(self, request_id: str, timeout: Optional[float] = None) -> Optional[PerfTestResult]:
        """
        Get result for a specific request ID
        
        Args:
            request_id: Request ID to get result for
            timeout: Optional timeout in seconds
            
        Returns:
            PerfTestResult if available, None otherwise
        """
        start_time = time.time()
        
        while request_id not in self.results:
            if timeout and (time.time() - start_time) > timeout:
                return None
            await asyncio.sleep(0.1)
            
        return self.results.get(request_id)
        
    async def get_all_results(self) -> Dict[str, PerfTestResult]:
        """Get all available results"""
        return self.results.copy()
        
    async def _worker(self, worker_name: str):
        """Worker task that processes requests from the queue"""
        logger.info(f"{worker_name} started")
        
        while self.running:
            try:
                # Get request from queue with timeout
                priority, request = await asyncio.wait_for(
                    self.request_queue.get(), 
                    timeout=1.0
                )
                
                logger.info(f"{worker_name} processing request {request.request_id}")
                
                # Run test in executor
                loop = asyncio.get_event_loop()
                future = loop.run_in_executor(
                    self.executor,
                    self._run_single_test,
                    request
                )
                
                # Track active test
                self.active_tests[request.request_id] = future
                
                # Wait for completion
                result = await future
                
                # Store result
                self.results[request.request_id] = result
                
                # Remove from active tests
                del self.active_tests[request.request_id]
                
                logger.info(f"{worker_name} completed request {request.request_id} with status {result.status}")
                
            except asyncio.TimeoutError:
                # No requests in queue, continue
                continue
            except asyncio.CancelledError:
                # Worker cancelled, exit
                break
            except Exception as e:
                logger.error(f"{worker_name} error: {str(e)}")
                
        logger.info(f"{worker_name} stopped")
        
    def _run_single_test(self, request: PerfTestRequest) -> PerfTestResult:
        """
        Run a single performance test (blocking)
        
        Args:
            request: PerfTestRequest object
            
        Returns:
            PerfTestResult object
        """
        start_time = datetime.now()
        
        # Initialize result
        result = PerfTestResult(
            request_id=request.request_id,
            status='error',
            start_time=start_time,
            end_time=start_time,
            duration=0.0,
            source_info=self._get_device_info(request.source_device, request.source_port),
            dest_info=self._get_device_info(request.dest_device, request.dest_port),
            server_output=[],
            client_output=[]
        )
        
        # Check if perf_test exists
        if not os.path.exists(self.perf_test_path) or not os.access(self.perf_test_path, os.X_OK):
            result.error_message = f"perf_test not found or not executable at {self.perf_test_path}"
            result.end_time = datetime.now()
            result.duration = (result.end_time - result.start_time).total_seconds()
            return result
            
        server_process = None
        client_process = None
        
        try:
            # Build server command
            server_cmd = self._build_command(
                request, 
                is_server=True
            )
            
            # Start server
            logger.debug(f"Starting server: {' '.join(server_cmd)}")
            server_process = subprocess.Popen(
                server_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid,
                universal_newlines=True
            )
            
            # Give server time to start
            time.sleep(2)
            
            # Build client command
            client_cmd = self._build_command(
                request,
                is_server=False
            )
            
            # Start client
            logger.debug(f"Starting client: {' '.join(client_cmd)}")
            client_process = subprocess.Popen(
                client_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid,
                universal_newlines=True
            )
            
            # Wait for client to complete with timeout
            try:
                client_stdout, _ = client_process.communicate(timeout=request.timeout)
                result.client_output = client_stdout.splitlines()
                
                # Wait for server readiness
                server_ready = False
                for _ in range(10):  # Check readiness for up to 10 seconds
                    if server_process.poll() is None:
                        server_ready = True
                        break
                    time.sleep(1)

                if not server_ready:
                    result.error_message = "Server did not become ready within the expected time"
                    result.status = "failed"
                    return result

                # Terminate server with a delay to allow graceful shutdown
                if server_process.poll() is None:
                    time.sleep(2)  # Allow server more time to complete operations
                    os.killpg(os.getpgid(server_process.pid), signal.SIGTERM)
                    try:
                        server_stdout, _ = server_process.communicate(timeout=5)
                        result.server_output = server_stdout.splitlines()
                    except subprocess.TimeoutExpired:
                        os.killpg(os.getpgid(server_process.pid), signal.SIGKILL)
                        
            except subprocess.TimeoutExpired:
                result.status = 'timeout'
                result.error_message = f"Test timed out after {request.timeout} seconds"
                
                # Kill both processes
                for proc in [client_process, server_process]:
                    if proc and proc.poll() is None:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                        
            # Analyze results
            if result.status != 'timeout':
                result.status, result.metrics = self._analyze_output(
                    result.client_output,
                    result.server_output,
                    client_process.returncode if client_process else -1
                )

                # If both client and server tests passed, report success
                if result.status == 'failed' and 'Test PASS' in result.client_output and 'Test PASS' in result.server_output:
                    result.status = 'success'
                
                # Log server and client outputs
                logger.debug(f"Server output: {result.server_output}")
                logger.debug(f"Client output: {result.client_output}")
                
        except Exception as e:
            result.error_message = f"Exception during test: {str(e)}"
            logger.error(f"Test {request.request_id} failed with exception: {str(e)}")
            
        finally:
            # Ensure processes are cleaned up
            for proc in [server_process, client_process]:
                if proc and proc.poll() is None:
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    except:
                        pass
                        
        # Set end time and duration
        result.end_time = datetime.now()
        result.duration = (result.end_time - result.start_time).total_seconds()
        
        # Clean up ANSI escape sequences and format outputs for readability
        result.server_output = [re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', line).strip() for line in result.server_output]
        result.client_output = [re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', line).strip() for line in result.client_output]

        # Log cleaned outputs in a human-readable format
        logger.info("\nServer Output:")
        for line in result.server_output:
            logger.info(line)

        logger.info("\nClient Output:")
        for line in result.client_output:
            logger.info(line)
        
        # Save logs
        self._save_test_logs(request.request_id, result)
        
        return result
        
    def _build_command(self, request: PerfTestRequest, is_server: bool) -> List[str]:
        """Build command arguments for server or client"""
        cmd = [self.perf_test_path]
        
        # Common arguments
        cmd.extend(['-t', request.test_type])
        cmd.extend(['-s', str(request.size)])
        cmd.extend(['-n', str(request.iterations)])
        
        if is_server:
            # Server-specific
            device = request.source_device
            port = request.source_port
            
            if hasattr(device, 'ib_name') and device.ib_name:
                cmd.extend(['-d', device.ib_name])
            cmd.extend(['-i', str(port)])
            cmd.extend(['-g', '0'])  # Always use GID index 0
            
        else:
            # Client-specific
            device = request.dest_device
            port = request.dest_port
            
            if hasattr(device, 'ib_name') and device.ib_name:
                cmd.extend(['-d', device.ib_name])
            cmd.extend(['-i', str(port)])
            cmd.extend(['-g', '0'])  # Always use GID index 0
            
            # Add server address (using localhost for now)
            cmd.append('127.0.0.1')
            
        return cmd
        
    def _get_device_info(self, device: Any, port: int) -> str:
        """Get device information string"""
        if not device:
            return f"Unknown device:port{port}"
            
        ib_name = getattr(device, 'ib_name', 'Unknown')
        
        # Try to get GID
        gid = None
        if hasattr(device, 'ports') and isinstance(device.ports, dict):
            port_info = device.ports.get(port)
            if port_info:
                gid = port_info.get('gid')
                
        if gid:
            return f"{ib_name}:port{port} (GID: {gid})"
        else:
            return f"{ib_name}:port{port}"
            
    def _analyze_output(self, client_output: List[str], server_output: List[str], 
                       client_returncode: int) -> Tuple[str, Dict[str, Any]]:
        """Analyze test output to determine status and extract metrics"""
        metrics = {}
        
        # Check return code
        if client_returncode != 0:
            return 'failed', metrics
            
        # Look for performance metrics in output
        success_found = False
        
        for line in client_output + server_output:
            line_lower = line.lower()
            
            # Check for errors
            if any(err in line_lower for err in ['error', 'failed', 'cannot', 'unable']):
                return 'failed', metrics
                
            # Extract metrics
            if 'bandwidth' in line_lower or 'bw' in line_lower:
                success_found = True
                # Try to extract bandwidth value
                parts = line.split()
                for i, part in enumerate(parts):
                    if 'mb/s' in part.lower() or 'mbps' in part.lower():
                        try:
                            metrics['bandwidth_mbps'] = float(parts[i-1])
                        except:
                            pass
                    elif 'gb/s' in part.lower() or 'gbps' in part.lower():
                        try:
                            metrics['bandwidth_gbps'] = float(parts[i-1])
                        except:
                            pass
                            
            if 'latency' in line_lower:
                success_found = True
                # Try to extract latency value
                parts = line.split()
                for i, part in enumerate(parts):
                    if 'usec' in part.lower() or 'us' in part.lower():
                        try:
                            metrics['latency_usec'] = float(parts[i-1])
                        except:
                            pass
                            
        # Refine logic to ensure test status reflects outputs correctly
        if 'Test PASS' in client_output and 'Test PASS' in server_output:
            return 'success', metrics
        
        return 'success' if success_found else 'failed', metrics
        
    def _save_test_logs(self, request_id: str, result: PerfTestResult):
        """Save test logs to files"""
        timestamp = result.start_time.strftime("%Y%m%d_%H%M%S")
        test_dir = os.path.join(self.log_dir, f"{request_id}_{timestamp}")
        os.makedirs(test_dir, exist_ok=True)
        
        # Save server output
        if result.server_output:
            with open(os.path.join(test_dir, "server.log"), 'w') as f:
                f.write('\n'.join(result.server_output))
                
        # Save client output
        if result.client_output:
            with open(os.path.join(test_dir, "client.log"), 'w') as f:
                f.write('\n'.join(result.client_output))
                
        # Save result summary
        summary = {
            'request_id': result.request_id,
            'status': result.status,
            'start_time': result.start_time.isoformat(),
            'end_time': result.end_time.isoformat(),
            'duration': result.duration,
            'source': result.source_info,
            'destination': result.dest_info,
            'metrics': result.metrics,
            'error_message': result.error_message
        }
        
        with open(os.path.join(test_dir, "summary.json"), 'w') as f:
            json.dump(summary, f, indent=2)


async def run_connection_tests_async(connections: List[Tuple], 
                                   max_concurrent: int = 5,
                                   test_params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Run connection tests asynchronously using the AsyncPerfRunner
    
    Args:
        connections: List of (src_device, src_port, dst_device, dst_port) tuples
        max_concurrent: Maximum number of concurrent tests
        test_params: Optional test parameters (test_type, size, iterations, etc.)
        
    Returns:
        Dictionary with summary and detailed results
    """
    test_params = test_params or {}
    
    # Create async runner
    runner = AsyncPerfRunner(max_concurrent_tests=max_concurrent)
    
    # Start runner in background
    runner_task = asyncio.create_task(runner.start())
    
    try:
        # Submit all test requests
        request_ids = []
        
        for i, (src, src_port, dst, dst_port) in enumerate(connections):
            request = PerfTestRequest(
                request_id=f"test_{i}_{int(time.time()*1000)}",
                source_device=src,
                source_port=src_port,
                dest_device=dst,
                dest_port=dst_port,
                **test_params
            )
            
            request_id = await runner.submit_test(request)
            request_ids.append(request_id)
            
        logger.info(f"Submitted {len(request_ids)} test requests")
        
        # Wait for all results
        results = []
        for request_id in request_ids:
            result = await runner.get_result(request_id, timeout=600)  # 10 min timeout
            if result:
                results.append(result)
                
        # Calculate summary
        success_count = sum(1 for r in results if r.status == 'success')
        failed_count = sum(1 for r in results if r.status == 'failed')
        timeout_count = sum(1 for r in results if r.status == 'timeout')
        error_count = sum(1 for r in results if r.status == 'error')
        
        # Prepare detailed results
        detailed_results = []
        for result in results:
            detailed_results.append({
                'request_id': result.request_id,
                'status': result.status,
                'duration': result.duration,
                'source': result.source_info,
                'destination': result.dest_info,
                'metrics': result.metrics,
                'error': result.error_message
            })
            
        return {
            'summary': {
                'total': len(connections),
                'submitted': len(request_ids),
                'completed': len(results),
                'success': success_count,
                'failed': failed_count,
                'timeout': timeout_count,
                'error': error_count
            },
            'details': detailed_results
        }
        
    finally:
        # Stop runner
        await runner.stop()
        runner_task.cancel()
        try:
            await runner_task
        except asyncio.CancelledError:
            pass


# Example usage
if __name__ == "__main__":
    # Example test
    async def example():
        # Mock connections for testing
        MockDevice_src = type('MockDevice', (), {
            'ib_name': 'hbl_3',
            'ports': {7: {'gid': '0'}}
        })
        
        MockDevice_dst = type('MockDevice', (), {
            'ib_name': 'hbl_6',
            'ports': {7: {'gid': '0'}}
        })
        
        connections = [
            (MockDevice_src(), 7, MockDevice_dst(), 7)
        ]
        
        results = await run_connection_tests_async(
            connections,
            max_concurrent=2,
            test_params={
                'test_type': 'pp',
                'size': 4096,
                'iterations': 100
            }
        )
        
        print(json.dumps(results, indent=2))
        
    asyncio.run(example())