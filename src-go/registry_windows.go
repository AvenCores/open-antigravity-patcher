//go:build windows

package main

import (
	"path/filepath"
	"strings"

	"golang.org/x/sys/windows/registry"
)

func registryGetInstallLocation() string {
	for _, hive := range []registry.Key{registry.CURRENT_USER, registry.LOCAL_MACHINE} {
		key, err := registry.OpenKey(hive, AgRegistrySubkey, registry.QUERY_VALUE)
		if err == nil {
			val, _, err := key.GetStringValue("InstallLocation")
			key.Close()
			if err == nil && val != "" {
				return strings.TrimSpace(val)
			}
		}
	}
	return ""
}

func registryGetDisplayVersion() string {
	for _, hive := range []registry.Key{registry.CURRENT_USER, registry.LOCAL_MACHINE} {
		key, err := registry.OpenKey(hive, AgRegistrySubkey, registry.QUERY_VALUE)
		if err == nil {
			val, _, err := key.GetStringValue("DisplayVersion")
			key.Close()
			if err == nil && val != "" {
				return strings.TrimSpace(val)
			}
		}
	}
	return ""
}

func registryFindAntigravityRoots() []string {
	var candidates []string
	hives := []registry.Key{registry.CURRENT_USER, registry.LOCAL_MACHINE}
	subkeys := []string{
		`SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall`,
		`SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall`,
	}

	for _, hive := range hives {
		for _, subkey := range subkeys {
			key, err := registry.OpenKey(hive, subkey, registry.ENUMERATE_SUB_KEYS)
			if err != nil {
				continue
			}
			names, err := key.ReadSubKeyNames(-1)
			key.Close()
			if err != nil {
				continue
			}

			for _, name := range names {
				subKeyPath := subkey + `\` + name
				subKey, err := registry.OpenKey(hive, subKeyPath, registry.QUERY_VALUE)
				if err != nil {
					continue
				}

				disp, _, err := subKey.GetStringValue("DisplayName")
				if err == nil {
					dispLower := strings.ToLower(disp)
					nameLower := strings.ToLower(name)

					if (strings.Contains(dispLower, "antigravity") || strings.Contains(nameLower, "antigravity")) &&
						!strings.Contains(dispLower, "ide") && !strings.Contains(nameLower, "ide") &&
						!strings.Contains(dispLower, "tools") && !strings.Contains(nameLower, "tools") {

						iconVal, _, err := subKey.GetStringValue("DisplayIcon")
						if err == nil && iconVal != "" {
							parts := strings.Split(iconVal, ",")
							iconPath := strings.Trim(parts[0], ` "`)
							if iconPath != "" {
								candidates = append(candidates, filepath.Dir(iconPath))
							}
						}

						uninstVal, _, err := subKey.GetStringValue("UninstallString")
						if err == nil && uninstVal != "" {
							parts := strings.Split(strings.ToLower(uninstVal), ".exe")
							uninstPath := strings.Trim(parts[0], ` "`)
							if uninstPath != "" {
								candidates = append(candidates, filepath.Dir(uninstPath+".exe"))
							}
						}
					}
				}
				subKey.Close()
			}
		}
	}
	return candidates
}
