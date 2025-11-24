# Cisco 3850 MCP Server

## Bridging Legacy Enterprise Hardware with Next-Generation AI

This project represents a pioneering effort to breathe new life into proven enterprise network infrastructure by connecting legacy Cisco 3850 switches directly to modern Large Language Models through the Model Context Protocol (MCP). By creating an intelligent bridge between Cisco's battle-tested IOS XE platform and cutting-edge AI assistants, we're demonstrating that yesterday's enterprise hardware can become tomorrow's AI-managed infrastructure.

### The Vision

In an era where AI is transforming how we interact with technology, enterprise network equipment often remains locked behind CLI interfaces and proprietary management tools. This MCP server shatters that barrier, enabling natural language interaction with production-grade Cisco Catalyst 3850 switches—equipment that powers countless enterprise networks worldwide.

Rather than discarding perfectly functional hardware in favor of cloud-managed solutions, this project leverages the **RESTCONF** protocol (RFC 8040) and **YANG data models** to create a modern, token-efficient API layer that AI can understand and interact with seamlessly. The result is a system where network administrators can simply ask their AI assistant to "show me which ports are down" or "set all unused admin-down ports to have a NOT USED description"—and watch as the AI executes these tasks with precision.

## Overview

This MCP server transforms your Cisco 3850 switch into an AI-accessible network appliance. By utilizing **RESTCONF over HTTPS** and structured **YANG models**, the server exposes a carefully curated set of network operations to AI assistants while maintaining enterprise-grade security and reliability.

**Key Technical Achievements:**
- **Zero-dependency RESTCONF client** using Python's async `httpx` library
- **Token-optimized responses** that minimize LLM context pollution through client-side filtering
- **Structured YANG data consumption** directly from IOS XE, bypassing CLI parsing overhead
- **Secure credential management** via environment variables and `.env` files
- **Real-time network state awareness** through operational data models

## Features

This MCP server exposes a comprehensive suite of network management capabilities, organized into three strategic categories that enable full-spectrum network operations:

### 1. 🔍 State and Status Intelligence
Query real-time network state with precision and efficiency.
- **`get_interfaces_status`**: Retrieve comprehensive interface metrics including operational status, administrative state, speed, duplex mode, and VLAN assignments. Supports optional filtering by status (`up`/`down`) or interface name to reduce token consumption.
- **`get_vlan_brief`**: Obtain a consolidated view of all VLANs with port memberships and status—essential for rapid network segmentation audits.
- **`get_system_summary`**: Access critical system information including IOS XE version, uptime, hardware model, and serial numbers for compliance and inventory management.
- **`get_transceiver_stats`**: Deep-dive into optical transceiver diagnostics including transmit/receive power levels, temperature, and voltage—crucial for fiber infrastructure monitoring.

### 2. 🏥 Troubleshooting and Health Monitoring
Proactive diagnostics and health checks for maintaining network reliability.
- **`get_device_health`**: Real-time monitoring of CPU utilization, memory consumption, and environmental sensors (fans, power supplies, temperature)—enabling predictive maintenance.
- **`get_recent_logs`**: Stream the latest syslog entries directly from the device, allowing AI-assisted log analysis and anomaly detection.
- **`check_interface_errors`**: Automated scanning for interface errors including CRC failures, input/output drops, and collision counts—critical for identifying layer 1 and 2 issues.

### 3. ⚙️ Safe Configuration Management
Execute configuration changes with precision and safety.
- **`set_interface_state`**: Administratively enable (`no shutdown`) or disable (`shutdown`) interfaces with a simple command—perfect for authorized maintenance windows.
- **`set_interface_vlan`**: Dynamically assign interfaces to access VLANs, enabling rapid network reconfiguration and device onboarding.
- **`set_vlan_name`**: Update VLAN descriptions for improved network documentation and organization.
- **`bounce_interface`**: Automatically execute a shut/no-shut sequence to reset problematic connections—a common troubleshooting step now available through natural language.

## Why This Matters

### Sustainability Through Innovation
The tech industry's push toward cloud-managed solutions often creates unnecessary e-waste. The Cisco Catalyst 3850 platform represents **millions of dollars in deployed infrastructure** across enterprises worldwide—equipment that remains fully functional but is increasingly difficult to integrate with modern automation workflows. This project proves that with the right software layer, legacy hardware can participate in the AI revolution without requiring hardware replacement.

### Real-World Applications
- **Homelab Excellence**: Transform your home network into an AI-managed environment, gaining enterprise-level capabilities without enterprise-level complexity.
- **Small Business Empowerment**: Enable small IT teams to manage networks through natural language, reducing the learning curve and operational overhead.
- **Education and Research**: Provide students and researchers with hands-on experience in AI-assisted network management using production-grade equipment.
- **Proof of Concept**: Demonstrate to enterprise stakeholders that AI-assisted network management is achievable with existing infrastructure.

### Token Optimization Philosophy
Every tool in this server is designed with **token efficiency** in mind. Optional filtering parameters allow AI assistants to request only relevant data, reducing context window consumption and improving response times. For example, requesting `get_interfaces_status(status_filter="down")` returns only problematic interfaces rather than the entire switch inventory—a critical optimization when working with large network deployments.

## Prerequisites

- Python 3.10 or higher
- Network access to the Cisco 3850 switch (HTTPS/RESTCONF enabled)
- Valid credentials (username, password)
- **RESTCONF enabled on the device**:
  ```cisco
  ip http secure-server
  restconf
  ```

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/c3850-mcp-server.git
   cd c3850-mcp-server
   ```

2. **Install dependencies:**
   It is recommended to use a virtual environment.
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install .
   ```

## Configuration

### Secure Credential Management

This server follows security best practices by **never hardcoding credentials** in source code. All sensitive information is managed through environment variables, with support for `.env` files for local development convenience.

The server requires the following environment variables to establish a secure connection to your Cisco 3850 switch:

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `C3850_HOST` | IP address or hostname of the switch | - | ✅ Yes |
| `C3850_USERNAME` | RESTCONF-enabled username | - | ✅ Yes |
| `C3850_PASSWORD` | User password | - | ✅ Yes |
| `C3850_PORT` | HTTPS RESTCONF port | 443 | ❌ No |

### Setting Up Credentials

**Option 1: Environment Variables (Production)**
```bash
export C3850_HOST="192.168.1.10"
export C3850_USERNAME="admin"
export C3850_PASSWORD="YourSecurePassword"
```

**Option 2: .env File (Development)**
Create a `.env` file in the project root:
```env
C3850_HOST=192.168.1.10
C3850_USERNAME=admin
C3850_PASSWORD=YourSecurePassword
C3850_PORT=443
```

> **⚠️ Security Note**: The `.env` file is automatically excluded from version control via `.gitignore`. Never commit credentials to your repository.

## Usage

Run the MCP server using the following command:

```bash
export C3850_HOST="192.168.1.10"
export C3850_USERNAME="admin"
export C3850_PASSWORD="MySecurePassword"

python3 src/c3850_mcp/server.py
```

Once running, the server will communicate over stdio, allowing it to be integrated with any MCP-compliant client.

## Development

To run the test suite (which uses a mock device):

```bash
python3 -m unittest tests/test_server.py
```

## Example AI Interactions

Once integrated with an AI assistant (like Claude or ChatGPT with MCP support), you can interact with your network using natural language:

**User**: "Show me all the ports that are down on my switch"  
**AI**: *Calls `get_interfaces_status(status_filter="down")` and presents a formatted list*

**User**: "The WAP ports need to be shutdown for maintenance"  
**AI**: *Identifies interfaces with "WAP" in description and executes `set_interface_state` on each*

**User**: "Set all admin-down ports without descriptions to 'NOT USED'"  
**AI**: *Queries interfaces, filters by admin status and empty descriptions, then sets descriptions*

These interactions demonstrate how natural language can replace complex CLI navigation and scripting.

## Technical Architecture

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│             │  MCP    │              │ RESTCONF│   Cisco     │
│ AI Assistant│◄───────►│  MCP Server  │◄───────►│  3850 Switch│
│  (Claude)   │ stdio   │   (Python)   │ HTTPS  │  (IOS XE)   │
│             │         │              │         │             │
└─────────────┘         └──────────────┘         └─────────────┘
                              │
                              ▼
                        ┌──────────┐
                        │  YANG    │
                        │  Models  │
                        └──────────┘
```

The server acts as a translation layer, converting high-level MCP tool calls into precise RESTCONF API requests that conform to Cisco's YANG models.

## Future Enhancements

This project is actively evolving. Planned features include:

- **📊 Advanced Analytics**: Historical data collection and trend analysis for capacity planning
- **🔔 Event Streaming**: WebSocket-based real-time event notifications from NETCONF
- **🔐 Enhanced Security**: Certificate-based authentication and role-based access control (RBAC)
- **📈 Telemetry Integration**: Model-driven telemetry subscription for high-frequency metric collection
- **🌐 Multi-Device Support**: Fleet management capabilities for multiple switch deployments
- **🤖 Automated Remediation**: AI-driven automatic response to common network issues

## Contributing

Contributions are welcome! This project aims to demonstrate that legacy enterprise hardware deserves a place in the AI-managed future. Whether you're adding features, improving documentation, or extending support to other Cisco platforms (3650, 9300, etc.), your input helps advance the vision.

## License

This project is provided as-is for educational and experimental purposes. Please ensure compliance with your organization's network policies before deploying in production environments.

## Acknowledgments

Built on the shoulders of giants:
- **Model Context Protocol (MCP)** by Anthropic - for creating an elegant AI-tool interface standard
- **RESTCONF (RFC 8040)** - for providing a modern HTTP API to network devices  
- **YANG Data Models** - for structured, machine-readable network configuration
- **Cisco IOS XE** - for maintaining RESTCONF support in mature hardware platforms

---

*Transforming legacy infrastructure into AI-ready assets—one RESTCONF call at a time.* 🚀
