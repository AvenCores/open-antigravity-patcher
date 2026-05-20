import sys
import os
import subprocess

from patcher.utils.admin import is_admin, run_as_admin
from patcher.utils.console import setup_console
from patcher.cli import run_cli, confirmed


def ensure_linux_terminal():
    if sys.platform != 'linux':
        return
    if not getattr(sys, 'frozen', False):
        return
    if (sys.stdout and sys.stdout.isatty()) or (sys.stdin and sys.stdin.isatty()):
        return
    
    terminals = [
        ['x-terminal-emulator', '-e'],
        ['gnome-terminal', '--'],
        ['konsole', '-e'],
        ['xfce4-terminal', '-x'],
        ['mate-terminal', '-x'],
        ['lxterminal', '-e'],
        ['tilix', '-e'],
        ['terminator', '-e'],
        ['xterm', '-e']
    ]
    
    executable = sys.executable
    args = sys.argv[1:]
    
    for term in terminals:
        try:
            subprocess.Popen(term + [executable] + args)
            sys.exit(0)
        except Exception:
            continue


if __name__ == "__main__":
    ensure_linux_terminal()
    setup_console()
    if os.name == "nt" and not is_admin():
        if run_as_admin():
            sys.exit(0)
        else:
            print("  [!] Could not elevate privileges. The script may fail to modify files.")
    elif os.name == "posix" and not is_admin():
        print("  [!] Root access is required to patch files in /usr/share/antigravity-ide.")
        if confirmed("Re-launch with sudo?"):
            try:
                if getattr(sys, "frozen", False):
                    args = ["sudo", sys.executable] + sys.argv[1:]
                else:
                    args = ["sudo", sys.executable] + sys.argv
                os.execvp("sudo", args)
            except Exception as e:
                print(f"  [!] Failed to re-launch with sudo: {e}")
                sys.exit(1)
        else:
            from patcher.constants import COLOR_YELLOW
            from patcher.utils.console import color
            print(color("  [!] Proceeding without root. Write errors are possible.", COLOR_YELLOW))
            print()

    try:
        run_cli()
    except KeyboardInterrupt:
        print("\n  [i] Exiting...")
        sys.exit(0)