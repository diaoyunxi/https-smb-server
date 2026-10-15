# -*- coding: utf-8 -*-
"""
速率限制中间件

基于滑动窗口的简单速率限制，防止 DoS 攻击 (CWE-770)。
使用内存存储，适用于单实例部署。多实例部署时建议替换为 Redis 后端。
"""

import logging
import os
import time
from collections import defaultdict
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# 速率限制配置（可通过环境变量覆盖）
RATE_LIMIT_REQUESTS = int(os.environ.get("HTTPS_SMB_RATE_LIMIT", "100"))
RATE_LIMIT_WINDOW = int(os.environ.get("HTTPS_SMB_RATE_WINDOW", "60"))


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    基于 IP 的滑动窗口速率限制中间件。
    默认限制每个 IP 在 60 秒窗口内最多 100 次请求。
    超限返回 HTTP 429 Too Many Requests。
    """

    def __init__(
        self,
        app,
        max_requests: int = RATE_LIMIT_REQUESTS,
        window_seconds: int = RATE_LIMIT_WINDOW,
        exempt_paths: set = None,
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.exempt_paths = exempt_paths or {"/api/health", "/docs", "/openapi.json"}
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._cleanup_counter = 0
        self._cleanup_interval = 1000

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _cleanup_expired(self, now: float):
        cutoff = now - self.window_seconds
        expired_ips = []
        for ip, timestamps in self._requests.items():
            self._requests[ip] = [t for t in timestamps if t > cutoff]
            if not self._requests[ip]:
                expired_ips.append(ip)
        for ip in expired_ips:
            del self._requests[ip]

    async def dispatch(self, request: Request, call_next: Callable):
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        now = time.time()
        client_ip = self._get_client_ip(request)
        cutoff = now - self.window_seconds

        self._cleanup_counter += 1
        if self._cleanup_counter >= self._cleanup_interval:
            self._cleanup_expired(now)
            self._cleanup_counter = 0

        recent = [t for t in self._requests[client_ip] if t > cutoff]
        self._requests[client_ip] = recent

        if len(recent) >= self.max_requests:
            retry_after = int(self.window_seconds - (now - recent[0])) + 1
            return JSONResponse(
                status_code=429,
                content={"success": False, "detail": "请求过于频繁，请稍后重试"},
                headers={"Retry-After": str(max(retry_after, 1))},
            )

        self._requests[client_ip].append(now)
        return await call_next(request)
