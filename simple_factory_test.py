#!/usr/bin/env python3
"""
Simple test for GaudiDeviceFactory
"""
from gaudi_connect.devices.GaudiDeviceFactory import GaudiDeviceFactory

def main():
    factory = GaudiDeviceFactory()
    devices = factory.get_devices_by_module_id()
    print(f'Found {len(devices)} devices by module ID')
    
    for module_id, device in sorted(devices.items()):
        print(f'Module {module_id}: Bus ID {device.bus_id}, Index {device.index}, IB Name {device.ib_name}')

if __name__ == "__main__":
    main()
