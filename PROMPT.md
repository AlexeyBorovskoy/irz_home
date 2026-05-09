# PROJECT: IRZ_HOME_WIFI_LAB

## Цель проекта

Создать инженерный проект аудита, оптимизации и расширения домашней Wi-Fi инфраструктуры с использованием:

- TP-Link EC220-G5
- Linux Mint VM
- VSCode + Codex
- VMware Workstation
- iRZ RL22w
- Wi-Fi/LAN анализа
- последующего развертывания репитера/моста/STA+AP

Проект должен быть оформлен как полноценный инженерный репозиторий.

---

# ОСНОВНЫЕ ПРИНЦИПЫ

## Режим работы

- Только пошаговая работа
- Один шаг → проверка → следующий шаг
- Все изменения документировать
- Никаких опасных изменений без подтверждения
- Сначала аудит → потом оптимизация

---

# ВАЖНО

## ЗАПРЕЩЕНО

Без отдельного подтверждения НЕ выполнять:

- reset роутеров
- обновление firmware
- отключение DHCP
- изменение LAN IP
- bridge WAN/LAN
- включение mesh
- смену режима работы роутера
- отключение NAT
- изменение VPN маршрутов
- aggressive Wi-Fi scans
- deauth
- aircrack attacks

---

# РАБОЧАЯ ДИРЕКТОРИЯ

Использовать:

```text
/home/alexey/work/IRZ_home
ЗАДАЧА №1 — СОЗДАНИЕ СТРУКТУРЫ ПРОЕКТА

Создать инженерную структуру каталогов.

Требуемая структура
IRZ_home/
├── README.md
├── PROJECT_CONTEXT.md
├── ARCHITECTURE.md
├── NETWORK_TOPOLOGY.md
├── DECISIONS.md
├── TODO.md
├── CHANGELOG.md
├── INVENTORY.md
├── SECURITY_RULES.md
├── TEST_PLAN.md
├── AGENTS.md
│
├── docs/
│   ├── router/
│   ├── irz/
│   ├── wifi/
│   ├── vmware/
│   ├── linux/
│   ├── diagrams/
│   ├── reports/
│   └── screenshots/
│
├── configs/
│   ├── tplink/
│   ├── irz/
│   ├── linux/
│   ├── vmware/
│   └── backups/
│
├── scripts/
│   ├── audit/
│   ├── wifi/
│   ├── network/
│   ├── diagnostics/
│   └── backup/
│
├── scans/
│   ├── wifi/
│   ├── network/
│   ├── spectrum/
│   └── reports/
│
├── data/
│   ├── logs/
│   ├── captures/
│   ├── exports/
│   └── measurements/
│
├── diagrams/
│   ├── drawio/
│   ├── png/
│   └── svg/
│
├── tools/
│   ├── linux/
│   ├── windows/
│   └── firmware/
│
└── tmp/
ЗАДАЧА №2 — ИНИЦИАЛИЗАЦИЯ GIT
Требования

Создать:

git repository
.gitignore
базовые commit rules
Исключить из git
*.pcap
*.cap
*.csv
*.tar.gz
*.zip
*.img
*.bin
tmp/
data/logs/
data/captures/
ЗАДАЧА №3 — СОЗДАНИЕ БАЗОВОЙ ДОКУМЕНТАЦИИ

Сгенерировать:

README.md

Должен содержать:

назначение проекта
архитектуру
оборудование
цели
ограничения
этапы
PROJECT_CONTEXT.md

Описать:

текущую инфраструктуру
Windows host
Linux Mint VM
VMware
TP-Link EC220-G5
iRZ RL22w
VPN
планы по repeater/WDS
NETWORK_TOPOLOGY.md

Создать ASCII схемы:

Текущая
Internet
   │
TP-Link EC220-G5
   │
Windows Host
   │
VMware
   │
Linux Mint VM
Планируемая
Internet
   │
TP-Link
   )))))
iRZ RL22w
   │
Extended Wi-Fi Zone
SECURITY_RULES.md

Описать:

read-only first
rollback before changes
backup configs
no destructive scans
no firmware flashing without approval
ЗАДАЧА №4 — ИНВЕНТАРИЗАЦИЯ

Создать INVENTORY.md.

Зафиксировать:

TP-Link EC220-G5
модель
firmware
LAN IP
DHCP pool
Wi-Fi modes
channels
Linux VM
distro
kernel
network interfaces
VMware mode
iRZ RL22w

Пока создать placeholder section.

ЗАДАЧА №5 — АУДИТ СЕТИ

Создать scripts/audit/basic_audit.sh

Скрипт должен выполнять:

ip addr
ip route
nmcli dev status
nmcli dev wifi list
resolvectl status
arp -a
ping gateway
traceroute 8.8.8.8

Результаты сохранять:

data/logs/
ЗАДАЧА №6 — АУДИТ WIFI

Создать:

scripts/wifi/wifi_scan.sh

Сбор:

SSID
BSSID
RSSI
Channel
Security
Band

Использовать:

nmcli
iw
iwlist
ЗАДАЧА №7 — АНАЛИЗ TP-LINK

На основании скриншотов сформировать:

docs/router/TP_LINK_AUDIT.md

Включить:

DHCP analysis
channel analysis
mixed mode risks
WPS risks
DFS discussion
Smart Connect analysis
optimization recommendations
ЗАДАЧА №8 — ПОДГОТОВКА К РАБОТЕ С IRZ

Создать:

docs/irz/IRZ_REPEATER_PLAN.md

Проанализировать:

repeater mode
WDS bridge
STA+AP
throughput loss
roaming behavior
compatibility with TP-Link
ЗАДАЧА №9 — ДИАГРАММЫ

Создать:

ASCII схемы
draw.io placeholders
markdown diagrams
ЗАДАЧА №10 — ИНЖЕНЕРНЫЙ СТИЛЬ

Все документы:

строгий инженерный стиль
markdown
таблицы
схемы
риски
rollback
conclusions
РЕЖИМ РАБОТЫ CODEX
ОБЯЗАТЕЛЬНО

После каждого шага:

Показать:
что создано
какие файлы
какие команды
Ждать подтверждения.
ПЕРВЫЙ ШАГ

Сейчас:

Создать структуру каталогов
Инициализировать git
Создать:
README.md
PROJECT_CONTEXT.md
.gitignore
Показать результаты
Остановиться и ждать подтверждения