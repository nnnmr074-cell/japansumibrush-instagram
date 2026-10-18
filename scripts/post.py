"""Publish due, approved posts from queue/posts.json to Instagram (Instagram API with Instagram Login).

Runs in GitHub Actions. Secrets: IG_TOKEN, IG_USER_ID. Media are served from GitHub Pages (MEDIA_BASE).
Safety: only status == "approved", only when scheduled_at <= now, at most MAX_PER_RUN posts per run.
"""
import json, os, sys, time, urllib.parse, urllib.request, datetime as dt

API = "https://graph.instagram.com/v23.0"
TOKEN = os.environ["IG_TOKEN"].strip()
UID = os.environ["IG_USER_ID"].strip()
MEDIA_BASE = os.environ.get("MEDIA_BASE", "https://nnnmr074-cell.github.io/japansumibrush-instagram/")
QUEUE = "queue/posts.json"
MAX_PER_RUN = 1


def call(method, path, **params):
    params["access_token"] = TOKEN
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    if method == "GET":
        req = urllib.request.Request(url + "?" + data.decode())
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode().replace(TOKEN, "***")
        raise RuntimeError(f"{method} {path} -> HTTP {e.code}: {body[:400]}")


def url_of(rel):
    return rel if rel.startswith("http") else MEDIA_BASE + urllib.parse.quote(rel)


def wait_ready(cid, timeout=600):
    t0 = time.time()
    while time.time() - t0 < timeout:
        st = call("GET", cid, fields="status_code,status").get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"container {cid} status {st}")
        time.sleep(10)
    raise RuntimeError(f"container {cid} not ready after {timeout}s")


def item(rel, carousel=False):
    p = {"is_carousel_item": "true"} if carousel else {}
    if rel.lower().endswith((".mp4", ".mov")):
        return call("POST", f"{UID}/media", media_type="VIDEO", video_url=url_of(rel), **p)["id"]
    return call("POST", f"{UID}/media", image_url=url_of(rel), **p)["id"]


def publish(post):
    kind, media, cap = post["type"], post["media"], post["caption"]
    if kind == "REELS":
        extra = {"cover_url": url_of(post["cover"])} if post.get("cover") else {}
        cid = call("POST", f"{UID}/media", media_type="REELS", video_url=url_of(media[0]),
                   caption=cap, share_to_feed="true", **extra)["id"]
    elif kind == "CAROUSEL":
        kids = [item(m, carousel=True) for m in media]
        for k in kids:
            wait_ready(k)
        cid = call("POST", f"{UID}/media", media_type="CAROUSEL", children=",".join(kids), caption=cap)["id"]
    elif kind == "IMAGE":
        cid = call("POST", f"{UID}/media", image_url=url_of(media[0]), caption=cap)["id"]
    else:
        raise RuntimeError(f"unknown type {kind}")
    wait_ready(cid)
    mid = call("POST", f"{UID}/media_publish", creation_id=cid)["id"]
    info = call("GET", mid, fields="permalink,timestamp")
    return mid, info.get("permalink", "")


def main():
    q = json.load(open(QUEUE, encoding="utf-8"))
    now = dt.datetime.now(dt.timezone.utc)
    due = [p for p in q["posts"] if p.get("status") == "approved"
           and dt.datetime.fromisoformat(p["scheduled_at"]) <= now]
    due.sort(key=lambda p: p["scheduled_at"])
    if not due:
        print("nothing due"); return 0
    failed = False
    for p in due[:MAX_PER_RUN]:
        try:
            mid, link = publish(p)
            p.update(status="posted", media_id=mid, permalink=link,
                     posted_at=now.isoformat(timespec="seconds"))
            print("posted", p["id"], link)
        except Exception as e:
            p.update(status="error", error=str(e)[:500], tried_at=now.isoformat(timespec="seconds"))
            print("ERROR", p["id"], e); failed = True
    json.dump(q, open(QUEUE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
