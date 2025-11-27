import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(str(Path.cwd() / "src"))

# Load env vars
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from c3850_mcp.device import C3850Device

async def main():
    print("Initializing device...")
    device = C3850Device()
    
    target_filter = "2"
    print(f"Getting interface status for filter '{target_filter}'...")
    
    try:
        # Fetch interfaces with "2" in the name
        status = await device.get_interfaces_status(status_filter=target_filter)
        
        print(f"Found {len(status)} interfaces matching '{target_filter}'")
        
        found_port_2 = False
        for interface in status:
            print(f"Interface: {interface['name']}")
            print(f"  Admin Status: {interface['admin_status']}")
            print(f"  Oper Status: {interface['oper_status']}")
            print(f"  Description: {interface['description']}")
            print("-" * 20)
            
            # Check if this is likely "Port 2"
            if interface['name'].endswith("/2") or interface['name'].endswith("Ethernet2"):
                found_port_2 = True
        
        if not found_port_2:
            print("WARNING: Did not find an interface that clearly looks like 'Port 2' (ending in /2).")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
