> [← 返回文档目录](../README.md) ｜ 本分册由 `README.md` 的「API 接口」章节拆分而来。

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
