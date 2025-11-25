#!/usr/bin/env python3
import sys
import os

# Shim logging
with open("/tmp/shim.log", "a") as f:
    f.write(f"Starting with {sys.executable}\n")
    f.write(f"Args: {sys.argv}\n")
    f.write(f"CWD: {os.getcwd()}\n")

# Force usage of venv python if available
from pathlib import Path

# Force usage of venv python if available
# This script is in src/c3850_mcp/server.py, so project root is 3 levels up
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"

if sys.executable != str(VENV_PYTHON) and VENV_PYTHON.exists():
    with open("/tmp/shim.log", "a") as f:
        f.write(f"Re-executing with {VENV_PYTHON}\n")
    # Re-execute with the correct interpreter
    try:
        os.execv(str(VENV_PYTHON), [str(VENV_PYTHON)] + sys.argv)
    except Exception as e:
        with open("/tmp/shim.log", "a") as f:
            f.write(f"Execv failed: {e}\n")


import asyncio
import logging
import httpx
from dotenv import load_dotenv
from typing import Any, Dict, List, Optional

# Load environment variables
load_dotenv()

from mcp.server.fastmcp import FastMCP, Context
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

from c3850_mcp.device import C3850Device

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    filename="/tmp/mcp_server_prod.log",
    filemode="a",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
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
        except httpx.RequestError as e:
            # Handle connection timeouts, refused connections, etc.
            return f"⚠️ Device Communication Error: {str(e)}"
        except Exception as e:
            logger.error(f"Critical error in {func.__name__}: {e}")
            return f"❌ Internal Tool Error: {str(e)}"
            return f"❌ Internal Tool Error: {str(e)}"
    return wrapper

def format_blast_radius_report(impact: Dict[str, Any]) -> str:
    """Format the blast radius analysis report."""
    if impact['risk_level'] == "ZERO":
        return f"ℹ️ ANALYSIS: {impact.get('interface', 'Target')} is already in a safe state (e.g., down). No impact. Call with confirm=True to proceed."
    
    warnings = "\n".join([f"- {w}" for w in impact['warnings']])
    return (
        f"⛔ STOP! BLAST RADIUS ANALYSIS for {impact.get('interface', 'Target')}:\n"
        f"Risk Level: {impact['risk_level']}\n"
        f"Warnings:\n{warnings}\n\n"
        f"ACTION REQUIRED: Explain these risks to the user. "
        f"Do not proceed until the user explicitly approves 'confirm=True'."
    )

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
async def get_capabilities() -> str:
    """Get the capabilities of this MCP server and the connected device.
    
    Returns:
        A summary of supported features, tools, and device information.
    """
    capabilities = device.get_capabilities()
    return str(capabilities)

@mcp.tool()
@tool_error_handler
async def get_interfaces_status(status_filter: Optional[str] = None) -> str:
    """Get the status of all interfaces (up/down, speed, duplex, vlan).
    
    Args:
        status_filter: Optional. 'up', 'down', 'connected', 'not connected', or specific interface name.
                       Use 'connected' to ignore unused ports.
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
async def set_interface_state(interface: str, state: str, confirm: bool = False) -> str:
    """Set an interface state to 'up' or 'down'.
    
    Args:
        interface: Interface name (e.g., GigabitEthernet1/0/1).
        state: Desired state ('up' or 'down').
        confirm: Set to True to execute the change after reviewing the blast radius.
    """
    interface = device.normalize_interface_name(interface)
    impact = await device.analyze_interface_impact(interface)
    
    if not confirm:
        return format_blast_radius_report(impact)

    result = await device.set_interface_state(interface, state)
    return str(result)

@mcp.tool()
@tool_error_handler
async def set_interface_vlan(interface: str, vlan_id: int, confirm: bool = False) -> str:
    """Assign an interface to a specific VLAN (access mode).
    
    Args:
        interface: Interface name.
        vlan_id: VLAN ID.
        confirm: Set to True to execute.
    """
    interface = device.normalize_interface_name(interface)
    impact = await device.analyze_interface_impact(interface)
    
    if not confirm:
        return format_blast_radius_report(impact)

    result = await device.set_interface_vlan(interface, vlan_id)
    return str(result)

@mcp.tool()
@tool_error_handler
async def set_vlan_name(vlan_id: int, name: str, confirm: bool = False) -> str:
    """Set the name of a VLAN.
    
    Args:
        vlan_id: VLAN ID.
        name: New name for the VLAN.
        confirm: Set to True to execute.
    """
    impact = await device.analyze_vlan_impact(vlan_id)
    
    if not confirm:
        return format_blast_radius_report(impact)

    result = await device.set_vlan_name(vlan_id, name)
    return str(result)

@mcp.tool()
@tool_error_handler
async def bounce_interface(interface: str, confirm: bool = False) -> str:
    """Bounce (shutdown then no shutdown) an interface.
    
    Args:
        interface: Interface name.
        confirm: Set to True to execute.
    """
    interface = device.normalize_interface_name(interface)
    impact = await device.analyze_interface_impact(interface)
    
    if not confirm:
        return format_blast_radius_report(impact)

    result = await device.bounce_interface(interface)
    return str(result)

if __name__ == "__main__":
    mcp.run()
