import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(str(Path.cwd() / "src"))

from c3850_mcp.device import C3850Device
from dotenv import load_dotenv

async def main():
    load_dotenv()
    print("Initializing device...")
    device = C3850Device()
    
    print("Getting interface status for '1/0/1'...")
    try:
        # Try to filter for 1/0/1
        status = await device.get_interfaces_status(status_filter="1/0/1")
        print(f"Found {len(status)} interfaces matching '1/0/1'")
        for interface in status:
            print(f"Interface: {interface['name']}")
            print(f"  Admin Status: {interface['admin_status']}")
            print(f"  Oper Status: {interface['oper_status']}")
            print(f"  Description: {interface['description']}")
            
        if not status:
            print("No interface found matching '1/0/1'. Listing first 10 interfaces to check naming convention...")
            all_status = await device.get_interfaces_status()
            for interface in all_status[:10]:
                 print(f"  {interface['name']}: {interface['oper_status']}")
                 
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
