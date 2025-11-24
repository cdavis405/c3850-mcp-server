import os
from typing import Any, Dict, List, Optional
from netmiko import ConnectHandler
from pydantic import BaseModel

class DeviceConfig(BaseModel):
    host: str
    username: str
    password: str
    secret: str
    device_type: str = "cisco_ios"

class C3850Device:
    def __init__(self, config: Optional[DeviceConfig] = None):
        if config:
            self.config = config
        else:
            # Load from environment variables if not provided
            self.config = DeviceConfig(
                host=os.getenv("C3850_HOST", ""),
                username=os.getenv("C3850_USERNAME", ""),
                password=os.getenv("C3850_PASSWORD", ""),
                secret=os.getenv("C3850_SECRET", ""),
            )
        self.connection = None

    def connect(self):
        """Establish connection to the device."""
        if not self.connection:
            self.connection = ConnectHandler(
                device_type=self.config.device_type,
                host=self.config.host,
                username=self.config.username,
                password=self.config.password,
                secret=self.config.secret,
            )
            self.connection.enable()

    def disconnect(self):
        """Disconnect from the device."""
        if self.connection:
            self.connection.disconnect()
            self.connection = None

    def send_command(self, command: str, use_textfsm: bool = False) -> str | List[Dict[str, Any]]:
        """Send a command to the device and return output."""
        self.connect()
        return self.connection.send_command(command, use_textfsm=use_textfsm)

    def send_config_set(self, commands: List[str]) -> str:
        """Send a set of configuration commands."""
        self.connect()
        return self.connection.send_config_set(commands)

    def get_interfaces_status(self) -> List[Dict[str, Any]]:
        """Get status of all interfaces."""
        # Use textfsm to parse 'show interfaces status'
        return self.send_command("show interfaces status", use_textfsm=True)

    def get_vlan_brief(self) -> str:
        """Get VLAN information."""
        return self.send_command("show vlan brief")

    def get_system_summary(self) -> str:
        """Get system summary (version, etc)."""
        return self.send_command("show version")
    
    def get_transceiver_stats(self) -> str:
        """Get transceiver statistics."""
        return self.send_command("show interfaces transceiver detail")

    def get_device_health(self) -> Dict[str, str]:
        """Get device health (CPU, Memory, Environment)."""
        cpu = self.send_command("show processes cpu sorted | include CPU")
        mem = self.send_command("show processes memory sorted | include Processor")
        env = self.send_command("show environment all")
        return {
            "cpu": cpu,
            "memory": mem,
            "environment": env
        }

    def get_recent_logs(self, count: int = 50) -> str:
        """Get recent log messages."""
        return self.send_command(f"show logging | last {count}")

    def check_interface_errors(self) -> str:
        """Check for interface errors."""
        return self.send_command("show interfaces | include (Interface|CRC|error)")

    def set_interface_state(self, interface: str, state: str) -> str:
        """Set interface state (up/down)."""
        cmd = "no shutdown" if state.lower() == "up" else "shutdown"
        return self.send_config_set([f"interface {interface}", cmd])

    def set_interface_vlan(self, interface: str, vlan_id: int) -> str:
        """Set access VLAN for an interface."""
        commands = [
            f"interface {interface}",
            "switchport mode access",
            f"switchport access vlan {vlan_id}"
        ]
        return self.send_config_set(commands)

    def set_vlan_name(self, vlan_id: int, name: str) -> str:
        """Set name for a VLAN."""
        commands = [
            f"vlan {vlan_id}",
            f"name {name}"
        ]
        return self.send_config_set(commands)

    def bounce_interface(self, interface: str) -> str:
        """Bounce (shut/no shut) an interface."""
        commands = [
            f"interface {interface}",
            "shutdown",
            "no shutdown"
        ]
        return self.send_config_set(commands)
