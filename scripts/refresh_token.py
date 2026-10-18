"""Refresh the 60-day Instagram token and store the new one in the IG_TOKEN repository secret.

Secrets: IG_TOKEN, GH_PAT (fine-grained, Secrets: read/write on this repo). Env: REPO (owner/name).
"""
import base64, json, os, urllib.parse, urllib.request
from nacl import encoding, public

tok = os.environ["IG_TOKEN"].strip()
pat = os.environ["GH_PAT"].strip()
repo = os.environ["REPO"]

u = "https://graph.instagram.com/refresh_access_token?" + urllib.parse.urlencode(
    {"grant_type": "ig_refresh_token", "access_token": tok})
try:
    with urllib.request.urlopen(u, timeout=30) as r:
        res = json.load(r)
except urllib.error.HTTPError as e:
    raise SystemExit("refresh failed: HTTP %s %s" % (e.code, e.read().decode().replace(tok, "***")[:300]))
new = res["access_token"]
print("refreshed; expires_in days =", round(res.get("expires_in", 0) / 86400, 1))


def gh(path, method="GET", data=None):
    req = urllib.request.Request("https://api.github.com" + path, method=method,
                                 data=json.dumps(data).encode() if data is not None else None,
                                 headers={"Authorization": "Bearer " + pat,
                                          "Accept": "application/vnd.github+json",
                                          "X-GitHub-Api-Version": "2022-11-28"})
    with urllib.request.urlopen(req, timeout=30) as r:
        b = r.read()
        return json.loads(b) if b else {}


k = gh(f"/repos/{repo}/actions/secrets/public-key")
box = public.SealedBox(public.PublicKey(k["key"].encode(), encoding.Base64Encoder()))
enc = base64.b64encode(box.encrypt(new.encode())).decode()
gh(f"/repos/{repo}/actions/secrets/IG_TOKEN", "PUT", {"encrypted_value": enc, "key_id": k["key_id"]})
print("IG_TOKEN secret updated")
