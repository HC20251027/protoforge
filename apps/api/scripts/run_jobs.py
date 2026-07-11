"""PowerShell 包装:不返回非零退出码的 PowerShell 包装器。"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

token = os.environ.get("GH_TOKEN")
run_id = sys.argv[1]
url = f"https://api.github.com/repos/HC20251027/protoforge/actions/runs/{run_id}/jobs"
headers = {
    "Authorization": f"token {token}",
    "Accept": "application/vnd.github+json",
    "User-Agent": "TRAE-CLI",
}
# 重试 3 次应对 github api 偶发 ConnectionReset
last_err = None
for i in range(3):
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        break
    except urllib.error.URLError as e:
        last_err = e
        time.sleep(2 * (i + 1))
else:
    print(f"ERROR: {last_err}", file=sys.stderr)
    sys.exit(2)
for j in data["jobs"]:
    print(f"=== job: {j['name']} (id={j['id']}, conclusion={j.get('conclusion')}) ===")
    for s in j.get("steps", []):
        conc = s.get("conclusion") or s.get("status") or "?"
        print(f"  [{conc:12}] {s['number']}. {s['name']}")
