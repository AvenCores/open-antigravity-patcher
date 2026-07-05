//go:build windows

package main

import (
	"os"
	"os/exec"
	"strings"
	"syscall"
	"unsafe"
)

func isAdmin() bool {
	shell32 := syscall.NewLazyDLL("shell32.dll")
	isUserAnAdmin := shell32.NewProc("IsUserAnAdmin")
	ret, _, _ := isUserAnAdmin.Call()
	return ret != 0
}

func runAsAdmin() bool {
	if isAdmin() {
		return true
	}

	shell32 := syscall.NewLazyDLL("shell32.dll")
	shellExecuteW := shell32.NewProc("ShellExecuteW")

	verbPtr, _ := syscall.UTF16PtrFromString("runas")
	exePtr, _ := syscall.UTF16PtrFromString(os.Args[0])

	var args []string
	if len(os.Args) > 1 {
		for _, arg := range os.Args[1:] {
			args = append(args, `"`+arg+`"`)
		}
	}
	argsStr := strings.Join(args, " ")
	argsPtr, _ := syscall.UTF16PtrFromString(argsStr)

	ret, _, _ := shellExecuteW.Call(
		0,
		uintptr(unsafe.Pointer(verbPtr)),
		uintptr(unsafe.Pointer(exePtr)),
		uintptr(unsafe.Pointer(argsPtr)),
		0,
		1, // SW_SHOWNORMAL
	)

	return ret > 32
}

func getuid() int {
	return -1
}

func setCmdUser(cmd *exec.Cmd, uidStr, gidStr string) {
	// No-op on Windows
}

func relaunchWithSudo() bool {
	return false
}
