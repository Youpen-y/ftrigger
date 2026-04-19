"""Status display module for ftrigger

Provides user-friendly status panel showing configuration and monitoring state.
"""

from ftrigger.activity import get_tracker
from ftrigger.config import Config


def show_status(config: Config) -> None:
    """Display status panel with configuration and monitoring information

    Args:
        config: Configuration object containing watch rules and settings
    """
    # Display header
    print("📊 ftrigger Status Panel")
    print("=" * 40)

    # Basic information
    source_file = getattr(config, "_source_file", "unknown")
    log_level = config.log_level

    print(f"Mode:          Status Query")
    print(f"Config file:   {source_file}")
    print(f"Log level:     {log_level}")

    # Display watch paths
    print(f"\nWatch paths ({len(config.watches)} total):")
    for i, watch in enumerate(config.watches, 1):
        # Determine icon based on whether it's a file or directory
        is_directory = getattr(watch, "_is_directory", True)
        icon = "📁" if is_directory else "📄"

        print(f"  {i}. {icon} {watch.path}")

        # Display prompt (truncated if too long)
        prompt = watch.prompt
        if len(prompt) > 60:
            prompt = prompt[:57] + "..."
        print(f"     Prompt:      {prompt}")

        # Display extensions filter
        if watch.extensions:
            ext_str = ", ".join(watch.extensions)
            print(f"     Extensions: {ext_str}")
        else:
            print(f"     Extensions: all")

        # Display permission mode
        print(f"     Permission:  {watch.permission_mode}")

        # Display allowed tools if specified
        if watch.allowed_tools:
            tools_str = ", ".join(watch.allowed_tools)
            print(f"     Tools:       {tools_str}")

        # Display event types if specified
        if watch.events:
            events_str = ", ".join(watch.events)
            print(f"     Events:      {events_str}")

        # Display exclude patterns if specified
        if watch.exclude_patterns:
            exclude_str = ", ".join(watch.exclude_patterns)
            print(f"     Excludes:    {exclude_str}")

        # Add separator between watches except for the last one
        if i < len(config.watches):
            print()

    # Display today's statistics
    try:
        tracker = get_tracker()
        stats = tracker.get_today_stats()

        print(f"\nToday's Statistics:")
        print(f"  Triggers:     {stats['triggers']}")
        print(f"  Files:        {stats['files']}")

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
                print(f"  Events:       {', '.join(events)}")

    except Exception as e:
        print(f"\nToday's Statistics: unavailable ({e})")

    # Display recent activities
    try:
        tracker = get_tracker()
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

    # Display hints
    print("\n" + "=" * 40)
    print("Hints:")
    print("  Run monitoring mode: ftrigger")
    print("  View logs: journalctl --user -u ftrigger -f")
    print("  Stop service: systemctl --user stop ftrigger")
