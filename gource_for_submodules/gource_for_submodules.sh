#!/bin/bash

# Function to display help
show_help() {
    echo "Usage: $0 [options] [gource_options]"
    echo
    echo "This script generates a Gource visualization of Git submodules in the current repository."
    echo
    echo "It finds all Git submodules, creates custom Gource log files for each, and combines them into a single log file for visualization."
    echo
    echo "Arguments:"
    echo "  gource_options  Optional arguments to be passed to the Gource command."
    echo "                  For example: --seconds-per-day 0.1 --max-files 100"
    echo
    echo "Options:"
    echo "  -h, --help           Display this help message."
    echo "  --exclude <list>     Comma-separated list of submodules to exclude."
    echo
}

# Variables
exclude_submodules=()

# Parse options
while [[ "$1" != "" ]]; do
    case "$1" in
        -h | --help)
            show_help
            exit 0
            ;;
        --exclude)
            shift
            exclude_submodules=($(echo "$1" | tr ',' ' '))
            ;;
        *)
            # Collect Gource options
            gource_args+="$1 "
            ;;
    esac
    shift
done

# Function to find all Git submodules
find_submodules() {
    git submodule | awk '{ print $2 }'
}

# Check if the script is executed in a Git repository
if [ ! -d ".git" ]; then
    echo "Error: This script must be run inside a Git repository."
    exit 1
fi

# Create a directory for the log files in the root folder
log_dir="./gource_logs"
mkdir -p "$log_dir"

# Find all submodules
echo "Finding submodules..."
submodules=$(find_submodules)

# Check if any submodules were found
if [ -z "$submodules" ]; then
    echo "No submodules found."
    exit 0
fi

# Generate custom log files for each submodule except excluded ones
for repo in $submodules; do
    repo_name=$(basename "$repo")
    
    # Skip excluded submodules
    if [[ " ${exclude_submodules[@]} " =~ " $repo_name " ]]; then
        echo "Excluding submodule $repo_name..."
        continue
    fi

    echo "Generating log for submodule $repo_name..."
    
    # Generate Gource custom log
    gource --output-custom-log "$log_dir/log_$repo_name.txt" "$repo"
    
    # Modify paths to separate the repos
    sed -i -r "s#(.+)\|#\1|/$repo_name#" "$log_dir/log_$repo_name.txt"
done

# Combine the logs together and sort them
echo "Combining logs..."
cat "$log_dir/log_"*.txt | sort -n > "$log_dir/combined.txt"

# Feed the result into Gource with optional arguments
echo "Generating Gource visualization..."
gource "$log_dir/combined.txt" --hide-root $gource_args

echo "Gource visualization generated successfully."
