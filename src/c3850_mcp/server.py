import asyncio
import logging
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

from c3850_mcp.device import C3850Device

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("c3850-mcp-server")

app = Server("c3850-mcp-server")
device = C3850Device()

@app.list_tools()
async def list_tools() -> List[Tool]:
    return [
        Tool(
            name="get_interfaces_status",
            description="Get the status of all interfaces (up/down, speed, duplex, vlan).",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="get_vlan_brief",
            description="Get a brief summary of all VLANs.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="get_system_summary",
            description="Get system summary information (version, uptime, etc).",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="get_transceiver_stats",
            description="Get detailed transceiver statistics.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="get_device_health",
            description="Get device health metrics (CPU, Memory, Environment).",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="get_recent_logs",
            description="Get the most recent log messages.",
            inputSchema={
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "Number of log lines to retrieve (default 50).",
                        "default": 50
                    }
                },
            },
        ),
        Tool(
            name="check_interface_errors",
            description="Check for interface errors (CRC, etc).",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="set_interface_state",
            description="Set an interface state to 'up' or 'down'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "interface": {
                        "type": "string",
                        "description": "Interface name (e.g., GigabitEthernet1/0/1)."
                    },
                    "state": {
                        "type": "string",
                        "enum": ["up", "down"],
                        "description": "Desired state."
                    }
                },
                "required": ["interface", "state"]
            },
        ),
        Tool(
            name="set_interface_vlan",
            description="Assign an interface to a specific VLAN (access mode).",
            inputSchema={
                "type": "object",
                "properties": {
                    "interface": {
                        "type": "string",
                        "description": "Interface name."
                    },
                    "vlan_id": {
                        "type": "integer",
                        "description": "VLAN ID."
                    }
                },
                "required": ["interface", "vlan_id"]
            },
        ),
        Tool(
            name="set_vlan_name",
            description="Set the name of a VLAN.",
            inputSchema={
                "type": "object",
                "properties": {
                    "vlan_id": {
                        "type": "integer",
                        "description": "VLAN ID."
                    },
                    "name": {
                        "type": "string",
                        "description": "New name for the VLAN."
                    }
                },
                "required": ["vlan_id", "name"]
            },
        ),
        Tool(
            name="bounce_interface",
            description="Bounce (shutdown then no shutdown) an interface.",
            inputSchema={
                "type": "object",
                "properties": {
                    "interface": {
                        "type": "string",
                        "description": "Interface name."
                    }
                },
                "required": ["interface"]
            },
        ),
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> List[TextContent | ImageContent | EmbeddedResource]:
    try:
        if name == "get_interfaces_status":
            result = await device.get_interfaces_status()
            return [TextContent(type="text", text=str(result))]
        
        elif name == "get_vlan_brief":
            result = await device.get_vlan_brief()
            return [TextContent(type="text", text=str(result))]
        
        elif name == "get_system_summary":
            result = await device.get_system_summary()
            return [TextContent(type="text", text=str(result))]
        
        elif name == "get_transceiver_stats":
            result = await device.get_transceiver_stats()
            return [TextContent(type="text", text=str(result))]
        
        elif name == "get_device_health":
            result = await device.get_device_health()
            return [TextContent(type="text", text=str(result))]
        
        elif name == "get_recent_logs":
            # count = arguments.get("count", 50) # RESTCONF log retrieval might not support count directly in the same way
            result = await device.get_recent_logs()
            return [TextContent(type="text", text=str(result))]
        
        elif name == "check_interface_errors":
            result = await device.check_interface_errors()
            return [TextContent(type="text", text=str(result))]
        
        elif name == "set_interface_state":
            interface = arguments["interface"]
            state = arguments["state"]
            result = await device.set_interface_state(interface, state)
            return [TextContent(type="text", text=str(result))]
        
        elif name == "set_interface_vlan":
            interface = arguments["interface"]
            vlan_id = arguments["vlan_id"]
            result = await device.set_interface_vlan(interface, vlan_id)
            return [TextContent(type="text", text=str(result))]
        
        elif name == "set_vlan_name":
            vlan_id = arguments["vlan_id"]
            name = arguments["name"]
            result = await device.set_vlan_name(vlan_id, name)
            return [TextContent(type="text", text=str(result))]
        
        elif name == "bounce_interface":
            interface = arguments["interface"]
            result = await device.bounce_interface(interface)
            return [TextContent(type="text", text=str(result))]
        
        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
