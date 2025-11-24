# Cisco 3850 MCP Server

A Model Context Protocol (MCP) server designed specifically for managing and monitoring Cisco 3850 (WS-C3850-24XU) switches. This server provides a bridge between LLMs and your network infrastructure, allowing for natural language interaction with your network devices.

## Overview

This project implements an MCP server that connects to a Cisco 3850 switch via **RESTCONF** using `httpx`. It exposes a set of tools that allow an AI assistant to retrieve device status, check health metrics, and perform basic configuration tasks. The tools are optimized to use minimal tokens and context by leveraging structured data from YANG models.

## Features

The server supports three main categories of operations:

### 1. State and Status
Retrieve real-time information about the device's current state.
- **`get_interfaces_status`**: Get the status (up/down, speed, duplex, VLAN) of all interfaces.
- **`get_vlan_brief`**: View a summary of all VLANs and their assigned ports.
- **`get_system_summary`**: Access high-level system info like version, uptime, and serial numbers.
- **`get_transceiver_stats`**: detailed optical transceiver statistics.

### 2. Troubleshooting and Health
Monitor the health of the switch and diagnose issues.
- **`get_device_health`**: Check CPU utilization, memory usage, and environmental status (fans, power supplies).
- **`get_recent_logs`**: Retrieve the most recent syslog messages to identify errors or events.
- **`check_interface_errors`**: Scan for interface errors such as CRC errors, input/output errors, and collisions.

### 3. Basic Configuration
Perform essential configuration changes safely.
- **`set_interface_state`**: Administratively enable (`no shutdown`) or disable (`shutdown`) an interface.
- **`set_interface_vlan`**: Assign an interface to a specific access VLAN.
- **`set_vlan_name`**: Rename a VLAN for better organization.
- **`bounce_interface`**: Automatically shut and then no-shut an interface to reset a connection.

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

The server requires the following environment variables to connect to the switch:

| Variable | Description | Default |
|----------|-------------|---------|
| `C3850_HOST` | IP address or hostname of the switch | |
| `C3850_USERNAME` | Username | |
| `C3850_PASSWORD` | Password | |
| `C3850_PORT` | RESTCONF Port | 443 |

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
