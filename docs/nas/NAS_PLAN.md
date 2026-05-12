# NAS Plan: Jetson Nano + 1TB HDD

> Дата планирования: 2026-05-12
> Статус: **Планирование** — к реализации

---

## Оборудование

| Устройство        | Характеристики                                      |
|-------------------|-----------------------------------------------------|
| Jetson Nano       | ARM Cortex-A57, 128-core Maxwell GPU, 4GB LPDDR4   |
| HDD               | 1 ТБ, внешний блок питания                         |
| Подключение HDD   | USB 3.0                                             |
| Питание Jetson    | 5V/4A barrel jack (не micro-USB)                   |
| Текущий доступ    | SSH через USB Ethernet (192.168.55.1) с ноутбука   |

---

## Целевая архитектура сети

```
Интернет
  └── TP-Link EC220-G5 (192.168.0.1) — DHCP-сервер
        ├── Wi-Fi клиенты (192.168.0.x)
        ├── [патчкорд LAN→LAN] → iRZ RL22w (192.168.0.2, dumb AP)
        │     ├── Wi-Fi AP: iRZ-034D61 (клиенты получают IP от TP-Link)
        │     └── LAN → Jetson Nano (192.168.0.50, static)
        │                 └── USB 3.0 → 1TB HDD (/mnt/nas/)
        │                       ├── Samba  (порт 445)
        │                       ├── NFS    (порт 2049)
        │                       ├── Nextcloud (порт 8080)
        │                       └── Jellyfin  (порт 8096)
        └── Linux Mint VM (192.168.238.128 / VMware NAT)
```

---

## Структура HDD

```
/mnt/nas/
  shared/      ← общий диск (Samba + NFS)
  media/       ← медиатека (Jellyfin)
  nextcloud/   ← данные Nextcloud
  docker/      ← Docker volumes
```

---

## План реализации

### Фаза 0 — Инвентаризация Jetson
- [ ] Подключиться по SSH (192.168.55.1 или через VMware USB passthrough)
- [ ] Проверить версию JetPack / Ubuntu
- [ ] Проверить видимость HDD (`lsblk`)
- [ ] Оценить текущее состояние SD-карты

### Фаза 1 — Переключить iRZ в режим dumb AP
- [ ] Отключить DHCP сервер iRZ
- [ ] Убрать NAT/MASQUERADE и firewall.user правила
- [ ] Убрать watchdog cron и hotplug-скрипт STA
- [ ] Отключить STA-интерфейс (wlan0)
- [ ] Подключить TP-Link LAN → iRZ LAN (не WAN-порт!)
- [ ] Назначить iRZ статический IP 192.168.0.2 из сети TP-Link
- [ ] Проверить: Wi-Fi клиенты iRZ получают IP от TP-Link

### Фаза 2 — Подключить Jetson к сети
- [ ] Ethernet: Jetson → LAN порт iRZ
- [ ] Назначить статический IP 192.168.0.50 на Jetson
- [ ] DHCP reservation на TP-Link по MAC Jetson
- [ ] Настроить avahi (mDNS): hostname `nas.local`
- [ ] Проверить SSH с других устройств сети

### Фаза 3 — Подготовить HDD
- [ ] Форматировать в ext4 (полная очистка)
- [ ] Auto-mount через `/etc/fstab` по UUID
- [ ] Создать структуру директорий `/mnt/nas/`
- [ ] Проверить права доступа

### Фаза 4 — Samba
- [ ] Установить samba
- [ ] Настроить шары: `shared` (rw), `media` (rw)
- [ ] Создать пользователя samba
- [ ] Проверить доступ с Windows и Android

### Фаза 5 — NFS
- [ ] Установить nfs-kernel-server
- [ ] Экспорт `/mnt/nas/shared`
- [ ] Проверить монтирование с Linux Mint VM

### Фаза 6 — Docker
- [ ] Установить Docker (ARM64, совместимый с JetPack)
- [ ] Перенести `data-root` в `/mnt/nas/docker`
- [ ] Проверить работу контейнеров

### Фаза 7 — Nextcloud
- [ ] Docker Compose: Nextcloud + MariaDB + Redis
- [ ] Data volume → `/mnt/nas/nextcloud`
- [ ] Порт 8080, доступ `http://192.168.0.50:8080`
- [ ] Настроить мобильное приложение

### Фаза 8 — Jellyfin
- [ ] Docker с GPU passthrough (Jetson NVENC)
- [ ] Media volume → `/mnt/nas/media`
- [ ] Порт 8096, доступ `http://192.168.0.50:8096`
- [ ] Проверить аппаратное транскодирование

### Фаза 9 — Финализация
- [ ] Автозапуск всех сервисов (systemd)
- [ ] Проверить восстановление после перезагрузки
- [ ] Обновить INVENTORY.md
- [ ] Зафиксировать конфиги в git

---

## Сервисы и порты

| Сервис     | Порт  | URL                            |
|------------|-------|--------------------------------|
| Samba      | 445   | `\\192.168.0.50\shared`        |
| NFS        | 2049  | `192.168.0.50:/mnt/nas/shared` |
| Nextcloud  | 8080  | `http://192.168.0.50:8080`     |
| Jellyfin   | 8096  | `http://192.168.0.50:8096`     |
| SSH Jetson | 22    | `ssh user@192.168.0.50`        |

---

## Известные ограничения

- Jetson Nano: один USB-контроллер на все 4 порта — HDD занимает пропускную способность
- Jellyfin GPU passthrough: требует правильной версии JetPack и Docker с NVIDIA runtime
- iRZ в dumb AP режиме теряет функцию LTE-резерва (APN и так не настроен)
