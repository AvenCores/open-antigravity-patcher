import os
import sys
import glob
import shutil
import struct
import json


def clean_path(raw_path):
    return raw_path.strip().strip('"').strip("'")


def _dedup_newest(paths):
    seen = set()
    out = []
    existing = {p for p in paths if p and os.path.exists(p)}
    for p in sorted(existing, key=lambda x: os.path.getmtime(x), reverse=True):
        key = os.path.normcase(os.path.realpath(p))
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def _win_candidate_roots():
    out = []
    for var in ("LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)", "ProgramData", "APPDATA"):
        p = os.environ.get(var)
        if not p:
            continue
        out.append(os.path.join(p, "Programs"))
        out.append(p)
    up = os.environ.get("USERPROFILE", "")
    if up:
        out.append(os.path.join(up, "scoop", "apps"))
    scoop = os.environ.get("SCOOP", "")
    if scoop:
        out.append(os.path.join(scoop, "apps"))
    
    # Реестр
    try:
        import winreg
        hives = [(winreg.HKEY_CURRENT_USER, 'HKCU'), (winreg.HKEY_LOCAL_MACHINE, 'HKLM')]
        subkeys = [
            r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
            r'SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall'
        ]
        for hive, _ in hives:
            for subkey in subkeys:
                try:
                    with winreg.OpenKey(hive, subkey) as key:
                        info_key = winreg.QueryInfoKey(key)
                        for i in range(info_key[0]):
                            try:
                                name = winreg.EnumKey(key, i)
                                with winreg.OpenKey(key, name) as sub:
                                    disp = ''
                                    try:
                                        disp, _ = winreg.QueryValueEx(sub, 'DisplayName')
                                    except OSError:
                                        pass
                                    if disp and 'antigravity' in disp.lower():
                                        try:
                                            loc, _ = winreg.QueryValueEx(sub, 'InstallLocation')
                                            if loc:
                                                out.append(loc)
                                        except OSError:
                                            pass
                            except OSError:
                                pass
                except OSError:
                    pass
    except ImportError:
        pass
    
    return [p for p in out if p and os.path.isdir(p)]


def _posix_candidate_roots():
    from patcher.utils.file import get_posix_invoking_user_home
    user_home = get_posix_invoking_user_home()
    out = ["/opt", "/usr/share", "/usr/lib", "/usr/local/share", "/usr/local/lib"]
    if sys.platform == "darwin":
        out.append("/Applications")
        if user_home:
            out.append(os.path.join(user_home, "Applications"))
        else:
            out.append(os.path.expanduser("~/Applications"))
    
    if user_home:
        out.append(os.path.join(user_home, ".local/share"))
    else:
        out.append(os.path.expanduser("~/.local/share"))
    return [p for p in out if p and os.path.isdir(p)]


def find_manager_binary():
    """Ищет бинарный файл language_server (language_server.exe на Windows)."""
    rel = os.path.join("resources", "bin", "language_server" + (".exe" if os.name == "nt" else ""))
    
    # 1. Поиск в PATH через which
    w = shutil.which("language_server")
    if w:
        return w
        
    cands = []
    
    # 2. Поиск в стандартных директориях
    if os.name == "nt":
        for root in _win_candidate_roots():
            cands += glob.glob(os.path.join(root, "*ntigravity*", rel))
            cands += glob.glob(os.path.join(root, "*ntigravity*", "*", rel))
            direct = os.path.join(root, rel)
            if os.path.isfile(direct):
                cands.append(direct)
    else:
        for root in _posix_candidate_roots():
            cands += glob.glob(os.path.join(root, "*ntigravity*", rel))
            cands += glob.glob(os.path.join(root, "*ntigravity*", "*", rel))
            # macOS .app support
            if sys.platform == "darwin":
                cands += glob.glob(os.path.join(root, "*ntigravity*.app", "Contents", "Resources", "app", rel))
            direct = os.path.join(root, rel)
            if os.path.isfile(direct):
                cands.append(direct)
                
    deduped = _dedup_newest(cands)
    return deduped[0] if deduped else ""


def resolve_manager_path(raw_path):
    if not raw_path:
        return ""
    cleaned = clean_path(raw_path)
    if not cleaned:
        return ""
    resolved = os.path.abspath(os.path.expandvars(os.path.expanduser(cleaned)))
    
    if os.path.isfile(resolved):
        name = os.path.basename(resolved).lower()
        if name in ("language_server", "language_server.exe"):
            return resolved
        return resolved
        
    if os.path.isdir(resolved):
        rel = os.path.join("resources", "bin", "language_server" + (".exe" if os.name == "nt" else ""))
        path1 = os.path.join(resolved, rel)
        if os.path.isfile(path1):
            return path1
        # macOS app contents
        if sys.platform == "darwin":
            path2 = os.path.join(resolved, "Contents", "Resources", "app", rel)
            if os.path.isfile(path2):
                return path2
        # direct bin inside
        path3 = os.path.join(resolved, "language_server" + (".exe" if os.name == "nt" else ""))
        if os.path.isfile(path3):
            return path3
            
    return ""


def _read_asar_header(f):
    try:
        f.seek(0)
        _, header_size, _, json_size = struct.unpack('<IIII', f.read(16))
        json_bytes = f.read(json_size)
        header = json.loads(json_bytes.decode('utf-8'))
        payload_offset = 8 + header_size
        return header, payload_offset
    except Exception:
        return None, None


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


def find_asar_relative_to_manager(manager_path):
    parent = os.path.dirname(manager_path)
    for _ in range(4):
        if not parent or parent == os.path.dirname(parent):
            break
        for sub in ("resources/app.asar", "resources/app1.asar", "app.asar", "app1.asar", "Contents/Resources/app.asar", "Contents/Resources/app1.asar"):
            p = os.path.join(parent, sub)
            if os.path.exists(p):
                return p
        parent = os.path.dirname(parent)
    return ""


def get_antigravity_version(manager_path):
    asar_path = find_asar_relative_to_manager(manager_path)
    if not asar_path:
        return None
    return read_package_json_from_asar(asar_path)
