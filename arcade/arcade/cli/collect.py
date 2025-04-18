"""Functions for collecting process and system based statistics and information"""

import platform
import time
from threading import Thread
from typing import Any

import psutil
from pydantic import BaseModel, Field
from rich.box import ROUNDED
from rich.table import Table

from arcade.cli.utils import b2h  # bytes to human readable

COLLECT_RATE_MS = 1000

BYTES_STYLE = "green"
HZ_STYLE = "blue"
NUM_STYLE = "magenta"


class SystemInfo(BaseModel):
    """System information"""

    os: dict[str, str] = Field(..., description="OS information")
    cpu: dict[str, str | int | float] = Field(..., description="CPU information")
    memory: dict[str, int] = Field(..., description="Memory information")
    disk: dict[str, int] = Field(..., description="Disk information")
    network: dict[str, list[str]] = Field(..., description="Network information")

    def as_rich_table(self) -> Table:
        """Return a compact table of system info"""
        table = Table(
            title="System Information",
            show_header=True,
            header_style="bold magenta",
            expand=True,
            box=ROUNDED,
            padding=(0, 0),  # Minimal padding
        )

        # Define columns with compact widths
        table.add_column("Component", style="bold dim", width=10)
        table.add_column("Information", style="blue")

        # Combine OS and CPU into one row to save space
        os_info = f"{self.os['name']} ({self.os['architecture']})"
        cpu_info = f"{self.cpu['cores']} cores @ {self.cpu['frequency']:.0f} MHz"
        table.add_row("OS & CPU", f"{os_info}, {cpu_info}")

        # Combine Memory and Disk into one row
        mem_disk = f"Memory: {b2h(self.memory['total'])}, Disk: {b2h(self.disk['total'])}"
        table.add_row("Storage", mem_disk)

        return table


def get_default_system_info() -> SystemInfo:
    """Return a dict of system information at startup

    Values returned:
    - OS
        - name
        - version
        - architecture
    - CPU
        - name
        - cores
        - threads
        - frequency
    - Memory:
        - total memory
    - Disk:
        - total disk space
    - Network:
        - network interfaces

    """
    return SystemInfo(**{
        "os": {
            "name": platform.system(),
            "version": platform.version(),
            "architecture": platform.machine(),
        },
        "cpu": {
            "name": platform.processor(),
            "cores": psutil.cpu_count(logical=False),
            "threads": psutil.cpu_count(logical=True),
            "frequency": psutil.cpu_freq().current,
        },
        "memory": {
            "total": psutil.virtual_memory().total,
        },
        "disk": {
            "total": psutil.disk_usage("/").total,
        },
        "network": {
            "interfaces": [i for i in psutil.net_if_addrs()],
        },
    })


class SystemMetrics(BaseModel):
    """Metrics of this system that are collected at a regular interval

    Values returned:
    - CPU
        - percent_used
    - Memory
        - percent_used
    - Disk
        - percent_used
        - read_count
        - write_count
        - read_bytes
        - write_bytes
    - Network
        - bytes_sent
        - bytes_recv
        - packets_sent
        - packets_recv
        - errin
        - errout
        - dropin
        - dropout
    """

    cpu: dict[str, float] = Field(..., description="CPU metrics")
    memory: dict[str, float] = Field(..., description="Memory metrics")
    disk: dict[str, float] = Field(..., description="Disk metrics")
    network: dict[str, float] = Field(..., description="Network metrics")

    def as_rich_table(self) -> Table:
        """Return a compact table of system metrics"""
        table = Table(
            title="System Metrics",
            show_header=True,
            header_style="bold magenta",
            expand=True,
            box=ROUNDED,
            padding=(0, 0),  # Minimal padding
        )

        # Define two columns for compact display
        table.add_column("Resource", style="bold dim", width=10)
        table.add_column("Usage", style="blue")

        # Combine CPU and Memory into one row
        cpu_mem = (
            f"CPU: {self.cpu['percent_used']:.1f}%, Memory: {self.memory['percent_used']:.1f}%"
        )
        table.add_row("CPU/Memory", cpu_mem)

        # Combine Disk and Network into one row
        disk_info = f"Disk: {self.disk['percent_used']:.1f}%"
        net_info = (
            f"Net: {b2h(self.network['bytes_recv'])}/s ↓, {b2h(self.network['bytes_sent'])}/s ↑"
        )
        table.add_row("Disk/Net", f"{disk_info}, {net_info}")

        return table


class SystemCollector(Thread):
    """Collects system information at a regular interval"""

    def __init__(self, collect_rate_ms: int = COLLECT_RATE_MS):
        self.collect_rate_ms = collect_rate_ms
        self.system_info = get_default_system_info()
        self.system_metrics = None
        super().__init__(daemon=True)

    def run(self):
        should_continue = True
        self.system_metrics = self.collect_metrics()
        while should_continue:
            try:
                self.system_metrics = self.collect_metrics()
                time.sleep(self.collect_rate_ms / 1000)
            except KeyboardInterrupt:
                should_continue = False

    def collect_metrics(self) -> SystemMetrics:
        """Collect system metrics"""
        cpu_percent = psutil.cpu_percent()
        memory_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage("/").percent
        disk_io = psutil.disk_io_counters()
        network_io = psutil.net_io_counters()
        return SystemMetrics(**{
            "cpu": {
                "percent_used": cpu_percent,
            },
            "memory": {
                "percent_used": memory_percent,
            },
            "disk": {
                "percent_used": disk_percent,
                "read_count": disk_io.read_count,
                "write_count": disk_io.write_count,
                "read_bytes": disk_io.read_bytes,
                "write_bytes": disk_io.write_bytes,
            },
            "network": {
                "bytes_sent": network_io.bytes_sent,
                "bytes_recv": network_io.bytes_recv,
                "packets_sent": network_io.packets_sent,
                "packets_recv": network_io.packets_recv,
                "errin": network_io.errin,
                "errout": network_io.errout,
                "dropin": network_io.dropin,
                "dropout": network_io.dropout,
            },
        })


class ProcessInfo(BaseModel):
    """Static information about a process"""

    pid: int = Field(..., description="Process ID")
    name: str = Field(..., description="Process name")
    username: str = Field(..., description="Process owner")


class ProcessMetrics(BaseModel):
    """Dynamic metrics about a process

    accounts for when metric is not available because of
    differences between operating systems

    Values returned:
    - CPU
        - percent_used
        - user_time
        - system_time
        - child_user_time
        - child_system_time
    - Process
        - num_children
        - num_threads
        - num_ctx_switches
            - voluntary
            - involuntary
    - Memory
        - percent_used
        - rss
        - vms
    - Disk
        - read_count
        - write_count
        - read_bytes
        - write_bytes
        - open_files
        - num_fds
    - Connections
        - local_address
        - remote_address
        - status
        - family
        - kind
    """

    cpu: dict[str, float] = Field(..., description="CPU metrics")
    process: dict[str, int | float] = Field(..., description="Process metrics")
    memory: dict[str, int | float] = Field(..., description="Memory metrics")
    disk: dict[str, int | float] = Field(..., description="Disk metrics")
    connections: list[dict[str, str | int]] = Field(..., description="Network connections")

    def as_rich_table(self) -> tuple[Table, Table]:
        """Return compact tables for process metrics and connections"""
        # Main process metrics table
        table = Table(
            title="Process Metrics",
            show_header=True,
            header_style="bold magenta",
            expand=True,
            box=ROUNDED,
            padding=(0, 0),  # Minimal padding
        )

        # Use two columns for compact display
        table.add_column("Resource", style="bold dim", width=10)  # Grey
        table.add_column("Stats", style="blue")  # Blue

        # Combine CPU and Memory into one row
        cpu_info = f"CPU: {self.cpu['percent_used']:.1f}%"
        mem_info = f"Memory: {self.memory['percent_used']:.2f}% ({b2h(self.memory['rss'])})"
        table.add_row("Resources", f"{cpu_info}, {mem_info}")

        # Combine Process and Files info into one row
        proc_info = (
            f"Threads: {self.process['num_threads']}, Children: {self.process['num_children']}"
        )
        files_info = f"Files: {self.disk['num_fds'] or 0}"
        table.add_row("Process", f"{proc_info}, {files_info}")

        # Connection table - optimized for better column proportions
        connections_table = Table(
            title="Connections",
            show_header=True,
            header_style="bold magenta",
            expand=True,
            box=ROUNDED,
            padding=(0, 0),  # Minimal padding
        )

        show = 20
        if self.connections:
            # Display connections
            connections_to_show = self.connections[:show]
            total_connections = len(self.connections)

            # Adjust column widths - make local address a bit narrower to give remote more space
            connections_table.add_column("Local", style="bold dim", width=20)  # Grey
            connections_table.add_column(
                "Remote", style="bold dim", width=28
            )  # Grey, wider for remote addresses
            connections_table.add_column("Status", style="blue", width=10)  # Blue

            for c in connections_to_show:
                local = str(c["local_address"]).strip("()')").replace("'", "")
                remote = str(c["remote_address"]).strip("()')").replace("'", "")
                if remote == "":
                    remote = "-"

                # Truncate long addresses if needed
                if len(local) > 20:
                    local = local[:17] + "..."
                if len(remote) > 28:
                    remote = remote[:25] + "..."

                connections_table.add_row(local, remote, str(c["status"]))

            if total_connections > show:
                connections_table.add_row(f"+ {total_connections - show} more", "", "")
        else:
            connections_table.add_column("Status", style="blue")
            connections_table.add_row("No connections")

        return table, connections_table


class ProcessCollector(Thread):
    """Collects process information at a regular interval"""

    def __init__(self, proc: psutil.Process, collect_rate_ms: int = COLLECT_RATE_MS):
        self._process = proc
        self.collect_rate_ms = collect_rate_ms

        self.process_info = ProcessInfo(**{
            "pid": self._process.pid,
            "name": self._process.name(),
            "username": self._process.username(),
        })
        self.process_metrics = None
        super().__init__(daemon=True)

    def run(self):
        should_continue = True
        self.process_metrics = self.collect_metrics()
        while should_continue:
            try:
                if self._is_alive():
                    self.process_metrics = self.collect_metrics()
                    time.sleep(self.collect_rate_ms / 1000)
                else:
                    should_continue = False
            except KeyboardInterrupt:
                should_continue = False

    def _is_alive(self) -> bool:
        return self._process.is_running() and self._process.status() != psutil.STATUS_ZOMBIE

    def _get_metric(self, metric_name: str, default: Any = None) -> Any:
        try:
            return getattr(self._process, metric_name)()
        except:
            return default

    def collect_metrics(self) -> ProcessMetrics:
        with self._process.oneshot():
            cpu_percent = self._get_metric("cpu_percent")
            cpu_times = self._get_metric("cpu_times")
            num_children = len(self._get_metric("children"))
            num_threads = self._get_metric("num_threads")
            num_ctx_switches = self._get_metric("num_ctx_switches")
            memory_percent = self._get_metric("memory_percent")
            memory_info = self._get_metric("memory_info")
            disk_io = self._get_metric("io_counters")
            num_fds = self._get_metric("num_fds")
            connections = self._get_metric("connections")

        return ProcessMetrics(**{
            "cpu": {
                "percent_used": cpu_percent,
                "user_time": cpu_times.user,
                "system_time": cpu_times.system,
                "child_user_time": cpu_times.children_user,
                "child_system_time": cpu_times.children_system,
            },
            "process": {
                "num_children": num_children,
                "num_threads": num_threads,
                "num_ctx_switches": num_ctx_switches.voluntary + num_ctx_switches.involuntary,
            },
            "memory": {
                "percent_used": memory_percent,
                "rss": memory_info.rss,
                "vms": memory_info.vms,
            },
            "disk": {
                "num_fds": num_fds,
            },
            "connections": [
                {
                    "local_address": str(c.laddr),
                    "remote_address": str(c.raddr),
                    "status": str(c.status),
                    "family": str(c.family),
                    "kind": str(c.type),
                }
                for c in connections
            ],
        })


def get_process_by_name(name):
    for proc in psutil.process_iter(["name"]):
        if proc.info["name"] == name:
            return proc


def get_process_by_pid(pid):
    try:
        return psutil.Process(pid)
    except psutil.NoSuchProcess:
        return None
