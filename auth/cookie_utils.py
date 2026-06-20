"""登录 Cookie 校验（文件或浏览器上下文通用）。"""
import time
from typing import Iterable, List, Mapping, Union

from config.settings import AUTH_COOKIE_NAMES

CookieLike = Mapping[str, Union[str, int, float]]


def has_auth_cookies(cookies: Iterable[CookieLike]) -> bool:
    """是否包含 uid + 任一有效登录令牌 Cookie。"""
    by_name = {c["name"]: c for c in cookies}
    uid = by_name.get("uid")
    if not uid or not uid.get("value"):
        return False
    for name in AUTH_COOKIE_NAMES:
        if name == "uid":
            continue
        item = by_name.get(name)
        if item and item.get("value"):
            return True
    return False


def auth_cookies_expired(cookies: List[CookieLike]) -> bool:
    """
    关键登录 Cookie 是否已过期。
    仅当存在带 expires 的 auth cookie 且全部已过期时返回 True。
    """
    auth = [c for c in cookies if c.get("name") in AUTH_COOKIE_NAMES]
    if not auth:
        return True

    now = time.time()
    for c in auth:
        exp = c.get("expires", -1)
        if exp == -1:
            continue
        if exp < now:
            return True
    return False
