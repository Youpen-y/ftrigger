"""Status display module for ftrigger

Provides user-friendly status panel showing running instances, configuration,
and monitoring information.
"""

import sys
from typing import Optional

from ftrigger.activity import ActivityTracker, get_tracker
from ftrigger.config import Config, load_config
from ftrigger.process import (
    InstanceInfo,
    format_duration,
    get_all_instances,
    get_instance_by_name,
    get_instance_by_pid,
    shorten_path,
)


def show_status_overview() -> None:
    """Display status overview with all running instances

    Shows systemd services and standalone processes in a grouped format.
    """
    instances = get_all_instances()

    print("📊 ftrigger Status Panel")
    print("=" * 40)
    print(f"\nRunning Instances: {len(instances)}\n")

    if not instances:
        print("No ftrigger instances are currently running.")
        print("\nTo start monitoring:")
        print("  ftrigger                    # Start with config.yaml in current directory")
        print("  ftrigger -c <config.yaml>   # Start with specific config")
        print("  systemctl --user start ftrigger  # Start as a service")
        return

    # 分组显示
    services = [i for i in instances if i.type == "service"]
    standalones = [i for i in instances if i.type == "standalone"]

    if services:
        print("┌─ Systemd Services " + "─" * 23 + "┐")
        for inst in services:
            icon = "✅" if inst.status == "running" else "❌"
            since = format_duration(inst.start_time) if inst.start_time else "unknown"
            config = shorten_path(inst.config_path)
            print(f"│ {icon} {inst.name}")
            print(f"│    PID:     {inst.pid}")
            print(f"│    Config:  {config}")
            print(f"│    Since:   {since}")
            print(f"│    Status:  {inst.status}")
            if inst.watches_count > 0:
                print(f"│    Watches: {inst.watches_count} path{'s' if inst.watches_count > 1 else ''}")
            print("│")
        print("└" + "─" * 40 + "┘")

    if standalones:
        if services:
            print()  # 分组间隔

        print("┌─ Standalone Processes " + "─" * 19 + "┐")
        for inst in standalones:
            since = format_duration(inst.start_time) if inst.start_time else "unknown"
            config = shorten_path(inst.config_path)
            print(f"│ PID {inst.pid}")
            print(f"│    Config:  {config}")
            print(f"│    Running: {since}")
            if inst.watches_count > 0:
                print(f"│    Watches: {inst.watches_count} path{'s' if inst.watches_count > 1 else ''}")
        print("└" + "─" * 40 + "┘")

    print("\nUse --status --pid <pid|name> for instance details")


def show_status_detail(instance: InstanceInfo) -> None:
    """Display detailed status for a specific instance

    Args:
        instance: Instance information
    """
    print("📊 ftrigger Instance Details")
    print("=" * 40)

    # 基本信息
    status_icon = "●" if instance.status == "running" else "○"
    print(f"\nInstance: {instance.name} ({instance.type})")
    print(f"PID:      {instance.pid}")
    print(f"Status:   {status_icon} {instance.status.capitalize()}")

    if instance.start_time:
        since_str = instance.start_time.strftime("%Y-%m-%d %H:%M:%S")
        duration = format_duration(instance.start_time)
        print(f"Since:    {since_str} ({duration} ago)")

    print(f"Config:   {instance.config_path}")

    # 尝试加载配置
    try:
        config = load_config(instance.config_path)
        instance.watches_count = len(config.watches)

        print(f"\nWatch paths ({len(config.watches)} total):")
        for i, watch in enumerate(config.watches, 1):
            is_directory = getattr(watch, "_is_directory", True)
            icon = "📁" if is_directory else "📄"
            print(f"  {i}. {icon} {watch.path}")

            # Display prompt (truncated if too long)
            prompt = watch.prompt
            if len(prompt) > 60:
                prompt = prompt[:57] + "..."
            print(f"     Prompt:  {prompt}")

            # Display events
            if watch.events:
                events_str = ", ".join(watch.events)
                print(f"     Events:  {events_str}")

            # Display extensions filter
            if watch.extensions:
                ext_str = ", ".join(watch.extensions)
                print(f"     Extensions: {ext_str}")

            # Display permission mode
            print(f"     Permission:  {watch.permission_mode}")

            # Display allowed tools if specified
            if watch.allowed_tools:
                tools_str = ", ".join(watch.allowed_tools)
                print(f"     Tools:  {tools_str}")

            # Add separator between watches except for the last one
            if i < len(config.watches):
                print()

    except FileNotFoundError:
        print(f"\n⚠️  Configuration file not found: {instance.config_path}")
    except ValueError as e:
        print(f"\n⚠️  Configuration error: {e}")

    # 获取该实例的统计信息
    tracker = ActivityTracker(instance_id=f"pid{instance.pid}")
    instance_info = tracker.get_instance_info()

    print(f"\nToday's Activity:")
    stats = tracker.get_today_stats()
    print(f"  Triggers:  {stats['triggers']}")
    print(f"  Files:     {stats['files']}")

    # Show event breakdown if there were any triggers
    if stats['triggers'] > 0:
        events = []
        if stats['created']:
            events.append(f"created: {stats['created']}")
        if stats['modified']:
            events.append(f"modified: {stats['modified']}")
        if stats['deleted']:
            events.append(f"deleted: {stats['deleted']}")
        if stats['moved']:
            events.append(f"moved: {stats['moved']}")

        if events:
            print(f"  Events:  {', '.join(events)}")

    # 显示最近活动
    try:
        recent = tracker.get_recent_activities(limit=5)

        if recent:
            print(f"\nRecent Activity:")
            for activity in recent:
                print(f"  {activity['time']}  {activity['file_path']}  {activity['event_type']}")
        else:
            print(f"\nRecent Activity:")
            print(f"  No activity recorded yet")

    except Exception as e:
        print(f"\nRecent Activity: unavailable ({e})")


def show_status_with_args(pid_arg: Optional[str] = None) -> None:
    """Display status based on arguments

    Args:
        pid_arg: PID or service name for detailed view, or None for overview
    """
    if pid_arg:
        # 详细状态模式
        instance = None

        # 尝试作为 PID 解析
        try:
            pid = int(pid_arg)
            instance = get_instance_by_pid(pid)
        except ValueError:
            # 尝试作为服务名解析
            instance = get_instance_by_name(pid_arg)

        if instance:
            show_status_detail(instance)
        else:
            print(f"Instance not found: {pid_arg}", file=sys.stderr)
            print("\nRunning instances:", file=sys.stderr)
            instances = get_all_instances()
            if instances:
                for inst in instances:
                    print(f"  {inst.name} (PID: {inst.pid})", file=sys.stderr)
            else:
                print("  None", file=sys.stderr)
            sys.exit(1)
    else:
        # 总览模式
        show_status_overview()


def show_status(config: Config) -> None:
    """Display status panel with configuration and monitoring information

    Legacy function for backward compatibility.

    Args:
        config: Configuration object containing watch rules and settings
    """
    # For backward compatibility, show overview
    # This function is kept for existing code that may call it directly
    show_status_overview()
