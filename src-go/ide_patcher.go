package main

import (
	"encoding/json"
	"fmt"
	"io/fs"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"runtime"
	"strings"
	"time"
)

type VersionStatus string

const (
	VersionStatusOk         VersionStatus = "ok"
	VersionStatusTooOld     VersionStatus = "too_old"
	VersionStatusNotFound   VersionStatus = "not_found"
	VersionStatusParseError VersionStatus = "parse_error"
)

func parseVersion(v string) []int {
	var parts []int
	rawSegments := strings.Split(v, ".")
	for _, s := range rawSegments {
		var digits string
		for _, char := range s {
			if char >= '0' && char <= '9' {
				digits += string(char)
			} else {
				break
			}
		}
		if digits != "" {
			var val int
			fmt.Sscanf(digits, "%d", &val)
			parts = append(parts, val)
		}
	}
	return parts
}

func compareVersions(v1, v2 string) int {
	p1 := parseVersion(v1)
	p2 := parseVersion(v2)
	maxLen := len(p1)
	if len(p2) > maxLen {
		maxLen = len(p2)
	}
	for i := 0; i < maxLen; i++ {
		val1 := 0
		if i < len(p1) {
			val1 = p1[i]
		}
		val2 := 0
		if i < len(p2) {
			val2 = p2[i]
		}
		if val1 < val2 {
			return -1
		} else if val1 > val2 {
			return 1
		}
	}
	return 0
}

func findPortableCandidates(searchType string) []string {
	var roots []string
	home := getPosixInvokingUserHome()
	if home == "" {
		home = os.Getenv("USERPROFILE")
		if home == "" {
			home = os.Getenv("HOME")
		}
	}

	if home != "" {
		standardSubs := []string{
			"Downloads", "Загрузки", "downloads", "загрузки",
			"Desktop", "Рабочий стол", "desktop", "рабочий стол",
			"Documents", "Документы", "documents", "документы",
		}
		for _, sub := range standardSubs {
			p := filepath.Join(home, sub)
			if fi, err := os.Stat(p); err == nil && fi.IsDir() {
				roots = append(roots, p)
			}
		}
	}

	if runtime.GOOS != "windows" {
		sudoUser := os.Getenv("SUDO_USER")
		for _, folderType := range []string{"DOWNLOAD", "DESKTOP", "DOCUMENTS"} {
			cmd := exec.Command("xdg-user-dir", folderType)
			if sudoUser != "" {
				cmd = exec.Command("sudo", "-u", sudoUser, "xdg-user-dir", folderType)
			}
			res, err := cmd.Output()
			if err == nil {
				path := strings.TrimSpace(string(res))
				if path != "" {
					if fi, err := os.Stat(path); err == nil && fi.IsDir() {
						roots = append(roots, path)
					}
				}
			}
		}
	}

	cwd, err := os.Getwd()
	if err == nil {
		roots = append(roots, cwd)
	}

	if runtime.GOOS == "windows" {
		for _, letter := range "DEFGHIJKLMNOPQRSTUVWXYZ" {
			drive := string(letter) + ":\\"
			if _, err := os.Stat(drive); err == nil {
				roots = append(roots, drive)
			}
		}
	}

	if home != "" {
		roots = append(roots, home)
	}

	// Dedup roots
	seen := make(map[string]bool)
	var uniqueRoots []string
	for _, r := range roots {
		abs, err := filepath.Abs(r)
		if err == nil && !seen[abs] {
			seen[abs] = true
			uniqueRoots = append(uniqueRoots, abs)
		}
	}

	var candidates []string
	visitedDirs := 0
	maxDirs := 1500
	pruneDirs := map[string]bool{
		".git": true, "node_modules": true, "appdata": true, "application data": true, "library": true,
		"system volume information": true, "$recycle.bin": true, "windows": true, "program files": true,
		"program files (x86)": true, "usr": true, "var": true, "sys": true, "proc": true, "dev": true,
		"dist": true, "build": true, "__pycache__": true, ".idea": true, ".vscode": true,
	}

	for _, root := range uniqueRoots {
		if visitedDirs > maxDirs {
			break
		}
		filepath.WalkDir(root, func(path string, d fs.DirEntry, err error) error {
			if err != nil {
				return filepath.SkipDir
			}
			if visitedDirs > maxDirs {
				return filepath.SkipAll
			}
			if d.IsDir() {
				visitedDirs++
				dirName := strings.ToLower(d.Name())
				if pruneDirs[dirName] || strings.HasPrefix(dirName, ".") {
					return filepath.SkipDir
				}

				// Compute depth
				rel, err := filepath.Rel(root, path)
				if err == nil {
					depth := len(strings.Split(filepath.ToSlash(rel), "/"))
					if depth >= 3 {
						return filepath.SkipDir
					}
				}

				pathLower := strings.ToLower(path)
				isMatch := strings.Contains(pathLower, "antigravity") || path == root || root == cwd

				if isMatch {
					if searchType == "ide" {
						subs := []string{
							filepath.Join("resources", "app", "out", "main.js"),
							filepath.Join("resources", "app", "main.js"),
							filepath.Join("out", "main.js"),
							"main.js",
						}
						for _, sub := range subs {
							p := filepath.Join(path, sub)
							if _, err := os.Stat(p); err == nil {
								if !containsString(candidates, path) {
									candidates = append(candidates, path)
									consoleOk("Found portable Antigravity IDE at: " + path)
									break
								}
							}
						}
					} else if searchType == "antigravity" {
						p1 := filepath.Join(path, "resources", "app.asar")
						p2 := filepath.Join(path, "resources", "app1.asar")
						_, err1 := os.Stat(p1)
						_, err2 := os.Stat(p2)
						if err1 == nil || err2 == nil {
							if !containsString(candidates, path) {
								candidates = append(candidates, path)
								consoleOk("Found portable Antigravity at: " + path)
							}
						}
					}
				}
			}
			return nil
		})
	}
	return candidates
}

func containsString(arr []string, s string) bool {
	for _, v := range arr {
		if v == s {
			return true
		}
	}
	return false
}

func findInstallRoot() string {
	var candidates []string

	if runtime.GOOS == "darwin" {
		macCandidates := []string{
			"/Applications/Antigravity IDE.app",
			filepath.Join(getPosixInvokingUserHome(), "Applications/Antigravity IDE.app"),
			"/Applications/antigravity ide.app",
			filepath.Join(getPosixInvokingUserHome(), "Applications/antigravity ide.app"),
		}
		for _, app := range macCandidates {
			candidates = append(candidates, filepath.Join(app, "Contents", "Resources", "app"))
		}
	} else if runtime.GOOS == "linux" {
		candidates = append(candidates,
			"/usr/share/antigravity-ide",
			"/opt/Antigravity IDE",
			"/opt/antigravity-ide",
			"/opt/antigravity ide",
			"/opt/Antigravity IDE/resources/app/out",
		)
	} else if runtime.GOOS == "windows" {
		localAppData := os.Getenv("LOCALAPPDATA")
		if localAppData != "" {
			candidates = append(candidates, filepath.Join(localAppData, "Programs", "Antigravity IDE"))
		}
		pf := os.Getenv("PROGRAMFILES")
		if pf != "" {
			candidates = append(candidates, filepath.Join(pf, "Antigravity IDE"))
		}
		pfx86 := os.Getenv("PROGRAMFILES(X86)")
		if pfx86 != "" {
			candidates = append(candidates, filepath.Join(pfx86, "Antigravity IDE"))
		}

		loc := registryGetInstallLocation()
		if loc != "" {
			candidates = append(candidates, loc)
		}
	}

	foundStandard := ""
	for _, path := range candidates {
		subs := []string{
			filepath.Join("resources", "app", "out", "main.js"),
			filepath.Join("resources", "app", "main.js"),
			filepath.Join("out", "main.js"),
			"main.js",
		}
		for _, sub := range subs {
			p := filepath.Join(path, sub)
			if _, err := os.Stat(p); err == nil {
				foundStandard = path
				break
			}
		}
		if foundStandard != "" {
			break
		}
	}

	portable := findPortableCandidates("ide")
	if foundStandard != "" {
		return foundStandard
	}
	if len(portable) > 0 {
		return portable[0]
	}
	return ""
}

func findMainJs(root string) string {
	if runtime.GOOS == "darwin" && strings.HasSuffix(strings.ToLower(root), ".app") {
		root = filepath.Join(root, "Contents", "Resources", "app")
	}

	subs := []string{
		filepath.Join("resources", "app", "out", "main.js"),
		filepath.Join("resources", "app", "main.js"),
		filepath.Join("out", "main.js"),
		"main.js",
	}
	for _, sub := range subs {
		p := filepath.Join(root, sub)
		if _, err := os.Stat(p); err == nil {
			return p
		}
	}
	return ""
}

func getAgVersion(mainJsPath string) (string, bool) {
	if runtime.GOOS == "linux" {
		pkgNames := []string{"antigravity-ide", "antigravity-ide-bin", "antigravity-ide-custom"}
		// dpkg-query
		for _, pkg := range pkgNames {
			res, err := exec.Command("dpkg-query", "-W", "-f=${Version}", pkg).Output()
			if err == nil {
				ver := strings.TrimSpace(string(res))
				if ver != "" {
					return ver, true
				}
			}
		}
		// rpm
		for _, pkg := range pkgNames {
			res, err := exec.Command("rpm", "-q", "--queryformat", "%{VERSION}", pkg).Output()
			if err == nil {
				ver := strings.TrimSpace(string(res))
				if ver != "" {
					return ver, true
				}
			}
		}

		// Fallback package.json
		dirs := []string{
			filepath.Join(filepath.Dir(mainJsPath), "..", "package.json"),
			filepath.Join(filepath.Dir(mainJsPath), "package.json"),
		}
		for _, rel := range dirs {
			pkg := filepath.Clean(rel)
			if _, err := os.Stat(pkg); err == nil {
				data, err := os.ReadFile(pkg)
				if err == nil {
					var result map[string]interface{}
					if err := json.Unmarshal(data, &result); err == nil {
						if ver, exists := result["version"].(string); exists {
							return strings.TrimSpace(ver), false
						}
					}
				}
			}
		}
		return "", false
	}

	if runtime.GOOS == "windows" {
		ver := registryGetDisplayVersion()
		if ver != "" {
			return ver, true
		}
	}

	return "", false
}

func checkAgVersion(mainJsPath string) (VersionStatus, string) {
	verStr, isPkgMgr := getAgVersion(mainJsPath)
	if verStr == "" {
		return VersionStatusNotFound, ""
	}

	minVerStr := MinAgVersion
	if runtime.GOOS == "linux" && !isPkgMgr {
		minVerStr = "1.107.0"
	}

	cmp := compareVersions(verStr, minVerStr)
	if cmp < 0 {
		return VersionStatusTooOld, verStr
	}
	return VersionStatusOk, verStr
}

func resolveTargetPath(rawPath string) string {
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
	if fi, err := os.Stat(resolved); err == nil && fi.IsDir() {
		found := findMainJs(resolved)
		if found != "" {
			return found
		}
		return resolved
	}
	return resolved
}

func assignCustomPath(rawPath string) (string, string) {
	resolved := resolveTargetPath(rawPath)
	if _, err := os.Stat(resolved); os.IsNotExist(err) {
		return "", ""
	}

	fi, _ := os.Stat(resolved)
	if !fi.IsDir() && strings.HasSuffix(resolved, "main.js") {
		return resolved, ""
	}

	asarPath, _ := resolveAntigravityPaths(resolved)
	if _, err := os.Stat(asarPath); err == nil {
		return "", resolved
	}

	mainJs := findMainJs(resolved)
	if mainJs != "" {
		return mainJs, ""
	}

	if !fi.IsDir() {
		return resolved, ""
	}
	return "", resolved
}

type patchResult struct {
	Name    string
	Applied bool
	Detail  string
}

func patchIsGoogleInternal(content string) (string, patchResult) {
	reIfInternal := regexp.MustCompile(`if\(this\.([a-zA-Z_$]+)\.isGoogleInternal\)`)
	matches := reIfInternal.FindAllString(content, -1)
	newContent := reIfInternal.ReplaceAllString(content, "if(true)")
	applied := newContent != content
	detail := ""
	if applied {
		detail = fmt.Sprintf("replaced %d occurrences: %v", len(matches), matches)
	}
	return newContent, patchResult{
		Name:    "if(isGoogleInternal) → if(true)",
		Applied: applied,
		Detail:  detail,
	}
}

func patchIsGoogleInternalComma(content string, agVersion string) (string, patchResult) {
	var authRegex *regexp.Regexp
	patternLabel := "auto"

	if agVersion != "" {
		if compareVersions(agVersion, AuthPatchSwitchVersion) < 0 {
			authRegex = ReAuthIsGoogleInternalOld
			patternLabel = "< " + AuthPatchSwitchVersion
		} else {
			authRegex = ReAuthIsGoogleInternalNew
			patternLabel = ">= " + AuthPatchSwitchVersion
		}
	} else {
		authRegex = ReAuthIsGoogleInternal
	}

	matches := authRegex.FindAllString(content, -1)
	newContent := authRegex.ReplaceAllString(content, "if(${1}true)")
	applied := newContent != content

	detail := fmt.Sprintf("%s pattern not found", patternLabel)
	if applied {
		detail = fmt.Sprintf("replaced %d auth occurrence(s) using %s pattern", len(matches), patternLabel)
	}
	return newContent, patchResult{
		Name:    "comma isGoogleInternal → true (auth)",
		Applied: applied,
		Detail:  detail,
	}
}

func patchIdeName(content string) (string, patchResult) {
	newContent := strings.ReplaceAll(content, `ideName:"antigravity"`, `ideName:"antigravity-insiders"`)
	return newContent, patchResult{
		Name:    `ideName → antigravity-insiders`,
		Applied: newContent != content,
		Detail:  "",
	}
}

func patchIneligibleScreen(content string) (string, patchResult) {
	oldStr := `...s?{}:{errorType:"ineligible",reason:a,verificationUrl:i}`
	newStr := `...s?{}:{}`
	applied := strings.Contains(content, oldStr)
	newContent := strings.ReplaceAll(content, oldStr, newStr)
	detail := "pattern not found"
	if applied {
		detail = "Replaced ineligible spread with empty object"
	}
	return newContent, patchResult{
		Name:    "ineligible screen bypass (v1.22+)",
		Applied: applied,
		Detail:  detail,
	}
}

func applyPatchesMinimal(content string, agVersion string) (string, []patchResult) {
	var results []patchResult
	var r patchResult

	content, r = patchIsGoogleInternal(content)
	results = append(results, r)

	content, r = patchIsGoogleInternalComma(content, agVersion)
	results = append(results, r)

	content, r = patchIdeName(content)
	results = append(results, r)

	content, r = patchIneligibleScreen(content)
	results = append(results, r)

	return content, results
}

func isAlreadyPatched(content string) bool {
	reSimple := regexp.MustCompile(`if\(this\.[a-zA-Z_$]+\.isGoogleInternal\)`)
	hasUnpatchedSimple := reSimple.MatchString(content)
	hasUnpatchedAuth := ReAuthIsGoogleInternal.MatchString(content)
	hasIde := strings.Contains(content, `ideName:"antigravity-insiders"`)
	return !hasUnpatchedSimple && !hasUnpatchedAuth && hasIde
}

func getUserSettingsPath() string {
	if runtime.GOOS == "windows" {
		appData := os.Getenv("APPDATA")
		if appData != "" {
			return filepath.Join(appData, "Antigravity IDE", "User", "settings.json")
		}
		return ""
	}
	if runtime.GOOS == "darwin" {
		return filepath.Join(
			getPosixInvokingUserHome(),
			"Library",
			"Application Support",
			"Antigravity IDE",
			"User",
			"settings.json",
		)
	}

	// POSIX Linux
	configHome := os.Getenv("XDG_CONFIG_HOME")
	if configHome == "" {
		configHome = filepath.Join(getPosixInvokingUserHome(), ".config")
	}
	return filepath.Join(configHome, "Antigravity IDE", "User", "settings.json")
}

func getUserDataDir() string {
	p := getUserSettingsPath()
	if p == "" {
		return ""
	}
	return filepath.Dir(filepath.Dir(p))
}

func patchRuntimeSettings(agVersion string) patchResult {
	if agVersion != "" && compareVersions(agVersion, RuntimeSettingsSwitchVersion) < 0 {
		return patchResult{
			Name:    "temporary runtime settings workaround",
			Applied: false,
			Detail:  "skipped for Antigravity IDE < " + RuntimeSettingsSwitchVersion,
		}
	}

	settingsPath := getUserSettingsPath()
	if settingsPath == "" {
		return patchResult{
			Name:    "temporary runtime settings workaround",
			Applied: false,
			Detail:  "settings path not detected",
		}
	}

	settingsDir := filepath.Dir(settingsPath)
	dataDir := filepath.Dir(settingsDir)
	if _, err := os.Stat(settingsDir); os.IsNotExist(err) {
		err := os.MkdirAll(settingsDir, 0755)
		if err == nil {
			fixPosixPermissions(dataDir)
		} else {
			return patchResult{
				Name:    "temporary runtime settings workaround",
				Applied: false,
				Detail:  "could not create settings directory: " + err.Error(),
			}
		}
	}

	settings := make(map[string]interface{})
	if _, err := os.Stat(settingsPath); err == nil {
		raw, err := os.ReadFile(settingsPath)
		if err == nil && len(strings.TrimSpace(string(raw))) > 0 {
			json.Unmarshal(raw, &settings)
		}
	}

	beforeBytes, _ := json.Marshal(settings)

	settings["jetski.cloudCodeUrl"] = CloudCodeEndpoint
	settings["codeiumDev.forceDisableExperiments"] = strings.Join(RuntimeExperimentsToDisable, ",")

	env, ok := settings["codeiumDev.languageServerEnv"].(map[string]interface{})
	if !ok {
		env = make(map[string]interface{})
	}
	env["BORG_DISABLE_EXPERIMENTS"] = strings.Join(RuntimeExperimentsToDisable, ",")
	env["BORG_EXPERIMENTS"] = ""
	settings["codeiumDev.languageServerEnv"] = env

	afterBytes, _ := json.Marshal(settings)
	if string(beforeBytes) == string(afterBytes) {
		return patchResult{
			Name:    "temporary runtime settings workaround",
			Applied: false,
			Detail:  "already present",
		}
	}

	backupPath := backupJsonFile(settingsPath)
	fBytes, err := json.MarshalIndent(settings, "", "    ")
	if err != nil {
		return patchResult{
			Name:    "temporary runtime settings workaround",
			Applied: false,
			Detail:  "failed to format json: " + err.Error(),
		}
	}

	err = os.WriteFile(settingsPath, append(fBytes, '\n'), 0644)
	if err != nil {
		return patchResult{
			Name:    "temporary runtime settings workaround",
			Applied: false,
			Detail:  "write error: " + err.Error(),
		}
	}
	fixPosixPermissions(settingsPath)

	detail := "updated " + settingsPath
	if backupPath != "" {
		detail += "; backup: " + filepath.Base(backupPath)
	}

	return patchResult{
		Name:    "temporary runtime settings workaround",
		Applied: true,
		Detail:  detail,
	}
}

func printRuntimeSettingsResult(res patchResult) {
	var applied interface{} = res.Applied
	if !res.Applied && strings.HasPrefix(res.Detail, "skipped") {
		applied = nil
	}
	step(res.Name, applied, res.Detail)
}

func warnAboutUnsafeBackup(mainJsPath string) (bool, bool) {
	bak := mainJsPath + ".bak"
	if _, err := os.Stat(bak); os.IsNotExist(err) {
		return true, false
	}

	bakSize := fileSize(bak)
	curSize := fileSize(mainJsPath)
	warnings := false

	data, err := os.ReadFile(bak)
	if err != nil {
		warn("Backup check error: " + err.Error())
		return false, false
	}

	if bakSize <= 2048 || len(strings.TrimSpace(string(data))) <= 512 {
		warn(fmt.Sprintf("backup size is only %s and it looks almost empty", formatBytes(bakSize)))
		warnings = true
	} else if bakSize < 4096 || (curSize > 0 && bakSize < curSize/10) {
		warn(fmt.Sprintf("backup is much smaller than expected (%s vs %s)", formatBytes(bakSize), formatBytes(curSize)))
		warnings = true
	}

	if warnings {
		warn("Restoring this backup may break Antigravity IDE.")
		warn("Backup kept: " + filepath.Base(bak))
	}
	return true, warnings
}

func doPatch(mainJsPath string) {
	if fi, err := os.Stat(mainJsPath); err != nil || fi.IsDir() {
		errLine := "Target is not a file: " + mainJsPath
		if err != nil {
			errLine = err.Error()
		}
		consoleErr(errLine)
		hint("Please select a valid main.js file or Antigravity IDE folder.")
		return
	}

	verStatus, verStr := checkAgVersion(mainJsPath)
	if verStatus == VersionStatusTooOld {
		consoleErr("Unsupported version: " + verStr)
		consoleErr("Minimum required: " + MinAgVersion)
		hint("Please update Antigravity IDE and try again.")
		if !confirmed("Proceed anyway?") {
			return
		}
	} else if verStatus == VersionStatusNotFound {
		warn("Could not detect Antigravity IDE version (registry key or package.json not found).")
		if !confirmed("Proceed without version check?") {
			return
		}
	} else if verStatus == VersionStatusParseError {
		warn("Could not parse version string: " + verStr)
		if !confirmed("Proceed anyway?") {
			return
		}
	}

	data, err := os.ReadFile(mainJsPath)
	if err != nil {
		consoleErr("Read error: " + err.Error())
		return
	}
	content := string(data)

	currentIsPatched := isAlreadyPatched(content)
	runtimeSettingsChecked := false

	if currentIsPatched {
		hint("File appears already patched.")
		info("Applying runtime settings workaround...")
		printRuntimeSettingsResult(patchRuntimeSettings(verStr))
		runtimeSettingsChecked = true
		if !confirmed("Apply main.js patches anyway?") {
			return
		}
	}

	bak := mainJsPath + ".bak"
	if _, err := os.Stat(bak); os.IsNotExist(err) && !currentIsPatched {
		info("Creating backup...")
		if err := copyFile(mainJsPath, bak); err == nil {
			fixPosixPermissions(bak)
			consoleOk(fmt.Sprintf("Backup: %s (%s)", filepath.Base(bak), formatBytes(fileSize(bak))))
		} else {
			consoleErr("Backup error: " + err.Error())
			return
		}
	} else if _, err := os.Stat(bak); err == nil {
		hint("Backup already exists — skipping")
	} else if currentIsPatched {
		warn("main.js is already patched — no backup needed")
	}

	hashBefore := fileHash(mainJsPath)

	info("Applying patches...")
	fmt.Println()

	newContent, results := applyPatchesMinimal(content, verStr)

	applied := 0
	for _, r := range results {
		if r.Applied {
			applied++
		}
		step(r.Name, r.Applied, r.Detail)
	}
	fmt.Println()

	if applied == 0 {
		consoleErr("No patches applied.")
		return
	}

	writeSuccess := false
	for attempt := 0; attempt < 2; attempt++ {
		err := os.WriteFile(mainJsPath, []byte(newContent), 0644)
		if err == nil {
			fixPosixPermissions(mainJsPath)
			writeSuccess = true
			break
		}

		// check permissions / lock
		if os.IsPermission(err) || strings.Contains(err.Error(), "sharing violation") || strings.Contains(err.Error(), "locked") {
			if attempt == 0 {
				warn("Permission denied (file locked): " + err.Error())
				if confirmed("Would you like to automatically close running Antigravity processes and retry?") {
					terminateProcesses([]string{"Antigravity", "Antigravity IDE", "antigravity", "antigravity-ide"})
					time.Sleep(1500 * time.Millisecond)
					continue
				}
			}
			consoleErr("Write error (Permission denied): " + err.Error())
			return
		} else {
			consoleErr("Write error: " + err.Error())
			return
		}
	}

	if !writeSuccess {
		return
	}

	hashAfter := fileHash(mainJsPath)
	resignMacosBundle(mainJsPath)

	if !runtimeSettingsChecked {
		info("Applying runtime settings workaround...")
		printRuntimeSettingsResult(patchRuntimeSettings(verStr))
	}

	var panelRows [][]string
	panelRows = append(panelRows, []string{"Target", filepath.Base(mainJsPath)})
	panelRows = append(panelRows, []string{"Patches", fmt.Sprintf("%d/%d applied", applied, len(results))})
	if _, err := os.Stat(bak); err == nil {
		panelRows = append(panelRows, []string{"Backup", fmt.Sprintf("%s (%s)", filepath.Base(bak), formatBytes(fileSize(bak)))})
	}
	if hashBefore != "" && hashAfter != "" {
		panelRows = append(panelRows, []string{"Before", hashBefore[:8] + "..." + hashBefore[len(hashBefore)-8:]})
		panelRows = append(panelRows, []string{"After", hashAfter[:8] + "..." + hashAfter[len(hashAfter)-8:]})
	}
	panelRows = append(panelRows, []string{"Done", time.Now().Format("15:04:05")})

	printPanel("PATCH COMPLETE", panelRows, ColorGreen)
	hint("Restart Antigravity IDE and sign in.")
}

func doFix429() {
	dataDir := getUserDataDir()
	if dataDir == "" {
		consoleErr("Antigravity IDE data directory not found.")
		return
	}
	if fi, err := os.Stat(dataDir); err != nil || !fi.IsDir() {
		consoleErr("Antigravity IDE data directory not found.")
		return
	}

	info("Data directory: " + color(dataDir, ColorCyan))
	warn("This will reset your Antigravity IDE configuration (tokens, quota).")
	warn("Dialogues will be preserved, but you will need to sign in again.")
	consoleErr("Ensure Antigravity IDE is COMPLETELY closed before proceeding.")

	if !confirmed("Proceed with the fix?") {
		return
	}
	fmt.Println()

	timestamp := time.Now().Format("20060102_150405")
	backupDir := dataDir + "_backup_" + timestamp
	counter := 1
	for {
		if _, err := os.Stat(backupDir); os.IsNotExist(err) {
			break
		}
		backupDir = fmt.Sprintf("%s_%d", dataDir+"_backup_"+timestamp, counter)
		counter++
	}

	info("Moving current data to: " + filepath.Base(backupDir) + "...")

	moveSuccess := false
	for attempt := 0; attempt < 2; attempt++ {
		err := os.Rename(dataDir, backupDir)
		if err == nil {
			moveSuccess = true
			break
		}

		if attempt == 0 {
			warn("Permission denied (files locked): " + err.Error())
			if confirmed("Would you like to automatically close running Antigravity processes and retry?") {
				terminateProcesses([]string{"Antigravity", "Antigravity IDE", "antigravity", "antigravity-ide"})
				time.Sleep(1500 * time.Millisecond)
				continue
			}
		}
		consoleErr("Permission denied: Could not move data directory.")
		consoleErr("Antigravity IDE is likely still running or holding files.")
		hint("Close Antigravity IDE completely (check Task Manager) and try again.")
		return
	}

	if !moveSuccess {
		return
	}

	consoleOk("Data moved to backup")
	info("Creating fresh configuration...")

	userDir := filepath.Join(dataDir, "User")
	err := os.MkdirAll(userDir, 0755)
	if err != nil {
		consoleErr("Failed to create user config directory: " + err.Error())
		return
	}

	storageFolders := []string{"globalStorage", "workspaceStorage"}
	restoredCount := 0
	for _, folder := range storageFolders {
		src := filepath.Join(backupDir, "User", folder)
		dst := filepath.Join(userDir, folder)
		if fi, err := os.Stat(src); err == nil && fi.IsDir() {
			info("Restoring " + folder + "...")
			err := copyDir(src, dst)
			if err == nil {
				restoredCount++
			} else {
				warn("Could not restore " + folder + ": " + err.Error())
			}
		}
	}

	if restoredCount > 0 {
		consoleOk(fmt.Sprintf("Restored %d storage folder(s)", restoredCount))
	} else {
		hint("No storage folders were restored")
	}

	fixPosixPermissions(dataDir)

	var panelRows [][]string
	panelRows = append(panelRows, []string{"Backup", filepath.Base(backupDir)})
	panelRows = append(panelRows, []string{"Folders", fmt.Sprintf("%d restored", restoredCount)})

	printPanel("HTTP 429 FIX APPLIED", panelRows, ColorGreen)
	hint("What to do now:")
	fmt.Println("      1. Start Antigravity IDE.")
	fmt.Println("      2. Sign in to your account.")
	fmt.Println("      3. If you still see errors, run 'Apply patch' (Option 1) again.")
	warn("Note: VPNs or other bypass methods might be detected by Google and cause 429 errors.")
	hint("Your backup is safe at: " + backupDir)
}

func copyDir(src string, dst string) error {
	return filepath.Walk(src, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		relPath, err := filepath.Rel(src, path)
		if err != nil {
			return err
		}
		targetPath := filepath.Join(dst, relPath)
		if info.IsDir() {
			return os.MkdirAll(targetPath, info.Mode())
		}
		return copyFile(path, targetPath)
	})
}

func doRestore(mainJsPath string) {
	okCheck, hasWarnings := warnAboutUnsafeBackup(mainJsPath)
	if !okCheck {
		return
	}

	bak := mainJsPath + ".bak"
	if _, err := os.Stat(bak); os.IsNotExist(err) {
		consoleErr("Backup file not found: " + bak)
		return
	}

	data, err := os.ReadFile(bak)
	if err != nil {
		consoleErr("Could not read backup: " + err.Error())
		return
	}

	if len(data) <= 2048 {
		consoleErr("Backup looks too small — may be corrupted!")
		if !confirmed("Restore anyway?") {
			hint("Restore cancelled.")
			return
		}
	}

	if isAlreadyPatched(string(data)) {
		warn("Backup itself appears to be patched!")
		if !confirmed("Restore this patched backup?") {
			hint("Restore cancelled.")
			return
		}
	}

	restoreQuestion := "Restore backup?"
	if hasWarnings {
		restoreQuestion = "Restore this backup anyway?"
	}
	if !confirmed(restoreQuestion) {
		hint("Restore cancelled.")
		return
	}

	hashBefore := fileHash(mainJsPath)

	tmpPath := mainJsPath + ".tmp"
	err = os.WriteFile(tmpPath, data, 0644)
	if err != nil {
		consoleErr("Restore error (write temp): " + err.Error())
		return
	}

	err = os.Rename(tmpPath, mainJsPath)
	if err != nil {
		// Try fallback if rename fails across partitions
		err = copyFile(tmpPath, mainJsPath)
		os.Remove(tmpPath)
		if err != nil {
			consoleErr("Restore error: " + err.Error())
			return
		}
	}
	fixPosixPermissions(mainJsPath)

	hashAfter := fileHash(mainJsPath)
	resignMacosBundle(mainJsPath)

	redrawMainScreen(mainJsPath, "", "", false)
	fmt.Println()

	var panelRows [][]string
	panelRows = append(panelRows, []string{"Target", filepath.Base(mainJsPath)})
	if hashBefore != "" && hashAfter != "" && hashBefore != hashAfter {
		panelRows = append(panelRows, []string{"Before", hashBefore[:8] + "..." + hashBefore[len(hashBefore)-8:]})
		panelRows = append(panelRows, []string{"After", hashAfter[:8] + "..." + hashAfter[len(hashAfter)-8:]})
	}
	panelRows = append(panelRows, []string{"Done", time.Now().Format("15:04:05")})

	printPanel("RESTORE COMPLETE", panelRows, ColorGreen)
}
