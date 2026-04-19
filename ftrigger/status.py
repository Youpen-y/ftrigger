"""Status display module for ftrigger

Provides user-friendly status panel showing configuration and monitoring state.
"""

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

    # Display hints
    print("\n" + "=" * 40)
    print("Hints:")
    print("  Run monitoring mode: ftrigger")
    print("  View logs: journalctl --user -u ftrigger -f")
    print("  Stop service: systemctl --user stop ftrigger")
