# Sharing Your MCP Server

Make your MCP server accessible to others by exposing it through a secure tunnel and registering it with Arcade. This allows remote users and services to interact with your tools without deploying to a cloud platform.

## Overview

By default, your MCP server runs locally on `localhost:8000`. To share it:
1. Run your server with HTTP transport
2. Create a secure tunnel to expose it publicly
3. Register your server in Arcade
4. Share the tools with others

## Step 1: Run Your Server

First, start your MCP server with HTTP transport:

```bash
# Navigate to your server directory
cd my_server

# Run with HTTP transport (default)
uv run server.py
uv run server.py http
```

Your server will start on `http://localhost:8000`. Keep this terminal running.

## Step 2: Create a Secure Tunnel

Open a **separate terminal** and create a tunnel using one of these options:

### Option A: ngrok (Recommended for Getting Started)

[ngrok](https://ngrok.com) is easy to set up and works across all platforms.

1. **Install ngrok:**
   ```bash
   # macOS
   brew install ngrok

   # Or download from https://ngrok.com/download
   ```

2. **Create a tunnel:**
   ```bash
   ngrok http 8000
   ```

3. **Copy your URL:**
   Look for the "Forwarding" line in the ngrok output:
   ```
   Forwarding  https://abc123.ngrok-free.app -> http://localhost:8000
   ```

   Copy the `https://abc123.ngrok-free.app` URL - this is your public URL.

**Pros:**
- Quick setup, no account required for basic use
- Automatic HTTPS
- Web dashboard to inspect requests

**Cons:**
- Free tier URLs change on each restart
- May show interstitial page for free tier

### Option B: Cloudflare Tunnel

[Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/) provides persistent URLs and advanced features.

1. **Install cloudflared:**
   ```bash
   # macOS
   brew install cloudflare/cloudflare/cloudflared

   # Or download from https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/
   ```

2. **Create a tunnel:**
   ```bash
   cloudflared tunnel --url http://localhost:8000
   ```

3. **Copy your URL:**
   Look for the "Your quick Tunnel has been created" message with your URL.

**Pros:**
- Free tier includes persistent URLs (with setup)
- Built-in DDoS protection
- Access control features

**Cons:**
- Requires Cloudflare account for persistent URLs
- More complex setup for advanced features

### Option C: Tailscale Funnel

[Tailscale Funnel](https://tailscale.com/kb/1223/tailscale-funnel) is ideal for sharing within a team or organization.

1. **Install Tailscale:**
   ```bash
   # macOS
   brew install tailscale

   # Or download from https://tailscale.com/download
   ```

2. **Authenticate:**
   ```bash
   tailscale up
   ```

3. **Create a funnel:**
   ```bash
   tailscale funnel 8000
   ```

4. **Get your URL:**
   Tailscale will display your funnel URL (e.g., `https://my-machine.tail-scale.ts.net`)

**Pros:**
- Persistent URLs tied to your machine
- Private by default (only shared with specified users)
- No bandwidth limits

**Cons:**
- Requires Tailscale account
- Best for team/organization use cases

## Step 3: Register Your MCP Server in Arcade

Once you have a public URL, register your MCP server in the Arcade dashboard to make it accessible through the Arcade API.

### Register Your Server

1. **Navigate to the MCP Servers page** in your [Arcade dashboard](https://api.arcade.dev/dashboard/servers)

2. **Click "Add Server"**

3. **Fill in the registration form:**
   - **ID**: Choose a unique identifier (e.g., `my-mcp-server`)
   - **Server Type**: Select "HTTP/SSE"
   - **URL**: Enter your public tunnel URL from Step 2 with `/mcp` appended
     - Example: `https://abc123.ngrok-free.app/mcp`
     - Example: `https://my-tunnel.trycloudflare.com/mcp`
     - Example: `https://my-machine.tail-scale.ts.net/mcp`
   - **Secret**: Enter a secret for your server (or use `dev` for testing)
   - **Timeout**: Configure request timeout (default: 30s)
   - **Retry**: Configure retry attempts (default: 3)

4. **Click "Create"**

### Configuration Example

```yaml
ID: my-mcp-server
Server Type: HTTP/SSE
URL: https://abc123.ngrok-free.app
Secret: my-secure-secret-123
Timeout: 30s
Retry: 3
```

## Step 4: Test Your MCP Server

Verify that your server is accessible and working correctly.

### Using the Arcade Playground

1. **Go to the [Arcade Playground](https://api.arcade.dev/dashboard/playground/chat)**

2. **Select your MCP server** from the dropdown

3. **Choose a tool** from your server

4. **Execute the tool** with test parameters

5. **Verify the response:**
   - Check that the response is correct
   - View request logs in your local server terminal
   - Inspect the tunnel dashboard for request details
