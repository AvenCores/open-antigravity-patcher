<div align="center">
    <a href="https://www.youtube.com/@avencores/" target="_blank">
      <img src="https://github.com/user-attachments/assets/338bcd74-e3c3-4700-87ab-7985058bd17e" alt="YouTube" height="40">
    </a>
    <a href="https://t.me/avencoresyt" target="_blank">
      <img src="https://github.com/user-attachments/assets/939f8beb-a49a-48cf-89b9-d610ee5c4b26" alt="Telegram" height="40">
    </a>
    <a href="https://vk.ru/avencoresreuploads" target="_blank">
      <img src="https://github.com/user-attachments/assets/dc109dda-9045-4a06-95a5-3399f0e21dc4" alt="VK" height="40">
    </a>
    <a href="https://dzen.ru/avencores" target="_blank">
      <img src="https://github.com/user-attachments/assets/bd55f5cf-963c-4eb8-9029-7b80c8c11411" alt="Dzen" height="40">
    </a>
</div>

# 🔑 Open AG Patcher
[![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)](https://github.com/AvenCores/open-antigravity-patcher)
[![GPL-3.0 License](https://img.shields.io/badge/License-GPL--3.0-blue?style=for-the-badge)](./LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/AvenCores/open-antigravity-patcher?style=for-the-badge)](https://github.com/AvenCores/open-antigravity-patcher/stargazers)
![GitHub forks](https://img.shields.io/github/forks/AvenCores/open-antigravity-patcher?style=for-the-badge)
[![GitHub pull requests](https://img.shields.io/github/issues-pr/AvenCores/open-antigravity-patcher?style=for-the-badge)](https://github.com/AvenCores/open-antigravity-patcher/pulls)
[![GitHub issues](https://img.shields.io/github/issues/AvenCores/open-antigravity-patcher?style=for-the-badge)](https://github.com/AvenCores/open-antigravity-patcher/issues)

Опенсорс патчер для Antigravity: снимает регионные ограничения без VPN и смены региона аккаунта Google. Опенсурс аналог утилиты [Antigravity в России без VPN и смены региона аккаунта Google](https://github.com/confeden/Antigravity).

![maxresdefault](https://github.com/user-attachments/assets/025e2354-2a66-414e-b4dc-3db8910b0d85)

# 🎦 Видео гайд по установке и решению проблем

![maxresdefault](https://i127.fastpic.org/big/2026/0314/98/07b762c3a6a29ff220a66da40e16e698.png?md5=BNMT3ALCT2xXPA_7iuzW2g&expires=1773496800)

<div align="center">

[**Смотреть на YouTube**](https://youtu.be/hMOeXUQHy4I)

[**Смотреть на Dzen**](https://dzen.ru/video/watch/69b43e995330f8608c7b39e3)

[**Смотреть в VK Video**](https://vkvideo.ru/video-234234162_456239068)

[**Смотреть в Telegram**](https://t.me/avencoreschat/456321)

</div>

## ⚠️ Ошибка HTTP 500 Internal Server Error
Если при запросе в Antigravity появляется ошибка HTTP 500 Internal Server Error, то ничего не поделать, меняйте аккаунт (желательно на регион, где Antigravity официально работает или куплена платная подписка), платная утилита также её не решала.

**Пример ошибки**
```
Trajectory ID: 2669b09c-1d11-4620-9bfa-6ad1f0e26a88
Error: HTTP 500 Internal Server Error
Sherlog: 
TraceID: 0xd9ada64bcca3260c
Headers: {"Alt-Svc":["h3=\":443\"; ma=2592000,h3-29=\":443\"; ma=2592000"],"Content-Length":["109"],"Content-Type":["text/event-stream"],"Date":["Sat, 14 Mar 2026 13:51:24 GMT"],"Server":["ESF"],"Server-Timing":["gfet4t7; dur=423"],"Vary":["Origin","X-Origin","Referer"],"X-Cloudaicompanion-Trace-Id":["d9ada64bcca3260c"],"X-Content-Type-Options":["nosniff"],"X-Frame-Options":["SAMEORIGIN"],"X-Xss-Protection":["0"]}

{
  "error": {
    "code": 500,
    "message": "Internal error encountered.",
    "status": "INTERNAL"
  }
}
```

## 🌟 Возможности
- Автоматический поиск установленного Antigravity в стандартных путях и реестре Windows.
- Поддержка Linux: поиск по `/usr/share/antigravity`, определение версии через `dpkg`, `rpm` и `package.json`.
- Поддержка macOS: поиск `.app`-бандла в `/Applications` и `~/Applications`, ad-hoc переподпись после изменения `main.js`.
- Создание резервной копии `main.js.bak` перед изменениями.
- Применение и откат патча через простое меню.
- Поддержка путей `resources/app/out/main.js` и `resources/app/main.js`.
- Цветной вывод и попытка автоматического повышения прав (UAC на Windows, предложение `sudo` на Linux).
- Проверка минимальной версии Antigravity (>= `1.22.2`) перед применением патча.
- Определение версии Antigravity через реестр Windows, пакетный менеджер на Linux или `package.json` на macOS.
- Обнаружение уже применённого патча с предложением применить повторно.

## 🚀 Как использовать
1. Закройте Antigravity.
2. Запустите патчер от имени администратора (скрипт сам запросит повышение прав при необходимости).
3. В меню выберите нужное действие:

| Пункт меню | Описание |
|---|---|
| `1. Apply patch` | Применить патч к `main.js` |
| `2. Restore from backup` | Восстановить оригинальный файл из резервной копии |
| `3. Open GitHub repository` | Открыть страницу проекта в браузере |
| `0. Exit` | Выйти |

Запуск из исходников:
```bash
python main.py
```

Запуск с указанием пути:
```bash
# Windows
python main.py "C:\\Program Files\\Antigravity"
python main.py "C:\\Program Files\\Antigravity\\resources\\app\\out\\main.js"

# Linux
python main.py /usr/share/antigravity
python main.py /usr/share/antigravity/resources/app/out/main.js

# macOS
python3 main.py /Applications/Antigravity.app
python3 main.py ~/Applications/Antigravity.app
python3 main.py /Applications/Antigravity.app/Contents/Resources/app/out/main.js
```

Если `main.js` находится рядом со скриптом, путь указывать не нужно — он будет найден автоматически.

> **macOS:** если `Antigravity.app` лежит в `/Applications`, запись потребует `sudo` (скрипт сам предложит перезапуск). Для установки в `~/Applications` или пользовательскую директорию `sudo` не нужен. После успешного патча `.app` автоматически переподписывается ad-hoc подписью (`codesign --force --deep --sign -`) — без этого Electron с Hardened Runtime не запустится на macOS.

## ❓ Что именно меняется

Патчер вносит **4 правки** в `main.js`. Все изменения обратимы через резервную копию (`main.js.bak`).

### 1. `if(isGoogleInternal)` → `if(true)`
Заменяет проверку флага `isGoogleInternal` на безусловное `true`, снимая региональные/внутренние ограничения. Применяется ко всем вхождениям в файле (паттерн `if(this.<svc>.isGoogleInternal)`).

### 2. `if(X(),this.Y.isGoogleInternal)` → `if(X(),true)` (auth service)
В v1.22+ auth service проверяет `if(this.w.resetIsTierGCPTos(),this.t.isGoogleInternal)`. Этот патч заменяет проверку на `true`, обеспечивая обход проверки в сервисе авторизации.

### 3. `ideName` → `"antigravity-insiders"`
Заменяет `ideName:"antigravity"` на `ideName:"antigravity-insiders"` для корректной идентификации клиента.

### 4. Экран `ineligible` — обход (v1.22+)
Заменяет spread тернар `...s?{}:{errorType:"ineligible",reason:a,verificationUrl:i}` на `...s?{}:{}` — ошибка ineligible не отправляется, экран блокировки не показывается.

> **Примечание:** Патч `onboardUser injection` отключён начиная с v1.22+, так как в новых версиях Antigravity `onboardUser` уже вызывается нативно, и инъекция дублирует вызов, ломая поток авторизации.

## 🔍 Логика поиска файла

Патчер ищет `main.js` в следующем порядке:

1. Аргумент командной строки (путь к директории или напрямую к `main.js`).
2. Текущая директория (`./main.js`).
3. Автоматический поиск по стандартным путям:
   - **Windows:**
     - `%LOCALAPPDATA%\Programs\Antigravity`
     - `%PROGRAMFILES%\Antigravity`
     - `%PROGRAMFILES(X86)%\Antigravity`
   - **Linux:**
     - `/usr/share/antigravity`
   - **macOS:**
     - `/Applications/Antigravity.app/Contents/Resources/app`
     - `~/Applications/Antigravity.app/Contents/Resources/app`
4. Реестр Windows (ключ `{AA73B3E3-C6C8-45C8-B1DC-4AE56C751432}_is1` в `HKCU` и `HKLM`: `SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\`).

Внутри найденной директории проверяются пути:
- `resources/app/out/main.js`
- `resources/app/main.js`
- `out/main.js` (macOS)
- `main.js` (если путь указан напрямую)

На macOS скрипт также принимает путь к `.app`-бандлу напрямую — `Contents/Resources/app/out/main.js` ресолвится автоматически.

## 🔎 Определение версии Antigravity

| Платформа | Метод определения версии |
|---|---|
| **Windows** | Реестр: `DisplayVersion` из ключа `{AA73B3E3-...}_is1` |
| **Linux (deb)** | `dpkg-query -W antigravity` |
| **Linux (rpm)** | `rpm -q --queryformat %{VERSION} antigravity` |
| **Linux (portable/snap/flatpak)** | `package.json` рядом с `main.js` |
| **macOS** | `package.json` в `Antigravity.app/Contents/Resources/app/` |

Если версия не определена, патчер предлагает продолжить без проверки. Если версия ниже `1.22.2` — предупреждает и также предлагает выбор.

## 🔒 Проверка уже применённого патча

Перед патчингом скрипт проверяет, не был ли файл уже пропатчен, по двум признакам:
- отсутствие `if(this.X.isGoogleInternal)` (паттерн заменён на `if(true)`)
- наличие строки `"antigravity-insiders"`

Если оба признака найдены, выдаётся предупреждение с запросом подтверждения повторного применения.

## 🛡️ Повышение прав

- **Windows**: автоматический UAC-запрос через `ShellExecuteW` с параметром `runas`. Корректно обрабатывает пути с пробелами.
- **Linux**: если скрипт запущен не от root, предлагает перезапуститься через `sudo` (`os.execvp`). При отказе продолжает с предупреждением о возможных ошибках записи.
- **macOS**: использует ту же posix-ветку — `sudo` предлагается, если запущено без root. Для `~/Applications/Antigravity.app` на `sudo` можно ответить «n» (директория уже доступна на запись), для `/Applications/Antigravity.app` — согласиться.

## 🍎 Особенности macOS

### Переподпись `.app` после патча

Любое изменение файла внутри подписанного `.app`-бандла нарушает code signature. Electron-приложения с включённым Hardened Runtime (Antigravity — одно из них) после этого **не запускаются** на macOS — до того, как Gatekeeper вообще покажет пользователю диалог.

Чтобы `.app` продолжал работать, скрипт после `do_patch` и `do_restore` автоматически выполняет:

```bash
codesign --force --deep --sign - /path/to/Antigravity.app
xattr -dr com.apple.quarantine /path/to/Antigravity.app
```

`--sign -` — ad-hoc подпись (без Developer ID). Этого достаточно для локального запуска приложения. Notarization не требуется.

Требуется установленный `codesign` — он идёт в составе **Xcode Command Line Tools**:
```bash
xcode-select --install
```

### Если приложение не запускается после патча

1. Убедись, что `codesign` доступен: `which codesign`.
2. Проверь, что `.app` был переподписан: `codesign -dv /Applications/Antigravity.app 2>&1 | grep Authority` — должен быть `Signature=adhoc`.
3. Если macOS всё равно блокирует: `Системные настройки → Конфиденциальность и безопасность` — внизу будет кнопка «Открыть всё равно».

## ⚙️ Требования

- **Python** 3.x
- **Зависимости**: `packaging` (для сравнения версий)
- **ОС**:
  - **Windows** — полная поддержка автопоиска через реестр и UAC.
  - **Linux** — автопоиск в `/usr/share/antigravity`, определение версии через `dpkg`/`rpm`/`package.json`, sudo-повышение.
  - **macOS** — автопоиск в `/Applications/Antigravity.app` и `~/Applications/Antigravity.app`, определение версии через `package.json`, ad-hoc переподпись через `codesign` (Xcode Command Line Tools).
- **Минимальная версия Antigravity**: `1.22.2`

## 🛠️ Сборка
Требуется `pyinstaller`:
```bash
pip install -r requirements.txt
Windows: pyinstaller --onefile --uac-admin --icon=icon.ico --name="Open_AG_Patcher_Windows" main.py
Linux:   pyinstaller --onefile --icon=icon.ico --name="Open_AG_Patcher_Linux" main.py
macOS:   pyinstaller --onefile --name="Open_AG_Patcher_macOS" main.py
```

## Структура проекта
- `main.py` — основной патчер.
- `requirements.txt` — зависимости для сборки.
- `build.txt` — пример команды сборки.
- `icon.ico` — иконка для `exe`.

# 📜 Лицензия

Проект распространяется под лицензией GPL-3.0. Полный текст лицензии содержится в файле [`LICENSE`](LICENSE).

---
# 💰 Поддержать автора
+ **SBER**: `2202 2050 1464 4675`
