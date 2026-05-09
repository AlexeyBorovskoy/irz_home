#!/usr/bin/env python3
"""
Read-only audit script for TP-Link EC220-G5.
Collects firmware, status, devices, DHCP data. No changes made.
Usage:
  python3 tplink_readonly_audit.py           -- collect all data
  python3 tplink_readonly_audit.py --backup  -- also download config.bin
"""

import sys
import json
import os
from datetime import datetime
from pathlib import Path

ROUTER_URL = "http://192.168.0.1"
ROUTER_PIN = "80276760"
OUT_DIR = Path(__file__).parent.parent.parent / "configs" / "tplink"

CANDIDATE_CLASSES = [
    "TplinkRouterProvider",  # auto-detect first
    "TplinkRouter",
    "TPLinkMRClient",
    "TPLinkMRClientGCM",
    "TPLinkEXClient",
    "TPLinkEXClientGCM",
]


def save(name: str, data) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    print(f"  saved → {path.relative_to(Path.cwd()) if path.is_relative_to(Path.cwd()) else path}")
    return path


def get_router():
    try:
        import tplinkrouterc6u as lib
    except ImportError:
        print("ERROR: tplinkrouterc6u not installed. Run: pip install tplinkrouterc6u")
        sys.exit(1)

    # Try auto-detection first
    try:
        router = lib.TplinkRouterProvider.get_client(ROUTER_URL, ROUTER_PIN)
        router.authorize()
        print(f"  connected via TplinkRouterProvider (auto: {type(router).__name__})")
        return router
    except Exception as e:
        print(f"  TplinkRouterProvider failed: {e}")

    # Try each class manually
    for cls_name in ["TplinkRouter", "TPLinkMRClient", "TPLinkMRClientGCM",
                     "TPLinkEXClient", "TPLinkEXClientGCM"]:
        cls = getattr(lib, cls_name, None)
        if cls is None:
            continue
        try:
            router = cls(ROUTER_URL, ROUTER_PIN)
            router.authorize()
            print(f"  connected via {cls_name}")
            return router
        except Exception as e:
            print(f"  {cls_name}: {e}")

    print("ERROR: no client class worked. Is Firefox closed? Is the router reachable?")
    sys.exit(1)


def collect_firmware(router):
    print("\n[firmware]")
    try:
        fw = router.get_firmware()
        data = {
            "hardware_version": getattr(fw, "hardware_ver", None),
            "software_version": getattr(fw, "software_ver", None),
            "firmware_version": getattr(fw, "firmware_ver", None),
            "raw": str(fw),
        }
        print(f"  hw={data['hardware_version']}  sw={data['software_version']}")
        save("firmware", data)
        return data
    except Exception as e:
        print(f"  FAILED: {e}")
        return {}


def collect_status(router):
    print("\n[status]")
    try:
        st = router.get_status()
        data = {
            "wifi_2g_enable": st.wifi_2g_enable,
            "wifi_5g_enable": st.wifi_5g_enable,
            "guest_2g_enable": st.guest_2g_enable,
            "guest_5g_enable": getattr(st, "guest_5g_enable", None),
            "wired_total": getattr(st, "wired_total", None),
            "wifi_clients_total": getattr(st, "wifi_clients_total", None),
            "guest_clients_total": getattr(st, "guest_clients_total", None),
            "clients_total": getattr(st, "clients_total", None),
            "wan_ipv4_addr": getattr(st, "wan_ipv4_addr", None),
        }
        print(f"  2.4G={'on' if st.wifi_2g_enable else 'off'}  "
              f"5G={'on' if st.wifi_5g_enable else 'off'}  "
              f"clients={data['clients_total']}")
        save("status", data)
        return st
    except Exception as e:
        print(f"  FAILED: {e}")
        return None


def collect_devices(router, status):
    print("\n[connected devices]")
    try:
        devices = status.devices if status else []
        data = [
            {
                "mac": getattr(d, "macaddr", None),
                "hostname": getattr(d, "hostname", None),
                "type": getattr(d, "type", None),
            }
            for d in devices
        ]
        print(f"  found {len(data)} device(s)")
        for d in data:
            print(f"    {d['mac']}  {d['hostname'] or '—'}")
        save("devices", data)
    except Exception as e:
        print(f"  FAILED: {e}")


def collect_dhcp_leases(router):
    print("\n[DHCP leases]")
    try:
        leases = router.get_ipv4_dhcp_leases()
        data = [
            {
                "mac": getattr(l, "macaddr", None),
                "ip": getattr(l, "ipaddr", None),
                "hostname": getattr(l, "hostname", None),
            }
            for l in leases
        ]
        print(f"  found {len(data)} lease(s)")
        for d in sorted(data, key=lambda x: x["ip"] or ""):
            print(f"    {d['ip']:16s}  {d['mac']}  {d['hostname'] or '—'}")
        save("dhcp_leases", data)
    except Exception as e:
        print(f"  FAILED: {e}")


def collect_dhcp_reservations(router):
    print("\n[DHCP reservations]")
    try:
        reservations = router.get_ipv4_reservations()
        data = [
            {
                "mac": getattr(r, "macaddr", None),
                "ip": getattr(r, "ipaddr", None),
                "hostname": getattr(r, "hostname", None),
            }
            for r in reservations
        ]
        print(f"  found {len(data)} reservation(s)")
        for d in sorted(data, key=lambda x: x["ip"] or ""):
            print(f"    {d['ip']:16s}  {d['mac']}  {d['hostname'] or '—'}")
        save("dhcp_reservations", data)
    except Exception as e:
        print(f"  FAILED: {e}")


def download_backup(router):
    print("\n[config.bin backup]")
    import requests as req

    stok = None
    for attr in ("_stok", "stok", "_token", "token"):
        stok = getattr(router, attr, None)
        if stok:
            break

    if not stok:
        print("  WARNING: could not extract stok — skipping backup")
        print("  Download manually: http://192.168.0.1 → Advanced → System Tools → Backup")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"config_{timestamp}.bin"

    backup_urls = [
        f"http://192.168.0.1/cgi-bin/luci/;stok={stok}/admin/firmware?form=backup",
        f"http://192.168.0.1/cgi-bin/luci/;stok={stok}/admin/system?form=backup",
        f"http://192.168.0.1/cgi-bin/luci/;stok={stok}/admin/syslog?form=pcm",
    ]

    session = req.Session()
    for url in backup_urls:
        try:
            resp = session.post(url, data={"operation": "backup"}, timeout=15)
            if resp.status_code == 200 and len(resp.content) > 200:
                out_path.write_bytes(resp.content)
                print(f"  saved → {out_path}  ({len(resp.content)} bytes)")
                return str(out_path)
            else:
                print(f"  {url.split('?')[1]}: {resp.status_code}, {len(resp.content)} bytes")
        except Exception as e:
            print(f"  {url.split('?')[1]}: {e}")

    print("  FAILED: backup not downloaded via API")
    print("  Download manually: http://192.168.0.1 → Дополнительно → Сист. инструменты → Бэкап")


def main():
    do_backup = "--backup" in sys.argv

    print("=" * 55)
    print("TP-Link EC220-G5 read-only audit")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)
    print("\nNOTE: Firefox must be closed — router allows only 1 session")
    print("\n[connecting]")

    router = get_router()
    try:
        fw_data = collect_firmware(router)
        status = collect_status(router)
        collect_devices(router, status)
        collect_dhcp_leases(router)
        collect_dhcp_reservations(router)
        if do_backup:
            download_backup(router)
    finally:
        try:
            router.logout()
            print("\n[logged out]")
        except Exception:
            pass

    print("\n" + "=" * 55)
    print("Audit complete. Results saved to configs/tplink/")
    print("Next: fill in docs/router/TP_LINK_AUDIT.md")


if __name__ == "__main__":
    main()
