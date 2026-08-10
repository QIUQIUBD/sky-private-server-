#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sky Gold (2018) — AccountServer Mock
=====================================
根据逆向提取的 82 个 /account/* API 端点模拟 TGC 账号服务器。
用途：让 Sky.app (macOS 客户端) 在服务器下线后仍能完成登录/数据流程（单机复活）。

【连接方式】(三选一)
  1. macOS 上修改 /etc/hosts:  127.0.0.1 skygold.top
  2. 修改包内 Info.plist 的 SkyServerHostname 为 127.0.0.1（会破坏签名，
     需 codesign --force --deep -s - 重新签名，Developer ID 证书已过期，
     系统信任后仍可运行）
  3. 若客户端强制 HTTPS，用 stunnel/nginx 做 TLS 终结再转发本服务

【运行】
  sudo python3 account_server_mock.py --port 443 --log
  （客户端很可能访问 https://skygold.top:443；HTTP 模式用 --http）

【注意】
  - 响应格式为推测(JSON)。若客户端期望 protobuf 或特定字段，请观察 --log
    记录的请求/响应再调整。
  - 联机部分(SkyNet WebSocket)未模拟，本服务只覆盖 AccountServer HTTP API。
"""
import argparse
import json
import logging
import ssl
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("sky-mock")

# ---------------------------------------------------------------------------
# 账号数据(内存态，够单机流程使用)
# ---------------------------------------------------------------------------
class AccountDB:
    def __init__(self):
        self.accounts = {}
        self.next_id = 1000

    def create(self, req):
        uid = self.next_id
        self.next_id += 1
        self.accounts[uid] = {
            "id": uid,
            "account_id": str(uid),
            "display_name": "MockPlayer%d" % uid,
            "created_at": int(time.time()),
            "currency": {"candles": 10, "hearts": 0, "wax": 100, "storm_hearts": 0},
            "collectibles": [],
            "friends": [],
            "unlocks": [],
        }
        return {"status": "ok", "account_id": str(uid), "session_token": "mock-token-%d" % uid}

    def login(self, req):
        if "account_id" in req:
            uid = int(req["account_id"])
            if uid in self.accounts:
                return {"status": "ok", "account_id": str(uid),
                        "session_token": "mock-token-%d" % uid}
        # 新账号自动创建(便于无感进入)
        return self.create(req)


db = AccountDB()


# ---------------------------------------------------------------------------
# 响应表：每个端点 -> (handler or 默认响应)
# ---------------------------------------------------------------------------
def empty_list():
    return []

def ok_empty():
    return {"status": "ok"}

def echo_vars():
    return {
        "vars": {
            "kEnableNetProfileHud": False,
            "kShowInactiveAvatars": False,
            "kEnableScreenshot": True,
        }
    }

def get_shop():
    return {"items": [], "spirits": []}

def get_motd():
    return {"motd": {"title": "Sky Gold Mock Server", "body": "服务器已下线，本响应由逆向 mock 提供", "url": ""}}

def get_event_schedule():
    return {"events": []}

def get_latest_build_version():
    return {"version": "0.3.18", "build": 119668, "required": False}

def get_friend_statues():
    return {"statues": []}

def get_pending_gift_messages():
    return {"messages": []}

def get_local_notifications():
    return {"notifications": []}

def get_questionnaires():
    return {"questionnaires": []}

def get_daily_quests():
    return {"quests": []}

def get_achievements():
    return {"achievements": []}

def get_collectibles():
    return {"collectibles": []}

def get_currency(req):
    a = db.accounts.get(int(req.get("account_id", 0)), {})
    return {"currency": a.get("currency", {})}

def get_friends(req):
    a = db.accounts.get(int(req.get("account_id", 0)), {})
    return {"friends": a.get("friends", [])}

def get_unlocks(req):
    a = db.accounts.get(int(req.get("account_id", 0)), {})
    return {"unlocks": a.get("unlocks", [])}

def hb(req):
    return {"status": "ok", "interval": 60, "time": int(time.time())}

# 端点路由: 路径 -> (处理函数, 默认响应)
ENDPOINTS = {
    "/account/create": (db.create, None),
    "/account/login": (db.login, None),
    "/account/hb": (hb, None),
    "/account/get_vars": (None, echo_vars()),
    "/account/get_shop": (None, get_shop()),
    "/account/get_motd": (None, get_motd()),
    "/account/get_event_schedule": (None, get_event_schedule()),
    "/account/get_latest_build_version": (None, get_latest_build_version()),
    "/account/get_friend_statues": (None, get_friend_statues()),
    "/account/get_pending_gift_messages": (None, get_pending_gift_messages()),
    "/account/get_local_notifications": (None, get_local_notifications()),
    "/account/get_questionnaires": (None, get_questionnaires()),
    "/account/get_daily_quests": (None, get_daily_quests()),
    "/account/get_achievements": (None, get_achievements()),
    "/account/get_collectibles": (None, get_collectibles()),
    "/account/get_currency": (get_currency, None),
    "/account/get_friends": (get_friends, None),
    "/account/get_unlocks": (get_unlocks, None),
    "/account/get_level_pickups": (None, {"pickups": []}),
    "/account/get_account_world_quests": (None, {"quests": []}),
    "/account/get_relationship_abilities": (None, {"abilities": []}),
    "/account/get_spirit_shops": (None, {"shops": []}),
    "/account/get_achievement_stats": (None, {"stats": {}}),
    "/account/get_app_badge_number": (None, {"count": 0}),
    "/account/get_invites": (None, {"invites": []}),
    "/account/geonote/get_user_geonotes": (None, {"geonotes": []}),
    "/account/geonote/request_geonotes_for_n_friends": (None, {"geonotes": []}),
    "/account/geonote/request_n_bug_report_geonotes": (None, {"geonotes": []}),
    "/account/sync_user_data": (None, {"status": "ok"}),
    "/account/set_device_token": (None, {"status": "ok"}),
    "/account/ack_collectible": (None, {"status": "ok"}),
    "/account/ack_unlock": (None, {"status": "ok"}),
    "/account/collect_collectible": (None, {"status": "ok"}),
    "/account/collect_collectible_list": (None, {"status": "ok"}),
    "/account/collect_pickup": (None, {"status": "ok"}),
    "/account/drop_collectible": (None, {"status": "ok"}),
    "/account/drop_unlock": (None, {"status": "ok"}),
    "/account/lock_collectibles": (None, {"status": "ok"}),
    "/account/add_currency": (None, {"status": "ok"}),
    "/account/buy_candle_wax": (None, {"status": "ok"}),
    "/account/claim_storm_key": (None, {"status": "ok"}),
    "/account/deposit_storm_key": (None, {"status": "ok"}),
    "/account/claim_achievement_reward": (None, {"status": "ok"}),
    "/account/claim_daily_quests_reward": (None, {"status": "ok"}),
    "/account/claim_quest_reward": (None, {"status": "ok"}),
    "/account/claim_questionnaire_reward": (None, {"status": "ok"}),
    "/account/redeem_reward": (None, {"status": "ok"}),
    "/account/reset_account_world_quest_cooldowns": (None, {"status": "ok"}),
    "/account/reset_account_world_quests": (None, {"status": "ok"}),
    "/account/reset_achievement_stats": (None, {"status": "ok"}),
    "/account/reset_daily_quests_tracking": (None, {"status": "ok"}),
    "/account/reset_storm_key_progress": (None, {"status": "ok"}),
    "/account/set_achievement_stats": (None, {"status": "ok"}),
    "/account/set_friend_block": (None, {"status": "ok"}),
    "/account/set_friend_favorite": (None, {"status": "ok"}),
    "/account/set_friend_mute": (None, {"status": "ok"}),
    "/account/set_friend_name": (None, {"status": "ok"}),
    "/account/give_candle": (None, {"status": "ok"}),
    "/account/join_friend_game": (None, {"status": "ok", "server": None}),
    "/account/join_random_game": (None, {"status": "ok", "server": None}),
    "/account/join_previous_game": (None, {"status": "ok", "server": None}),
    "/account/find_previous_or_empty": (None, {"status": "ok", "server": None}),
    "/account/find_prev_or_empty": (None, {"status": "ok", "server": None}),
    "/account/accept_invite": (None, {"status": "ok"}),
    "/account/check_invite": (None, {"status": "ok"}),
    "/account/create_invite": (None, {"status": "ok"}),
    "/account/delete_invite": (None, {"status": "ok"}),
    "/account/link_gamecenter": (None, {"status": "ok"}),
    "/account/recover_gamecenter": (None, {"status": "ok"}),
    "/account/support_recover": (None, {"status": "ok"}),
    "/account/purchase_unlock": (None, {"status": "ok"}),
    "/account/iaplist": (None, {"items": []}),
    "/account/receipt": (None, {"status": "ok"}),
    "/account/remove_relationship_hint": (None, {"status": "ok"}),
    "/account/geonote/create_geonote2": (None, {"status": "ok", "id": 1}),
    "/account/geonote/delete_geonote": (None, {"status": "ok"}),
    "/account/geonote/edit_message_geonote": (None, {"status": "ok"}),
    "/account/geonote/social_geonote": (None, {"status": "ok"}),
    "/account/geonote/create_bug_report_geonote": (None, {"status": "ok"}),
    "/account/geonote/delete_bug_report_geonote": (None, {"status": "ok"}),
}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _handle(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)
        # 读取 body
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""
        req = {}
        try:
            if body:
                req = json.loads(body)
        except Exception:
            req = {"_raw_body": body.decode("utf-8", "replace")}
        req.update({k: v[0] for k, v in qs.items()})

        # 查找端点
        handler, default = ENDPOINTS.get(path, (None, None))
        if default is None and handler is None:
            # 未知端点: 返回通用成功(并记录)
            resp = {"status": "ok", "unmocked": True}
            code = 200
            log.warning("UNMOCKED %s %s", self.command, path)
        else:
            try:
                resp = handler(req) if handler else default
                code = 200
            except Exception as e:
                resp = {"status": "error", "error": str(e)}
                code = 400
            log.info("%-6s %s -> %s", self.command, path, json.dumps(resp)[:200])

        data = json.dumps(resp).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_GET = _handle
    do_POST = _handle
    do_PUT = _handle
    do_DELETE = _handle
    do_OPTIONS = _handle

    def log_message(self, fmt, *args):  # 静默默认日志
        pass


def main():
    ap = argparse.ArgumentParser(description="Sky Gold AccountServer Mock")
    ap.add_argument("--port", type=int, default=443, help="监听端口(默认443)")
    ap.add_argument("--http", action="store_true", help="纯HTTP模式(默认尝试HTTPS)")
    ap.add_argument("--cert", default=None, help="TLS证书路径(可选)")
    ap.add_argument("--key", default=None, help="TLS私钥路径(可选)")
    ap.add_argument("--log", action="store_true", help="详细请求日志")
    args = ap.parse_args()

    if args.log:
        log.setLevel(logging.DEBUG)

    server = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    if not args.http:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        if args.cert and args.key:
            ctx.load_cert_chain(args.cert, args.key)
        else:
            # 生成自签证书(需先执行: openssl req -x509 -newkey rsa:2048 -nodes
            #   -keyout sky.key -out sky.crt -days 365 -subj "/CN=skygold.top")
            log.error("HTTPS 模式需要证书: --cert sky.crt --key sky.key")
            log.error("或先生成: openssl req -x509 -newkey rsa:2048 -nodes -keyout sky.key -out sky.crt -days 365 -subj '/CN=skygold.top'")
            sys.exit(1)
        server.socket = ctx.wrap_socket(server.socket, server_side=True)
        proto = "HTTPS"
    else:
        proto = "HTTP"

    log.info("SkyGold Mock AccountServer 已启动: %s://0.0.0.0:%d (%d 个端点)",
             proto, args.port, len(ENDPOINTS))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("停止")


if __name__ == "__main__":
    main()