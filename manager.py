#!/usr/bin/env python3
"""
agy-manager — environment manager for Antigravity developer tools on Windows.
Provides location restriction bypass (patching eligibility gates)
and multi-account profile switching.

  * cli      Antigravity CLI         (agy.exe, Go binary)        -> suppress eligibility screen
  * manager  Antigravity (Manager)   (language_server.exe, Go)   -> force hasValidAuth=true
  * ide      Antigravity IDE         (VS Code fork, out/main.js)  -> force the internal-eligible branch
  * accounts Multi-account manager                               -> save & switch logins in-place

None of the patches unlock anything you can't already use — they only stop a local,
non-blocking eligibility screen from appearing. Every change is backed up
(<file>.agybak) and reversible with `restore`. Pure standard library.

Usage:
    python manager.py status                 # show all three (default)
    python manager.py patch                  # patch all detected apps
    python manager.py restore                # restore all from backup
    python manager.py patch ide manager      # only specific targets
    python manager.py --path-cli "C:\\...\\agy.exe" patch cli

    python manager.py accounts list          # saved logins (+ which is active)
    python manager.py accounts save work     # snapshot the current login as "work"
    python manager.py accounts use personal  # switch login in-place (no re-login)
"""
from __future__ import annotations
import argparse, base64, contextlib, filecmp, functools, glob, json, mmap, os, re, shutil, sqlite3, sys, time
from concurrent.futures import ThreadPoolExecutor
try:
    import winreg
except Exception:
    winreg = None

BAK = ".agybak"
TARGETS = ("cli", "manager", "ide")

# ----------------------------------------------------------------------- utils
def _say(tag, msg): print(f"  [{tag}] {msg}")
def ok(m):   _say("ok", m)
def info(m): _say("..", m)
def warn(m): _say("!!", m)

def _bin(name):
    """Platform executable name: 'language_server' on Linux/mac, 'language_server.exe'
    on Windows. The Go binaries are byte-identical across OSes (same source, same
    linux/windows-amd64 codegen), so only the on-disk name and search roots differ."""
    return name + (".exe" if os.name == "nt" else "")

def is_locked(path):
    try:
        with open(path, "r+b"):
            return False
    except OSError:
        return True

def make_backup(path):
    """Snapshot the clean file as <path>.agybak (callers reach here only when unpatched,
    so the live bytes are this build's pristine original). A backup that no longer
    matches the file is stale (app auto-updated) — refresh it instead of keeping it."""
    bak = path + BAK
    if os.path.exists(bak):
        if filecmp.cmp(path, bak, shallow=False):
            return                                  # backup already matches this build
        info(f"backup is stale (app updated) — refreshing {os.path.basename(path)}{BAK}")
    else:
        info(f"backup -> {os.path.basename(path)}{BAK}")
    shutil.copy2(path, bak)

def restore_file(path):
    b = path + BAK
    if not os.path.exists(b):
        warn(f"no backup for {os.path.basename(path)} (nothing to restore)")
        return False
    if is_locked(path):
        warn("file is locked — close the app first"); return False
    shutil.copy2(b, path)
    ok(f"restored {os.path.basename(path)}")
    return True

def rmtree_quiet(p):
    try:
        if os.path.isdir(p): shutil.rmtree(p, ignore_errors=True)
    except OSError:
        pass

@contextlib.contextmanager
def mapped(path):
    """Read-only, zero-copy bytes-like view (works with .find(), slicing, re) for
    marker/regex scans — avoids slurping multi-MB binaries into RAM."""
    with open(path, "rb") as f:
        if os.fstat(f.fileno()).st_size == 0:
            yield b""; return
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try: yield mm
        finally: mm.close()

# ----------------------------------------------------------------- discovery --
# Install-location-agnostic search: env roots + Programs/Program Files + registry
# InstallLocation + PATH (+ scoop). Apps are matched by a structural marker file,
# never a hard-coded path or version.
@functools.lru_cache(maxsize=1)
def _reg_install_dirs():
    dirs = []
    if not winreg: return dirs
    for hive, sub in ((winreg.HKEY_CURRENT_USER,  r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
                      (winreg.HKEY_LOCAL_MACHINE,  r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
                      (winreg.HKEY_LOCAL_MACHINE,  r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall")):
        try: key = winreg.OpenKey(hive, sub)
        except OSError: continue
        try: cnt = winreg.QueryInfoKey(key)[0]
        except OSError: cnt = 0
        for i in range(cnt):
            try:
                s = winreg.OpenKey(key, winreg.EnumKey(key, i))
                if "antigravity" in str(winreg.QueryValueEx(s, "DisplayName")[0]).lower():
                    loc = winreg.QueryValueEx(s, "InstallLocation")[0]
                    if loc: dirs.append(loc)
            except OSError:
                pass
    return dirs

@functools.lru_cache(maxsize=1)
def _roots():
    out = []
    for v in ("LOCALAPPDATA", "ProgramW6432", "PROGRAMFILES", "PROGRAMFILES(X86)", "ProgramData", "APPDATA"):
        p = os.environ.get(v)
        if not p: continue
        out += [p, os.path.join(p, "Programs")]
    up = os.environ.get("USERPROFILE", "")
    out += [os.path.join(up, "scoop", "apps"), os.path.join(os.environ.get("SCOOP", ""), "apps")]
    out += _reg_install_dirs()
    seen, roots = set(), []
    for r in out:
        if r and os.path.isdir(r):
            k = os.path.normcase(os.path.realpath(r))
            if k not in seen: seen.add(k); roots.append(r)
    return roots

def _dedup_newest(paths):
    seen, out = set(), []
    for p in sorted({p for p in paths if os.path.exists(p)},
                    key=lambda x: os.path.getmtime(x), reverse=True):
        k = os.path.normcase(os.path.realpath(p))
        if k not in seen: seen.add(k); out.append(p)
    return out

def find_marker(rel):
    """Find <root>/*antigravity*/<rel> (also one level deeper for scoop version/
    'current' dirs, and rel directly under a registry InstallLocation)."""
    hits = []
    for root in _roots():
        hits += glob.glob(os.path.join(root, "*ntigravity*", rel))
        hits += glob.glob(os.path.join(root, "*ntigravity*", "*", rel))
        direct = os.path.join(root, rel)
        if os.path.isfile(direct): hits.append(direct)
    return _dedup_newest(hits)

# Linux/mac discovery (Windows keeps _roots()/find_marker). Release tarballs unpack to
# <root>/*ntigravity*/ under a handful of standard prefixes; a launcher on PATH also
# contributes its own install dir. Apps are matched by the same structural marker
# rel-path as on Windows — never a hard-coded path or version.
def _posix_install_roots(*launchers):
    home = os.path.expanduser("~")
    roots = ["/opt", "/usr/share", "/usr/lib", "/usr/local/share", "/usr/local/lib",
             "/Applications",                              # macOS
             os.path.join(home, ".local", "share"),
             os.path.join(home, "Applications"),           # macOS (per-user)
             os.path.join(home, "Downloads"), home]
    for launcher in launchers:
        w = shutil.which(launcher)
        if w: roots.append(os.path.dirname(os.path.realpath(w)))
    return roots

def _posix_find(rel, *launchers):
    """POSIX analogue of find_marker: <root>/*ntigravity*/<rel> (and one level deeper),
    plus rel directly under a launcher's install dir."""
    hits = []
    for root in _posix_install_roots(*launchers):
        hits += glob.glob(os.path.join(root, "*ntigravity*", rel))
        hits += glob.glob(os.path.join(root, "*ntigravity*", "*", rel))
        direct = os.path.join(root, rel)
        if os.path.isfile(direct): hits.append(direct)
    return _dedup_newest(hits)

# ---------------------------------------------------- byte-signature gate -----
# CLI and Manager each fix ONE machine-code site found by a binary-unique signature,
# overwriting a few bytes in place. The machinery is shared; only the signatures,
# replacement bytes, write offset and labels differ, so each target declares a Gate.
# (Signatures use re.S so a `.` wildcard also matches a 0x0a displacement byte.)
class Gate:
    def __init__(self, sig, patched, fix, offset=0, desc=""):
        self.sig, self.patched = re.compile(sig, re.S), re.compile(patched, re.S)
        self.fix, self.offset, self.desc = fix, offset, desc
    def find(self, data):
        """('patched'|'unpatched', file offset to write at), or raise LookupError if
        the signature is missing or not unique (unknown build — refuse to guess)."""
        m = self.patched.search(data)
        if m: return ("patched", m.start()+self.offset)
        m = self.sig.search(data)
        if not m: raise LookupError("gate signature not found (unsupported version?)")
        if self.sig.search(data, m.end()): raise LookupError("gate signature is not unique — refusing to guess")
        return ("unpatched", m.start()+self.offset)

def gate_status(path, gate):
    with mapped(path) as d:
        try: return (gate.find(d)[0], None)
        except LookupError: return ("unknown", None)

def gate_patch(path, gate, app, fname):
    if is_locked(path):
        warn(f"{fname} is locked — close {app} first"); return False
    with mapped(path) as d:                       # zero-copy scan; mmap closed before we write
        try: kind, off = gate.find(d)
        except LookupError as e: warn(str(e)); return False
        if kind == "patched": ok(f"{app} already patched"); return True
    make_backup(path)
    with open(path, "r+b") as f:
        f.seek(off); f.write(gate.fix); f.flush(); os.fsync(f.fileno())
    ok(f"{app} patched ({gate.desc} @ file 0x{off:x})")
    return True

# ------------------------------------------------------------------- CLI ------
# agy.exe's handleAuthResult gates the cosmetic "Eligibility Check" on the server
# AuthResult's hasValidAuth (+8):  test rax,rax ; je ; cmp byte[rax+8],0 ; jne.
# rax is non-null here (the je above), so rewriting the compare to `test rax,rax`+nop
# keeps ZF=0 -> the jne always takes the eligible branch and the screen never renders.
CLI_GATE = Gate(rb"\x48\x85\xc0\x0f\x84....\x80\x78\x08\x00\x0f\x85....",
                rb"\x48\x85\xc0\x0f\x84....\x48\x85\xc0\x90\x0f\x85....",
                b"\x48\x85\xc0\x90", offset=9, desc="eligibility screen off")

def cli_default_paths():
    cands = []
    w = shutil.which("agy")
    if w:                                    # PATH hit (Windows which() appends PATHEXT's .EXE — normalize case)
        base, ext = os.path.splitext(w); cands.append(base + ext.lower())
    if os.name == "nt":
        for root in _roots():
            cands += glob.glob(os.path.join(root, "agy", "bin", "agy.exe"))
            cands += glob.glob(os.path.join(root, "agy", "*", "bin", "agy.exe"))   # scoop version dirs
            cands += glob.glob(os.path.join(root, "agy*", "agy.exe"))
    else:                                    # Linux/mac: install.sh drops a flat `agy` into ~/.local/bin
        home = os.path.expanduser("~")      # (default), or a custom --dir on PATH (caught by which() above)
        cands += [os.path.join(d, "agy") for d in
                  (os.path.join(home, ".local", "bin"), os.path.join(home, "bin"),
                   "/usr/local/bin", "/usr/bin", "/opt/homebrew/bin")]
    return _dedup_newest(cands)

# --------------------------------------------------- Manager (auth gate) ------
# language_server.exe (Go) decides the account's hasValidAuth (proto3 bool = byte at
# AuthResult+8) in authclient.(*PersonalAuthValidator).Validate — the single root
# authority. It calls ValidateAndOnboardAccount, then gates on the verdict:
#   cmp byte[rax+8],0 ; je skip ; mov r,[rsp+d] ; mov [rax+0x60],r   (attach the token)
# This is the AuthResult GetAuthStatus returns, so it governs EVERY path: cold restart /
# token-restore, AND the first interactive login ((*AuthClient).Login calls this
# validator and, on the no-error path, gates on this exact result object — so forcing the
# byte here also satisfies Login's later check; no separate Login patch needed).
# Fix: rewrite the compare to `mov byte[rax+8],1` and NOP the `je`, forcing the byte true
# AND always falling through to the token-attach branch. (Store offset moved +0x40 ->
# +0x60 vs older builds; displacements wildcarded via re.S to survive recompiles.)
# cmp byte[rax+8],0 ; je short  ->  mov byte[rax+8],1 ; nop*2
MANAGER_GATE = Gate(rb"\x80\x78\x08\x00\x74.\x48\x8b.\x24.\x48\x89.\x60",
                    rb"\xc6\x40\x08\x01\x90\x90\x48\x8b.\x24.\x48\x89.\x60",
                    b"\xc6\x40\x08\x01\x90\x90", desc="hasValidAuth=true")

def manager_default_bins():
    rel = os.path.join("resources", "bin", _bin("language_server"))
    if os.name == "nt":
        return find_marker(rel)                            # Windows: shared registry/env discovery
    return _posix_find(rel, "antigravity")                 # Linux/mac: launcher `antigravity`

# --------------------------------------------------------------------- IDE ----
IDE_RE = re.compile(rb"(resetIsTierGCPTos\(\),)this\.[A-Za-z_$0-9]+\.isGoogleInternal")
IDE_DONE = b"resetIsTierGCPTos(),true"

def ide_default_mains():
    rel = os.path.join("resources", "app", "out", "main.js")
    if os.name == "nt":
        return find_marker(rel)                            # Windows: shared registry/env discovery
    return _posix_find(rel, "antigravity-ide", "antigravity")   # Linux/mac: VS Code-fork launcher

def ide_status(path):
    with mapped(path) as d:
        gate = IDE_RE.search(d)
        if d.find(IDE_DONE) != -1 and not gate: return ("patched", None)
        return ("unpatched" if gate else "unknown", None)

def _ide_cache_dirs():
    """VS Code CachedData / Code Cache dirs to drop after patching main.js, so the IDE
    recompiles the patched bytes instead of replaying a stale compile cache. The user-data
    folder is the product nameLong ('Antigravity IDE') under each OS's app-data root."""
    home = os.path.expanduser("~")
    if os.name == "nt":
        bases = [os.path.expandvars(p) for p in
                 (r"%USERPROFILE%\scoop\persist\antigravity-ide\data\user-data",
                  r"%APPDATA%\Antigravity IDE")]
    elif sys.platform == "darwin":
        bases = [os.path.join(home, "Library", "Application Support", "Antigravity IDE")]
    else:                                                  # Linux (respect XDG_CONFIG_HOME)
        cfg = os.environ.get("XDG_CONFIG_HOME") or os.path.join(home, ".config")
        bases = [os.path.join(cfg, "Antigravity IDE")]
    dirs = []
    for base in bases:
        dirs += [os.path.join(base, "CachedData"),
                 os.path.join(base, "Code Cache", "js")]
    return dirs

def ide_patch(path):
    if is_locked(path): warn("main.js is locked — close Antigravity IDE first"); return False
    with open(path, "rb") as f: d = f.read()
    if IDE_DONE in d and not IDE_RE.search(d): ok("IDE already patched"); return True
    if not IDE_RE.search(d):
        warn("isGoogleInternal auth-gate pattern not found (unsupported version?)"); return False
    make_backup(path)
    with open(path, "wb") as f: f.write(IDE_RE.sub(rb"\1true", d))
    for c in _ide_cache_dirs(): rmtree_quiet(c)
    ok("IDE patched (isGoogleInternal -> true) + caches cleared")
    return True

# ============================================================== accounts =====
# Save / switch Antigravity logins WITHOUT the app's own logout (which revokes the
# refresh token server-side). The login lives in two independent stores:
#   * CLI + Manager : Windows Credential Manager generic cred "gemini:antigravity"
#                     (plaintext JSON holding a long-lived refresh_token)
#   * IDE           : the VS Code state.vscdb -> antigravityUnifiedStateSync.* keys
# Both are treated as OPAQUE blobs — snapshot and restore the bytes, never decrypt —
# so the refresh token survives, an expired access token is re-minted by the app, and
# the format stays version-robust. Saved profiles are themselves Credential Manager
# entries "agy-manager:account:<name>" (same OS at-rest protection, nothing on disk).
ACCT_PREFIX = "agy-manager:account:"
CRED_TARGET = "gemini:antigravity"                       # shared by CLI + Manager
CRED_USER   = "antigravity"
IDE_KEYS = ("antigravityUnifiedStateSync.oauthToken",    # the token itself, plus the
            "antigravityUnifiedStateSync.userStatus",    # identity/UI keys so the IDE
            "antigravityUnifiedStateSync.profileUrl",    # doesn't keep showing the
            "antigravityUnifiedStateSync.modelCredits")  # previous account after swap

def _advapi():
    """Bind advapi32 Cred* with correct 64-bit signatures (ctypes is stdlib)."""
    import ctypes
    from ctypes import wintypes
    class CREDENTIAL(ctypes.Structure):
        _fields_ = [("Flags", wintypes.DWORD), ("Type", wintypes.DWORD),
                    ("TargetName", wintypes.LPWSTR), ("Comment", wintypes.LPWSTR),
                    ("LastWritten", wintypes.FILETIME), ("CredentialBlobSize", wintypes.DWORD),
                    ("CredentialBlob", ctypes.POINTER(ctypes.c_char)), ("Persist", wintypes.DWORD),
                    ("AttributeCount", wintypes.DWORD), ("Attributes", ctypes.c_void_p),
                    ("TargetAlias", wintypes.LPWSTR), ("UserName", wintypes.LPWSTR)]
    a = ctypes.WinDLL("advapi32", use_last_error=True)
    PCRED = ctypes.POINTER(CREDENTIAL)
    a.CredReadW.argtypes  = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(PCRED)]
    a.CredWriteW.argtypes = [PCRED, wintypes.DWORD]
    a.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
    a.CredEnumerateW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD,
                                 ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(ctypes.POINTER(PCRED))]
    a.CredFree.argtypes = [ctypes.c_void_p]; a.CredFree.restype = None
    for fn in (a.CredReadW, a.CredWriteW, a.CredDeleteW, a.CredEnumerateW): fn.restype = wintypes.BOOL
    return ctypes, wintypes, a, CREDENTIAL, PCRED

def cred_read(target):
    """Raw CredentialBlob bytes for a GENERIC credential, or None if it doesn't exist."""
    ctypes, wintypes, a, CRED, PCRED = _advapi()
    p = PCRED()
    if not a.CredReadW(target, 1, 0, ctypes.byref(p)):   # 1 = CRED_TYPE_GENERIC
        return None
    try:    return ctypes.string_at(p.contents.CredentialBlob, p.contents.CredentialBlobSize)
    finally: a.CredFree(p)

def cred_write(target, blob, user):
    ctypes, wintypes, a, CRED, PCRED = _advapi()
    buf = ctypes.create_string_buffer(blob, len(blob))
    c = CRED(); c.Type = 1; c.TargetName = target; c.UserName = user
    c.CredentialBlobSize = len(blob)
    c.CredentialBlob = ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))
    c.Persist = 2                                          # CRED_PERSIST_LOCAL_MACHINE
    if not a.CredWriteW(ctypes.byref(c), 0):
        raise OSError(f"CredWrite failed (err {ctypes.get_last_error()})")

def cred_delete(target):
    ctypes, wintypes, a, CRED, PCRED = _advapi()
    return bool(a.CredDeleteW(target, 1, 0))

def cred_enum(prefix):
    ctypes, wintypes, a, CRED, PCRED = _advapi()
    n = wintypes.DWORD(); arr = ctypes.POINTER(PCRED)()
    if not a.CredEnumerateW(prefix + "*", 0, ctypes.byref(n), ctypes.byref(arr)):
        return []
    try:    return [arr[i].contents.TargetName for i in range(n.value)]
    finally: a.CredFree(arr)

def _ide_state_db():
    """Path to the IDE's active VS Code global-state DB (newest of the candidates)."""
    cands = []
    for base in (r"%USERPROFILE%\scoop\persist\antigravity-ide\data\user-data",
                 r"%APPDATA%\Antigravity IDE"):
        p = os.path.join(os.path.expandvars(base), "User", "globalStorage", "state.vscdb")
        if os.path.isfile(p): cands.append(p)
    return max(cands, key=os.path.getmtime) if cands else None

def ide_read():
    db = _ide_state_db()
    if not db: return {}
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        cur, out = con.cursor(), {}
        for k in IDE_KEYS:
            row = cur.execute("select value from ItemTable where key=?", (k,)).fetchone()
            if row is not None: out[k] = row[0]
        return out
    finally: con.close()

def ide_write(values):
    db = _ide_state_db()
    if not db: raise OSError("IDE state.vscdb not found")
    con = sqlite3.connect(db, timeout=2)
    try:
        cur = con.cursor()
        for k in IDE_KEYS:
            if k in values:
                cur.execute("insert into ItemTable(key,value) values(?,?) "
                            "on conflict(key) do update set value=excluded.value", (k, values[k]))
            else:
                cur.execute("delete from ItemTable where key=?", (k,))
        con.commit()
    finally: con.close()

# IDE values may be str or bytes; tag them so a bundle stays JSON-serializable.
def _enc(v): return {"b": base64.b64encode(v).decode()} if isinstance(v, (bytes, bytearray)) else {"s": v}
def _dec(d): return base64.b64decode(d["b"]) if "b" in d else d["s"]

def _snapshot(target_type):
    """Bundle the live login from the specified store into a JSON-safe dict."""
    if target_type == "cli-manager":
        cred = cred_read(CRED_TARGET)
        return {"version": 1, "type": "cli-manager", "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "cred": base64.b64encode(cred).decode() if cred else None}
    elif target_type == "ide":
        return {"version": 1, "type": "ide", "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "ide": {k: _enc(v) for k, v in ide_read().items()}}
    else:
        raise ValueError(f"unknown target type {target_type}")

def _apply(target_type, bundle):
    if target_type == "cli-manager":
        if bundle.get("cred"):
            cred_write(CRED_TARGET, base64.b64decode(bundle["cred"]), CRED_USER)
    elif target_type == "ide":
        ide = {k: _dec(v) for k, v in (bundle.get("ide") or {}).items()}
        if ide:
            if _ide_state_db():
                ide_write(ide)                           # lock-prone store first
            else:
                info("IDE database not found — skipping IDE token restoration")

def _ide_refresh_token(oauth_token_val):
    if not oauth_token_val:
        return None
    try:
        dec = base64.b64decode(oauth_token_val)
        match = re.search(rb'(CoQC[a-zA-Z0-9_-]+)', dec)
        if not match:
            return None
        b64_str = match.group(1)
        raw = base64.urlsafe_b64decode(b64_str + b'===')
        rt_match = re.search(rb'1//[a-zA-Z0-9_-]+', raw)
        return rt_match.group(0).decode("utf-8") if rt_match else None
    except Exception:
        return None

def _refresh_token(target_type, bundle):
    """The (stable) refresh_token in a bundle's CLI/Manager or IDE blob — used to match
    a live login to a saved profile."""
    if target_type == "cli-manager":
        b64 = bundle.get("cred")
        if not b64: return None
        try:    return json.loads(base64.b64decode(b64)).get("token", {}).get("refresh_token")
        except Exception: return None
    elif target_type == "ide":
        ide_data = bundle.get("ide") or {}
        token_val = ide_data.get("antigravityUnifiedStateSync.oauthToken")
        if not token_val: return None
        try:
            raw_val = _dec(token_val)
            return _ide_refresh_token(raw_val)
        except Exception:
            return None
    return None

# A bundle can exceed Credential Manager's ~2560-byte blob cap (the IDE userStatus key
# alone is ~8 KB), so each profile is stored as numbered chunks "...<name>/<i>" — the
# same way go-keyring shards large secrets.
_CHUNK = 2000

def _acct_prefix(target_type):
    return f"agy-manager:account:{target_type}:"

def profile_names(target_type):
    prefix = _acct_prefix(target_type)
    return sorted({t[len(prefix):].rsplit("/", 1)[0] for t in cred_enum(prefix)})

def profile_load(target_type, name):
    prefix = _acct_prefix(target_type)
    chunks, i = [], 0
    while True:
        raw = cred_read(f"{prefix}{name}/{i}")
        if raw is None: break
        chunks.append(raw); i += 1
    return json.loads(b"".join(chunks)) if chunks else None

def _profile_delete(target_type, name):
    prefix = _acct_prefix(target_type)
    i = n = 0
    while cred_delete(f"{prefix}{name}/{i}"): n += 1; i += 1
    return n

def profile_save(target_type, name, bundle):
    prefix = _acct_prefix(target_type)
    _profile_delete(target_type, name)                                # drop old chunks (new blob may be shorter)
    data = json.dumps(bundle).encode("utf-8")
    parts = [data[j:j+_CHUNK] for j in range(0, len(data), _CHUNK)] or [b""]
    for i, part in enumerate(parts):
        cred_write(f"{prefix}{name}/{i}", part, name)

def current_account(target_type):
    """Name of the saved profile matching the live login (by refresh_token), or None."""
    if target_type == "cli-manager":
        live = cred_read(CRED_TARGET)
        if not live: return None
        try:    rt = json.loads(live).get("token", {}).get("refresh_token")
        except Exception: return None
    elif target_type == "ide":
        db = _ide_state_db()
        if not db: return None
        live = ide_read().get("antigravityUnifiedStateSync.oauthToken")
        if not live: return None
        rt = _ide_refresh_token(live)
    else:
        return None

    if not rt: return None
    for name in profile_names(target_type):
        b = profile_load(target_type, name)
        if b and _refresh_token(target_type, b) == rt: return name
    return None

def _accounts_busy(target_type):
    """Token-holding apps currently running (their store is in use), so a switch would
    be ignored (token cached) or hit a locked store."""
    busy = []
    if target_type == "cli-manager":
        for t, label in (("manager", "Manager"), ("cli", "CLI")):
            p = resolve(t, {})
            if p and is_locked(p): busy.append(label)         # running exe image is write-locked
    elif target_type == "ide":
        db = _ide_state_db()
        if db:
            try:
                con = sqlite3.connect(db, timeout=0.3)
                try: con.execute("BEGIN IMMEDIATE"); con.rollback()
                finally: con.close()
            except sqlite3.OperationalError:
                busy.append("IDE")                            # state.vscdb is write-locked by the IDE
    return busy

def acct_list(target_type):
    names = profile_names(target_type)
    if not names:
        info(f"no saved accounts yet - use 'accounts {target_type} save <name>'"); return 0
    cur = current_account(target_type)
    for n in names:
        b = profile_load(target_type, n) or {}
        ok(f"{'* ' if n == cur else '  '}{n}   (saved {b.get('saved_at', '?')})")
    if cur is None:
        info("the current live login is not saved as any profile")
    return 0

def acct_current(target_type):
    cur = current_account(target_type)
    (ok if cur else info)(f"active account: {cur}" if cur else "current login is not saved as a profile")
    return 0

def acct_save(target_type, name):
    if "/" in name:
        warn("account name can't contain '/'"); return 1
    snap = _snapshot(target_type)
    if target_type == "cli-manager":
        if not snap["cred"]:
            warn("no active login found to save - log in to Antigravity first"); return 1
    elif target_type == "ide":
        if not _ide_state_db():
            warn("IDE database not found"); return 1
        if not any(snap["ide"].values()):
            warn("no active login found to save - log in to Antigravity IDE first"); return 1
    profile_save(target_type, name, snap)
    ok(f"saved current login as '{name}'"); return 0

def acct_use(target_type, name):
    target = profile_load(target_type, name)
    if target is None:
        warn(f"no saved account '{name}' (see 'accounts {target_type} list')"); return 1
    busy = _accounts_busy(target_type)
    if busy:
        warn(f"close {', '.join(busy)} first - the token is cached in memory while running"); return 1
    cur = current_account(target_type)
    if cur and cur != name:                               # sync-on-switch: capture any refresh-token
        try: profile_save(target_type, cur, _snapshot(target_type)); info(f"synced '{cur}' before switching")  # rotation since
        except Exception as e: warn(f"couldn't sync '{cur}': {e}")
    try:
        _apply(target_type, target)
    except sqlite3.OperationalError:
        warn("IDE database is locked - close Antigravity IDE and retry"); return 1
    ok(f"switched to '{name}' - (re)start Antigravity to use it"); return 0

def acct_rm(target_type, name):
    if _profile_delete(target_type, name):
        ok(f"removed account '{name}'"); return 0
    warn(f"no saved account '{name}'"); return 1

def acct_rename(target_type, old_name, new_name):
    if "/" in new_name:
        warn("new name can't contain '/'"); return 1
    target = profile_load(target_type, old_name)
    if target is None:
        warn(f"no saved account '{old_name}'"); return 1
    if profile_load(target_type, new_name) is not None:
        warn(f"account '{new_name}' already exists"); return 1
    profile_save(target_type, new_name, target)
    _profile_delete(target_type, old_name)
    ok(f"renamed account '{old_name}' to '{new_name}'"); return 0

def acct_logout(target_type):
    """Clear the live login LOCALLY (no server-side revoke) so the app shows its login
    screen and you can sign into another account to capture it — without invalidating
    the refresh token of the account you just saved. Use this instead of the app's own
    'log out' button when adding accounts."""
    busy = _accounts_busy(target_type)
    if busy:
        warn(f"close {', '.join(busy)} first - the token is cached in memory while running"); return 1
    cur = current_account(target_type)
    if cur:                                              # keep the saved copy current before clearing
        try: profile_save(target_type, cur, _snapshot(target_type)); info(f"synced '{cur}' first")
        except Exception as e: warn(f"couldn't sync '{cur}': {e}")
    
    if target_type == "cli-manager":
        cred_delete(CRED_TARGET)
        ok("live CLI/Manager login cleared locally (NOT revoked) - launch Antigravity, "
           "sign into the next account, then `accounts cli-manager save <name>`")
    elif target_type == "ide":
        try:
            if _ide_state_db():
                ide_write({})                            # delete all IDE token keys (lock-prone first)
        except sqlite3.OperationalError:
            warn("IDE database is locked - close Antigravity IDE and retry"); return 1
        ok("live IDE login cleared locally (NOT revoked) - launch Antigravity IDE, "
           "sign into the next account, then `accounts ide save <name>`")
    return 0

def run_accounts(argv):
    if os.name != "nt":
        warn("account management is Windows-only"); return 2
    if not argv:
        warn("usage: accounts <cli-manager|ide> <list|save|use|rename|current|logout|rm> [name1] [name2]"); return 1
    
    target_type = argv[0].lower()
    if target_type not in ("cli-manager", "ide"):
        warn(f"unknown account target '{target_type}' (choose: cli-manager | ide)")
        warn("usage: accounts <cli-manager|ide> <list|save|use|rename|current|logout|rm> [name1] [name2]"); return 1

    sub = (argv[1] if len(argv) > 1 else "list").lower()
    arg = argv[2] if len(argv) > 2 else None
    need = lambda: (warn(f"usage: accounts {target_type} {sub} <name>"), 1)[1]
    try:
        if sub in ("list", "ls"):          return acct_list(target_type)
        if sub in ("current", "who"):      return acct_current(target_type)
        if sub == "save":                  return acct_save(target_type, arg) if arg else need()
        if sub in ("use", "switch"):       return acct_use(target_type, arg)  if arg else need()
        if sub in ("rm", "remove", "del"): return acct_rm(target_type, arg)   if arg else need()
        if sub in ("rename", "mv"):
            arg2 = argv[3] if len(argv) > 3 else None
            need_rename = lambda: (warn(f"usage: accounts {target_type} {sub} <old_name> <new_name>"), 1)[1]
            return acct_rename(target_type, arg, arg2) if (arg and arg2) else need_rename()
        if sub in ("logout", "signout", "clear"): return acct_logout(target_type)
    except Exception as e:
        warn(f"accounts error: {e}"); return 1
    warn(f"unknown accounts subcommand '{sub}' (list | current | save | use | rename | logout | rm)"); return 2

# -------------------------------------------------------------------- driver --
SPEC = {
    "cli":     dict(name="Antigravity CLI",      find=cli_default_paths,     status=functools.partial(gate_status, gate=CLI_GATE),
                    patch=functools.partial(gate_patch, gate=CLI_GATE, app="CLI", fname=_bin("agy"))),
    "manager": dict(name="Antigravity Manager",  find=manager_default_bins,  status=functools.partial(gate_status, gate=MANAGER_GATE),
                    patch=functools.partial(gate_patch, gate=MANAGER_GATE, app="Manager", fname=_bin("language_server"))),
    "ide":     dict(name="Antigravity IDE",      find=ide_default_mains,     status=ide_status,     patch=ide_patch),
}

def resolve(target, override):
    if override: return override if os.path.exists(override) else None
    for p in SPEC[target]["find"]():
        if p and os.path.exists(p): return p
    return None

def run(action, targets, overrides):
    rc = 0
    for t in targets:
        spec = SPEC[t]; path = resolve(t, overrides.get(t))
        print(f"\n=== {spec['name']} ({t}) ===")
        if not path:
            warn("not found (use --path-%s to point at it)" % t); continue
        print(f"  target: {path}")
        try:
            if action == "status":
                st, _ = spec["status"](path); ok(f"status: {st}")
            elif action == "patch":
                if not spec["patch"](path): rc = 1
            elif action == "restore":
                if spec["status"](path)[0] == "patched":
                    restore_file(path)
                else:
                    warn("not patched — skipping restore (backup may be a different build)")
        except Exception as e:
            warn(f"error: {e}"); rc = 1
    return rc

def _status_of(t, path):
    """Status string for an already-resolved path (no filesystem/registry scan)."""
    if not path: return "not found"
    try:
        return SPEC[t]["status"](path)[0]
    except Exception:
        return "error"

def state(t, overrides=None):
    """(path|None, status_str) for one target."""
    path = resolve(t, (overrides or {}).get(t))
    return path, _status_of(t, path)

def scan(overrides):
    """Resolve paths + status for every target once, concurrently. Discovery and
    binary scans happen here (not per menu redraw); the registry/root probe is
    shared and the three targets run in parallel. Returns (paths, status) dicts."""
    _reg_install_dirs.cache_clear(); _roots.cache_clear()   # rediscover on (re)scan
    _roots()                                                # warm shared cache once
    def one(t):
        p = resolve(t, overrides.get(t))
        return t, p, _status_of(t, p)
    paths, status = {}, {}
    with ThreadPoolExecutor(max_workers=len(TARGETS)) as ex:
        for t, p, st in ex.map(one, TARGETS):
            paths[t], status[t] = p, st
    return paths, status

# --------------------------------------------------------------- interactive --
_STYLE = {"patched": "bold green", "unpatched": "yellow", "unknown": "magenta",
          "not found": "dim", "error": "bold red"}
_ICON  = {"patched": "✓", "unpatched": "●", "unknown": "?", "not found": "·", "error": "!"}

def _render(console, paths, status):
    from rich.table import Table
    from rich.panel import Panel
    cur_cli_manager = None
    cur_ide = None
    if os.name == "nt":
        try:
            cur_cli_manager = current_account("cli-manager")
            cur_ide = current_account("ide")
        except Exception:
            pass

    tbl = Table(box=None, expand=True, pad_edge=False)
    tbl.add_column("App", style="bold cyan", no_wrap=True)
    tbl.add_column("Status", no_wrap=True)
    tbl.add_column("Account", style="bold green", no_wrap=True)
    tbl.add_column("Location", style="dim", overflow="fold")
    
    for t in TARGETS:
        path, st = paths[t], status[t]
        acct = cur_cli_manager if t in ("cli", "manager") else cur_ide
        acct_str = acct if acct else "[white dim]—[/]"
        tbl.add_row(SPEC[t]["name"], f"[{_STYLE[st]}]{_ICON[st]} {st}[/]", acct_str, path or "—")
        
    console.print(Panel(tbl, title="[bold white]agy-manager[/] · Antigravity environment manager",
                        subtitle="[dim]↑↓ move · enter select · space toggle[/]", border_style="cyan"))

def _accounts_submenu(console, qs, target_type):
    import questionary
    from rich.table import Table
    from rich.panel import Panel
    label = "CLI + Manager" if target_type == "cli-manager" else "IDE"
    while True:
        console.clear()
        try:
            names, cur = profile_names(target_type), current_account(target_type)
        except Exception as e:
            console.print(f"[bold red]accounts error:[/] {e}")
            questionary.press_any_key_to_continue("Enter to continue…", style=qs).ask(); return
        tbl = Table(box=None, expand=True, pad_edge=False)
        tbl.add_column("Account", style="bold cyan"); tbl.add_column("", style="bold green", no_wrap=True)
        if names:
            for n in names: tbl.add_row(n, "● active" if n == cur else "")
        else:
            tbl.add_row("[dim]— none saved —[/]", "")
        console.print(Panel(tbl, title=f"[bold white]accounts ({label})[/] · switch login",
                            border_style="cyan"))
        if names and cur is None:
            console.print("[dim]the current login isn't saved as a profile yet[/]")
        act = questionary.select("Accounts:", style=qs, qmark="»", choices=[
            questionary.Choice("Save current login as…", "save"),
            questionary.Choice("Switch to…", "use"),
            questionary.Choice("Rename…", "rename"),
            questionary.Choice("Sign out locally", "logout"),
            questionary.Choice("Remove…", "rm"),
            questionary.Choice("Back", "back"),
        ]).ask()
        if act in (None, "back"): return
        console.rule(f"[bold cyan]{act}[/]")
        if act == "save":
            name = questionary.text("Name for this account:", style=qs).ask()
            if name and name.strip(): acct_save(target_type, name.strip())
        elif act == "logout":
            acct_logout(target_type)
        elif act == "use":
            if not names: console.print("[yellow]Nothing saved yet.[/]")
            else:
                choices = [questionary.Choice(n, n) for n in names] + [questionary.Choice("Back", "back")]
                name = questionary.select("Switch to:", style=qs, choices=choices).ask()
                if name and name != "back": acct_use(target_type, name)
        elif act == "rename":
            if not names: console.print("[yellow]Nothing saved yet.[/]")
            else:
                choices = [questionary.Choice(n, n) for n in names] + [questionary.Choice("Back", "back")]
                old_name = questionary.select("Select account to rename:", style=qs, choices=choices).ask()
                if old_name and old_name != "back":
                    new_name = questionary.text(f"New name for '{old_name}':", style=qs).ask()
                    if new_name and new_name.strip(): acct_rename(target_type, old_name, new_name.strip())
        elif act == "rm":
            if not names: console.print("[yellow]Nothing to remove.[/]")
            else:
                choices = [questionary.Choice(n, n) for n in names] + [questionary.Choice("Back", "back")]
                name = questionary.select("Remove:", style=qs, choices=choices).ask()
                if name and name != "back": acct_rm(target_type, name)
        questionary.press_any_key_to_continue("Enter to continue…", style=qs).ask()

def _accounts_menu(console, qs):
    import questionary
    if os.name != "nt":
        console.print("[yellow]Account management is Windows-only.[/]")
        questionary.press_any_key_to_continue("Enter to continue…", style=qs).ask(); return
    while True:
        console.clear()
        act = questionary.select("Manage accounts for:", style=qs, qmark="»", choices=[
            questionary.Choice("CLI + Manager", "cli-manager"),
            questionary.Choice("IDE", "ide"),
            questionary.Choice("Back", "back"),
        ]).ask()
        if act in (None, "back"): return
        _accounts_submenu(console, qs, act)

def interactive(overrides):
    import questionary
    from rich.console import Console
    console = Console()
    qs = questionary.Style([("qmark", "fg:#00afff bold"), ("pointer", "fg:#00afff bold"),
                            ("highlighted", "fg:#00afff bold"), ("selected", "fg:#00ff87 bold"),
                            ("answer", "fg:#00ff87 bold")])
    paths, status = scan(overrides)        # discover + status once; reused across redraws
    while True:
        console.clear()
        _render(console, paths, status)
        action = questionary.select("What do you want to do?", style=qs, qmark="»", choices=[
            questionary.Choice("Patch app(s)", "patch"),
            questionary.Choice("Restore app(s) from backup", "restore"),
            questionary.Choice("Manage accounts", "accounts"),
            questionary.Choice("Refresh status", "refresh"),
            questionary.Choice("Quit", "quit"),
        ]).ask()
        if action in (None, "quit"):
            console.print("[dim]bye 👋[/]"); return 0
        if action == "refresh":
            paths, status = scan(overrides)        # explicit rescan on user request
            continue
        if action == "accounts":
            _accounts_menu(console, qs); continue
        opts = []
        for t in TARGETS:
            path, st = paths[t], status[t]
            if not path:
                continue
            if action == "patch" and st == "patched": continue        # nothing to do
            if action == "restore" and st != "patched": continue   # only undo a real patch
            opts.append(questionary.Choice(f"{SPEC[t]['name']}  · {st}", value=t))
        if not opts:
            console.print(f"[yellow]Nothing to {action}.[/]")
            questionary.press_any_key_to_continue("Enter to continue…", style=qs).ask(); continue
        sel = questionary.checkbox(f"Select app(s) to {action}:", choices=opts, style=qs).ask()
        if not sel:
            continue
        console.rule(f"[bold cyan]{action}[/]")
        run(action, sel, overrides)
        for t in sel:                              # refresh only what we just touched
            status[t] = _status_of(t, paths[t])
        console.rule(style="dim")
        questionary.press_any_key_to_continue("Enter to return to the menu…", style=qs).ask()

def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Manage the Antigravity environment (patch location gates and manage profiles). "
                    "Run with no arguments for the interactive menu.")
    ap.add_argument("action", choices=("menu", "status", "patch", "restore", "accounts"), nargs="?",
                    help="menu (default) | status | patch | restore | "
                         "accounts <cli-manager|ide> <list|save|use|rename|current|logout|rm> [name1] [name2]")
    ap.add_argument("targets", nargs="*", default=[], metavar="{cli,manager,ide}",
                    help="which apps to act on (default: all)")
    for t in TARGETS: ap.add_argument(f"--path-{t}", help=f"explicit path for {t}")
    args = ap.parse_args(argv)

    if args.action == "accounts":                       # free-form subcommand; skip target validation
        return run_accounts(args.targets)

    bad = [t for t in args.targets if t not in TARGETS]
    if bad:
        ap.error(f"invalid target(s): {', '.join(bad)} (choose from: {', '.join(TARGETS)})")
    overrides = {t: getattr(args, f"path_{t}") for t in TARGETS}

    if args.action in (None, "menu"):
        try:
            import questionary, rich  # noqa: F401
            if not (sys.stdin.isatty() and sys.stdout.isatty()):
                raise RuntimeError("not a terminal")
            return interactive(overrides)
        except KeyboardInterrupt:
            print(); return 0
        except ImportError:
            warn("interactive menu needs:  pip install rich questionary")
            if args.action == "menu": return 2
        except Exception:
            if args.action == "menu":
                warn("interactive menu needs a real terminal"); return 2
        # plain fallback (no TTY / missing deps)
        print("agy-manager - status")
        return run("status", list(TARGETS), overrides)

    targets = args.targets if args.targets else list(TARGETS)
    print(f"agy-manager - {args.action}")
    return run(args.action, targets, overrides)

if __name__ == "__main__":
    raise SystemExit(main())
