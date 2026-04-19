# File Trigger

<div align="center">

[**English**](README.md) | 中文

![版本](https://img.shields.io/badge/版本-0.1.0-blue)
![许可证](https://img.shields.io/badge/许可证-MIT-green)
![Python](https://img.shields.io/badge/python-3.9+-blue)
![状态](https://img.shields.io/badge/状态-开发中-orange)

文件监控触发 Claude CLI 工具 - 当指定目录下的文件发生变化时，使用自定义提示词模板自动执行 Claude CLI 命令。

</div>

## 功能特性

- 🔍 监控路径变化（创建、修改、删除、移动）
    - 📁 **目录监控** - 递归监控整个目录
    - 📄 **单文件监控** - 监控单个文件的变化
- 🎯 **事件过滤** - 选择要监控的事件类型
- ⏱️ **智能防抖** - 将快速变化合并为单次触发（1秒延迟）
- 🤖 自动触发 Claude CLI 执行配置的提示词
- ⚙️ 支持多个监控路径，每个路径独立配置
- 📝 提示词支持变量替换（如 `{file}`、`{events}`）
- 🎯 支持文件扩展名过滤（仅目录模式）
- 🚫 支持排除模式（如 `.git`、`node_modules`）
- 🔄 跨平台支持（Linux、macOS、Windows）
- 🛡️ 权限控制和工具白名单，增强安全性
- 📊 **状态显示** - 使用 `--status` 查看配置和统计信息
- 📈 **活动跟踪** - 记录触发历史和每日统计

## 应用场景

### 📖 实时构建 LLM Wiki

与传统的定时任务（cron）不同，**ftrigger 提供实时的、事件驱动的自动化**。当新的源文件添加到您的 wiki 时：

- **即时处理**：文件创建后立即处理，无需等待下一个预定的间隔
- **动态内容**：您的 LLM Wiki 随着新内容的添加而自动更新
- **资源高效**：仅在发生实际更改时运行，节省计算资源

**LLM Wiki 配置示例：**

```yaml
watches:
  - path: /path/to/llm-wiki/raw/sources
    events: ["created"]
    prompt: "LLM Wiki 源目录有新文件 {file}。基于新内容和 CLAUDE.md，请处理并相应更新 wiki。"
    recursive: true
    permission_mode: bypassPermissions
    exclude_patterns:
      - ".git"
      - "__pycache__"
      - "*.tmp"
    allowed_tools:
      - "Read"
      - "Write"
      - "Edit"
      - "LSP"
```

**相比定时任务的优势：**
| 方面 | 定时任务（Cron） | 事件驱动（ftrigger） |
|------|------------------|---------------------|
| 响应时间 | 固定间隔（如每小时） | 即时（秒级） |
| 资源使用 | 无论是否有变化都运行 | 仅在需要时运行 |
| 可扩展性 | 空闲时浪费资源 | 随活动量扩展 |
| 用户体验 | 延迟更新 | 实时反馈 |

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
    events: ["modified"]
    prompt: "Review the changed file {file} and do something thing you want."
    recursive: true
    extensions: [".py", ".js", ".ts"]
```

### 2. 启动监控

```bash
# 启动监控（使用当前目录的 config.yaml）
ftrigger

# 显式指定配置文件
ftrigger -c /path/to/config.yaml

# 显示状态面板
ftrigger --status

# 显示详细日志
ftrigger -v
```

### 配置模式

ftrigger 支持两种不同的模式，配置行为不同：

**命令行模式**：
- 默认使用当前目录的 `config.yaml`
- 可以使用 `-c` 选项指定任意配置文件
- 忽略标准服务配置位置，除非通过 `-c` 显式指定
- 适用于临时监控和测试

**服务模式**：
- 根据服务类型使用固定的配置路径
- **用户服务**：`~/.config/ftrigger/config.yaml`
- **系统服务**：`/etc/ftrigger/config.yaml`
- 适用于长期后台监控

这种分离防止了服务和命令行实例之间的冲突。

## 作为服务运行

对于长期运行的监控，可以将 ftrigger 安装为 systemd 服务。

### 快速安装（Linux）

使用自动化安装脚本进行交互式模式选择：

```bash
# 交互式安装（首次使用推荐）
./install-service.sh

# 直接安装为用户服务
./install-service.sh --mode user

# 直接安装为系统服务
./install-service.sh --mode system

# 卸载服务
./install-service.sh --uninstall
```

安装程序会提示您选择：
- **[0] 用户服务** - 为当前用户安装（`~/.config/ftrigger/config.yaml`）
- **[1] 系统服务** - 全局安装（`/etc/ftrigger/config.yaml`）

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

详细文档请参考 [`ftrigger.systemd.tutorial.md`](./ftrigger.systemd.tutorial.md)。

## 配置说明

### 配置文件结构

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `log_level` | string | 否 | 日志级别：DEBUG, INFO, WARNING, ERROR（默认：INFO） |
| `watches` | list | 是 | 监控规则列表 |

### 监控规则配置

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `path` | string | 是 | 要监控的文件或目录路径（必须存在） |
| `prompt` | string | 是 | 触发时执行的提示词 |
| `events` | list | 是 | 要监控的事件类型：["created", "modified", "deleted", "moved"] |
| `recursive` | boolean | 否 | 是否递归监控子目录（默认：true，仅目录模式） |
| `extensions` | list | 否 | 只监控指定扩展名的文件（仅目录模式） |
| `permission_mode` | string | 否 | Claude CLI 权限模式（默认：default） |
| `allowed_tools` | list | 否 | 允许的工具白名单（可选） |
| `exclude_patterns` | list | 否 | 排除路径模式（仅目录模式） |

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
- `{events}` - 触发操作的事件类型：`created`、`modified`、`deleted`、`moved`

**`moved` 事件的专用变量：**
- `{src_path}` / `{src}` - 源路径（文件从哪里移动）
- `{dest_path}` / `{dest}` - 目标路径（文件移动到哪里）

示例：

```yaml
prompt: "Review the Python file {file} for bugs and improvements"
# 或使用事件类型
prompt: "文件 {events}：检查 {file} 的代码质量"
```

## 使用示例

### 监控单个文件

监控特定配置文件或重要文档：

```yaml
watches:
  - path: /etc/nginx/nginx.conf
    prompt: "Nginx 配置文件 {file} 已更改。请验证语法并检查潜在问题。"
    events: ["modified"]
    permission_mode: acceptEdits

  - path: /home/user/重要文档.md
    prompt: "文档 {file} 已修改。请审查并总结更改内容。"
    events: ["modified"]
    permission_mode: acceptEdits
```

**注意：** 监控单个文件时，`recursive` 和 `extensions` 选项会自动被忽略。

### 监控 Python 项目

```yaml
watches:
  - path: ./src
    prompt: "Analyze {file} for code quality issues and suggest refactoring opportunities."
    recursive: true
    permission_mode: acceptEdits
    extensions: [".py"]
```

### 监控文档变化

```yaml
watches:
  - path: ./docs
    prompt: "Check the documentation for clarity, consistency, and completeness."
    recursive: true
    permission_mode: acceptEdits
    extensions: [".md", ".rst"]
```

### 多路径监控

```yaml
watches:
  - path: ./backend
    prompt: "Review backend code changes for security issues."
    permission_mode: acceptEdits
    extensions: [".py"]

  - path: ./frontend
    prompt: "Review frontend code changes for accessibility and performance."
    permission_mode: acceptEdits
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

### 事件过滤

仅监控特定事件类型：

```yaml
watches:
  # 仅监控新文件创建
  - path: ./uploads
    prompt: "新文件已创建：{file}。请处理并分析。"
    events: ["created"]
    recursive: true
    permission_mode: acceptEdits

  # 监控创建和修改，忽略删除
  - path: ./src
    prompt: "文件 {events}：检查 {file} 的代码质量。"
    events: ["created", "modified"]
    extensions: [".py"]
    permission_mode: bypassPermissions
    allowed_tools:
      - "Read"
      - "LSP"
```

**支持的事件类型：**
- `created` - 文件/目录创建
- `modified` - 文件/目录修改
- `deleted` - 文件/目录删除
- `moved` - 文件/目录移动/重命名

**注意：** 如果未指定 `events` 字段，默认监控所有事件类型。

## 命令

| 命令 | 描述 |
|------|------|
| `ftrigger` | 使用当前目录的 `config.yaml` 启动监控 |
| `ftrigger -c/--config <path>` | 使用指定的配置文件启动监控 |
| `ftrigger --status` | 显示配置和统计面板 |
| `ftrigger -v` | 显示详细日志（DEBUG 级别） |
| `ftrigger -h, --help` | 显示帮助信息 |

## 工作原理

1. 使用 `watchdog` 库监控文件系统事件
2. 根据配置的事件类型（created、modified、deleted、moved）过滤事件
3. 应用防抖机制，将快速变化合并（1 秒延迟）
4. 构建并执行带有提示词变量的 `claude` 命令
5. 记录活动统计用于跟踪
6. 在独立线程中异步执行，不阻塞监控

## 防抖机制

为避免快速文件变化时多次触发（例如快速多次保存文件），ftrigger 使用智能防抖策略：

- **1 秒延迟**：事件发生后，等待 1 秒再触发
- **合并处理**：如果延迟窗口内再次发生事件，重置计时器
- **按事件类型跟踪**：每个 文件:事件类型 组合都有独立的计时器

这确保只有最终状态才会触发 Claude，减少不必要的 API 调用并提高效率。

## 常见问题

### Q: 如何停止监控？

- **如果是以服务运行**：使用 `systemctl --user stop ftrigger` 或相应的服务管理命令停止服务
- **如果是直接运行**：按 `Ctrl+C` 或发送 `SIGTERM` 信号以优雅关闭

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
│   ├── executor.py      # CLI 执行器
│   ├── status.py        # 状态显示
│   └── activity.py      # 活动跟踪
├── config.yaml          # 配置文件
├── requirements.txt     # Python 依赖
├── install-service.sh   # 服务安装脚本
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
