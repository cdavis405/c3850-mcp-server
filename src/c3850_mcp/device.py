import os
import httpx
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class DeviceConfig(BaseModel):
    host: str
    username: str
    password: str
    port: int = 443

class C3850Device:
    def __init__(self, config: Optional[DeviceConfig] = None):
        if config:
            self.config = config
        else:
            self.config = DeviceConfig(
                host=os.getenv("C3850_HOST", ""),
                username=os.getenv("C3850_USERNAME", ""),
                password=os.getenv("C3850_PASSWORD", ""),
                port=int(os.getenv("C3850_PORT", "443")),
            )
        self.base_url = f"https://{self.config.host}:{self.config.port}/restconf/data"
        self.headers = {
            "Accept": "application/yang-data+json",
            "Content-Type": "application/yang-data+json",
        }
        self.auth = (self.config.username, self.config.password)

    async def _request(self, method: str, path: str, json: Optional[Dict] = None) -> Dict[str, Any]:
        """Make an HTTP request to the device."""
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.request(
                method,
                f"{self.base_url}{path}",
                auth=self.auth,
                headers=self.headers,
                json=json,
                timeout=10.0
            )
            response.raise_for_status()
            if response.status_code == 204:
                return {}
            return response.json()

    async def get_interfaces_status(self) -> Dict[str, Any]:
        """Get status of all interfaces."""
        # ietf-interfaces:interfaces-state
        return await self._request("GET", "/ietf-interfaces:interfaces-state")

    async def get_vlan_brief(self) -> Dict[str, Any]:
        """Get VLAN information."""
        # Cisco-IOS-XE-vlan-oper:vlan-oper-data
        return await self._request("GET", "/Cisco-IOS-XE-vlan-oper:vlan-oper-data")

    async def get_system_summary(self) -> Dict[str, Any]:
        """Get system summary."""
        # Cisco-IOS-XE-native:native/version
        return await self._request("GET", "/Cisco-IOS-XE-native:native/version")
    
    async def get_transceiver_stats(self) -> Dict[str, Any]:
        """Get transceiver statistics."""
        # Note: Specific YANG model for transceiver stats might vary, using a generic interface query for now
        # or assuming a specific model if known. For now, we'll try to get interface details which often contain this.
        return await self._request("GET", "/Cisco-IOS-XE-interfaces-oper:interfaces/interface")

    async def get_device_health(self) -> Dict[str, Any]:
        """Get device health (CPU, Memory, Environment)."""
        cpu = await self._request("GET", "/Cisco-IOS-XE-process-cpu-oper:cpu-usage")
        mem = await self._request("GET", "/Cisco-IOS-XE-process-memory-oper:memory-usage-processes")
        env = await self._request("GET", "/Cisco-IOS-XE-environment-oper:environment-sensors")
        return {
            "cpu": cpu,
            "memory": mem,
            "environment": env
        }

    async def get_recent_logs(self) -> Dict[str, Any]:
        """Get recent log messages."""
        # Cisco-IOS-XE-checkpoint-archive-oper:checkpoint-archives
        # Note: Syslog via RESTCONF is not always straightforward. 
        # We might need to rely on a specific operational model if available.
        # Fallback to native logging config if operational data isn't exposed.
        return await self._request("GET", "/Cisco-IOS-XE-native:native/logging")

    async def check_interface_errors(self) -> Dict[str, Any]:
        """Check for interface errors."""
        return await self._request("GET", "/ietf-interfaces:interfaces-state")

    async def set_interface_state(self, interface: str, state: str) -> Dict[str, Any]:
        """Set interface state (up/down)."""
        enabled = state.lower() == "up"
        payload = {
            "ietf-interfaces:interface": {
                "name": interface,
                "enabled": enabled
            }
        }
        # Using PATCH to merge config
        return await self._request("PATCH", f"/ietf-interfaces:interfaces/interface={interface}", json=payload)

    async def set_interface_vlan(self, interface: str, vlan_id: int) -> Dict[str, Any]:
        """Set access VLAN for an interface."""
        # Cisco-IOS-XE-native:native/interface/GigabitEthernet={name}
        # Note: Interface type needs to be handled dynamically in a real scenario.
        # Assuming GigabitEthernet for simplicity or parsing the name.
        if "GigabitEthernet" in interface:
            if_type = "GigabitEthernet"
            if_name = interface.replace("GigabitEthernet", "")
        elif "TenGigabitEthernet" in interface:
            if_type = "TenGigabitEthernet"
            if_name = interface.replace("TenGigabitEthernet", "")
        else:
            raise ValueError("Unsupported interface type")

        payload = {
            f"Cisco-IOS-XE-native:{if_type}": {
                "name": if_name,
                "switchport": {
                    "access": {
                        "vlan": {
                            "vlan": vlan_id
                        }
                    },
                    "mode": {
                        "access": {}
                    }
                }
            }
        }
        return await self._request("PATCH", f"/Cisco-IOS-XE-native:native/interface/{if_type}={if_name}", json=payload)

    async def set_vlan_name(self, vlan_id: int, name: str) -> Dict[str, Any]:
        """Set name for a VLAN."""
        payload = {
            "Cisco-IOS-XE-vlan-oper:vlan-instance": {
                "id": vlan_id,
                "name": name
            }
        }
        # Note: vlan-oper is usually read-only. Configuration should go to native vlan.
        payload_config = {
            "Cisco-IOS-XE-native:vlan": {
                "id": vlan_id,
                "name": name
            }
        }
        return await self._request("PATCH", f"/Cisco-IOS-XE-native:native/vlan/vlan-list={vlan_id}", json=payload_config)

    async def bounce_interface(self, interface: str) -> Dict[str, Any]:
        """Bounce (shut/no shut) an interface."""
        # RESTCONF doesn't have a "bounce" primitive, so we do two requests.
        await self.set_interface_state(interface, "down")
        return await self.set_interface_state(interface, "up")
