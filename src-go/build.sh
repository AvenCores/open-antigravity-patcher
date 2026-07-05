#!/bin/bash
# Script to build the Open AG Patcher in Go for all platforms

# Create output directory
mkdir -p dist

echo "Fetching dependencies..."
go mod tidy

# Install go-winres if not present in path
if ! command -v go-winres &> /dev/null; then
    echo "Installing go-winres..."
    go install github.com/tc-hib/go-winres@latest
fi

# Add default Go bin path to PATH
export PATH=$PATH:$HOME/go/bin

echo "Compiling Windows resources (icon, metadata, UAC)..."
go-winres make

echo "Building for Windows (x64)..."
GOOS=windows GOARCH=amd64 go build -ldflags="-s -w" -o dist/Open_AG_Patcher_Windows.exe

echo "Building for Windows (x86)..."
GOOS=windows GOARCH=386 go build -ldflags="-s -w" -o dist/Open_AG_Patcher_Windows_x86.exe

echo "Building for Linux (x64)..."
GOOS=linux GOARCH=amd64 go build -ldflags="-s -w" -o dist/open_ag_patcher_linux_x64

echo "Building for Linux (ARM64)..."
GOOS=linux GOARCH=arm64 go build -ldflags="-s -w" -o dist/open_ag_patcher_linux_arm64

echo "Building for macOS (Intel)..."
GOOS=darwin GOARCH=amd64 go build -ldflags="-s -w" -o dist/open_ag_patcher_macos_intel

echo "Building for macOS (Apple Silicon)..."
GOOS=darwin GOARCH=arm64 go build -ldflags="-s -w" -o dist/open_ag_patcher_macos_arm64

echo "Build complete! Check the dist/ directory."
