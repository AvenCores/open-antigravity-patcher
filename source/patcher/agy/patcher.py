import os
import re
import mmap
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
from patcher.utils.update import handle_patch_failure
from patcher.utils.admin import terminate_processes
from patcher.utils.atomic import atomic_replace_posix, apply_patches_to_data

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
        """('patched'|'unpatched', [file offsets to write at]).
        LookupError, если сигнатура отсутствует (неизвестный билд).
        Несколько unpatched-вхождений допустимы — патчим все (Go может
        компилировать одну функцию в нескольких экземплярах)."""
        patched_offsets = [m.start() + self.offset for m in self.patched.finditer(data)]
        if patched_offsets:
            return ("patched", patched_offsets)
        unpatched_offsets = [m.start() + self.offset for m in self.sig.finditer(data)]
        if not unpatched_offsets:
            raise LookupError("gate signature not found (unsupported version?)")
        return ("unpatched", unpatched_offsets)


    def resolve(self, data):
        """(kind, [write-offsets], concrete-gate). The concrete gate carries the fix bytes
        and label to apply — so a MultiGate can hand back the arch-matching sub-gate."""
        kind, offsets = self.find(data)
        return kind, offsets, self


class MultiGate:
    """One logical gate whose machine code differs per CPU arch (the Manager's auth check
    compiles to distinct amd64 vs arm64 instructions), so it declares one Gate signature
    per arch. A given binary matches exactly one — different archs share no byte pattern —
    so there's no ambiguity; the first that finds a match wins."""

    def __init__(self, *gates, desc=""):
        self.gates = gates
        self.desc = desc

    def resolve(self, data):
        err = None
        for g in self.gates:
            try:
                return g.resolve(data)
            except LookupError as e:
                err = e
        raise err or LookupError("no gate signature matched")


# ---------------------------------------------------------------------------
# Gate 1: CLI eligibility screen (единственный гейт начальной проверки).
# x64:
#   test rax,rax ; je eligible ; cmp byte[rax+8],0 ; jne eligible ; call failure_builder
# Repeating the non-null test keeps ZF=0, so jne always selects eligible.
# Сигнатура ограничена 16-байтным ядром проверки: хвост (call + register spills)
# варьируется между сборками, поэтому в паттерн не включается.
CLI_GATE_X64 = Gate(
    rb"\x48\x85\xc0\x0f\x84....\x80\x78\x08\x00\x0f\x85....",
    rb"\x48\x85\xc0\x0f\x84....\x48\x85\xc0\x90\x0f\x85....",
    b"\x48\x85\xc0\x90",
    offset=9,
    desc="eligibility screen off (x64)",
)
# arm64:
#   cbnz x1,error ; cbz x0,eligible ; ldrb w1,[x0,#8] ; tbnz w1,#0,eligible
#   bl failure_builder
# Loading 1 instead makes tbnz always select eligible.
# Хвост (bl + stores) варьируется — в паттерн не включается.
CLI_GATE_ARM64 = Gate(
    rb"...\xb5...\xb4\x01\x20\x40\x39...\x37",
    rb"...\xb5...\xb4\x21\x00\x80\x52...\x37",
    b"\x21\x00\x80\x52",
    offset=8,
    desc="eligibility screen off (arm64)",
)

CLI_GATE = MultiGate(
    CLI_GATE_X64,
    CLI_GATE_ARM64,
    desc="eligibility screen off",
)

ALL_GATES = [
    (CLI_GATE, "eligibility screen off"),
]


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
    """
    True, если файл занят (приложение запущено).

    На POSIX замена файла через os.replace возможна даже при работающем процессе,
    поэтому блокирующим считаем только Windows.

    Примечание: на POSIX это не гарантирует, что файл не используется.
    Если нужна проверка на занятость, требуется более сложная логика
    (например, проверка процессов или файловые блокировки).
    """
    if os.name != "nt":
        return False

    try:
        with open(path, "r+b"):
            return False
    except OSError:
        return True


def get_status(path):
    """('patched'|'unpatched'|'unknown', None) — без исключений наружу.
    'patched' только если ВСЕ гейты применены."""
    if not path or not os.path.isfile(path):
        return ("unknown", None)
    try:
        with _mapped(path) as d:
            states = []
            for gate, _ in ALL_GATES:
                try:
                    state, off, g = gate.resolve(d)
                    states.append(state)
                except LookupError:
                    return ("unknown", None)
            if all(s == "patched" for s in states):
                return ("patched", None)
            if all(s == "unpatched" for s in states):
                return ("unpatched", None)
            return ("unpatched", None)  # частично применён — считаем unpatched
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

    if not path or not os.path.isfile(path):
        from patcher.cli import offer_download_and_block
        offer_download_and_block("Antigravity CLI")
        return

    hash_before = file_hash(path)
    info(f"Target: {color(path, COLOR_CYAN)}")
    hint(f"Size: {color(format_bytes(file_size(path)), COLOR_CYAN)}")
    print()

    write_success = False
    patches = []  # [(offset, gate), ...] — гейты, требующие записи
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
        patches = []
        try:
            with _mapped(path) as d:
                all_patched = True
                for gate_obj, gate_label in ALL_GATES:
                    try:
                        kind, offsets, g = gate_obj.resolve(d)
                    except LookupError as e:
                        err(f"{gate_label}: {e}")
                        handle_patch_failure()
                        return
                    if kind == "unpatched":
                        all_patched = False
                        for off in offsets:
                            patches.append((off, g))
                if all_patched:
                    hint("agy already patched (all gates).")
                    if not confirm_with_captcha("Apply patch anyway?"):
                        return
                    # re-patch: перезаписываем все гейты
                    patches = []
                    for gate_obj, _ in ALL_GATES:
                        kind, offsets, g = gate_obj.resolve(d)
                        for off in offsets:
                            patches.append((off, g))
        except OSError as e:
            err(f"Read error: {e}")
            return

        if not patches:
            return

        _make_backup(path)

        try:
            if os.name == "nt":
                # Windows: прямая запись с проверкой блокировки
                with open(path, "r+b") as f:
                    bdata = bytearray(f.read())
                    bdata = apply_patches_to_data(bdata, patches)
                    f.seek(0)
                    f.write(bdata)
                    f.flush()
                    os.fsync(f.fileno())
            else:
                # POSIX: атомарная замена через временный файл
                with open(path, "rb") as f:
                    bdata = bytearray(f.read())

                bdata = apply_patches_to_data(bdata, patches)

                # Атомарная замена с безопасным временным файлом
                atomic_replace_posix(path, bytes(bdata))

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
            handle_patch_failure()
            return
        except Exception as e:
            err(f"Write error: {e}")
            handle_patch_failure()
            return

    if not write_success:
        handle_patch_failure()
        return

    hash_after = file_hash(path)
    resign_macos_bundle(path)
    resign_macos_binary(path)
    if os.name == "posix":
        _copy_to_user_bin(path)
    print()
    step("Patch agy binary", True, f"{len(patches)} gate(s)")
    print()
    panel_rows = [
        ("Target", os.path.basename(path)),
    ]
    for off, g in patches:
        panel_rows.append(("Gate", f"{g.desc} @ 0x{off:x}"))
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
        if os.name == "nt":
            shutil.copy2(bak, path)
        else:
            # Читаем бэкап в память
            with open(bak, "rb") as f:
                bak_data = f.read()

            # Атомарная замена с метаданными из бэкапа
            atomic_replace_posix(path, bak_data, meta_source=bak)

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
