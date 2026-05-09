# TP-Link EC220-G5 — Документация для автоматизации через агент/терминал

## Содержание
1. [Технические параметры роутера](#1-технические-параметры-роутера)
2. [Как работает аутентификация](#2-как-работает-аутентификация)
3. [Метод 1 — Python библиотека tplinkrouterc6u](#3-метод-1--python-библиотека-tplinkrouterc6u)
4. [Метод 2 — Прямые HTTP запросы через curl](#4-метод-2--прямые-http-запросы-через-curl)
5. [Резервное копирование конфигурации](#5-резервное-копирование-конфигурации)
6. [Декодирование файла резервной копии conf.bin](#6-декодирование-файла-резервной-копии-confbin)
7. [Полный скрипт автоматизации](#7-полный-скрипт-автоматизации)
8. [Что агент может сделать](#8-что-агент-может-сделать)
9. [Известные проблемы](#9-известные-проблемы)

---

## 1. Технические параметры роутера

| Параметр | Значение |
|---|---|
| Модель | TP-Link EC220-G5 (ISP-customized версия) |
| Web-интерфейс | http://192.168.0.1 или http://tplinkwifi.net |
| Логин по умолчанию | admin / admin |
| LAN IP | 192.168.0.1 / 255.255.255.0 |
| WAN интерфейс | eth0.2 |
| CPU | MIPS 24KEc @ 580 MHz |
| RAM | 64 MB DDR |
| Flash | 8 MB SPI (W25Q64BV) |
| Wi-Fi 2.4G чип | Ralink MT7620 |
| Wi-Fi 5G чип | Ralink MT76x2 |
| Switch | Realtek RTL8367C |
| ОС | Linux 3.10.14 |
| TR-069 порт | 7547 (TCP) |
| Поддерживаемые протоколы | TR-069, TR-181, TR-111, TR-143 |

---

## 2. Как работает аутентификация

### Важно: роутер поддерживает только 1 активную сессию одновременно

EC220-G5 как ISP-роутер использует **шифрование AES** для передачи пароля. Процесс входа:

1. GET `/` — роутер возвращает RSA публичный ключ и sequence number
2. Пароль шифруется AES, подписывается RSA
3. POST `/cgi-bin/luci/;stok=/login?form=login` с зашифрованными данными
4. Роутер возвращает `stok` — токен сессии
5. Все последующие запросы используют `stok` в URL

Структура URL после авторизации:
```
http://192.168.0.1/cgi-bin/luci/;stok=<ТОКЕН>/...
```

### Перехват запросов из браузера (для отладки)
Открой DevTools → Network в браузере при входе в роутер и выполни в консоли:
```javascript
$.Iencryptor.AESDecrypt = function(data) {
    let d = $.Iencryptor.AESDecrypt_backup(data);
    console.log("RECV:\n" + d);
    return d;
}
$.Iencryptor.AESEncrypt = function(data) {
    console.log("SEND:\n" + data);
    return $.Iencryptor.AESEncrypt_backup(data);
}
```
Это покажет расшифрованные запросы/ответы в консоли.

---

## 3. Метод 1 — Python библиотека tplinkrouterc6u

Это **самый простой способ** — готовая библиотека с поддержкой множества TP-Link роутеров.

### Установка
```bash
pip install tplinkrouterc6u
```

### Базовое использование
```python
from tplinkrouterc6u import TplinkRouterProvider, Connection
from logging import Logger

ROUTER_IP = "http://192.168.0.1"
PASSWORD = "твой_пароль"

# Автоопределение типа роутера
router = TplinkRouterProvider.get_client(ROUTER_IP, PASSWORD)

try:
    router.authorize()

    # Получить информацию о прошивке
    firmware = router.get_firmware()
    print(f"Firmware: {firmware}")

    # Получить статус
    status = router.get_status()
    print(f"Wi-Fi 2.4G: {status.wifi_2g_enable}")
    print(f"Wi-Fi 5G:   {status.wifi_5g_enable}")
    print(f"Гостевой 2.4G: {status.guest_2g_enable}")
    print(f"Клиентов: {len(status.devices)}")

    # Список подключённых устройств
    for device in status.devices:
        print(f"  {device.macaddr}  {device.hostname}")

    # DHCP аренды
    leases = router.get_ipv4_dhcp_leases()
    for lease in leases:
        print(f"  {lease.macaddr}  {lease.ipaddr:16s}  {lease.hostname}")

    # Статические IP (резервирования)
    reservations = router.get_ipv4_reservations()
    for r in reservations:
        print(f"  {r.macaddr}  {r.ipaddr:16s}  {r.hostname}")

    # Управление Wi-Fi
    router.set_wifi(Connection.HOST_2G, True)   # включить 2.4G
    router.set_wifi(Connection.HOST_5G, True)   # включить 5G
    router.set_wifi(Connection.GUEST_2G, False) # выключить гостевой 2.4G

finally:
    router.logout()
```

### Если автоопределение не работает — попробуй классы напрямую
```python
from tplinkrouterc6u import (
    TplinkRouter,          # стандартный Archer
    TPLinkMRClient,        # MR серия, старая прошивка AES CBC
    TPLinkMRClientGCM,     # MR серия, новая прошивка AES GCM
    TPLinkEXClient,        # EX серия, старая прошивка
    TPLinkEXClientGCM,     # EX серия, новая прошивка
    TplinkC1200Router,     # C1200
)

# Попробуй по очереди пока не сработает:
for ClientClass in [TplinkRouter, TPLinkMRClient, TPLinkMRClientGCM, TPLinkEXClient]:
    try:
        router = ClientClass("http://192.168.0.1", "пароль")
        router.authorize()
        print(f"Успех с классом: {ClientClass.__name__}")
        break
    except Exception as e:
        print(f"Не подошёл {ClientClass.__name__}: {e}")
```

### Доступные функции библиотеки

| Функция | Описание | Возвращает |
|---|---|---|
| `get_firmware()` | Версия прошивки | Firmware |
| `get_status()` | Статус и список клиентов | Status |
| `get_ipv4_dhcp_leases()` | DHCP аренды | list[DhcpLease] |
| `get_ipv4_reservations()` | Статические IP | list[IPv4Reservation] |
| `set_wifi(conn, enable)` | Вкл/выкл Wi-Fi | bool |
| `reboot()` | Перезагрузить роутер | — |

---

## 4. Метод 2 — Прямые HTTP запросы через curl

Если библиотека не работает, используй прямые запросы.

### Шаг 1 — Проверить доступность
```bash
curl -s -o /dev/null -w "%{http_code}" http://192.168.0.1/
# Ожидается: 200
```

### Шаг 2 — Получить stok токен вручную через браузер

Зайди в роутер через браузер, открой DevTools → Application → Cookies → найди `sysauth` или посмотри URL в адресной строке после входа — там будет `stok=XXXXXX`.

Или перехвати POST запрос входа в DevTools → Network и скопируй `stok` из ответа.

### Шаг 3 — Использовать stok для запросов
```bash
STOK="вставь_свой_токен_сюда"
BASE="http://192.168.0.1/cgi-bin/luci/;stok=${STOK}"

# Получить список клиентов
curl -s "${BASE}/admin/wireless?form=ap_vm_client_list" \
  -d "operation=load"

# Получить DHCP настройки
curl -s "${BASE}/admin/dhcps?form=dhcp_settings" \
  -d "operation=load"

# Получить WAN статус
curl -s "${BASE}/admin/status?form=wan_status" \
  -d "operation=load"
```

### Скрипт получения stok через Python (с шифрованием)
```python
import requests
import hashlib
import json

def get_stok(ip, password):
    """
    Упрощённая авторизация для роутеров без RSA шифрования.
    Если не работает — используй библиотеку tplinkrouterc6u.
    """
    session = requests.Session()
    
    # MD5 хеш пароля (используется в некоторых моделях)
    pwd_md5 = hashlib.md5(password.encode()).hexdigest()
    
    url = f"http://{ip}/cgi-bin/luci/;stok=/login?form=login"
    data = {
        "operation": "login",
        "username": "admin",
        "password": pwd_md5
    }
    
    resp = session.post(url, data=data, timeout=10)
    result = resp.json()
    
    if result.get("success"):
        return result["data"]["stok"], session
    else:
        raise Exception(f"Ошибка авторизации: {result}")
```

---

## 5. Резервное копирование конфигурации

### Через web-интерфейс (ручной способ)
```
http://192.168.0.1 → Advanced → System Tools → Backup & Restore → Backup
```
Скачивается файл `config.bin` — зашифрованный бинарный файл конфигурации.

### Через curl (автоматический способ)
```bash
STOK="твой_токен"

# Скачать резервную копию
curl -s "http://192.168.0.1/cgi-bin/luci/;stok=${STOK}/admin/syslog?form=pcm" \
  -d "operation=load" \
  -o "backup_$(date +%Y%m%d_%H%M%S).bin"
```

Или стандартный путь для ISP роутеров TP-Link:
```bash
curl -s "http://192.168.0.1/cgi-bin/luci/;stok=${STOK}/admin/firmware?form=backup" \
  -d "operation=backup" \
  -o config_backup.bin
```

### Через Python (полный скрипт бэкапа)
```python
import requests
from datetime import datetime

def backup_router_config(ip, stok, output_dir="./backups"):
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    session = requests.Session()
    filename = f"{output_dir}/ec220g5_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bin"
    
    # Попробуй разные пути — зависит от прошивки
    backup_urls = [
        f"http://{ip}/cgi-bin/luci/;stok={stok}/admin/firmware?form=backup",
        f"http://{ip}/cgi-bin/luci/;stok={stok}/admin/syslog?form=pcm",
        f"http://{ip}/cgi-bin/luci/;stok={stok}/admin/system?form=backup",
    ]
    
    for url in backup_urls:
        resp = session.post(url, data={"operation": "backup"}, stream=True)
        if resp.status_code == 200 and len(resp.content) > 100:
            with open(filename, "wb") as f:
                f.write(resp.content)
            print(f"Бэкап сохранён: {filename} ({len(resp.content)} байт)")
            return filename
    
    raise Exception("Не удалось скачать бэкап ни по одному из путей")
```

### Восстановление из бэкапа
```bash
STOK="токен"
curl -s "http://192.168.0.1/cgi-bin/luci/;stok=${STOK}/admin/firmware?form=restore" \
  -F "operation=restore" \
  -F "filename=@config_backup.bin"
```

---

## 6. Декодирование файла резервной копии conf.bin

Файл `config.bin` зашифрован DES. Для его чтения и редактирования используй утилиту **tpconf_bin_xml**.

### Установка
```bash
pip install pycryptodomex
# Скачать скрипт
wget https://raw.githubusercontent.com/sta-c0000/tpconf_bin_xml/master/tpconf_bin_xml.py
```

### Конвертация bin → xml (для чтения)
```bash
python3 tpconf_bin_xml.py config_backup.bin config_backup.xml
```

### Конвертация xml → bin (для загрузки обратно)
```bash
python3 tpconf_bin_xml.py config_backup.xml config_new.bin
```

### Что можно найти в XML
- Все параметры Wi-Fi (SSID, пароли, каналы)
- DHCP настройки и резервирования IP
- WAN параметры (PPPoE логин/пароль, IP)
- Правила файрвола
- Пользователи и пароли (в зашифрованном виде)
- Параметры QoS и родительского контроля

### Пример изменения SSID через XML
```xml
<!-- Найди и измени в conf.xml -->
<SSID val="НовоеИмяСети"/>
<PreSharedKey val="НовыйПароль"/>
```
После изменения конвертируй обратно в bin и загрузи через веб-интерфейс.

---

## 7. Полный скрипт автоматизации

Сохрани как `router_agent.py` и запусти в папке проекта.

```python
#!/usr/bin/env python3
"""
Агент для автоматической работы с TP-Link EC220-G5
Использование: python3 router_agent.py
"""

import os
import sys
import json
from datetime import datetime

ROUTER_IP = "http://192.168.0.1"
ROUTER_PASSWORD = "admin"  # замени на свой пароль
BACKUP_DIR = "./router_backups"

def install_deps():
    """Установить зависимости если не установлены"""
    os.system("pip install tplinkrouterc6u pycryptodomex -q")

def get_router():
    """Подключиться к роутеру"""
    from tplinkrouterc6u import TplinkRouterProvider
    return TplinkRouterProvider.get_client(ROUTER_IP, ROUTER_PASSWORD)

def cmd_status():
    """Показать статус роутера"""
    router = get_router()
    try:
        router.authorize()
        fw = router.get_firmware()
        st = router.get_status()
        
        print("=== СТАТУС РОУТЕРА TP-Link EC220-G5 ===")
        print(f"Прошивка: {fw}")
        print(f"Wi-Fi 2.4G: {'ВКЛ' if st.wifi_2g_enable else 'ВЫКЛ'}")
        print(f"Wi-Fi 5G:   {'ВКЛ' if st.wifi_5g_enable else 'ВЫКЛ'}")
        print(f"Гостевой 2.4G: {'ВКЛ' if st.guest_2g_enable else 'ВЫКЛ'}")
        print(f"\nПодключённые устройства ({len(st.devices)}):")
        for d in st.devices:
            print(f"  {d.macaddr}  {d.hostname or '—'}")
    finally:
        router.logout()

def cmd_clients():
    """Список всех клиентов DHCP"""
    router = get_router()
    try:
        router.authorize()
        leases = router.get_ipv4_dhcp_leases()
        reservations = router.get_ipv4_reservations()
        
        print("=== DHCP АРЕНДЫ ===")
        for l in sorted(leases, key=lambda x: x.ipaddr):
            print(f"  {l.ipaddr:16s} {l.macaddr}  {l.hostname or '—'}")
        
        print("\n=== СТАТИЧЕСКИЕ IP (резервирования) ===")
        for r in sorted(reservations, key=lambda x: x.ipaddr):
            print(f"  {r.ipaddr:16s} {r.macaddr}  {r.hostname or '—'}")
    finally:
        router.logout()

def cmd_backup():
    """Сделать резервную копию конфигурации"""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    # Сначала получаем stok через библиотеку
    router = get_router()
    try:
        router.authorize()
        
        import requests
        session = requests.Session()
        
        # Попытка скачать бэкап
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{BACKUP_DIR}/config_{timestamp}.bin"
        
        # Стандартный путь ISP прошивки
        stok = getattr(router, '_stok', None) or getattr(router, 'stok', None)
        
        if stok:
            url = f"http://192.168.0.1/cgi-bin/luci/;stok={stok}/admin/firmware?form=backup"
            resp = session.post(url, data={"operation": "backup"})
            if resp.status_code == 200 and len(resp.content) > 100:
                with open(filename, "wb") as f:
                    f.write(resp.content)
                print(f"Бэкап сохранён: {filename}")
                print(f"Размер: {len(resp.content)} байт")
            else:
                print("Не удалось скачать бэкап через API")
                print("Скачай вручную: http://192.168.0.1 → Advanced → System Tools → Backup")
        else:
            print("Не удалось получить stok. Скачай бэкап вручную:")
            print("http://192.168.0.1 → Advanced → System Tools → Backup & Restore → Backup")
    finally:
        router.logout()

def cmd_decode(bin_file):
    """Расшифровать conf.bin в XML"""
    if not os.path.exists(bin_file):
        print(f"Файл не найден: {bin_file}")
        return
    
    xml_file = bin_file.replace(".bin", ".xml")
    
    # Скачать утилиту если нет
    if not os.path.exists("tpconf_bin_xml.py"):
        print("Скачиваю tpconf_bin_xml.py...")
        os.system("wget -q https://raw.githubusercontent.com/sta-c0000/tpconf_bin_xml/master/tpconf_bin_xml.py")
    
    os.system(f"python3 tpconf_bin_xml.py {bin_file} {xml_file}")
    print(f"XML сохранён: {xml_file}")

def cmd_reboot():
    """Перезагрузить роутер"""
    confirm = input("Перезагрузить роутер? (yes/no): ")
    if confirm.lower() == "yes":
        router = get_router()
        try:
            router.authorize()
            router.reboot()
            print("Роутер перезагружается...")
        finally:
            try:
                router.logout()
            except:
                pass

def cmd_wifi(band, state):
    """Управление Wi-Fi: wifi 2g on/off, wifi 5g on/off"""
    from tplinkrouterc6u import Connection
    
    band_map = {
        "2g": Connection.HOST_2G,
        "5g": Connection.HOST_5G,
        "guest2g": Connection.GUEST_2G,
        "guest5g": Connection.GUEST_5G,
    }
    enable = state.lower() in ("on", "1", "true", "вкл")
    
    if band not in band_map:
        print(f"Неверный диапазон: {band}. Доступны: {list(band_map.keys())}")
        return
    
    router = get_router()
    try:
        router.authorize()
        router.set_wifi(band_map[band], enable)
        print(f"Wi-Fi {band}: {'включён' if enable else 'выключен'}")
    finally:
        router.logout()

# === ТОЧКА ВХОДА ===
if __name__ == "__main__":
    install_deps()
    
    args = sys.argv[1:]
    
    if not args or args[0] == "status":
        cmd_status()
    elif args[0] == "clients":
        cmd_clients()
    elif args[0] == "backup":
        cmd_backup()
    elif args[0] == "decode" and len(args) > 1:
        cmd_decode(args[1])
    elif args[0] == "reboot":
        cmd_reboot()
    elif args[0] == "wifi" and len(args) == 3:
        cmd_wifi(args[1], args[2])
    else:
        print("""
Использование:
  python3 router_agent.py status            — статус роутера
  python3 router_agent.py clients           — список клиентов DHCP
  python3 router_agent.py backup            — сделать бэкап конфига
  python3 router_agent.py decode config.bin — расшифровать бэкап в XML
  python3 router_agent.py reboot            — перезагрузить роутер
  python3 router_agent.py wifi 2g on        — включить Wi-Fi 2.4G
  python3 router_agent.py wifi 5g off       — выключить Wi-Fi 5G
        """)
```

---

## 8. Что агент может сделать

| Действие | Поддерживается | Метод |
|---|---|---|
| Прочитать статус Wi-Fi | ✅ | tplinkrouterc6u |
| Список подключённых устройств | ✅ | tplinkrouterc6u |
| Список DHCP аренд | ✅ | tplinkrouterc6u |
| Список статических IP | ✅ | tplinkrouterc6u |
| Включить/выключить Wi-Fi | ✅ | tplinkrouterc6u |
| Перезагрузить роутер | ✅ | tplinkrouterc6u |
| Скачать бэкап config.bin | ✅ | curl / requests |
| Расшифровать config.bin → XML | ✅ | tpconf_bin_xml.py |
| Загрузить конфиг на роутер | ✅ | curl / веб-форма |
| Изменить SSID/пароль Wi-Fi | ⚠️ | Через XML редактирование |
| Добавить статический IP | ⚠️ | Прямой HTTP POST |
| QoS / родительский контроль | ⚠️ | Прямой HTTP POST |

---

## 9. Известные проблемы

**Роутер не отвечает на API запросы:**
- Убедись что подключён через Ethernet, а не Wi-Fi
- Роутер поддерживает только 1 сессию — если другой браузер открыт, закрой его
- После каждой работы вызывай `router.logout()`

**Библиотека не определяет тип роутера:**
- EC220-G5 это ISP-кастомизированная версия, может не быть в списке поддерживаемых
- Попробуй классы `TPLinkMRClient`, `TPLinkEXClient` напрямую
- Перехвати запросы через DevTools и используй прямые HTTP вызовы

**Бэкап скачивается пустым:**
- Нужен актуальный `stok` токен (живёт ~10 минут)
- Попробуй скачать бэкап через браузер вручную и расшифровать через `tpconf_bin_xml.py`

**Ошибка авторизации:**
- Пароль на ISP-роутерах часто изменён провайдером
- Проверь пароль вручную зайдя на http://192.168.0.1

---

## Полезные ссылки

- Python библиотека: https://github.com/AlexandrErohin/TP-Link-Archer-C6U
- Декодер config.bin: https://github.com/sta-c0000/tpconf_bin_xml
- ISP документация TP-Link: https://service-provider.tp-link.com/wifi-router/ec220-g5/
- FAQ по настройке: https://www.tp-link.com/us/support/download/ec220-g5/
