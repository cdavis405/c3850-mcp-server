import sys
import os
import asyncio
from urllib.parse import quote

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

# Load env vars
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from c3850_mcp.device import C3850Device

async def set_interface_description(device: C3850Device, interface: str, description: str):
    """Set description for an interface."""
    from urllib.parse import quote
    
    payload = {
        "ietf-interfaces:interface": {
            "name": interface,
            "description": description
        }
    }
    
    encoded_interface = quote(interface, safe='')
    return await device._request("PATCH", f"/ietf-interfaces:interfaces/interface={encoded_interface}", json=payload)

async def main():
    device = C3850Device()
    
    print("Fetching interface status...")
    interfaces = await device.get_interfaces_status()
    
    # Find admin down ports with empty or no description
    ports_to_update = []
    for iface in interfaces:
        if iface.get('admin_status') == 'down':
            desc = iface.get('description', '').strip()
            if not desc or desc == '()':
                ports_to_update.append(iface['name'])
    
    if not ports_to_update:
        print("No ports found that need description updates.")
        return
    
    print(f"\nFound {len(ports_to_update)} admin down ports with no description:")
    for port in ports_to_update:
        print(f"  - {port}")
    
    print(f"\nSetting description to 'NOT USED' for {len(ports_to_update)} ports...")
    
    for port in ports_to_update:
        try:
            await set_interface_description(device, port, "NOT USED")
            print(f"  ✓ {port} - Description set to 'NOT USED'")
        except Exception as e:
            print(f"  ✗ {port} - Failed: {e}")
    
    print("\nDone!")

if __name__ == "__main__":
    asyncio.run(main())
