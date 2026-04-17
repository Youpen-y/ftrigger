# File Trigger

<div align="center">

English | [**中文**](README.zh-CN.md)

![Version](https://img.shields.io/badge/version-0.1.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.9+-blue)
![Status](https://img.shields.io/badge/status-alpha-orange)

File monitoring tool for Claude CLI - Automatically executes Claude CLI commands with **Customized Prompt Template** when files in specified directories change.

</div>

## Features

- 🔍 Monitor file changes in specified directories (creation, modification)
- 🤖 Automatically trigger Claude CLI with configured prompts
- ⚙️ Support multiple watch paths with independent configurations
- 🎯 File extension filtering support
- 📝 Prompt variable substitution (e.g., `{file}`)
- 🚫 Exclude patterns support (e.g., `.git`, `node_modules`)
- 🔄 Cross-platform support (Linux, macOS, Windows)
- 🛡️ Permission control and tool whitelisting for security
- 📚 **Hierarchical configuration** - System, user, and project level configs

## Use Cases

### 📖 Real-time LLM Wiki Building

Unlike traditional scheduled cron jobs, **ftrigger provides real-time, event-driven automation**. When new source files are added to your wiki:

- **Instant Processing**: Files are processed immediately upon creation, not waiting for the next scheduled interval
- **Dynamic Content**: Your LLM Wiki updates automatically as you add new content
- **Resource Efficient**: Only runs when actual changes occur, saving computational resources

**Example configuration for LLM Wiki:**

```yaml
watches:
  - path: /path/to/llm-wiki/raw/sources
    prompt: "LLM Wiki sources directory has a new file {file}. Based on the new content and CLAUDE.md, please process and update the wiki accordingly."
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

**Benefits over scheduled tasks:**
| Aspect | Scheduled (Cron) | Event-Driven (ftrigger) |
|--------|------------------|-------------------------|
| Response Time | Fixed intervals (e.g., every hour) | Immediate (seconds) |
| Resource Usage | Runs regardless of changes | Only runs when needed |
| Scalability | Wastes resources on idle times | Scales with activity |
| User Experience | Delayed updates | Real-time feedback |

## Installation

### Install Globally (Recommended)

```bash
# Clone repository
git clone https://github.com/Youpen-y/ftrigger
cd ftrigger

# Install globally
pip install .

# Or install in editable mode (for development)
pip install -e .
```

After installation, you can run `ftrigger` directly from anywhere:

```bash
ftrigger
ftrigger --config /path/to/config.yaml
ftrigger -v
```

### Install from Source (Development)

```bash
# Clone repository
git clone https://github.com/Youpen-y/ftrigger
cd ftrigger

# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or .venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run with python -m
python -m ftrigger
```

### System Requirements

- Python 3.9+
- Claude CLI (must be installed and configured)

## Quick Start

### 1. Create Configuration File

Create `config.yaml` in your project directory:

```yaml
log_level: INFO

watches:
  - path: /path/to/your/project
    prompt: "Review the changed file {file} and suggest improvements."
    recursive: true
    extensions: [".py", ".js", ".ts"]
```

### 2. Start Monitoring

```bash
# Auto-discover and merge configs (project -> user -> system)
ftrigger

# Or specify config file explicitly
ftrigger --config /path/to/config.yaml

# Show verbose logs
ftrigger -v
```

### Configuration Hierarchy

ftrigger supports hierarchical configuration with automatic merging:

| Level | Path | Priority |
|-------|------|----------|
| **System** | `/etc/ftrigger/config.yaml` | Low |
| **User** | `~/.config/ftrigger/config.yaml` | Medium |
| **Project** | `./config.yaml` or `--config` | High |

Higher priority configs override lower priority ones, while `watches` from all levels are merged.

## Run as a Service

For long-running monitoring, install ftrigger as a systemd user service.

### Quick Install (Linux)

Use the automated installation script:

```bash
# Install single instance service (recommended)
./install-service.sh

# Install with custom config
./install-service.sh --config /path/to/config.yaml

# Uninstall service
./install-service.sh --uninstall
```

### Manual Installation

```bash
# Copy service file
mkdir -p ~/.config/systemd/user/
cp ftrigger.service ~/.config/systemd/user/

# Edit paths in the service file
nano ~/.config/systemd/user/ftrigger.service

# Install and start
systemctl --user daemon-reload
systemctl --user enable ftrigger
systemctl --user start ftrigger
```

### Service Management

```bash
# Check status
systemctl --user status ftrigger

# View logs
journalctl --user -u ftrigger -f

# Restart
systemctl --user restart ftrigger

# Stop
systemctl --user stop ftrigger
```

### Multiple Instances (Advanced)

For isolated monitoring environments:

```bash
# Install template service
./install-service.sh --multi-instance

# Create configs
cp config.yaml ~/.config/ftrigger/dev.yaml
cp config.yaml ~/.config/ftrigger/prod.yaml

# Start instances
systemctl --user start ftrigger@dev
systemctl --user start ftrigger@prod
```

See `ftrigger.systemd.tutorial.md` for detailed documentation.

## Configuration

### Configuration File Structure

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `log_level` | string | No | Log level: DEBUG, INFO, WARNING, ERROR (default: INFO) |
| `watches` | list | Yes | List of watch rules |

### Watch Rule Configuration

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `path` | string | Yes | Directory path to monitor (must exist and be a directory) |
| `prompt` | string | Yes | Prompt to execute when triggered |
| `recursive` | boolean | No | Whether to monitor subdirectories recursively (default: true) |
| `extensions` | list | No | Only monitor files with specified extensions (optional) |
| `permission_mode` | string | No | Claude CLI permission mode (default: default) |
| `allowed_tools` | list | No | Allowed tools whitelist (optional) |
| `exclude_patterns` | list | No | Exclude path patterns (optional) |

### Permission Modes (permission_mode)

Control Claude CLI permission behavior:

| Mode | CLI Argument | Description |
|------|--------------|-------------|
| `default` | (none) | Default mode |
| `auto` | `--permission-mode auto` | Auto mode |
| `acceptEdits` | `--permission-mode acceptEdits` | Automatically accept edit operations |
| `dontAsk` | `--permission-mode dontAsk` | Don't ask, automatically grant permissions |
| `bypassPermissions` | `--dangerously-skip-permissions` | Skip all permission checks (use with caution) |

### Tools Whitelist (allowed_tools)

Restrict tools that Claude can use for enhanced security. Common tools:

- `Read` - Read files
- `Write` - Write files
- `Edit` - Edit files
- `Bash` - Execute shell commands
- `Glob` - File pattern matching
- `Grep` - Content search
- `LSP` - Use Language Server Protocol
- `AskUserQuestion` - Ask user questions

Supports wildcard restrictions, e.g., `Bash(git:*)` only allows git-related commands.

Example:

```yaml
allowed_tools:
  - "Read"
  - "Bash(git:*)"
  - "LSP"
```

### Exclude Patterns (exclude_patterns)

Specify path patterns to exclude, supports wildcards:

```yaml
exclude_patterns:
  - ".git"
  - "node_modules"
  - "*.log"
  - "__pycache__"
```

### Prompt Variables

The following variables are supported in prompts:

- `{file}` - Full path of the changed file
- `{path}` - Same as `{file}`

Example:

```yaml
prompt: "Review the Python file {file} for bugs and improvements"
```

## Usage Examples

### Monitor Python Project

```yaml
watches:
  - path: ./src
    prompt: "Analyze {file} for code quality issues and suggest refactoring opportunities."
    recursive: true
    extensions: [".py"]
```

### Monitor Documentation Changes

```yaml
watches:
  - path: ./docs
    prompt: "Check the documentation for clarity, consistency, and completeness."
    recursive: true
    extensions: [".md", ".rst"]
```

### Multi-Path Monitoring

```yaml
watches:
  - path: ./backend
    prompt: "Review backend code changes for security issues."
    extensions: [".py"]

  - path: ./frontend
    prompt: "Review frontend code changes for accessibility and performance."
    extensions: [".js", ".ts", ".jsx", ".tsx"]
```

### Using Permissions and Tool Restrictions

```yaml
watches:
  # Read-only code review - only allow read tools
  - path: ./src
    prompt: "Review {file} for code quality issues."
    extensions: [".py"]
    permission_mode: bypassPermissions
    allowed_tools:
      - "Read"
      - "LSP"

  # Git auto-commit - allow git commands and file editing
  - path: ./repo
    prompt: "Create a git commit and push when files change"
    extensions: [".py", ".js"]
    permission_mode: bypassPermissions
    allowed_tools:
      - "Bash(git:*)"
      - "Read"
      - "Edit"
      - "Write"
```

## How It Works

1. Uses the `watchdog` library to monitor file system events
2. Filters events based on configuration when file creation or modification is detected
3. Builds and executes `claude -p <prompt>` command
4. Executes asynchronously in a separate thread without blocking monitoring

## Debouncing

To avoid multiple triggers in a short time, the same file will only trigger once within 5 seconds.

## FAQ

### Q: How to stop monitoring?

Press `Ctrl+C` or send `SIGTERM` signal for graceful shutdown.

### Q: Not detecting file changes?

Check:
1. If the path in the config file is correct and exists
2. If file extensions match
3. If log level is set to DEBUG for detailed information

### Q: Claude CLI not found?

Ensure Claude CLI is installed and in system PATH:

```bash
which claude  # Linux/macOS
where claude  # Windows
```

## Project Structure

```
ftrigger/
├── ftrigger/
│   ├── __init__.py      # Package initialization
│   ├── __main__.py      # Supports python -m ftrigger
│   ├── main.py          # Main entry point
│   ├── config.py        # Configuration management
│   ├── watcher.py       # File monitoring
│   └── executor.py      # CLI executor
├── config.yaml          # Configuration file
├── requirements.txt     # Python dependencies
└── README.md            # This document
```

## Development

```bash
# Run (development mode)
python -m ftrigger

# Use custom configuration
python -m ftrigger --config my-config.yaml
```

## License

MIT License

## Contributing

Issues and Pull Requests are welcome!
