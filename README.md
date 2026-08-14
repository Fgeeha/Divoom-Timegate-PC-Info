# Divoom-Timegate-PC-Info

Кроссплатформенный монитор ПК для пиксельных часов **Divoom Times Gate**.
Собирает телеметрию компьютера (CPU/GPU, RAM, температуры, сеть) и выводит её на 5 дисплеев часов по локальной сети — без облака Divoom.

> Управление часами идёт по локальной сети напрямую (`POST http://<ip>/post`). Облако нужно только для первичной активации устройства. Подробнее о протоколе — в [`CLAUDE.md`](./CLAUDE.md).

Поддерживаемые платформы: **Linux (Ubuntu LTS)** и **Windows 11**.

---

## Возможности

- Сбор метрик: загрузка и температура CPU/GPU, использование RAM, диск, uptime, load average, сетевой трафик.
- Локальный HTTP-сервер, отдающий метрики часам (динамический «интернет-текст» без экрана «Loading»).
- Текстовые шкалы загрузки (`[####------]`) для CPU/GPU/RAM/диска и уровня шума.
- Оформление: у каждого дисплея свой фон с заголовком, цветовым акцентом и разделителями.
- Погода, дата/время с учётом часового пояса, уровень шума с микрофона часов.
- Авто-обнаружение IP часов в LAN либо ручная настройка.
- Готовые сборки под Linux и Windows через CI.

---

## Что показывают дисплеи

| # | Экран | Содержимое |
|---|-------|------------|
| 0 | `SYSTEM` | CPU, GPU, RAM — значение + шкала загрузки под каждым |
| 1 | `WEATHER`| Город, температура, ощущается как, состояние, влажность, ветер, давление |
| 2 | `DETAIL` | Сеть вверх/вниз, диск + шкала, uptime, load average |
| 3 | `TIME`   | Крупные часы, дата, город, состояние погоды |
| 4 | `NOISE`  | Часы, дата, город, уровень шума с микрофона + шкала |

Раскладка задана в `src/divoom_pc_monitor/divoom/layout.py` (структура `SCREENS`),
фоны рисуются из неё же в `divoom/background.py`.

> **Про ширину текста.** Прошивка не сообщает метрики шрифтов, поэтому в
> `layout.CHAR_PX` заданы калибровочные константы «пикселей на символ». Из них
> считается лимит символов для каждого поля, и сервер обрезает строку по нему.
> Если на вашем экземпляре текст, который должен помещаться, начинает
> прокручиваться — увеличьте значение для этого шрифта; если строки уезжают за
> правый край — уменьшите.

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
ip = ""          # IP часов; пусто = авто-обнаружение
autodiscover = true
# token = ""     # DeviceToken — если в логах "DeviceToken is err" (см. ниже)

[server]
listen_host = "" # пусто = авто-определить LAN-IP
listen_port = 3380

[monitor]
update_interval = 1

[weather]
city = "Moscow"
api_key = ""     # ключ OpenWeatherMap (бесплатно на openweathermap.org)
units = "metric" # metric (°C) или imperial (°F)
update_interval = 600

[display]
timezone = "Europe/Moscow"  # IANA-имя; пусто = системное время
```

`config.toml` игнорируется git'ом — реальные IP и ключи в репозиторий не попадают.

### Где взять IP часов

Способы (по приоритету разрешения адреса):

1. Флаг `--device-ip` или переменная окружения `DIVOOM_DEVICE_IP`.
2. Ключ `[device].ip` в `config.toml`.
3. Авто-обнаружение (`[device].autodiscover = true`) — запрос к Divoom возвращает устройства в вашей LAN:
   ```bash
   curl -XPOST https://app.divoom-gz.com/Device/ReturnSameLANDevice | jq
   ```
   В ответе поле `DevicePrivateIP` — это и есть адрес часов.

### DeviceToken (если в логах `DeviceToken is err`)

Некоторые версии прошивки требуют токен аутентификации в каждом запросе.
Токен можно найти в приложении Divoom → настройки устройства, или через:

```bash
curl -s -XPOST http://<ip>/post -H 'Content-Type: application/json' \
     -d '{"Command":"Device/GetDeviceToken"}' | jq
```

Затем задайте токен в конфиге или через переменную окружения:

```toml
# ~/.divoom-pc-monitor/config.toml
[device]
token = "your_token_here"
```

```bash
# или через env
DIVOOM_DEVICE_TOKEN=your_token_here divoom-pc-monitor --device-ip 192.168.1.182
```

### Погода

Зарегистрируйтесь на [openweathermap.org](https://openweathermap.org/api) и получите бесплатный API-ключ.
Задайте его в конфиге (`[weather].api_key`) или через переменную окружения:

```bash
OPENWEATHER_API_KEY=abc123 divoom-pc-monitor --device-ip 192.168.1.182
```

Без ключа погодные поля отображаются как `--`, приложение работает в штатном режиме.

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

- Фон и поля задаются один раз методом `Draw/SendHttpItemList`. Каждый дисплей получает свой фон (`/images/bg{0..4}.gif`), сгенерированный при старте.
- Динамические значения отдаются как «интернет-текст» (`type: 23`): часы опрашивают `/text/{id}` и берут поле `DispData` — так текст обновляется без экрана загрузки.
- Чтобы не «вешать» подсветку часов, частота запросов ограничена (`update_interval` ≥ 1 с).

---

## Разработка

```bash
pip install .[dev]
ruff check .
pytest
```

---

## Автозапуск (systemd, Linux)

Создайте файл сервиса:

```bash
sudo nano /etc/systemd/system/divoom-pc-monitor.service
```

```ini
[Unit]
Description=Divoom Times Gate PC monitor
After=network.target

[Service]
ExecStart=/usr/bin/divoom-pc-monitor --device-ip 192.168.1.182
Restart=on-failure
RestartSec=5
# Секреты передавайте через окружение, не хардкодьте в файлы
Environment=OPENWEATHER_API_KEY=your_key_here
# Environment=DIVOOM_DEVICE_TOKEN=your_token_if_needed

[Install]
WantedBy=multi-user.target
```

Активация:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now divoom-pc-monitor
sudo systemctl status divoom-pc-monitor
journalctl -u divoom-pc-monitor -f   # логи в реальном времени
```

При завершении (в т.ч. по `systemctl stop`) приложение автоматически восстанавливает исходную тему часов.

---

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

- Нет элемента «шкала прогресса» — только картинка и текст, поэтому шкалы загрузки нарисованы текстом (`[####------]`).
- Цвет поля фиксируется в момент раскладки, менять его на лету нельзя: подсветка порогов (зелёный → красный) потребовала бы повторного `SendHttpItemList` с экраном «Loading». Величину показывает шкала.
- Фон меняется только вместе с раскладкой, поэтому он статичен (заголовок, акцент, разделители).
- Выравнивание текста по центру/правому краю не работает.
- Версию прошивки узнать нельзя.
- Слишком частые запросы приводят к «зависанию» подсветки.
- Имена параметров чувствительны к опечаткам прошивки (например, фон — `BackgroudGif`).

---

## Лицензия

См. [`LICENSE`](./LICENSE).
