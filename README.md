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

- 🔍 Monitor path changes (creation, modification, deletion, move)
    - 📁 **Directory monitoring** - Watch entire directories recursively
    - 📄 **Single file monitoring** - Watch individual files for changes
- 🎯 **Event filtering** - Select which event types to monitor
- ⏱️ **Smart debouncing** - Coalesce rapid changes into single trigger (1s delay)
- 🤖 Automatically trigger Claude CLI with configured prompts
- ⚙️ Support multiple watch paths with independent configurations
- 📝 Prompt variable substitution (e.g., `{file}`, `{events}`)
- 🎯 File extension filtering support (directories only)
- 🚫 Exclude patterns support (e.g., `.git`, `node_modules`)
- 🔄 Cross-platform support (Linux, macOS, Windows)
- 🛡️ Permission control and tool whitelisting for security
- 📊 **Status display** - View configuration and statistics with `--status`
- 📈 **Activity tracking** - Track trigger history and daily statistics

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
    events: ["created"]
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
    events: ["modified"]
    prompt: "Review the changed file {file} and do something thing you want."
    recursive: true
    extensions: [".py", ".js", ".ts"]
```

### 2. Start Monitoring

```bash
# Start monitoring (uses config.yaml in current directory)
ftrigger

# Specify config file explicitly
ftrigger -c /path/to/config.yaml

# Show status panel
ftrigger --status

# Show verbose logs
ftrigger -v
```

### Configuration Mode

ftrigger supports two distinct modes with different configuration behavior:

**Command-Line Mode:**
- Uses `config.yaml` in current directory by default
- Can specify any config file with `-c` option
- Ignores standard service config locations unless explicitly specified via `-c`
- Designed for temporary monitoring and testing

**Service Mode:**
- Uses fixed configuration paths based on service type
- **User service**: `~/.config/ftrigger/config.yaml`
- **System service**: `/etc/ftrigger/config.yaml`
- Designed for long-running background monitoring

This separation prevents conflicts between service and command-line instances.

## Run as a Service

For long-running monitoring, install ftrigger as a systemd service.

### Quick Install (Linux)

Use the automated installation script with interactive mode selection:

```bash
# Install with interactive prompt (recommended for first-time)
./install-service.sh

# Install as user service directly
./install-service.sh --mode user

# Install as system service directly
./install-service.sh --mode system

# Uninstall service
./install-service.sh --uninstall
```

The installer will prompt you to select:
- **[0] User service** - Install for current user (`~/.config/ftrigger/config.yaml`)
- **[1] System service** - Install system-wide (`/etc/ftrigger/config.yaml`)

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

See [`ftrigger.systemd.tutorial.md`](./ftrigger.systemd.tutorial.md) for detailed documentation.

## Configuration

### Configuration File Structure

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `log_level` | string | No | Log level: DEBUG, INFO, WARNING, ERROR (default: INFO) |
| `watches` | list | Yes | List of watch rules |

### Watch Rule Configuration

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `path` | string | Yes | File or directory path to monitor (must exist) |
| `prompt` | string | Yes | Prompt to execute when triggered |
| `events` | list | No | Event types to monitor: ["created", "modified", "deleted", "moved"] |
| `recursive` | boolean | No | Whether to monitor subdirectories recursively (default: true, directories only) |
| `extensions` | list | No | Only monitor files with specified extensions (directories only) |
| `permission_mode` | string | No | Claude CLI permission mode (default: default) |
| `allowed_tools` | list | No | Allowed tools whitelist (optional) |
| `exclude_patterns` | list | No | Exclude path patterns (directories only) |

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
- `{events}` - Event type that triggered the action: `created`, `modified`, `deleted`, `moved`

**Event-specific variables for `moved` events:**
- `{src_path}` / `{src}` - Source path (where file was moved from)
- `{dest_path}` / `{dest}` - Destination path (where file was moved to)

Example:

```yaml
prompt: "Review the Python file {file} for bugs and improvements"
# Or with event type
prompt: "File {events}: Review {file} for bugs and improvements"
```

## Usage Examples

### Monitor a Single File

Monitor specific configuration files or important documents:

```yaml
watches:
  - path: /etc/nginx/nginx.conf
    prompt: "Nginx config changed at {file}. Please validate the syntax and check for potential issues."
    events: ["modified"]
    permission_mode: acceptEdits

  - path: /home/user/important-document.md
    prompt: "Document {file} was modified. Please review and summarize the changes."
    events: ["modified"]
    permission_mode: acceptEdits
```

**Note:** When monitoring a single file, the `recursive` and `extensions` options are automatically ignored.

### Monitor Python Project

```yaml
watches:
  - path: ./src
    prompt: "Analyze {file} for code quality issues and suggest refactoring opportunities."
    recursive: true
    permission_mode: acceptEdits
    extensions: [".py"]
```

### Monitor Documentation Changes

```yaml
watches:
  - path: ./docs
    prompt: "Check the documentation for clarity, consistency, and completeness."
    recursive: true
    permission_mode: acceptEdits
    extensions: [".md", ".rst"]
```

### Multi-Path Monitoring

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

### Event Filtering

Monitor specific event types only:

```yaml
watches:
  # Only monitor new file creation
  - path: ./uploads
    prompt: "New file created: {file}. Please process and analyze."
    events: ["created"]
    recursive: true
    permission_mode: acceptEdits

  # Monitor creation and modification, ignore deletion
  - path: ./src
    prompt: "File {events}: Review {file} for code quality."
    events: ["created", "modified"]
    extensions: [".py"]
    permission_mode: bypassPermissions
    allowed_tools:
      - "Read"
      - "LSP"
```

**Supported event types:**
- `created` - File/directory created
- `modified` - File/directory modified
- `deleted` - File/directory deleted
- `moved` - File/directory moved/renamed

**Note:** If `events` field is not specified, all event types are monitored by default.

## Commands

| Command | Description |
|---------|-------------|
| `ftrigger` | Start monitoring with `config.yaml` in current directory |
| `ftrigger -c/--config <path>` | Start monitoring with specified config file |
| `ftrigger --status` | Display configuration and statistics panel |
| `ftrigger -v` | Show verbose logs (DEBUG level) |
| `ftrigger -h, --help` | Show help message |

## How It Works

1. Uses the `watchdog` library to monitor file system events
2. Filters events based on configured event types (created, modified, deleted, moved)
3. Applies debouncing to coalesce rapid changes (1-second delay)
4. Builds and executes `claude` CLI command with prompt variables
5. Records activity statistics for tracking
6. Executes asynchronously in a separate thread without blocking monitoring

## Debouncing

To avoid multiple triggers during rapid file changes (e.g., saving a file multiple times quickly), ftrigger uses a smart debouncing strategy:

- **1-second delay**: When an event occurs, wait 1 second before triggering
- **Coalescing**: If another event occurs within the delay window, reset the timer
- **Per-event-type tracking**: Each file:event_type combination has its own timer

This ensures only the final state triggers Claude, reducing unnecessary API calls and improving efficiency.

## FAQ

### Q: How to stop monitoring?

- **If running as a service**: Use `systemctl --user stop ftrigger` or the corresponding service management command
- **If running directly**: Press `Ctrl+C` or send `SIGTERM` signal for graceful shutdown

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
│   ├── executor.py      # CLI executor
│   ├── status.py        # Status display
│   └── activity.py      # Activity tracking
├── config.yaml          # Configuration file
├── requirements.txt     # Python dependencies
├── install-service.sh   # Service installation script
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
