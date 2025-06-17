import pytest
from unittest.mock import patch, MagicMock
from src.devices.GaudiDeviceFactory import GaudiDeviceFactory

class TestGaudiDeviceFactory:
    @pytest.fixture
    def factory(self, mock_gaudi_devices):
        with patch('src.devices.InfinibandDevices.InfinibandDevices') as mock_ib:
            # Mock InfinibandDevices
            mock_ib_instance = mock_ib.return_value
            mock_ib_instance.get_ib_ports.return_value = {
                "ibp155s0": {
                    1: {"state": "active", "gid": "ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff"},
                    2: {"state": "down"}
                },
                "ibp156s0": {
                    1: {"state": "active", "gid": "fe80:0000:0000:0000:b2fd:0bff:fed6:11d1"}
                }
            }
            
            factory = GaudiDeviceFactory()
            yield factory

    def test_get_devices_by_module_id(self, factory):
        devices = factory.get_devices_by_module_id()
        assert len(devices) > 0
        # Check that devices are organized by module_id
        assert all(isinstance(key, int) for key in devices.keys())

    def test_get_all_devices(self, factory):
        devices = factory.get_all_devices()
        assert len(devices) > 0
        # Check that devices are organized by bus_id
        assert all(isinstance(key, str) for key in devices.keys())
        assert all(":" in key for key in devices.keys())

    def test_get_device_by_bus_id(self, factory):
        # Should return a device for a valid bus_id
        with patch.object(factory, 'get_all_devices') as mock_get:
            mock_get.return_value = {
                "0000:4d:00.0": MagicMock(bus_id="0000:4d:00.0")
            }
            device = factory.get_device_by_bus_id("0000:4d:00.0")
            assert device is not None
            assert device.bus_id == "0000:4d:00.0"
        
        # Should return None for an invalid bus_id
        with patch.object(factory, 'get_all_devices') as mock_get:
            mock_get.return_value = {
                "0000:4d:00.0": MagicMock(bus_id="0000:4d:00.0")
            }
            assert factory.get_device_by_bus_id("invalid") is None

    def test_get_active_ports(self, factory):
        # Mock get_all_devices
        with patch.object(factory, 'get_all_devices') as mock_get:
            mock_get.return_value = {
                "0000:4d:00.0": MagicMock(
                    bus_id="0000:4d:00.0", 
                    ports={
                        1: {"is_active": True},
                        2: {"is_active": False}
                    }
                ),
                "0000:4e:00.0": MagicMock(
                    bus_id="0000:4e:00.0", 
                    ports={
                        1: {"is_active": True}
                    }
                )
            }
            
            active_ports = factory.get_active_ports()
            assert "0000:4d:00.0" in active_ports
            assert 1 in active_ports["0000:4d:00.0"]
            assert 2 not in active_ports["0000:4d:00.0"]  # port 2 is down