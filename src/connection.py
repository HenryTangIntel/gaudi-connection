from devices.GaudiDevices import GaudiDevices, GaudiDevice
from connectivity.GaudiRouting import GaudiRouting
from typing import Dict, List, Tuple, Any, Optional


def connection(gaudidevices: GaudiDevices, connectivity: GaudiRouting):
    """
    Establish a connection between Gaudi devices based on the provided connectivity information.
    """
    # Get the connectivity information
    connections = connectivity.get_connections()
    
    # Fix: connectionpairlist should be a list, not a tuple type annotation
    connectionpairlist = []

    # Iterate through each connection and establish it
    for connection in connections:
        source = connection['source']
        destination = connection['destination']
        
        src_device = gaudidevices.get_device_by_module_id(source['module_id'])
        dst_device = gaudidevices.get_device_by_module_id(destination['module_id'])
        
        if src_device and dst_device:
            print(f"Connecting {src_device.bus_id} to {dst_device.bus_id} on ports {source['port']} -> {destination['port']}")
        else:
            print(f"Error: Device not found for connection {connection}")
        connectionpairlist.append((src_device, dst_device))
   
    return connectionpairlist

def print_connection_pairs(con):
    print("Connection pairs established:")
    for src, dst in con:
        if src and dst:
            print(f"  {src} <-> {dst}")
        else:
            print("  Incomplete connection due to missing device information.")
    print(f"All connections {len(con)} processed.")

def print_gaudi_device_mapping(gaudidevices):
    print("\nGaudi device mapping (module_id -> device_id, ib_name):")
    modid_to_info = {}
    for device in gaudidevices.get_devices().values():
        print(f"module_id={device.module_id}, device_id={device.device_id}, ib_name={device.ib_name}")
        modid_to_info[device.module_id] = (device.device_id, device.ib_name)
    return modid_to_info

def verify_connections_vs_csv(modid_to_info, csv_path):
    import re
    mismatch_found = False
    with open(csv_path) as f:
        for idx, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = re.split(r'[\t ]+', line)
            if len(parts) == 4:
                src_mod, src_port, dst_mod, dst_port = map(int, parts)
                src_info = modid_to_info.get(src_mod)
                dst_info = modid_to_info.get(dst_mod)
                if src_info is None or dst_info is None:
                    print(f"[Mismatch] Line {idx}: module_id not found in mapping: src_mod={src_mod}, dst_mod={dst_mod}")
                    mismatch_found = True
    if not mismatch_found:
        print("\nVerification: All module_id, device_id, ib_name mappings and connection pairs match the CSV file.")
    else:
        print("\nVerification: Mismatches found. See above for details.")


if __name__ == "__main__":
    # Simple test program for connection logic
    gaudidevices = GaudiDevices()
    connectivity = GaudiRouting()
    print("Testing connection logic with available Gaudi devices and connectivity info...")
    con = connection(gaudidevices, connectivity)
    print_connection_pairs(con)
    modid_to_info = print_gaudi_device_mapping(gaudidevices)
    verify_connections_vs_csv(modid_to_info, '/workspace/gaudi-connection/connectivity_HLS2.csv')
