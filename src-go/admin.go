package main

import (
	"os/exec"
	"runtime"
	"strings"
)

func terminateProcesses(names []string) bool {
	success := false
	for _, name := range names {
		var cmd *exec.Cmd
		if runtime.GOOS == "windows" {
			execName := name
			if !strings.HasSuffix(strings.ToLower(name), ".exe") {
				execName = name + ".exe"
			}
			cmd = exec.Command("taskkill", "/F", "/IM", execName)
		} else {
			cmd = exec.Command("pkill", "-f", name)
		}
		if err := cmd.Run(); err == nil {
			success = true
		}
	}
	return success
}
