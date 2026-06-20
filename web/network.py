"""网页服务网络地址工具。"""
from __future__ import annotations

import socket
from typing import List


def resolve_bind_host(host: str) -> str:
    """解析 uvicorn 绑定地址。"""
    h = (host or "0.0.0.0").strip()
    if h.lower() == "localhost":
        return "127.0.0.1"
    return h


def _primary_lan_ip() -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return None


def list_access_urls(port: int, *, bind_host: str) -> List[str]:
    """生成本机与局域网可访问的 URL 列表（去重）。"""
    seen: set[str] = set()
    urls: List[str] = []

    def add(url: str) -> None:
        if url not in seen:
            seen.add(url)
            urls.append(url)

    add(f"http://127.0.0.1:{port}/")
    add(f"http://localhost:{port}/")

    lan_ip = _primary_lan_ip()
    if lan_ip:
        add(f"http://{lan_ip}:{port}/")

    if bind_host not in ("0.0.0.0", "127.0.0.1", "localhost"):
        add(f"http://{bind_host}:{port}/")

    return urls


def browser_open_url(port: int) -> str:
    return f"http://127.0.0.1:{port}/"
