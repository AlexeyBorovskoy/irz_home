# TP-Link EC220-G5 — План тестирования (только чтение)

> Цель: собрать полную картину конфигурации TP-Link без каких-либо изменений.  
> Создан: 2026-05-09 | Статус: готов к выполнению

---

## Предусловия

| Условие | Проверка |
|---|---|
| TP-Link доступен | `curl -s -o /dev/null -w "%{http_code}" http://192.168.0.1/` → 200 |
| Firefox закрыт | Роутер держит **только 1 сессию** — открытый браузер вытесняет скрипт |
| tplinkrouterc6u установлен | `pip install tplinkrouterc6u` |
| Директории созданы | `configs/tplink/`, `docs/router/` |

### Подготовка окружения
```bash
# Установить библиотеку
pip install tplinkrouterc6u

# Проверить доступность роутера
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://192.168.0.1/

# Закрыть все сессии Firefox перед запуском
# (или подождать ~10 минут пока сессия истечёт сама)
```

---

## Фаза 1 — Проверка подключения

**Цель:** убедиться что роутер отвечает и путь сети работает.

```bash
# Пинг через NAT (ens33 → 192.168.238.2 → 192.168.0.1)
ping -c 4 192.168.0.1

# HTTP доступность
curl -v http://192.168.0.1/ 2>&1 | head -30

# Проверка через какой интерфейс идёт трафик
ip route get 192.168.0.1
```

**Ожидаемый результат:** пинг проходит, HTTP 200, маршрут через ens33.

---

## Фаза 2 — Тест библиотеки tplinkrouterc6u

**Цель:** автоматическая авторизация через AES+RSA, сбор данных без ручного перехвата токенов.

### Шаг 2.1 — Автоопределение класса роутера

```python
from tplinkrouterc6u import TplinkRouterProvider

router = TplinkRouterProvider.get_client("http://192.168.0.1", "80276760")
router.authorize()
fw = router.get_firmware()
print(fw)
router.logout()
```

EC220-G5 — ISP-кастомизированная версия, автоопределение может не сработать.

### Шаг 2.2 — Перебор классов вручную

```python
from tplinkrouterc6u import (
    TplinkRouter, TPLinkMRClient, TPLinkMRClientGCM, TPLinkEXClient, TPLinkEXClientGCM
)

for Cls in [TplinkRouter, TPLinkMRClient, TPLinkMRClientGCM, TPLinkEXClient, TPLinkEXClientGCM]:
    try:
        r = Cls("http://192.168.0.1", "80276760")
        r.authorize()
        print(f"УСПЕХ: {Cls.__name__}")
        r.logout()
        break
    except Exception as e:
        print(f"  {Cls.__name__}: {e}")
```

**Критерий успеха:** хотя бы один класс выполняет `authorize()` без исключения.

---

## Фаза 3 — Сбор данных (только чтение)

**Запустить:** `python3 scripts/audit/tplink_readonly_audit.py`

Скрипт собирает (только GET/load операции):

| Данные | Метод | Файл вывода |
|---|---|---|
| Версия прошивки | `get_firmware()` | configs/tplink/firmware.json |
| Статус Wi-Fi 2.4G/5G | `get_status()` | configs/tplink/status.json |
| Подключённые устройства | `status.devices` | configs/tplink/devices.json |
| DHCP аренды | `get_ipv4_dhcp_leases()` | configs/tplink/dhcp_leases.json |
| DHCP резервирования | `get_ipv4_reservations()` | configs/tplink/dhcp_reservations.json |

### Данные уже известны (из /cgi?1 в предыдущей сессии)

| Параметр | Значение |
|---|---|
| Модель | EC220-G5 |
| Версия ПО | 3.16.0 0.9.1 Build 220707 |
| MAC (Flash) | 5C:62:8B:4D:82:8C |
| DNS серверы | 94.19.255.4, 93.100.1.4 |
| CPU | 2% |
| RAM | 58564 KB total / 33388 KB free (~57% свободно) |
| Время системы | 2026-05-09T17:26:58+03:00 |

---

## Фаза 4 — Резервная копия конфигурации

**Цель:** скачать `config.bin` для офлайн-анализа.

```bash
# Автоматически через скрипт (использует stok из библиотеки):
python3 scripts/audit/tplink_readonly_audit.py --backup

# Или вручную через браузер:
# http://192.168.0.1 → Дополнительно → Системные инструменты → Резервная копия
```

Файл сохраняется в `configs/tplink/config_YYYYMMDD_HHMMSS.bin`.

---

## Фаза 5 — Декодирование config.bin → XML

**Цель:** получить полную конфигурацию роутера в читаемом виде (SSID, пароли, WAN, DHCP, firewall).

```bash
# Скачать утилиту (один раз)
wget -q https://raw.githubusercontent.com/sta-c0000/tpconf_bin_xml/master/tpconf_bin_xml.py \
  -O tools/tpconf_bin_xml.py

# Декодировать
python3 tools/tpconf_bin_xml.py configs/tplink/config_*.bin configs/tplink/config_decoded.xml

# Просмотр
grep -i "ssid\|channel\|passwd\|dhcp\|wan" configs/tplink/config_decoded.xml | head -50
```

**Что ожидаем найти в XML:**
- SSID и пароли Wi-Fi (2.4G и 5G)
- Номера каналов → можно сравнить с iRZ (канал 11, 2.4GHz)
- WAN параметры (PPPoE / DHCP / Static)
- DHCP пул и резервирования IP
- Пользователи системы

---

## Фаза 6 — Сравнительный анализ каналов

После получения каналов TP-Link:

| Устройство | Диапазон | Канал | Ширина |
|---|---|---|---|
| iRZ RL22w | 2.4 GHz | **11** | HT20 |
| TP-Link 2.4G | 2.4 GHz | **TBD** | TBD |
| TP-Link 5G | 5 GHz | TBD | TBD |

**Риск конфликта:** если TP-Link тоже на канале 11 (2.4G) — интерференция гарантирована.  
**Решение:** разнести каналы (1/6/11 в 2.4G — единственные неперекрывающиеся).

---

## Результирующие артефакты

По окончании аудита должны быть созданы:

```
configs/tplink/
├── firmware.json
├── status.json
├── devices.json
├── dhcp_leases.json
├── dhcp_reservations.json
├── config_YYYYMMDD.bin
└── config_decoded.xml

docs/router/
└── TP_LINK_AUDIT.md    ← сводный отчёт
```

---

## Ограничения и риски

| Риск | Вероятность | Митигация |
|---|---|---|
| Библиотека не поддерживает EC220-G5 | Высокая | Перебор классов → fallback на /cgi?1 |
| Сессия вытесняется Firefox | Высокая | Закрыть Firefox перед запуском |
| config.bin путь не стандартный | Средняя | Пробуем 3 URL из automation doc |
| Токен истекает за время сбора | Низкая | Скрипт авторизуется один раз и работает быстро |

---

## Следующий шаг после аудита

1. Заполнить `INVENTORY.md` — раздел TP-Link (firmware, каналы, DHCP пул)
2. Принять решение о канале iRZ (разнести с TP-Link)
3. Принять решение о режиме iRZ: AP / STA+AP / WDS
4. Настроить APN на iRZ для LTE
