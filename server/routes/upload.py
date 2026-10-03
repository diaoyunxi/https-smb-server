# -*- coding: utf-8 -*-
"""
文件上传 API 路由
支持简单上传和分块上传（断点续传）
"""

import os
import time
from fastapi import APIRouter, HTTPException, UploadFile, File, Query, Form
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional

from core.filesystem import (
    simple_upload,
    init_chunk_upload,
    upload_chunk,
    complete_chunk_upload,
    cancel_chunk_upload,
    get_upload_status,
    _safe_path,
)
from core.config import CHUNK_SIZE

router = APIRouter(prefix="/api/upload", tags=["文件上传"])


# =====================================================================
# 请求模型
# =====================================================================

class InitUploadRequest(BaseModel):
    """初始化分块上传请求"""
    path: str = Field(default="", description="目标目录相对路径")
    file_name: str = Field(..., min_length=1, max_length=255, description="文件名")
    file_size: int = Field(..., gt=0, description="文件总大小（字节）")
    file_hash: str = Field(default="", description="文件完整MD5，用于秒传判断")


class CompleteUploadRequest(BaseModel):
    """完成分块上传请求"""
    upload_id: str = Field(..., description="上传会话ID")


class CancelUploadRequest(BaseModel):
    """取消分块上传请求"""
    upload_id: str = Field(..., description="上传会话ID")


# =====================================================================
# 简单上传（小文件，非分块）
# =====================================================================

@router.post("/simple")
async def api_simple_upload(
    path: str = Form(default="", description="目标目录相对路径"),
    file: UploadFile = File(..., description="上传的文件"),
    overwrite: bool = Form(default=False, description="是否覆盖已存在文件"),
):
    """
    简单文件上传（适合小文件，单次请求完成）
    """
    try:
        content = await file.read()
        info = simple_upload(path, file.filename or "unnamed", content, overwrite)
        return {"success": True, "data": info}
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="上传失败，请稍后重试")


# =====================================================================
# 分块上传（大文件，支持断点续传）
# =====================================================================

@router.post("/init")
async def api_init_upload(req: InitUploadRequest):
    """
    初始化分块上传会话

    返回 upload_id，后续用此ID上传各分块。
    如果文件已存在且MD5匹配，自动秒传。
    """
    try:
        total_chunks = (req.file_size + CHUNK_SIZE - 1) // CHUNK_SIZE
        result = init_chunk_upload(
            req.path, req.file_name, req.file_size,
            total_chunks, req.file_hash,
        )
        return {"success": True, "data": result}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="初始化失败，请稍后重试")


@router.put("/chunk/{upload_id}/{chunk_index}")
async def api_upload_chunk(
    upload_id: str,
    chunk_index: int,
    chunk: UploadFile = File(..., description="分块数据"),
):
    """
    上传单个分块

    :param upload_id: 上传会话ID（由 /init 返回）
    :param chunk_index: 分块索引（从0开始）
    """
    try:
        data = await chunk.read()
        result = upload_chunk(upload_id, chunk_index, data)
        return {"success": True, "data": result}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="分块上传失败，请稍后重试")


@router.post("/complete")
async def api_complete_upload(req: CompleteUploadRequest):
    """
    完成分块上传，合并所有分块为完整文件
    """
    try:
        result = complete_chunk_upload(req.upload_id)
        return {"success": True, "data": result}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except OSError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="合并失败，请稍后重试")


@router.post("/cancel")
async def api_cancel_upload(req: CancelUploadRequest):
    """
    取消分块上传，清理临时文件
    """
    result = cancel_chunk_upload(req.upload_id)
    return {"success": True, "data": result}


@router.get("/status/{upload_id}")
async def api_upload_status(upload_id: str):
    """
    查询分块上传进度
    """
    try:
        result = get_upload_status(upload_id)
        return {"success": True, "data": result}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="查询上传状态失败，请稍后重试")