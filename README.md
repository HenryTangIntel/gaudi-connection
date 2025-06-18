# Gaudi Connection Reporting Tool

A tool for reporting connectivity between Gaudi devices in an HLS2 system based on routing information.

## Overview

This tool provides utilities to discover Gaudi devices on a system, parse routing information from CSV files, and generate reports about which devices can connect to each other. It supports outputting connection data in both human-readable and JSON formats. All connection outputs now include port information for both source and destination devices.

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
- `-d, --devices`: Show summary of discovered devices
- `-r, --routes`: Show routing information between devices (default behavior)
- `-j, --json`: Output results in JSON format
- `-v, --verify`: Verify connections have active ports
- `-o, --output FILE`: Write output to a file (JSON format)
- `-p, --perf`: Run performance tests on connections (prints perf_test command lines as a dry run if GIDs are missing or perf_test is not executable)
### Examples

Show device summary:
```bash
./run_gc.sh -d
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
./run_gc.sh -o connections.json
```

Use a custom connectivity file:
```bash
./run_gc.sh -c /path/to/connectivity.csv
```

Run performance tests on connections:
```bash
./run_gc.sh -r -p
```


Run performance tests and save results to a file:
```bash
./run_gc.sh -r -p -o perf_results.json
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
- Performance testing between connected Gaudi devices using the built-in `perf_test` utility
- Summary reporting of performance test results with detailed output option
- Filtering connections by module ID or port number
- Verification of active ports on connections
- Class-based structure for better code organization and reuse


## Performance Testing

The tool includes functionality to run performance tests between connected Gaudi devices using the Habana `perf_test` utility. Performance testing helps measure bandwidth, latency, and other metrics between Gaudi devices.

### How Performance Testing Works

1. For each connection discovered, the tool:
   - Extracts source and destination device information including GIDs and port numbers (all outputs now include port info)
   - If GIDs are missing or the `perf_test` utility is not found/executable, the tool prints the server and client perf_test command lines as a dry run for each connection, and skips execution.
   - Otherwise, runs the `/opt/habanalabs/perf-test/perf_test` utility in server mode on the source device and client mode on the destination device, collecting and processing the results.

2. After all tests complete, a summary is displayed showing:
   - Total number of connections tested
   - Number of successful tests
   - Number of failed tests
   - Number of errors or skipped tests

### Performance Test Output

When using the `-o` or `--output` option with `-p`, the tool saves detailed performance test results in JSON format.

### Requirements

- The `/opt/habanalabs/perf-test/perf_test` utility must be installed and executable for real performance tests to run
- Running performance tests requires appropriate permissions to access the devices

## Official Connectivity Files

The tool looks for official connectivity files at:
- HLS2: `/opt/habanalabs/perf-test/scale_up_tool/internal_data/connectivity_HLS2.csv`
- HLS2-PCIE: `/opt/habanalabs/perf-test/scale_up_tool/internal_data/connectivity_HLS2PCIE.csv`

If these files are not accessible, the tool falls back to local versions included in this repository.

## Testing

To run the tests:

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run specific test modules
pytest tests/unit/connectivity/test_gaudi_routing.py

# Run with coverage report
pytest --cov=src
```
