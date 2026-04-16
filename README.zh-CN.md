# File Trigger

<div align="center">

[**English**](README.md) | 中文

![版本](https://img.shields.io/badge/版本-0.1.0-blue)
![许可证](https://img.shields.io/badge/许可证-MIT-green)
![Python](https://img.shields.io/badge/python-3.9+-blue)
![状态](https://img.shields.io/badge/状态-开发中-orange)

文件监控触发 Claude CLI 工具 - 当指定目录下的文件发生变化时，自动执行 Claude CLI 命令。

</div>

## 功能特性

- 🔍 监控指定目录的文件变化（创建、修改）
- 🤖 自动触发 Claude CLI 执行配置的提示词
- ⚙️ 支持多个监控路径，每个路径独立配置
- 🎯 支持文件扩展名过滤
- 📝 提示词支持变量替换（如 `{file}`）
- 🚫 支持排除模式（如 `.git`、`node_modules`）
- 🔄 跨平台支持（Linux、macOS、Windows）
- 🛡️ 权限控制和工具白名单，增强安全性
- 📚 **分层配置** - 系统级、用户级、项目级配置

## 安装

### 全局安装（推荐）

```bash
# 克隆仓库
git clone https://github.com/Youpen-y/ftrigger
cd ftrigger

# 全局安装
pip install .

# 或以可编辑模式安装（用于开发）
pip install -e .
```

安装后可以在任何位置直接运行 `ftrigger`：

```bash
ftrigger
ftrigger --config /path/to/config.yaml
ftrigger -v
```

### 从源码运行（开发模式）

```bash
# 克隆仓库
git clone https://github.com/Youpen-y/ftrigger
cd ftrigger

# 创建虚拟环境（推荐）
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# 或 .venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 使用 python -m 运行
python -m ftrigger
```

### 系统要求

- Python 3.9+
- Claude CLI（需要已安装并配置）

## 快速开始

### 1. 创建配置文件

在项目目录中创建 `config.yaml`：

```yaml
log_level: INFO

watches:
  - path: /path/to/your/project
    prompt: "Review the changed file {file} and suggest improvements."
    recursive: true
    extensions: [".py", ".js", ".ts"]
```

### 2. 启动监控

```bash
# 自动发现并合并配置（项目 -> 用户 -> 系统）
ftrigger

# 或显式指定配置文件
ftrigger --config /path/to/config.yaml

# 显示详细日志
ftrigger -v
```

### 配置层次

ftrigger 支持分层配置，自动合并：

| 层级 | 路径 | 优先级 |
|------|------|--------|
| **系统级** | `/etc/ftrigger/config.yaml` | 低 |
| **用户级** | `~/.config/ftrigger/config.yaml` | 中 |
| **项目级** | `./config.yaml` 或 `--config` | 高 |

高优先级配置覆盖低优先级配置，所有层级的 `watches` 会合并。

## 作为服务运行

对于长期运行的监控，可以将 ftrigger 安装为 systemd 用户服务。

### 快速安装（Linux）

使用自动化安装脚本：

```bash
# 安装单实例服务（推荐）
./install-service.sh

# 使用自定义配置安装
./install-service.sh --config /path/to/config.yaml

# 卸载服务
./install-service.sh --uninstall
```

### 手动安装

```bash
# 复制 service 文件
mkdir -p ~/.config/systemd/user/
cp ftrigger.service ~/.config/systemd/user/

# 编辑 service 文件中的路径
nano ~/.config/systemd/user/ftrigger.service

# 安装并启动
systemctl --user daemon-reload
systemctl --user enable ftrigger
systemctl --user start ftrigger
```

### 服务管理

```bash
# 查看状态
systemctl --user status ftrigger

# 查看日志
journalctl --user -u ftrigger -f

# 重启
systemctl --user restart ftrigger

# 停止
systemctl --user stop ftrigger
```

### 多实例（高级）

用于隔离的监控环境：

```bash
# 安装模板服务
./install-service.sh --multi-instance

# 创建配置
cp config.yaml ~/.config/ftrigger/dev.yaml
cp config.yaml ~/.config/ftrigger/prod.yaml

# 启动实例
systemctl --user start ftrigger@dev
systemctl --user start ftrigger@prod
```

详细文档请参考 `ftrigger.systemd.tutorial.md`。

## 配置说明

### 配置文件结构

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `log_level` | string | 否 | 日志级别：DEBUG, INFO, WARNING, ERROR（默认：INFO） |
| `watches` | list | 是 | 监控规则列表 |

### 监控规则配置

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `path` | string | 是 | 要监控的目录路径（必须存在且为目录） |
| `prompt` | string | 是 | 触发时执行的提示词 |
| `recursive` | boolean | 否 | 是否递归监控子目录（默认：true） |
| `extensions` | list | 否 | 只监控指定扩展名的文件（可选） |
| `permission_mode` | string | 否 | Claude CLI 权限模式（默认：default） |
| `allowed_tools` | list | 否 | 允许的工具白名单（可选） |
| `exclude_patterns` | list | 否 | 排除路径模式（可选） |

### 权限模式 (permission_mode)

控制 Claude CLI 的权限行为：

| 模式 | 说明 |
|------|------|
| `default` | 默认模式 |
| `auto` | 自动模式 |
| `acceptEdits` | 自动接受编辑操作 |
| `dontAsk` | 不询问，自动授予权限 |
| `bypassPermissions` | 跳过所有权限检查（谨慎使用） |

### 工具白名单 (allowed_tools)

限制 Claude 可以使用的工具，提高安全性。常用工具：

- `Read` - 读取文件
- `Write` - 写入文件
- `Edit` - 编辑文件
- `Bash` - 执行 shell 命令
- `Glob` - 文件模式匹配
- `Grep` - 内容搜索
- `LSP` - 使用语言服务器协议
- `AskUserQuestion` - 向用户提问

支持通配符限制，如 `Bash(git:*)` 只允许 git 相关命令。

示例：

```yaml
allowed_tools:
  - "Read"
  - "Bash(git:*)"
  - "LSP"
```

### 排除模式 (exclude_patterns)

指定要排除的路径模式，支持通配符：

```yaml
exclude_patterns:
  - ".git"
  - "node_modules"
  - "*.log"
  - "__pycache__"
```

### 提示词变量

提示词中支持以下变量：

- `{file}` - 变化的文件完整路径
- `{path}` - 同 `{file}`

示例：

```yaml
prompt: "Review the Python file {file} for bugs and improvements"
```

## 使用示例

### 监控 Python 项目

```yaml
watches:
  - path: ./src
    prompt: "Analyze {file} for code quality issues and suggest refactoring opportunities."
    recursive: true
    extensions: [".py"]
```

### 监控文档变化

```yaml
watches:
  - path: ./docs
    prompt: "Check the documentation for clarity, consistency, and completeness."
    recursive: true
    extensions: [".md", ".rst"]
```

### 多路径监控

```yaml
watches:
  - path: ./backend
    prompt: "Review backend code changes for security issues."
    extensions: [".py"]

  - path: ./frontend
    prompt: "Review frontend code changes for accessibility and performance."
    extensions: [".js", ".ts", ".jsx", ".tsx"]
```

### 使用权限和工具限制

```yaml
watches:
  # 只读代码审查 - 只允许读取工具
  - path: ./src
    prompt: "Review {file} for code quality issues."
    extensions: [".py"]
    permission_mode: bypassPermissions
    allowed_tools:
      - "Read"
      - "LSP"

  # Git 自动提交 - 允许 git 命令和文件编辑
  - path: ./repo
    prompt: "当文件变化时，创建 git commit 并推送"
    extensions: [".py", ".js"]
    permission_mode: bypassPermissions
    allowed_tools:
      - "Bash(git:*)"
      - "Read"
      - "Edit"
      - "Write"
```

## 工作原理

1. 使用 `watchdog` 库监控文件系统事件
2. 当检测到文件创建或修改时，根据配置过滤事件
3. 构建并执行 `claude -p <prompt>` 命令
4. 在独立线程中异步执行，不阻塞监控

## 防抖机制

为避免短时间内多次触发，同一文件在 5 秒内只会触发一次。

## 常见问题

### Q: 如何停止监控？

按 `Ctrl+C` 或发送 `SIGTERM` 信号即可优雅退出。

### Q: 监控不到文件变化？

检查：
1. 配置文件中的路径是否正确且存在
2. 文件扩展名是否匹配
3. 日志级别是否设置为 DEBUG 以查看详细信息

### Q: Claude CLI 未找到？

确保 Claude CLI 已安装并在系统 PATH 中：

```bash
which claude  # Linux/macOS
where claude  # Windows
```

## 项目结构

```
ftrigger/
├── ftrigger/
│   ├── __init__.py      # 包初始化
│   ├── __main__.py      # 支持 python -m ftrigger
│   ├── main.py          # 主入口
│   ├── config.py        # 配置管理
│   ├── watcher.py       # 文件监控
│   └── executor.py      # CLI 执行器
├── config.yaml          # 配置文件
├── requirements.txt     # Python 依赖
└── README.md            # 本文档
```

## 开发

```bash
# 运行（开发模式）
python -m ftrigger

# 使用自定义配置
python -m ftrigger --config my-config.yaml
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
