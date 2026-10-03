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
MAX_UPLOAD_SIZE = int(os.getenv("HTTPS_SMB_MAX_UPLOAD", str(500 * 1024 * 1024)))  # 500MB