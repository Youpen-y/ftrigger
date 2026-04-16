# 设计文档

## 文件事件细分设计讨论

### 背景

当前实现对所有文件变化事件（created, modified）使用统一的处理方式。问题是：是否需要针对不同事件类型提供不同的配置？

### 场景分析

#### 支持细分的理由 ✅

1. **不同操作需要不同响应**
   - **新增文件**：检查结构、命名规范、是否需要文档、模板是否合适
   - **修改文件**：审查改动、检查是否引入问题、代码质量
   - **删除文件**：更新引用、清理资源、检查依赖

2. **更精细的控制场景**
   - 只监控新增，忽略修改（如新文件模板检查）
   - 只监控修改，忽略新增（如代码审查）
   - 不同操作需要完全不同的提示词

3. **更好的自动化**
   - 新增文件时自动创建配套文件
   - 修改文件时自动运行测试
   - 删除文件时自动更新文档

#### 不需要细分的理由 ❌

1. **复杂度大幅增加**
   - 配置文件层级变深
   - 用户理解成本提高
   - 维护成本增加

2. **实际需求有限**
   - 大多数场景下，对文件变化的处理是相似的
   - "文件有变化 → 分析它" 覆盖了 80% 的需求

3. **技术现实**
   - 编辑器保存文件时，往往同时触发 `created` 和 `modified` 事件
   - 事件顺序和数量因编辑器而异，难以精确区分
   - 临时文件、备份文件可能产生额外事件

4. **现有方案已够用**
   - 可以在提示词中让 Claude 自己判断发生了什么
   - 简单的统一处理覆盖大多数场景

### 当前决策（MVP）

**不实现事件细分**，原因：

1. ✅ **简单直观** - 一份配置，一种处理
2. ✅ **覆盖大多数场景** - 代码审查、文档检查等
3. ✅ **易于理解** - 用户不需要想太多
4. ✅ **降低维护成本** - 代码和配置都更简洁

### 未来增强方案

如果用户反馈有此需求，可以考虑以下实现方式：

#### 方案 A：完整的事件配置

```yaml
watches:
  - path: ./src
    prompt: "默认处理"  # fallback
    events:  # 可选，不配置则使用统一处理
      created:
        prompt: "检查新文件的设计和结构"
        extensions: [".py", ".js"]
      modified:
        prompt: "审查代码改动"
        extensions: [".py", ".js"]
      deleted:
        prompt: "清理相关引用"
        extensions: [".py", ".js"]
```

#### 方案 B：事件类型变量

```yaml
watches:
  - path: ./src
    prompt: "文件 {event_type}: 处理 {file}"
    # {event_type} 会被替换为 "created", "modified", "deleted"
```

#### 方案 C：事件过滤器

```yaml
watches:
  - path: ./src
    prompt: "只处理新增文件"
    events: ["created"]  # 只监控创建事件

  - path: ./src
    prompt: "只处理修改"
    events: ["modified"]  # 只监控修改事件
```

### 实现注意事项

1. **事件去重**
   - 编辑器可能同时触发多个事件
   - 需要防抖机制避免重复触发

2. **事件顺序**
   - 不能保证事件按预期顺序到达
   - 需要考虑事件乱序的情况

3. **向后兼容**
   - 如果添加此功能，需要保持现有配置的兼容性
   - 未配置细分时应使用统一处理

### 相关文件

- `ftrigger/watcher.py` - 当前事件处理实现
- `ftrigger/config.py` - 配置加载逻辑

### 决策日期

2026-04-14

---

## 后台运行模式设计讨论

### 背景

当前 ftrigger 在前台运行，需要占用一个终端窗口。问题是：是否应该支持后台运行（daemon 模式）？

### 前台 vs 后台对比

#### 前台运行（当前实现）

```bash
python -m ftrigger --config config.yaml
```

**优点**：
- ✅ 简单直观，开发调试方便
- ✅ 日志实时可见
- ✅ 易于理解和控制

**缺点**：
- ❌ 占用终端窗口
- ❌ 关闭终端就停止
- ❌ 不适合长期运行

#### 后台运行需求

**典型场景**：
- 长期监控代码变化，自动触发审查
- 作为开发环境的一部分持续运行
- 不想占用专门的终端窗口

### 解决方案

#### 方案 A：用户自己后台化（当前方案）

```bash
# 使用 nohup
nohup python -m ftrigger --config config.yaml > /var/log/ftrigger.log 2>&1 &

# 使用 screen/tmux
screen -dmS ftrigger python -m ftrigger --config config.yaml

# 使用 systemd（生产环境）
systemctl --user start ftrigger
```

**评价**：简单但不友好，需要用户自己处理。

#### 方案 B：内置 daemon 模式

```bash
# 添加 --daemon 选项
python -m ftrigger --daemon --config config.yaml

# 添加 PID 文件管理
python -m ftrigger --daemon --pid-file /var/run/ftrigger.pid

# 添加状态管理
python -m ftrigger --status
python -m ftrigger --stop
```

**评价**：更友好，但增加了代码复杂度。

#### 方案 C：systemd 集成（生产环境）⭐ 推荐

提供预配置的 systemd service 文件：

**单实例（推荐）**：
```bash
# 复制 service 文件
cp ftrigger.service ~/.config/systemd/user/

# 编辑配置（路径等）
nano ~/.config/systemd/user/ftrigger.service

# 启用并启动
systemctl --user daemon-reload
systemctl --user enable ftrigger
systemctl --user start ftrigger
```

**多实例（高级）**：
```bash
# 使用模板支持多个配置
cp ftrigger@.service ~/.config/systemd/user/

# 为每个项目创建配置
cp config.yaml ~/.config/ftrigger/project1.yaml
cp config.yaml ~/.config/ftrigger/project2.yaml

# 启动多个实例
systemctl --user enable ftrigger@project1
systemctl --user enable ftrigger@project2
systemctl --user start ftrigger@project1
systemctl --user start ftrigger@project2
```

**评价**：
- ✅ **零代码成本** - 只需提供配置文件
- ✅ **生产级质量** - 自动重启、日志管理、资源限制
- ✅ **Linux 标准** - 符合系统管理最佳实践
- ✅ **开箱即用** - 提供预配置模板
- ✅ **多实例支持** - 一个模板运行多个配置

### 当前决策（MVP）

**优先方案 C（systemd 集成）**，原因：

1. ✅ **开箱即用** - 提供预配置的 service 文件
2. ✅ **生产级质量** - 自动重启、日志轮转、资源限制
3. ✅ **零代码成本** - 只需提供配置文件，不修改代码
4. ✅ **Linux 标准** - 符合系统管理最佳实践
5. ✅ **多实例支持** - 使用模板可运行多个配置

同时保留方案 A（用户自选）作为备选，满足不同用户需求。

### 推荐使用方式

#### 开发环境

使用 screen 或 tmux：

```bash
# 创建会话
screen -dmS ftrigger

# 附加到会话
screen -r ftrigger

# 在会话中运行
python -m ftrigger --config config.yaml

# 分离会话：Ctrl+A, D
```

#### 生产环境

提供 systemd service 模板：

```bash
# 创建 user service
mkdir -p ~/.config/systemd/user/
cp ftrigger.service ~/.config/systemd/user/

# 启动服务
systemctl --user daemon-reload
systemctl --user enable ftrigger
systemctl --user start ftrigger
```

### 未来增强方案

如果用户反馈强烈，可以考虑：

1. **添加 `--daemon` 选项**
   - 自动后台运行
   - 写入日志文件
   - 记录 PID 文件

2. **添加状态管理命令**
   - `--status`：查看运行状态
   - `--stop`：停止后台进程
   - `--restart`：重启后台进程

3. **提供配置生成工具**
   - 自动生成 systemd service 文件
   - 根据系统环境调整配置

### 实现注意事项

1. **日志管理**
   - 后台运行时日志必须写入文件
   - 支持日志轮转
   - 提供日志查看命令

2. **进程管理**
   - PID 文件管理
   - 防止重复启动
   - 优雅关闭处理

3. **用户权限**
   - 支持 user-level service
   - 不需要 root 权限
   - 安全的文件权限

### 相关文件

- `ftrigger/main.py` - 主入口，信号处理
- `ftrigger.service` - systemd service 模板（单实例）
- `ftrigger@.service` - systemd service 模板（多实例）
- `ftrigger.systemd.example.md` - systemd 配置指南

### 决策日期

2026-04-14

---

## 多编码智能体支持设计讨论

### 背景

当前实现专门针对 Claude CLI，但市场上存在多个编码智能体工具。问题是：是否应该支持其他编码智能体，以及如何设计通用架构？

### 主流编码智能体对比

| 工具 | CLI 命令 | 特点 | 权限控制 |
|------|----------|------|----------|
| **Claude CLI** | `claude -p` | Anthropic 官方，多模态 | `--permission-mode`, `--allowed-tools` |
| **Cursor** | `cursor-cli` | VS Code 集成，IDE 原生 | 配置文件 |
| **Continue** | `continue` | VS Code/JetBrains 插件 | 配置文件 |
| **Aider** | `aider` | Git 集成，自动提交 | `--yes` 标志 |
| **OpenAI Codex** | API 调用 | 无官方 CLI | API Key 限制 |
| **Cline** | `cline` | VS Code 扩展 | 配置文件 |
| **Codeium** | `codeium` | 多 IDE 支持 | 配置文件 |

### 设计方案

#### 方案 A：抽象命令执行器（推荐）⭐

创建抽象接口，不同的智能体作为插件实现：

```python
# ftrigger/executors/base.py
class BaseExecutor(ABC):
    """Base executor interface for coding assistants"""

    @abstractmethod
    def execute(self, prompt: str, file_path: str, context: ExecutionContext) -> None:
        """Execute the coding assistant with given prompt"""
        pass

    @abstractmethod
    def build_command(self, prompt: str, context: ExecutionContext) -> list[str]:
        """Build CLI command for the assistant"""
        pass
```

```python
# ftrigger/executors/claude.py
class ClaudeExecutor(BaseExecutor):
    """Claude CLI executor"""

    def build_command(self, prompt: str, context: ExecutionContext) -> list[str]:
        cmd = ["claude"]
        if context.permissions:
            cmd.extend(context.permissions.to_args())
        if context.allowed_tools:
            cmd.extend(["--allowed-tools", ",".join(context.allowed_tools)])
        cmd.extend(["-p", prompt])
        return cmd
```

```python
# ftrigger/executors/aider.py
class AiderExecutor(BaseExecutor):
    """Aider executor"""

    def build_command(self, prompt: str, context: ExecutionContext) -> list[str]:
        cmd = ["aider"]
        if context.auto_confirm:
            cmd.append("--yes")
        if context.file_path:
            cmd.extend(["--file", context.file_path])
        cmd.extend(["--message", prompt])
        return cmd
```

**配置文件示例：**

```yaml
# config.yaml
executor:
  type: claude  # claude, aider, openai, custom
  options:
    permission_mode: bypassPermissions
    allowed_tools: ["Read", "Edit"]

watches:
  - path: ./src
    executor:
      type: aider
      options:
        auto_confirm: true
    prompt: "Review {file}"
```

**优点：**
- ✅ 可扩展性强，易于添加新的智能体
- ✅ 配置清晰，每个监控规则可以指定不同的智能体
- ✅ 符合开闭原则
- ✅ 便于测试和维护

**缺点：**
- ❌ 初期开发成本较高
- ❌ 需要维护多个执行器

#### 方案 B：命令模板配置

使用简单的命令模板替换：

```yaml
executors:
  claude:
    command: "claude --permission-mode {permission_mode} -p \"{prompt}\""

  aider:
    command: "aider --yes --file {file} --message \"{prompt}\""

  openai:
    command: "python -m openai_cli --model {model} \"{prompt}\""

watches:
  - path: ./src
    executor: claude
    prompt: "Review {file}"
```

**优点：**
- ✅ 实现简单
- ✅ 用户可以自定义任何命令
- ✅ 灵活性高

**缺点：**
- ❌ 参数替换容易出现安全问题
- ❌ 缺乏类型检查和验证
- ❌ 复杂场景难以处理

#### 方案 C：仅支持 Claude（当前方案）

保持当前设计，只支持 Claude CLI：

```yaml
watches:
  - path: ./src
    permission_mode: bypassPermissions
    allowed_tools: ["Read", "Edit"]
    prompt: "Review {file}"
```

**优点：**
- ✅ 代码简洁，维护成本低
- ✅ 专注做好一件事
- ✅ Claude CLI 功能强大，覆盖大多数场景

**缺点：**
- ❌ 无法使用其他智能体
- ❌ 用户可能有其他偏好

### 智能体能力对比

| 能力 | Claude | Aider | Cursor | Continue |
|------|--------|-------|--------|----------|
| 文件读取 | ✅ | ✅ | ✅ | ✅ |
| 文件编辑 | ✅ | ✅ | ✅ | ✅ |
| Shell 执行 | ✅ | ✅ | ❌ | ❌ |
| 多文件操作 | ✅ | ✅ | ✅ | ✅ |
| Git 集成 | ❌ | ✅ | ✅ | ❌ |
| 权限控制 | ✅ | 部分 | ❌ | ❌ |
| 工具白名单 | ✅ | ❌ | ❌ | ❌ |
| 多模态 | ✅ | ❌ | ❌ | ❌ |

### 当前决策（MVP）

**保持 Claude CLI 专用**，原因：

1. ✅ **Claude CLI 最强大** - 工具白名单、权限控制、多模态
2. ✅ **聚焦核心价值** - 文件监控触发，而非多工具集成
3. ✅ **降低复杂度** - 减少维护成本
4. ✅ **质量优于数量** - 把一件事做到极致

### 未来增强方案

#### 阶段 1：抽象化内部架构

不改变外部 API，内部重构为可扩展架构：

```python
# 内部抽象，用户无感知
class BaseExecutor:
    ...

class ClaudeExecutor(BaseExecutor):
    ...  # 当前实现
```

**目标：** 为未来扩展打好基础，不影响现有用户。

#### 阶段 2：添加 Aider 支持

Aider 与 Claude 互补性强（Git 集成），可作为第二个支持的智能体：

```yaml
watches:
  - path: ./src
    executor: aider  # 新增
    prompt: "Review and improve {file}"
```

**优先级：** 中 - 取决于用户反馈。

#### 阶段 3：开放插件系统

允许用户编写自己的执行器：

```python
# my_executor.py
from ftrigger import BaseExecutor

class MyExecutor(BaseExecutor):
    def build_command(self, prompt, context):
        return ["my-tool", "--prompt", prompt]
```

```yaml
# config.yaml
executors:
  - my_executor.MyExecutor

watches:
  - path: ./src
    executor: MyExecutor
    prompt: "Process {file}"
```

**优先级：** 低 - 高级功能，按需实现。

### 实现路线图

```
当前 (v0.1.0)
└── Claude CLI only
    ↓
v0.2.0 (内部重构)
└── 抽象 BaseExecutor 接口
└── ClaudeExecutor 实现
    ↓
v0.3.0 (多智能体)
└── AiderExecutor 实现
└── 配置文件支持 executor 字段
    ↓
v0.4.0 (插件系统)
└── 用户自定义执行器
└── 执行器发现机制
```

### 安全考虑

1. **命令注入防护**
   - 使用 `subprocess.list2cmdline` 或类似机制
   - 参数验证和转义
   - 禁止 shell=True

2. **权限隔离**
   - 不同执行器使用不同的权限配置
   - 敏感操作需要用户确认

3. **沙箱执行**
   - 考虑使用容器或虚拟环境
   - 限制文件系统访问范围

### 相关文件

- `ftrigger/executor.py` - 当前 Claude 执行器实现
- `ftrigger/executors/` - 未来多执行器目录（待创建）
- `ftrigger/config.py` - 配置加载逻辑

### 决策日期

2026-04-15

---

## 三层配置系统设计

### 背景

当前只支持单一配置文件，用户需要在每个项目中复制配置。问题是：如何支持系统级、用户级和项目级的配置层次？

### 设计目标

1. **配置复用** - 用户级和系统级配置可被多个项目共享
2. **优先级清晰** - 项目配置覆盖用户配置，用户配置覆盖系统配置
3. **向后兼容** - 保持现有单一配置文件的使用方式
4. **简单直观** - 自动查找配置，无需复杂设置

### 配置层次

| 层级 | 配置路径 | 用途 | 优先级 |
|------|----------|------|--------|
| **系统级** | `/etc/ftrigger/config.yaml` | 全局默认配置 | 低 |
| **用户级** | `~/.config/ftrigger/config.yaml` | 用户个人默认 | 中 |
| **项目级** | `./config.yaml` 或 `--config` | 项目特定配置 | 高 |

### 合并规则

```
系统级 + 用户级 + 项目级 = 最终配置
```

- **log_level**：高优先级覆盖低优先级
- **watches**：所有层的 watches 合并

### 配置查找顺序

```python
# 1. 命令行指定（跳过自动查找）
ftrigger --config /path/to/custom.yaml

# 2. 自动查找（按优先级）
ftrigger  # 查找：项目 -> 用户 -> 系统
```

### 实现细节

#### Config.merge() 方法

```python
@dataclass
class Config:
    log_level: str = "INFO"
    watches: list[WatchConfig] = field(default_factory=list)

    def merge(self, other: "Config") -> "Config":
        """合并高优先级配置到当前配置"""
        log_level = other.log_level if other.log_level != "INFO" else self.log_level
        watches = self.watches + other.watches
        return Config(log_level=log_level, watches=watches)
```

#### 查找逻辑

```python
def load_config(config_path: Optional[str] = None) -> Config:
    if config_path:
        # 显式指定：只加载该文件
        return load_single_config(config_path)

    # 自动查找：按优先级加载并合并
    configs = []
    if system_config_exists():
        configs.append(load_system_config())
    if user_config_exists():
        configs.append(load_user_config())
    if project_config_exists():
        configs.append(load_project_config())

    return merge_configs(configs)
```

### 使用示例

#### 示例 1：系统级默认配置

```yaml
# /etc/ftrigger/config.yaml
log_level: INFO

watches:
  - path: /tmp
    prompt: "Generic review"
    extensions: [".py", ".js"]
```

#### 示例 2：用户级个人配置

```yaml
# ~/.config/ftrigger/config.yaml
log_level: DEBUG  # 覆盖系统级

watches:
  - path: ~/projects
    prompt: "My project review"
    extensions: [".py"]
```

#### 示例 3：项目级特定配置

```yaml
# ./config.yaml
# 继承 log_level = DEBUG（来自用户级）

watches:
  - path: ./src
    prompt: "This project specific review"
    extensions: [".py", ".ts"]
    permission_mode: bypassPermissions
```

#### 最终合并结果

```yaml
log_level: DEBUG  # 来自用户级

watches:
  - path: /tmp           # 系统级
    prompt: "Generic review"
    extensions: [".py", ".js"]

  - path: ~/projects     # 用户级
    prompt: "My project review"
    extensions: [".py"]

  - path: ./src          # 项目级
    prompt: "This project specific review"
    extensions: [".py", ".ts"]
    permission_mode: bypassPermissions
```

### 向后兼容

```python
# 旧方式：仍然有效
ftrigger --config my-config.yaml

# 新方式：自动查找
ftrigger  # 自动查找并合并配置
```

### 当前状态

✅ **已实现** - v0.1.0

### 相关文件

- `ftrigger/config.py` - 配置加载和合并逻辑
- `/etc/ftrigger/config.yaml` - 系统级配置（需手动创建）
- `~/.config/ftrigger/config.yaml` - 用户级配置（需手动创建）
- `./config.yaml` - 项目级配置

### 决策日期

2026-04-15

---

## 用户友好的日志和状态管理设计讨论

### 背景

当前 ftrigger 的日志查看对用户不够友好：

1. **命令复杂** - 需要记住 `journalctl --user -u ftrigger -f` 等复杂命令
2. **信息过载** - DEBUG 模式下输出太多，难以找到关键信息
3. **格式混乱** - 多个线程的日志混在一起，难以阅读
4. **无快捷方式** - 没有简单的命令查看关键信息

### 问题分析

#### 当前日志查看的问题

| 问题 | 说明 | 影响 |
|------|------|------|
| **命令复杂** | systemd 日志需要 `journalctl --user -u ftrigger -f` | 新用户难以使用 |
| **信息过载** | DEBUG 级别输出所有文件系统事件 | 难以找到关键信息 |
| **格式不清晰** | 纯文本日志，缺乏视觉层次 | 阅读体验差 |
| **无状态概览** | 无法快速了解当前监控状态 | 需要查看配置文件 |

### 设计方案

#### 方案 A：添加 `--status` 参数（推荐）⭐

提供简洁的状态面板和最近活动：

```bash
# 显示当前状态
ftrigger --status

# 或者使用子命令形式
ftrigger status
```

**输出示例：**

```
📊 ftrigger 状态面板
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
运行状态:     ✅ 正在运行
配置文件:     /home/user/.config/ftrigger/config.yaml
日志级别:     INFO

监控路径 (2 个):
├─ 📁 /tmp/ftrigger_test1
│  └─ 扩展名: .py, .txt, .md
│  └─ 权限: auto (工具: Read)
└─ 📁 /tmp/ftrigger_test2
   └─ 扩展名: .js, .txt, .md
   └─ 权限: auto (工具: Read)

今日统计:
├─ 文件创建: 15 次
├─ 文件修改: 42 次
└─ Claude 触发: 57 次

最近活动:
✅ [20:15:22] /tmp/ftrigger_test1/test.py 已修改
✅ [20:14:45] /tmp/ftrigger_test1/subfolder/nested.py 已创建
✅ [20:14:29] /tmp/ftrigger_test1/note1.txt 已创建
✅ [20:14:29] /tmp/ftrigger_test2/note2.txt 已创建
❌ [20:13:30] Claude CLI 执行失败: claude 命令未找到
```

**实现要点：**

```python
def show_status(config: Config):
    """显示状态面板"""
    print("📊 ftrigger 状态面板")
    print("━" * 40)

    # 运行状态
    print(f"运行状态:     ✅ 正在运行")
    print(f"配置文件:     {config_path}")
    print(f"日志级别:     {config.log_level}")

    # 监控路径
    print(f"\n监控路径 ({len(config.watches)} 个):")
    for i, watch in enumerate(config.watches, 1):
        print(f"├─ 📁 {watch.path}")
        print(f"│  └─ 扩展名: {', '.join(watch.extensions) or '全部'}")
        print(f"│  └─ 权限: {watch.permission_mode}")
        if watch.allowed_tools:
            print(f"│  └─ 工具: {', '.join(watch.allowed_tools)}")

    # 统计信息（需要持久化）
    print("\n今日统计:")
    print("├─ 文件创建: 15 次")
    print("├─ 文件修改: 42 次")
    print("└─ Claude 触发: 57 次")
```

#### 方案 B：添加 `--logs` 参数

简化日志查看：

```bash
# 查看最近的日志（默认 20 条）
ftrigger --logs

# 实时查看
ftrigger --logs --follow

# 查看最近 N 条
ftrigger --logs --last 50

# 过滤级别
ftrigger --logs --level ERROR
ftrigger --logs --level WARNING

# 搜索关键词
ftrigger --logs --grep "test.py"
```

**输出格式改进：**

```
# 当前格式
2026-04-16 20:13:29 - ftrigger.watcher - INFO - File created: /tmp/test.py

# 改进后（带图标和颜色）
✅ [20:13:29] 文件已创建: /tmp/test.py
🤖 [20:13:29] 已触发 Claude CLI: Test: Detected change...
❌ [20:13:30] 执行失败: claude 命令未找到
⚠️  [20:13:31] 配置警告: 排除模式 '*.log' 不匹配任何文件
```

**实现要点：**

```python
def show_logs(last_n=20, follow=False, level=None, grep=None):
    """显示友好的日志输出"""

    # 日志级别到图标的映射
    icons = {
        "INFO": "✅",
        "WARNING": "⚠️ ",
        "ERROR": "❌",
        "DEBUG": "🔍",
    }

    # 消息类型到中文的映射
    messages = {
        "File created": "文件已创建",
        "File modified": "文件已修改",
        "Triggering Claude CLI": "已触发 Claude CLI",
    }
```

#### 方案 C：添加 `--interactive` 模式（高级功能）

提供交互式界面：

```bash
ftrigger --interactive
# 或简写
ftrigger -i
```

**交互界面示例：**

```
📊 ftrigger 交互模式
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

输入 'help' 查看可用命令

ftrigger> status
[显示状态面板]

ftrigger> logs
[显示最近日志]

ftrigger> logs --follow
[实时跟踪日志，按 Ctrl+C 退出]

ftrigger> watches
列出所有监控规则:
1. /tmp/ftrigger_test1 (.py, .txt, .md)
2. /tmp/ftrigger_test2 (.js, .txt, .md)

ftrigger> test /tmp/ftrigger_test1
测试监控: /tmp/ftrigger_test1
[创建测试文件并验证监控是否工作]

ftrigger> reload
重新加载配置文件...

ftrigger> quit
正在停止监控...
再见！
```

**实现要点：**

```python
import cmd
import readline

class FTriggerInteractive(cmd.Cmd):
    """交互式命令行界面"""

    prompt = "ftrigger> "
    intro = "📊 ftrigger 交互模式\n输入 'help' 查看可用命令"

    def __init__(self, config):
        super().__init__()
        self.config = config

    def do_status(self, args):
        """显示状态面板"""
        show_status(self.config)

    def do_logs(self, args):
        """显示日志"""
        # 解析参数并显示日志
        pass

    def do_watches(self, args):
        """列出所有监控规则"""
        for i, watch in enumerate(self.config.watches, 1):
            print(f"{i}. {watch.path} ({', '.join(watch.extensions) or '全部'})")

    def do_test(self, args):
        """测试指定路径的监控"""
        # 创建测试文件并验证
        pass

    def do_reload(self, args):
        """重新加载配置"""
        print("正在重新加载配置...")
        # 重新加载配置
        print("✅ 配置已重新加载")

    def do_quit(self, args):
        """退出程序"""
        print("正在停止监控...")
        return True

    def do_exit(self, args):
        """退出程序（同 quit）"""
        return self.do_quit(args)
```

### 命令行参数设计

更新后的参数结构：

```python
parser = argparse.ArgumentParser(
    description="File Trigger - Monitor file changes and trigger Claude CLI"
)

# 主要模式（互斥）
mode_group = parser.add_mutually_exclusive_group()
mode_group.add_argument(
    "--status", "-s",
    action="store_true",
    help="显示状态面板并退出"
)
mode_group.add_argument(
    "--logs", "-l",
    action="store_true",
    help="显示日志"
)
mode_group.add_argument(
    "--interactive", "-i",
    action="store_true",
    help="进入交互模式"
)

# 日志选项
parser.add_argument(
    "--follow", "-f",
    action="store_true",
    help="实时跟踪日志（配合 --logs 使用）"
)
parser.add_argument(
    "--last", "-n",
    type=int,
    default=20,
    help="显示最近 N 条日志（配合 --logs 使用，默认: 20）"
)
parser.add_argument(
    "--level",
    choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    help="过滤日志级别"
)
parser.add_argument(
    "--grep",
    help="搜索包含指定关键词的日志"
)

# 配置选项
parser.add_argument(
    "-c", "--config",
    default="config.yaml",
    help="配置文件路径（默认: config.yaml）"
)
parser.add_argument(
    "-v", "--verbose",
    action="store_true",
    help="显示详细日志"
)
parser.add_argument(
    "-V", "--version",
    action="version",
    version=f"%(prog)s {__version__}"
)
```

### 使用示例对比

#### 当前方式

```bash
# 启动监控
python -m ftrigger

# 查看状态
systemctl --user status ftrigger

# 查看日志
journalctl --user -u ftrigger -f
journalctl --user -u ftrigger -n 20
journalctl --user -u ftrigger | grep "error"
```

#### 改进后

```bash
# 启动监控（默认行为）
ftrigger

# 快速查看状态
ftrigger --status

# 快速查看日志
ftrigger --logs
ftrigger --logs --follow
ftrigger --logs --last 50
ftrigger --logs --grep "error"

# 交互模式
ftrigger --interactive
ftrigger -i
```

### 功能优先级

| 功能 | 优先级 | 复杂度 | 价值 |
|------|--------|--------|------|
| **--status** | 高 | 低 | ⭐⭐⭐⭐⭐ |
| **--logs** | 高 | 低 | ⭐⭐⭐⭐⭐ |
| **--interactive** | 中 | 中 | ⭐⭐⭐ |
| 统计信息持久化 | 低 | 高 | ⭐⭐ |
| 日志格式改进 | 低 | 低 | ⭐⭐ |

### 实现路线图

```
v0.2.0 (用户体验改进)
├── 添加 --status 参数
│   ├── 状态面板显示
│   ├── 监控规则列表
│   └── 最近活动摘要
├── 添加 --logs 参数
│   ├── 友好的日志格式
│   ├── 过滤和搜索选项
│   └── 实时跟踪模式
└── 改进日志格式
    ├── 添加图标
    ├── 简化消息
    └── 彩色输出（可选）
    ↓
v0.3.0 (交互模式)
├── 添加 --interactive 参数
│   ├── 命令行界面
│   ├── 内置命令
│   └── 测试功能
└── 统计信息持久化
    ├── 记录事件计数
    ├── 持久化存储
    └── 趋势分析（可选）
```

### 统计信息持久化设计（可选）

为了支持统计功能，需要持久化事件记录：

```python
# 使用简单的 JSON 文件存储
import json
from datetime import datetime
from pathlib import Path

class StatsManager:
    """统计信息管理器"""

    def __init__(self, stats_file: Path):
        self.stats_file = stats_file
        self.stats = self._load()

    def _load(self) -> dict:
        """加载统计数据"""
        if self.stats_file.exists():
            return json.loads(self.stats_file.read_text())
        return {"events": [], "counts": {}}

    def record_event(self, event_type: str, file_path: str):
        """记录事件"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "file": file_path,
        }
        self.stats["events"].append(event)

        # 更新计数
        today = datetime.now().date().isoformat()
        if today not in self.stats["counts"]:
            self.stats["counts"][today] = {}
        self.stats["counts"][today][event_type] = \
            self.stats["counts"][today].get(event_type, 0) + 1

        # 只保留最近 7 天的事件
        cutoff = datetime.now() - timedelta(days=7)
        self.stats["events"] = [
            e for e in self.stats["events"]
            if datetime.fromisoformat(e["timestamp"]) > cutoff
        ]

        self._save()

    def get_today_counts(self) -> dict:
        """获取今日统计"""
        today = datetime.now().date().isoformat()
        return self.stats["counts"].get(today, {})

    def get_recent_events(self, n=10) -> list:
        """获取最近的事件"""
        return self.stats["events"][-n:]
```

### 向后兼容

所有新功能都是可选的，不影响现有使用方式：

```bash
# 现有方式仍然有效
python -m ftrigger --config config.yaml
python -m ftrigger -v

# 新功能是可选的增强
ftrigger --status      # 不启动监控，只显示状态
ftrigger --logs        # 不启动监控，只显示日志
ftrigger               # 启动监控（默认行为）
```

### 相关文件

- `ftrigger/main.py` - 添加新的命令行参数和处理逻辑
- `ftrigger/stats.py` - 统计信息管理（新文件，可选）
- `ftrigger/interactive.py` - 交互式界面（新文件，可选）
- `README.md` - 更新使用文档

### 决策日期

2026-04-16

---

## 基于监控路径的日志过滤和查看设计讨论

### 背景

当 ftrigger 同时监控多个路径时，所有日志混在一起输出，导致以下问题：

1. **日志混杂** - 多个路径的日志事件交织在一起，难以区分
2. **定位困难** - 想要查看特定路径的活动时，需要手动过滤
3. **统计不便** - 无法快速了解某个特定路径的监控活动情况
4. **调试困难** - 某个路径出现问题时，难以快速定位

### 使用场景

#### 场景 1：多项目监控

用户同时监控多个项目目录：

```yaml
watches:
  - path: /home/user/projects/backend
    prompt: "Review backend code"
    extensions: [".py"]

  - path: /home/user/projects/frontend
    prompt: "Review frontend code"
    extensions: [".js", ".ts"]

  - path: /home/user/projects/docs
    prompt: "Check documentation"
    extensions: [".md"]
```

用户想快速查看：
- 前端项目的活动
- 后端项目的错误
- 文档项目的所有事件

#### 场景 2：不同环境监控

用户同时监控开发和生产环境：

```yaml
watches:
  - path: /home/user/dev-env
    prompt: "Dev environment changes"
    log_level: DEBUG

  - path: /home/user/prod-env
    prompt: "Production environment changes"
    log_level: WARNING
```

用户想区分开发和生产环境的日志。

### 设计方案

#### 方案 A：添加 `--watch` 或 `--path` 过滤器（推荐）⭐

在 `--logs` 和 `--status` 命令中添加路径过滤选项：

```bash
# 查看特定监控路径的日志
ftrigger --logs --watch /tmp/ftrigger_test1

# 使用路径别名（需要配置）
ftrigger --logs --watch backend
ftrigger --logs --watch frontend

# 查看多个路径的日志
ftrigger --logs --watch backend --watch frontend

# 排除某些路径
ftrigger --logs --exclude-watch docs
```

**实现示例：**

```python
import argparse
from pathlib import Path

def filter_logs_by_watch(logs, watch_paths: list[str], exclude: bool = False):
    """根据监控路径过滤日志"""
    filtered = []
    for log in logs:
        log_path = log.get("watch_path", "")
        if not exclude:
            # 包含模式：只显示指定路径的日志
            if any(log_path.startswith(path) or path in log_path for path in watch_paths):
                filtered.append(log)
        else:
            # 排除模式：不显示指定路径的日志
            if not any(log_path.startswith(path) or path in log_path for path in watch_paths):
                filtered.append(log)
    return filtered

# 命令行参数
parser.add_argument(
    "--watch", "--path", "-w",
    action="append",
    dest="watches",
    help="过滤特定监控路径的日志（可多次使用）"
)
parser.add_argument(
    "--exclude-watch",
    action="append",
    dest="exclude_watches",
    help="排除特定监控路径的日志（可多次使用）"
)
```

#### 方案 B：为监控路径添加别名/标签

在配置文件中为每个监控规则添加别名：

```yaml
watches:
  - name: backend        # 新增：别名
    path: /home/user/projects/backend
    prompt: "Review backend code"
    extensions: [".py"]

  - name: frontend       # 新增：别名
    path: /home/user/projects/frontend
    prompt: "Review frontend code"
    extensions: [".js", ".ts"]

  - name: docs           # 新增：别名
    path: /home/user/projects/docs
    prompt: "Check documentation"
    extensions: [".md"]
```

**使用别名过滤：**

```bash
# 更简洁的语法
ftrigger --logs --watch backend
ftrigger --status --watch frontend
ftrigger --logs --watch backend --watch frontend

# 在交互模式中
ftrigger> logs --watch backend
ftrigger> status --watch frontend
```

**配置类更新：**

```python
@dataclass
class WatchConfig:
    """Single watch rule configuration"""

    name: str              # 新增：监控规则别名
    path: str
    prompt: str
    recursive: bool = True
    extensions: Optional[list[str]] = None
    permission_mode: str = "default"
    allowed_tools: Optional[list[str]] = None
    exclude_patterns: Optional[list[str]] = None

    def __post_init__(self):
        # 如果没有提供 name，使用路径的最后一部分作为默认 name
        if not self.name:
            self.name = Path(self.path).name
```

#### 方案 C：在日志输出中添加路径标识

改进日志格式，明确标识每个事件属于哪个监控路径：

```
# 当前格式
2026-04-16 20:13:29 - ftrigger.watcher - INFO - File created: /tmp/test.py

# 改进后
[backend] 2026-04-16 20:13:29 ✅ 文件已创建: /tmp/test.py
[frontend] 2026-04-16 20:13:30 ✅ 文件已创建: /tmp/app.js
[docs] 2026-04-16 20:13:31 ✅ 文件已创建: /tmp/readme.md
```

**实现示例：**

```python
import logging

class WatchPathFilter(logging.Filter):
    """为日志添加监控路径标识"""

    def __init__(self, watch_name: str):
        super().__init__()
        self.watch_name = watch_name

    def filter(self, record):
        # 为日志记录添加监控路径标识
        record.watch_name = self.watch_name
        return True

# 在配置中使用
formatter = logging.Formatter(
    fmt="[%(watch_name)s] %(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
```

#### 方案 D：按路径分组的状态面板

在 `--status` 输出中按监控路径分组显示统计信息：

```bash
$ ftrigger --status

📊 ftrigger 状态面板
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📁 backend (/home/user/projects/backend)
├─ 扩展名: .py
├─ 权限: bypassPermissions (工具: Read, Edit)
├─ 状态: ✅ 正在监控
└─ 今日活动:
   ├─ 文件创建: 12 次
   ├─ 文件修改: 28 次
   └─ Claude 触发: 40 次

📁 frontend (/home/user/projects/frontend)
├─ 扩展名: .js, .ts
├─ 权限: auto (工具: Read)
├─ 状态: ✅ 正在监控
└─ 今日活动:
   ├─ 文件创建: 8 次
   ├─ 文件修改: 15 次
   └─ Claude 触发: 23 次

📁 docs (/home/user/projects/docs)
├─ 扩展名: .md
├─ 权限: default
├─ 状态: ✅ 正在监控
└─ 今日活动:
   ├─ 文件创建: 3 次
   ├─ 文件修改: 5 次
   └─ Claude 触发: 8 次

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
总计: 23 创建, 48 修改, 71 触发
```

**实现示例：**

```python
def show_status_by_watch(config: Config, stats: StatsManager):
    """按监控路径显示状态"""

    print("📊 ftrigger 状态面板")
    print("━" * 40)

    for watch in config.watches:
        print(f"\n📁 {watch.name} ({watch.path})")
        print(f"├─ 扩展名: {', '.join(watch.extensions) or '全部'}")

        perm_info = f"{watch.permission_mode}"
        if watch.allowed_tools:
            perm_info += f" (工具: {', '.join(watch.allowed_tools)})"
        print(f"├─ 权限: {perm_info}")
        print(f"├─ 状态: ✅ 正在监控")

        # 获取该路径的统计信息
        counts = stats.get_counts_for_watch(watch.name)
        print(f"└─ 今日活动:")
        print(f"   ├─ 文件创建: {counts.get('created', 0)} 次")
        print(f"   ├─ 文件修改: {counts.get('modified', 0)} 次")
        print(f"   └─ Claude 触发: {counts.get('triggered', 0)} 次")

    print("\n" + "━" * 40)
    total = stats.get_total_counts()
    print(f"总计: {total['created']} 创建, {total['modified']} 修改, {total['triggered']} 触发")
```

#### 方案 E：交互模式中的路径选择

在交互模式中提供更便捷的路径选择：

```
ftrigger> logs
选择监控路径:
  1. backend (/home/user/projects/backend)
  2. frontend (/home/user/projects/frontend)
  3. docs (/home/user/projects/docs)
  4. 全部

请选择 (1-4): 1

显示 backend 的最近日志:
[backend] [20:13:29] ✅ 文件已创建: /tmp/test.py
[backend] [20:13:30] 🤖 已触发 Claude CLI
...
```

**实现示例：**

```python
import sys

class FTriggerInteractive(cmd.Cmd):
    """交互式命令行界面"""

    def do_logs(self, args):
        """显示日志"""
        watches = self.config.watches

        if len(watches) > 1:
            # 如果有多个监控路径，让用户选择
            print("选择监控路径:")
            for i, watch in enumerate(watches, 1):
                print(f"  {i}. {watch.name} ({watch.path})")
            print(f"  {len(watches) + 1}. 全部")

            choice = input(f"\n请选择 (1-{len(watches) + 1}): ").strip()

            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(watches):
                    # 显示特定路径的日志
                    self._show_logs_for_watch(watches[choice_num - 1])
                elif choice_num == len(watches) + 1:
                    # 显示全部日志
                    self._show_all_logs()
                else:
                    print("无效的选择")
            except ValueError:
                print("请输入数字")
        else:
            # 只有一个监控路径，直接显示
            self._show_all_logs()
```

### 统计信息的路径维度

为了支持按路径查看统计，需要扩展统计信息存储：

```python
@dataclass
class EventStats:
    """事件统计信息"""

    watch_name: str           # 新增：监控路径名称
    event_type: str           # 事件类型：created, modified, triggered
    timestamp: str
    file_path: str

class StatsManager:
    """统计信息管理器（扩展版）"""

    def record_event(self, watch_name: str, event_type: str, file_path: str):
        """记录事件（带监控路径）"""
        event = EventStats(
            watch_name=watch_name,
            event_type=event_type,
            timestamp=datetime.now().isoformat(),
            file_path=file_path
        )
        self.stats["events"].append(event)

    def get_counts_for_watch(self, watch_name: str) -> dict:
        """获取特定监控路径的统计"""
        today = datetime.now().date().isoformat()
        key = f"{today}:{watch_name}"

        return self.stats["counts"].get(key, {
            "created": 0,
            "modified": 0,
            "triggered": 0
        })

    def get_events_for_watch(self, watch_name: str, n=20) -> list[EventStats]:
        """获取特定监控路径的事件"""
        return [
            e for e in self.stats["events"][-n:]
            if e.watch_name == watch_name
        ]
```

### 使用示例对比

#### 当前方式

```bash
# 查看所有日志（混杂在一起）
journalctl --user -u ftrigger -f

# 手动过滤特定路径
journalctl --user -u ftrigger | grep "/tmp/ftrigger_test1"
```

#### 改进后

```bash
# 查看所有日志
ftrigger --logs

# 查看特定路径的日志
ftrigger --logs --watch backend
ftrigger --logs -w frontend

# 使用别名（更简洁）
ftrigger --logs --watch backend

# 查看多个路径
ftrigger --logs --watch backend --watch frontend

# 排除某些路径
ftrigger --logs --exclude-watch docs

# 查看特定路径的状态
ftrigger --status --watch backend

# 交互模式选择
ftrigger -i
ftrigger> logs
选择监控路径: backend
```

### 完整的命令行参数设计

```python
parser = argparse.ArgumentParser(
    description="File Trigger - Monitor file changes and trigger Claude CLI"
)

# 主要模式（互斥）
mode_group = parser.add_mutually_exclusive_group()
mode_group.add_argument(
    "--status", "-s",
    action="store_true",
    help="显示状态面板并退出"
)
mode_group.add_argument(
    "--logs", "-l",
    action="store_true",
    help="显示日志"
)
mode_group.add_argument(
    "--interactive", "-i",
    action="store_true",
    help="进入交互模式"
)

# 路径过滤选项
parser.add_argument(
    "--watch", "--path", "-w",
    action="append",
    dest="watches",
    metavar="NAME_OR_PATH",
    help="过滤特定监控路径的日志（可使用别名或路径，可多次使用）"
)
parser.add_argument(
    "--exclude-watch",
    action="append",
    dest="exclude_watches",
    metavar="NAME_OR_PATH",
    help="排除特定监控路径的日志（可多次使用）"
)

# 日志选项
parser.add_argument(
    "--follow", "-f",
    action="store_true",
    help="实时跟踪日志（配合 --logs 使用）"
)
parser.add_argument(
    "--last", "-n",
    type=int,
    default=20,
    metavar="N",
    help="显示最近 N 条日志（默认: 20）"
)
parser.add_argument(
    "--level",
    choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    help="过滤日志级别"
)
parser.add_argument(
    "--grep",
    metavar="PATTERN",
    help="搜索包含指定模式的日志"
)

# 配置选项
parser.add_argument(
    "-c", "--config",
    default="config.yaml",
    metavar="FILE",
    help="配置文件路径（默认: config.yaml）"
)
parser.add_argument(
    "-v", "--verbose",
    action="store_true",
    help="显示详细日志"
)
parser.add_argument(
    "-V", "--version",
    action="version",
    version=f"%(prog)s {__version__}"
)
```

### 配置文件完整示例

```yaml
# config.yaml
log_level: INFO

watches:
  # 使用 name 别名
  - name: backend
    path: /home/user/projects/backend
    prompt: "Review backend code for bugs and improvements"
    recursive: true
    extensions: [".py"]
    permission_mode: bypassPermissions
    allowed_tools: ["Read", "Edit", "LSP"]

  - name: frontend
    path: /home/user/projects/frontend
    prompt: "Review frontend code for accessibility"
    recursive: true
    extensions: [".js", ".ts", ".jsx", ".tsx"]
    permission_mode: auto
    allowed_tools: ["Read", "LSP"]

  - name: docs
    path: /home/user/projects/docs
    prompt: "Check documentation for clarity"
    recursive: true
    extensions: [".md", ".rst"]
    permission_mode: default

  # 如果不指定 name，将使用目录名作为默认别名
  - path: /home/user/projects/scripts
    prompt: "Review script changes"
    extensions: [".sh", ".bash"]
    # name 将自动设置为 "scripts"
```

### 功能优先级

| 功能 | 优先级 | 复杂度 | 价值 |
|------|--------|--------|------|
| **路径别名（name）** | 高 | 低 | ⭐⭐⭐⭐⭐ |
| **--watch 过滤器** | 高 | 中 | ⭐⭐⭐⭐⭐ |
| **路径标识日志** | 中 | 低 | ⭐⭐⭐⭐ |
| **按路径状态面板** | 中 | 中 | ⭐⭐⭐⭐ |
| **交互模式路径选择** | 低 | 低 | ⭐⭐⭐ |
| **统计信息路径维度** | 低 | 中 | ⭐⭐ |

### 实现路线图

```
v0.2.0 (用户体验改进)
├── 添加 --status 参数
├── 添加 --logs 参数
└── 改进日志格式
    ↓
v0.2.1 (路径过滤)
├── 配置文件添加 name 字段
├── --logs 支持 --watch 过滤器
├── 日志输出添加路径标识
└── --status 支持路径过滤
    ↓
v0.3.0 (交互模式)
├── 添加 --interactive 参数
└── 交互模式支持路径选择
    ↓
v0.3.1 (高级统计)
├── 统计信息按路径维度存储
└── 按路径分组的状态面板
```

### 向后兼容

所有新功能都向后兼容：

```yaml
# 旧配置文件仍然有效（没有 name 字段）
watches:
  - path: /tmp/test
    prompt: "Test"
    extensions: [".py"]
# name 将自动设置为 "test"
```

```bash
# 旧命令仍然有效
ftrigger --logs

# 新功能是可选的
ftrigger --logs --watch backend
```

### 相关文件

- `ftrigger/config.py` - 添加 WatchConfig.name 字段
- `ftrigger/stats.py` - 扩展统计信息支持路径维度
- `ftrigger/main.py` - 添加 --watch 和 --exclude-watch 参数
- `ftrigger/watcher.py` - 日志输出添加路径标识
- `ftrigger/interactive.py` - 交互模式路径选择
- `README.md` - 更新使用文档

### 决策日期

2026-04-16
