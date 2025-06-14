# Gaudi Connection Testing Framework

A framework for testing connectivity between Gaudi and InfiniBand devices in a multi-device setup.

## Overview

This framework provides tools to validate connectivity between Gaudi devices based on connectivity information provided in CSV files. It supports checking InfiniBand port status before attempting connections and reports detailed results.

## Directory Structure

```
gaudi-connection/
├── bin/                    # Executable scripts
│   └── gaudi-connection-test  # Main executable
├── gaudi_connect/          # Main package
│   ├── __init__.py
│   ├── connection_test_main.py  # Main testing logic
│   ├── connectivity/       # Connectivity parsing modules
│   │   ├── __init__.py
│   │   └── gaudi2_connect.py
│   ├── devices/           # Device detection modules
│   │   ├── __init__.py
│   │   ├── gaudi_devices.py
│   │   └── infiniband_devices.py
│   ├── tests/            # Test utilities
│   │   └── __init__.py
│   └── utils/            # Utility functions
│       └── __init__.py
├── examples/              # Example connectivity files (legacy)
└── README.md              # This file
```

## Usage

To run the connection tester:

```bash
./bin/gaudi-connection-test [options]
```

### Options

- `-t, --type {HLS2,HLS2pcie,HLS3,HLS3pcie}`: Select predefined connectivity type
- `-f, --file PATH`: Path to a custom connectivity CSV file
- `-p, --parallel`: Run tests in parallel
- `--timeout SECONDS`: Timeout in seconds for parallel execution (default: 30)
- `-v, --verbose`: Show detailed failure information
- `-j, --json`: Output results in JSON format
- `-n, --no-port-check`: Skip checking InfiniBand port status
- `-r, --real`: Use real connection APIs instead of simulation
### Examples

Test HLS2 connectivity:
```bash
./bin/gaudi-connection-test -t HLS2 -v
```

Run tests in parallel:
```bash
./bin/gaudi-connection-test -p -t HLS3
```

## Individual Components

You can also use the individual modules separately:

### Getting Gaudi Device Information

```bash
python3 -m gaudi_connect.devices.gaudi_devices [options]
```

Options:
- `-d, --detailed`: Show detailed device information
- `-j, --json`: Output in JSON format

### Getting InfiniBand Device Information

```bash
python3 -m gaudi_connect.devices.infiniband_devices [options]
```

Options:
- `-d, --detailed`: Show detailed port information
- `-j, --json`: Output in JSON format

### Parsing Connectivity Information

```bash
python3 -m gaudi_connect.connectivity.gaudi2_connect [options]
```

Options:
- `-f, --file FILE`: Path to the connectivity CSV file
- `-m, --module ID`: Show connections for a specific module ID
- `-j, --json`: Output in JSON format
- `-d, --detailed`: Show detailed connection information

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

## Device Support

Currently supports:
- HLS2 systems (default)
- HLS2pcie systems
- HLS3 systems
- HLS3pcie systems

## Port Status Checking

By default, the framework checks the status of InfiniBand ports before attempting connections
and reports failures when ports are inactive. This can be disabled with the `-n/--no-port-check` option.
