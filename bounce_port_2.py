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
    
    interface_name = "TenGigabitEthernet1/0/2"
    
    print(f"1. Shutting down {interface_name}...")
    await device.set_interface_state(interface_name, "down")
    print("   Shutdown command sent.")
    
    print("   Verifying shutdown state...")
    status = await device.get_interfaces_status(status_filter=interface_name)
    if status:
        print(f"   Admin Status: {status[0].get('admin_status')}")
    
    print(f"2. Bringing up {interface_name}...")
    await device.set_interface_state(interface_name, "up")
    print("   No Shutdown command sent.")
    
    print("   Verifying final state...")
    status = await device.get_interfaces_status(status_filter=interface_name)
    if status:
        print(f"   Admin Status: {status[0].get('admin_status')}")
        print(f"   Oper Status: {status[0].get('oper_status')}")
        
        if status[0].get('admin_status') == 'up':
            print("SUCCESS: Interface is administratively UP.")
        else:
            print("FAILURE: Interface is still administratively DOWN.")

if __name__ == "__main__":
    asyncio.run(main())
