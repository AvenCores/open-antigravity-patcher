import os
import sys
import json
import struct
import mmap

from patcher.asar.archive import _read_asar_header


def find_antigravity_root():
    candidates = []

    if sys.platform == "darwin":
        mac_candidates = [
            "/Applications/Antigravity.app",
            os.path.expanduser("~/Applications/Antigravity.app"),
            "/Applications/antigravity.app",
            os.path.expanduser("~/Applications/antigravity.app"),
        ]
        for app in mac_candidates:
            if os.path.exists(app):
                candidates.append(app)
    elif os.name == "posix":
        candidates.extend([
            "/usr/share/antigravity",
            "/opt/Antigravity",
            "/opt/antigravity",
            "/usr/local/share/antigravity",
            "/usr/local/share/Antigravity",
        ])

    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            candidates.append(os.path.join(local_app_data, "Programs", "Antigravity"))
            candidates.append(os.path.join(local_app_data, "Programs", "antigravity"))
        pf = os.environ.get("PROGRAMFILES")
        if pf:
            candidates.append(os.path.join(pf, "Antigravity"))
        pfx86 = os.environ.get("PROGRAMFILES(X86)")
        if pfx86:
            candidates.append(os.path.join(pfx86, "Antigravity"))

        try:
            import winreg
            hives = [
                (winreg.HKEY_CURRENT_USER, 'HKCU'),
                (winreg.HKEY_LOCAL_MACHINE, 'HKLM')
            ]
            subkeys = [
                r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
                r'SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall'
            ]
            for hive, hname in hives:
                for subkey in subkeys:
                    try:
                        with winreg.OpenKey(hive, subkey) as key:
                            info = winreg.QueryInfoKey(key)
                            for i in range(info[0]):
                                try:
                                    name = winreg.EnumKey(key, i)
                                    with winreg.OpenKey(key, name) as sub:
                                        disp = ''
                                        try:
                                            disp, _ = winreg.QueryValueEx(sub, 'DisplayName')
                                        except OSError:
                                            pass
                                        
                                        disp_lower = disp.lower()
                                        name_lower = name.lower()
                                        if ('antigravity' in disp_lower or 'antigravity' in name_lower) and \
                                           'ide' not in disp_lower and 'ide' not in name_lower and \
                                           'tools' not in disp_lower and 'tools' not in name_lower:
                                            
                                            try:
                                                icon_val, _ = winreg.QueryValueEx(sub, 'DisplayIcon')
                                                if icon_val:
                                                    icon_path = icon_val.split(',')[0].strip().strip('"')
                                                    if icon_path:
                                                        candidates.append(os.path.dirname(icon_path))
                                            except OSError:
                                                pass

                                            try:
                                                uninst_val, _ = winreg.QueryValueEx(sub, 'UninstallString')
                                                if uninst_val:
                                                    uninst_path = uninst_val.split('.exe')[0].strip().strip('"')
                                                    if uninst_path:
                                                        candidates.append(os.path.dirname(uninst_path + '.exe'))
                                            except OSError:
                                                pass
                                except OSError:
                                    pass
                    except OSError:
                        pass
        except ImportError:
            pass

    # Always execute portable search to print matches for visibility
    from patcher.ide.discovery import find_portable_candidates
    portable = find_portable_candidates("antigravity")

    # 1. Return standard if valid
    for path in candidates:
        path = os.path.abspath(path)
        if os.path.exists(os.path.join(path, "resources", "app.asar")) or \
           os.path.exists(os.path.join(path, "resources", "app1.asar")):
            return path
        if sys.platform == "darwin" and path.endswith(".app"):
            resources_path = os.path.join(path, "Contents", "Resources")
            if os.path.exists(os.path.join(resources_path, "app.asar")) or \
               os.path.exists(os.path.join(resources_path, "app1.asar")):
                return path

    # 2. Return portable if found
    if portable:
        return portable[0]

    # 3. Fallback to any existing candidate directory
    for path in candidates:
        if os.path.isdir(path):
            return path

    return ""


def resolve_antigravity_paths(root):
    if sys.platform == "darwin" and root.endswith(".app"):
        asar = os.path.join(root, "Contents", "Resources", "app.asar")
        if not os.path.exists(asar):
            asar = os.path.join(root, "Contents", "Resources", "app1.asar")
        exe = os.path.join(root, "Contents", "MacOS", "Antigravity")
        if not os.path.exists(exe):
            lower_exe = os.path.join(root, "Contents", "MacOS", "antigravity")
            if os.path.exists(lower_exe):
                exe = lower_exe
        return asar, exe

    asar = os.path.join(root, "resources", "app.asar")
    if not os.path.exists(asar):
        asar = os.path.join(root, "resources", "app1.asar")

    exe_name = "Antigravity"
    if os.name == "nt":
        exe_name += ".exe"

    exe = os.path.join(root, exe_name)
    if os.name == "posix" and sys.platform != "darwin":
        if not os.path.exists(exe):
            lower_exe = os.path.join(root, "antigravity")
            if os.path.exists(lower_exe):
                exe = lower_exe

    return asar, exe


def is_antigravity_patched(asar_path):
    if not os.path.exists(asar_path):
        return False
    try:
        with open(asar_path, 'rb') as f:
            size = os.fstat(f.fileno()).st_size
            if size == 0:
                return False
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                return mm.find(b"patchFrontendMainJs") != -1
            finally:
                mm.close()
    except Exception:
        return False


def read_package_json_from_asar(asar_path):
    if not os.path.exists(asar_path):
        return None
    try:
        with open(asar_path, 'rb') as f:
            header, payload_offset = _read_asar_header(f)
            if header is None:
                return None

            files = header.get('files', {})
            pkg_entry = files.get('package.json')
            if pkg_entry and 'offset' in pkg_entry and 'size' in pkg_entry:
                offset = int(pkg_entry['offset'])
                size = pkg_entry['size']
                f.seek(payload_offset + offset)
                data = f.read(size)
                pkg_data = json.loads(data.decode('utf-8'))
                return pkg_data.get('version')
    except Exception:
        pass
    return None
