"""
设 GitHub Secret - 用 token 认证 + libsodium 加密 secret value。

用法: python set_secret.py <repo> <name> <value> [--token <ghp_xxx>]
"""
import argparse
import base64
import json
import os
import sys
import urllib.request

from nacl import encoding, public


def encrypt(public_key: str, secret_value: str) -> str:
    pk = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())
    sealed = public.SealedBox(pk).encrypt(secret_value.encode("utf-8"), encoder=encoding.Base64Encoder())
    return sealed.decode("utf-8")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("repo")
    p.add_argument("name")
    p.add_argument("value")
    p.add_argument("--token", default=os.environ.get("GH_TOKEN"))
    a = p.parse_args()
    if not a.token:
        print("ERROR: --token or GH_TOKEN required", file=sys.stderr)
        sys.exit(1)
    headers = {
        "Authorization": f"token {a.token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "TRAE-CLI",
    }
    # 1) 取公钥
    req = urllib.request.Request(
        f"https://api.github.com/repos/{a.repo}/actions/secrets/public-key", headers=headers
    )
    with urllib.request.urlopen(req) as r:
        key = json.loads(r.read())
    # 2) 加密
    encrypted = encrypt(key["key"], a.value)
    # 3) PUT secret
    body = json.dumps({"encrypted_value": encrypted, "key_id": key["key_id"]}).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.github.com/repos/{a.repo}/actions/secrets/{a.name}",
        data=body, headers={**headers, "Content-Type": "application/json"}, method="PUT"
    )
    with urllib.request.urlopen(req) as r:
        print(f"{a.name}: HTTP {r.status} (key_id={key['key_id']})")


if __name__ == "__main__":
    main()
