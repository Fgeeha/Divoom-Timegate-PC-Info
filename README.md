# Divoom-Timegate-PC-Info

Кроссплатформенный монитор ПК для пиксельных часов **Divoom Times Gate**.
Собирает телеметрию компьютера (CPU/GPU, RAM, температуры, сеть) и выводит её на 5 дисплеев часов по локальной сети — без облака Divoom.

> Управление часами идёт по локальной сети напрямую (`POST http://<ip>/post`). Облако нужно только для первичной активации устройства. Подробнее о протоколе — в [`CLAUDE.md`](./CLAUDE.md).

Поддерживаемые платформы: **Linux (Ubuntu LTS)** и **Windows 11**.

---

## Возможности

- Сбор метрик: загрузка и температура CPU/GPU, использование RAM, сетевой трафик.
- Локальный HTTP-сервер, отдающий метрики часам (динамический «интернет-текст» без экрана «Loading»).
- Авто-обнаружение IP часов в LAN либо ручная настройка.
- Готовые сборки под Linux и Windows через CI.

---

## Установка

### Из исходников (любая платформа)

Требуется Python 3.12+.

```bash
git clone https://github.com/Fgeeha/Divoom-Timegate-PC-Info.git
cd divoom-pc-monitor
pip install .
```

### Linux: системные зависимости (для температур)

```bash
sudo apt update
sudo apt install -y lm-sensors
sudo sensors-detect --auto
```

### Windows 11

Установите Python 3.12+ с python.org. Для температур/частот GPU опционально установите **LibreHardwareMonitor** и запустите его (приложение читает его данные, если доступны). Без него работают базовые метрики через `psutil`.

### Готовые сборки

При создании тега `v*` в [**GitHub Releases**](../../releases) появляются три файла:

- `divoom-pc-monitor-linux` — автономный бинарь для Ubuntu/Linux;
- `divoom-pc-monitor-windows.exe` — автономный бинарь для Windows 11;
- `divoom-pc-monitor_X.Y.Z_amd64.deb` — deb-пакет для Ubuntu/Debian.

Запуск не требует установленного Python.

#### Установка через deb (Ubuntu/Debian)

```bash
sudo dpkg -i divoom-pc-monitor_X.Y.Z_amd64.deb
# пример конфига ставится в /usr/share/divoom-pc-monitor/config.example.toml
mkdir -p ~/.divoom-pc-monitor
cp /usr/share/divoom-pc-monitor/config.example.toml ~/.divoom-pc-monitor/config.toml
```

После этого отредактируйте `~/.divoom-pc-monitor/config.toml` и запускайте:

```bash
divoom-pc-monitor --device-ip 192.168.1.182
```

---

## Настройка

Приложение ищет конфиг в следующем порядке:

1. `--config FILE` (явный путь)
2. `~/.divoom-pc-monitor/config.toml` (пользовательский конфиг, **рекомендуется**)
3. `./config.toml` (текущая директория, удобно при разработке)

Создайте конфиг в домашней директории:

```bash
mkdir -p ~/.divoom-pc-monitor
cp config.example.toml ~/.divoom-pc-monitor/config.toml
```

```toml
[device]
# IP часов в локальной сети. Оставьте пустым, чтобы включить авто-обнаружение.
ip = ""
autodiscover = true

[server]
# Адрес, на котором слушает наш сервер. Часы должны достучаться сюда по сети,
# поэтому 127.0.0.1 НЕ подойдёт — нужен LAN-адрес этой машины.
# Оставьте пустым для авто-определения LAN-IP.
listen_host = ""
listen_port = 3380

[monitor]
update_interval = 1   # период обновления метрик, секунды
```

`config.toml` и `.env` игнорируются git'ом — реальные адреса в репозиторий не попадают.

### Где взять IP часов

Способы (по приоритету разрешения адреса):

1. Флаг `--device-ip` или переменная окружения `DIVOOM_DEVICE_IP`.
2. Ключ `[device].ip` в `config.toml`.
3. Авто-обнаружение (`[device].autodiscover = true`) — запрос к Divoom возвращает устройства в вашей LAN:
   ```bash
   curl -XPOST https://app.divoom-gz.com/Device/ReturnSameLANDevice | jq
   ```
   В ответе поле `DevicePrivateIP` — это и есть адрес часов.

---

## Запуск

```bash
# из исходников
python -m divoom_pc_monitor --config config.toml

# с явным IP часов
python -m divoom_pc_monitor --device-ip 192.168.1.182

# через переменную окружения
DIVOOM_DEVICE_IP=192.168.1.182 python -m divoom_pc_monitor
```

Готовый бинарь:

```bash
./divoom-pc-monitor --device-ip 192.168.1.182        # Linux
divoom-pc-monitor-windows.exe --device-ip 192.168.1.182   # Windows
```

После старта приложение один раз раскладывает текстовые поля на дисплеях, затем часы сами периодически опрашивают локальный сервер за свежими значениями.

---

## Как это работает

```
коллекторы метрик ──▶ состояние ──▶ FastAPI  /text/{id}  ──▶ часы (GET раз в update_time)
                                  └▶ /images/*.gif (фоны)
                  divoom-клиент ──▶ POST http://<ip>/post  (разовая раскладка полей)
```

- Фон и поля задаются один раз методом `Draw/SendHttpItemList`.
- Динамические значения отдаются как «интернет-текст» (`type: 23`): часы опрашивают `/text/{id}` и берут поле `DispData` — так текст обновляется без экрана загрузки.
- Чтобы не «вешать» подсветку часов, частота запросов ограничена (`update_interval` ≥ 1 с).

---

## Разработка

```bash
pip install .[dev]
ruff check .
pytest
```


## CI/CD

GitHub Actions (`.github/workflows/build.yml`) на каждый push и pull request:

1. Матрица `ubuntu-latest` + `windows-latest`.
2. Lint (`ruff`) и тесты (`pytest`).
3. Сборка автономных бинарников (`pyinstaller`).
4. Публикация артефактов для Linux и Windows.

При создании тега `v*` (например `git tag v1.0.0 && git push origin v1.0.0`) дополнительно запускается job `release`:

5. Скачивает оба бинарника из артефактов.
6. Собирает `.deb`-пакет через `fpm` (бинарь → `/usr/bin/`, пример конфига → `/usr/share/divoom-pc-monitor/`).
7. Создаёт GitHub Release с автосгенерированными release notes и тремя файлами: Linux-бинарь, Windows-бинарь, `.deb`.

Для публикации релиза никаких дополнительных секретов не нужно — используется встроенный `GITHUB_TOKEN`.

---

## Известные ограничения

Унаследованы от прошивки Divoom Times Gate:

- Нельзя сделать шкалы прогресса — только картинка и текст.
- Выравнивание текста по центру/правому краю не работает.
- Версию прошивки узнать нельзя.
- Слишком частые запросы приводят к «зависанию» подсветки.
- Имена параметров чувствительны к опечаткам прошивки (например, фон — `BackgroudGif`).

---

## Лицензия

См. [`LICENSE`](./LICENSE).
