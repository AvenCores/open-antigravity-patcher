import os
import sys
import ctypes
import subprocess


def is_admin():
    try:
        if os.name == "posix":
            return os.getuid() == 0
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def run_as_admin():
    if os.name != "nt":
        return True
    if is_admin():
        return True

    # Автоматическое повышение прав с обработкой путей с пробелами
    if getattr(sys, "frozen", False):
        executable = sys.executable
        args_str = " ".join([f'"{a}"' for a in sys.argv[1:]])
    else:
        executable = sys.executable
        script = sys.argv[0]
        args_str = " ".join([f'"{a}"' for a in [script] + sys.argv[1:]])

    try:
        ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, args_str, None, 1)
        return ret > 32
    except Exception:
        return False


def terminate_processes(names):
    """Пытается завершить процессы по их именам."""
    success = False
    for name in names:
        try:
            if os.name == "nt":
                exec_name = name if name.lower().endswith(".exe") else f"{name}.exe"
                res = subprocess.run(
                    ["taskkill", "/F", "/IM", exec_name],
                    capture_output=True, text=True, timeout=10
                )
                if res.returncode == 0:
                    success = True
            else:
                res = subprocess.run(
                    ["pkill", "-f", name],
                    capture_output=True, text=True, timeout=10
                )
                if res.returncode == 0:
                    success = True
        except Exception:
            pass
    return success
