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
    
    print(f"Fetching IETF configuration for {interface_name}...")
    
    try:
        # Fetch config
        config_data = await device._request("GET", f"/ietf-interfaces:interfaces/interface={encoded_name}")
        print("Config:")
        print(json.dumps(config_data, indent=2))
        
        # Fetch state
        state_data = await device._request("GET", f"/ietf-interfaces:interfaces-state/interface={encoded_name}")
        print("State:")
        print(json.dumps(state_data, indent=2))
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
