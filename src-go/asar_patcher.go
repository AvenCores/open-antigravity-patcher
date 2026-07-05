package main

import (
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"io/fs"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"time"
)

// ASAR structures
type AsarIntegrity struct {
	Algorithm string   `json:"algorithm"`
	Hash      string   `json:"hash"`
	BlockSize int64    `json:"blockSize"`
	Blocks    []string `json:"blocks"`
}

type AsarEntry struct {
	Size      int64                  `json:"size,omitempty"`
	Offset    string                 `json:"offset,omitempty"`
	Unpacked  bool                   `json:"unpacked,omitempty"`
	Integrity *AsarIntegrity         `json:"integrity,omitempty"`
	Files     map[string]*AsarEntry  `json:"files,omitempty"`
}

func alignTo(value int64, alignment int64) int64 {
	remainder := value % alignment
	if remainder == 0 {
		return value
	}
	return value + (alignment - remainder)
}

func computeIntegrity(filePath string) (*AsarIntegrity, error) {
	f, err := os.Open(filePath)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	fullHash := sha256.New()
	var blockHashes []string
	buf := make([]byte, IntegrityBlockSize)

	for {
		n, err := f.Read(buf)
		if n > 0 {
			block := buf[:n]
			fullHash.Write(block)
			bh := sha256.Sum256(block)
			blockHashes = append(blockHashes, hex.EncodeToString(bh[:]))
		}
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, err
		}
	}

	return &AsarIntegrity{
		Algorithm: "SHA256",
		Hash:      hex.EncodeToString(fullHash.Sum(nil)),
		BlockSize: IntegrityBlockSize,
		Blocks:    blockHashes,
	}, nil
}

func findUnpackedFile(asarPath, currentPath string) string {
	resourceDir := filepath.Dir(asarPath)
	candidates := []string{
		asarPath + ".unpacked",
		filepath.Join(resourceDir, "app.asar.unpacked"),
		filepath.Join(resourceDir, "app1.asar.unpacked"),
	}

	for _, cand := range candidates {
		candFile := filepath.Join(cand, currentPath)
		if _, err := os.Stat(candFile); err == nil {
			return candFile
		}
	}
	return ""
}

func extractAsar(asarPath, destDir string) bool {
	asarPath, err := filepath.Abs(asarPath)
	if err != nil {
		consoleErr("ASAR path error: " + err.Error())
		return false
	}
	if _, err := os.Stat(asarPath); os.IsNotExist(err) {
		consoleErr("ASAR file not found at " + asarPath)
		return false
	}

	info("Extracting '" + filepath.Base(asarPath) + "' to temp directory...")

	f, err := os.Open(asarPath)
	if err != nil {
		consoleErr("Failed to open ASAR: " + err.Error())
		return false
	}
	defer f.Close()

	var pickleHeader, headerSize, jsonPayloadSize, jsonSize uint32
	if err := binary.Read(f, binary.LittleEndian, &pickleHeader); err != nil {
		consoleErr("Invalid ASAR format (read error 1)")
		return false
	}
	if err := binary.Read(f, binary.LittleEndian, &headerSize); err != nil {
		consoleErr("Invalid ASAR format (read error 2)")
		return false
	}
	if err := binary.Read(f, binary.LittleEndian, &jsonPayloadSize); err != nil {
		consoleErr("Invalid ASAR format (read error 3)")
		return false
	}
	if err := binary.Read(f, binary.LittleEndian, &jsonSize); err != nil {
		consoleErr("Invalid ASAR format (read error 4)")
		return false
	}

	jsonBytes := make([]byte, jsonSize)
	if _, err := io.ReadFull(f, jsonBytes); err != nil {
		consoleErr("Failed to read ASAR JSON header: " + err.Error())
		return false
	}

	var header AsarEntry
	if err := json.Unmarshal(jsonBytes, &header); err != nil {
		consoleErr("Failed to parse ASAR header JSON: " + err.Error())
		return false
	}

	payloadOffset := int64(8 + headerSize)

	var extractEntry func(entry *AsarEntry, currentPath string) error
	extractEntry = func(entry *AsarEntry, currentPath string) error {
		if entry.Files != nil {
			dirPath := filepath.Join(destDir, currentPath)
			if err := os.MkdirAll(dirPath, 0755); err != nil {
				return err
			}
			for name, child := range entry.Files {
				if err := extractEntry(child, filepath.Join(currentPath, name)); err != nil {
					return err
				}
			}
		} else {
			filePath := filepath.Join(destDir, currentPath)
			if err := os.MkdirAll(filepath.Dir(filePath), 0755); err != nil {
				return err
			}

			if entry.Unpacked {
				srcFile := findUnpackedFile(asarPath, currentPath)
				if srcFile != "" {
					if err := copyFile(srcFile, filePath); err != nil {
						return err
					}
				} else {
					warn("Unpacked file '" + currentPath + "' not found in external directory.")
				}
			} else {
				offsetVal, err := strconv.ParseInt(entry.Offset, 10, 64)
				if err != nil {
					return err
				}
				_, err = f.Seek(payloadOffset+offsetVal, io.SeekStart)
				if err != nil {
					return err
				}

				outF, err := os.Create(filePath)
				if err != nil {
					return err
				}
				defer outF.Close()

				_, err = io.CopyN(outF, f, entry.Size)
				if err != nil {
					return err
				}
			}
		}
		return nil
	}

	if err := extractEntry(&header, ""); err != nil {
		consoleErr("Extraction failed during entry processing: " + err.Error())
		return false
	}

	fixPosixPermissions(destDir)
	consoleOk("Extraction completed successfully.")
	return true
}

func getUnpackedPaths(asarPath string) map[string]bool {
	unpackedPaths := make(map[string]bool)
	if _, err := os.Stat(asarPath); os.IsNotExist(err) {
		return unpackedPaths
	}

	f, err := os.Open(asarPath)
	if err != nil {
		return unpackedPaths
	}
	defer f.Close()

	var pickleHeader, headerSize, jsonPayloadSize, jsonSize uint32
	// Read 16 bytes
	binary.Read(f, binary.LittleEndian, &pickleHeader)
	binary.Read(f, binary.LittleEndian, &headerSize)
	binary.Read(f, binary.LittleEndian, &jsonPayloadSize)
	if err := binary.Read(f, binary.LittleEndian, &jsonSize); err != nil {
		return unpackedPaths
	}

	jsonBytes := make([]byte, jsonSize)
	if _, err := io.ReadFull(f, jsonBytes); err != nil {
		return unpackedPaths
	}

	var header AsarEntry
	if err := json.Unmarshal(jsonBytes, &header); err != nil {
		return unpackedPaths
	}

	var collectUnpacked func(entry *AsarEntry, currentPath string)
	collectUnpacked = func(entry *AsarEntry, currentPath string) {
		if entry.Files != nil {
			for name, child := range entry.Files {
				nextPath := name
				if currentPath != "" {
					nextPath = currentPath + "/" + name
				}
				collectUnpacked(child, nextPath)
			}
		} else {
			if entry.Unpacked {
				unpackedPaths[strings.ReplaceAll(currentPath, "\\", "/")] = true
			}
		}
	}

	collectUnpacked(&header, "")
	return unpackedPaths
}

type filePair struct {
	RelPath  string
	FullPath string
}

func packAsar(sourceDir, asarPath, referenceAsarPath string) bool {
	info("Packing '" + sourceDir + "' to '" + filepath.Base(asarPath) + "'...")

	refPath := asarPath
	if referenceAsarPath != "" {
		refPath = referenceAsarPath
	}

	unpackedPaths := getUnpackedPaths(refPath)
	if len(unpackedPaths) > 0 {
		info(fmt.Sprintf("Found %d unpacked files to preserve.", len(unpackedPaths)))
	}

	unpackedDir := asarPath + ".unpacked"
	if _, err := os.Stat(unpackedDir); err == nil {
		os.RemoveAll(unpackedDir)
	}
	os.MkdirAll(unpackedDir, 0755)

	tempPayloadFile, err := os.CreateTemp("", "ag_payload_")
	if err != nil {
		consoleErr("Failed to create temp payload: " + err.Error())
		return false
	}
	defer func() {
		tempPayloadFile.Close()
		os.Remove(tempPayloadFile.Name())
	}()

	var allFiles []filePair
	filepath.WalkDir(sourceDir, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if !d.IsDir() {
			rel, err := filepath.Rel(sourceDir, path)
			if err == nil {
				relSlash := strings.ReplaceAll(rel, "\\", "/")
				if !PackExcludePaths[relSlash] {
					allFiles = append(allFiles, filePair{RelPath: relSlash, FullPath: path})
				}
			}
		}
		return nil
	})

	// Sort files for determinism
	sort.Slice(allFiles, func(i, j int) bool {
		return allFiles[i].RelPath < allFiles[j].RelPath
	})

	header := AsarEntry{Files: make(map[string]*AsarEntry)}
	var currentOffset int64 = 0

	for _, pair := range allFiles {
		fi, err := os.Stat(pair.FullPath)
		if err != nil {
			continue
		}
		size := fi.Size()
		isUnpacked := unpackedPaths[pair.RelPath]

		entry := &AsarEntry{
			Size: size,
		}

		integrity, err := computeIntegrity(pair.FullPath)
		if err == nil {
			entry.Integrity = integrity
		}

		if isUnpacked {
			entry.Unpacked = true
			destUnpacked := filepath.Join(unpackedDir, filepath.FromSlash(pair.RelPath))
			os.MkdirAll(filepath.Dir(destUnpacked), 0755)
			copyFile(pair.FullPath, destUnpacked)
		} else {
			data, err := os.ReadFile(pair.FullPath)
			if err != nil {
				continue
			}
			tempPayloadFile.Write(data)
			entry.Offset = strconv.FormatInt(currentOffset, 10)
			currentOffset += size
		}

		// Insert into tree
		parts := strings.Split(pair.RelPath, "/")
		currentNode := &header
		for _, part := range parts[:len(parts)-1] {
			if currentNode.Files == nil {
				currentNode.Files = make(map[string]*AsarEntry)
			}
			if _, exists := currentNode.Files[part]; !exists {
				currentNode.Files[part] = &AsarEntry{Files: make(map[string]*AsarEntry)}
			}
			currentNode = currentNode.Files[part]
		}
		if currentNode.Files == nil {
			currentNode.Files = make(map[string]*AsarEntry)
		}
		currentNode.Files[parts[len(parts)-1]] = entry
	}

	jsonBytes, err := json.Marshal(header)
	if err != nil {
		consoleErr("Failed to marshal ASAR header JSON: " + err.Error())
		return false
	}

	jsonSize := int64(len(jsonBytes))
	jsonPayloadSize := alignTo(jsonSize+4, 4)
	jsonPaddingSize := jsonPayloadSize - (jsonSize + 4)
	headerSize := jsonPayloadSize + 4
	var pickleHeader uint32 = 4

	tempAsar, err := os.CreateTemp(filepath.Dir(asarPath), "ag_asar_")
	if err != nil {
		consoleErr("Failed to create temp ASAR: " + err.Error())
		return false
	}
	defer func() {
		tempAsar.Close()
		os.Remove(tempAsar.Name())
	}()

	binary.Write(tempAsar, binary.LittleEndian, pickleHeader)
	binary.Write(tempAsar, binary.LittleEndian, uint32(headerSize))
	binary.Write(tempAsar, binary.LittleEndian, uint32(jsonPayloadSize))
	binary.Write(tempAsar, binary.LittleEndian, uint32(jsonSize))
	tempAsar.Write(jsonBytes)
	if jsonPaddingSize > 0 {
		tempAsar.Write(make([]byte, jsonPaddingSize))
	}

	tempPayloadFile.Seek(0, io.SeekStart)
	io.Copy(tempAsar, tempPayloadFile)
	tempAsar.Close()

	replaceSuccess := false
	for attempt := 0; attempt < 2; attempt++ {
		// handle locked files on Windows
		if _, err := os.Stat(asarPath); err == nil {
			errRemove := os.Remove(asarPath)
			if errRemove != nil {
				// Rename it out of the way if it is locked
				tempOldPath := asarPath + ".old"
				os.Remove(tempOldPath)
				errRename := os.Rename(asarPath, tempOldPath)
				if errRename == nil {
					info("Locked file renamed to " + filepath.Base(tempOldPath))
				} else {
					if attempt == 0 {
						warn("Permission denied (ASAR file locked): " + errRename.Error())
						if confirmed("Would you like to automatically close running Antigravity processes and retry?") {
							terminateProcesses([]string{"Antigravity", "Antigravity IDE", "antigravity", "antigravity-ide"})
							time.Sleep(1500 * time.Millisecond)
							continue
						}
					}
					consoleErr("Could not overwrite or rename '" + asarPath + "' (locked by another process). " + errRename.Error())
					return false
				}
			}
		}

		err = os.Rename(tempAsar.Name(), asarPath)
		if err != nil {
			err = copyFile(tempAsar.Name(), asarPath)
			if err != nil {
				consoleErr("Failed to write to target ASAR: " + err.Error())
				return false
			}
		}
		replaceSuccess = true
		break
	}

	if !replaceSuccess {
		return false
	}
	consoleOk("Packing completed successfully.")

	// Clean empty unpacked folder
	if fi, err := os.Stat(unpackedDir); err == nil && fi.IsDir() {
		files, _ := os.ReadDir(unpackedDir)
		if len(files) == 0 {
			os.Remove(unpackedDir)
		}
	}
	return true
}

func findAntigravityRoot() string {
	var candidates []string

	switch runtime.GOOS {
	case "darwin":
		macCandidates := []string{
			"/Applications/Antigravity.app",
			filepath.Join(getPosixInvokingUserHome(), "Applications/Antigravity.app"),
			"/Applications/antigravity.app",
			filepath.Join(getPosixInvokingUserHome(), "Applications/antigravity.app"),
		}
		for _, app := range macCandidates {
			if _, err := os.Stat(app); err == nil {
				candidates = append(candidates, app)
			}
		}
	case "linux":
		candidates = append(candidates,
			"/usr/share/antigravity",
			"/opt/Antigravity",
			"/opt/antigravity",
			"/usr/local/share/antigravity",
			"/usr/local/share/Antigravity",
		)
	case "windows":
		localAppData := os.Getenv("LOCALAPPDATA")
		if localAppData != "" {
			candidates = append(candidates, filepath.Join(localAppData, "Programs", "Antigravity"))
			candidates = append(candidates, filepath.Join(localAppData, "Programs", "antigravity"))
		}
		pf := os.Getenv("PROGRAMFILES")
		if pf != "" {
			candidates = append(candidates, filepath.Join(pf, "Antigravity"))
		}
		pfx86 := os.Getenv("PROGRAMFILES(X86)")
		if pfx86 != "" {
			candidates = append(candidates, filepath.Join(pfx86, "Antigravity"))
		}

		candidates = append(candidates, registryFindAntigravityRoots()...)
	}

	portable := findPortableCandidates("antigravity")

	for _, path := range candidates {
		path, _ = filepath.Abs(path)
		asar1 := filepath.Join(path, "resources", "app.asar")
		asar2 := filepath.Join(path, "resources", "app1.asar")
		_, err1 := os.Stat(asar1)
		_, err2 := os.Stat(asar2)
		if err1 == nil || err2 == nil {
			return path
		}

		if runtime.GOOS == "darwin" && strings.HasSuffix(path, ".app") {
			macAsar1 := filepath.Join(path, "Contents", "Resources", "app.asar")
			macAsar2 := filepath.Join(path, "Contents", "Resources", "app1.asar")
			_, errM1 := os.Stat(macAsar1)
			_, errM2 := os.Stat(macAsar2)
			if errM1 == nil || errM2 == nil {
				return path
			}
		}
	}

	if len(portable) > 0 {
		return portable[0]
	}

	for _, path := range candidates {
		if fi, err := os.Stat(path); err == nil && fi.IsDir() {
			return path
		}
	}

	return ""
}

func resolveAntigravityPaths(root string) (string, string) {
	if runtime.GOOS == "darwin" && strings.HasSuffix(root, ".app") {
		asar := filepath.Join(root, "Contents", "Resources", "app.asar")
		if _, err := os.Stat(asar); os.IsNotExist(err) {
			asar = filepath.Join(root, "Contents", "Resources", "app1.asar")
		}
		exe := filepath.Join(root, "Contents", "MacOS", "Antigravity")
		if _, err := os.Stat(exe); os.IsNotExist(err) {
			exe = filepath.Join(root, "Contents", "MacOS", "antigravity")
		}
		return asar, exe
	}

	asar := filepath.Join(root, "resources", "app.asar")
	if _, err := os.Stat(asar); os.IsNotExist(err) {
		asar = filepath.Join(root, "resources", "app1.asar")
	}

	exeName := "Antigravity"
	if runtime.GOOS == "windows" {
		exeName += ".exe"
	}

	exe := filepath.Join(root, exeName)
	if runtime.GOOS == "linux" {
		if _, err := os.Stat(exe); os.IsNotExist(err) {
			lowerExe := filepath.Join(root, "antigravity")
			if _, err := os.Stat(lowerExe); err == nil {
				exe = lowerExe
			}
		}
	}

	return asar, exe
}

func isAntigravityPatched(asarPath string) bool {
	if _, err := os.Stat(asarPath); os.IsNotExist(err) {
		return false
	}
	f, err := os.Open(asarPath)
	if err != nil {
		return false
	}
	defer f.Close()

	buf := make([]byte, 1024*1024)
	for {
		n, err := f.Read(buf)
		if n > 0 {
			if strings.Contains(string(buf[:n]), "patchFrontendMainJs") {
				return true
			}
		}
		if err == io.EOF {
			break
		}
		if err != nil {
			return false
		}
	}
	return false
}

func readPackageJsonFromAsar(asarPath string) string {
	if _, err := os.Stat(asarPath); os.IsNotExist(err) {
		return ""
	}

	f, err := os.Open(asarPath)
	if err != nil {
		return ""
	}
	defer f.Close()

	var pickleHeader, headerSize, jsonPayloadSize, jsonSize uint32
	binary.Read(f, binary.LittleEndian, &pickleHeader)
	binary.Read(f, binary.LittleEndian, &headerSize)
	binary.Read(f, binary.LittleEndian, &jsonPayloadSize)
	if err := binary.Read(f, binary.LittleEndian, &jsonSize); err != nil {
		return ""
	}

	jsonBytes := make([]byte, jsonSize)
	if _, err := io.ReadFull(f, jsonBytes); err != nil {
		return ""
	}

	var header AsarEntry
	if err := json.Unmarshal(jsonBytes, &header); err != nil {
		return ""
	}

	if header.Files != nil {
		pkgEntry := header.Files["package.json"]
		if pkgEntry != nil && pkgEntry.Offset != "" {
			offsetVal, _ := strconv.ParseInt(pkgEntry.Offset, 10, 64)
			payloadOffset := int64(8 + headerSize)
			_, err = f.Seek(payloadOffset+offsetVal, io.SeekStart)
			if err == nil {
				data := make([]byte, pkgEntry.Size)
				if _, err = io.ReadFull(f, data); err == nil {
					var pkgData map[string]interface{}
					if err = json.Unmarshal(data, &pkgData); err == nil {
						if ver, ok := pkgData["version"].(string); ok {
							return ver
						}
					}
				}
			}
		}
	}

	return ""
}

func patchAntigravityMainJs(destFolder string, rollback bool) bool {
	mainJsPath := filepath.Join(destFolder, "dist", "main.js")
	backupPath := mainJsPath + ".bak"

	if _, err := os.Stat(mainJsPath); os.IsNotExist(err) {
		consoleErr("main.js not found at " + mainJsPath)
		return false
	}

	data, err := os.ReadFile(mainJsPath)
	if err != nil {
		consoleErr("Failed to read main.js: " + err.Error())
		return false
	}
	content := string(data)

	escapedDestFolder := strings.ReplaceAll(destFolder, "\\", "/")
	injectionCode := strings.ReplaceAll(AntigravityInjectionCodeTemplate, "{dest_folder}", escapedDestFolder)
	injectionCode = strings.ReplaceAll(injectionCode, "{key_pem}", strings.ReplaceAll(LocalPatchServerKey, "\n", "\\n"))
	injectionCode = strings.ReplaceAll(injectionCode, "{cert_pem}", strings.ReplaceAll(LocalPatchServerCert, "\n", "\\n"))

	if rollback {
		if strings.Contains(content, injectionCode) {
			patchedContent := strings.ReplaceAll(content, injectionCode, "")
			err := os.WriteFile(mainJsPath, []byte(patchedContent), 0644)
			if err == nil {
				consoleOk("Rolled back patch by removing the injected lines directly.")
				return true
			}
		} else if _, err := os.Stat(backupPath); err == nil {
			err := copyFile(backupPath, mainJsPath)
			if err == nil {
				consoleOk("Rolled back patch using the backup file (main.js.bak).")
				return true
			}
		}
		consoleErr("Patch not found in main.js and backup file does not exist.")
		return false
	}

	if _, err := os.Stat(backupPath); os.IsNotExist(err) {
		copyFile(mainJsPath, backupPath)
		info("Created backup of original main.js inside temp folder.")
	}

	targetStr := "(0, ipcHandlers_1.registerIpcHandlers)(storageManager);"
	if strings.Contains(content, "patchFrontendMainJs") {
		hint("Patch already applied to main.js.")
		return true
	}
	if strings.Contains(content, "downloaded_frontend_main.js") {
		if _, err := os.Stat(backupPath); err == nil {
			backupData, err := os.ReadFile(backupPath)
			if err == nil {
				content = string(backupData)
				hint("Found old download-only patch; restored backup content before applying frontend patch proxy.")
			}
		}
	}

	if !strings.Contains(content, targetStr) {
		consoleErr("Target line '" + targetStr + "' not found in main.js")
		return false
	}

	patchedContent := strings.ReplaceAll(content, targetStr, targetStr+injectionCode)
	err = os.WriteFile(mainJsPath, []byte(patchedContent), 0644)
	if err != nil {
		consoleErr("Failed to write patched main.js: " + err.Error())
		return false
	}

	consoleOk("Patched main.js inside extracted ASAR.")
	return true
}

func doPatchAntigravity(antigravityRoot string) {
	if antigravityRoot == "" {
		consoleErr("Antigravity root path not found.")
		return
	}
	if fi, err := os.Stat(antigravityRoot); err != nil || !fi.IsDir() {
		consoleErr("Antigravity root is not a valid directory: " + antigravityRoot)
		return
	}

	asarPath, exePath := resolveAntigravityPaths(antigravityRoot)
	if _, err := os.Stat(asarPath); os.IsNotExist(err) {
		consoleErr("ASAR file not found: " + asarPath)
		return
	}

	if isAntigravityPatched(asarPath) {
		hint("Antigravity appears already patched.")
		if !confirmed("Apply patch anyway?") {
			return
		}
	}

	sourceAsarPath := asarPath + ".bak"
	legacyBackup := filepath.Join(filepath.Dir(asarPath), "app_original.asar")
	if _, err := os.Stat(legacyBackup); err == nil {
		if _, err := os.Stat(sourceAsarPath); os.IsNotExist(err) {
			sourceAsarPath = legacyBackup
		}
	}

	if _, err := os.Stat(sourceAsarPath); os.IsNotExist(err) {
		info("Creating backup of original ASAR...")
		if err := copyFile(asarPath, sourceAsarPath); err == nil {
			fixPosixPermissions(sourceAsarPath)
			consoleOk(fmt.Sprintf("Backup: %s (%s)", filepath.Base(sourceAsarPath), formatBytes(fileSize(sourceAsarPath))))
		} else {
			consoleErr("Backup error: " + err.Error())
			return
		}
	} else {
		hint("Backup of original ASAR already exists: " + filepath.Base(sourceAsarPath))
	}

	tempDir := os.TempDir()
	if resolved, err := filepath.EvalSymlinks(tempDir); err == nil {
		tempDir = resolved
	}
	destFolder := filepath.Join(tempDir, "ag_patcher_temp")

	if _, err := os.Stat(destFolder); err == nil {
		os.RemoveAll(destFolder)
	}
	os.MkdirAll(destFolder, 0755)
	fixPosixPermissions(destFolder)

	fmt.Println()
	info("Extracting ASAR archive...")
	success := extractAsar(sourceAsarPath, destFolder)
	step("Extract ASAR", success, filepath.Base(sourceAsarPath))
	if !success {
		consoleErr("Extraction failed.")
		return
	}

	info("Modifying files...")
	patchOk := patchAntigravityMainJs(destFolder, false)
	step("Patch main.js", patchOk, "")
	if !patchOk {
		consoleErr("Patching main.js failed.")
		return
	}

	info("Packing ASAR archive...")
	packOk := packAsar(destFolder, asarPath, sourceAsarPath)
	step("Pack ASAR", packOk, "")
	if !packOk {
		consoleErr("Packing failed.")
		return
	}

	fixPosixPermissions(asarPath)
	unpackedFolder := asarPath + ".unpacked"
	if _, err := os.Stat(unpackedFolder); err == nil {
		fixPosixPermissions(unpackedFolder)
	}
	resignMacosBundle(asarPath)

	verifyDetail := "skipped (no executable)"
	var verifiedOk interface{} = nil

	if _, err := os.Stat(exePath); err == nil {
		info("Launching application to verify: " + exePath)
		targetFile := filepath.Join(destFolder, "frontend_patch_result.json")
		os.Remove(targetFile)

		cmd := exec.Command(exePath)
		cmd.Dir = antigravityRoot

		// On POSIX, drop root privileges if we ran with sudo
		if runtime.GOOS != "windows" {
			cmd.Env = os.Environ()
			if getuid() == 0 {
				sudoUID := os.Getenv("SUDO_UID")
				sudoGID := os.Getenv("SUDO_GID")
				if sudoUID != "" && sudoGID != "" {
					// In Go, dropping privileges on cmd can be done using SysProcAttr on Linux
					setCmdUser(cmd, sudoUID, sudoGID)
				}
			}
		}

		errStart := cmd.Start()
		if errStart == nil {
			info("Waiting for frontend_patch_result.json to be written...")
			startTime := time.Now()
			timeout := 120 * time.Second
			patched := false
			var verification map[string]interface{}

			for time.Since(startTime) < timeout {
				if fi, err := os.Stat(targetFile); err == nil && fi.Size() > 0 {
					patched = true
					data, err := os.ReadFile(targetFile)
					if err == nil {
						json.Unmarshal(data, &verification)
					}
					break
				}
				time.Sleep(500 * time.Millisecond)
			}

			if patched && verification != nil {
				if verified, ok := verification["verified"].(bool); ok && verified {
					verifiedOk = true
					verifyDetail = filepath.Base(targetFile)
					consoleOk("Frontend patch result verified: " + targetFile)
				} else {
					verifiedOk = false
					verifyDetail = "verification failed"
					warn("Frontend patch result was written but verification failed: " + targetFile)
					if results, exists := verification["results"].([]interface{}); exists {
						for _, r := range results {
							if rm, ok := r.(map[string]interface{}); ok {
								status := "not applied"
								if app, ok := rm["applied"].(bool); ok && app {
									status = "applied"
								}
								name := rm["name"]
								detail := rm["detail"]
								fmt.Printf("      - %v: %s; %v\n", name, status, detail)
							}
						}
					}
				}
			} else {
				verifiedOk = false
				verifyDetail = "verification timed out"
				warn("Timeout: frontend_patch_result.json was not written.")
				hint("The patch was applied, but verification timed out. You may need to sign in manually.")
			}

			info("Stopping the application...")
			if runtime.GOOS == "windows" {
				cmd.Process.Kill()
			} else {
				cmd.Process.Signal(os.Interrupt)
			}
			// Wait with timeout
			done := make(chan error, 1)
			go func() {
				done <- cmd.Wait()
			}()
			select {
			case <-done:
				// finished
			case <-time.After(5 * time.Second):
				if runtime.GOOS != "windows" {
					warn("Forcing application to stop...")
					cmd.Process.Kill()
				}
			}
		} else {
			verifiedOk = false
			verifyDetail = "launch error: " + errStart.Error()
			warn("Error launching application: " + errStart.Error())
		}
	} else {
		warn("Executable not found at " + exePath + ". Cannot auto-verify.")
	}

	step("Verify frontend", verifiedOk, verifyDetail)
	fmt.Println()

	var panelRows [][]string
	panelRows = append(panelRows, []string{"Target", filepath.Base(asarPath)})
	panelRows = append(panelRows, []string{"Backup", fmt.Sprintf("%s (%s)", filepath.Base(sourceAsarPath), formatBytes(fileSize(sourceAsarPath)))})

	printPanel("PATCH COMPLETE", panelRows, ColorGreen)
}

func doRestoreAntigravity(antigravityRoot string) {
	if antigravityRoot == "" {
		consoleErr("Antigravity root path not found.")
		return
	}
	if fi, err := os.Stat(antigravityRoot); err != nil || !fi.IsDir() {
		consoleErr("Antigravity root is not a valid directory: " + antigravityRoot)
		return
	}

	asarPath, _ := resolveAntigravityPaths(antigravityRoot)
	sourceAsarPath := asarPath + ".bak"
	legacyBackup := filepath.Join(filepath.Dir(asarPath), "app_original.asar")
	if _, err := os.Stat(legacyBackup); err == nil {
		if _, err := os.Stat(sourceAsarPath); os.IsNotExist(err) {
			sourceAsarPath = legacyBackup
		}
	}

	if _, err := os.Stat(sourceAsarPath); os.IsNotExist(err) {
		consoleErr("Original ASAR backup not found: " + sourceAsarPath)
		info("Attempting in-place rollback by extracting and patching...")
		if _, err := os.Stat(asarPath); os.IsNotExist(err) {
			consoleErr("Target ASAR file not found: " + asarPath)
			return
		}

		tempDir := os.TempDir()
		if resolved, err := filepath.EvalSymlinks(tempDir); err == nil {
			tempDir = resolved
		}
		destFolder := filepath.Join(tempDir, "ag_patcher_temp")
		if _, err := os.Stat(destFolder); err == nil {
			os.RemoveAll(destFolder)
		}
		os.MkdirAll(destFolder, 0755)

		fmt.Println()
		info("Extracting ASAR...")
		extractOk := extractAsar(asarPath, destFolder)
		step("Extract ASAR", extractOk, filepath.Base(asarPath))
		if !extractOk {
			consoleErr("Extraction failed.")
			return
		}

		info("Performing rollback in main.js...")
		rollbackOk := patchAntigravityMainJs(destFolder, true)
		step("Rollback main.js", rollbackOk, "")
		if !rollbackOk {
			consoleErr("Rollback failed (patch not found or backup missing).")
			return
		}

		info("Packing ASAR...")
		packOk := packAsar(destFolder, asarPath, "")
		step("Pack ASAR", packOk, "")
		if !packOk {
			consoleErr("Packing failed.")
			return
		}

		fixPosixPermissions(asarPath)
		unpackedFolder := asarPath + ".unpacked"
		if _, err := os.Stat(unpackedFolder); err == nil {
			fixPosixPermissions(unpackedFolder)
		}
		resignMacosBundle(asarPath)

		fmt.Println()
		var panelRows [][]string
		panelRows = append(panelRows, []string{"Target", filepath.Base(asarPath)})
		panelRows = append(panelRows, []string{"Mode", "in-place rollback"})
		printPanel("RESTORE COMPLETE", panelRows, ColorGreen)
		return
	}

	info("Found original ASAR backup: " + filepath.Base(sourceAsarPath))
	if !confirmed("Restore original ASAR from backup?") {
		return
	}

	// Rename it first if locked
	if _, err := os.Stat(asarPath); err == nil {
		errRemove := os.Remove(asarPath)
		if errRemove != nil {
			tempOldPath := asarPath + ".old"
			os.Remove(tempOldPath)
			os.Rename(asarPath, tempOldPath)
		}
	}

	err := copyFile(sourceAsarPath, asarPath)
	if err == nil {
		fixPosixPermissions(asarPath)
		resignMacosBundle(asarPath)
		fmt.Println()

		var panelRows [][]string
		panelRows = append(panelRows, []string{"Target", filepath.Base(asarPath)})
		panelRows = append(panelRows, []string{"Backup", filepath.Base(sourceAsarPath) + " (kept)"})
		printPanel("RESTORE COMPLETE", panelRows, ColorGreen)
	} else {
		consoleErr("Failed to restore backup: " + err.Error())
	}
}
