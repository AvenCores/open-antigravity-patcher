import os
import stat
import tempfile


def fsync_dir(dirpath):
    """Синхронизировать директорию для надёжности переименования."""
    if os.name == "nt":
        return

    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY

    fd = os.open(dirpath, flags)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_replace_posix(path, data, meta_source=None):
    """
    Атомарная замена файла на POSIX-системах с безопасным временным файлом.

    Args:
        path: Целевой путь файла
        data: Байтовые данные для записи
        meta_source: Файл-источник для метаданных (владелец, права).
                     По умолчанию используется path.
    """
    path = os.path.abspath(path)

    # Запрещаем работу с символическими ссылками
    if os.path.islink(path):
        raise ValueError("Refusing to patch symlink")

    if not os.path.isfile(path):
        raise ValueError("Target is not a regular file")

    if meta_source is None:
        meta_source = path

    st = os.stat(meta_source)
    directory = os.path.dirname(path)

    # Безопасное создание временного файла с O_EXCL
    fd, tmp_path = tempfile.mkstemp(
        prefix=f".{os.path.basename(path)}.",
        suffix=".tmp",
        dir=directory,
    )

    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())

            # Сохраняем владельца ДО chmod (chown может сбросить setuid/setgid)
            try:
                os.fchown(f.fileno(), st.st_uid, st.st_gid)
            except OSError:
                # Может не хватить прав, это не всегда критично
                pass

            # Применяем права из оригинального файла
            os.fchmod(f.fileno(), stat.S_IMODE(st.st_mode))

        # Атомарная замена
        os.replace(tmp_path, path)

        # Синхронизируем директорию
        fsync_dir(directory)

        tmp_path = None  # Помечаем как успешно заменённый
    finally:
        # Удаляем временный файл при ошибке
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def validate_patch_params(bdata, patches):
    """
    Валидация параметров патчей перед применением.

    Args:
        bdata: bytearray с данными файла
        patches: список патчей в формате (offset, gate_object)

    Raises:
        ValueError: если параметры патча некорректны
    """
    for off, g in patches:
        # Проверка на отрицательное смещение
        if off < 0:
            raise ValueError(f"Negative offset: {off}")

        fix = g.fix

        # Если есть оригинальные байты для проверки
        if hasattr(g, "orig"):
            orig = g.orig

            # Патч не должен менять размер файла
            if len(fix) != len(orig):
                raise ValueError(
                    f"Patch changes file size: orig={len(orig)}, fix={len(fix)}"
                )

            # Проверка выхода за границы файла
            if off + len(orig) > len(bdata):
                raise ValueError(
                    f"Patch offset out of bounds: offset={off}, "
                    f"patch_size={len(orig)}, file_size={len(bdata)}"
                )

            # Проверка соответствия оригинальных байтов
            if bdata[off:off + len(orig)] != orig:
                raise ValueError(
                    f"Original bytes mismatch at offset {off}"
                )
        else:
            # Без оригинала хотя бы проверяем границы
            if off + len(fix) > len(bdata):
                raise ValueError(
                    f"Patch offset out of bounds: offset={off}, "
                    f"patch_size={len(fix)}, file_size={len(bdata)}"
                )


def apply_patches_to_data(bdata, patches):
    """
    Применение патчей к bytearray с валидацией.

    Args:
        bdata: bytearray с данными файла
        patches: список патчей в формате (offset, gate_object)

    Returns:
        bytearray: модифицированные данные
    """
    # Валидация всех патчей перед применением
    validate_patch_params(bdata, patches)

    # Применяем патчи
    for off, g in patches:
        if hasattr(g, "orig"):
            bdata[off:off + len(g.orig)] = g.fix
        else:
            bdata[off:off + len(g.fix)] = g.fix

    return bdata
