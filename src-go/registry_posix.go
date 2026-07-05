//go:build !windows

package main

func registryGetInstallLocation() string {
	return ""
}

func registryGetDisplayVersion() string {
	return ""
}

func registryFindAntigravityRoots() []string {
	return nil
}
