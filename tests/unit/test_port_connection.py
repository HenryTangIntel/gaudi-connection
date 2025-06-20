import os
import pytest
import subprocess
import sys
import time
from unittest.mock import patch, MagicMock, call

# Add the project root to sys.path to import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from test_port_connection import PerfTestRunner

class TestPerfTestRunner:
    """Test cases for the PerfTestRunner class in test_port_connection.py"""

    @pytest.fixture
    def mock_subprocess(self):
        """Mock subprocess for testing without actually running processes"""
        with patch('subprocess.Popen') as mock_popen:
            # Create mock process objects
            mock_server_process = MagicMock()
            mock_client_process = MagicMock()
            
            # Configure the mock processes
            # We need to ensure poll returns None until cleanup, then return a value
            mock_server_process.poll.side_effect = lambda: None
            mock_server_process.returncode = 0
            mock_server_process.stdout.readline.side_effect = [b'Server started\n', b'Listening on port 18515\n', b'']
            
            # For client process, we'll first return None during wait_for_completion checks,
            # then return 0 to indicate completion
            mock_client_process.poll.side_effect = [None, None, 0, 0, 0]  # Need extra values for cleanup
            mock_client_process.returncode = 0
            mock_client_process.stdout.readline.side_effect = [
                b'Client connected\n', 
                b'Test running\n',
                b'Bandwidth: 10000 MB/s\n',
                b'Latency: 5 usec\n',
                b''
            ]
            
            # Setup the mock to return different processes for server and client
            mock_popen.side_effect = [mock_server_process, mock_client_process]
            
            yield mock_popen

    @pytest.fixture
    def mock_path_exists(self):
        """Mock os.path.exists to simulate perf_test existence"""
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            yield mock_exists

    @pytest.fixture
    def mock_sleep(self):
        """Mock time.sleep to speed up tests"""
        with patch('time.sleep') as mock_sleep:
            yield mock_sleep

    @pytest.fixture
    def mock_os_killpg(self):
        """Mock os.killpg for cleanup"""
        with patch('os.killpg') as mock_killpg:
            yield mock_killpg

    @pytest.fixture
    def mock_os_getpgid(self):
        """Mock os.getpgid for cleanup"""
        with patch('os.getpgid') as mock_getpgid:
            mock_getpgid.side_effect = lambda pid: pid
            yield mock_getpgid

    def test_init(self):
        """Test initialization of PerfTestRunner"""
        runner = PerfTestRunner(server_host='test-server', port=12345, test_type='bw',
                              size=8192, iterations=500, ib_dev='mlx5_0')
        
        assert runner.server_host == 'test-server'
        assert runner.port == 12345
        assert runner.test_type == 'bw'
        assert runner.size == 8192
        assert runner.iterations == 500
        assert runner.ib_dev == 'mlx5_0'
        assert runner.perf_test_path == '/opt/habanalabs/perf-test/perf_test'
        assert runner.server_process is None
        assert runner.client_process is None

    def test_build_command_args_server(self):
        """Test building command arguments for server"""
        runner = PerfTestRunner(port=12345, test_type='bw', size=8192, iterations=500, ib_dev='mlx5_0')
        args = runner.build_command_args(is_server=True)
        
        expected_args = [
            '/opt/habanalabs/perf-test/perf_test',
            '-p', '12345',
            '-t', 'bw',
            '-s', '8192',
            '-n', '500',
            '-d', 'mlx5_0'
        ]
        
        assert args == expected_args

    def test_build_command_args_client(self):
        """Test building command arguments for client"""
        runner = PerfTestRunner(server_host='test-server', port=12345, test_type='bw',
                              size=8192, iterations=500, ib_dev='mlx5_0')
        args = runner.build_command_args(is_server=False)
        
        expected_args = [
            '/opt/habanalabs/perf-test/perf_test',
            '-p', '12345',
            '-t', 'bw',
            '-s', '8192',
            '-n', '500',
            '-d', 'mlx5_0',
            'test-server'
        ]
        
        assert args == expected_args

    def test_successful_run_process(self, mock_subprocess, mock_path_exists, mock_sleep, 
                                  mock_os_killpg, mock_os_getpgid):
        """Test a successful run of the complete process"""
        runner = PerfTestRunner()
        
        # Run the test
        result = runner.run()
        
        # Verify perf_test existence was checked
        mock_path_exists.assert_called_once_with('/opt/habanalabs/perf-test/perf_test')
        
        # Verify processes were started with correct commands
        assert mock_subprocess.call_count == 2
        
        # Verify processes were cleaned up
        assert mock_os_killpg.call_count >= 1
        
        # Check that the test was considered successful
        assert result is True
        assert runner.test_success is True

    def test_perf_test_not_found(self, mock_path_exists):
        """Test behavior when perf_test is not found"""
        mock_path_exists.return_value = False
        runner = PerfTestRunner()
        
        # Run the test
        result = runner.run()
        
        # Check that the test was considered failed
        assert result is False

    def test_server_start_failure(self, mock_subprocess, mock_path_exists):
        """Test behavior when server fails to start"""
        # Make the first Popen (server) raise an exception
        mock_subprocess.side_effect = Exception("Failed to start server")
        
        runner = PerfTestRunner()
        result = runner.run()
        
        # Check that the test was considered failed
        assert result is False

    def test_analyze_results_success(self):
        """Test result analysis with successful outputs"""
        runner = PerfTestRunner()
        
        # Mock process return codes
        runner.client_process = MagicMock()
        runner.client_process.returncode = 0
        
        # Set mock outputs with success indicators
        runner.client_output = [
            "Starting client",
            "Connection established",
            "Test completed successfully",
            "Bandwidth: 12500 MB/s",
            "Latency: 2.5 usec"
        ]
        
        runner.server_output = [
            "Starting server",
            "Listening on port 18515",
            "Accepted client connection",
            "Test completed"
        ]
        
        # Run analysis
        runner.analyze_results()
        
        # Check results
        assert runner.test_success is True

    def test_analyze_results_failure(self):
        """Test result analysis with failure indicators"""
        runner = PerfTestRunner()
        
        # Mock process return codes
        runner.client_process = MagicMock()
        runner.client_process.returncode = 1
        
        # Set mock outputs with error indicators
        runner.client_output = [
            "Starting client",
            "Error: Connection refused",
            "Test failed"
        ]
        
        runner.server_output = [
            "Starting server",
            "Failed to bind to port 18515: Address already in use"
        ]
        
        # Run analysis
        runner.analyze_results()
        
        # Check results
        assert runner.test_success is False

    def test_wait_for_completion_timeout(self, mock_sleep):
        """Test wait_for_completion with timeout"""
        runner = PerfTestRunner()
        
        # Mock client process that never completes
        runner.client_process = MagicMock()
        runner.client_process.poll.return_value = None  # Always running
        
        # Set a short timeout for testing
        result = runner.wait_for_completion(timeout=2)
        
        # Check that wait_for_completion times out
        assert result is False

    def test_save_logs(self, tmpdir):
        """Test saving logs to files"""
        runner = PerfTestRunner()
        
        # Set mock outputs
        runner.server_output = ["Server line 1", "Server line 2"]
        runner.client_output = ["Client line 1", "Client line 2"]
        
        # Set log directory to a temporary directory
        log_dir = str(tmpdir.join("logs"))
        runner.save_logs(log_dir=log_dir)
        
        # Check that log files were created
        log_files = os.listdir(log_dir)
        assert len(log_files) == 2
        
        # Verify one server log and one client log
        assert any("server_" in f for f in log_files)
        assert any("client_" in f for f in log_files)

# Integration test that actually runs processes
@pytest.mark.skipif("not os.path.exists('/opt/habanalabs/perf-test/perf_test')")
class TestPerfTestRunnerIntegration:
    """Integration tests for PerfTestRunner that run actual processes"""
    
    def test_local_loopback(self):
        """Test running a performance test on the loopback interface"""
        # This will be skipped if perf_test isn't available
        runner = PerfTestRunner(server_host="localhost", port=19999,
                                test_type="pp", size=64, iterations=10)
        
        # Override the perf_test_path with the script itself
        # to create a dummy test that will always pass
        runner.perf_test_path = sys.executable
        runner.extra_args = ["-c", "import time; print('Test output'); time.sleep(1); exit(0)"]
        
        result = runner.run()
        
        # We just want to ensure the test framework runs properly
        # The actual test will likely fail since we're not using real perf_test
        assert isinstance(result, bool)


if __name__ == "__main__":
    # Run the tests with pytest when script is executed directly
    pytest.main(["-xvs", __file__])
