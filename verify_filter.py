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
    
    print("--- Testing Filter: 'up' ---")
    up_interfaces = await device.get_interfaces_status(status_filter="up")
    print(f"Found {len(up_interfaces)} UP interfaces.")
    for iface in up_interfaces:
        if iface['oper_status'] != 'up':
            print(f"ERROR: Found non-UP interface: {iface['name']} ({iface['oper_status']})")
            
    print("\n--- Testing Filter: 'down' ---")
    down_interfaces = await device.get_interfaces_status(status_filter="down")
    print(f"Found {len(down_interfaces)} DOWN interfaces.")
    for iface in down_interfaces:
        if iface['oper_status'] != 'down':
            print(f"ERROR: Found non-DOWN interface: {iface['name']} ({iface['oper_status']})")

    print("\n--- Testing Filter: 'GigabitEthernet0/0' ---")
    specific_interfaces = await device.get_interfaces_status(status_filter="GigabitEthernet0/0")
    print(f"Found {len(specific_interfaces)} matching interfaces.")
    for iface in specific_interfaces:
        if "GigabitEthernet0/0" not in iface['name']:
             print(f"ERROR: Found non-matching interface: {iface['name']}")
        else:
            print(f"  - {iface['name']}")

if __name__ == "__main__":
    asyncio.run(main())
