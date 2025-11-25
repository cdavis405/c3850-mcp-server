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
    
    target_interface = "Te1/0/2"
    print(f"Getting interface status for '{target_interface}'...")
    
    import time
    start_time = time.time()
    
    try:
        # Try to filter for specific interface
        status = await device.get_interfaces_status(status_filter=target_interface)
        end_time = time.time()
        
        print(f"Time taken: {end_time - start_time:.4f} seconds")
        print(f"Found {len(status)} interfaces matching '{target_interface}'")
        
        for interface in status:
            print(f"Interface: {interface['name']}")
            print(f"  Admin Status: {interface['admin_status']}")
            print(f"  Oper Status: {interface['oper_status']}")
            print(f"  Description: {interface['description']}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
