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
[![Website](https://img.shields.io/badge/Website-Goida%20VPN-207e5c?style=for-the-badge&logo=firefox)](https://avencores.github.io/goida-vpn-site/)
[![GitHub stars](https://img.shields.io/github/stars/AvenCores/open-antigravity-unlock?style=for-the-badge)](https://github.com/AvenCores/open-antigravity-unlock/stargazers)
![GitHub forks](https://img.shields.io/github/forks/AvenCores/open-antigravity-unlock?style=for-the-badge)
[![GitHub pull requests](https://img.shields.io/github/issues-pr/AvenCores/open-antigravity-unlock?style=for-the-badge)](https://github.com/AvenCores/open-antigravity-unlock/pulls)
[![GitHub issues](https://img.shields.io/github/issues/AvenCores/open-antigravity-unlock?style=for-the-badge)](https://github.com/AvenCores/open-antigravity-unlock/issues)

Опенсорс патчер для Antigravity: снимает регионные ограничения без VPN и смены региона аккаунта Google. Опенсурс аналог утилиты [Antigravity в России без VPN и смены региона аккаунта Google](https://github.com/confeden/Antigravity).

<img width="979" height="512" alt="1" src="https://github.com/user-attachments/assets/541f452c-1137-4113-bf68-e602e73b6ac5" />

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
Требуется `nuitka`:
```bash
pip install -r requirements.txt
nuitka --onefile --windows-icon-from-ico=icon.ico --windows-uac-admin main.py
```

## Структура проекта
- `main.py` — основной патчер.
- `requirements.txt` — зависимости для сборки.
- `build.txt` — пример команды сборки.
- `icon.ico` — иконка для `exe`.
- `main.exe` — готовая сборка (если присутствует в репозитории).

# 📜 Лицензия

Проект распространяется под лицензией GPL-3.0. Полный текст лицензии содержится в файле [`LICENSE`](LICENSE).

---
# 💰 Поддержать автора
+ **SBER**: `2202 2050 1464 4675`
