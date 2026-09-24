# -*- coding: utf-8 -*-
"""
文件下载 API 路由
支持完整下载、分块下载（Range 请求）、批量下载（ZIP 打包）
"""

import os
import io
import zipfile
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from typing import Optional, List

from core.filesystem import _safe_path, _file_stat
from core.config import BASE_DIR, DOWNLOAD_CHUNK_SIZE

router = APIRouter(prefix="/api/download", tags=["文件下载"])


def _get_download_headers(file_path: Path, file_name: str) -> dict:
    """
    构建下载响应头

    :param file_path: 文件路径
    :param file_name: 显示的文件名
    :return: 响应头字典
    """
    import urllib.parse
    encoded_name = urllib.parse.quote(file_name)
    return {
        "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}",
        "Content-Type": "application/octet-stream",
        "Accept-Ranges": "bytes",
        "Cache-Control": "no-cache",
    }


@router.get("/file")
async def api_download_file(
    path: str = Query(..., description="文件相对路径"),
    request: Request = None,
):
    """
    下载文件
    支持 Range 请求（分块下载/断点续传下载）
    """
    try:
        target = _safe_path(path)
        if not target.exists():
            raise HTTPException(status_code=404, detail=f"文件不存在: {path}")
        if not target.is_file():
            raise HTTPException(status_code=400, detail=f"不是文件: {path}")

        file_size = target.stat().st_size
        headers = _get_download_headers(target, target.name)

        # 处理 Range 请求 (RFC 7233)
        range_header = request.headers.get("range") if request else None
        if range_header and range_header.startswith("bytes="):
            range_spec = range_header[6:]  # 去掉 "bytes="
            parts = range_spec.split("-")
            
            if len(parts) != 2:
                raise HTTPException(
                    status_code=416,
                    detail="无效的 Range 格式",
                    headers={"Content-Range": f"bytes */{file_size}"},
                )
            
            start_str, end_str = parts[0].strip(), parts[1].strip()
            
            # 解析 start 和 end
            if start_str == "" and end_str == "":
                # 无效: "bytes=-"
                raise HTTPException(
                    status_code=416,
                    detail="无效的 Range 格式",
                    headers={"Content-Range": f"bytes */{file_size}"},
                )
            elif start_str == "":
                # 后缀范围: "bytes=-500" 表示最后 500 字节
                suffix_length = int(end_str)
                if suffix_length <= 0:
                    raise HTTPException(
                        status_code=416,
                        detail="后缀长度必须为正数",
                        headers={"Content-Range": f"bytes */{file_size}"},
                    )
                start = max(0, file_size - suffix_length)
                end = file_size - 1
            else:
                start = int(start_str)
                end = int(end_str) if end_str else file_size - 1
                
                # RFC 7233: end 超过 file_size-1 时自动截断
                if end >= file_size:
                    end = file_size - 1
                
                if start > end or start < 0:
                    raise HTTPException(
                        status_code=416,
                        detail="请求范围无效",
                        headers={"Content-Range": f"bytes */{file_size}"},
                    )

            content_length = end - start + 1

            def _range_stream():
                """分块流式读取"""
                with open(target, "rb") as f:
                    f.seek(start)
                    remaining = content_length
                    while remaining > 0:
                        chunk = f.read(min(DOWNLOAD_CHUNK_SIZE, remaining))
                        if not chunk:
                            break
                        remaining -= len(chunk)
                        yield chunk

            return StreamingResponse(
                _range_stream(),
                status_code=206,
                headers={
                    **headers,
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Content-Length": str(content_length),
                },
            )

        # 完整下载
        return FileResponse(
            str(target),
            filename=target.name,
            headers=headers,
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")


@router.get("/batch")
async def api_download_batch(
    paths: str = Query(..., description="要下载的文件路径列表，逗号分隔"),
):
    """
    批量下载文件（打包为 ZIP）
    路径用逗号分隔，例如: paths=/a.txt,/b/c.pdf
    """
    try:
        path_list = [p.strip() for p in paths.split(",") if p.strip()]
        if not path_list:
            raise HTTPException(status_code=400, detail="未指定要下载的文件")

        # 解析所有文件
        files_to_add = []
        for p in path_list:
            target = _safe_path(p)
            if not target.exists():
                raise HTTPException(status_code=404, detail=f"文件不存在: {p}")
            files_to_add.append(target)

        # 使用临时文件流式创建 ZIP（避免大文件 OOM）
        import tempfile
        import time
        
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        tmp_path = tmp_file.name
        
        try:
            with zipfile.ZipFile(tmp_file, "w", zipfile.ZIP_DEFLATED) as zf:
                for file_path in files_to_add:
                    if file_path.is_file():
                        # 流式写入，避免一次性加载到内存
                        with open(file_path, "rb") as src:
                            zf.writestr(
                                zipfile.ZipInfo(file_path.name, date_time=time.localtime(file_path.stat().st_mtime)[:6]),
                                src.read(),
                                compress_type=zipfile.ZIP_DEFLATED,
                            )
                    elif file_path.is_dir():
                        for root, dirs, files in os.walk(file_path):
                            for file in files:
                                if file.startswith("."):
                                    continue
                                full_path = Path(root) / file
                                arc_name = full_path.relative_to(file_path.parent)
                                with open(full_path, "rb") as src:
                                    zf.writestr(
                                        zipfile.ZipInfo(str(arc_name), date_time=time.localtime(full_path.stat().st_mtime)[:6]),
                                        src.read(),
                                        compress_type=zipfile.ZIP_DEFLATED,
                                    )
            tmp_file.close()
            
            zip_name = f"batch_download_{int(time.time())}.zip"
            
            def _stream_and_cleanup():
                try:
                    with open(tmp_path, "rb") as f:
                        while chunk := f.read(DOWNLOAD_CHUNK_SIZE):
                            yield chunk
                finally:
                    os.unlink(tmp_path)
            
            file_size = os.path.getsize(tmp_path)
            return StreamingResponse(
                _stream_and_cleanup(),
                media_type="application/zip",
                headers={
                    "Content-Disposition": f"attachment; filename*=UTF-8''{zip_name}",
                    "Content-Length": str(file_size),
                },
            )
        except Exception:
            # 出错时清理临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"打包下载失败: {str(e)}")
