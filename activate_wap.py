import sys
import os
import asyncio
from typing import List

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from c3850_mcp.device import C3850Device, DeviceConfig

async def main():
    # Load env vars
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    # Initialize device - will pick up env vars automatically
    device = C3850Device()
    
    print("Fetching interface status...")
    interfaces = await device.get_interfaces_status()
    
    wap_ports = []
    for iface in interfaces:
        desc = iface.get("description", "")
        if "WAP" in desc:
            wap_ports.append(iface)
            
    if not wap_ports:
        print("No ports found with 'WAP' in description.")
        return

    print(f"Found {len(wap_ports)} WAP ports:")
    for port in wap_ports:
        print(f"  - {port['name']}: {port['description']} (Status: {port['admin_status']})")
        
    print("\nActivating ports...")
    for port in wap_ports:
        name = port['name']
        print(f"Activating {name}...")
        try:
            await device.set_interface_state(name, "up")
            print(f"  Success: {name} is now up.")
        except Exception as e:
            print(f"  Failed to activate {name}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
