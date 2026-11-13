#!/usr/bin/env python3
"""Send a widget HTML file with Bot API sendWidget.

Dry-run by default, add --yes to actually send.
Reads BOT_TOKEN and CHAT_ID from the environment or --env-file.
Use --last-chat to look up the most recent private chat via getUpdates.
"""

import argparse
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

ap = argparse.ArgumentParser()
ap.add_argument("--html", type=pathlib.Path, required=True)
ap.add_argument("--chat-id", default=os.environ.get("CHAT_ID") or os.environ.get("BOT_UID"))
ap.add_argument("--last-chat", action="store_true", help="find latest private chat via getUpdates")
ap.add_argument("--token", default=os.environ.get("BOT_TOKEN", ""))
ap.add_argument("--env-file", type=pathlib.Path, default=None)
ap.add_argument("--api-root", default=None)
ap.add_argument("--no-test-env", action="store_true")
ap.add_argument("--width", type=int, default=390)
ap.add_argument("--allow-queries", action="store_true")
ap.add_argument("--background-query", action="store_true")
ap.add_argument("--yes", action="store_true", help="actually send")
a = ap.parse_args()

if a.env_file and a.env_file.is_file():
    for raw in a.env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip("'\"")
        os.environ.setdefault(k, v)
        if k == "BOT_TOKEN" and not a.token:
            a.token = v
        if k in ("CHAT_ID", "BOT_UID") and not a.chat_id:
            a.chat_id = v

api_root = (a.api_root or os.environ.get("TELEGRAM_API_ROOT")
            or "https://api.telegram.org/beta").rstrip("/")
if a.no_test_env:
    test_env = ""
else:
    test_env = "" if os.environ.get("TELEGRAM_TEST_ENV", "1").lower() in {
        "0", "false", "no", "off"
    } else "/test"
base = f"{api_root}{test_env}/bot{a.token}"

if not a.html.is_file():
    sys.exit(f"no such file: {a.html}")
html = a.html.read_text(encoding="utf-8")
if len(html.encode("utf-8")) > 32768:
    sys.exit("HTML over 32768-byte sendWidget limit")

if not a.token:
    sys.exit("need --token/BOT_TOKEN")
if a.last_chat and not a.chat_id:
    try:
        with urllib.request.urlopen(f"{base}/getUpdates", timeout=25) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        sys.exit(f"getUpdates failed: {e}")
    for upd in reversed(data.get("result", [])):
        msg = upd.get("message") or upd.get("edited_message") or {}
        chat = msg.get("chat") or {}
        if chat.get("type") == "private" and chat.get("id") is not None:
            a.chat_id = chat["id"]
            break
    if not a.chat_id:
        sys.exit("no private chat in getUpdates; send /start to the bot first")
if not a.chat_id:
    sys.exit("need --chat-id/CHAT_ID (or --last-chat)")

body = json.dumps({
    "chat_id": a.chat_id,
    "html": html,
    "width": a.width,
    "disable_notification": True,
    **({"allow_queries": True} if a.allow_queries else {}),
    **({"background_query": True} if a.background_query else {}),
}).encode("utf-8")

print(f"target: {api_root}{test_env}/bot<redacted>/sendWidget")
print(f"chat_id: {a.chat_id}  html: {len(html.encode('utf-8'))} bytes")
if not a.yes:
    print("dry run; add --yes to send")
    sys.exit(0)

req = urllib.request.Request(f"{base}/sendWidget", data=body,
                             headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode("utf-8"))
except urllib.error.HTTPError as e:
    print(e.read().decode("utf-8", "replace"))
    sys.exit(1)
except Exception as e:
    print(f"request failed: {e}")
    sys.exit(1)
if not data.get("ok"):
    print(json.dumps(data, indent=2))
    sys.exit(1)
print(f"ok: message_id={data.get('result', {}).get('message_id')}")
