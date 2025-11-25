import asyncio
import logging
import httpx
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP, Context
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

from c3850_mcp.device import C3850Device

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("c3850-mcp-server")

from contextlib import asynccontextmanager
from functools import wraps

def tool_error_handler(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except httpx.HTTPStatusError as e:
            # Handle 401/403/404 specifically for the LLM
            return f"⚠️ Network Error {e.response.status_code}: {e.response.text}"
        except httpx.ConnectTimeout:
            return "⚠️ Error: The Cisco 3850 is unreachable (Timeout)."
        except Exception as e:
            logger.error(f"Critical error in {func.__name__}: {e}")
            return f"❌ Internal Tool Error: {str(e)}"
    return wrapper

# Global client storage
http_client = None
device = None

@asynccontextmanager
async def server_lifespan(server: FastMCP):
    global http_client, device
    # Verify=False is usually needed for self-signed Cisco certs
    # Limits are key here - Cisco httpd creates a new process per request
    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    http_client = httpx.AsyncClient(verify=False, limits=limits)
    device = C3850Device(http_client=http_client)
    try:
        yield
    finally:
        if http_client:
            await http_client.aclose()

# Initialize with lifespan management
mcp = FastMCP("cisco-3850", dependencies=["httpx"], lifespan=server_lifespan)

@mcp.tool()
@tool_error_handler
async def get_interfaces_status(status_filter: Optional[str] = None) -> str:
    """Get the status of all interfaces (up/down, speed, duplex, vlan).
    
    Args:
        status_filter: Optional. 'up', 'down', or specific interface name.
    """
    result = await device.get_interfaces_status(status_filter)
    return str(result)

@mcp.tool()
@tool_error_handler
async def get_vlan_brief() -> str:
    """Get a brief summary of all VLANs."""
    result = await device.get_vlan_brief()
    return str(result)

@mcp.tool()
@tool_error_handler
async def get_system_summary() -> str:
    """Get system summary information (version, uptime, etc)."""
    result = await device.get_system_summary()
    return str(result)

@mcp.tool()
@tool_error_handler
async def get_transceiver_stats() -> str:
    """Get optical levels (dBm) for fiber interfaces. 
    USE THIS IF: User suspects physical layer issues, bad cables, or low light levels.
    """
    result = await device.get_transceiver_stats()
    return str(result)

@mcp.tool()
@tool_error_handler
async def get_device_health() -> str:
    """Get device health metrics (CPU, Memory, Environment)."""
    result = await device.get_device_health()
    return str(result)

@mcp.tool()
@tool_error_handler
async def get_recent_logs(count: int = 50, search_term: Optional[str] = None) -> str:
    """Get the most recent log messages.
    
    Args:
        count: Number of log lines to retrieve (default 50).
        search_term: Optional. Filter logs by this term (case-insensitive).
    """
    result = await device.get_recent_logs(count, search_term)
    return str(result)

@mcp.tool()
@tool_error_handler
async def check_interface_errors() -> str:
    """Check for interface errors (CRC, etc)."""
    result = await device.check_interface_errors()
    return str(result)

@mcp.tool()
@tool_error_handler
async def set_interface_state(interface: str, state: str) -> str:
    """Set an interface state to 'up' or 'down'.
    
    Args:
        interface: Interface name (e.g., GigabitEthernet1/0/1).
        state: Desired state ('up' or 'down').
    """
    result = await device.set_interface_state(interface, state)
    return str(result)

@mcp.tool()
@tool_error_handler
async def set_interface_vlan(interface: str, vlan_id: int) -> str:
    """Assign an interface to a specific VLAN (access mode).
    
    Args:
        interface: Interface name.
        vlan_id: VLAN ID.
    """
    result = await device.set_interface_vlan(interface, vlan_id)
    return str(result)

@mcp.tool()
@tool_error_handler
async def set_vlan_name(vlan_id: int, name: str) -> str:
    """Set the name of a VLAN.
    
    Args:
        vlan_id: VLAN ID.
        name: New name for the VLAN.
    """
    result = await device.set_vlan_name(vlan_id, name)
    return str(result)

@mcp.tool()
@tool_error_handler
async def bounce_interface(interface: str) -> str:
    """Bounce (shutdown then no shutdown) an interface.
    
    Args:
        interface: Interface name.
    """
    result = await device.bounce_interface(interface)
    return str(result)

if __name__ == "__main__":
    mcp.run()
