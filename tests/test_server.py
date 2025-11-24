import asyncio
import unittest
from unittest.mock import AsyncMock, patch
from c3850_mcp.server import call_tool

class TestC3850MCPServer(unittest.IsolatedAsyncioTestCase):
    async def test_get_interfaces_status(self):
        with patch("c3850_mcp.server.device") as mock_device:
            # Mock async method
            mock_device.get_interfaces_status = AsyncMock(return_value={"ietf-interfaces:interfaces-state": {}})
            result = await call_tool("get_interfaces_status", {})
            self.assertIn("ietf-interfaces", result[0].text)
            mock_device.get_interfaces_status.assert_called_once()

    async def test_get_vlan_brief(self):
        with patch("c3850_mcp.server.device") as mock_device:
            mock_device.get_vlan_brief = AsyncMock(return_value={"vlan-oper-data": {}})
            result = await call_tool("get_vlan_brief", {})
            self.assertIn("vlan-oper-data", result[0].text)
            mock_device.get_vlan_brief.assert_called_once()

    async def test_set_interface_state(self):
        with patch("c3850_mcp.server.device") as mock_device:
            mock_device.set_interface_state = AsyncMock(return_value={})
            result = await call_tool("set_interface_state", {"interface": "GigabitEthernet1/0/1", "state": "up"})
            self.assertEqual(result[0].text, "{}")
            mock_device.set_interface_state.assert_called_once_with("GigabitEthernet1/0/1", "up")

    async def test_set_interface_vlan(self):
        with patch("c3850_mcp.server.device") as mock_device:
            mock_device.set_interface_vlan = AsyncMock(return_value={})
            result = await call_tool("set_interface_vlan", {"interface": "GigabitEthernet1/0/1", "vlan_id": 10})
            self.assertEqual(result[0].text, "{}")
            mock_device.set_interface_vlan.assert_called_once_with("GigabitEthernet1/0/1", 10)

    async def test_bounce_interface(self):
        with patch("c3850_mcp.server.device") as mock_device:
            mock_device.bounce_interface = AsyncMock(return_value={})
            result = await call_tool("bounce_interface", {"interface": "GigabitEthernet1/0/1"})
            self.assertEqual(result[0].text, "{}")
            mock_device.bounce_interface.assert_called_once_with("GigabitEthernet1/0/1")

if __name__ == "__main__":
    unittest.main()
