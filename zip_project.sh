#!/bin/bash

# Exit immediately if any command fails
set -e

# Get the current project directory name
PROJECT_DIR_NAME=$(basename "$PWD")

# Prompt for build directory name
DEFAULT_BUILD_DIR="${PROJECT_DIR_NAME}_build"
read -p "Use '$DEFAULT_BUILD_DIR' as build directory? [Y/n]: " CONFIRM

if [[ "$CONFIRM" =~ ^[Nn] ]]; then
    read -p "Enter custom build directory name: " CUSTOM_BUILD_DIR
    if [[ -z "$CUSTOM_BUILD_DIR" ]]; then
        echo "Error: No directory name provided."
        exit 1
    fi
    BUILD_DIR="$CUSTOM_BUILD_DIR"
else
    BUILD_DIR="$DEFAULT_BUILD_DIR"
fi

ZIP_FILE="${BUILD_DIR}.zip"

# Clean up any previous build
rm -rf "$BUILD_DIR" "$ZIP_FILE"

# Create the new build directory
mkdir "$BUILD_DIR"

# Copy assets folder
cp -r assets "$BUILD_DIR/assets"

# Find the .exe file in build/Release
EXE_FILE=$(find build/Release -maxdepth 1 -type f -iname "*.exe" | head -n 1)

if [[ -z "$EXE_FILE" ]]; then
    echo "Error: No .exe file found in build/Release"
    exit 1
fi

# Copy the executable to the build directory
cp "$EXE_FILE" "$BUILD_DIR/$(basename "$EXE_FILE")"

# Zip the build directory
zip -r "$ZIP_FILE" "$BUILD_DIR"

echo "Packaging complete: $ZIP_FILE"

