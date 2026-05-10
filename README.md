# IRZ Home Wi-Fi Lab

Домашняя лаборатория для аудита и настройки Wi-Fi инфраструктуры. Основная задача — настройка iRZ RL22w в качестве беспроводного репитера для расширения зоны покрытия сети TP-Link EC220-G5.

---

## Топология сети

```
Интернет (провайдер, ~100 Мбит/с)
  │
  └── TP-Link EC220-G5 (основной роутер)
        │   LAN: 192.168.0.1
        │   Wi-Fi 2.4GHz: TP-Link_828C (канал 6, 802.11n HT20)
        │   Wi-Fi 5GHz:   TP-Link_828C_5G (802.11ac)
        │
        └── [Wi-Fi 2.4GHz STA] iRZ RL22w (репитер)
              │   wlan0 (STA): 192.168.0.200  →  шлюз 192.168.0.1
              │   wlan0-1 (AP): iRZ-034D61 (канал 6, 802.11n HT20)
              │   br-lan: 192.168.1.1  |  NAT: iptables MASQUERADE
              │
              ├── [USB-Ethernet] Linux VM   192.168.1.100
              └── [Wi-Fi AP]    Мобильные   192.168.1.100–249
```

---

## Оборудование

### TP-Link EC220-G5 (основной роутер)

| Параметр       | Значение                                      |
|----------------|-----------------------------------------------|
| Модель         | EC220-G5 v2                                   |
| Firmware       | 3.16.0.0.9.1 v6055.0 Build 220707 Rel.16116n  |
| LAN IP         | 192.168.0.1                                   |
| LAN MAC        | 5C:62:8B:4D:82:8C                             |
| DHCP pool      | 192.168.0.100 – 192.168.0.199                 |
| WAN            | IPoE (Dynamic IP), CGNAT                      |
| Wi-Fi 2.4GHz   | SSID: TP-Link_828C, 802.11n, канал 6, HT20    |
| Wi-Fi 5GHz     | SSID: TP-Link_828C_5G, 802.11ac               |
| Web UI         | http://192.168.0.1/                           |

### iRZ RL22w (беспроводной репитер)

| Параметр       | Значение                                      |
|----------------|-----------------------------------------------|
| Модель         | iRZ RL22w (irz_mt02)                          |
| ОС             | OpenWrt 19.07.0 (kernel 4.14.162)             |
| CPU            | MIPS 24KEc @ 580 MHz                          |
| RAM / Flash    | 64 MB / 16 MB                                 |
| Wi-Fi          | 1× 2.4GHz (rt2800, 802.11n)                   |
| LTE            | QUECTEL EC25 (SIM1/SIM2, не используется)     |
| LAN IP         | 192.168.1.1                                   |
| LAN MAC        | f0:81:af:03:4d:5d                             |
| Web UI         | http://192.168.1.1/                           |
| API            | http://192.168.1.1/api/*                      |

---

## Конфигурация iRZ как Wi-Fi репитера

### Режим STA+AP (один 2.4GHz радиомодуль)

iRZ RL22w настроен для работы на одном 2.4GHz радиомодуле в двух режимах одновременно:

- **wlan0 (STA)** — подключается к `TP-Link_828C` как клиент, получает IP `192.168.0.200`
- **wlan0-1 (AP)** — раздаёт сеть `iRZ-034D61` для мобильных устройств и VM

Оба интерфейса работают на канале 6, настроенном вручную для стабильности.

### UCI-конфигурация на iRZ (OpenWrt)

```
/etc/config/wireless   — wlan0 (STA→TP-Link) + wlan0-1 (AP для клиентов)
/etc/config/network    — lan: br-lan 192.168.1.1 | sta: static 192.168.0.200/24
/etc/config/firewall   — wan zone = sta, masq=1; forwarding lan→wan
/etc/config/dhcp       — dnsmasq на br-lan, upstream 8.8.8.8/8.8.4.4/1.1.1.1, кэш 1000
```

### Маршрутизация и NAT (применяется автоматически через hotplug)

```bash
ip addr add 192.168.0.200/24 dev wlan0
ip route replace default via 192.168.0.1 dev wlan0
iptables -t nat -A POSTROUTING -o wlan0 -j MASQUERADE
iptables -A FORWARD -i br-lan -o wlan0 -j ACCEPT
iptables -A FORWARD -i wlan0 -o br-lan -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
echo 1 > /proc/sys/net/ipv4/ip_forward
```

---

## Автовосстановление при потере питания

Все настройки сохраняются в UCI (OverlayFS) и восстанавливаются автоматически при перезагрузке. Дополнительные механизмы надёжности:

| Механизм | Файл на iRZ | Когда срабатывает |
|----------|-------------|-------------------|
| **Hotplug-скрипт** | `/etc/hotplug.d/iface/30-sta-internet` | При поднятии интерфейса `sta` |
| **Firewall backup** | `/etc/firewall.user` | При каждом перезапуске fw3 |
| **Watchdog** | `/usr/bin/repeater-watchdog` | Каждые 3 мин (cron) |

Watchdog: при 3 последовательных неудачах `ping -c 1 -W 5 -I wlan0 8.8.8.8` — выполняет `wifi down && wifi up`. Hotplug затем автоматически восстанавливает IP, маршрут и iptables.

---

## Производительность

> ⚠️ Ограничение одного радиомодуля: STA и AP делят один 2.4GHz канал (half-duplex). Реальная пропускная способность — примерно вдвое ниже прямого подключения к TP-Link.

| Метрика | Значение |
|---------|----------|
| Wi-Fi сигнал STA→TP-Link | −54 dBm |
| Wi-Fi bitrate (burst RX) | до 130 Мбит/с (MCS 14, short GI) |
| Реальная скорость загрузки | ~0.5 Мбит/с (при активном SSH-трафике) |
| Ping до 8.8.8.8 | 7–18 мс |
| Ping до TP-Link GW | 2–10 мс |
| Android connectivity check | HTTP 204 OK |

---

## Структура проекта

```
IRZ_home/
├── README.md                              # этот файл
├── INVENTORY.md                           # полная инвентаризация устройств
│
├── configs/
│   ├── irz/                               # UCI-конфиги iRZ (placeholder, собраны через API)
│   └── tplink/
│       └── upnp_data.json                 # данные UPnP SOAP-опроса TP-Link
│
├── docs/
│   ├── irz/
│   │   ├── IRZ_AUDIT.md                   # полный аудит iRZ (2026-05-09)
│   │   └── R2_UserGuide_RU.pdf            # руководство пользователя iRZ R2
│   └── router/
│       ├── EC220-G5_agent_automation.md   # план API-автоматизации TP-Link
│       ├── TPLINK_READONLY_TEST_PLAN.md   # план тестирования (только чтение)
│       └── screenshots/                   # 21 скриншот web UI TP-Link (аудит 2026-05-10)
│
└── scripts/
    └── audit/
        └── tplink_gdpr_auth.py            # аутентификация и сбор данных TP-Link GDPR-прошивки
```

---

## Безопасность

- **`env.md`** — Wi-Fi пароли и PIN роутера. Добавлен в `.gitignore`, **не в репозитории**.
- **Скрипты** — PIN читается из переменной окружения `ROUTER_PIN`.
- **Документация** — пароли заменены на `[скрыт — см. env.md]`.

```bash
# Запуск скрипта аудита TP-Link:
export ROUTER_PIN="ВАШ_PIN"
python3 scripts/audit/tplink_gdpr_auth.py
```

---

## Аудит

| Устройство | Дата | Метод | Документ |
|------------|------|-------|----------|
| iRZ RL22w | 2026-05-09 | USB-Ethernet → REST API | [docs/irz/IRZ_AUDIT.md](docs/irz/IRZ_AUDIT.md) |
| TP-Link EC220-G5 | 2026-05-10 | Web UI (21 скриншот) | [docs/router/screenshots/](docs/router/screenshots/) |

---

## Выявленные проблемы

| № | Устройство | Проблема | Статус |
|---|-----------|---------|--------|
| 1 | iRZ | APN не настроен — LTE не работает | Открыто (LTE не нужен в текущей конфигурации) |
| 2 | iRZ | Часовой пояс GMT вместо Europe/Moscow | Открыто |
| 3 | iRZ | Пароль root слабый (по умолчанию) | Открыто |
| 4 | Сеть | Single-radio STA+AP: пропускная способность ~50% от прямого подключения | Аппаратное ограничение |

---

## Требования к окружению

- Linux VM (VMware Workstation) с USB-Ethernet адаптером (прямой доступ к iRZ LAN 192.168.1.x)
- Python 3.x + `pycryptodome`, `requests` (для скриптов аудита TP-Link)
- SSH-доступ к iRZ (root, порт 22)
