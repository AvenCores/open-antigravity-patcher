package main

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io"
	"os"
	"os/exec"
	"os/user"
	"path/filepath"
	"runtime"
	"strings"
	"time"
)

func fileHash(path string) string {
	f, err := os.Open(path)
	if err != nil {
		return ""
	}
	defer f.Close()

	h := sha256.New()
	if _, err := io.Copy(h, f); err != nil {
		return ""
	}
	return hex.EncodeToString(h.Sum(nil))
}

func fileSize(path string) int64 {
	fi, err := os.Stat(path)
	if err != nil {
		return 0
	}
	return fi.Size()
}

func formatBytes(sizeBytes int64) string {
	if sizeBytes >= 1024*1024 {
		return fmt.Sprintf("%.1f MB", float64(sizeBytes)/1024/1024)
	}
	if sizeBytes >= 1024 {
		return fmt.Sprintf("%.1f KB", float64(sizeBytes)/1024)
	}
	return fmt.Sprintf("%d B", sizeBytes)
}

func fixPosixPermissions(path string) {
	if runtime.GOOS == "windows" || getuid() != 0 {
		return
	}
	sudoUID := os.Getenv("SUDO_UID")
	sudoGID := os.Getenv("SUDO_GID")
	if sudoUID != "" && sudoGID != "" {
		exec.Command("chown", "-R", sudoUID+":"+sudoGID, path).Run()
	}
}

func getPosixInvokingUserHome() string {
	if runtime.GOOS == "windows" {
		return ""
	}
	sudoUID := os.Getenv("SUDO_UID")
	if sudoUID != "" {
		if u, err := user.LookupId(sudoUID); err == nil {
			return u.HomeDir
		}
	}
	sudoUser := os.Getenv("SUDO_USER")
	if sudoUser != "" {
		if u, err := user.Lookup(sudoUser); err == nil {
			return u.HomeDir
		}
	}
	if home := os.Getenv("HOME"); home != "" {
		return home
	}
	if u, err := user.Current(); err == nil {
		return u.HomeDir
	}
	return ""
}

func backupJsonFile(path string) string {
	if _, err := os.Stat(path); os.IsNotExist(err) {
		return ""
	}

	timestamp := time.Now().Format("20060102-150405")
	base := fmt.Sprintf("%s.bak-%s", path, timestamp)
	backupPath := base
	counter := 1
	for {
		if _, err := os.Stat(backupPath); os.IsNotExist(err) {
			break
		}
		counter++
		backupPath = fmt.Sprintf("%s-%d", base, counter)
	}

	if err := copyFile(path, backupPath); err != nil {
		return ""
	}
	fixPosixPermissions(backupPath)
	return backupPath
}

func copyFile(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()

	out, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer out.Close()

	if _, err = io.Copy(out, in); err != nil {
		return err
	}

	si, err := os.Stat(src)
	if err == nil {
		os.Chmod(dst, si.Mode())
	}
	return nil
}

func findAppBundle(path string) string {
	p, err := filepath.Abs(path)
	if err != nil {
		return ""
	}
	for {
		if strings.HasSuffix(p, ".app") {
			return p
		}
		parent := filepath.Dir(p)
		if parent == p {
			break
		}
		p = parent
	}
	return ""
}

func resignMacosBundle(mainJsPath string) {
	if runtime.GOOS != "darwin" {
		return
	}

	appPath := findAppBundle(mainJsPath)
	if appPath == "" {
		return
	}

	info("Re-signing " + filepath.Base(appPath) + " (ad-hoc)...")
	cmd := exec.Command("codesign", "--force", "--deep", "--sign", "-", appPath)
	if err := cmd.Run(); err != nil {
		warn("codesign failed: " + err.Error())
		return
	}
	consoleOk("Ad-hoc signature applied")

	// remove quarantine
	exec.Command("xattr", "-dr", "com.apple.quarantine", appPath).Run()
}

func resignMacosBinary(path string) {
	if runtime.GOOS != "darwin" {
		return
	}

	realPath, err := filepath.EvalSymlinks(path)
	if err != nil {
		realPath = path
	}

	info("Re-signing " + filepath.Base(realPath) + " (ad-hoc)...")
	cmd := exec.Command("codesign", "--force", "--sign", "-", realPath)
	if err := cmd.Run(); err != nil {
		warn("codesign failed: " + err.Error())
		return
	}
	consoleOk("Ad-hoc signature applied")
}
