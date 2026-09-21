"""
文件下载 API 路由
支持完整下载、分块下载（Range 请求）、批量下载（ZIP 打包）
"""

import io
import os
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse

from core.config import DOWNLOAD_CHUNK_SIZE
from core.filesystem import _safe_path

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

        # 处理 Range 请求
        range_header = request.headers.get("range") if request else None
        if range_header:
            # 解析 Range: bytes=start-end
            range_spec = range_header.replace("bytes=", "")
            parts = range_spec.split("-")
            start = int(parts[0]) if parts[0] else 0
            end = int(parts[1]) if parts[1] else file_size - 1

            if start >= file_size or end >= file_size or start > end:
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

        # 在内存中创建 ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in files_to_add:
                if file_path.is_file():
                    zf.write(file_path, file_path.name)
                elif file_path.is_dir():
                    for root, dirs, files in os.walk(file_path):
                        for file in files:
                            if file.startswith("."):
                                continue
                            full_path = Path(root) / file
                            arc_name = full_path.relative_to(file_path.parent)
                            zf.write(full_path, arc_name)

        zip_buffer.seek(0)
        import time
        zip_name = f"batch_download_{int(time.time())}.zip"

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{zip_name}",
                "Content-Length": str(zip_buffer.getbuffer().nbytes),
            },
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"打包下载失败: {str(e)}")
