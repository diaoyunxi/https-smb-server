# -*- coding: utf-8 -*-
"""
文件和目录操作 API 路由
提供文件系统的增删改查、移动、复制、搜索等接口
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional

from core.filesystem import (
    list_directory,
    create_directory,
    get_file_info,
    delete_path,
    rename_path,
    move_path,
    copy_path,
    search_files,
    get_storage_info,
)

router = APIRouter(prefix="/api", tags=["文件操作"])


# =====================================================================
# 请求/响应模型
# =====================================================================

class CreateDirRequest(BaseModel):
    """创建目录请求"""
    path: str = Field(default="", description="父目录相对路径，空字符串表示根目录")
    name: str = Field(..., min_length=1, max_length=255, description="新目录名称")


class RenameRequest(BaseModel):
    """重命名请求"""
    path: str = Field(..., description="文件/目录相对路径")
    new_name: str = Field(..., min_length=1, max_length=255, description="新名称")


class MoveRequest(BaseModel):
    """移动请求"""
    src: str = Field(..., description="源文件/目录相对路径")
    dest: str = Field(..., description="目标目录相对路径")


class CopyRequest(BaseModel):
    """复制请求"""
    src: str = Field(..., description="源文件/目录相对路径")
    dest: str = Field(..., description="目标目录相对路径")


class DeleteRequest(BaseModel):
    """删除请求"""
    path: str = Field(..., description="文件/目录相对路径")
    recursive: bool = Field(default=False, description="是否递归删除目录")


class BatchDeleteRequest(BaseModel):
    """批量删除请求"""
    paths: List[str] = Field(..., min_length=1, description="要删除的文件/目录路径列表")
    recursive: bool = Field(default=False, description="是否递归删除目录")


# =====================================================================
# 接口实现
# =====================================================================

@router.get("/files")
async def api_list_files(
    path: str = Query(default="", description="目录相对路径"),
    sort_by: str = Query(default="name", description="排序字段: name/size/modified"),
    sort_order: str = Query(default="asc", description="排序方向: asc/desc"),
):
    """
    列出目录内容
    """
    try:
        items = list_directory(path, sort_by, sort_order)
        return {"success": True, "data": items}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except NotADirectoryError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/files/info")
async def api_file_info(
    path: str = Query(..., description="文件/目录相对路径"),
):
    """
    获取单个文件/目录的详细信息
    """
    try:
        info = get_file_info(path)
        return {"success": True, "data": info}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/files/mkdir")
async def api_create_directory(req: CreateDirRequest):
    """
    创建目录
    """
    try:
        info = create_directory(req.path, req.name)
        return {"success": True, "data": info}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/files/rename")
async def api_rename(req: RenameRequest):
    """
    重命名文件或目录
    """
    try:
        info = rename_path(req.path, req.new_name)
        return {"success": True, "data": info}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/files/move")
async def api_move(req: MoveRequest):
    """
    移动文件或目录
    """
    try:
        info = move_path(req.src, req.dest)
        return {"success": True, "data": info}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/files/copy")
async def api_copy(req: CopyRequest):
    """
    复制文件或目录
    """
    try:
        info = copy_path(req.src, req.dest)
        return {"success": True, "data": info}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/files/delete")
async def api_delete(req: DeleteRequest):
    """
    删除文件或目录
    """
    try:
        result = delete_path(req.path, req.recursive)
        return {"success": True, "data": result}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except OSError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/files/batch-delete")
async def api_batch_delete(req: BatchDeleteRequest):
    """
    批量删除文件或目录
    """
    results = []
    errors = []
    for path in req.paths:
        try:
            result = delete_path(path, req.recursive)
            results.append(result)
        except Exception as e:
            errors.append({"path": path, "error": str(e)})
    return {"success": len(errors) == 0, "data": {"deleted": results, "errors": errors}}


@router.get("/files/search")
async def api_search(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    path: str = Query(default="", description="搜索起始目录"),
):
    """
    搜索文件和目录
    """
    try:
        items = search_files(q, path)
        return {"success": True, "data": items}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/storage")
async def api_storage_info():
    """
    获取存储空间信息
    """
    info = get_storage_info()
    return {"success": True, "data": info}