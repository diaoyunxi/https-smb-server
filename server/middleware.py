# -*- coding: utf-8 -*-
"""
认证中间件
通过 API Key 保护所有 /api/ 端点
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import API_KEY


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """
    API Key 认证中间件

    对 /api/ 开头的请求检查 X-API-Key 或 Authorization: Bearer 头。
    静态文件和健康检查不需要认证。
    """

    # 不需要认证的路径前缀
    PUBLIC_PATHS = {"/", "/health", "/api/health", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next):
        # 未配置 API Key 时跳过认证
        if not API_KEY:
            return await call_next(request)

        # 静态路径和健康检查不认证
        path = request.url.path
        if path in self.PUBLIC_PATHS or path == "/api/health":
            return await call_next(request)

        # 非 /api/ 路径不认证（静态文件等）
        if not path.startswith("/api/"):
            return await call_next(request)

        # 提取 API Key
        key = request.headers.get("X-API-Key", "")
        if not key:
            auth = request.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                key = auth[7:]

        # 验证
        if key != API_KEY:
            return JSONResponse(
                status_code=401,
                content={"success": False, "error": "未授权: 请提供有效的 API Key"},
            )

        return await call_next(request)
