import os
import re
import mmap
import struct
import shutil
import contextlib
import filecmp

from patcher.constants import COLOR_CYAN
from patcher.utils.console import (
    color,
    info,
    hint,
    ok,
    warn,
    err,
    step,
    print_panel,
)
from patcher.utils.file import (
    file_hash,
    file_size,
    format_bytes,
    fix_posix_permissions,
    resign_macos_bundle,
    resign_macos_binary,
)
from patcher.utils.admin import terminate_processes

BAK_EXT = ".agybak"


# ----------------------------------------------------------------------- Gate --
# Байт-сигнатурный патчинг машинного кода Go-бинаря agy/agy.exe.
# Сигнатуры используют re.S, чтобы '.' захватывала также displacement-байт 0x0a.
class Gate:
    def __init__(self, sig, patched, fix, offset=0, desc=""):
        self.sig = re.compile(sig, re.S)
        self.patched = re.compile(patched, re.S)
        self.fix = fix
        self.offset = offset
        self.desc = desc

    def find(self, data):
        """('patched'|'unpatched', file offset to write at).
        LookupError, если сигнатура отсутствует или не уникальна
        (неизвестный билд — отказываемся угадывать)."""
        m = self.patched.search(data)
        if m:
            return ("patched", m.start() + self.offset)
        m = self.sig.search(data)
        if not m:
            raise LookupError("gate signature not found (unsupported version?)")
        if self.sig.search(data, m.end()):
            raise LookupError("gate signature is not unique — refusing to guess")
        return ("unpatched", m.start() + self.offset)


# x86-64 (Intel Mac / Windows): handleAuthResult проверяет AuthResult.hasValidAuth
# (байт +8): test rax,rax ; je ; cmp byte[rax+8],0 ; jne.
# Патч: заменяем compare на test rax,rax + nop → ZF=0 → jne всегда берёт eligible.
CLI_GATE = Gate(
    rb"\x48\x85\xc0\x0f\x84....\x80\x78\x08\x00\x0f\x85....",
    rb"\x48\x85\xc0\x0f\x84....\x48\x85\xc0\x90\x0f\x85....",
    b"\x48\x85\xc0\x90",
    offset=9,
    desc="eligibility screen off",
)

# ARM64 (Apple Silicon): handleAuthResult проверяет поле ServerBackend+0x1c0
# (ineligibility-объект): ldr x3,[x0,#0x1c0] ; cbz x3,skip ; mov x0,x3 ; …
# Патч: заменяем ldr на mov x3,xzr → cbz всегда берёт skip → ineligible-экран не вызывается.
ARM64_CLI_GATE = Gate(
    rb"\x03\xe0\x40\xf9...\xb4\xe0\x03\x03\xaa\xe1\x03\x1f\xaa\xe2\x03\x1f\xaa",
    rb"\xe3\x03\x1f\xaa...\xb4\xe0\x03\x03\xaa\xe1\x03\x1f\xaa\xe2\x03\x1f\xaa",
    b"\xe3\x03\x1f\xaa",
    offset=0,
    desc="eligibility screen off (arm64)",
)


def _detect_arch(path):
    """Возвращает 'arm64', 'x86_64' или 'unknown' по заголовку бинаря."""
    try:
        with open(path, "rb") as f:
            hdr = f.read(64)
        if len(hdr) < 8:
            return "unknown"
        magic = hdr[:4]
        if magic == b"\xcf\xfa\xed\xfe":          # Mach-O 64-bit LE
            cputype = struct.unpack_from("<I", hdr, 4)[0]
            if cputype == 0x0100000C:
                return "arm64"
            if cputype == 0x01000007:
                return "x86_64"
        elif hdr[:2] == b"MZ":                    # Windows PE → всегда x86_64
            return "x86_64"
        elif magic == b"\x7fELF":                 # Linux ELF
            if len(hdr) >= 20:
                endian = hdr[5]
                if endian == 1:                   # Little Endian
                    machine = struct.unpack_from("<H", hdr, 18)[0]
                elif endian == 2:                 # Big Endian
                    machine = struct.unpack_from(">H", hdr, 18)[0]
                else:
                    return "unknown"

                if machine == 62:                 # EM_X86_64
                    return "x86_64"
                elif machine == 183:              # EM_AARCH64 (ARM64)
                    return "arm64"
    except OSError:
        pass
    return "unknown"


def _gate_for(path):
    """Выбирает Gate под архитектуру бинаря."""
    return ARM64_CLI_GATE if _detect_arch(path) == "arm64" else CLI_GATE


@contextlib.contextmanager
def _mapped(path):
    """Read-only, zero-copy bytes-view (работает с .find(), слайсами, re) для
    сканирования сигнатур — не грузит мульти-МБ бинарь в ОЗУ целиком."""
    with open(path, "rb") as f:
        if os.fstat(f.fileno()).st_size == 0:
            yield b""
            return
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            yield mm
        finally:
            mm.close()


def is_locked(path):
    """True, если файл занят (приложение запущено)."""
    try:
        with open(path, "r+b"):
            return False
    except OSError:
        return True


def get_status(path):
    """('patched'|'unpatched'|'unknown', None) — без исключений наружу."""
    if not path or not os.path.isfile(path):
        return ("unknown", None)
    try:
        gate = _gate_for(path)
        with _mapped(path) as d:
            try:
                return (gate.find(d)[0], None)
            except LookupError:
                return ("unknown", None)
    except OSError:
        return ("unknown", None)


def is_already_patched(path):
    """Совместимый с IDE/asar интерфейс: True только если патч уже применён."""
    return get_status(path)[0] == "patched"


def _make_backup(path):
    """Снимок чистого файла как <path>.agybak.
    Вызывается только когда файл unpatched — живые байты это pristine-оригинал.
    Бэкап, не совпадающий с файлом, устарел (приложение автообновилось) —
    обновляем его, а не храним."""
    bak = path + BAK_EXT
    if os.path.exists(bak):
        if filecmp.cmp(path, bak, shallow=False):
            return  # бэкап уже соответствует этому билду
        info(f"Backup is stale (app updated) — refreshing {os.path.basename(path)}{BAK_EXT}")
    else:
        info(f"Creating backup -> {os.path.basename(path)}{BAK_EXT}")
    shutil.copy2(path, bak)
    fix_posix_permissions(bak)
    ok(f"Backup: {os.path.basename(bak)} ({format_bytes(file_size(bak))})")


def _copy_to_user_bin(path):
    from patcher.utils.file import get_posix_invoking_user_home
    user_home = get_posix_invoking_user_home()
    dest_dir = os.path.join(user_home, ".local", "bin") if user_home else os.path.expanduser("~/.local/bin")
    dest_path = os.path.join(dest_dir, "agy")
    if os.path.abspath(path) == os.path.abspath(dest_path):
        return
    info(f"Storing file in user system folder -> {dest_path}")
    try:
        os.makedirs(dest_dir, exist_ok=True)
        if os.path.exists(dest_path):
            try:
                os.remove(dest_path)
            except Exception:
                pass
        shutil.copy2(path, dest_path)
        os.chmod(dest_path, 0o755)
        ok(f"File successfully copied to: {dest_path}")
    except Exception as e:
        warn(f"Could not copy file to {dest_path}: {e}")


def do_patch_agy(path):
    from patcher.cli import confirmed
    from patcher.utils.captcha import confirm_with_captcha

    if not os.path.isfile(path):
        err(f"Target is not a file: {path}")
        hint("Please select a valid agy/agy.exe binary.")
        return

    hash_before = file_hash(path)
    info(f"Target: {color(path, COLOR_CYAN)}")
    hint(f"Size: {color(format_bytes(file_size(path)), COLOR_CYAN)}")
    print()

    gate = _gate_for(path)
    write_success = False
    off = 0
    for attempt in range(2):
        if is_locked(path):
            if attempt == 0:
                warn("Binary is locked (Antigravity CLI is running).")
                if confirmed("Would you like to automatically close running agy processes and retry?"):
                    terminate_processes(["agy"])
                    import time
                    time.sleep(1.5)
                    continue
            err("File is locked — close Antigravity CLI first.")
            return

        # Сканируем в mmap, закрываем ДО записи (zero-copy scan)
        try:
            with _mapped(path) as d:
                try:
                    kind, off = gate.find(d)
                except LookupError as e:
                    err(f"{e}")
                    return
                if kind == "patched":
                    hint("agy already patched.")
                    if not confirm_with_captcha("Apply patch anyway?"):
                        return
        except OSError as e:
            err(f"Read error: {e}")
            return

        _make_backup(path)

        try:
            with open(path, "r+b") as f:
                f.seek(off)
                f.write(gate.fix)
                f.flush()
                os.fsync(f.fileno())
            write_success = True
            break
        except PermissionError as e:
            if attempt == 0:
                warn(f"Permission denied (file locked): {e}")
                if confirmed("Would you like to automatically close running agy processes and retry?"):
                    terminate_processes(["agy"])
                    import time
                    time.sleep(1.5)
                    continue
            err(f"Write error (Permission denied): {e}")
            return
        except Exception as e:
            err(f"Write error: {e}")
            return

    if not write_success:
        return

    hash_after = file_hash(path)
    resign_macos_bundle(path)
    resign_macos_binary(path)
    if os.name == "posix":
        _copy_to_user_bin(path)
    print()
    step("Patch agy binary", True, gate.desc)
    print()
    panel_rows = [
        ("Target", os.path.basename(path)),
        ("Gate", f"{gate.desc} @ 0x{off:x}"),
    ]
    if hash_before and hash_after:
        panel_rows.append(("Before", f"{hash_before[:8]}...{hash_before[56:]}"))
        panel_rows.append(("After", f"{hash_after[:8]}...{hash_after[56:]}"))
    print_panel("PATCH COMPLETE", panel_rows)
    hint("Restart Antigravity CLI for the change to take effect.")


def do_restore_agy(path):
    from patcher.cli import confirmed

    if not os.path.isfile(path):
        err(f"Target is not a file: {path}")
        return

    bak = path + BAK_EXT
    if not os.path.exists(bak):
        warn(f"No backup for {os.path.basename(path)} (nothing to restore).")
        return

    status, _ = get_status(path)
    if status != "patched":
        warn("agy is not patched — skipping restore (backup may be a different build).")
        if not confirmed("Restore from backup anyway?"):
            hint("Restore cancelled.")
            return

    if is_locked(path):
        err("Binary is locked — close Antigravity CLI first.")
        return

    if not confirmed("Restore agy from backup?"):
        hint("Restore cancelled.")
        return

    hash_before = file_hash(path)
    try:
        shutil.copy2(bak, path)
        fix_posix_permissions(path)
    except Exception as e:
        err(f"Restore error: {e}")
        return

    hash_after = file_hash(path)
    resign_macos_bundle(path)
    resign_macos_binary(path)
    if os.name == "posix":
        _copy_to_user_bin(path)
    print()
    panel_rows = [("Target", os.path.basename(path))]
    if hash_before and hash_after and hash_before != hash_after:
        panel_rows.append(("Before", f"{hash_before[:8]}...{hash_before[56:]}"))
        panel_rows.append(("After", f"{hash_after[:8]}...{hash_after[56:]}"))
    print_panel("RESTORE COMPLETE", panel_rows)
