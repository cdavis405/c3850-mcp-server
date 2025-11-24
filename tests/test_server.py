import asyncio
import unittest
from unittest.mock import AsyncMock, patch
from c3850_mcp.server import mcp

class TestC3850MCPServer(unittest.IsolatedAsyncioTestCase):
    async def test_get_interfaces_status(self):
        with patch("c3850_mcp.server.device") as mock_device:
            # Mock async method returning raw structure
            mock_device.get_interfaces_status = AsyncMock(return_value=[
                {"name": "GigabitEthernet1/0/1", "admin_status": "up", "oper_status": "up", "speed": 1000000000, "mac": "00:11:22:33:44:55"}
            ])
            result = await mcp.call_tool("get_interfaces_status", {})
            # result is (content_list, meta_dict)
            content = result[0]
            self.assertIn("GigabitEthernet1/0/1", content[0].text)
            self.assertIn("00:11:22:33:44:55", content[0].text)
            mock_device.get_interfaces_status.assert_called_once()

    async def test_get_vlan_brief(self):
        with patch("c3850_mcp.server.device") as mock_device:
            mock_device.get_vlan_brief = AsyncMock(return_value=[
                {"id": 10, "name": "User_VLAN", "status": "active", "ports": ["Gi1/0/1"]}
            ])
            result = await mcp.call_tool("get_vlan_brief", {})
            content = result[0]
            self.assertIn("User_VLAN", content[0].text)
            mock_device.get_vlan_brief.assert_called_once()

    async def test_set_interface_state(self):
        with patch("c3850_mcp.server.device") as mock_device:
            mock_device.set_interface_state = AsyncMock(return_value={})
            result = await mcp.call_tool("set_interface_state", {"interface": "GigabitEthernet1/0/1", "state": "up"})
            content = result[0]
            self.assertEqual(content[0].text, "{}")
            mock_device.set_interface_state.assert_called_once_with("GigabitEthernet1/0/1", "up")

    async def test_set_interface_vlan(self):
        with patch("c3850_mcp.server.device") as mock_device:
            mock_device.set_interface_vlan = AsyncMock(return_value={})
            result = await mcp.call_tool("set_interface_vlan", {"interface": "GigabitEthernet1/0/1", "vlan_id": 10})
            content = result[0]
            self.assertEqual(content[0].text, "{}")
            mock_device.set_interface_vlan.assert_called_once_with("GigabitEthernet1/0/1", 10)

    async def test_bounce_interface(self):
        with patch("c3850_mcp.server.device") as mock_device:
            mock_device.bounce_interface = AsyncMock(return_value={})
            result = await mcp.call_tool("bounce_interface", {"interface": "GigabitEthernet1/0/1"})
            content = result[0]
            self.assertEqual(content[0].text, "{}")
            mock_device.bounce_interface.assert_called_once_with("GigabitEthernet1/0/1")

if __name__ == "__main__":
    unittest.main()
