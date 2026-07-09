# macOS Release: установка и восстановление после чёрного окна

Этот fork публикует `universal2`-бинарник Open AG Patcher для Intel и Apple Silicon. История и авторство исходного проекта сохранены через fork от [AvenCores/open-antigravity-patcher](https://github.com/AvenCores/open-antigravity-patcher).

Скачивайте `Open_AG_Patcher_macOS-universal2.zip` со [страницы последнего release](https://github.com/coneldiablo/open-antigravity-patcher/releases/latest).

## Первый запуск

Закройте Antigravity. В Terminal выполните:

```bash
cd ~/Downloads
unzip Open_AG_Patcher_macOS-universal2.zip
xattr -dr com.apple.quarantine Open_AG_Patcher_macOS
chmod +x Open_AG_Patcher_macOS
sudo ./Open_AG_Patcher_macOS
```

Для standalone-приложения `/Applications/Antigravity.app` используйте `PATCH -> 2`.

Для `Antigravity IDE.app` используйте `PATCH -> 1`.

## Если после старого патча открылось чёрное окно

Старые macOS-сборки использовали локальный HTTP proxy. Текущий патчер использует HTTPS proxy с обработкой сертификата и адресов `localhost`/`127.0.0.1`.

1. Полностью закройте Antigravity.
2. Запустите текущий патчер через `sudo`.
3. Выберите `RESTORE -> 5` для standalone `Antigravity.app`.
4. Подтвердите восстановление из `app.asar.bak`.
5. После завершения снова выберите `PATCH -> 2`.

Это заново применит патч к оригинальному `app.asar`, а не поверх старой HTTP-инъекции.

Если `app.asar.bak` отсутствует, переустановите Antigravity перед применением нового патча. Без оригинального архива патчер не должен пытаться угадать, как восстановить старую модификацию.

## Если macOS не даёт записать или открыть приложение

Для `Operation not permitted` включите полный доступ к диску для Terminal:

```text
System Settings -> Privacy & Security -> Full Disk Access -> Terminal
```

После изменения разрешения полностью закройте Terminal, откройте его снова и повторите запуск.

Проверить подпись приложения после патча можно так:

```bash
codesign -dv /Applications/Antigravity.app 2>&1 | grep Signature
```

Ожидаемый вывод:

```text
Signature=adhoc
```

## Если чёрное окно осталось

Запустите приложение из Terminal с диагностическими логами и приложите вывод вместе с версией Antigravity:

```bash
pkill -f Antigravity
AG_DEBUG=1 /Applications/Antigravity.app/Contents/MacOS/Antigravity
```
