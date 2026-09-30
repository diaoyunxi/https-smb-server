#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
https-smb-server 主入口
基于 FastAPI 的 HTTPS 文件服务器，通过 cloudflared 暴露为 HTTPS
提供类 SMB/云盘 的文件管理功能

启动方式:
    python main.py

环境变量:
    HTTPS_SMB_ROOT    - 存储根目录（默认: ./data）
    HTTPS_SMB_HOST    - 监听地址（默认: 0.0.0.0）
    HTTPS_SMB_PORT    - 监听端口（默认: 8080）
    HTTPS_SMB_CHUNK_SIZE - 分块上传大小（默认: 8MB）
"""

import sys
import os

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path

from core.config import BASE_DIR, HOST, PORT
from server.routes.files import router as files_router
from server.routes.upload import router as upload_router
from server.routes.download import router as download_router

# =====================================================================
# 创建 FastAPI 应用
# =====================================================================
app = FastAPI(
    title="HTTPS SMB Server",
    description="基于 FastAPI 的 HTTPS 文件服务器，提供类 SMB/云盘 的文件管理功能",
    version="1.0.0",
)

# 注册 API 路由
app.include_router(files_router)
app.include_router(upload_router)
app.include_router(download_router)

# 静态文件目录
STATIC_DIR = Path(__file__).parent / "static"


# =====================================================================
# 页面路由
# =====================================================================

@app.get("/")
async def index():
    """
    返回前端主页面
    """
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse(
        content={
            "name": "HTTPS SMB Server",
            "version": "1.0.0",
            "docs": "/docs",
            "message": "前端页面未找到，请检查 static/index.html",
        }
    )


# =====================================================================
# 健康检查
# =====================================================================

@app.get("/api/health")
async def health_check():
    """
    健康检查接口
    """
    from core.filesystem import get_storage_info
    storage = get_storage_info()
    return {
        "success": True,
        "data": {
            "status": "ok",
            "version": "1.0.0",
            "storage": storage,
        },
    }


# =====================================================================
# 错误处理
# =====================================================================

from fastapi import Request
from fastapi.responses import JSONResponse as _JSONResponse


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    全局异常处理器，防止堆栈信息泄露
    """
    return _JSONResponse(
        status_code=500,
        content={"success": False, "detail": "服务器内部错误"},
    )


# =====================================================================
# 启动
# =====================================================================

def main():
    """
    启动 HTTP 服务器（配合 cloudflared 自动转为 HTTPS）
    """
    import uvicorn

    # 确保数据目录存在
    BASE_DIR.mkdir(parents=True, exist_ok=True)

    print(f"存储目录: {BASE_DIR.resolve()}")
    print(f"监听地址: {HOST}:{PORT}")
    print(f"访问地址: http://{HOST}:{PORT}")
    print(f"API 文档: http://{HOST}:{PORT}/docs")
    print("-" * 50)

    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        log_level="info",
        reload=False,
    )


if __name__ == "__main__":
    main()