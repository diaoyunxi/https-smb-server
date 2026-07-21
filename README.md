# HTTPS SMB Server

基于 FastAPI 的 HTTPS 文件服务器，通过 Cloudflare Tunnel 自动转为 HTTPS，提供类 SMB/云盘的完整文件管理功能。

## 功能特性

- **文件管理**: 浏览、上传、下载、重命名、移动、复制、删除文件和目录
- **大文件支持**: 分块上传（8MB/块），支持断点续传和秒传（MD5 判断）
- **批量操作**: 批量删除、批量下载（自动打包 ZIP）
- **搜索**: 递归搜索文件和目录
- **拖拽上传**: 拖拽文件/文件夹到页面即可上传
- **现代 UI**: 深色主题、列表/网格视图切换、排序、面包屑导航
- **下载断点续传**: 支持 HTTP Range 请求
- **快捷键**: Delete 删除、Ctrl+A 全选、F2 重命名、Backspace 返回上级
- **存储监控**: 顶栏实时显示磁盘使用情况
- **API 文档**: 自动生成 Swagger UI (`/docs`)

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python main.py
```

默认监听 `0.0.0.0:8080`，数据存储在 `./data` 目录。

### 3. 配合 Cloudflare Tunnel 使用 HTTPS

```bash
# 安装 cloudflared
cloudflared tunnel --url http://localhost:8080
```

Cloudflare Tunnel 会自动提供一个 HTTPS URL，无需手动配置证书。

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `HTTPS_SMB_ROOT` | 存储根目录 | `./data` |
| `HTTPS_SMB_HOST` | 监听地址 | `0.0.0.0` |
| `HTTPS_SMB_PORT` | 监听端口 | `8080` |
| `HTTPS_SMB_CHUNK_SIZE` | 分块上传大小（字节） | `8388608` (8MB) |
| `HTTPS_SMB_DOWNLOAD_CHUNK` | 下载流式块大小（字节） | `4194304` (4MB) |

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/files` | 列出目录内容 |
| GET | `/api/files/info` | 获取文件信息 |
| GET | `/api/files/search` | 搜索文件 |
| POST | `/api/files/mkdir` | 创建目录 |
| POST | `/api/files/rename` | 重命名 |
| POST | `/api/files/move` | 移动 |
| POST | `/api/files/copy` | 复制 |
| POST | `/api/files/delete` | 删除 |
| POST | `/api/files/batch-delete` | 批量删除 |
| POST | `/api/upload/simple` | 简单上传（小文件） |
| POST | `/api/upload/init` | 初始化分块上传 |
| PUT | `/api/upload/chunk/{id}/{index}` | 上传分块 |
| POST | `/api/upload/complete` | 完成分块上传 |
| POST | `/api/upload/cancel` | 取消分块上传 |
| GET | `/api/upload/status/{id}` | 查询上传进度 |
| GET | `/api/download/file` | 下载文件（支持 Range） |
| GET | `/api/download/batch` | 批量下载（ZIP 打包） |
| GET | `/api/storage` | 存储空间信息 |
| GET | `/api/health` | 健康检查 |

完整 API 文档请访问 `/docs`。

## 项目结构

```
https-smb-server/
├── main.py                    # 主入口
├── requirements.txt           # Python 依赖
├── README.md                  # 项目说明
├── core/
│   ├── __init__.py
│   ├── config.py              # 配置管理
│   └── filesystem.py          # 文件系统操作核心
├── server/
│   ├── __init__.py
│   └── routes/
│       ├── __init__.py
│       ├── files.py           # 文件操作路由
│       ├── upload.py          # 上传路由
│       └── download.py        # 下载路由
├── static/
│   └── index.html             # 前端界面
└── data/                      # 文件存储目录（运行时自动创建）
```

## 技术栈

- **后端**: Python 3.8+ / FastAPI / Uvicorn
- **前端**: 原生 HTML + CSS + JavaScript（无框架依赖）
- **HTTPS**: Cloudflare Tunnel（零配置自动 HTTPS）

## 许可证

MIT License