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
<p align="center">
  <a href="https://github.com/AvenCores/open-antigravity-patcher"><img src="https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54" alt="Python"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/License-GPL--3.0-blue?style=for-the-badge" alt="GPL-3.0 License"></a>
  <a href="https://github.com/AvenCores/open-antigravity-patcher/releases/latest"><img src="https://img.shields.io/github/v/release/AvenCores/open-antigravity-patcher?style=for-the-badge" alt="Latest release"></a>
  <a href="https://github.com/AvenCores/open-antigravity-patcher/stargazers"><img src="https://img.shields.io/github/stars/AvenCores/open-antigravity-patcher?style=for-the-badge" alt="GitHub stars"></a>
  <img src="https://img.shields.io/github/forks/AvenCores/open-antigravity-patcher?style=for-the-badge" alt="GitHub forks">
  <a href="https://github.com/AvenCores/open-antigravity-patcher/watchers">
  <img src="https://img.shields.io/github/watchers/AvenCores/open-antigravity-patcher?style=for-the-badge" alt="GitHub Watchers"></a>
  <a href="https://github.com/AvenCores/open-antigravity-patcher/releases"><img src="https://img.shields.io/github/downloads/AvenCores/open-antigravity-patcher/total?style=for-the-badge" alt="Downloads"></a>
  <a href="https://github.com/AvenCores/open-antigravity-patcher/pulls"><img src="https://img.shields.io/github/issues-pr/AvenCores/open-antigravity-patcher?style=for-the-badge" alt="GitHub pull requests"></a>
  <a href="https://github.com/AvenCores/open-antigravity-patcher/issues"><img src="https://img.shields.io/github/issues/AvenCores/open-antigravity-patcher?style=for-the-badge" alt="GitHub issues"></a>
</p>

Опенсорс патчер для Antigravity 2.0, Antigravity IDE и Antigravity CLI: снимает регионные ограничения без VPN и смены региона аккаунта Google. Опенсурс аналог утилиты [Antigravity IDE в России без VPN и смены региона аккаунта Google](https://github.com/confeden/Antigravity).

![maxresdefault](https://i.ibb.co/DPWgQPVQ/chrome-9-Uppenlpg7.png)

# 🎦 Видео гайд по установке и решению проблем

![maxresdefault](https://i127.fastpic.org/big/2026/0314/98/07b762c3a6a29ff220a66da40e16e698.png?md5=BNMT3ALCT2xXPA_7iuzW2g&expires=1773496800)

<div align="center">

[**Смотреть на YouTube**](https://youtu.be/hMOeXUQHy4I)

[**Смотреть на Dzen**](https://dzen.ru/video/watch/69b43e995330f8608c7b39e3)

[**Смотреть в VK Video**](https://vkvideo.ru/video-234234162_456239068)

[**Смотреть в Telegram**](https://t.me/avencoreschat/456321)

</div>

## ⚠️ Ошибка HTTP 500 Internal Server Error
Если при запросе в Antigravity IDE появляется ошибка HTTP 500 Internal Server Error, то ничего не поделать, меняйте аккаунт (желательно на регион, где Antigravity IDE официально работает или куплена платная подписка), платная утилита также её не решала.

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

## ⚠️ Ошибка HTTP 400 Bad Request
Если вы получаете ошибку `HTTP 400 Bad Request` с сообщением `User location is not supported for the API use`, это означает, что Google определил ваше местоположение как неподдерживаемое.

**Важно:** использование VPN, прокси или других способов обхода ограничений может детектироваться Google и приводить к этой ошибке. Google активно борется с методами обхода, и если ваш IP-адрес или другие параметры сессии вызывают подозрение, доступ может быть заблокирован.

**Решение:**
1. Примените патч (**PATCH → `1`: Antigravity IDE patch**). Патчер настроит корректный обход `isGoogleInternal` на уровне кода.
2. Если патч уже применен, попробуйте сменить аккаунт Google или использовать другой VPN.
3. Попробуйте использовать **[Xbox DNS](https://xbox-dns.ru/)**, **[dns.malw.link](https://info.dns.malw.link/)**, **[GeoHide](https://dns.geohide.ru:8443/)** (специальные DNS-серверы для обхода ограничений на ПК или роутере).

**Пример ошибки:**
```json
{
  "error": {
    "code": 400,
    "message": "User location is not supported for the API use.",
    "status": "FAILED_PRECONDITION"
  }
}
```

## ⚠️ Ошибка лицензии Antigravity CLI (#3501)
Если в Antigravity CLI (`agy`) появляется ошибка `You do not have a valid license of this product`, это не проблема локального патча и не экран `Eligibility Check`.

Эта ошибка связана с API Google и состоянием аккаунта пользователя: лицензией, доступом или проверкой прав на стороне Google. Патчер меняет только локальные файлы Antigravity/Antigravity CLI и не может выдать аккаунту лицензию или изменить ответ Google API, поэтому с этой ошибкой он не поможет.

**Пример ошибки:**
```text
⚠ You do not have a valid license of this product. Please contact your administrator to request a license. If you are
not an enterprise user and believe you are receiving this message as an error, please try using the latest version and
logging in again. (#3501)
Error ID: b2c1d9edcaac4fd5ac5766de06c2253b
Trajectory ID: d3ee4302-4213-40f9-9ac5-42e83e38a5ce
```

## 📚 Дополнительная информация по ошибкам
Для более глубокого понимания типов HTTP-ошибок и способов их диагностики рекомендуем ознакомиться с данным руководством:
- [5xx Server Errors: The Complete Guide](https://komodor.com/learn/5xx-server-errors-the-complete-guide/) — подробный разбор серверных ошибок.

## 🌟 Возможности
- Автоматический поиск установленного Antigravity 2.0, Antigravity IDE и Antigravity CLI (`agy`) в стандартных путях и реестре Windows.
- **Проверка обновлений** — автоматическая проверка новых версий при запуске и ручная проверка через меню (TOOLS → `7`).
- **Патч Antigravity CLI** — снятие экрана «Eligibility Check» в Go-бинаре `agy`/`agy.exe` на уровне машинного кода по байтовой сигнатуре для архитектур x86-64 и ARM64 (с резервной копией и откатом).
- **Патч Antigravity Manager (`language_server`)** — снятие проверки авторизации (`hasValidAuth=true`) в скомпилированном бинарнике бэкенда по байтовой сигнатуре для архитектур x86-64 и ARM64 (с резервной копией и откатом).
- Поддержка Linux: поиск по `/usr/share/antigravity-ide`, определение версии через `dpkg`, `rpm` и `package.json`.
- Поддержка macOS: поиск `.app`-бандла в `/Applications` и `~/Applications`, ad-hoc переподпись после изменения `main.js`.
- Создание резервной копии перед изменениями.
- Применение и откат патча через простое меню.
- Поддержка путей `resources/app/out/main.js` и `resources/app/main.js`.
- Цветной вывод и попытка автоматического повышения прав (UAC на Windows, предложение `sudo` на Linux).
- Проверка минимальной версии Antigravity IDE (>= `2.1.1`) перед применением патча.
- Определение версии Antigravity IDE через реестр Windows, пакетный менеджер на Linux или `package.json` на macOS.
- Обнаружение уже применённого патча с предложением применить повторно.

## 🚀 Как использовать
1. Закройте Antigravity IDE или Antigravity 2.0.
2. Запустите патчер от имени администратора (скрипт сам запросит повышение прав при необходимости).
3. В меню выберите нужное действие:

| Пункт меню | Описание |
|---|---|
| **PATCH** | |
| `1` Antigravity IDE patch | Применить патч к `main.js` для Antigravity IDE (bypass region lock) |
| `2` Antigravity 2.0 patch | Применить патч к бинарному файлу `language_server` (Antigravity Manager) |
| `3` Antigravity CLI (agy) patch | Применить патч к бинарю `agy`/`agy.exe` (unlock agy tool) |
| **RESTORE** | |
| `4` Antigravity IDE | Восстановить оригинальный `main.js` для Antigravity IDE из бэкапа |
| `5` Antigravity 2.0 | Восстановить оригинальный `language_server` из бэкапа |
| `6` Antigravity CLI | Восстановить оригинальный `agy`/`agy.exe` из бэкапа |
| **TOOLS** | |
| `7` Check for updates | Проверить наличие новых версий на GitHub |
| `8` Open GitHub repository | Открыть страницу проекта в браузере |
| `9` Select custom path | Выбрать путь к папке приложения или файлу вручную |
| **`0` Exit** | Выйти из патчера |

Запуск из исходников:
```bash
python main.py
```

Запуск с указанием пути (для Antigravity IDE, Antigravity 2.0 или Antigravity CLI):
```bash
# Windows
python main.py "C:\\Users\\<username>\\AppData\\Local\\Programs\\Antigravity IDE"
python main.py "C:\\Users\\<username>\\AppData\\Local\\Programs\\Antigravity\\resources\\bin\\language_server.exe"
python main.py "C:\\Users\\<username>\\AppData\\Local\\agy\\bin\\agy.exe"

# Linux
python main.py /usr/share/antigravity-ide
python main.py /opt/Antigravity/resources/bin/language_server
python main.py /usr/local/bin/agy

# macOS
python3 main.py /Applications/Antigravity\ IDE.app
python3 main.py /Applications/Antigravity.app
python3 main.py /usr/local/bin/agy
```

Если `main.js` или `language_server` находится рядом со скриптом, путь указывать не нужно — они будут найдены автоматически.

> **macOS:** если `Antigravity IDE.app` лежит в `/Applications`, запись потребует `sudo` (скрипт сам предложит перезапуск). Для установки в `~/Applications` или пользовательскую директорию `sudo` не нужен. После успешного патча `.app` автоматически переподписывается ad-hoc подписью (`codesign --force --deep --sign -`) — без этого Electron с Hardened Runtime не запустится на macOS.

### 🍎 Использование на macOS

Поскольку готовые бинарные сборки для macOS отсутствуют в официальных релизах (доступны только для Windows и Linux), вы можете либо запускать патчер напрямую из исходного кода, либо собрать исполняемый файл самостоятельно.

#### Вариант 1: Запуск из исходного кода (рекомендуется)
1. Создайте виртуальное окружение, активируйте его и установите необходимые зависимости:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Полностью закройте Antigravity 2.0 или Antigravity IDE.
3. Запустите патчер, указав путь к приложению:
   ```bash
   # Для Antigravity IDE
   python3 main.py "/Applications/Antigravity IDE.app"
   
   # Для Antigravity 2.0
   python3 main.py "/Applications/Antigravity.app"
   ```
   *Примечание: Если приложение находится в папке `/Applications`, скрипт автоматически запросит повышение прав (`sudo`) для записи.*

#### Вариант 2: Самостоятельная сборка бинарного файла
Если вам необходим готовый исполняемый файл, вы можете собрать его самостоятельно, следуя инструкции в разделе [🛠️ Сборка](#%EF%B8%8F-сборка).

После успешной сборки запуск скомпилированного файла выполняется через Терминал:
```bash
cd dist
chmod +x Open_AG_Patcher_macOS
sudo ./Open_AG_Patcher_macOS
```
Если macOS блокирует запуск скомпилированного файла, снимите quarantine-атрибут:
```bash
xattr -dr com.apple.quarantine Open_AG_Patcher_macOS
```

#### Что выбрать в меню
Используйте:
- **PATCH → `1`** (Antigravity IDE patch) для `Antigravity IDE.app`
- **PATCH → `2`** (Antigravity 2.0 patch) для `Antigravity.app` (бэкенд language_server)
- **PATCH → `3`** (Antigravity CLI (agy) patch) для бинаря `agy` (если установлен)
- **RESTORE → `4`**, `5` или `6` для восстановления из бэкапа

Для `Antigravity.app` патчер обычно сам находит:
```text
/Applications/Antigravity.app
```
Если автопоиск не нашел приложение, выберите **TOOLS → `9`** (Select custom path) и укажите один из путей:
```text
/Applications/Antigravity.app
/Applications/Antigravity IDE.app
```

#### Проверить подпись
После патча `.app` автоматически переподписывается ad-hoc подписью. Проверить это можно следующей командой:
```bash
codesign -dv /Applications/Antigravity.app 2>&1 | grep Signature
```
Ожидаемый результат:
```text
Signature=adhoc
```

## ❓ Что именно меняется

### Патч для Antigravity IDE

Патчер вносит изменения в `main.js` для обхода проверки `isGoogleInternal`. Изменения обратимы через резервную копию (`main.js.bak`).

### `resetIsTierGCPTos(),this.XXX.isGoogleInternal` → `resetIsTierGCPTos(),true`
Заменяет проверку флага `isGoogleInternal` после вызова `resetIsTierGCPTos()` в сервисе авторизации на безусловное `true`, активируя внутренний путь доступа Google. После применения патча автоматически очищаются папки кэша VS Code (`CachedData` и `Code Cache/js`), принуждая IDE перекомпилировать пропатченный JS-код.


### Патч для Antigravity Manager (language_server)

Antigravity Manager (`language_server` или `language_server.exe`) — бэкенд-служба, запускаемая внутри Antigravity 2.0. По умолчанию она требует валидную проверку авторизации и лицензии на стороне Google.

Патчер вносит изменения непосредственно в скомпилированный бинарный файл `language_server` по байтовой сигнатуре для двух архитектур:
- **x86-64** (Intel Mac / Windows / Linux x64): Находит и заменяет проверку `cmp byte ptr [rax + 8], 0` на `mov byte ptr [rax + 8], 1` с последующими `nop` (`\xc6\x40\x08\x01\x90\x90`).
- **ARM64** (Apple Silicon macOS / ARM64): Находит и заменяет инструкцию `ldr x8, [x1, #8]` (`28 04 40 f9`) на `movz x8, #1` (`28 00 80 d2`).

В результате возвращаемое значение `hasValidAuth` всегда принудительно выставляется в `true`, снимая блокировку.
Патч обратим через **RESTORE → `5`** восстановлением оригинального бинарника из `.agybak`.

### Патч для Antigravity CLI (agy)

Antigravity CLI — отдельный Go-бинарь (`agy.exe` на Windows, `agy` на Linux/macOS), который тоже показывает косметический экран «Eligibility Check», блокирующий дальнейшую работу. Поскольку это скомпилированный бинарь (не JS), патчинг выполняется **на уровне машинного кода** по уникальной байтовой сигнатуре под две архитектуры: **x86-64** (Windows / Intel Mac) и **ARM64** (Apple Silicon macOS).

#### x86-64 (Intel Mac / Windows)
1. В функции `handleAuthResult` eligibility-гейт строится на серверном поле `AuthResult.hasValidAuth` (байт по смещению `+8`):
   ```asm
   test rax,rax      ; 48 85 c0
   je   ...          ; 0f 84 xx xx xx xx
   cmp  byte[rax+8],0; 80 78 08 00     <-- проверка eligibility
   jne  ...          ; 0f 85 xx xx xx xx
   ```
2. Патчер находит эту последовательность по сигнатуре и переписывает `cmp byte[rax+8],0` на `test rax,rax ; nop` (`48 85 c0 90`). При этом `ZF=0`, и условный переход `jne` всегда берёт «eligible»-ветку — экран Eligibility больше не показывается.

#### ARM64 (Apple Silicon macOS)
1. В функции `handleAuthResult` (или `handleAuthResult.func1`) проверяется поле `AuthResult.hasValidAuth` (байт по смещению `+8`):
   ```asm
   cbnz x1, error_path   ; 01 20 00 b5
   cbz  x0, failure_path ; a0 14 00 b4
   ldrb w8, [x0, #8]     ; 08 20 40 39     <-- загрузка hasValidAuth
   tbnz w8, #0, success  ; 68 14 00 37     <-- проверка eligibility
   ```
2. Патчер находит эту последовательность по сигнатуре и заменяет инструкцию `ldrb w8, [x0, #8]` на `mov w8, #1` (`28 00 80 52`). В результате регистр `w8` всегда равен 1, и условный переход `tbnz` всегда переходит на success-путь, минуя экран блокировки.

#### Общие шаги
3. Перед записью создаётся резервная копия `agy.exe.agybak` (или `agy.agybak` на POSIX). Если существующий бэкап устарел (приложение автообновилось), он автоматически обновляется — stale-копии не хранятся.
4. На macOS после модификации бинарь переподписывается ad-hoc (как и в случае с `.app`).

**Безопасность патча:**
- Если байтовая сигнатура не найдена в бинаре (неизвестная/неподдерживаемая версия), патчер **отказывается патчить** и ничего не меняет — выводится «signature not found (unsupported version?)».
- Если сигнатура встречается больше одного раза, патчер тоже отказывается («not unique — refusing to guess») — не угадывает, какой сайт править.
- Откат выполняется через **RESTORE → `6`** (Antigravity CLI) восстановлением из `.agybak`.

> **Примечание по платформам:** сигнатура для x86-64 проверена под Windows и Intel macOS, для ARM64 — под Apple Silicon macOS. Discovery ищет бинарь кроссплатформенно (`PATH`, scoop на Windows, `/usr/local/bin`, `/opt/antigravity/bin`, `~/.local/bin` на POSIX). На Linux бинарь `agy` может быть скомпилирован иначе, и сигнатура может не совпасть — в этом случае патч честно сообщит об этом без модификации файла.

## 🔍 Логика поиска файла

Патчер ищет `main.js` в следующем порядке:

1. Аргумент командной строки (путь к директории или напрямую к `main.js`).
2. Текущая директория (`./main.js`).
3. Автоматический поиск по стандартным путям:
   - **Windows:**
     - `%LOCALAPPDATA%\Programs\Antigravity IDE`
   - **Linux:**
     - `/usr/share/antigravity-ide`
     - `/opt/Antigravity IDE`
     - `/opt/Antigravity IDE/resources/app/out`
   - **macOS:**
     - `/Applications/Antigravity IDE.app/Contents/Resources/app`
     - `~/Applications/Antigravity IDE.app/Contents/Resources/app`
4. Реестр Windows (ключ `{AA73B3E3-C6C8-45C8-B1DC-4AE56C751432}_is1` в `HKCU` и `HKLM`: `SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\`).

Внутри найденной директории проверяются пути:
- `resources/app/out/main.js`
- `resources/app/main.js`
- `out/main.js` (macOS)
- `main.js` (если путь указан напрямую)

На macOS скрипт также принимает путь к `.app`-бандлу напрямую — `Contents/Resources/app/out/main.js` ресолвится автоматически.

### Поиск Antigravity CLI (`agy`)

Бинарь `agy` (`agy.exe` на Windows) ищется location-agnostic — по `PATH` и стандартным каталогам, без хардкодных путей/версий:

1. Аргумент командной строки или **TOOLS → `9` → `3`** (путь к файлу `agy`/`agy.exe` или к папке).
2. `PATH` (`shutil.which("agy")`).
3. Стандартные каталоги:
   - **Windows:** `%LOCALAPPDATA%`, `%PROGRAMFILES%`, `%PROGRAMFILES(X86)%`, `%ProgramData%`, `%APPDATA%` (+ подпапки `Programs`), scoop (`%USERPROFILE%\scoop\apps`, `%SCOOP%\apps`). Шаблоны: `agy/bin/agy.exe`, `agy/*/bin/agy.exe` (scoop version-dirs), `agy*/agy.exe`.
   - **Linux/macOS:** `/usr/local/bin`, `/usr/bin`, `/opt/antigravity/bin`, `/opt/antigravity`, `~/.local/bin`, `~/bin`.

Если найдено несколько копий (например, scoop с несколькими версиями), выбирается самая свежая по mtime.

## 🔎 Определение версии Antigravity IDE

| Платформа | Метод определения версии |
|---|---|
| **Windows** | Реестр: `DisplayVersion` из ключа `{AA73B3E3-...}_is1` |
| **Linux (deb)** | `dpkg-query -W antigravity-ide` |
| **Linux (rpm)** | `rpm -q --queryformat %{VERSION} antigravity-ide` |
| **Linux (portable/snap/flatpak)** | `package.json` рядом с `main.js` |
| **macOS** | `package.json` в `Antigravity IDE.app/Contents/Resources/app/` |

Если версия не определена, патчер предлагает продолжить без проверки. Если версия ниже `2.1.1` — предупреждает и также предлагает выбор.

## 🔒 Проверка уже применённого патча

Перед патчингом скрипт проверяет, не был ли файл уже пропатчен, по двум признакам:
- отсутствие `if(this.X.isGoogleInternal)` (паттерн заменён на `if(true)`)
- отсутствие немодифицированных `isGoogleInternal` (comma-based auth check).

## 🛡️ Повышение прав

- **Windows**: автоматический UAC-запрос через `ShellExecuteW` с параметром `runas`. Корректно обрабатывает пути с пробелами.
- **Linux**: если скрипт запущен не от root, предлагает перезапуститься через `sudo` (`os.execvp`). При отказе продолжает с предупреждением о возможных ошибках записи. При этом runtime workaround пишет в `settings.json` исходного пользователя (`SUDO_USER`/`SUDO_UID`), а не в `/root/.config/...`.
- **macOS**: использует ту же posix-ветку — `sudo` предлагается, если запущено без root. Для `~/Applications/Antigravity IDE.app` на `sudo` можно ответить «n» (директория уже доступна на запись), для `/Applications/Antigravity IDE.app` — согласиться. Пользовательский `settings.json` при запуске через `sudo` также берётся из home исходного пользователя, а не `root`.

## 🍎 Особенности macOS

### Переподпись `.app` после патча

Любое изменение файла внутри подписанного `.app`-бандла нарушает code signature. Electron-приложения с включённым Hardened Runtime (Antigravity IDE — одно из них) после этого **не запускаются** на macOS — до того, как Gatekeeper вообще покажет пользователю диалог.

Чтобы `.app` продолжал работать, скрипт после `do_patch` и `do_restore` автоматически выполняет:

```bash
codesign --force --deep --sign - /path/to/Antigravity\ IDE.app
xattr -dr com.apple.quarantine /path/to/Antigravity\ IDE.app
```

`--sign -` — ad-hoc подпись (без Developer ID). Этого достаточно для локального запуска приложения. Notarization не требуется.

Требуется установленный `codesign` — он идёт в составе **Xcode Command Line Tools**:
```bash
xcode-select --install
```

### Ошибка "Operation not permitted" при патчинге

Если вы столкнулись с ошибкой `[!] Backup error: [Errno 1] Operation not permitted: '/Applications/Antigravity IDE.app/Contents/Resources/app/out/main.js.bak'`:

1. Добавьте для терминала разрешение на полный доступ к диску: **Системные настройки → Конфиденциальность и безопасность → Полный доступ к диску** (System Settings → Privacy & Security → Full Disk Access).
2. Снимите карантин с приложения командой:
   ```bash
   sudo xattr -rd com.apple.quarantine /path/to/Antigravity\ IDE.app
   ```

### Если приложение не запускается после патча

1. Убедись, что `codesign` доступен: `which codesign`.
2. Проверь, что `.app` был переподписан: `codesign -dv /Applications/Antigravity\ IDE.app 2>&1 | grep Authority` — должен быть `Signature=adhoc`.
3. Если macOS всё равно блокирует: `Системные настройки → Конфиденциальность и безопасность` — внизу будет кнопка «Открыть всё равно».

## ⚙️ Требования

- **Python** 3.x
- **Зависимости**: `packaging` (для сравнения версий)
- **ОС**:
  - **Windows** — полная поддержка автопоиска через реестр и UAC.
  - **Linux** — автопоиск в `/usr/share/antigravity-ide`, определение версии через `dpkg`/`rpm`/`package.json`, sudo-повышение.
  - **macOS** — автопоиск в `/Applications/Antigravity IDE.app` и `~/Applications/Antigravity IDE.app`, определение версии через `package.json`, ad-hoc переподпись через `codesign` (Xcode Command Line Tools).
- **Минимальная версия Antigravity 2.0**: `2.3.0`
- **Минимальная версия Antigravity IDE**: `2.1.1`
- **Поддерживаемые версии**: `2.3.0` и выше для Antigravity 2.0, `2.1.1` и выше для IDE

## 🛠️ Сборка

Для сборки исполняемых файлов рекомендуется использовать виртуальное окружение:

1. **Создание и активация виртуального окружения:**
   * **Windows:**
     ```bash
     cd source
     python -m venv .venv
     .venv\Scripts\activate
     ```
   * **Linux / macOS:**
     ```bash
     cd source
     python3 -m venv .venv
     source .venv/bin/activate
     ```

2. **Установка зависимостей:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Сборка через PyInstaller:**
   * **Windows:**
     ```bash
     pyinstaller --onefile --uac-admin --icon=icon.ico --name="Open_AG_Patcher_Windows" --noupx --clean --version-file=version.txt main.py
     ```
   * **Linux:**
     ```bash
     pyinstaller --onefile --icon=icon.ico --name="Open_AG_Patcher_Linux" --hidden-import=packaging --hidden-import=packaging.version --hidden-import=packaging.specifiers --hidden-import=packaging.requirements main.py
     ```
   * **macOS (Universal2):**
     ```bash
     pyinstaller --onefile --name="Open_AG_Patcher_macOS" --target-arch universal2 --hidden-import=packaging --hidden-import=packaging.version --hidden-import=packaging.specifiers --hidden-import=packaging.requirements main.py
     ```

## Структура проекта

- `source/main.py` — основная точка входа в патчер (выполняет проверку прав доступа и запуск CLI).
- `source/patcher/` — основной исходный код патчера с модульной архитектурой:
  - `constants.py` — глобальные константы, регулярные выражения, версии.
  - `cli.py` — консольный интерфейс пользователя, меню и обработка ввода.
  - `utils/` — системные вспомогательные утилиты (цвета консоли, права администратора, POSIX-права, хэширование файлов).
  - `ide/` — логика поиска и патчинга непосредственно Antigravity IDE (файлы `main.js`).
  - `agy/` — логика поиска и байт-сигнатурного патчинга бинаря Antigravity CLI (`agy`/`agy.exe`).
  - `manager/` — логика поиска и байт-сигнатурного патчинга бинаря Antigravity Manager (`language_server`/`language_server.exe`).
- `source/requirements.txt` — зависимости для сборки и запуска.
- `source/build.txt` — примеры команд сборки под разные ОС.
- `source/icon.ico` — иконка для `exe`/`app`.

# 📜 Лицензия

Проект распространяется под лицензией GPL-3.0. Полный текст лицензии содержится в файле [`LICENSE`](LICENSE).

---
# 💰 Поддержать автора
+ **SBER**: `2202 2050 1464 4675`
