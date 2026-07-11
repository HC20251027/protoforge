"""列出最近 N 个 workflow run。"""
import json
import os
import sys
import urllib.request

token = os.environ.get("GH_TOKEN")
if not token:
    print("ERROR: GH_TOKEN env required", file=sys.stderr)
    sys.exit(1)

per_page = int(sys.argv[1]) if len(sys.argv) > 1 else 5
req = urllib.request.Request(
    f"https://api.github.com/repos/HC20251027/protoforge/actions/runs?per_page={per_page}",
    headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "TRAE-CLI",
    },
)
with urllib.request.urlopen(req) as r:
    data = json.loads(r.read())
for x in data["workflow_runs"]:
    print(
        f"id={x['id']} name={x['name']} status={x['status']} "
        f"conclusion={x.get('conclusion')} created={x['created_at']} head={x['head_branch']}"
    )
