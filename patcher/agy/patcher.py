import os
import re
import mmap
import shutil
import contextlib
import filecmp

from patcher.constants import (
    COLOR_GREEN,
    COLOR_YELLOW,
    COLOR_RED,
    COLOR_CYAN,
    COLOR_BOLD,
)
from patcher.utils.console import color
from patcher.utils.file import (
    file_hash,
    file_size,
    format_bytes,
    fix_posix_permissions,
    resign_macos_bundle,
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


# agy's handleAuthResult гейтит косметический "Eligibility Check" на серверном
# AuthResult.hasValidAuth (байт +8):  test rax,rax ; je ; cmp byte[rax+8],0 ; jne.
# Переписываем compare на `test rax,rax`+nop -> ZF=0 -> jne всегда берёт eligible.
CLI_GATE = Gate(
    rb"\x48\x85\xc0\x0f\x84....\x80\x78\x08\x00\x0f\x85....",
    rb"\x48\x85\xc0\x0f\x84....\x48\x85\xc0\x90\x0f\x85....",
    b"\x48\x85\xc0\x90",
    offset=9,
    desc="eligibility screen off",
)


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
        with _mapped(path) as d:
            try:
                return (CLI_GATE.find(d)[0], None)
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
        print(color(f"  [*] Backup is stale (app updated) — refreshing {os.path.basename(path)}{BAK_EXT}", COLOR_YELLOW))
    else:
        print(f"  [*] Creating backup -> {os.path.basename(path)}{BAK_EXT}")
    shutil.copy2(path, bak)
    fix_posix_permissions(bak)
    print(f"  [+] Backup: {os.path.basename(bak)} ({format_bytes(file_size(bak))})")


def do_patch_agy(path):
    from patcher.cli import confirmed

    if not os.path.isfile(path):
        print(color(f"  [!] Target is not a file: {path}", COLOR_RED))
        print(color("  [i] Please select a valid agy/agy.exe binary.", COLOR_YELLOW))
        return

    hash_before = file_hash(path)
    print(f"  [*] Target: {color(path, COLOR_CYAN)}")
    print(f"  [i] Size: {color(format_bytes(file_size(path)), COLOR_CYAN)}")
    print()

    write_success = False
    for attempt in range(2):
        if is_locked(path):
            if attempt == 0:
                print(color("  [!] Binary is locked (Antigravity CLI is running).", COLOR_YELLOW))
                if confirmed("Would you like to automatically close running agy processes and retry?"):
                    terminate_processes(["agy"])
                    import time
                    time.sleep(1.5)
                    continue
            print(color("  [!] File is locked — close Antigravity CLI first.", COLOR_RED))
            return

        # Сканируем в mmap, закрываем ДО записи (zero-copy scan)
        try:
            with _mapped(path) as d:
                try:
                    kind, off = CLI_GATE.find(d)
                except LookupError as e:
                    print(color(f"  [!] {e}", COLOR_RED))
                    return
                if kind == "patched":
                    print(color("  [i] agy already patched — nothing to do.", COLOR_YELLOW))
                    return
        except OSError as e:
            print(color(f"  [!] Read error: {e}", COLOR_RED))
            return

        _make_backup(path)

        try:
            with open(path, "r+b") as f:
                f.seek(off)
                f.write(CLI_GATE.fix)
                f.flush()
                os.fsync(f.fileno())
            write_success = True
        except PermissionError as e:
            if attempt == 0:
                print(color(f"  [!] Permission denied (file locked): {e}", COLOR_YELLOW))
                if confirmed("Would you like to automatically close running agy processes and retry?"):
                    terminate_processes(["agy"])
                    import time
                    time.sleep(1.5)
                    continue
            print(color(f"  [!] Write error (Permission denied): {e}", COLOR_RED))
            return
        except Exception as e:
            print(color(f"  [!] Write error: {e}", COLOR_RED))
            return

    if not write_success:
        return

    hash_after = file_hash(path)
    resign_macos_bundle(path)
    print()
    print(color("  [+] agy patched", COLOR_GREEN, COLOR_BOLD))
    print(f"      {CLI_GATE.desc} @ file 0x{off:x}")
    if hash_before and hash_after:
        print(f"  [+] Before: {hash_before[:8]}...{hash_before[56:]}")
        print(f"  [+] After:  {hash_after[:8]}...{hash_after[56:]}")
    print("  [i] Restart Antigravity CLI for the change to take effect.")


def do_restore_agy(path):
    from patcher.cli import confirmed

    if not os.path.isfile(path):
        print(color(f"  [!] Target is not a file: {path}", COLOR_RED))
        return

    bak = path + BAK_EXT
    if not os.path.exists(bak):
        print(color(f"  [!] No backup for {os.path.basename(path)} (nothing to restore).", COLOR_YELLOW))
        return

    status, _ = get_status(path)
    if status != "patched":
        print(color("  [!] agy is not patched — skipping restore (backup may be a different build).", COLOR_YELLOW))
        if not confirmed("Restore from backup anyway?"):
            print("  [i] Restore cancelled.")
            return

    if is_locked(path):
        print(color("  [!] Binary is locked — close Antigravity CLI first.", COLOR_RED))
        return

    if not confirmed("Restore agy from backup?"):
        print("  [i] Restore cancelled.")
        return

    hash_before = file_hash(path)
    try:
        shutil.copy2(bak, path)
        fix_posix_permissions(path)
    except Exception as e:
        print(color(f"  [!] Restore error: {e}", COLOR_RED))
        return

    hash_after = file_hash(path)
    resign_macos_bundle(path)
    print(color(f"  [+] Restored {os.path.basename(path)} from backup.", COLOR_GREEN))
    if hash_before and hash_after and hash_before != hash_after:
        print(f"  [+] Before: {hash_before[:8]}...{hash_before[56:]}")
        print(f"  [+] After:  {hash_after[:8]}...{hash_after[56:]}")
