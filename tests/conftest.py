import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock

@pytest.fixture
def mock_csv_file():
    """Create a temporary mock CSV file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as temp:
        temp.write("0\t1\t1\t1\n")
        temp.write("1\t2\t2\t2\n")
        temp.write("2\t3\t3\t3\n")
        temp.write("# This is a comment\n")
        temp.write("3\t4\t4\t4\n")
        temp_path = temp.name
    
    yield temp_path
    os.unlink(temp_path)

@pytest.fixture
def mock_gaudi_devices():
    """Mock GaudiDevices class to avoid hardware dependencies."""
    with patch('src.devices.GaudiDevices.GaudiDevices') as mock:
        devices = mock.return_value
        devices.get_device_objects.return_value = {
            "0000:4d:00.0": {
                "module_id": 0,
                "bus_id": "0000:4d:00.0",
                "ib_name": "ibp155s0",
                "device_id": "hbl_2",
                "ports": {
                    1: {"state": "active", "gid": "ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff"},
                    2: {"state": "active", "gid": "fe80:0000:0000:0000:b2fd:0bff:fed6:11d1"}
                }
            },
            "0000:4e:00.0": {
                "module_id": 1,
                "bus_id": "0000:4e:00.0",
                "ib_name": "ibp156s0",
                "device_id": "hbl_3",
                "ports": {
                    1: {"state": "active", "gid": "ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff"}
                }
            }
        }
        yield devices