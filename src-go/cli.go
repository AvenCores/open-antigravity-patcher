package main

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
)

func readConsoleLine(prompt string) string {
	fmt.Print(prompt)
	reader := bufio.NewReader(os.Stdin)
	text, _ := reader.ReadString('\n')
	return strings.TrimRight(text, "\r\n")
}

func promptYN(question string) string {
	q := strings.TrimSpace(question)
	p := fmt.Sprintf("  [?] %s (%s/%s): ", q, color("y", ColorGreen), color("n", ColorRed))
	return strings.ToLower(strings.TrimSpace(readConsoleLine(p)))
}

func confirmed(question string) bool {
	ans := promptYN(question)
	return ans == "y" || ans == "yes" || ans == "д" || ans == "да"
}

func kv(label, valueText, valueColor string) {
	fmt.Printf("      %-9s%s\n", label, color(valueText, valueColor))
}

func printTargetInfo(mainJsPath, antigravityRoot, agyPath string, showSearchLine bool) {
	if showSearchLine {
		info("Searching for installations...")
	}

	// 1. Antigravity IDE Info
	printMenuSection("ANTIGRAVITY IDE")
	target := mainJsPath
	if target == "" {
		target = "Not found"
	}
	kv("Target:", target, ColorCyan)

	if mainJsPath != "" {
		if fi, err := os.Stat(mainJsPath); err == nil {
			if fi.IsDir() {
				kv("Status:", "directory (missing main.js)", ColorYellow)
			} else {
				data, err := os.ReadFile(mainJsPath)
				if err == nil {
					kv("Status:", "found", ColorGreen)
					patchedText := "not patched"
					patchedColor := ColorGreen
					if isAlreadyPatched(string(data)) {
						patchedText = "already patched"
						patchedColor = ColorYellow
					}
					kv("Patch:", patchedText, patchedColor)
				} else {
					kv("Status:", "unreadable", ColorRed)
					kv("Patch:", "unreadable", ColorRed)
				}

				verStr, _ := getAgVersion(mainJsPath)
				verText := "not detected"
				verColor := ColorYellow
				if verStr != "" {
					verText = verStr
					verColor = ColorGreen
				}
				kv("Version:", verText, verColor)

				sizeColor := ColorGreen
				if fi.Size() <= 0 {
					sizeColor = ColorYellow
				}
				kv("Size:", formatBytes(fi.Size()), sizeColor)
			}
		} else {
			kv("Status:", "not found", ColorRed)
		}
	} else {
		kv("Status:", "not found", ColorRed)
	}
	fmt.Println()

	// 2. Antigravity Info
	printMenuSection("ANTIGRAVITY")
	targetAg := antigravityRoot
	if targetAg == "" {
		targetAg = "Not found"
	}
	kv("Target:", targetAg, ColorCyan)

	if antigravityRoot != "" {
		if fi, err := os.Stat(antigravityRoot); err == nil && fi.IsDir() {
			asarPath, _ := resolveAntigravityPaths(antigravityRoot)
			if asarFi, err := os.Stat(asarPath); err == nil {
				kv("Status:", "found", ColorGreen)
				patchedText := "not patched"
				patchedColor := ColorGreen
				if isAntigravityPatched(asarPath) {
					patchedText = "already patched"
					patchedColor = ColorYellow
				}
				kv("Patch:", patchedText, patchedColor)

				verStr := readPackageJsonFromAsar(asarPath)
				verText := "not detected"
				verColor := ColorYellow
				if verStr != "" {
					verText = verStr
					verColor = ColorGreen
				}
				kv("Version:", verText, verColor)

				sizeColor := ColorGreen
				if asarFi.Size() <= 0 {
					sizeColor = ColorYellow
				}
				kv("Size:", formatBytes(asarFi.Size()), sizeColor)
			} else {
				kv("Status:", "ASAR missing", ColorRed)
			}
		} else {
			kv("Status:", "not found", ColorRed)
		}
	} else {
		kv("Status:", "not found", ColorRed)
	}
	fmt.Println()

	// 3. Antigravity CLI Info
	printMenuSection("ANTIGRAVITY CLI")
	targetCli := agyPath
	if targetCli == "" {
		targetCli = "Not found"
	}
	kv("Target:", targetCli, ColorCyan)

	if agyPath != "" {
		if fi, err := os.Stat(agyPath); err == nil && !fi.IsDir() {
			kv("Status:", "found", ColorGreen)
			patchedText := "not patched"
			patchedColor := ColorGreen
			if isAgyPatched(agyPath) {
				patchedText = "already patched"
				patchedColor = ColorYellow
			}
			kv("Patch:", patchedText, patchedColor)

			sizeColor := ColorGreen
			if fi.Size() <= 0 {
				sizeColor = ColorYellow
			}
			kv("Size:", formatBytes(fi.Size()), sizeColor)
		} else {
			kv("Status:", "not found", ColorYellow)
		}
	} else {
		kv("Status:", "not found", ColorYellow)
	}
}

func redrawMainScreen(mainJsPath, antigravityRoot, agyPath string, showSearchLine bool) {
	clearScreen()
	printBanner()
	printTargetInfo(mainJsPath, antigravityRoot, agyPath, showSearchLine)
	fmt.Println()
}

func printLaunchExamples() {
	exeName := "patcher"
	if runtime.GOOS == "windows" {
		exeName += ".exe"
	}
	cmd := exeName

	windowsExample := fmt.Sprintf(`%s "C:\Path\To\Antigravity IDE"`, cmd)
	macosExample := fmt.Sprintf(`%s "/Applications/Antigravity IDE.app"`, cmd)
	linuxExample := fmt.Sprintf(`%s "/usr/share/antigravity-ide"`, cmd)

	hint("Usage examples with custom path:")
	fmt.Printf("      Windows: %s\n", color(windowsExample, ColorYellow))
	fmt.Printf("      macOS:   %s\n", color(macosExample, ColorYellow))
	fmt.Printf("      Linux:   %s\n", color(linuxExample, ColorYellow))
}

func printPathExamples() {
	windowsPath := `C:\Users\Name\AppData\Local\Programs\Antigravity IDE`
	macosPath := "/Applications/Antigravity IDE.app"
	linuxPath := "/usr/share/antigravity-ide"

	hint("Path examples:")
	fmt.Printf("      Windows: %s\n", color(windowsPath, ColorYellow))
	fmt.Printf("      macOS:   %s\n", color(macosPath, ColorYellow))
	fmt.Printf("      Linux:   %s\n", color(linuxPath, ColorYellow))
}

func openWebBrowser(url string) {
	var cmd *exec.Cmd
	switch runtime.GOOS {
	case "windows":
		cmd = exec.Command("cmd", "/c", "start", url)
	case "darwin":
		cmd = exec.Command("open", url)
	default:
		cmd = exec.Command("xdg-open", url)
	}
	cmd.Start()
}

func pauseMenu() {
	readConsoleLine("  Press Enter to return to menu...")
}

func runCli() {
	var mainJsPath, antigravityRoot, agyPath string
	searched := false

	// 1. Process command line arguments
	if len(os.Args) > 1 {
		var args []string
		for _, arg := range os.Args[1:] {
			if arg != "--rollback" && arg != "-r" {
				args = append(args, arg)
			}
		}
		if len(args) > 0 {
			pathArg := strings.Join(args, " ")
			mainJsPath, antigravityRoot = assignCustomPath(pathArg)
			if mainJsPath == "" && antigravityRoot == "" {
				resolvedAgy := resolveAgyPath(pathArg)
				if resolvedAgy != "" {
					agyPath = resolvedAgy
				} else {
					consoleErr("Provided path does not exist or is invalid: " + pathArg)
				}
			}
		}
	}

	// 2. Check current directory
	if mainJsPath == "" && antigravityRoot == "" && agyPath == "" {
		cwd, err := os.Getwd()
		if err == nil {
			local := filepath.Join(cwd, "main.js")
			if _, err := os.Stat(local); err == nil {
				mainJsPath = local
				info("Found main.js in current directory")
			}
		}
	}

	// 3. Auto-search in system
	if mainJsPath == "" && antigravityRoot == "" && agyPath == "" {
		info("Searching for installations...")
		searched = true

		ideRoot := findInstallRoot()
		if ideRoot != "" {
			mainJsPath = findMainJs(ideRoot)
		}
		antigravityRoot = findAntigravityRoot()
		agyPath = findAgyBinary()
	}

	// Prompt manual input if nothing found
	if mainJsPath == "" && antigravityRoot == "" && agyPath == "" {
		warn("No installations found automatically.")
		hint("Please specify the path to Antigravity IDE, Antigravity, agy, or main.js.")
		printPathExamples()
		raw := strings.TrimSpace(readConsoleLine(color("\n  Path > ", ColorCyan, ColorBold)))
		if raw != "" {
			mainJsPath, antigravityRoot = assignCustomPath(raw)
			if mainJsPath == "" && antigravityRoot == "" {
				resolvedAgy := resolveAgyPath(raw)
				if resolvedAgy != "" {
					agyPath = resolvedAgy
				}
			}
		}
	}

	redrawMainScreen(mainJsPath, antigravityRoot, agyPath, searched)

	for {
		printMenuSection("PATCH")
		printMenuRow("1", "Antigravity IDE patch", "bypass region lock", ColorGreen)
		printMenuRow("2", "Antigravity patch", "unlock full app", ColorGreen)
		printMenuRow("3", "Antigravity CLI (agy) patch", "unlock agy tool", ColorGreen)

		printMenuSection("RESTORE")
		printMenuRow("4", "Antigravity IDE", "from backup", ColorYellow)
		printMenuRow("5", "Antigravity", "from backup", ColorYellow)
		printMenuRow("6", "Antigravity CLI", "from backup", ColorYellow)

		printMenuSection("TOOLS")
		printMenuRow("7", "Fix HTTP 429", "rate-limit / too many requests", ColorCyan)
		printMenuRow("8", "Open GitHub repository", "source & updates", ColorCyan)
		printMenuRow("9", "Select custom path", "override auto-detected target", ColorCyan)

		fmt.Println()
		printMenuRow("0", "Exit", "quit the patcher", ColorRed)
		printMenuFooter("Tip: patches are reversible — use RESTORE any time.")

		choice := strings.TrimSpace(readConsoleLine(color("\n  Select option > ", ColorCyan, ColorBold)))
		fmt.Println()

		if choice == "0" {
			return
		}

		// Empty input — do not exit, just redraw menu
		if choice == "" {
			redrawMainScreen(mainJsPath, antigravityRoot, agyPath, searched)
			continue
		}

		validChoices := map[string]bool{
			"1": true, "2": true, "3": true, "4": true, "5": true, "6": true, "7": true, "8": true, "9": true,
		}
		if !validChoices[choice] {
			consoleErr("Invalid choice")
			fmt.Println()
			pauseMenu()
			redrawMainScreen(mainJsPath, antigravityRoot, agyPath, searched)
			continue
		}

		handled := true
		clearScreen()
		printBanner()

		switch choice {
		case "1":
			if mainJsPath != "" {
				doPatch(mainJsPath)
			} else {
				consoleErr("Antigravity IDE path is not set. Please select custom path (Option 9) first.")
			}
		case "2":
			if antigravityRoot != "" {
				doPatchAntigravity(antigravityRoot)
			} else {
				consoleErr("Antigravity path is not set. Please select custom path (Option 9) first.")
			}
		case "3":
			if agyPath != "" {
				doPatchAgy(agyPath)
			} else {
				consoleErr("Antigravity CLI path is not set. Please select custom path (Option 9) first.")
			}
		case "4":
			if mainJsPath != "" {
				doRestore(mainJsPath, searched)
			} else {
				consoleErr("Antigravity IDE path is not set. Please select custom path (Option 9) first.")
			}
		case "5":
			if antigravityRoot != "" {
				doRestoreAntigravity(antigravityRoot)
			} else {
				consoleErr("Antigravity path is not set. Please select custom path (Option 9) first.")
			}
		case "6":
			if agyPath != "" {
				doRestoreAgy(agyPath)
			} else {
				consoleErr("Antigravity CLI path is not set. Please select custom path (Option 9) first.")
			}
		case "7":
			doFix429()
		case "8":
			printTargetInfo(mainJsPath, antigravityRoot, agyPath, searched)
			fmt.Println()
			if confirmed("Open GitHub repository in browser?") {
				url := "https://github.com/AvenCores/open-antigravity-unlock"
				openWebBrowser(url)
				consoleOk(fmt.Sprintf("Opening: %s", color(url, ColorCyan)))
			} else {
				cancel("Cancelled.")
			}
		case "9":
			for {
				redrawMainScreen(mainJsPath, antigravityRoot, agyPath, searched)
				printMenuSection("SELECT CUSTOM PATH")
				printMenuRow("1", "Antigravity IDE path", "folder or main.js", ColorGreen)
				printMenuRow("2", "Antigravity path", "app folder", ColorGreen)
				printMenuRow("3", "Antigravity CLI path", "agy.exe or folder", ColorGreen)
				fmt.Println()
				printMenuRow("0", "Back", "return to main menu", ColorRed)
				printMenuFooter("Leaves auto-detection results intact for other targets.")

				subChoice := strings.TrimSpace(readConsoleLine(color("\n  Select option > ", ColorCyan, ColorBold)))
				if subChoice == "0" {
					break
				}

				switch subChoice {
				case "1":
					fmt.Println()
					hint("Enter the path to Antigravity IDE folder or main.js file.")
					printPathExamples()
					raw := strings.TrimSpace(readConsoleLine(color("\n  IDE Path > ", ColorCyan, ColorBold)))
					if raw != "" {
						newMainJs, _ := assignCustomPath(raw)
						if newMainJs != "" {
							mainJsPath = newMainJs
							searched = false
							consoleOk("Antigravity IDE path updated!")
						} else {
							consoleErr("Could not resolve a valid Antigravity IDE target.")
						}
					}
					pauseMenu()
				case "2":
					fmt.Println()
					hint("Enter the path to Antigravity folder.")
					printPathExamples()
					raw := strings.TrimSpace(readConsoleLine(color("\n  Antigravity Path > ", ColorCyan, ColorBold)))
					if raw != "" {
						_, newAgRoot := assignCustomPath(raw)
						if newAgRoot != "" {
							antigravityRoot = newAgRoot
							searched = false
							consoleOk("Antigravity path updated!")
						} else {
							consoleErr("Could not resolve a valid Antigravity target.")
						}
					}
					pauseMenu()
				case "3":
					fmt.Println()
					hint("Enter the path to the agy binary (agy.exe) or its folder.")
					printPathExamples()
					raw := strings.TrimSpace(readConsoleLine(color("\n  AGY Path > ", ColorCyan, ColorBold)))
					if raw != "" {
						newAgy := resolveAgyPath(raw)
						if newAgy != "" {
							agyPath = newAgy
							searched = false
							consoleOk("Antigravity CLI path updated!")
						} else {
							consoleErr("Could not resolve a valid Antigravity CLI target.")
						}
					}
					pauseMenu()
				}
			}
			handled = true
		}

		fmt.Println()

		if handled {
			pauseMenu()
			redrawMainScreen(mainJsPath, antigravityRoot, agyPath, searched)
		}
	}
}
