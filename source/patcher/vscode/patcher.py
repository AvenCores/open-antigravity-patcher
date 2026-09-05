import os
import re
import shutil
import filecmp

from patcher.constants import COLOR_CYAN, COLOR_GREEN, COLOR_YELLOW
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
)
from patcher.utils.update import handle_patch_failure

BAK_EXT = ".vscodebak"

# ---------------------------------------------------------------------------
# PART 1 — маркер и оригинальная строка в extension.js
PART1_ANCHOR = "outputChannel.appendLine('[INSTALL] Checking Antigravity releases...');"

# Гибкий regex для PART 1: допускает разные кавычки и пробелы, но требует
# ПОЛНЫЙ вызов appendLine — вместе с закрывающей скобкой и опциональной ';'.
# Это гарантирует, что вставка попадёт ПОСЛЕ вызова, а не внутри него.
# Группа 1 — весь вызов целиком (точка вставки = m.end(1)).
PART1_ANCHOR_RE = re.compile(
    r"(outputChannel\s*\.\s*appendLine\s*\(\s*"            # outputChannel.appendLine(
    r"(['\"])\[INSTALL\]\s*Checking Antigravity releases[^'\"]*\2"  # 'строка-маркер'
    r"\s*\)\s*;?)"                                         # ) или );
)

# Инъекция: если бинарь уже скачан (targetPathOverride или ~/.gemini/bin),
# пропускаем проверку версии и повторное скачивание.
PART1_INJECT = (
    "{const __primary=options.targetPathOverride||getInstalledTargetPath();"
    "const __candidates=[__primary,"
    "(0,path_1.join)((0,path_1.dirname)(__primary),'antigravity'+((0,path_1.extname)(__primary)||''))];"
    "for(const __p of __candidates){if(__p&&await pathExists(__p)){"
    "outputChannel.appendLine('[INSTALL] Existing binary found at '+__p+'. "
    "Skipping version check and re-download.');return __p;}}}"
)

# PART 2 — строка проверки смены канала заменяется на константу false,
# чтобы расширение не считало канал изменённым и не перекачивало бинарь.
# Строгий regex: ровно три идентификатора (manifestFetched, lastInstalledUrl,
# releaseBaseUrl) в известном порядке — не цепляет посторонние выражения вида
# `const X = a && b !== c;`.
PART2_RE = re.compile(
    r"const\s+isChannelChanged\s*=\s*"
    r"manifestFetched\s*&&\s*lastInstalledUrl\s*!==\s*releaseBaseUrl\s*;"
)
PART2_DONE_RE = re.compile(r"const\s+isChannelChanged\s*=\s*false\s*;")
PART2_REPLACEMENT = "const isChannelChanged = false;"


def is_already_patched(content):
    """True, если обе части патча уже применены к extension.js."""
    return (PART1_INJECT in content) and ("const isChannelChanged = false;" in content)


def _apply_part1(content):
    """Возвращает (новый_контент, статус). Статус: 'applied'|'already'|'not-found'."""
    if PART1_INJECT in content:
        return content, "already"
    m = PART1_ANCHOR_RE.search(content)
    if m:
        insert_at = m.end(1)
        new_content = content[:insert_at] + PART1_INJECT + content[insert_at:]
        return new_content, "applied"
    # Фолбэк: точный поиск по маркеру (на случай экзотического форматирования)
    idx = content.find(PART1_ANCHOR)
    if idx == -1:
        return content, "not-found"
    insert_at = idx + len(PART1_ANCHOR)
    new_content = content[:insert_at] + PART1_INJECT + content[insert_at:]
    return new_content, "applied"


def _apply_part2(content):
    """Возвращает (новый_контент, статус)."""
    if PART2_DONE_RE.search(content):
        # Уже пропатчено; но если рядом остался оригинальный вариант — это другой
        # экземпляр, обрабатываем его ниже.
        new_content, n = PART2_RE.subn(PART2_REPLACEMENT, content)
        if n:
            return new_content, "applied"
        return content, "already"
    new_content, n = PART2_RE.subn(PART2_REPLACEMENT, content)
    if not n:
        return content, "not-found"
    return new_content, "applied"


def _make_backup(path):
    bak = path + BAK_EXT
    if os.path.exists(bak):
        if filecmp.cmp(path, bak, shallow=False):
            return
        info(f"Backup is stale (extension updated) — refreshing {os.path.basename(path)}{BAK_EXT}")
    else:
        info(f"Creating backup -> {os.path.basename(path)}{BAK_EXT}")
    shutil.copy2(path, bak)
    fix_posix_permissions(bak)
    ok(f"Backup: {os.path.basename(bak)} ({format_bytes(file_size(bak))})")


def do_patch_vscode(extension_js_path):
    """Патчит extension.js расширения google.google-antigravity (PART 1 + PART 2)."""
    from patcher.cli import confirmed

    if not extension_js_path or not os.path.isfile(extension_js_path):
        err("Antigravity VS Code extension.js not found.")
        hint("Install the 'Google Antigravity' extension in VS Code and run it once.")
        return False

    path = extension_js_path
    info(f"Target: {color(path, COLOR_CYAN)}")
    hint(f"Size: {color(format_bytes(file_size(path)), COLOR_CYAN)}")
    print()

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        err(f"Read error: {e}")
        handle_patch_failure()
        return False

    already = is_already_patched(content)

    new_content, s1 = _apply_part1(content)
    new_content, s2 = _apply_part2(new_content)

    statuses = [s1, s2]
    if all(s == "not-found" for s in statuses):
        err("Patch patterns not found in extension.js (unsupported extension version?).")
        handle_patch_failure()
        return False

    if all(s in ("already", "not-found") for s in statuses) and already:
        hint("extension.js already patched (both parts).")
        if not confirmed("Apply patch anyway?"):
            return True
        # re-patch: пересобираем из бэкапа, если он есть, иначе просто продолжаем
        bak = path + BAK_EXT
        if os.path.isfile(bak):
            try:
                with open(bak, "r", encoding="utf-8") as f:
                    new_content = f.read()
            except Exception as e:
                warn(f"Could not read backup for re-patch: {e}")
        new_content, s1 = _apply_part1(new_content)
        new_content, s2 = _apply_part2(new_content)

    changed = new_content != content
    if changed:
        try:
            _make_backup(path)
        except (PermissionError, OSError) as e:
            err(f"Backup error: {e}")
            hint("Close VS Code windows and retry. If installed as root, re-run with sudo.")
            handle_patch_failure()
            return False
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(new_content)
        except PermissionError as e:
            err(f"Write error (file locked?): {e}")
            hint("Close VS Code windows and retry.")
            handle_patch_failure()
            return False
        except Exception as e:
            err(f"Write error: {e}")
            handle_patch_failure()
            return False

    applied_parts = sum(1 for s in statuses if s in ("applied", "already"))
    print()
    step("Patch Antigravity VS Code extension", bool(changed or already),
         f"{applied_parts}/2 part(s)")
    print()
    panel_rows = [
        ("Target", os.path.basename(os.path.dirname(path))),
        ("File", os.path.basename(path)),
        ("Part 1", {"applied": "injected skip-download guard",
                    "already": "already patched",
                    "not-found": "pattern not found"}[s1]),
        ("Part 2", {"applied": "isChannelChanged -> false",
                    "already": "already patched",
                    "not-found": "pattern not found"}[s2]),
    ]
    hash_before = file_hash(path)
    panel_rows.append(("Hash", f"{hash_before[:8]}...{hash_before[56:]}" if hash_before else "n/a"))
    print_panel("PATCH COMPLETE" if (changed or already) else "PATCH SKIPPED", panel_rows)
    if changed:
        hint("Reload VS Code window (Developer: Reload Window) for the change to take effect.")
    return True


def do_restore_vscode(extension_js_path):
    """Восстанавливает extension.js из бэкапа .vscodebak, а также бинарь
    в ~/.gemini/bin (antigravity/agy) из его .agybak, если тот был пропатчен
    пунктом 'Antigravity VS Code Patch'."""
    from patcher.cli import confirmed

    if not extension_js_path or not os.path.isfile(extension_js_path):
        err("Antigravity VS Code extension.js not found.")
        return

    path = extension_js_path
    bak = path + BAK_EXT
    if not os.path.exists(bak):
        warn(f"No backup for {os.path.basename(path)} (nothing to restore).")
        return

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        err(f"Read error: {e}")
        return

    if not is_already_patched(content):
        warn("extension.js is not patched — skipping restore (backup may be a different build).")
        if not confirmed("Restore from backup anyway?"):
            hint("Restore cancelled.")
            return

    if not confirmed("Restore Antigravity VS Code extension.js from backup?"):
        hint("Restore cancelled.")
        return

    hash_before = file_hash(path)
    try:
        shutil.copy2(bak, path)
        fix_posix_permissions(path)
    except PermissionError as e:
        err(f"Restore error (file locked?): {e}")
        hint("Close VS Code windows and retry.")
        return
    except Exception as e:
        err(f"Restore error: {e}")
        return

    hash_after = file_hash(path)
    print()
    panel_rows = [("Target", os.path.basename(path))]
    if hash_before and hash_after and hash_before != hash_after:
        panel_rows.append(("Before", f"{hash_before[:8]}...{hash_before[56:]}"))
        panel_rows.append(("After", f"{hash_after[:8]}...{hash_after[56:]}"))
    print_panel("RESTORE COMPLETE", panel_rows)
    hint("Reload VS Code window (Developer: Reload Window) for the change to take effect.")

    # --- Восстановление бинаря в ~/.gemini/bin (пропатчен agy-патчером) ---
    from patcher.vscode.discovery import find_gemini_antigravity_binary
    from patcher.agy.patcher import do_restore_agy

    gemini_bin = find_gemini_antigravity_binary()
    if gemini_bin and os.path.exists(gemini_bin + ".agybak"):
        print()
        info(f"Found patched binary backup: {color(gemini_bin, COLOR_CYAN)}")
        do_restore_agy(gemini_bin)
    elif gemini_bin:
        hint(f"Binary {os.path.basename(gemini_bin)} in ~/.gemini/bin has no backup — nothing to restore.")
