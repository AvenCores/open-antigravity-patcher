import os
import shutil
import json
import struct
import hashlib
import tempfile
import time

from patcher.constants import INTEGRITY_BLOCK_SIZE, PACK_EXCLUDE_PATHS
from patcher.utils.console import info, ok, warn, err
from patcher.utils.file import fix_posix_permissions


def align_to(value, alignment):
    remainder = value % alignment
    return value if remainder == 0 else value + (alignment - remainder)


def compute_integrity(file_path):
    full_hash = hashlib.sha256()
    block_hashes = []

    with open(file_path, 'rb') as f:
        while True:
            block = f.read(INTEGRITY_BLOCK_SIZE)
            if not block:
                break
            full_hash.update(block)
            block_hashes.append(hashlib.sha256(block).hexdigest())

    return {
        "algorithm": "SHA256",
        "hash": full_hash.hexdigest(),
        "blockSize": INTEGRITY_BLOCK_SIZE,
        "blocks": block_hashes,
    }


def find_unpacked_file(asar_path, current_path):
    resource_dir = os.path.dirname(asar_path)
    candidates = [
        asar_path + '.unpacked',
        os.path.join(resource_dir, 'app.asar.unpacked'),
        os.path.join(resource_dir, 'app1.asar.unpacked'),
    ]

    seen = set()
    for candidate_dir in candidates:
        if candidate_dir in seen:
            continue
        seen.add(candidate_dir)
        candidate_file = os.path.join(candidate_dir, current_path)
        if os.path.exists(candidate_file):
            return candidate_file

    return None


def _read_asar_header(f):
    """Read ASAR header from an open binary file positioned at the start.
    Returns (header_dict, payload_offset) or (None, None) on error.
    """
    try:
        _, header_size, _, json_size = struct.unpack('<IIII', f.read(16))
        json_bytes = f.read(json_size)
        header = json.loads(json_bytes.decode('utf-8'))
        payload_offset = 8 + header_size
        return header, payload_offset
    except Exception:
        return None, None


def extract_asar(asar_path, dest_dir):
    asar_path = os.path.abspath(asar_path)
    if not os.path.exists(asar_path):
        err(f"ASAR file not found at '{asar_path}'")
        return False

    info(f"Extracting '{os.path.basename(asar_path)}' to temp directory...")

    with open(asar_path, 'rb') as f:
        header, payload_offset = _read_asar_header(f)
        if header is None:
            err("Invalid ASAR file format (unable to read header structure or JSON).")
            return False

        def _copy_chunked(src_f, dst_path, size, chunk_size=1024*1024):
            remaining = size
            with open(dst_path, 'wb') as out_f:
                while remaining > 0:
                    chunk = src_f.read(min(chunk_size, remaining))
                    if not chunk:
                        break
                    out_f.write(chunk)
                    remaining -= len(chunk)

        def extract_entry(entry, current_path):
            if 'files' in entry:
                dir_path = os.path.join(dest_dir, current_path)
                os.makedirs(dir_path, exist_ok=True)
                for name, child in entry['files'].items():
                    extract_entry(child, os.path.join(current_path, name))
            else:
                file_path = os.path.join(dest_dir, current_path)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)

                if entry.get('unpacked'):
                    src_file = find_unpacked_file(asar_path, current_path)
                    if src_file:
                        shutil.copy2(src_file, file_path)
                    else:
                        warn(f"Unpacked file '{current_path}' not found in external directory.")
                else:
                    offset = int(entry['offset'])
                    size = entry['size']
                    f.seek(payload_offset + offset)
                    _copy_chunked(f, file_path, size)

        extract_entry(header, '')
        fix_posix_permissions(dest_dir)
        ok("Extraction completed successfully.")
        return True


def get_unpacked_paths(asar_path):
    unpacked_paths = set()
    if not os.path.exists(asar_path):
        return unpacked_paths

    try:
        with open(asar_path, 'rb') as f:
            header, _ = _read_asar_header(f)
            if header is None:
                return unpacked_paths

            def collect_unpacked(entry, current_path):
                if 'files' in entry:
                    for name, child in entry['files'].items():
                        collect_unpacked(child, os.path.join(current_path, name) if current_path else name)
                else:
                    if entry.get('unpacked'):
                        unpacked_paths.add(current_path.replace('\\', '/'))

            collect_unpacked(header, '')
    except Exception as e:
        warn(f"Could not read original ASAR header to check unpacked files: {e}")

    return unpacked_paths


def build_asar_tree(source_dir, unpacked_paths, payload_file, unpacked_dir):
    header = {"files": {}}
    current_offset = 0
    
    all_files = []
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, source_dir).replace('\\', '/')
            if rel_path in PACK_EXCLUDE_PATHS:
                continue
            all_files.append((rel_path, full_path))
            
    all_files.sort()
    
    for rel_path, full_path in all_files:
        size = os.path.getsize(full_path)
        is_unpacked = rel_path in unpacked_paths
        
        entry = {}
        entry["size"] = size
        entry["integrity"] = compute_integrity(full_path)
        if is_unpacked:
            entry["unpacked"] = True
            
            dest_unpacked_file = os.path.join(unpacked_dir, os.path.normpath(rel_path))
            os.makedirs(os.path.dirname(dest_unpacked_file), exist_ok=True)
            shutil.copy2(full_path, dest_unpacked_file)
        else:
            with open(full_path, 'rb') as f:
                data = f.read()
            payload_file.write(data)
            entry["offset"] = str(current_offset)
            current_offset += size
            
        parts = rel_path.split('/')
        current_node = header
        for part in parts[:-1]:
            if "files" not in current_node:
                current_node["files"] = {}
            if part not in current_node["files"]:
                current_node["files"][part] = {"files": {}}
            current_node = current_node["files"][part]
            
        if "files" not in current_node:
            current_node["files"] = {}
        current_node["files"][parts[-1]] = entry
        
    return header


def pack_asar(source_dir, asar_path, reference_asar_path=None):
    from patcher.utils.admin import terminate_processes
    from patcher.cli import confirmed

    info(f"Packing '{source_dir}' to '{os.path.basename(asar_path)}'...")
    
    unpacked_paths = get_unpacked_paths(reference_asar_path or asar_path)
    if unpacked_paths:
        info(f"Found {len(unpacked_paths)} unpacked files to preserve.")
        
    unpacked_dir = asar_path + '.unpacked'
    if os.path.exists(unpacked_dir):
        try:
            shutil.rmtree(unpacked_dir)
        except Exception as e:
            warn(f"Could not clear old unpacked directory: {e}")
    os.makedirs(unpacked_dir, exist_ok=True)
    
    temp_payload_fd, temp_payload_path = tempfile.mkstemp()
    try:
        with os.fdopen(temp_payload_fd, 'wb') as payload_file:
            header = build_asar_tree(source_dir, unpacked_paths, payload_file, unpacked_dir)
            
        json_bytes = json.dumps(header, separators=(',', ':')).encode('utf-8')
        json_size = len(json_bytes)
        json_payload_size = align_to(json_size + 4, 4)
        json_padding_size = json_payload_size - (json_size + 4)
        header_size = json_payload_size + 4
        pickle_header = 4
        
        temp_asar_fd, temp_asar_path = tempfile.mkstemp(dir=os.path.dirname(asar_path))
        try:
            with os.fdopen(temp_asar_fd, 'wb') as out_f:
                out_f.write(struct.pack('<I', pickle_header))
                out_f.write(struct.pack('<I', header_size))
                out_f.write(struct.pack('<I', json_payload_size))
                out_f.write(struct.pack('<I', json_size))
                out_f.write(json_bytes)
                if json_padding_size:
                    out_f.write(b'\0' * json_padding_size)
                
                with open(temp_payload_path, 'rb') as pay_f:
                    shutil.copyfileobj(pay_f, out_f)
            
            replace_success = False
            for attempt in range(2):
                try:
                    if os.path.exists(asar_path):
                        try:
                            os.remove(asar_path)
                        except PermissionError:
                            temp_old_path = asar_path + ".old"
                            if os.path.exists(temp_old_path):
                                try:
                                    os.remove(temp_old_path)
                                except Exception:
                                    pass
                            os.rename(asar_path, temp_old_path)
                            info(f"Locked file renamed to {os.path.basename(temp_old_path)}")

                    shutil.move(temp_asar_path, asar_path)
                    replace_success = True
                    break
                except PermissionError as e:
                    if attempt == 0:
                        warn(f"Permission denied (ASAR file locked): {e}")
                        if confirmed("Would you like to automatically close running Antigravity processes and retry?"):
                            terminate_processes(["Antigravity", "Antigravity IDE", "antigravity", "antigravity-ide"])
                            time.sleep(1.5)
                            continue
                    err(f"Could not overwrite or rename '{asar_path}' (locked by another process). {e}")
                    return False
                except Exception as e:
                    err(f"Error during ASAR replacement: {e}")
                    return False

            if not replace_success:
                return False
            ok("Packing completed successfully.")
            
            if os.path.exists(unpacked_dir) and not os.listdir(unpacked_dir):
                os.rmdir(unpacked_dir)
                
            return True
        finally:
            if os.path.exists(temp_asar_path):
                try:
                    os.remove(temp_asar_path)
                except Exception:
                    pass
    finally:
        if os.path.exists(temp_payload_path):
            try:
                os.remove(temp_payload_path)
            except Exception:
                pass
    return False
