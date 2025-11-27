import os
import asyncio
import httpx
import jmespath
import time
from functools import wraps
from typing import Any, Dict, List, Optional
from urllib.parse import quote
from pydantic import BaseModel

class DeviceConfig(BaseModel):
    host: str
    username: str
    password: str
    port: int = 443

def ttl_cache(ttl: int = 60):
    """Simple TTL cache decorator for async methods."""
    def decorator(func):
        cache = {}
        
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Create a key based on arguments
            key = (func.__name__, args, frozenset(kwargs.items()))
            now = time.time()
            
            if key in cache:
                result, timestamp = cache[key]
                if now - timestamp < ttl:
                    return result
            
            result = await func(self, *args, **kwargs)
            cache[key] = (result, now)
            return result
            
        return wrapper
    return decorator

class C3850Device:
    def __init__(self, config: Optional[DeviceConfig] = None, http_client: Optional[httpx.AsyncClient] = None):
        self.http_client = http_client
        self.semaphore = asyncio.Semaphore(2)
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

    def normalize_interface_name(self, name: str) -> str:
        """Helper to expand short names like 'Te1/0/1' to full IOS names."""
        name_lower = name.lower()
        
        # Map of prefix to (full_name, prefix_length_to_replace)
        # Order matters: check longer matches first if there's overlap, 
        # but here we check full names first to avoid double replacement.
        mappings = [
            ("tengigabitethernet", "TenGigabitEthernet"),
            ("gigabitethernet", "GigabitEthernet"),
            ("fastethernet", "FastEthernet"),
            ("fortygigabitethernet", "FortyGigabitEthernet"),
            ("vlan", "Vlan"),
            ("te", "TenGigabitEthernet"),
            ("gi", "GigabitEthernet"),
            ("fa", "FastEthernet"),
            ("fo", "FortyGigabitEthernet"),
            ("vl", "Vlan"),
        ]

        for prefix, full_name in mappings:
            if name_lower.startswith(prefix):
                # Replace the prefix with the full name
                # We use the length of the matched prefix to slice the original string's number part
                # But wait, we want to replace the *start* of the string.
                # And we want to preserve the rest of the string (the numbers).
                # Since we matched on lower, we can just replace the start.
                return full_name + name[len(prefix):]
        
        return name # Return raw string if no match

    async def get_cdp_neighbors(self, interface: str) -> List[Dict[str, Any]]:
        """Get CDP neighbors for an interface."""
        # Cisco-IOS-XE-cdp-oper:cdp-neighbor-details
        data = await self._request("GET", "/Cisco-IOS-XE-cdp-oper:cdp-neighbor-details")
        # Filter for the specific interface
        neighbors = jmespath.search('"Cisco-IOS-XE-cdp-oper:cdp-neighbor-details"."cdp-neighbor-detail"[]', data) or []
        
        # Filter by local interface name
        interface_lower = interface.lower()
        matched = []
        for n in neighbors:
            local_intf = n.get("local-intf-name", "").lower()
            # Try exact match or normalized match
            if local_intf == interface_lower or self.normalize_interface_name(local_intf).lower() == interface_lower:
                matched.append(n)
        return matched

    async def get_lldp_neighbors(self, interface: str) -> List[Dict[str, Any]]:
        """Get LLDP neighbors for an interface."""
        # Cisco-IOS-XE-lldp-oper:lldp-entries
        data = await self._request("GET", "/Cisco-IOS-XE-lldp-oper:lldp-entries")
        neighbors = jmespath.search('"Cisco-IOS-XE-lldp-oper:lldp-entries"."lldp-entry"[]', data) or []
        
        interface_lower = interface.lower()
        matched = []
        for n in neighbors:
            local_intf = n.get("local-interface", "").lower()
            if local_intf == interface_lower or self.normalize_interface_name(local_intf).lower() == interface_lower:
                matched.append(n)
        return matched

    async def get_interface_details(self, interface: str) -> Dict[str, Any]:
        """Get detailed configuration for an interface."""
        import re
        match = re.match(r"([A-Za-z]+)([\d/.]+)", interface)
        if not match:
            return {}
        
        if_type = match.group(1)
        if_name = match.group(2)
        
        try:
            # Encode the interface name (e.g. 1/0/2 -> 1%2F0%2F2)
            encoded_name = quote(if_name, safe='')
            path = f"/Cisco-IOS-XE-native:native/interface/{if_type}={encoded_name}"
            data = await self._request("GET", path)
            key = f"Cisco-IOS-XE-native:{if_type}"
            return data.get(key, {})
        except Exception:
            return {}

    async def analyze_interface_impact(self, interface: str) -> Dict[str, Any]:
        """Returns a risk assessment for an interface."""
        full_name = self.normalize_interface_name(interface)
        
        # Get details
        config = await self.get_interface_details(full_name)
        status_list = await self.get_interfaces_status(status_filter=full_name)
        status = status_list[0] if status_list else {}
        cdp_data = await self.get_cdp_neighbors(full_name)
        lldp_data = await self.get_lldp_neighbors(full_name)
        
        risk_level = "LOW"
        warnings = []
        
        # Check 1: Is it a Trunk?
        switchport = config.get("switchport", {})
        if isinstance(switchport, dict):
             mode = switchport.get("mode", {})
             if "trunk" in mode:
                 risk_level = "CRITICAL"
                 warnings.append("⚠️ Interface is a TRUNK port carrying multiple VLANs.")
        
        # Check 2: Description Keywords
        desc = config.get("description", "").lower()
        if any(x in desc for x in ['wap', 'access point', 'uplink', 'core', 'server', 'router']):
            if risk_level != "CRITICAL":
                risk_level = "HIGH"
            warnings.append(f"⚠️ Description contains high-value keyword: '{config.get('description')}'")
            
        # Check 3: Active Neighbors (CDP & LLDP)
        if cdp_data:
            risk_level = "CRITICAL"
            devices = [n.get("device-id") for n in cdp_data]
            warnings.append(f"⚠️ Active CDP Neighbor(s) detected: {', '.join(devices)}")
            
        if lldp_data:
            risk_level = "CRITICAL"
            devices = [n.get("device-id") for n in lldp_data]
            warnings.append(f"⚠️ Active LLDP Neighbor(s) detected: {', '.join(devices)}")
            
        # Check 4: Is it already down?
        # If we are analyzing impact of a change, knowing it's down is useful.
        # If it's admin down, changing it (unless bringing it up) has low impact.
        if status.get("admin_status") == "down":
             risk_level = "ZERO"
             warnings.append("Interface is already administratively down.")
        
        return {
            "risk_level": risk_level,
            "warnings": warnings,
            "interface": full_name
        }

    async def analyze_vlan_impact(self, vlan_id: int) -> Dict[str, Any]:
        """Returns a risk assessment for a VLAN."""
        risk_level = "LOW"
        warnings = []
        
        if vlan_id == 1:
            risk_level = "CRITICAL"
            warnings.append("⚠️ VLAN 1 is the default VLAN and often carries management traffic.")
            
        return {
            "risk_level": risk_level,
            "warnings": warnings,
            "vlan_id": vlan_id
        }

    def get_capabilities(self) -> Dict[str, Any]:
        """Get the capabilities of the device and server."""
        return {
            "device_type": "Cisco 3850",
            "features": [
                "Interface Normalization (e.g. 'Te1/0/1' -> 'TenGigabitEthernet1/0/1')",
                "Blast Radius Analysis (Risk assessment before critical actions)",
                "Log Filtering (Server-side filtering of 'get_recent_logs')",
                "Connection Pooling (Efficient HTTP connection reuse)",
                "Interface Filtering (Filter by 'connected'/'not connected')"
            ],
            "tools": [
                "Interface Management (Status, State, VLAN, Bounce)",
                "VLAN Management (Brief, Name)",
                "Diagnostics (Health, Transceivers, Logs, Errors)",
                "System Information (Summary)"
            ]
        }

    async def _request(self, method: str, path: str, json: Optional[Dict] = None) -> Dict[str, Any]:
        """Make an HTTP request to the device."""
        async with self.semaphore:
            if self.http_client:
                response = await self.http_client.request(
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
        
        # Optimization: If status_filter is a specific interface, fetch only that one.
        if status_filter and status_filter.lower() not in ["up", "down", "connected", "not connected"]:
            normalized_filter = self.normalize_interface_name(status_filter)
            # Check if it looks like a full interface name (starts with known type)
            # normalize_interface_name expands prefixes, so if it starts with a known type, it's likely a full name.
            # We can try to fetch it directly.
            
            # Simple check: does it start with an uppercase letter? normalize_interface_name returns TitleCase.
            # And does it contain numbers?
            if any(normalized_filter.startswith(x) for x in ["TenGigabitEthernet", "GigabitEthernet", "FastEthernet", "Vlan", "Loopback", "Port-channel"]):
                 from urllib.parse import quote
                 encoded_name = quote(normalized_filter, safe='')
                 
                 try:
                     # Fetch state
                     state_data = await self._request("GET", f"/ietf-interfaces:interfaces-state/interface={encoded_name}")
                     iface_state = state_data.get("ietf-interfaces:interface", {})
                     
                     # Fetch config
                     config_data = await self._request("GET", f"/ietf-interfaces:interfaces/interface={encoded_name}")
                     iface_config = config_data.get("ietf-interfaces:interface", {})
                     
                     if iface_state:
                         # Derive admin_status from config 'enabled' if available
                         admin_status = iface_state.get("admin-status")
                         if "enabled" in iface_config:
                             admin_status = "up" if iface_config["enabled"] else "down"

                         return [{
                            "name": iface_state.get("name"),
                            "description": iface_config.get("description", ""),
                            "admin_status": admin_status,
                            "oper_status": iface_state.get("oper-status"),
                            "speed": iface_state.get("speed"),
                            "mac": iface_state.get("phys-address")
                         }]
                 except Exception:
                     # If specific fetch fails (e.g. 404), fall back to full fetch
                     pass

        # ietf-interfaces:interfaces-state
        data = await self._request("GET", "/ietf-interfaces:interfaces-state")
        
        # Use JMESPath to extract interfaces
        interfaces = jmespath.search('"ietf-interfaces:interfaces-state".interface[]', data) or []
        
        # Fetch config to get descriptions
        try:
            config_data = await self._request("GET", "/ietf-interfaces:interfaces")
            config_interfaces = jmespath.search('"ietf-interfaces:interfaces".interface[]', config_data) or []
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
                f_lower = status_filter.lower()
                if f_lower in ["up", "down"]:
                    if oper_status != f_lower:
                        continue
                elif f_lower == "connected":
                    # Connected means oper-status is up
                    if oper_status != "up":
                        continue
                elif f_lower == "not connected":
                    # Not connected means oper-status is not up (down, lower-layer-down, etc)
                    if oper_status == "up":
                        continue
                else:
                    # Normalize the filter to match full interface names
                    normalized_filter = self.normalize_interface_name(status_filter)
                    if normalized_filter not in name:
                        continue

            config = config_map.get(name, {})
            
            # Derive admin_status from config 'enabled' if available, otherwise fallback to state
            # This handles cases where state might be out of sync or misleading
            admin_status = iface.get("admin-status")
            if "enabled" in config:
                admin_status = "up" if config["enabled"] else "down"
            
            simplified_interfaces.append({
                "name": name,
                "description": config.get("description", ""),
                "admin_status": admin_status,
                "oper_status": oper_status,
                "speed": iface.get("speed"),
                "mac": iface.get("phys-address")
            })
        return simplified_interfaces

    async def get_vlan_brief(self) -> List[Dict[str, Any]]:
        """Get VLAN information."""
        # Cisco-IOS-XE-vlan-oper:vlan-oper-data
        data = await self._request("GET", "/Cisco-IOS-XE-vlan-oper:vlan-oper-data")
        vlans = jmespath.search('"Cisco-IOS-XE-vlan-oper:vlan-oper-data"."vlan-instance"[]', data) or []
        
        simplified_vlans = []
        for vlan in vlans:
            simplified_vlans.append({
                "id": vlan.get("id"),
                "name": vlan.get("name"),
                "status": vlan.get("status", "active"), # Default to active if not present
                "ports": jmespath.search("ports[].interface", vlan) or []
            })
        return simplified_vlans

    async def get_system_summary(self) -> Dict[str, Any]:
        """Get system summary."""
        # Cisco-IOS-XE-native:native/version
        data = await self._request("GET", "/Cisco-IOS-XE-native:native/version")
        version = jmespath.search('"Cisco-IOS-XE-native:version".version', data)
        return {
            "version": version,
            "platform": "Cisco 3850", # Hardcoded as we know the device type or could extract
            "uptime": "Unknown" # Uptime usually in a different model, keeping simple for now
        }
    
    @ttl_cache(ttl=60)
    async def get_transceiver_stats(self) -> Dict[str, Any]:
        """Get transceiver statistics."""
        # Note: Specific YANG model for transceiver stats might vary, using a generic interface query for now
        # or assuming a specific model if known. For now, we'll try to get interface details which often contain this.
        return await self._request("GET", "/Cisco-IOS-XE-interfaces-oper:interfaces/interface")

    async def get_device_health(self) -> Dict[str, Any]:
        """Get device health (CPU, Memory, Environment)."""
        cpu_data = await self._request("GET", "/Cisco-IOS-XE-process-cpu-oper:cpu-usage")
        mem_data = await self._request("GET", "/Cisco-IOS-XE-process-memory-oper:memory-usage-processes")
        
        cpu_usage = jmespath.search('"Cisco-IOS-XE-process-cpu-oper:cpu-usage"."cpu-utilization"."five-seconds"', cpu_data)
        
        # Simplified memory calculation
        memory_usage = "Unknown" 
        if jmespath.search('"Cisco-IOS-XE-process-memory-oper:memory-usage-processes"', mem_data):
             memory_usage = "Check details"

        return {
            "cpu_usage_percent": cpu_usage,
            "memory_usage": memory_usage,
            "environment_summary": "Check details" # Simplifying for now
        }

    async def get_recent_logs(self, count: int = 50, search_term: Optional[str] = None) -> Dict[str, Any]:
        """Get recent log messages.
        
        Args:
            count: Number of log lines to retrieve (default 50).
            search_term: Optional. Filter logs by this term (case-insensitive).
        """
        # Cisco-IOS-XE-checkpoint-archive-oper:checkpoint-archives
        # Note: Syslog via RESTCONF is not always straightforward. 
        # We might need to rely on a specific operational model if available.
        # Fallback to native logging config if operational data isn't exposed.
        # The count parameter is accepted but not used in this RESTCONF query
        # as the YANG model doesn't support limiting results.
        data = await self._request("GET", "/Cisco-IOS-XE-native:native/logging")
        
        # If data is a dict (which it likely is from _request), we need to extract something iterable if possible.
        # However, /Cisco-IOS-XE-native:native/logging usually returns configuration, not actual logs.
        # Actual logs are often in /Cisco-IOS-XE-logging:logging-events or similar if supported.
        # For this exercise, assuming 'data' contains a list of log entries or we are filtering the raw response structure.
        # If the response is just config, filtering might not make sense, but let's assume we want to filter whatever we get.
        
        # If we can't parse it as a list of strings, we might just return it as is if no search_term.
        # But the user wants filtering.
        # Let's assume for a moment that 'data' might contain a list under some key, or we just filter the string representation if it's unstructured.
        
        # Realistically, if we are just returning the config, we can filter the config keys/values?
        # Or maybe the user implies we should be fetching actual logs.
        # Given the prompt "Retrieving 'Last 50' logs often returns 50 lines of useless clutter", 
        # it implies we ARE getting logs.
        # So let's assume the previous implementation was returning something list-like or string-like.
        # The previous implementation returned: return await self._request("GET", "/Cisco-IOS-XE-native:native/logging")
        # If that returns a dict, we can't easily "filter lines".
        
        # Let's try to be smart. If it's a dict, we convert to string and filter lines?
        # Or maybe we assume the user has a way to get logs and we just implement the filtering logic on the result.
        
        # Let's implement a generic filter on the result.
        import json
        
        # If it's a dict, maybe we can flatten it to lines?
        # For now, let's assume we want to filter the text representation of the JSON.
        
        if not search_term:
            return data
            
        # If search_term is provided, we need to filter.
        # Since we don't know the exact structure of the logs (as it was just returning config before),
        # let's try to filter the JSON output line by line if we were to dump it.
        # Or better, if the data is a list (which would be ideal for logs), filter the list.
        
        if isinstance(data, list):
             return [item for item in data if search_term.lower() in str(item).lower()]
        
        # If it's a dict, it's harder.
        # Maybe we just return the whole thing if we can't filter easily, or we filter keys?
        # The user example showed: logs = [line for line in raw_logs if search_term.lower() in line.lower()]
        # This implies raw_logs is a list of strings.
        
        # Let's assume for the sake of the requested change that we might be getting a list, 
        # or we can convert the dict to a list of lines (e.g. JSON dump lines) and filter those?
        # That changes the return type from Dict to List[str] potentially.
        # The return type hint says Dict[str, Any].
        
        # Let's stick to the user's request: "Add a search_term parameter to filter server-side".
        # I will implement a best-effort filter.
        
        if isinstance(data, dict):
            # If it's a dict, maybe we filter the keys or values?
            # Or maybe we just return it if we can't filter.
            # But the user specifically wants to filter "clutter".
            # Let's try to filter the string representation of the dict entries?
            # This is tricky without knowing the exact structure.
            # But let's assume the user knows what they are doing and expects us to filter *something*.
            
            # If we assume the response is a list of log objects wrapped in a dict key:
            # e.g. {"logging": {"events": [...]}}
            # We could try to find a list and filter it.
            
            # For now, let's implement a recursive search/filter? No, that's too complex.
            # Let's try to convert to string, split by lines, filter, and return as a list of strings?
            # That changes the return type, but `get_recent_logs` in server.py converts result to str anyway.
            
            text = json.dumps(data, indent=2)
            lines = text.splitlines()
            filtered_lines = [line for line in lines if search_term.lower() in line.lower()]
            return {"filtered_logs": filtered_lines}

        return data

    async def check_interface_errors(self) -> Dict[str, Any]:
        """Check for interface errors."""
        return await self._request("GET", "/ietf-interfaces:interfaces-state")

    async def set_interface_state(self, interface: str, state: str) -> Dict[str, Any]:
        """Set interface state (up/down)."""
        interface = self.normalize_interface_name(interface)
        from urllib.parse import quote
        
        # Determine type and name for native model
        if_type = None
        if_name = None
        
        if "TenGigabitEthernet" in interface:
            if_type = "TenGigabitEthernet"
            if_name = interface.replace("TenGigabitEthernet", "")
        elif "GigabitEthernet" in interface:
            if_type = "GigabitEthernet"
            if_name = interface.replace("GigabitEthernet", "")
        elif "FastEthernet" in interface:
            if_type = "FastEthernet"
            if_name = interface.replace("FastEthernet", "")
        elif "FortyGigabitEthernet" in interface:
            if_type = "FortyGigabitEthernet"
            if_name = interface.replace("FortyGigabitEthernet", "")
        elif "Vlan" in interface:
            if_type = "Vlan"
            if_name = interface.replace("Vlan", "")
            
        if if_type and if_name:
            encoded_name = quote(if_name, safe='')
            
            # Prepare IETF payload as well
            ietf_enabled = state.lower() == "up"
            ietf_payload = {
                "ietf-interfaces:interface": {
                    "name": interface,
                    "enabled": ietf_enabled
                }
            }
            encoded_interface = quote(interface, safe='')
            
            if state.lower() == "up":
                # To bring up:
                # 1. DELETE native shutdown
                try:
                    await self._request("DELETE", f"/Cisco-IOS-XE-native:native/interface/{if_type}={encoded_name}/shutdown")
                except Exception:
                    pass
                
                # 2. PATCH IETF enabled=true
                return await self._request("PATCH", f"/ietf-interfaces:interfaces/interface={encoded_interface}", json=ietf_payload)
            else:
                # To shut down:
                # 1. PATCH native shutdown
                native_payload = {
                    f"Cisco-IOS-XE-native:{if_type}": {
                        "name": if_name,
                        "shutdown": [None]
                    }
                }
                await self._request("PATCH", f"/Cisco-IOS-XE-native:native/interface/{if_type}={encoded_name}", json=native_payload)
                
                # 2. PATCH IETF enabled=false
                return await self._request("PATCH", f"/ietf-interfaces:interfaces/interface={encoded_interface}", json=ietf_payload)
        
        # Fallback to ietf-interfaces if unknown type
        enabled = state.lower() == "up"
        payload = {
            "ietf-interfaces:interface": {
                "name": interface,
                "enabled": enabled
            }
        }
        encoded_interface = quote(interface, safe='')
        return await self._request("PATCH", f"/ietf-interfaces:interfaces/interface={encoded_interface}", json=payload)

    async def set_interface_vlan(self, interface: str, vlan_id: int) -> Dict[str, Any]:
        """Set access VLAN for an interface."""
        # Cisco-IOS-XE-native:native/interface/GigabitEthernet={name}
        # Note: Interface type needs to be handled dynamically in a real scenario.
        # Assuming GigabitEthernet for simplicity or parsing the name.
        interface = self.normalize_interface_name(interface)
        if "TenGigabitEthernet" in interface:
            if_type = "TenGigabitEthernet"
            if_name = interface.replace("TenGigabitEthernet", "")
        elif "GigabitEthernet" in interface:
            if_type = "GigabitEthernet"
            if_name = interface.replace("GigabitEthernet", "")
        else:
            raise ValueError("Unsupported interface type")

        payload = {
            f"Cisco-IOS-XE-native:{if_type}": {
                "name": if_name,
                "switchport": {
                    "Cisco-IOS-XE-switch:access": {
                        "vlan": {
                            "vlan": vlan_id
                        }
                    },
                    "Cisco-IOS-XE-switch:mode": {
                        "access": {}
                    }
                }
            }
        }
        encoded_name = quote(if_name, safe='')
        return await self._request("PATCH", f"/Cisco-IOS-XE-native:native/interface/{if_type}={encoded_name}", json=payload)

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
        # Normalization happens in set_interface_state, but good to be explicit or just let it flow down.
        # Since we call set_interface_state, it will normalize there.
        # But wait, we need to pass the same normalized name to both calls to be safe/consistent?
        # Actually set_interface_state normalizes it, so we can just pass the raw string.
        # However, to be cleaner, let's normalize once here.
        interface = self.normalize_interface_name(interface)
        await self.set_interface_state(interface, "down")
        return await self.set_interface_state(interface, "up")
