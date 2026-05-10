#!/usr/bin/env python3
"""
TP-Link EC220-G5 (ISP GDPR firmware) — authentication via /cgi_gdpr.
Based on https://github.com/0xf15h/tp_link_gdpr
"""
import os
import re
import math
import hashlib
import base64
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

ROUTER_URL = "http://192.168.0.1"
PIN        = os.environ.get("ROUTER_PIN", "")   # export ROUTER_PIN=<pin> перед запуском
AES_KEY    = "AAAAAAAAAAAAAAAA"   # 16 chars, fixed for simplicity
AES_IV     = "BBBBBBBBBBBBBBBB"   # 16 chars
HEADERS    = {"Referer": "http://192.168.0.1/", "User-Agent": "Mozilla/5.0"}


def get_rsa_key(session: requests.Session):
    r = session.get(f"{ROUTER_URL}/cgi/getGDPRParm", headers=HEADERS, timeout=5)
    nn  = re.search(r'var nn="(.+?)";', r.text).group(1)
    ee  = re.search(r'var ee="(.+?)";', r.text).group(1)
    seq = re.search(r'var seq="(.+?)";', r.text).group(1)
    print(f"  nn len={len(nn)} bits={len(nn)*4}  seq={seq}")
    return int(nn, 16), int(ee, 16), int(seq)


def rsa_encrypt(e: int, n: int, plaintext: bytes) -> bytes:
    block = 64
    if len(plaintext) % block:
        plaintext += b"\x00" * (block - len(plaintext) % block)
    out = b""
    for i in range(0, len(plaintext), block):
        m = int.from_bytes(plaintext[i:i+block], "big")
        c = pow(m, e, n)
        out += c.to_bytes(math.ceil(n.bit_length() / 8), "big")
    return out


def aes_enc(data: bytes) -> bytes:
    cipher = AES.new(AES_KEY.encode(), AES.MODE_CBC, AES_IV.encode())
    return cipher.encrypt(pad(data, 16))


def aes_dec(data: bytes) -> bytes:
    cipher = AES.new(AES_KEY.encode(), AES.MODE_CBC, AES_IV.encode())
    return unpad(cipher.decrypt(data), 16)


def try_login(session: requests.Session, username: str, b64_passwd: bool = False) -> dict:
    n, e, seq = get_rsa_key(session)

    passwd_field = base64.b64encode(PIN.encode()).decode() if b64_passwd else PIN
    user_field   = base64.b64encode(username.encode()).decode() if (username and b64_passwd) else username

    # AES-encrypt the login payload
    if username:
        login_plain = (f"8\r\n[/cgi/login#0,0,0,0,0,0#0,0,0,0,0,0]0,2\r\n"
                       f"username={user_field}\r\npassword={passwd_field}\r\n")
    else:
        login_plain = f"8\r\n[/cgi/login#0,0,0,0,0,0#0,0,0,0,0,0]0,1\r\npassword={passwd_field}\r\n"

    data_b64 = base64.b64encode(aes_enc(login_plain.encode())).decode()

    # RSA-encrypt the signature — hash always uses raw PIN
    auth_hash = hashlib.md5(f"{username}{PIN}".encode()).hexdigest()
    seq_with_len = seq + len(data_b64)
    sign_plain = f"key={AES_KEY}&iv={AES_IV}&h={auth_hash}&s={seq_with_len}\x00\r\n"
    sign_hex = rsa_encrypt(e, n, sign_plain.encode()).hex()

    print(f"  username={repr(username)}  hash={auth_hash[:8]}...  data_len={len(data_b64)}")

    post_data = f"sign={sign_hex}\r\ndata={data_b64}\r\n"
    h = {**HEADERS, "Content-Type": "text/plain"}
    r = session.post(f"{ROUTER_URL}/cgi_gdpr", headers=h, data=post_data, timeout=10)

    print(f"  status={r.status_code}  set-cookie={r.headers.get('Set-Cookie','—')[:60]}")

    try:
        decrypted = aes_dec(base64.b64decode(r.text)).decode("utf-8", errors="replace")
        print(f"  response: {decrypted[:200]}")
        success = "$.ret=0" in decrypted
    except Exception as ex:
        print(f"  decrypt error: {ex}  raw: {repr(r.text[:100])}")
        success = False

    return {"success": success, "session": session, "response": r}


def main():
    print("=" * 55)
    print("TP-Link EC220-G5 GDPR auth test")
    print("=" * 55)

    for username, b64 in [("admin", False), ("user", False), ("", False),
                           ("admin", True),  ("user", True),  ("", True)]:
        print(f"\n[trying username={repr(username)} b64_passwd={b64}]")
        s = requests.Session()
        result = try_login(s, username, b64)
        if result["success"]:
            print(f"\n✓ LOGIN OK  username={repr(username)}  b64={b64}")
            return s
        s.close()

    print("\n✗ All login attempts failed")
    return None


if __name__ == "__main__":
    main()
