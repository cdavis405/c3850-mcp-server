import sys
import os
import asyncio
from typing import List

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

# Load env vars
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from c3850_mcp.device import C3850Device

async def main():
    device = C3850Device()
    
    print("Fetching interface status...")
    # Get all interfaces (filter=None) because we need to check admin_status, 
    # and our filter logic currently filters by oper_status for 'down'.
    # Although usually admin down implies oper down, let's be safe and get all, then filter in python.
    interfaces = await device.get_interfaces_status()
    
    admin_down_ports = []
    for iface in interfaces:
        if iface.get('admin_status') == 'down':
            admin_down_ports.append(iface)
            
    print(f"Found {len(admin_down_ports)} ports that are ADMIN DOWN:")
    for port in admin_down_ports:
        print(f"  - {port['name']} ({port.get('description', 'No description')})")

if __name__ == "__main__":
    asyncio.run(main())
