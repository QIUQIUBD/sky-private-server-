# SkyNet — Sky Private Server

> 研究性项目 ｜ Sky: Children of the Light（2018 旧版）私有服务器 · 协议逆向与服务端模拟

![License](https://img.shields.io/badge/License-Apache%202.0-blue?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Research-8B0000?style=for-the-badge)
![Maintenance](https://img.shields.io/badge/Maintenance-Active-2EA44F?style=for-the-badge)

## 📌 项目定位

对 **Sky: Children of the Light**（2018 legacy 版本）客户端的网络通信进行逆向分析，
实现服务端协议模拟，用于**游戏网络层与引擎机制的学术研究**。

> ⚠️ 本项目仅用于技术研究、协议学习和游戏机制分析，不用于商业运营或任何侵权用途。

## 🧩 研究内容

- **协议逆向** — 客户端 ↔ 服务端通信协议还原（WebSocket / 私有 RPC / protobuf）
- **服务端模拟** — 核心会话、房间与同步逻辑的轻量模拟实现
- **工具链** — 抓包解析、消息构造、自动化验证脚本

## 🛠 技术栈

![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)
![Node.js](https://img.shields.io/badge/Node.js-339933?style=for-the-badge&logo=nodedotjs&logoColor=white)
![WebSocket](https://img.shields.io/badge/WebSocket-010101?style=for-the-badge)
![protobuf](https://img.shields.io/badge/protobuf-5C2D91?style=for-the-badge)
![Frida](https://img.shields.io/badge/Frida-000000?style=for-the-badge)

## 📁 目录结构

```
├── server/
│   └── account_server_mock.py    # Sky 2018 AccountServer 模拟（覆盖 82 个 /account/* 端点）
├── notes/
│   ├── skynet_protocol.txt       # SkyNet 实时联机协议逆向笔记（WebSocket / protobuf-c）
│   ├── account_api_endpoints.txt # /account API 端点清单
│   └── netrpc_list.txt           # NetRPC 消息类型列表（OfferCandle / FriendSync / GateSync ...）
└── README.md
```

## 🚀 快速开始

```bash
# 启动 AccountServer 模拟（客户端原指向 skygold.top:443）
sudo python3 server/account_server_mock.py --port 443 --log

# HTTP 模式（本地测试）
python3 server/account_server_mock.py --port 8080 --http
```

连接方式（三选一）：
1. 修改 `/etc/hosts`：`127.0.0.1 skygold.top`
2. 修改包内 `Info.plist` 的 `SkyServerHostname`（需重新签名）
3. 用 stunnel/nginx 做 TLS 终结转发至本服务

## 📚 相关项目

- [sky-shader-reverse-engineering](https://github.com/QIUQIUBD/sky-shader-reverse-engineering) — Sky 2018 渲染管线逆向工具链

## ⚠️ 免责声明

本项目为纯技术研究项目，与 thatgamecompany 及 Sky: Children of the Light 官方无任何关联。
所有分析均基于公开资料与个人学习目的，请勿用于商业用途。