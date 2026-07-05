//go:build !windows

package main

import (
	"os"
	"os/exec"
	"strconv"
	"syscall"
)

func isAdmin() bool {
	return os.Getuid() == 0
}

func runAsAdmin() bool {
	return true
}

func getuid() int {
	return os.Getuid()
}

func setCmdUser(cmd *exec.Cmd, uidStr, gidStr, userStr string) {
	uid, err1 := strconv.Atoi(uidStr)
	gid, err2 := strconv.Atoi(gidStr)
	if err1 == nil && err2 == nil {
		cmd.SysProcAttr = &syscall.SysProcAttr{
			Credential: &syscall.Credential{
				Uid: uint32(uid),
				Gid: uint32(gid),
			},
		}
	}
}

func relaunchWithSudo() bool {
	sudoPath, err := exec.LookPath("sudo")
	if err != nil {
		return false
	}
	args := append([]string{"sudo", os.Args[0]}, os.Args[1:]...)
	err = syscall.Exec(sudoPath, args, os.Environ())
	return err == nil
}
