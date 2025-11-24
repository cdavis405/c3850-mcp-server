import sys
import os
import asyncio
import argparse
from typing import List

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from c3850_mcp.device import C3850Device, DeviceConfig

async def main(search_term: str):
    # Load env vars
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    # Initialize device - will pick up env vars automatically
    device = C3850Device()
    
    print(f"Fetching interface status...")
    interfaces = await device.get_interfaces_status()
    
    matching_ports = []
    for iface in interfaces:
        desc = iface.get("description", "")
        # Case-insensitive search
        if search_term.lower() in desc.lower():
            matching_ports.append(iface)
            
    if not matching_ports:
        print(f"No ports found with '{search_term}' in description.")
        return

    print(f"Found {len(matching_ports)} port(s) matching '{search_term}':")
    for port in matching_ports:
        print(f"  - {port['name']}: {port['description']} (Status: {port['admin_status']})")
        
    print(f"\nShutting down ports...")
    for port in matching_ports:
        name = port['name']
        print(f"Shutting down {name}...")
        try:
            await device.set_interface_state(name, "down")
            print(f"  Success: {name} is now down.")
        except Exception as e:
            print(f"  Failed to shutdown {name}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Shutdown network ports by description search term.")
    parser.add_argument("search_term", type=str, help="Search term to find in interface descriptions (case-insensitive)")
    args = parser.parse_args()
    
    asyncio.run(main(args.search_term))
