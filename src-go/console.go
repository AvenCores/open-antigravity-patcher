package main

import (
	"fmt"
	"os"
	"os/exec"
	"regexp"
	"runtime"
	"strings"
	"unicode/utf8"
)

var (
	UseColor  = false
	ansiRegex = regexp.MustCompile(`\x1b\[[0-9;]*[a-zA-Z]`)
)

func visibleLen(text string) int {
	stripped := ansiRegex.ReplaceAllString(text, "")
	return utf8.RuneCountInString(stripped)
}

func setupConsole() {
	setupPlatformConsole()
}

func color(text string, styles ...string) string {
	if !UseColor || len(styles) == 0 {
		return text
	}
	return strings.Join(styles, "") + text + ColorReset
}

func clearScreen() {
	if runtime.GOOS == "windows" {
		cmd := exec.Command("cmd", "/c", "cls")
		cmd.Stdout = os.Stdout
		cmd.Run()
	} else {
		cmd := exec.Command("clear")
		cmd.Stdout = os.Stdout
		cmd.Run()
	}
}

const (
	BannerInnerWidth = 47
	MenuWidth        = BannerInnerWidth + 2
)

func frameBorder(leftCh, fillCh, rightCh string, accent ...string) string {
	acc := ColorCyan
	if len(accent) > 0 {
		acc = accent[0]
	}
	return color(leftCh+strings.Repeat(fillCh, BannerInnerWidth)+rightCh, acc, ColorBold)
}

func frameRow(left, right string, accent ...string) string {
	acc := ColorCyan
	if len(accent) > 0 {
		acc = accent[0]
	}
	leftStr := "  " + left
	fill := BannerInnerWidth - visibleLen(leftStr) - visibleLen(right) - 1
	if fill < 1 {
		fill = 1
	}
	body := leftStr + strings.Repeat(" ", fill) + right + " "
	vis := visibleLen(body)
	if vis < BannerInnerWidth {
		body = leftStr + strings.Repeat(" ", fill+BannerInnerWidth-vis) + right + " "
	} else if vis > BannerInnerWidth {
		// Truncate to fit if somehow wider
		runes := []rune(body)
		for visibleLen(string(runes)) > BannerInnerWidth && len(runes) > 0 {
			runes = runes[:len(runes)-1]
		}
		body = string(runes)
	}
	return color("║", acc, ColorBold) + body + color("║", acc, ColorBold)
}

func printBanner() {
	titleLeft := color("Open AG Patcher", ColorBold)
	titleRight := color("v"+Version, ColorGreen, ColorBold)

	labelCol := 12
	telegramLabel := color(fmt.Sprintf("%-*s", labelCol, "Telegram"), ColorYellow)
	telegram := telegramLabel + color("t.me/avencoresyt", ColorDim)
	youtubeLabel := color(fmt.Sprintf("%-*s", labelCol, "YouTube"), ColorYellow)
	youtube := youtubeLabel + color("youtube.com/@avencores", ColorDim)

	fmt.Println()
	fmt.Printf("  %s\n", frameBorder("╔", "═", "╗"))
	fmt.Printf("  %s\n", frameRow(titleLeft, titleRight))
	fmt.Printf("  %s\n", frameRow(color("Region bypass for Antigravity", ColorCyan), ""))
	fmt.Printf("  %s\n", frameRow(color("Clean • No keys • No telemetry", ColorGreen), ""))
	fmt.Printf("  %s\n", frameBorder("╟", "─", "╢"))
	fmt.Printf("  %s\n", frameRow(telegram, ""))
	fmt.Printf("  %s\n", frameRow(youtube, ""))
	fmt.Printf("  %s\n", frameBorder("╚", "═", "╝"))
	fmt.Println()
}

func printPanel(title string, rows [][]string, accent ...string) {
	acc := ColorGreen
	if len(accent) > 0 {
		acc = accent[0]
	}
	fmt.Println()
	fmt.Printf("  %s\n", frameBorder("╔", "═", "╗", acc))
	fmt.Printf("  %s\n", frameRow(color(title, ColorBold), "", acc))
	fmt.Printf("  %s\n", frameBorder("╟", "─", "╢", acc))
	for _, row := range rows {
		label := row[0]
		val := row[1]
		if !strings.Contains(val, "\x1b[") {
			val = color(val, ColorCyan)
		}
		labelText := color(label+":", ColorWhite)
		fmt.Printf("  %s\n", frameRow(labelText, val, acc))
	}
	fmt.Printf("  %s\n", frameBorder("╚", "═", "╝", acc))
	fmt.Println()
}

func info(msg string) {
	fmt.Printf("  [*] %s\n", msg)
}

func hint(msg string) {
	fmt.Println(color(fmt.Sprintf("  [i] %s", msg), ColorDim))
}

func consoleOk(msg string) {
	fmt.Println(color(fmt.Sprintf("  [+] %s", msg), ColorGreen, ColorBold))
}

func warn(msg string) {
	fmt.Println(color(fmt.Sprintf("  [!] %s", msg), ColorYellow))
}

func consoleErr(msg string) {
	fmt.Println(color(fmt.Sprintf("  [!] %s", msg), ColorRed))
}

func cancel(msg string) {
	fmt.Println(color(fmt.Sprintf("  [x] %s", msg), ColorDim))
}

func step(name string, applied interface{}, detail string) {
	var marker string
	if applied == nil {
		marker = color("•", ColorDim)
	} else {
		if val, isBool := applied.(bool); isBool {
			if val {
				marker = color("✓", ColorGreen)
			} else {
				marker = color("✗", ColorRed)
			}
		} else {
			marker = color("•", ColorDim)
		}
	}
	line := fmt.Sprintf("  %s %s", marker, name)
	if detail != "" {
		line += color(" — "+detail, ColorDim)
	}
	fmt.Println(line)
}

func printMenuSection(title string) {
	label := fmt.Sprintf(" %s ", title)
	dashesCount := MenuWidth - len(label) - 1
	if dashesCount < 1 {
		dashesCount = 1
	}
	dashes := strings.Repeat("─", dashesCount)
	line := color("─", ColorGray) + color(label, ColorCyan, ColorBold) + color(dashes, ColorGray)
	fmt.Printf("  %s\n", line)
}

func printMenuRow(number, label, labelHint string, accent ...string) {
	acc := ColorGreen
	if len(accent) > 0 {
		acc = accent[0]
	}
	var numPart string
	if number != "" {
		numPart = color(fmt.Sprintf("[%s]", number), acc, ColorBold)
	} else {
		numPart = color("  ", ColorGray)
	}
	labelPart := color(label, ColorWhite)
	left := fmt.Sprintf("  %s  %s", numPart, labelPart)
	if labelHint == "" {
		fmt.Println(left)
		return
	}
	leftVis := visibleLen(left)
	gap := MenuWidth + 2 - leftVis - visibleLen(labelHint)
	if gap < 2 {
		gap = 2
	}
	fmt.Printf("%s%s%s\n", left, strings.Repeat(" ", gap), color(labelHint, ColorDim))
}

func printMenuDivider() {
	fmt.Printf("  %s\n", color(strings.Repeat("─", MenuWidth), ColorGray))
}

func printMenuFooter(note string) {
	fmt.Printf("  %s\n", color(strings.Repeat("─", MenuWidth), ColorGray))
	if note != "" {
		fmt.Printf("  %s\n", color(note, ColorDim))
	}
}
