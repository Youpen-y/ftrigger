# systemd Service Setup Guide

This guide shows how to run ftrigger as a systemd user service.

## Prerequisites

1. Install ftrigger globally:
   ```bash
   pip install --user ftrigger
   # or using pipx (recommended)
   pipx install ftrigger
   ```

2. Create configuration:
   ```bash
   mkdir -p ~/.config/ftrigger
   cp config.yaml ~/.config/ftrigger/config.yaml
   ```

## Option 1: Single Instance (Recommended)

**Use this when you only need one ftrigger process.** A single config can contain multiple watches.

```yaml
# ~/.config/ftrigger/config.yaml
watches:
  - path: ~/project/src
    prompt: "Review code"
  - path: ~/project/docs
    prompt: "Check docs"
  - path: ~/project/tests
    prompt: "Run tests"
```

### Installation

```bash
# Copy service file
mkdir -p ~/.config/systemd/user/
cp ftrigger.service ~/.config/systemd/user/

# Edit the service file to match your setup
nano ~/.config/systemd/user/ftrigger.service
```

Edit these lines in `ftrigger.service`:
```ini
[Service]
User=YOUR_USERNAME           # Replace with your username
WorkingDirectory=/path/to/your/project
ExecStart=/path/to/ftrigger --config /path/to/config.yaml
```

### Enable and start

```bash
systemctl --user daemon-reload
systemctl --user enable ftrigger
systemctl --user start ftrigger
```

### Management

```bash
# Check status
systemctl --user status ftrigger

# View logs
journalctl --user -u ftrigger -f

# Restart
systemctl --user restart ftrigger

# Stop
systemctl --user stop ftrigger

# Disable (don't start on login)
systemctl --user disable ftrigger
```

## Option 2: Multiple Instances (Advanced)

**Use this when you need completely isolated ftrigger processes.**

Examples where this is useful:
- Different log levels (dev vs prod)
- Different resource limits
- Independent restart/management
- Different Claude accounts (future)

### Installation

```bash
# Copy template service
cp ftrigger@.service ~/.config/systemd/user/

# Create config for each instance
cp config.yaml ~/.config/ftrigger/dev.yaml
cp config.yaml ~/.config/ftrigger/prod.yaml

# Enable each instance
systemctl --user daemon-reload
systemctl --user enable ftrigger@dev
systemctl --user enable ftrigger@prod
systemctl --user start ftrigger@dev
systemctl --user start ftrigger@prod
```

### Management

```bash
# Status of specific instance
systemctl --user status ftrigger@dev

# Restart specific instance
systemctl --user restart ftrigger@dev

# View logs of specific instance
journalctl --user -u ftrigger@dev -f
```

## Logs

View logs with journalctl:

```bash
# Follow logs in real-time
journalctl --user -u ftrigger -f

# Last 100 lines
journalctl --user -u ftrigger -n 100

# Since last boot
journalctl --user -u ftrigger -b

# Filter by log level
journalctl --user -u ftrigger -f -p err
journalctl --user -u ftrigger -f -p debug
```

## Troubleshooting

### Service fails to start

1. Check the status:
   ```bash
   systemctl --user status ftrigger
   ```

2. View the logs:
   ```bash
   journalctl --user -u ftrigger -n 50 --no-pager
   ```

3. Verify paths in the service file are correct

### Service starts but stops immediately

1. Test config manually:
   ```bash
   ftrigger --config ~/.config/ftrigger/config.yaml --verbose
   ```

2. Verify watch paths exist

### Logs not appearing

1. Check journal is running:
   ```bash
   systemctl status systemd-journald
   ```

2. Check log level in config.yaml

## Advanced Configuration

### Resource Limits

Add to the `[Service]` section:

```ini
[Service]
# ... existing config ...

# Memory limit
MemoryLimit=512M

# CPU limit
CPUQuota=50%

# File descriptor limit
LimitNOFILE=65536
```

### Environment Variables

```ini
[Service]
# ... existing config ...

Environment="CLAUDE_API_KEY=your_key_here"
Environment="PYTHONUNBUFFERED=1"
EnvironmentFile=-%h/.config/ftrigger/environment
```

### Watchdog

```ini
[Service]
# ... existing config ...

# Watchdog timeout (restart if unresponsive)
WatchdogSec=60
```

## Cross-Platform

### Linux

User services work out of the box on systemd-based distributions.

### macOS

Use launchd instead:
```bash
# Create ~/Library/LaunchAgents/ftrigger.plist
# See: ftrigger.launchd.example.md (not included yet)
```

### Windows

Use Task Scheduler or run as a background service with NSSM (Not provided yet).

## Notes

- User services start automatically when you log in
- Services run with your user permissions (no root needed)
- Configuration files use YAML format with hierarchical support
- Single instance with multiple watches is recommended for most users
