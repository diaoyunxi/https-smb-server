# 贡献指南

感谢你对 HTTPS SMB Server 项目的关注！

## 开发环境

```bash
# 克隆仓库
git clone https://github.com/diaoyunxi/https-smb-server.git
cd https-smb-server

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

## 代码规范

- 遵循 PEP 8 代码风格
- 使用 type hints 标注函数参数和返回值类型
- 为公共函数编写 docstring
- 提交前运行 `ruff check .` 检查代码质量

## 提交 PR

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/xxx`)
3. 提交变更 (`git commit -m 'feat: add xxx'`)
4. 推送到分支 (`git push origin feature/xxx`)
5. 创建 Pull Request

## 报告 Bug

请在 Issues 中描述：
- 复现步骤
- 期望行为
- 实际行为
- 环境信息（Python 版本、操作系统）
