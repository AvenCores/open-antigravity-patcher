# Запуск готовой macOS-сборки

Этот fork публикует неофициальную macOS `universal2`-сборку для Intel и Apple Silicon.

История и авторство оригинального проекта сохранены через GitHub fork:

- оригинальный upstream: https://github.com/AvenCores/open-antigravity-patcher
- fork с macOS-релизом: https://github.com/coneldiablo/open-antigravity-patcher
- лицензия: GPL-3.0, без изменений

## Скачать

Откройте актуальный macOS-релиз:

https://github.com/coneldiablo/open-antigravity-patcher/releases/tag/v1.1.5-macos-universal2.2

Скачайте файл:

```text
Open_AG_Patcher_macOS-universal2.zip
```

## Запустить

Сначала полностью закройте Antigravity или Antigravity IDE.

Если приложение установлено в `/Applications`, патчер нужно запускать через `sudo`:

```bash
cd ~/Downloads
unzip Open_AG_Patcher_macOS-universal2.zip
chmod +x Open_AG_Patcher_macOS
sudo ./Open_AG_Patcher_macOS
```

Если macOS блокирует скачанный файл, снимите quarantine-атрибут:

```bash
xattr -dr com.apple.quarantine Open_AG_Patcher_macOS
```

После этого запустите снова:

```bash
sudo ./Open_AG_Patcher_macOS
```

## Что выбрать в меню

Используйте:

- `1. Apply Antigravity IDE patch` для `Antigravity IDE.app`
- `2. Apply Antigravity patch` для standalone `Antigravity.app`
- `3` или `4` для восстановления из backup

Для standalone `Antigravity.app` патчер обычно сам находит:

```text
/Applications/Antigravity.app
```

Если автопоиск не нашел приложение, выберите `7. Select custom path` и укажите один из путей:

```text
/Applications/Antigravity.app
/Applications/Antigravity IDE.app
```

## Проверить подпись

После патча `.app` автоматически переподписывается ad-hoc подписью. Проверить можно так:

```bash
codesign -dv /Applications/Antigravity.app 2>&1 | grep Signature
```

Ожидаемый результат:

```text
Signature=adhoc
```

## SHA256

```text
Open_AG_Patcher_macOS:
890a808e63ad9bdc7d4d8a44b84406eaa2ac865cee207591ee33bc730b12e66b

Open_AG_Patcher_macOS-universal2.zip:
072a5dbd8f8cc4caeed18d18da85fb31325579b7b41911801820234e185b078b
```
