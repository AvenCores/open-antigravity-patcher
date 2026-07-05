//go:build windows

package main

import (
	"os/exec"
	"syscall"
	"unsafe"
)

const (
	stdOutputHandle                 = uint32(0xfffffff5) // -11
	enableVirtualTerminalProcessing = uint32(0x0004)
)

func setupPlatformConsole() {
	// Set console page to UTF-8
	exec.Command("cmd", "/c", "chcp 65001 >nul").Run()

	kernel32 := syscall.NewLazyDLL("kernel32.dll")
	getConsoleMode := kernel32.NewProc("GetConsoleMode")
	setConsoleMode := kernel32.NewProc("SetConsoleMode")
	getStdHandle := kernel32.NewProc("GetStdHandle")

	handle, _, _ := getStdHandle.Call(uintptr(stdOutputHandle))
	if handle == 0 || handle == uintptr(syscall.InvalidHandle) {
		UseColor = false
		return
	}

	var mode uint32
	ret, _, _ := getConsoleMode.Call(handle, uintptr(unsafe.Pointer(&mode)))
	if ret == 0 {
		UseColor = false
		return
	}

	newMode := mode | enableVirtualTerminalProcessing
	if newMode == mode {
		UseColor = true
		return
	}

	ret, _, _ = setConsoleMode.Call(handle, uintptr(newMode))
	UseColor = (ret != 0)
}
