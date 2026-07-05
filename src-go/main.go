package main

import (
	"fmt"
	"os"
	"runtime"
)

func main() {
	setupConsole()

	if runtime.GOOS == "windows" {
		if os.Getenv("SKIP_ELEVATION") != "1" && !isAdmin() {
			if runAsAdmin() {
				os.Exit(0)
			} else {
				fmt.Println("  [!] Could not elevate privileges. The script may fail to modify files.")
			}
		}
	} else {
		// POSIX (Linux/macOS)
		if !isAdmin() {
			fmt.Println("  [!] Root access is required to patch files in the root directory.")
			if confirmed("Re-launch with sudo?") {
				if !relaunchWithSudo() {
					fmt.Println("  [!] Failed to re-launch with sudo.")
					os.Exit(1)
				}
			} else {
				fmt.Println(color("  [!] Proceeding without root. Write errors are possible.", ColorYellow))
				fmt.Println()
			}
		}
	}

	runCli()
}
