import os
import pytest
from src.connectivity.GaudiRouting import GaudiRouting

class TestGaudiRouting:
    def test_init_with_default_file(self, monkeypatch):
        # Mock os.path.exists to return True for the default path
        def mock_exists(path):
            return path == "/opt/habanalabs/perf-test/scale_up_tool/internal_data/connectivity_HLS2.csv"
        
        monkeypatch.setattr(os.path, "exists", mock_exists)
        
        # Mock parse_connectivity_file to avoid actual file operations
        monkeypatch.setattr(GaudiRouting, "parse_connectivity_file", lambda self: None)
        routing = GaudiRouting()
        assert routing.connectivity_file == "/opt/habanalabs/perf-test/scale_up_tool/internal_data/connectivity_HLS2.csv"

    def test_init_with_custom_file(self, monkeypatch):
        # Mock parse_connectivity_file to avoid actual file operations
        monkeypatch.setattr(GaudiRouting, "parse_connectivity_file", lambda self: None)
        routing = GaudiRouting("custom_file.csv")
        assert routing.connectivity_file == "custom_file.csv"

    def test_parse_connectivity_file(self, mock_csv_file):
        routing = GaudiRouting(mock_csv_file)
        assert len(routing.connections) == 4
        
        # Check first connection structure
        assert routing.connections[0]['source']['module_id'] == 0
        assert routing.connections[0]['source']['port'] == 1
        assert routing.connections[0]['destination']['module_id'] == 1
        assert routing.connections[0]['destination']['port'] == 1

    def test_get_module_connections(self, mock_csv_file):
        routing = GaudiRouting(mock_csv_file)
        module_conns = routing.get_module_connections()
        
        assert 0 in module_conns
        assert 'outgoing' in module_conns[0]
        assert 'incoming' in module_conns[0]
        assert len(module_conns[0]['outgoing']) == 1
        
        # Filter by module_id
        module_conns = routing.get_module_connections(module_id=1)
        assert len(module_conns) > 0
        assert 1 in module_conns

    def test_match_devices_to_connections(self, mock_csv_file):
        routing = GaudiRouting(mock_csv_file)
        
        # Mock devices dictionary
        devices = {
            "0000:4d:00.0": {"module_id": 0, "bus_id": "0000:4d:00.0"},
            "0000:4e:00.0": {"module_id": 1, "bus_id": "0000:4e:00.0"},
            "0000:4f:00.0": {"module_id": 2, "bus_id": "0000:4f:00.0"}
        }
        
        matches = routing.match_devices_to_connections(devices)
        assert len(matches) > 0
        
        # Check structure of first match
        assert 'source' in matches[0]
        assert 'destination' in matches[0]
        assert 'source_device_id' in matches[0]
        assert 'dest_device_id' in matches[0]