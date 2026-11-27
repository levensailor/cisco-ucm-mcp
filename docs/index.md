# Cisco UCM MCP

MCP server that answers Cisco UCM questions about phone registration, AXL data, and service status.

ucm-mcp gives an agent one tool call for Cisco Unified Communications Manager. It can ask whether a phone is registered, which IP it has, and who is logged in, using AXL and the real-time RIS port. The same server covers the AXL method list, Control Center, Perfmon, log collection, CDR, and the phone web and XSI interfaces.

AXL writes, service start and stop, and phone execute stay off until the matching flag is set. The server will not restart Cisco Tomcat. Run it with uv so Cursor can launch it over stdio, or set the transport to HTTP. It needs an application user with AXL access and a serviceability role that can read RIS.

## Source

Repository: [https://github.com/levensailor/ucm-mcp](https://github.com/levensailor/ucm-mcp)

## Topics

- AXL
- Cisco UCM
- MCP
- Python
