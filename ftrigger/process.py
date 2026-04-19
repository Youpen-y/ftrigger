"""Process detection and status management module for ftrigger

Detects running ftrigger instances including systemd services and standalone processes.
"""

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from logging import getLogger

logger = getLogger(__name__)


@dataclass
class InstanceInfo:
    """ftrigger instance information"""

    pid: int
    type: str  # "service" | "standalone"
    name: str  # 服务名或进程标识
    config_path: str
    start_time: Optional[datetime]
    status: str  # "running" | "stopped" | "unknown"
    watches_count: int = 0


def parse_systemd_timestamp(timestamp_str: str) -> Optional[datetime]:
    """解析 systemd 时间戳格式

    Args:
        timestamp_str: systemd 时间戳字符串

    Returns:
        datetime 对象或 None
    """
    if not timestamp_str or timestamp_str == "n/a":
        return None

    try:
        # systemd 时间戳格式: "Mon 2025-01-19 12:15:30 UTC"
        # 或 "2025-01-19 12:15:30"
        return datetime.fromisoformat(timestamp_str.replace(" UTC", "").replace(" ", "T"))
    except (ValueError, AttributeError):
        logger.debug(f"Failed to parse timestamp: {timestamp_str}")
        return None


def get_systemd_services() -> list[InstanceInfo]:
    """获取 systemd 服务状态

    Returns:
        实例信息列表
    """
    instances = []

    # 用户服务
    try:
        result = subprocess.run(
            ["systemctl", "--user", "show", "ftrigger.service"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        instance = parse_systemd_service(result.stdout, "ftrigger.service")
        if instance:
            instances.append(instance)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        logger.debug(f"Failed to query user service: {e}")

    # 多实例服务
    try:
        result = subprocess.run(
            ["systemctl", "--user", "list-units", "--type=service", "--all", "--plain"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        for line in result.stdout.split("\n"):
            if "ftrigger@" in line:
                # 解析服务名
                parts = line.split()
                if parts:
                    service_name = parts[0].replace(".service", "")
                    try:
                        detail = subprocess.run(
                            ["systemctl", "--user", "show", service_name + ".service"],
                            capture_output=True,
                            text=True,
                            timeout=5,
                        )
                        instance = parse_systemd_service(detail.stdout, service_name + ".service")
                        if instance:
                            instances.append(instance)
                    except (FileNotFoundError, subprocess.TimeoutExpired):
                        continue

    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        logger.debug(f"Failed to list template services: {e}")

    return instances


def parse_systemd_service(output: str, service_name: str) -> Optional[InstanceInfo]:
    """解析 systemctl show 输出

    Args:
        output: systemctl show 命令输出
        service_name: 服务名称

    Returns:
        InstanceInfo 或 None
    """
    properties = {}
    for line in output.split("\n"):
        if "=" in line:
            key, value = line.split("=", 1)
            properties[key] = value

    # 检查服务是否加载
    load_state = properties.get("LoadState", "")
    if load_state == "not-found" or load_state == "masked":
        return None

    # 获取 PID
    main_pid = properties.get("MainPID", "0")
    try:
        pid = int(main_pid)
    except ValueError:
        pid = 0

    # 检查是否在运行
    active_state = properties.get("ActiveState", "unknown")
    if active_state == "active" and pid > 0:
        status = "running"
    elif active_state == "inactive":
        status = "stopped"
    else:
        status = "unknown"

    # 获取启动时间
    start_time = parse_systemd_timestamp(properties.get("ExecMainStartTimestamp", ""))
    if not start_time:
        start_time = parse_systemd_timestamp(properties.get("ActiveEnterTimestamp", ""))

    # 推断配置文件路径
    if "@" in service_name:
        # 模板服务: ftrigger@dev -> ~/.config/ftrigger/dev.yaml
        instance_name = service_name.split("@")[1].replace(".service", "")
        config_path = str(Path.home() / ".config" / "ftrigger" / f"{instance_name}.yaml")
    else:
        # 单实例服务: ~/.config/ftrigger/config.yaml
        config_path = str(Path.home() / ".config" / "ftrigger" / "config.yaml")

    return InstanceInfo(
        pid=pid,
        type="service",
        name=service_name,
        config_path=config_path,
        start_time=start_time,
        status=status,
    )


def get_standalone_processes(exclude_pids: Optional[set[int]] = None) -> list[InstanceInfo]:
    """获取独立进程

    Args:
        exclude_pids: 要排除的 PID 集合（如 systemd 服务的 PID）

    Returns:
        实例信息列表
    """
    if exclude_pids is None:
        exclude_pids = set()

    instances = []

    try:
        # 使用 ps 命令查找 ftrigger 进程
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        for line in result.stdout.split("\n"):
            if "ftrigger" in line and "grep" not in line:
                parts = line.split(None, 10)
                if len(parts) < 11:
                    continue

                try:
                    pid = int(parts[1])
                except (ValueError, IndexError):
                    continue

                # 排除已知的 PID（systemd 服务等）
                if pid in exclude_pids:
                    continue

                command = parts[10]

                # 跳过 systemctl 调用
                if "systemctl" in command:
                    continue

                # 跳过状态查询命令（ftrigger --status 或 ftrigger -s）
                if "--status" in command or " -s" in command.replace("ftrigger", ""):
                    continue

                # 获取进程启动时间
                start_time = None
                try:
                    # 使用 ps 获取启动时间
                    time_result = subprocess.run(
                        ["ps", "-p", str(pid), "-o", "lstart="],
                        capture_output=True,
                        text=True,
                        timeout=2,
                    )
                    if time_result.stdout.strip():
                        start_time = datetime.strptime(time_result.stdout.strip(), "%a %b %d %H:%M:%S %Y")
                except (ValueError, subprocess.TimeoutExpired):
                    pass

                # 从命令行提取配置文件
                config_path = extract_config_from_command(command)
                if not config_path:
                    config_path = "unknown"

                # 尝试从 /proc 读取命令行
                if config_path == "unknown":
                    try:
                        with open(f"/proc/{pid}/cmdline", "r") as f:
                            cmdline = f.read().replace("\x00", " ")
                            config_path = extract_config_from_command(cmdline)
                    except (FileNotFoundError, PermissionError):
                        pass

                instances.append(
                    InstanceInfo(
                        pid=pid,
                        type="standalone",
                        name=f"pid{pid}",
                        config_path=config_path,
                        start_time=start_time,
                        status="running",
                    )
                )

    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        logger.debug(f"Failed to query processes: {e}")

    return instances


def extract_config_from_command(command: str) -> str:
    """从命令行提取配置文件路径

    Args:
        command: 命令行字符串

    Returns:
        配置文件路径，未找到返回 "unknown"
    """
    # 匹配 --config 或 -c 参数
    match = re.search(r"--config[=\s]+([^\s]+)|-c[=\s]+([^\s]+)", command)
    if match:
        config = match.group(1) or match.group(2)
        return config

    # 匹配直接传递的 YAML 文件
    match = re.search(r"([\w/~/\.\-]+\.yaml)", command)
    if match:
        return match.group(1)

    return "unknown"


def get_all_instances() -> list[InstanceInfo]:
    """获取所有运行中的实例

    Returns:
        实例信息列表
    """
    services = get_systemd_services()
    # 收集 systemd 服务的 PID，避免在独立进程中重复检测
    service_pids = {s.pid for s in services if s.pid > 0}
    standalones = get_standalone_processes(exclude_pids=service_pids)
    return services + standalones


def get_instance_by_pid(pid: int) -> Optional[InstanceInfo]:
    """根据 PID 获取实例信息

    Args:
        pid: 进程 ID

    Returns:
        InstanceInfo 或 None
    """
    instances = get_all_instances()
    for inst in instances:
        if inst.pid == pid:
            return inst
    return None


def get_instance_by_name(name: str) -> Optional[InstanceInfo]:
    """根据名称获取实例信息（支持服务名）

    Args:
        name: 服务名称或 "pid<数字>"

    Returns:
        InstanceInfo 或 None
    """
    instances = get_all_instances()
    for inst in instances:
        if inst.name == name or inst.name == name + ".service":
            return inst

    # 尝试解析为 "pid123" 格式
    if name.startswith("pid"):
        try:
            pid = int(name[3:])
            for inst in instances:
                if inst.pid == pid:
                    return inst
        except ValueError:
            pass

    return None


def format_duration(start_time: datetime) -> str:
    """格式化时间持续

    Args:
        start_time: 开始时间

    Returns:
        格式化的持续时间字符串
    """
    if not start_time:
        return "unknown"

    delta = datetime.now() - start_time

    if delta < timedelta(minutes=1):
        seconds = delta.seconds
        return f"{seconds} second{'s' if seconds != 1 else ''}"
    elif delta < timedelta(hours=1):
        minutes = delta.seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    elif delta < timedelta(days=1):
        hours = delta.seconds // 3600
        mins = (delta.seconds % 3600) // 60
        if mins > 0:
            return f"{hours}h {mins}m"
        return f"{hours} hour{'s' if hours != 1 else ''}"
    else:
        days = delta.days
        hours = delta.seconds // 3600
        if hours > 0:
            return f"{days}d {hours}h"
        return f"{days} day{'s' if days != 1 else ''}"


def shorten_path(path: str, max_len: int = 35) -> str:
    """缩短路径显示

    Args:
        path: 文件路径
        max_len: 最大长度

    Returns:
        缩短后的路径
    """
    if not path or path == "unknown":
        return path

    if len(path) <= max_len:
        return path

    # 替换 home 目录为 ~
    home = str(Path.home())
    if path.startswith(home):
        path = "~" + path[len(home):]

    if len(path) > max_len:
        # 保留开头和结尾
        return path[:20] + "..." + path[-12:]

    return path
