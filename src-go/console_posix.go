//go:build !windows

package main

func setupPlatformConsole() {
	UseColor = true
}
