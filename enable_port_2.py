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
    
    print(f"Checking initial status of {interface_name}...")
    initial_status = await device.get_interfaces_status(status_filter=interface_name)
    if initial_status:
        print(f"Current Admin Status: {initial_status[0].get('admin_status')}")
    else:
        print("Could not fetch initial status.")

    print(f"Enabling {interface_name}...")
    try:
        result = await device.set_interface_state(interface_name, "up")
        print("Command sent successfully.")
        
        # Verify
        print("Verifying new status...")
        # Small delay to allow device to process? RESTCONF is usually synchronous for config, 
        # but oper-status might take a moment. Admin status should be immediate.
        final_status = await device.get_interfaces_status(status_filter=interface_name)
        
        if final_status:
            admin_status = final_status[0].get('admin_status')
            oper_status = final_status[0].get('oper_status')
            print(f"New Admin Status: {admin_status}")
            print(f"New Oper Status: {oper_status}")
            
            if admin_status == "up":
                print("SUCCESS: Interface is administratively UP.")
            else:
                print("FAILURE: Interface is still administratively DOWN.")
        else:
            print("Error: Could not verify status.")
            
    except Exception as e:
        print(f"Error enabling interface: {e}")

if __name__ == "__main__":
    asyncio.run(main())
