import asyncio
import sys
import os
from pathlib import Path
import json

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
    print(f"Fetching NATIVE configuration for {interface_name}...")
    
    # We need to access the private _request method or use get_interface_details which uses native
    # get_interface_details uses: /Cisco-IOS-XE-native:native/interface/{if_type}={encoded_name}
    
    try:
        details = await device.get_interface_details(interface_name)
        print(json.dumps(details, indent=2))
        
        if "shutdown" in details:
            print("Status: SHUTDOWN is present in config.")
        else:
            print("Status: SHUTDOWN is NOT present in config.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
