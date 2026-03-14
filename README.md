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
[![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)](https://github.com/AvenCores/open-antigravity-unlock)
[![GPL-3.0 License](https://img.shields.io/badge/License-GPL--3.0-blue?style=for-the-badge)](./LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/AvenCores/open-antigravity-unlock?style=for-the-badge)](https://github.com/AvenCores/open-antigravity-unlock/stargazers)
![GitHub forks](https://img.shields.io/github/forks/AvenCores/open-antigravity-unlock?style=for-the-badge)
[![GitHub pull requests](https://img.shields.io/github/issues-pr/AvenCores/open-antigravity-unlock?style=for-the-badge)](https://github.com/AvenCores/open-antigravity-unlock/pulls)
[![GitHub issues](https://img.shields.io/github/issues/AvenCores/open-antigravity-unlock?style=for-the-badge)](https://github.com/AvenCores/open-antigravity-unlock/issues)

Опенсорс патчер для Antigravity: снимает регионные ограничения без VPN и смены региона аккаунта Google. Опенсурс аналог утилиты [Antigravity в России без VPN и смены региона аккаунта Google](https://github.com/confeden/Antigravity).

<img width="979" height="512" alt="1" src="https://github.com/user-attachments/assets/367f64de-241f-4210-84ad-5b9fecd76334" />

# 🎦 Видео гайд по установке и решению проблем

<img width="979" height="512" alt="1" src="https://i127.fastpic.org/big/2026/0314/98/07b762c3a6a29ff220a66da40e16e698.png?md5=BNMT3ALCT2xXPA_7iuzW2g&expires=1773496800" />

<div align="center">

[**Смотреть на YouTube**](https://youtu.be/hMOeXUQHy4I)

[**Смотреть на Dzen**](https://dzen.ru/video/watch/69b43e995330f8608c7b39e3)

[**Смотреть в VK Video**](https://vkvideo.ru/video-234234162_456239068)

[**Смотреть в Telegram**](https://t.me/avencoreschat/456321)

</div>

## ⚠️ Ошибка HTTP 500 Internal Server Error
Если при запросе в Antigravity появляется ошибка HTTP 500 Internal Server Error, то ничего не поделать, меняйте аккаунт (желательно на регион, где Antigravity официально работает или куплена платная подписка), платная утилита также её не решала.

**Пример ошибки**
> Trajectory ID: 2669b09c-1d11-4620-9bfa-6ad1f0e26a88
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

## 🌟 Возможности
- Автоматический поиск установленного Antigravity в стандартных путях и реестре Windows.
- Создание резервной копии `main.js.bak` перед изменениями.
- Применение и откат патча через простое меню.
- Поддержка путей `resources/app/out/main.js` и `resources/app/main.js`.
- Цветной вывод и попытка автоматического повышения прав (UAC).

## 🚀 Как использовать
1. Закройте Antigravity.
2. Запустите патчер от имени администратора (скрипт сам запросит повышение прав при необходимости).
3. В меню выберите `Apply patch` или `Restore from backup`.

Запуск из исходников:
```bash
python main.py
```

Запуск с указанием пути:
```bash
python main.py "C:\\Program Files\\Antigravity"
python main.py "C:\\Program Files\\Antigravity\\resources\\app\\out\\main.js"
```

## ❓ Что именно меняется
Патчер вносит правки в `main.js`, чтобы убрать проверки внутренних/региональных ограничений и корректно пройти онбординг. Также добавляется безопасный fallback для получения статуса пользователя. Все изменения обратимы через резервную копию.

## 🛠️ Сборка
Требуется `pyinstaller`:
```bash
pip install -r requirements.txt
pyinstaller --onefile --uac-admin --icon=icon.ico --name="Open AG Patcher" main.py
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
