"""触发 GitHub Actions workflow_dispatch。"""
import json
import os
import sys
import urllib.request

token = os.environ.get("GH_TOKEN")
workflow = sys.argv[1] if len(sys.argv) > 1 else "ci.yml"
ref = sys.argv[2] if len(sys.argv) > 2 else "main"
body = json.dumps({"ref": ref}).encode("utf-8")
req = urllib.request.Request(
    f"https://api.github.com/repos/HC20251027/protoforge/actions/workflows/{workflow}/dispatches",
    data=body,
    headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "TRAE-CLI",
    },
    method="POST",
)
try:
    with urllib.request.urlopen(req) as r:
        print(f"{workflow} dispatched on {ref}: HTTP {r.status}")
except urllib.error.HTTPError as e:
    print(f"ERROR: HTTP {e.code} {e.read().decode('utf-8')}", file=sys.stderr)
    sys.exit(1)
