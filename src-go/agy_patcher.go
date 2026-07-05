package main

import (
	"encoding/binary"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
	"time"
)

const BakExt = ".agybak"

type Gate struct {
	SigPrefix     []byte
	SigSuffix     []byte
	PatchedPrefix []byte
	PatchedSuffix []byte
	WildcardLen   int
	Fix           []byte
	Offset        int
	Desc          string
}

var (
	CliGate = Gate{
		SigPrefix:     []byte{0x48, 0x85, 0xc0, 0x0f, 0x84},
		SigSuffix:     []byte{0x80, 0x78, 0x08, 0x00, 0x0f, 0x85},
		PatchedPrefix: []byte{0x48, 0x85, 0xc0, 0x0f, 0x84},
		PatchedSuffix: []byte{0x48, 0x85, 0xc0, 0x90, 0x0f, 0x85},
		WildcardLen:   4,
		Fix:           []byte{0x48, 0x85, 0xc0, 0x90},
		Offset:        9,
		Desc:          "eligibility screen off",
	}

	Arm64CliGate = Gate{
		SigPrefix:     []byte{0x03, 0xd8, 0x40, 0xf9},
		SigSuffix:     []byte{0xb4, 0xe0, 0x03, 0x03, 0xaa, 0xe1, 0x03, 0x1f, 0xaa, 0xe2, 0x03, 0x1f, 0xaa},
		PatchedPrefix: []byte{0xe3, 0x03, 0x1f, 0xaa},
		PatchedSuffix: []byte{0xb4, 0xe0, 0x03, 0x03, 0xaa, 0xe1, 0x03, 0x1f, 0xaa, 0xe2, 0x03, 0x1f, 0xaa},
		WildcardLen:   3,
		Fix:           []byte{0xe3, 0x03, 0x1f, 0xaa},
		Offset:        0,
		Desc:          "eligibility screen off (arm64)",
	}
)

func findPattern(data []byte, prefix, suffix []byte, wildcardLen int) []int {
	var matches []int
	if len(data) < len(prefix)+wildcardLen+len(suffix) {
		return nil
	}

	limit := len(data) - (len(prefix) + wildcardLen + len(suffix))
	for i := 0; i <= limit; i++ {
		match := true
		for j := 0; j < len(prefix); j++ {
			if data[i+j] != prefix[j] {
				match = false
				break
			}
		}
		if !match {
			continue
		}

		suffixStart := i + len(prefix) + wildcardLen
		for j := 0; j < len(suffix); j++ {
			if data[suffixStart+j] != suffix[j] {
				match = false
				break
			}
		}

		if match {
			matches = append(matches, i)
		}
	}
	return matches
}

func detectArch(path string) string {
	f, err := os.Open(path)
	if err != nil {
		return "unknown"
	}
	defer f.Close()

	hdr := make([]byte, 8)
	n, err := f.Read(hdr)
	if err != nil || n < 8 {
		return "unknown"
	}

	if hdr[0] == 0xcf && hdr[1] == 0xfa && hdr[2] == 0xed && hdr[3] == 0xfe {
		cputype := binary.LittleEndian.Uint32(hdr[4:8])
		if cputype == 0x0100000C {
			return "arm64"
		}
		if cputype == 0x01000007 {
			return "x86_64"
		}
	} else if hdr[0] == 'M' && hdr[1] == 'Z' {
		return "x86_64"
	}
	return "unknown"
}

func gateFor(path string) Gate {
	if detectArch(path) == "arm64" {
		return Arm64CliGate
	}
	return CliGate
}

func findAgyBinary() string {
	var candidates []string

	w, err := exec.LookPath("agy")
	if err == nil {
		candidates = append(candidates, w)
	}

	if runtime.GOOS == "windows" {
		var winDirs []string
		for _, env := range []string{"LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)", "ProgramData", "APPDATA"} {
			val := os.Getenv(env)
			if val != "" {
				winDirs = append(winDirs, val)
				prog := filepath.Join(val, "Programs")
				if fi, err := os.Stat(prog); err == nil && fi.IsDir() {
					winDirs = append(winDirs, prog)
				}
			}
		}
		up := os.Getenv("USERPROFILE")
		if up != "" {
			winDirs = append(winDirs, filepath.Join(up, "scoop", "apps"))
		}
		scoop := os.Getenv("SCOOP")
		if scoop != "" {
			winDirs = append(winDirs, filepath.Join(scoop, "apps"))
		}

		for _, root := range winDirs {
			globFind(root, `agy\bin\agy.exe`, &candidates)
			globFind(root, `agy\*\bin\agy.exe`, &candidates)
			globFind(root, `agy*\agy.exe`, &candidates)
		}
	} else {
		cwd, err := os.Getwd()
		if err == nil {
			localAgy := filepath.Join(cwd, "agy")
			if fi, err := os.Stat(localAgy); err == nil && !fi.IsDir() {
				candidates = append(candidates, localAgy)
			}
		}

		userHome := getPosixInvokingUserHome()
		posixDirs := []string{"/usr/local/bin", "/usr/bin", "/opt/antigravity/bin", "/opt/antigravity"}
		if userHome != "" {
			posixDirs = append(posixDirs, filepath.Join(userHome, ".local/bin"), filepath.Join(userHome, "bin"))
		} else {
			posixDirs = append(posixDirs, os.ExpandEnv("$HOME/.local/bin"), os.ExpandEnv("$HOME/bin"))
		}

		for _, root := range posixDirs {
			globFind(root, "agy", &candidates)
		}
	}

	deduped := dedupNewest(candidates)
	if len(deduped) > 0 {
		return deduped[0]
	}
	return ""
}

func globFind(root, pattern string, candidates *[]string) {
	matches, err := filepath.Glob(filepath.Join(root, pattern))
	if err == nil {
		*candidates = append(*candidates, matches...)
	}
}

func dedupNewest(paths []string) []string {
	seen := make(map[string]bool)
	var existing []string
	for _, p := range paths {
		if p == "" {
			continue
		}
		if _, err := os.Stat(p); err == nil {
			existing = append(existing, p)
		}
	}

	sort.Slice(existing, func(i, j int) bool {
		fi1, _ := os.Stat(existing[i])
		fi2, _ := os.Stat(existing[j])
		return fi1.ModTime().After(fi2.ModTime())
	})

	var out []string
	for _, p := range existing {
		realP, err := filepath.EvalSymlinks(p)
		if err != nil {
			realP = p
		}
		key := strings.ToLower(realP)
		if !seen[key] {
			seen[key] = true
			out = append(out, p)
		}
	}
	return out
}

func resolveAgyPath(rawPath string) string {
	if rawPath == "" {
		return ""
	}
	cleaned := strings.Trim(rawPath, ` "'`)
	if cleaned == "" {
		return ""
	}

	expanded := os.ExpandEnv(cleaned)
	if strings.HasPrefix(expanded, "~") {
		home := os.Getenv("HOME")
		if home == "" {
			home = os.Getenv("USERPROFILE")
		}
		expanded = filepath.Join(home, expanded[1:])
	}
	resolved, err := filepath.Abs(expanded)
	if err != nil {
		return expanded
	}

	fi, err := os.Stat(resolved)
	if err == nil && !fi.IsDir() {
		return resolved
	}

	if err == nil && fi.IsDir() {
		var hits []string
		patterns := []string{"agy", "bin/agy"}
		if runtime.GOOS == "windows" {
			patterns = []string{"agy.exe", "bin/agy.exe"}
		}
		for _, pat := range patterns {
			globFind(resolved, pat, &hits)
			globFind(resolved, "*/"+pat, &hits)
		}
		deduped := dedupNewest(hits)
		if len(deduped) > 0 {
			return deduped[0]
		}
	}
	return ""
}

func isAgyLocked(path string) bool {
	f, err := os.OpenFile(path, os.O_RDWR, 0)
	if err != nil {
		return true
	}
	f.Close()
	return false
}

func getAgyStatus(path string) (string, error) {
	if path == "" {
		return "unknown", nil
	}

	gate := gateFor(path)
	patchedMatches, sigMatches, err := findPatternsInFile(path, gate)
	if err != nil {
		return "unknown", err
	}

	if len(patchedMatches) > 0 {
		return "patched", nil
	}

	if len(sigMatches) > 0 {
		return "unpatched", nil
	}

	return "unknown", nil
}

func isAgyPatched(path string) bool {
	status, _ := getAgyStatus(path)
	return status == "patched"
}

func makeAgyBackup(path string) {
	bak := path + BakExt
	if _, err := os.Stat(bak); err == nil {
		hash1 := fileHash(path)
		hash2 := fileHash(bak)
		if hash1 != "" && hash1 == hash2 {
			return
		}
		info("Backup is stale (app updated) — refreshing " + filepath.Base(path) + BakExt)
	} else {
		info("Creating backup -> " + filepath.Base(path) + BakExt)
	}

	if err := copyFile(path, bak); err == nil {
		fixPosixPermissions(bak)
		consoleOk(fmt.Sprintf("Backup: %s (%s)", filepath.Base(bak), formatBytes(fileSize(bak))))
	}
}

func copyToUserBin(path string) {
	if runtime.GOOS == "windows" {
		return
	}
	home := getPosixInvokingUserHome()
	destDir := filepath.Join(home, ".local", "bin")
	destPath := filepath.Join(destDir, "agy")

	absPath, _ := filepath.Abs(path)
	absDest, _ := filepath.Abs(destPath)
	if absPath == absDest {
		return
	}

	info("Storing file in user system folder -> " + destPath)
	os.MkdirAll(destDir, 0755)
	os.Remove(destPath)

	err := copyFile(path, destPath)
	if err == nil {
		os.Chmod(destPath, 0755)
		consoleOk("File successfully copied to: " + destPath)
	} else {
		warn("Could not copy file to " + destPath + ": " + err.Error())
	}
}

func doPatchAgy(path string) {
	if fi, err := os.Stat(path); err != nil || fi.IsDir() {
		errLine := "Target is not a file: " + path
		if err != nil {
			errLine = err.Error()
		}
		consoleErr(errLine)
		hint("Please select a valid agy/agy.exe binary.")
		return
	}

	hashBefore := fileHash(path)
	info("Target: " + color(path, ColorCyan))
	hint("Size: " + color(formatBytes(fileSize(path)), ColorCyan))
	fmt.Println()

	gate := gateFor(path)
	writeSuccess := false
	var offset int = 0

	for attempt := 0; attempt < 2; attempt++ {
		if isAgyLocked(path) {
			if attempt == 0 {
				warn("Binary is locked (Antigravity CLI is running).")
				if confirmed("Would you like to automatically close running agy processes and retry?") {
					terminateProcesses([]string{"agy"})
					time.Sleep(1500 * time.Millisecond)
					continue
				}
			}
			consoleErr("File is locked — close Antigravity CLI first.")
			return
		}

		patchedMatches, sigMatches, err := findPatternsInFile(path, gate)
		if err != nil {
			consoleErr("Read error: " + err.Error())
			return
		}

		if len(patchedMatches) > 0 {
			hint("agy already patched — nothing to do.")
			copyToUserBin(path)
			return
		}

		if len(sigMatches) == 0 {
			consoleErr("gate signature not found (unsupported version?)")
			return
		}

		if len(sigMatches) > 1 {
			consoleErr("gate signature is not unique — refusing to guess")
			return
		}

		offset = sigMatches[0] + gate.Offset

		makeAgyBackup(path)

		f, err := os.OpenFile(path, os.O_RDWR, 0)
		if err == nil {
			_, err = f.Seek(int64(offset), io.SeekStart)
			if err == nil {
				_, err = f.Write(gate.Fix)
				if err == nil {
					f.Sync()
					writeSuccess = true
				}
			}
			f.Close()
		}

		if err != nil {
			if os.IsPermission(err) || strings.Contains(err.Error(), "sharing violation") || strings.Contains(err.Error(), "locked") {
				if attempt == 0 {
					warn("Permission denied (file locked): " + err.Error())
					if confirmed("Would you like to automatically close running agy processes and retry?") {
						terminateProcesses([]string{"agy"})
						time.Sleep(1500 * time.Millisecond)
						continue
					}
				}
				consoleErr("Write error (Permission denied): " + err.Error())
				return
			}
			consoleErr("Write error: " + err.Error())
			return
		}

		if writeSuccess {
			break
		}
	}

	if !writeSuccess {
		return
	}

	hashAfter := fileHash(path)
	resignMacosBundle(path)
	resignMacosBinary(path)
	copyToUserBin(path)

	fmt.Println()
	step("Patch agy binary", true, gate.Desc)
	fmt.Println()

	var panelRows [][]string
	panelRows = append(panelRows, []string{"Target", filepath.Base(path)})
	panelRows = append(panelRows, []string{"Gate", fmt.Sprintf("%s @ 0x%x", gate.Desc, offset)})
	if hashBefore != "" && hashAfter != "" {
		panelRows = append(panelRows, []string{"Before", hashBefore[:8] + "..." + hashBefore[len(hashBefore)-8:]})
		panelRows = append(panelRows, []string{"After", hashAfter[:8] + "..." + hashAfter[len(hashAfter)-8:]})
	}
	printPanel("PATCH COMPLETE", panelRows, ColorGreen)
	hint("Restart Antigravity CLI for the change to take effect.")
}

func doRestoreAgy(path string) {
	if fi, err := os.Stat(path); err != nil || fi.IsDir() {
		consoleErr("Target is not a file: " + path)
		return
	}

	bak := path + BakExt
	if _, err := os.Stat(bak); os.IsNotExist(err) {
		warn("No backup for " + filepath.Base(path) + " (nothing to restore).")
		return
	}

	status, _ := getAgyStatus(path)
	if status != "patched" {
		warn("agy is not patched — skipping restore (backup may be a different build).")
		if !confirmed("Restore from backup anyway?") {
			hint("Restore cancelled.")
			return
		}
	}

	if isAgyLocked(path) {
		consoleErr("Binary is locked — close Antigravity CLI first.")
		return
	}

	if !confirmed("Restore agy from backup?") {
		hint("Restore cancelled.")
		return
	}

	hashBefore := fileHash(path)
	err := copyFile(bak, path)
	if err == nil {
		fixPosixPermissions(path)
		hashAfter := fileHash(path)
		resignMacosBundle(path)
		resignMacosBinary(path)
		copyToUserBin(path)

		fmt.Println()
		var panelRows [][]string
		panelRows = append(panelRows, []string{"Target", filepath.Base(path)})
		if hashBefore != "" && hashAfter != "" && hashBefore != hashAfter {
			panelRows = append(panelRows, []string{"Before", hashBefore[:8] + "..." + hashBefore[len(hashBefore)-8:]})
			panelRows = append(panelRows, []string{"After", hashAfter[:8] + "..." + hashAfter[len(hashAfter)-8:]})
		}
		printPanel("RESTORE COMPLETE", panelRows, ColorGreen)
	} else {
		consoleErr("Restore error: " + err.Error())
	}
}

func findPatternsInFile(path string, gate Gate) (patchedMatches []int, sigMatches []int, err error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, nil, err
	}
	defer f.Close()

	const chunkSize = 1024 * 1024 // 1 MB
	overlapSize := len(gate.SigPrefix) + gate.WildcardLen + len(gate.SigSuffix)
	if len(gate.PatchedPrefix) + gate.WildcardLen + len(gate.PatchedSuffix) > overlapSize {
		overlapSize = len(gate.PatchedPrefix) + gate.WildcardLen + len(gate.PatchedSuffix)
	}
	overlapSize += 32 // safety margin

	buf := make([]byte, chunkSize+overlapSize)
	var offset int64 = 0
	var bytesInBuf int = 0

	for {
		n, readErr := f.Read(buf[bytesInBuf:])
		if n > 0 {
			bytesInBuf += n
		}

		if bytesInBuf >= overlapSize {
			searchLimit := bytesInBuf - overlapSize + 1
			for i := 0; i < searchLimit; i++ {
				if matchPatternAt(buf[i:], gate.PatchedPrefix, gate.PatchedSuffix, gate.WildcardLen) {
					patchedMatches = append(patchedMatches, int(offset)+i)
				}
				if matchPatternAt(buf[i:], gate.SigPrefix, gate.SigSuffix, gate.WildcardLen) {
					sigMatches = append(sigMatches, int(offset)+i)
				}
			}

			keep := overlapSize
			copy(buf[0:keep], buf[bytesInBuf-keep:bytesInBuf])
			offset += int64(bytesInBuf - keep)
			bytesInBuf = keep
		}

		if readErr == io.EOF {
			pat1Len := len(gate.PatchedPrefix) + gate.WildcardLen + len(gate.PatchedSuffix)
			searchLimit1 := bytesInBuf - pat1Len
			for i := 0; i <= searchLimit1; i++ {
				if matchPatternAt(buf[i:], gate.PatchedPrefix, gate.PatchedSuffix, gate.WildcardLen) {
					patchedMatches = append(patchedMatches, int(offset)+i)
				}
			}

			pat2Len := len(gate.SigPrefix) + gate.WildcardLen + len(gate.SigSuffix)
			searchLimit2 := bytesInBuf - pat2Len
			for i := 0; i <= searchLimit2; i++ {
				if matchPatternAt(buf[i:], gate.SigPrefix, gate.SigSuffix, gate.WildcardLen) {
					sigMatches = append(sigMatches, int(offset)+i)
				}
			}
			break
		} else if readErr != nil {
			return nil, nil, readErr
		}
	}

	return patchedMatches, sigMatches, nil
}

func matchPatternAt(data []byte, prefix, suffix []byte, wildcardLen int) bool {
	patternLen := len(prefix) + wildcardLen + len(suffix)
	if len(data) < patternLen {
		return false
	}
	for j := 0; j < len(prefix); j++ {
		if data[j] != prefix[j] {
			return false
		}
	}
	suffixStart := len(prefix) + wildcardLen
	for j := 0; j < len(suffix); j++ {
		if data[suffixStart+j] != suffix[j] {
			return false
		}
	}
	return true
}
