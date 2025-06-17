#!/bin/bash
# Wrapper script for main_gc.py that sets the correct PYTHONPATH

# Set the PYTHONPATH to the directory containing the 'src' module
cd "$(dirname "$0")"

# Default connectivity files
SYSTEM_HLS2_CONNECTIVITY="/opt/habanalabs/perf-test/scale_up_tool/internal_data/connectivity_HLS2.csv"
LOCAL_HLS2_CONNECTIVITY="$(pwd)/connectivity_test.csv"

# Check if the system connectivity file exists
if [ -f "$SYSTEM_HLS2_CONNECTIVITY" ] && [ -r "$SYSTEM_HLS2_CONNECTIVITY" ]; then
    DEFAULT_CONNECTIVITY="$SYSTEM_HLS2_CONNECTIVITY"
    echo "Using official HLS2 connectivity file: $DEFAULT_CONNECTIVITY"
else
    # Fall back to local test connectivity file
    DEFAULT_CONNECTIVITY="$LOCAL_HLS2_CONNECTIVITY"
    echo "Warning: Official HLS2 connectivity file not accessible. Using local test file: $DEFAULT_CONNECTIVITY"
fi

# Function to print usage information
print_usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -r, --routes   Show routing connections"
    echo "  -j, --json     Output in JSON format"
    echo "  -c, --connectivity PATH  Specify connectivity file path"
    echo "  -o, --output PATH        Output file for connection data (JSON format)"
    echo "  -v, --verify             Verify connections have active ports"
    echo ""
    echo "Examples:"
    echo "  $0                       Show device summary"
    echo "  $0 -r                    Show routing connections using official HLS2 connectivity file"
    echo "  $0 -r -j                 Show routing connections in JSON format"
    echo "  $0 -r -j -o output.json  Save routing connections to file"
    echo ""
    echo "Notes:"
    echo "  By default, the script uses the official HLS2 connectivity file from:"
    echo "  $SYSTEM_HLS2_CONNECTIVITY"
    echo "  If this file is not accessible, it uses a local test file."
    echo ""
    exit 0
}

# Check for special options
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    print_usage
fi

# Process arguments to check if a connectivity file was specified
CONNECTIVITY_SPECIFIED=0
for ((i=1; i<=$#; i++)); do
    if [[ "${!i}" == "-c" || "${!i}" == "--connectivity" ]]; then
        CONNECTIVITY_SPECIFIED=1
        break
    fi
done

export PYTHONPATH=$(pwd)

# Add the default HLS2 connectivity file if none was specified
if [ $CONNECTIVITY_SPECIFIED -eq 0 ] && [ -n "$DEFAULT_CONNECTIVITY" ]; then
    python main_gc.py -c "$DEFAULT_CONNECTIVITY" "$@"
else
    python main_gc.py "$@"
fi
