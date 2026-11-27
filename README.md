# ucm-mcp

**Ask an agent “is SEP… registered, what’s its IP, and who’s logged in?” — it hits AXL + RIS in one tool call.**

```bash
uv sync
cp .env.example .env   # set UCM_HOST / UCM_USERNAME / UCM_PASSWORD
uv run ucm-mcp
```

Then ask Cursor: *phone status for SEPF8A5C59E0F1C*.

| Capability | Tools |
|---|---|
| Full AXL (1,000+ methods) | `axl_list_operations`, `axl_describe_operation`, `axl_call`, `axl_sql_query`, `axl_sql_update` |
| Real-time registration | `ris_select_devices`, `phone_status` |
| Control Center | `service_products`, `service_list`, `service_status`, `service_control`, `cluster_service_status` |
| Perfmon / logs / CDR | `perfmon_sample`, `logs_*`, `cdr_*` |
| Phone web + XSI | `phone_details`, `phone_inventory`, `phone_press`, `phone_execute`, `phone_reset_itl` |

## Quick Start

```bash
git clone https://github.com/levensailor/ucm-mcp.git
cd ucm-mcp
uv sync
cp .env.example .env
```

Edit `.env`:

```
UCM_HOST=10.10.20.1
UCM_USERNAME=axlaccess
UCM_PASSWORD=your-password
UCM_VERSION=15.0
```

Run:

```bash
uv run ucm-mcp
```

### Cursor MCP config

Add to your Cursor `mcp.json`:

```json
{
  "mcpServers": {
    "ucm": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/ucm-mcp", "ucm-mcp"],
      "env": {
        "UCM_HOST": "10.10.20.1",
        "UCM_USERNAME": "axlaccess",
        "UCM_PASSWORD": "your-password",
        "UCM_VERSION": "15.0"
      }
    }
  }
}
```

## Safety gates

| Flag | Default | Effect |
|---|---|---|
| `UCM_ALLOW_WRITES` | `false` | Enables AXL add/update/delete/reset/do and `axl_sql_update` |
| `UCM_ALLOW_SERVICE_CONTROL` | `false` | Enables `service_control` (start/stop/restart/activate/deactivate) |
| `UCM_ALLOW_PHONE_EXECUTE` | `false` | Enables phone CGI Execute / ITL macros |

Cisco Tomcat is never restarted over SSH. Control Center cannot restart Tomcat; the tool returns that fact.

## CUCM roles

Create an Application User with:

- **Standard AXL API Access**
- A Serviceability role that can read RIS and Control Center
- For phone Execute: phone **Web Access** enabled and an associated end user with `PHONE_USERNAME` / `PHONE_PASSWORD`

Enable **Cisco AXL Web Service** under Serviceability → Service Activation.

## Deployment

Stdio is the default (Cursor). For Streamable HTTP:

```
UCM_TRANSPORT=http
UCM_HTTP_HOST=127.0.0.1
UCM_HTTP_PORT=8000
```

No CI build artifacts or public URLs are required beyond this repository. Push to `main` runs pytest via GitHub Actions.

## Author

[![Jeff Levensailor](https://img.shields.io/badge/author-Jeff%20Levensailor-0A66C2?style=for-the-badge&logo=linkedin)](https://www.linkedin.com/in/jefflevensailor/)

MIT-licensed MCP server wrapping [ciscoaxl](https://github.com/levensailor/ciscoaxl) plus reimplemented RIS, Control Center, Perfmon, Log Collection, CDR, phone web, and XSI clients.
