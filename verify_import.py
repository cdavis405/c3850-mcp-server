import sys
import os
sys.path.append(os.path.join(os.getcwd(), "src"))

try:
    from c3850_mcp.server import mcp
    print("Successfully imported mcp")
    print(f"MCP Name: {mcp.name}")
except Exception as e:
    print(f"Failed to import mcp: {e}")
    sys.exit(1)
