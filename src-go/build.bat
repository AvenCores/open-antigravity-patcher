@echo off
rem Script to build the Open AG Patcher in Go for all platforms on Windows

if not exist dist mkdir dist

echo Fetching dependencies...
go mod tidy

rem Install go-winres if not present in path
where go-winres >nul 2>nul
if %errorlevel% neq 0 (
    echo Installing go-winres...
    go install github.com/tc-hib/go-winres@latest
)

rem Add default Go bin path to PATH
set PATH=%PATH%;%USERPROFILE%\go\bin

echo Compiling Windows resources (icon, metadata, UAC)...
go-winres make

echo Building for Windows (x64)...
set GOOS=windows
set GOARCH=amd64
go build -ldflags="-s -w" -o dist/Open_AG_Patcher_Windows.exe

echo Building for Windows (x86)...
set GOOS=windows
set GOARCH=386
go build -ldflags="-s -w" -o dist/Open_AG_Patcher_Windows_x86.exe

echo Building for Windows (ARM64)...
set GOOS=windows
set GOARCH=arm64
go build -ldflags="-s -w" -o dist/Open_AG_Patcher_Windows_arm64.exe

echo Building for Linux (x64)...
set GOOS=linux
set GOARCH=amd64
go build -ldflags="-s -w" -o dist/open_ag_patcher_linux_x64

echo Building for Linux (ARM64)...
set GOOS=linux
set GOARCH=arm64
go build -ldflags="-s -w" -o dist/open_ag_patcher_linux_arm64

echo Building for macOS (Intel)...
set GOOS=darwin
set GOARCH=amd64
go build -ldflags="-s -w" -o dist/open_ag_patcher_macos_intel

echo Building for macOS (Apple Silicon)...
set GOOS=darwin
set GOARCH=arm64
go build -ldflags="-s -w" -o dist/open_ag_patcher_macos_arm64

echo Build complete! Check the dist/ directory.
