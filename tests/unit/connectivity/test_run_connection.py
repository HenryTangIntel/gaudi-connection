import os
import json
import pytest
import tempfile
from unittest.mock import patch, MagicMock
from src.connectivity.RunConnection import RunConnection

class TestRunConnection:
    @pytest.fixture
    def run_connection(self, mock_csv_file):
        with patch('src.devices.GaudiDeviceFactory.GaudiDeviceFactory') as mock_factory:
            factory_instance = mock_factory.return_value
            
            # Mock get_devices_by_module_id
            factory_instance.get_devices_by_module_id.return_value = {
                0: MagicMock(bus_id="0000:4d:00.0", ib_name="ibp155s0", ports={1: {"gid": "ff:ff:ff:ff"}}),
                1: MagicMock(bus_id="0000:4e:00.0", ib_name="ibp156s0", ports={1: {"gid": "ff:ff:ff:ff"}})
            }
            
            # Mock get_device_by_bus_id
            factory_instance.get_device_by_bus_id.side_effect = lambda bus_id: {
                "0000:4d:00.0": MagicMock(bus_id="0000:4d:00.0", ib_name="ibp155s0", ports={1: {"gid": "ff:ff:ff:ff"}}),
                "0000:4e:00.0": MagicMock(bus_id="0000:4e:00.0", ib_name="ibp156s0", ports={1: {"gid": "ff:ff:ff:ff"}})
            }.get(bus_id)
            
            # Mock get_active_ports
            factory_instance.get_active_ports.return_value = {
                "0000:4d:00.0": [1, 2],
                "0000:4e:00.0": [1]
            }
            
            runner = RunConnection(mock_csv_file)
            yield runner

    def test_make_connections(self, run_connection):
        connections = run_connection.make_connections(display_output=False)
        assert isinstance(connections, list)
        assert len(connections) > 0
        
        # Check structure of connections
        assert 'source' in connections[0]
        assert 'destination' in connections[0]
        assert 'module_id' in connections[0]['source']
        assert 'port' in connections[0]['source']
        assert 'bus_id' in connections[0]['source']
        assert 'ib_name' in connections[0]['source']

    def test_filter_by_module_id(self, run_connection):
        connections = run_connection.make_connections(display_output=False)
        filtered = run_connection.filter_by_module_id(connections, 0)
        
        assert all(conn['source']['module_id'] == 0 or conn['destination']['module_id'] == 0 
                  for conn in filtered)

    def test_filter_by_port(self, run_connection):
        connections = run_connection.make_connections(display_output=False)
        filtered = run_connection.filter_by_port(connections, 1)
        
        assert all(conn['source']['port'] == 1 or conn['destination']['port'] == 1 
                  for conn in filtered)

    def test_save_to_json(self, run_connection):
        connections = run_connection.make_connections(display_output=False)
        
        # Create temp file for output
        with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as temp:
            temp_path = temp.name
        
        try:
            # Test saving to JSON
            run_connection.save_to_json(temp_path)
            
            # Verify JSON was written and can be read
            with open(temp_path, 'r') as f:
                data = json.load(f)
                assert isinstance(data, list)
                assert len(data) > 0
        finally:
            os.unlink(temp_path)