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
HOST = os.getenv("HTTPS_SMB_HOST", "127.0.0.1")
PORT = int(os.getenv("HTTPS_SMB_PORT", "8080"))

# 下载分块大小
DOWNLOAD_CHUNK_SIZE = int(os.getenv("HTTPS_SMB_DOWNLOAD_CHUNK", str(4 * 1024 * 1024)))  # 4MB

# 允许的文件名最大长度
MAX_FILENAME_LENGTH = 255

# 文件上传大小限制（默认 10GB，防止恶意上传超大文件填满磁盘导致 DoS）
# 可通过环境变量 HTTPS_SMB_MAX_UPLOAD_SIZE 调整，设为 0 表示不限制
_raw_upload_limit = os.getenv("HTTPS_SMB_MAX_UPLOAD_SIZE", "")
MAX_UPLOAD_SIZE = (
    None if _raw_upload_limit == "0" else int(_raw_upload_limit) if _raw_upload_limit else 10 * 1024 * 1024 * 1024
)

# 分块上传过期时间（秒），超过此时间未完成的上传将被自动清理
CHUNK_UPLOAD_EXPIRY_SECONDS = int(os.getenv("HTTPS_SMB_CHUNK_EXPIRY", str(24 * 3600)))  # 默认 24 小时