# -*- coding: utf-8 -*-
"""
认证模块
提供可选的 Bearer Token 认证中间件

安全修复：原服务器所有 API 无任何认证，任何人可上传/下载/删除文件 (CWE-306)。

启用方式：设置环境变量 HTTPS_SMB_TOKEN=your-secret-token
未设置时保持原有行为（无认证），启动时打印警告。
"""

import os
import logging
from typing import Optional

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

# 从环境变量读取 token，未设置则为空（保持向后兼容）
_AUTH_TOKEN: Optional[str] = os.environ.get("HTTPS_SMB_TOKEN", "").strip() or None

if _AUTH_TOKEN is None:
    logger.warning(
        "⚠️ HTTPS_SMB_TOKEN 未设置，所有 API 无需认证即可访问！"
        "生产环境请务必设置此环境变量。"
    )

# Bearer token 安全依赖
_security = HTTPBearer(auto_error=False)


async def verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_security),
) -> Optional[str]:
    """
    验证 Bearer Token。
    
    - HTTPS_SMB_TOKEN 未设置时：跳过认证（向后兼容）
    - HTTPS_SMB_TOKEN 已设置时：请求必须携带匹配的 Bearer Token
    
    健康检查 (/api/health) 和静态页面 (/) 不需要认证。
    """
    if _AUTH_TOKEN is None:
        return None  # 未配置 token 时允许所有请求

    if credentials is None or credentials.credentials != _AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证失败：无效的 Bearer Token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


def is_auth_enabled() -> bool:
    """返回认证是否已启用"""
    return _AUTH_TOKEN is not None
