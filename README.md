# Gaudi Connection Reporting Tool

A tool for reporting connectivity between Gaudi devices in an HLS2 system based on routing information.

## Overview

This tool provides utilities to discover Gaudi devices on a system, parse routing information from CSV files, and generate reports about which devices can connect to each other. It supports outputting connection data in both human-readable and JSON formats.

## Directory Structure

```
gaudi-connection/
├── main_gc.py             # Main executable Python script
├── run_gc.sh              # Wrapper script for easy execution
├── src/                   # Source code directory
│   ├── __init__.py
│   ├── connectivity/      # Connectivity parsing modules
│   │   ├── __init__.py
│   │   └── GaudiRouting.py
│   └── devices/           # Device detection modules
│       ├── __init__.py
│       ├── GaudiDeviceFactory.py
│       ├── GaudiDevices.py
│       └── InfinibandDevices.py
├── connectivity_HLS2.csv  # Local copy of connectivity data (fallback)
├── connectivity_test.csv  # Test connectivity data
└── README.md              # This file
```

## Usage

The easiest way to run the tool is using the wrapper script:

```bash
./run_gc.sh [options]
```

Alternatively, you can run the Python script directly:

```bash
python3 main_gc.py [options]
```

### Options

- `-c, --connectivity FILE`: Path to connectivity CSV file (default: official HLS2 connectivity file)
- `-s, --summarize`: Show summary of discovered devices
- `-r, --routing`: Show routing information between devices (default behavior)
- `-j, --json`: Output results in JSON format
- `-o, --output FILE`: Write output to a file
### Examples

Show device summary:
```bash
./run_gc.sh -s
```

Show routing information (default):
```bash
./run_gc.sh
```

Output in JSON format:
```bash
./run_gc.sh -j
```

Output to a file:
```bash
./run_gc.sh -o connections.txt
```

Use a custom connectivity file:
```bash
./run_gc.sh -c /path/to/connectivity.csv
```

## Connectivity File Format

The connectivity CSV files should follow this format:
```
# Comments start with #
<source_module_id> <source_port> <destination_module_id> <destination_port>
```

Example:
```
# Connect module 0 to module 1
0 7 1 7
0 6 1 6
```

## Features

- Automatic discovery of Gaudi and InfiniBand devices on the system
- Parsing of HLS2 routing information from official Habana connectivity files
- Reporting of all possible connections between discovered Gaudi devices
- Display of GID (Global Identifier) information for each connection
- Support for both human-readable and JSON output formats
- Fallback to local connectivity files if the official files aren't accessible

## Official Connectivity Files

The tool looks for official connectivity files at:
- HLS2: `/opt/habanalabs/perf-test/scale_up_tool/internal_data/connectivity_HLS2.csv`
- HLS2-PCIE: `/opt/habanalabs/perf-test/scale_up_tool/internal_data/connectivity_HLS2PCIE.csv`

If these files are not accessible, the tool falls back to local versions included in this repository.
