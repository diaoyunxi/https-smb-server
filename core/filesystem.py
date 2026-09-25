# -*- coding: utf-8 -*-
"""
文件系统操作核心模块
提供文件和目录的增删改查、移动、复制、搜索等功能
"""

import os
import shutil
import time
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.config import BASE_DIR, MAX_FILENAME_LENGTH, TEMP_CHUNK_DIR, CHUNK_SIZE


def _safe_path(requested_path: str) -> Path:
    """
    校验并安全化路径，防止目录遍历攻击

    :param requested_path: 用户请求的相对路径
    :return: 安全的绝对路径
    :raises ValueError: 路径不合法时抛出
    """
    if not requested_path:
        return BASE_DIR
    # 规范化路径
    clean = Path(requested).as_posix()
    # 拒绝包含 .. 的路径
    parts = [p for p in clean.split("/") if p and p != ".."]
    safe = BASE_DIR.joinpath(*parts).resolve()
    # 确保不会逃逸出根目录
    if not str(safe).startswith(str(BASE_DIR.resolve())):
        raise ValueError("路径不合法: 不允许访问根目录之外的内容")
    return safe


def _validate_filename(name: str) -> str:
    """
    校验文件名合法性

    :param name: 文件名
    :return: 校验后的文件名
    :raises ValueError: 文件名不合法时抛出
    """
    if not name or not name.strip():
        raise ValueError("文件名不能为空")
    # 移除首尾空格
    name = name.strip()
    if len(name) > MAX_FILENAME_LENGTH:
        raise ValueError(f"文件名过长，最大允许 {MAX_FILENAME_LENGTH} 个字符")
    # 禁止非法字符（Windows和Linux兼容）
    # 安全修复：添加 / 和 \ 防止文件名路径穿越（CWE-22）
    # 原列表仅含 Windows 非法字符，遗漏 Unix 路径分隔符 /，
    # 导致 simple_upload 等接口可通过含 / 的文件名写入任意子目录
    illegal = '/\\<>:"|?*\x00'
    for ch in illegal:
        if ch in name:
            raise ValueError(f"文件名包含非法字符: '{ch}'")
    if name in (".", ".."):
        raise ValueError("文件名不能为 '.' 或 '..'")
    return name


def _file_stat(path: Path) -> Dict[str, Any]:
    """
    获取文件/目录的元信息

    :param path: 文件路径
    :return: 包含元信息的字典
    """
    stat = path.stat()
    return {
        "name": path.name,
        "path": str(path.relative_to(BASE_DIR).as_posix()) if path != BASE_DIR else "/",
        "is_dir": path.is_dir(),
        "size": stat.st_size if path.is_file() else 0,
        "modified": stat.st_mtime,
        "created": stat.st_ctime,
        "extension": path.suffix.lower() if path.is_file() else "",
    }


def list_directory(dir_path: str = "", sort_by: str = "name",
                   sort_order: str = "asc") -> List[Dict[str, Any]]:
    """
    列出目录内容

    :param dir_path: 目录相对路径，空字符串表示根目录
    :param sort_by: 排序字段（name/size/modified）
    :param sort_order: 排序方向（asc/desc）
    :return: 文件信息列表
    :raises FileNotFoundError: 目录不存在时抛出
    """
    target = _safe_path(dir_path)
    if not target.exists():
        raise FileNotFoundError(f"目录不存在: {dir_path}")
    if not target.is_dir():
        raise NotADirectoryError(f"不是目录: {dir_path}")

    items = []
    for entry in sorted(target.iterdir()):
        # 跳过临时分块目录
        if entry.resolve() == TEMP_CHUNK_DIR.resolve():
            continue
        # 跳过隐藏文件（以.开头的）
        if entry.name.startswith(".") and entry.name != ".chunks":
            continue
        items.append(_file_stat(entry))

    # 排序
    reverse = sort_order.lower() == "desc"
    key_map = {
        "name": lambda x: x["name"].lower(),
        "size": lambda x: x["size"],
        "modified": lambda x: x["modified"],
    }
    key_func = key_map.get(sort_by.lower(), key_map["name"])
    items.sort(key=key_func, reverse=reverse)

    # 目录优先
    items.sort(key=lambda x: (not x["is_dir"],))

    return items


def create_directory(dir_path: str, name: str) -> Dict[str, Any]:
    """
    在指定目录下创建子目录

    :param dir_path: 父目录相对路径
    :param name: 新目录名称
    :return: 新目录的元信息
    """
    name = _validate_filename(name)
    parent = _safe_path(dir_path)
    if not parent.exists():
        raise FileNotFoundError(f"父目录不存在: {dir_path}")
    if not parent.is_dir():
        raise NotADirectoryError(f"不是目录: {dir_path}")

    new_dir = parent / name
    if new_dir.exists():
        raise FileExistsError(f"目录已存在: {name}")
    new_dir.mkdir(parents=False, exist_ok=False)
    return _file_stat(new_dir)


def get_file_info(file_path: str) -> Dict[str, Any]:
    """
    获取单个文件/目录的详细信息

    :param file_path: 文件相对路径
    :return: 文件元信息
    """
    target = _safe_path(file_path)
    if not target.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    return _file_stat(target)


def delete_path(file_path: str, recursive: bool = False) -> Dict[str, Any]:
    """
    删除文件或目录

    :param file_path: 文件相对路径
    :param recursive: 是否递归删除目录
    :return: 删除结果信息
    """
    target = _safe_path(file_path)
    if not target.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    info = _file_stat(target)
    if target.is_dir() and not recursive:
        # 检查目录是否为空
        contents = [e for e in target.iterdir() if not e.name.startswith(".")]
        if contents:
            raise OSError(f"目录非空，请使用递归删除: {file_path}")

    if target.is_dir():
        shutil.rmtree(target, ignore_errors=False)
    else:
        target.unlink()
    return {"deleted": True, "name": info["name"], "path": file_path}


def rename_path(file_path: str, new_name: str) -> Dict[str, Any]:
    """
    重命名文件或目录

    :param file_path: 文件相对路径
    :param new_name: 新名称
    :return: 重命名后的元信息
    """
    new_name = _validate_filename(new_name)
    target = _safe_path(file_path)
    if not target.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    new_path = target.parent / new_name
    if new_path.exists() and new_path != target:
        raise FileExistsError(f"目标名称已存在: {new_name}")

    target.rename(new_path)
    return _file_stat(new_path)


def move_path(src_path: str, dest_dir: str) -> Dict[str, Any]:
    """
    移动文件或目录到目标目录

    :param src_path: 源文件相对路径
    :param dest_dir: 目标目录相对路径
    :return: 移动后的元信息
    """
    src = _safe_path(src_path)
    dest = _safe_path(dest_dir)

    if not src.exists():
        raise FileNotFoundError(f"源文件不存在: {src_path}")
    if not dest.exists() or not dest.is_dir():
        raise NotADirectoryError(f"目标目录不存在: {dest_dir}")

    new_path = dest / src.name
    if new_path.exists() and new_path.resolve() != src.resolve():
        raise FileExistsError(f"目标位置已存在同名文件: {src.name}")

    shutil.move(str(src), str(dest))
    return _file_stat(new_path)


def copy_path(src_path: str, dest_dir: str) -> Dict[str, Any]:
    """
    复制文件或目录到目标目录

    :param src_path: 源文件相对路径
    :param dest_dir: 目标目录相对路径
    :return: 复制后的元信息
    """
    src = _safe_path(src_path)
    dest = _safe_path(dest_dir)

    if not src.exists():
        raise FileNotFoundError(f"源文件不存在: {src_path}")
    if not dest.exists() or not dest.is_dir():
        raise NotADirectoryError(f"目标目录不存在: {dest_dir}")

    new_path = dest / src.name
    if new_path.exists():
        raise FileExistsError(f"目标位置已存在同名文件: {src.name}")

    if src.is_dir():
        shutil.copytree(str(src), str(new_path))
    else:
        shutil.copy2(str(src), str(new_path))
    return _file_stat(new_path)


def search_files(query: str, dir_path: str = "") -> List[Dict[str, Any]]:
    """
    搜索文件和目录

    :param query: 搜索关键词
    :param dir_path: 搜索起始目录
    :return: 匹配的文件信息列表
    """
    target = _safe_path(dir_path)
    if not target.exists():
        raise FileNotFoundError(f"目录不存在: {dir_path}")
    if not target.is_dir():
        raise NotADirectoryError(f"不是目录: {dir_path}")

    query_lower = query.lower()
    results = []

    def _walk(directory: Path, depth: int = 0):
        """递归搜索目录"""
        if depth > 20:  # 限制递归深度，防止无限循环
            return
        try:
            for entry in directory.iterdir():
                # 跳过隐藏文件和临时目录
                if entry.name.startswith("."):
                    continue
                if entry.resolve() == TEMP_CHUNK_DIR.resolve():
                    continue
                if query_lower in entry.name.lower():
                    results.append(_file_stat(entry))
                if entry.is_dir():
                    _walk(entry, depth + 1)
        except PermissionError:
            pass

    _walk(target)
    return results


def get_storage_info() -> Dict[str, Any]:
    """
    获取存储空间信息

    :return: 存储信息字典
    """
    usage = shutil.disk_usage(str(BASE_DIR))
    return {
        "total": usage.total,
        "used": usage.used,
        "free": usage.free,
        "root_path": str(BASE_DIR),
    }


# =====================================================================
# 分块上传相关
# =====================================================================

def _get_chunk_dir(upload_id: str) -> Path:
    """获取分块上传的临时目录"""
    chunk_dir = TEMP_CHUNK_DIR / upload_id
    chunk_dir.mkdir(parents=True, exist_ok=True)
    return chunk_dir


def init_chunk_upload(file_path: str, file_name: str, file_size: int,
                      total_chunks: int, file_hash: str = "") -> Dict[str, Any]:
    """
    初始化分块上传会话

    :param file_path: 目标目录相对路径
    :param file_name: 文件名
    :param file_size: 文件总大小
    :param total_chunks: 总分块数
    :param file_hash: 文件完整MD5（可选，用于秒传判断）
    :return: 上传会话信息
    """
    file_name = _validate_filename(file_name)
    parent = _safe_path(file_path)

    if not parent.exists():
        raise FileNotFoundError(f"目标目录不存在: {file_path}")
    if not parent.is_dir():
        raise NotADirectoryError(f"不是目录: {file_path}")

    target_file = parent / file_name

    # 秒传判断：如果文件已存在且大小和MD5匹配
    if target_file.exists() and target_file.is_file():
        if file_hash:
            existing_hash = _compute_file_md5(target_file)
            if existing_hash == file_hash and target_file.stat().st_size == file_size:
                return {
                    "upload_id": "",
                    "status": "instant",
                    "message": "秒传成功，文件已存在",
                    "file": _file_stat(target_file),
                }

    # 生成上传会话ID
    import uuid
    upload_id = uuid.uuid4().hex

    # 保存会话元信息
    chunk_dir = _get_chunk_dir(upload_id)
    meta = {
        "file_name": file_name,
        "file_path": file_path,
        "file_size": file_size,
        "total_chunks": total_chunks,
        "file_hash": file_hash,
        "created_at": time.time(),
    }
    meta_path = chunk_dir / ".meta.json"
    import json
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return {
        "upload_id": upload_id,
        "status": "started",
        "chunk_size": CHUNK_SIZE,
        "message": f"上传会话已创建，共 {total_chunks} 块",
    }


def upload_chunk(upload_id: str, chunk_index: int, chunk_data: bytes) -> Dict[str, Any]:
    """
    上传单个分块

    :param upload_id: 上传会话ID
    :param chunk_index: 分块索引（从0开始）
    :param chunk_data: 分块数据
    :return: 上传结果
    """
    import json

    chunk_dir = _get_chunk_dir(upload_id)
    meta_path = chunk_dir / ".meta.json"

    if not meta_path.exists():
        raise FileNotFoundError(f"上传会话不存在或已过期: {upload_id}")

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    if chunk_index < 0 or chunk_index >= meta["total_chunks"]:
        raise ValueError(f"分块索引无效: {chunk_index}（有效范围: 0-{meta['total_chunks'] - 1}）")

    # 写入分块文件
    chunk_path = chunk_dir / f"chunk_{chunk_index:06d}"
    with open(chunk_path, "wb") as f:
        f.write(chunk_data)

    # 统计已上传分块数
    uploaded_chunks = len(list(chunk_dir.glob("chunk_*")))

    return {
        "upload_id": upload_id,
        "chunk_index": chunk_index,
        "chunk_size": len(chunk_data),
        "uploaded_chunks": uploaded_chunks,
        "total_chunks": meta["total_chunks"],
        "status": "partial" if uploaded_chunks < meta["total_chunks"] else "all_uploaded",
    }


def complete_chunk_upload(upload_id: str) -> Dict[str, Any]:
    """
    完成分块上传，合并所有分块

    :param upload_id: 上传会话ID
    :return: 合并后的文件信息
    """
    import json

    chunk_dir = _get_chunk_dir(upload_id)
    meta_path = chunk_dir / ".meta.json"

    if not meta_path.exists():
        raise FileNotFoundError(f"上传会话不存在或已过期: {upload_id}")

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    # 构建目标路径
    parent = _safe_path(meta["file_path"])
    target_file = parent / meta["file_name"]

    # 合并分块
    chunk_files = sorted(chunk_dir.glob("chunk_*"))
    if len(chunk_files) != meta["total_chunks"]:
        raise OSError(
            f"分块不完整: 已上传 {len(chunk_files)}/{meta['total_chunks']} 块"
        )

    with open(target_file, "wb") as f:
        for chunk_file in chunk_files:
            with open(chunk_file, "rb") as cf:
                # 分块读取写入，避免大分块内存占用
                while True:
                    data = cf.read(CHUNK_SIZE)
                    if not data:
                        break
                    f.write(data)

    # 验证MD5
    result = {"file": _file_stat(target_file)}
    if meta.get("file_hash"):
        actual_hash = _compute_file_md5(target_file)
        result["hash_match"] = actual_hash == meta["file_hash"]
        result["actual_hash"] = actual_hash
        if not result["hash_match"]:
            # MD5不匹配，删除文件并报错
            target_file.unlink()
            raise ValueError(
                f"文件校验失败: 期望MD5={meta['file_hash']}, 实际MD5={actual_hash}"
            )

    # 清理临时分块目录
    shutil.rmtree(chunk_dir, ignore_errors=True)

    return result


def cancel_chunk_upload(upload_id: str) -> Dict[str, Any]:
    """
    取消分块上传，清理临时文件

    :param upload_id: 上传会话ID
    :return: 取消结果
    """
    chunk_dir = _get_chunk_dir(upload_id)
    if chunk_dir.exists():
        shutil.rmtree(chunk_dir, ignore_errors=True)
    return {"upload_id": upload_id, "status": "cancelled"}


def _compute_file_md5(file_path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    """
    计算文件MD5

    :param file_path: 文件路径
    :param chunk_size: 读取块大小
    :return: MD5十六进制字符串
    """
    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        while True:
            data = f.read(chunk_size)
            if not data:
                break
            md5.update(data)
    return md5.hexdigest()


def get_upload_status(upload_id: str) -> Dict[str, Any]:
    """
    查询分块上传进度

    :param upload_id: 上传会话ID
    :return: 上传进度信息
    """
    import json

    chunk_dir = _get_chunk_dir(upload_id)
    meta_path = chunk_dir / ".meta.json"

    if not meta_path.exists():
        raise FileNotFoundError(f"上传会话不存在或已过期: {upload_id}")

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    uploaded_chunks = len(list(chunk_dir.glob("chunk_*")))
    uploaded_size = sum(f.stat().st_size for f in chunk_dir.glob("chunk_*"))

    return {
        "upload_id": upload_id,
        "file_name": meta["file_name"],
        "file_size": meta["file_size"],
        "uploaded_chunks": uploaded_chunks,
        "total_chunks": meta["total_chunks"],
        "uploaded_size": uploaded_size,
        "progress": round(uploaded_chunks / meta["total_chunks"] * 100, 1) if meta["total_chunks"] > 0 else 0,
        "status": "completed" if uploaded_chunks >= meta["total_chunks"] else "uploading",
    }


# =====================================================================
# 简单上传（小文件）
# =====================================================================

def simple_upload(dir_path: str, file_name: str, content: bytes,
                  overwrite: bool = False) -> Dict[str, Any]:
    """
    简单文件上传（非分块，适合小文件）

    :param dir_path: 目标目录相对路径
    :param file_name: 文件名
    :param content: 文件内容
    :param overwrite: 是否覆盖已存在文件
    :return: 文件元信息
    """
    file_name = _validate_filename(file_name)
    parent = _safe_path(dir_path)

    if not parent.exists():
        raise FileNotFoundError(f"目标目录不存在: {dir_path}")
    if not parent.is_dir():
        raise NotADirectoryError(f"不是目录: {dir_path}")

    target = parent / file_name
    if target.exists() and not overwrite:
        raise FileExistsError(f"文件已存在: {file_name}")

    with open(target, "wb") as f:
        f.write(content)

    return _file_stat(target)