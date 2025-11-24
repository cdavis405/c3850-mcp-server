import asyncio
import unittest
from unittest.mock import MagicMock, patch
from c3850_mcp.server import call_tool

class TestC3850MCPServer(unittest.IsolatedAsyncioTestCase):
    async def test_get_interfaces_status(self):
        with patch("c3850_mcp.server.device") as mock_device:
            mock_device.get_interfaces_status.return_value = [{"interface": "Gi1/0/1", "status": "connected"}]
            result = await call_tool("get_interfaces_status", {})
            self.assertIn("Gi1/0/1", result[0].text)
            mock_device.get_interfaces_status.assert_called_once()

    async def test_get_vlan_brief(self):
        with patch("c3850_mcp.server.device") as mock_device:
            mock_device.get_vlan_brief.return_value = "VLAN Name Status Ports"
            result = await call_tool("get_vlan_brief", {})
            self.assertEqual(result[0].text, "VLAN Name Status Ports")
            mock_device.get_vlan_brief.assert_called_once()

    async def test_set_interface_state(self):
        with patch("c3850_mcp.server.device") as mock_device:
            mock_device.set_interface_state.return_value = "Interface Gi1/0/1 changed state to up"
            result = await call_tool("set_interface_state", {"interface": "Gi1/0/1", "state": "up"})
            self.assertIn("changed state to up", result[0].text)
            mock_device.set_interface_state.assert_called_once_with("Gi1/0/1", "up")

    async def test_set_interface_vlan(self):
        with patch("c3850_mcp.server.device") as mock_device:
            mock_device.set_interface_vlan.return_value = "Configured"
            result = await call_tool("set_interface_vlan", {"interface": "Gi1/0/1", "vlan_id": 10})
            self.assertEqual(result[0].text, "Configured")
            mock_device.set_interface_vlan.assert_called_once_with("Gi1/0/1", 10)

    async def test_bounce_interface(self):
        with patch("c3850_mcp.server.device") as mock_device:
            mock_device.bounce_interface.return_value = "Bounced"
            result = await call_tool("bounce_interface", {"interface": "Gi1/0/1"})
            self.assertEqual(result[0].text, "Bounced")
            mock_device.bounce_interface.assert_called_once_with("Gi1/0/1")

if __name__ == "__main__":
    unittest.main()
