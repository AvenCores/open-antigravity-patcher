# 🔑 Open AG Patcher (Go Version)

Кроссплатформенная утилита для Antigravity IDE, standalone-приложения Antigravity и Antigravity CLI (`agy`), полностью переписанная на **Go (Golang)**. 

Этот проект является 1-в-1 портом оригинального скрипта на Python, но с рядом существенных преимуществ:
1. **Отсутствие зависимостей:** Не требует установленного Python или каких-либо тяжелых рантаймов.
2. **Маленький размер:** Готовый исполняемый файл занимает всего ~5-8 МБ (в отличие от громоздких PyInstaller-сборок).
3. **Безопасность и отсутствие ложных детектов:** Антивирусы не ругаются на сборку, как это часто бывает с упакованными Python-скриптами.
4. **Скорость работы:** Чтение, поиск сигнатур и упаковка/распаковка ASAR выполняются на нативной скорости скомпилированного кода.

---

## 🛠 Требования для сборки
* Установленный Go версии **1.20 или выше**.
* (Опционально) `git` для скачивания зависимостей.

---

## 🚀 Как запустить без сборки
Для запуска из исходного кода выполните в папке проекта:
```bash
go run .
```
Или с указанием кастомного пути:
```bash
go run . "C:\Program Files\Antigravity IDE"
```

---

## 🏗 Сборка под все платформы

Для автоматической сборки под все поддерживаемые системы и архитектуры используйте готовые скрипты:
* **Linux / macOS:** `./build.sh` (предварительно сделайте его исполняемым: `chmod +x build.sh`)
* **Windows:** `build.bat`

Скомпилированные файлы появятся в директории `dist/`.

### Команды ручной сборки

Если вы хотите собрать бинарный файл вручную под конкретную платформу, выполните соответствующую команду:

#### Windows
* **Windows x64 (64-bit):**
  ```bash
  GOOS=windows GOARCH=amd64 go build -ldflags="-s -w" -o dist/patcher_win_x64.exe
  ```
* **Windows x86 (32-bit):**
  ```bash
  GOOS=windows GOARCH=386 go build -ldflags="-s -w" -o dist/patcher_win_x86.exe
  ```

#### Linux
* **Linux x64 (64-bit):**
  ```bash
  GOOS=linux GOARCH=amd64 go build -ldflags="-s -w" -o dist/patcher_linux_x64
  ```
* **Linux ARM64:**
  ```bash
  GOOS=linux GOARCH=arm64 go build -ldflags="-s -w" -o dist/patcher_linux_arm64
  ```

#### macOS (OS X)
* **macOS Intel (x64):**
  ```bash
  GOOS=darwin GOARCH=amd64 go build -ldflags="-s -w" -o dist/patcher_macos_intel
  ```
* **macOS Apple Silicon (M1/M2/M3/M4, ARM64):**
  ```bash
  GOOS=darwin GOARCH=arm64 go build -ldflags="-s -w" -o dist/patcher_macos_arm64
  ```

> **Примечание по флагам:** Флаг `-ldflags="-s -w"` убирает отладочную информацию и таблицы символов DWARF, что уменьшает размер итогового файла примерно на 30-40% без потери функционала.
