import asyncio
import sys
import os
from pathlib import Path
import json
from urllib.parse import quote

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
    encoded_name = quote(interface_name, safe='')
    
    print(f"Fetching Cisco Operational Data for {interface_name}...")
    
    try:
        # Fetch Cisco operational data
        # Path: /Cisco-IOS-XE-interfaces-oper:interfaces/interface={name}
        path = f"/Cisco-IOS-XE-interfaces-oper:interfaces/interface={encoded_name}"
        data = await device._request("GET", path)
        print("Cisco Oper Data:")
        print(json.dumps(data, indent=2))
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
