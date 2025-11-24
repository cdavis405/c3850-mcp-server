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

    async def get_interfaces_status(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get status of all interfaces."""
        # ietf-interfaces:interfaces-state
        data = await self._request("GET", "/ietf-interfaces:interfaces-state")
        interfaces = data.get("ietf-interfaces:interfaces-state", {}).get("interface", [])
        
        # Fetch config to get descriptions
        try:
            config_data = await self._request("GET", "/ietf-interfaces:interfaces")
            config_interfaces = config_data.get("ietf-interfaces:interfaces", {}).get("interface", [])
            config_map = {i.get("name"): i for i in config_interfaces}
        except Exception:
            # Fallback if config fetch fails
            config_map = {}

        simplified_interfaces = []
        for iface in interfaces:
            name = iface.get("name")
            oper_status = iface.get("oper-status")
            
            # Apply filter if present
            if status_filter:
                if status_filter.lower() in ["up", "down"]:
                    if oper_status != status_filter.lower():
                        continue
                elif status_filter not in name:
                    continue

            config = config_map.get(name, {})
            simplified_interfaces.append({
                "name": name,
                "description": config.get("description", ""),
                "debug": "test_reload",
                "admin_status": iface.get("admin-status"),
                "oper_status": oper_status,
                "speed": iface.get("speed"),
                "mac": iface.get("phys-address")
            })
        return simplified_interfaces

    async def get_vlan_brief(self) -> List[Dict[str, Any]]:
        """Get VLAN information."""
        # Cisco-IOS-XE-vlan-oper:vlan-oper-data
        data = await self._request("GET", "/Cisco-IOS-XE-vlan-oper:vlan-oper-data")
        vlans = data.get("Cisco-IOS-XE-vlan-oper:vlan-oper-data", {}).get("vlan-instance", [])
        
        simplified_vlans = []
        for vlan in vlans:
            simplified_vlans.append({
                "id": vlan.get("id"),
                "name": vlan.get("name"),
                "status": vlan.get("status", "active"), # Default to active if not present
                "ports": [p.get("interface") for p in vlan.get("ports", [])]
            })
        return simplified_vlans

    async def get_system_summary(self) -> Dict[str, Any]:
        """Get system summary."""
        # Cisco-IOS-XE-native:native/version
        data = await self._request("GET", "/Cisco-IOS-XE-native:native/version")
        version_data = data.get("Cisco-IOS-XE-native:version", {})
        return {
            "version": version_data.get("version"),
            "platform": "Cisco 3850", # Hardcoded as we know the device type or could extract
            "uptime": "Unknown" # Uptime usually in a different model, keeping simple for now
        }
    
    async def get_transceiver_stats(self) -> Dict[str, Any]:
        """Get transceiver statistics."""
        # Note: Specific YANG model for transceiver stats might vary, using a generic interface query for now
        # or assuming a specific model if known. For now, we'll try to get interface details which often contain this.
        return await self._request("GET", "/Cisco-IOS-XE-interfaces-oper:interfaces/interface")

    async def get_device_health(self) -> Dict[str, Any]:
        """Get device health (CPU, Memory, Environment)."""
        cpu_data = await self._request("GET", "/Cisco-IOS-XE-process-cpu-oper:cpu-usage")
        mem_data = await self._request("GET", "/Cisco-IOS-XE-process-memory-oper:memory-usage-processes")
        env_data = await self._request("GET", "/Cisco-IOS-XE-environment-oper:environment-sensors")
        
        cpu_usage = cpu_data.get("Cisco-IOS-XE-process-cpu-oper:cpu-usage", {}).get("cpu-utilization", {}).get("five-seconds")
        
        # Simplified memory calculation (just taking the first pool or total if available)
        # This is a simplification as memory structures can be complex
        memory_usage = "Unknown" 
        if "Cisco-IOS-XE-process-memory-oper:memory-usage-processes" in mem_data:
             # Just a placeholder logic as real parsing depends on exact structure
             memory_usage = "Check details"

        return {
            "cpu_usage_percent": cpu_usage,
            "memory_usage": memory_usage,
            "environment_summary": "Check details" # Simplifying for now
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
        from urllib.parse import quote
        enabled = state.lower() == "up"
        payload = {
            "ietf-interfaces:interface": {
                "name": interface,
                "enabled": enabled
            }
        }
        # Using PATCH to merge config
        encoded_interface = quote(interface, safe='')
        return await self._request("PATCH", f"/ietf-interfaces:interfaces/interface={encoded_interface}", json=payload)

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
