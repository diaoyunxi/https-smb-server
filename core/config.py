# -*- coding: utf-8 -*-
"""
https-smb-server 配置模块
通过环境变量或 .env 文件配置
"""

import os
from pathlib import Path

# 存储根目录
BASE_DIR = Path(os.getenv("HTTPS_SMB_ROOT", "./data"))
BASE_DIR.mkdir(parents=True, exist_ok=True)

# 分块上传相关配置
CHUNK_SIZE = int(os.getenv("HTTPS_SMB_CHUNK_SIZE", str(8 * 1024 * 1024)))  # 8MB
TEMP_CHUNK_DIR = BASE_DIR / ".chunks"
TEMP_CHUNK_DIR.mkdir(parents=True, exist_ok=True)

# 服务配置
HOST = os.getenv("HTTPS_SMB_HOST", "0.0.0.0")
PORT = int(os.getenv("HTTPS_SMB_PORT", "8080"))

# 下载分块大小
DOWNLOAD_CHUNK_SIZE = int(os.getenv("HTTPS_SMB_DOWNLOAD_CHUNK", str(4 * 1024 * 1024)))  # 4MB

# 允许的文件名最大长度
MAX_FILENAME_LENGTH = 255

# 文件上传大小限制（无限制，仅受磁盘空间约束）
MAX_UPLOAD_SIZE = None

# 认证配置
# AUTH_TOKEN: Bearer Token，为空时禁用认证（不推荐用于公网环境）
# 设置方法: export HTTPS_SMB_AUTH_TOKEN="your-secret-token"
# 客户端请求时携带: Authorization: Bearer your-secret-token
AUTH_TOKEN = os.getenv("HTTPS_SMB_AUTH_TOKEN", "")
AUTH_ENABLED = bool(AUTH_TOKEN)

# 不需要认证的路径前缀（健康检查、前端页面、API 文档）
AUTH_EXEMPT_PATHS = ("/", "/api/health", "/docs", "/openapi.json", "/redoc", "/static")