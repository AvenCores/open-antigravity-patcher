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

Опенсорс патчер для Antigravity 2.0, Antigravity IDE, Antigravity CLI и расширения Google Antigravity для VS Code: снимает регионные ограничения без VPN и смены региона аккаунта Google. Опенсурс аналог утилиты [Antigravity IDE в России без VPN и смены региона аккаунта Google](https://github.com/confeden/Antigravity).

![maxresdefault](https://i.ibb.co/s9Vh80CM/python-w-TPlox-Po-G4.png)

# 🎦 Видео гайд по установке и решению проблем

![maxresdefault](https://github.com/user-attachments/assets/54c4f1bd-01f5-4ee8-92d1-f7bbb910d079)

<div align="center">

[**Смотреть на YouTube**](https://youtu.be/GyQVTxgt12E)

[**Смотреть на Rutube**](https://rutube.ru/video/aba4484f8e0b5e67e966ff8229385f83/)

[**Смотреть на Dzen**](https://dzen.ru/video/watch/6a7c430575822e0e4ba2970e)

[**Смотреть в VK Video**](https://vkvideo.ru/video-234234162_456239108)

[**Смотреть в Telegram**](https://t.me/avencoreschat/571689)

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

## ⚠️ Ошибка HTTP 403 Forbidden / SUBSCRIPTION_REQUIRED (#3501) / Agent execution terminated due to error
Если в Antigravity IDE или CLI (`agy`) появляется ошибка `HTTP 403 Forbidden` с причиной `SUBSCRIPTION_REQUIRED` или сообщением `You do not have a valid license of this product` или `Agent execution terminated due to error`, это не проблема локального патча и не экран `Eligibility Check`.

Эта ошибка связана с API Google и состоянием аккаунта пользователя: лицензией, доступом или проверкой прав на стороне Google. Патчер меняет только локальные файлы Antigravity/Antigravity CLI и не может выдать аккаунту лицензию или изменить ответ Google API, поэтому с этой ошибкой он не поможет.

**Решение:**
1. **Смените регион аккаунта Google** или используйте аккаунт, зарегистрированный в регионе, где Antigravity официально работает.
2. **Если смена региона не помогает**, необходимо купить официальную подписку.

**Доступные тарифные планы (Google AI):**

*   **Google AI Plus**
    *   **Цена:** 445 ₽ в месяц
    *   **Хранилище:** 400 ГБ
    *   **Возможности:** Используйте ИИ-инструменты для продуктивной работы и увеличенные в 2 раза лимиты* в Gemini.
    *   [Оформить подписку Plus](https://one.google.com/about/google-ai-plans/) | [Посмотреть преимущества тарифа](https://one.google.com/about/google-ai-plans/) *(Есть условия)*
*   **Google AI Pro**
    *   **Цена:** 1 790 ₽/мес.
    *   **Хранилище:** 5 ТБ
    *   **Возможности:** Успевайте больше с увеличенными в 4 раза лимитами* в Gemini.
    *   [Оформить подписку Pro](https://one.google.com/about/google-ai-plans/) | [Посмотреть преимущества тарифа](https://one.google.com/about/google-ai-plans/) *(Есть условия)*
*   **Google AI Ultra**
    *   **Цена:** От 6 990 ₽/мес.
    *   **Хранилище:** От 20 ТБ
    *   **Возможности:** Ускорьте рабочие процессы с увеличенными в 20 раз лимитами* в Gemini.
    *   [Оформить подписку Ultra](https://one.google.com/about/google-ai-plans/) | [Посмотреть преимущества тарифа](https://one.google.com/about/google-ai-plans/) *(Есть условия)*

**Пример ошибки:**
```json
{
  "error": {
    "code": 403,
    "details": [
      {
        "@type": "type.googleapis.com/google.rpc.ErrorInfo",
        "domain": "cloudaicompanion.googleapis.com",
        "metadata": {
          "error_number": "1001",
          "uiMessage": "true"
        },
        "reason": "SUBSCRIPTION_REQUIRED"
      }
    ],
    "message": "You do not have a valid license of this product. Please contact your administrator to request a license. If you are not an enterprise user and believe you are receiving this message as an error, please try using the latest version and logging in again. (#3501)",
    "status": "PERMISSION_DENIED"
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

## ⚠️ Ошибка патча: "✗ isGoogleInternal -> true (auth) — pattern not found"

Если при применении патча (PATCH → `1`: Antigravity IDE patch) вы получаете сообщение:

```text
✗ isGoogleInternal -> true (auth) — pattern not found
```

это означает, что патчер не нашёл ожидаемый паттерн `isGoogleInternal` в файле `main.js`, который он пытается пропатчить.

**В почти 100% случаев это происходит потому, что патчер нашёл и пытается пропатчить случайный `main.js` файл, не относящийся к Antigravity IDE.**

### Решение:

1. Проверьте в главном меню патчера, какой именно путь к файлу `main.js` был определён (обычно выводится перед началом патчинга).
2. Убедитесь, что путь ведёт к реальному файлу Antigravity IDE, например:
   - Windows: `%LOCALAPPDATA%\Programs\Antigravity IDE\resources\app\out\main.js`
   - Linux: `/usr/share/antigravity-ide/resources/app/out/main.js`
   - macOS: `/Applications/Antigravity IDE.app/Contents/Resources/app/out/main.js`
3. Если путь указывает на другой файл (например, `main.js` из другого Electron-приложения или из текущей директории скрипта), выберите **TOOLS → `11` (Select custom path)** и укажите корректный путь к папке Antigravity IDE вручную.
4. Убедитесь, что в рабочей директории патчера нет постороннего файла `main.js` — если он там есть, патчер может подхватить его вместо нужного (поиск начинается с текущей директории).

> **Примечание:** Если вы запускаете патчер из папки, где лежит какой-либо другой `main.js` (например, от другого проекта), переместите скрипт в другую директорию или явно укажите путь к Antigravity IDE через аргумент командной строки:
>
> ```bash
> python main.py "C:\Users\<username>\AppData\Local\Programs\Antigravity IDE"
> ```

## 📚 Дополнительная информация по ошибкам
Для более глубокого понимания типов HTTP-ошибок и способов их диагностики рекомендуем ознакомиться с данным руководством:
- [5xx Server Errors: The Complete Guide](https://komodor.com/learn/5xx-server-errors-the-complete-guide/) — подробный разбор серверных ошибок.

## 🌟 Возможности
- Автоматический поиск установленного Antigravity 2.0, Antigravity IDE, Antigravity CLI (`agy`) и расширения Google Antigravity для VS Code в стандартных путях и реестре Windows.
- **Проверка обновлений** — автоматическая проверка новых версий при запуске и ручная проверка через меню (TOOLS → `9`).
- **Патч Antigravity CLI** — снятие экрана «Eligibility Check» и обход проверки eligibility в Go-бинаре `agy`/`agy.exe` на уровне машинного кода по байтовой сигнатуре для архитектур x86-64 и ARM64 (с резервной копией и откатом).
- **Патч Antigravity Manager (`language_server`)** — снятие проверки авторизации (`hasValidAuth=true`) в скомпилированном бинарнике бэкенда по байтовой сигнатуре для архитектур x86-64 и ARM64 (с резервной копией и откатом).
- **Патч расширения Google Antigravity для VS Code** — инъекция guard'а от повторного скачивания бинаря в `extension.js` расширения `google.google-antigravity` + отключение проверки смены release-канала (`isChannelChanged -> false`), чтобы уже скачанный/пропатченный бинарь не перезаписывался. Дополнительно патчит скачанный бинарь `~/.gemini/bin/antigravity` agy-патчем.
- Поддержка Linux: поиск по `/usr/share/antigravity-ide`, определение версии через `dpkg`, `rpm` и `package.json`.
- Поддержка macOS: поиск `.app`-бандла в `/Applications` и `~/Applications`, ad-hoc переподпись после изменения `main.js`.
- Создание резервной копии перед изменениями.
- **Атомарная замена бинарей на POSIX** — `agy` и `language_server` на Linux/macOS записываются через временный файл (`tempfile.mkstemp` в той же директории, O_EXCL) и `os.replace`: запущенный процесс не блокирует патч (нет `ETXTBSY` / «Permission denied» из-за занятого бинаря), файл сохраняет права (`+x` не слетает), owner/group оригинала; временный файл удаляется при любой ошибке, а симлинки патчиться отказывается. Общая логика — `source/patcher/utils/atomic.py`.
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
| `4` Antigravity VS Code Patch | Патч `extension.js` расширения `google.google-antigravity` + бинаря `~/.gemini/bin/antigravity` (требует установленный и запатченный Antigravity 2.0) |
| **RESTORE** | |
| `5` Antigravity IDE | Восстановить оригинальный `main.js` для Antigravity IDE из бэкапа |
| `6` Antigravity 2.0 | Восстановить оригинальный `language_server` из бэкапа |
| `7` Antigravity CLI | Восстановить оригинальный `agy`/`agy.exe` из бэкапа |
| `8` Antigravity VS Code extension | Восстановить оригинальный `extension.js` (и бинарь `~/.gemini/bin`) из бэкапа |
| **TOOLS** | |
| `9` Check for updates | Проверить наличие новых версий на GitHub |
| `10` Open GitHub repository | Открыть страницу проекта в браузере |
| `11` Select custom path | Выбрать путь к папке приложения или файлу вручную (IDE / 2.0 / CLI / VS Code extension) |
| `12` About program | Показать информацию о программе и авторе |
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
- **PATCH → `4`** (Antigravity VS Code Patch) для расширения `google.google-antigravity` в VS Code
- **RESTORE → `5`**, `6`, `7` или `8` для восстановления из бэкапа

Для `Antigravity.app` патчер обычно сам находит:
```text
/Applications/Antigravity.app
```
Если автопоиск не нашел приложение, выберите **TOOLS → `11`** (Select custom path) и укажите один из путей:
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

Патчер вносит изменения непосредственно в скомпилированный бинарный файл `language_server` по байтовой сигнатуре для двух архитектур через класс `MultiGate`:
- **x86-64** (Intel Mac / Windows / Linux x64): Находит и заменяет проверку `cmp byte ptr [rax + 8], 0` на `mov byte ptr [rax + 8], 1` с последующими `nop` (`\xc6\x40\x08\x01\x90\x90`).
- **ARM64** (Linux arm64 / Apple Silicon macOS): Находит и заменяет последовательность `ldrb w3, [x0, #8] ; tbz w3, #0, skip` (с учётом одной или двух инструкций подготовки) на `mov w3, #1 ; strb w3, [x0, #8]` (`\x23\x00\x80\x52\x03\x20\x00\x39`).

В результате возвращаемое значение `hasValidAuth` всегда принудительно выставляется в `true`, снимая блокировку.
Патч обратим через **RESTORE → `6`** восстановлением оригинального бинарника из `.agybak`.
Запись на POSIX выполняется так же атомарно, как и для `agy` (временный файл + `os.replace`, сохранение `+x` и владельца), а работающий `language_server` не блокирует патч.

### Патч для Antigravity CLI (agy)

Antigravity CLI — отдельный Go-бинарь (`agy.exe` на Windows, `agy` на Linux/macOS), который показывает косметический экран «Eligibility Check» и формирует ошибку «Account ineligible» по ответу сервера. Поскольку это скомпилированный бинарь (не JS), патчинг выполняется **на уровне машинного кода** по уникальной байтовой сигнатуре под две архитектуры через `MultiGate`: **x86-64** (Windows / Linux x64 / Intel Mac) и **ARM64** (Windows ARM64 / Linux arm64 / Apple Silicon macOS).

Патчер применяет **один гейт** — внешняя проверка перед построением ошибки делает ветку ошибки недостижимой:

#### Gate 1 — экран «Eligibility Check»

##### x86-64
1. Патчер сканирует бинарник в поисках уникальной сигнатуры проверки гейта:
   ```asm
   test rax, rax              ; 48 85 c0            <-- auth-результат == nil?
   je  eligible               ; 0f 84 xx xx xx xx   <-- если nil → GOOD
   cmp byte ptr [rax+8], 0   ; 80 78 08 00         <-- проверка флага eligibility
   jne eligible               ; 0f 85 xx xx xx xx   <-- если флаг != 0 → GOOD
   call failure_builder       ; e8 xx xx xx xx      <-- BAD: построение ошибки
   ```
2. Патчер заменяет `cmp byte ptr [rax+8], 0` на `test rax,rax` + `NOP` (`48 85 c0 90`). Так как `rax` здесь гарантированно не равен нулю, переход `jne` всегда уводит выполнение в ветку «eligible».

##### ARM64
1. В актуальных нативных arm64-сборках внешняя проверка перед построением ошибки выглядит как:
   ```asm
   cbnz x1, error            ; xx xx xx b5     <-- если x1 != 0 → BAD
   cbz  x0, eligible         ; xx xx xx b4     <-- если x0 == 0 → GOOD
   ldrb w1, [x0, #8]        ; 01 20 40 39     <-- загрузка флага eligibility
   tbnz w1, #0, eligible    ; xx xx xx 37     <-- если бит 0 != 0 → GOOD
   bl   failure_builder      ; xx xx xx 97     <-- BAD: построение ошибки
   ```
2. Патчер заменяет загрузку флага `ldrb w1,[x0,#8]` на `mov w1,#1` (`21 00 80 52`), поэтому существующий `tbnz` всегда выбирает ветку «eligible». `MultiGate` автоматически выбирает x64- или arm64-сигнатуру.

#### Общие шаги
3. Перед записью создаётся резервная копия `agy.exe.agybak` (или `agy.agybak` на POSIX). Если существующий бэкап устарел (приложение автообновилось), он автоматически обновляется — stale-копии не хранятся.
4. На Linux/macOS запись выполняется атомарно: новые байты пишутся во временный файл (`tempfile.mkstemp`, O_EXCL) в той же директории, после `fsync` он переименовывается поверх целевого через `os.replace` с сохранением прав, владельца и группы оригинала. Запущенный `agy` не мешает патчу — ядро продолжает исполнять старый inode, а последующие запуски получают новый бинарь. На Windows запись идёт напрямую в файл.
5. На macOS после модификации бинарь переподписывается ad-hoc (как и в случае с `.app`).

**Безопасность патча:**
- Если байтовая сигнатура не найдена в бинаре (неизвестная/неподдерживаемая версия), патчер **отказывается патчить** и ничего не меняет — выводится «signature not found (unsupported version?)».
- Перед записью каждый патч валидируется: смещение не отрицательное, патч не выходит за границы файла и не меняет его размер.
- Патчинг симлинков запрещён: цель обязана быть обычным файлом, иначе патчер отказывается выполнять запись.
- Если сигнатура встречается несколько раз (Go может компилировать одну функцию в нескольких экземплярах), патчер применяет фикс ко **всем** вхождениям — они идентичны на уровне машинного кода.
- Откат выполняется через **RESTORE → `7`** (Antigravity CLI) восстановлением из `.agybak`.

> **Примечание по платформам:** сигнатуры для x86-64 проверены под Windows и Intel macOS, для ARM64 — под Apple Silicon macOS. Discovery ищет бинарь кроссплатформенно (`PATH`, scoop на Windows, `/usr/local/bin`, `/opt/antigravity/bin`, `~/.local/bin` на POSIX). На Linux бинарь `agy` может быть скомпилирован иначе, и сигнатура может не совпасть — в этом случае патч честно сообщит об этом без модификации файла.

### Патч для расширения Google Antigravity (VS Code)

> **⚠️ Важно:** для корректного патча VS Code расширения (`PATCH → 4`) нужен установленный и уже запатченный Antigravity 2.0 (`PATCH → 2` — патч `language_server`). Сначала установите Antigravity 2.0, примените к нему патч, и только потом патчите расширение `google.google-antigravity` в VS Code.

Расширение `google.google-antigravity` для VS Code при каждом запуске проверяет версию бэкенд-бинаря и перекачивает его с release-сервера Google. Патчер вносит два изменения в `extension.js` расширения:

#### Part 1 — guard от повторного скачивания

После строки `outputChannel.appendLine('[INSTALL] Checking Antigravity releases...')` инъектируется блок, который проверяет наличие уже скачанного бинаря (по `targetPathOverride` или в `~/.gemini/bin`) и, если он найден, **немедленно возвращает путь к нему**, пропуская проверку версии и повторное скачивание:

```js
{const __primary=options.targetPathOverride||getInstalledTargetPath();
const __candidates=[__primary,
(0,path_1.join)((0,path_1.dirname)(__primary),'antigravity'+((0,path_1.extname)(__primary)||''))];
for(const __p of __candidates){if(__p&&await pathExists(__p)){
outputChannel.appendLine('[INSTALL] Existing binary found at '+__p+'. Skipping version check and re-download.');return __p;}}}
```

Поиск точки вставки выполняется гибким regex'ом, который матчит **полный вызов** `outputChannel.appendLine('...');` — с учётом разных кавычек и пробелов, но строго до закрывающей скобки вызова, чтобы инъекция попала после него, а не внутрь.

#### Part 2 — отключение проверки смены release-канала

```js
// было:
const isChannelChanged = manifestFetched && lastInstalledUrl !== releaseBaseUrl;
// стало:
const isChannelChanged = false;
```

Без этого расширение считает release-канал изменённым и принудительно перекачивает бинарь, затирая пропатченный.

#### Дополнительно — патч скачанного бинаря

Сразу после патча `extension.js` патчер предлагает применить agy-патч (см. выше) к скачанному расширением бинарю `~/.gemini/bin/antigravity` (или `~/.gemini/bin/agy`) — он содержит ту же проверку eligibility.

**Детали:**
- Резервная копия: `extension.js.vscodebak` рядом с оригиналом; stale-бэкапы автоматически обновляются.
- Обнаружение уже применённого патча по наличию инъекции и `const isChannelChanged = false;`.
- Откат: **RESTORE → `8`** восстанавливает `extension.js` из `.vscodebak`, а также предлагает восстановить бинарь `~/.gemini/bin` из `.agybak`.
- После патча требуется перезагрузка окна VS Code (**Developer: Reload Window**).
- Поиск расширения: `~/.vscode/extensions`, `~/.vscode-insiders/extensions`, `~/.vscode-oss/extensions`, `~/.vscode-server/extensions`, `~/.vscode-server-insiders/extensions` (или каталог из env `VSCODE_EXTENSIONS`). При нескольких версиях выбирается самая свежая по mtime.

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

1. Аргумент командной строки или **TOOLS → `11` → `3`** (путь к файлу `agy`/`agy.exe` или к папке).
2. `PATH` (`shutil.which("agy")`).
3. Стандартные каталоги:
   - **Windows:** `%LOCALAPPDATA%`, `%PROGRAMFILES%`, `%PROGRAMFILES(X86)%`, `%ProgramData%`, `%APPDATA%` (+ подпапки `Programs`), scoop (`%USERPROFILE%\scoop\apps`, `%SCOOP%\apps`). Шаблоны: `agy/bin/agy.exe`, `agy/*/bin/agy.exe` (scoop version-dirs), `agy*/agy.exe`.
   - **Linux/macOS:** `/usr/local/bin`, `/usr/bin`, `/opt/antigravity/bin`, `/opt/antigravity`, `~/.local/bin`, `~/bin`.

Если найдено несколько копий (например, scoop с несколькими версиями), выбирается самая свежая по mtime.

### Поиск расширения Google Antigravity (VS Code)

Файл `extension.js` расширения `google.google-antigravity` ищется в следующих каталогах (первым — переопределение через env `VSCODE_EXTENSIONS`):

1. Аргумент командной строки или **TOOLS → `11` → `4`** (путь к `extension.js`, каталогу расширения `google.google-antigravity-*` или корню `extensions`).
2. `~/.vscode/extensions`
3. `~/.vscode-insiders/extensions`
4. `~/.vscode-oss/extensions`
5. `~/.vscode-server/extensions` (remote-сервер)
6. `~/.vscode-server-insiders/extensions`

Внутри каталога расширений ищутся папки по маске `google.google-antigravity-*`; при нескольких версиях выбирается самая свежая по mtime. Ожидаемый файл — `extension.js` в корне каталога расширения.

### Поиск бинаря `~/.gemini/bin`

Бинарь, скачиваемый расширением (используется только пунктом **PATCH → `4`**), ищется в `~/.gemini/bin`: `antigravity.exe`/`agy.exe` на Windows, `antigravity`/`agy` на POSIX. Если бинаря там нет, но расширение ещё ни разу не запускалось — патчер подскажет запустить расширение в VS Code один раз, чтобы оно скачало бинарь.

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
- **Минимальная версия Antigravity 2.0**: `2.5.0`
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
  - `utils/` — системные вспомогательные утилиты (цвета консоли, права администратора, POSIX-права, хэширование файлов, атомарная замена бинарей `atomic.py`).
  - `ide/` — логика поиска и патчинга непосредственно Antigravity IDE (файлы `main.js`).
  - `agy/` — логика поиска и байт-сигнатурного патчинга бинаря Antigravity CLI (`agy`/`agy.exe`).
  - `manager/` — логика поиска и байт-сигнатурного патчинга бинаря Antigravity Manager (`language_server`/`language_server.exe`).
  - `vscode/` — логика поиска и патчинга расширения `google.google-antigravity` для VS Code (`extension.js`) и скачанного им бинаря в `~/.gemini/bin`.
- `source/requirements.txt` — зависимости для сборки и запуска.
- `source/build.txt` — примеры команд сборки под разные ОС.
- `source/icon.ico` — иконка для `exe`/`app`.

# 📜 Лицензия и атрибуция

Проект распространяется под лицензией GPL-3.0. Полный текст лицензии содержится в файле [`LICENSE`](LICENSE).

Часть изменений и решений в данном проекте основана на наработках репозитория [eligibility-antigravity-patcher](https://github.com/QNIX-Dev/eligibility-antigravity-patcher), распространяемого под лицензией MIT. Все интеграции и изменения выполнены с сохранением авторских прав и указанием первоисточника.

---
# 💰 Поддержать автора
+ **SBER**: `2202 2050 1464 4675`
