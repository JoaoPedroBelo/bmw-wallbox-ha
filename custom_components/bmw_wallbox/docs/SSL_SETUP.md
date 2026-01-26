# SSL Certificate Setup Guide

BMW and Mini wallboxes **require valid SSL certificates** and actively validate them. Self-signed certificates or using IP addresses instead of hostnames will not work.

This guide explains how to set up valid SSL certificates using Cloudflare DNS + Let's Encrypt, allowing the wallbox to connect locally while using a trusted certificate.

## Why This Is Needed

BMW/Mini wallboxes have a strict SSL requirement:
- SSL certificates are issued for **domain names (hostnames)**, not IP addresses
- The wallbox validates that the certificate matches the URL hostname
- Self-signed certificates are rejected
- Using an IP address in the OCPP URL causes certificate validation to fail

## Solution: Cloudflare DNS + Let's Encrypt

Use Cloudflare for DNS management and Let's Encrypt for valid certificates. The wallbox connects **locally** - no traffic goes through Cloudflare's cloud.

### How It Works

1. Wallbox looks up `local.yourdomain.com` → Gets your local IP (e.g., `192.168.1.100`)
2. Wallbox connects **locally** to Home Assistant
3. Valid certificate matches the domain name
4. Certificate validation passes ✅
5. No external traffic - purely local connection

---

## Step-by-Step Setup

### 1. Set Up Domain in Cloudflare

1. Add your domain to Cloudflare (or [register a new one](https://www.cloudflare.com/products/registrar/))
2. Create an **A record**:

| Setting | Value |
|---------|-------|
| **Type** | A |
| **Name** | `local` (or `homeassistant`, `ha`, etc.) |
| **IPv4 address** | Your Home Assistant local IP (e.g., `192.168.1.100`) |
| **Proxy status** | **DNS only** (gray cloud) ⚠️ **IMPORTANT** |
| **TTL** | Auto |

This creates: `local.yourdomain.com` → `192.168.1.100`

> ⚠️ **Important:** The proxy status MUST be "DNS only" (gray cloud icon), not "Proxied" (orange cloud). The orange cloud would route traffic through Cloudflare, which breaks the local connection.

### 2. Get Cloudflare API Token

1. In Cloudflare dashboard → **My Profile** → **API Tokens**
2. Click **Create Token**
3. Use template: **Edit zone DNS**
4. Zone Resources: Include → Specific zone → Your domain
5. Click **Continue to summary** → **Create Token**
6. Copy the token (you'll need it for the next step)

### 3. Install Let's Encrypt Add-on in Home Assistant

1. Go to **Settings** → **Add-ons** → **Add-on Store**
2. Search for **Let's Encrypt** and click **Install**
3. Go to the **Configuration** tab
4. Configure with your details:

```yaml
email: your-email@example.com
domains:
  - local.yourdomain.com
certfile: fullchain.pem
keyfile: privkey.pem
challenge: dns
dns:
  provider: dns-cloudflare
  cloudflare_api_token: your-cloudflare-api-token-here
```

5. Click **Save**
6. Go to the **Info** tab and click **Start**
7. Check the **Log** tab for: `Congratulations! Your certificate has been saved`

Certificates are created at:
- `/ssl/fullchain.pem`
- `/ssl/privkey.pem`

### 4. Configure BMW Wallbox Integration

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for **BMW Wallbox**
3. Configure:

| Setting | Value |
|---------|-------|
| **WebSocket Port** | `9000` |
| **SSL Certificate Path** | `/ssl/fullchain.pem` |
| **SSL Key Path** | `/ssl/privkey.pem` |
| **Charge Point ID** | Your wallbox ID (e.g., `DE*BMW*XXXXXXXXXXXXXXXXX`) |
| **Maximum Current** | `32` |

### 5. Configure Wallbox in WBInstallation App

Open the WBInstallation app and configure:

| Setting | Value |
|---------|-------|
| **OCPP URL** | `wss://local.yourdomain.com:9000` |
| **Charge Station ID** | `DE*BMW*XXXXXXXXXXXXXXXXX` |
| **OCPP Version** | `2.0.1` |

> **Important:** The Charge Station ID format includes asterisks: `DE*BMW*XXXXXXXXXXXXXXXXX`. Copy it exactly as shown in the app.

---

## Verification

After configuration:

1. The wallbox should connect within a few minutes
2. Check Home Assistant logs for connection messages
3. The "Connected" binary sensor should turn ON
4. All sensors should start populating with data

### Enable Debug Logging (if needed)

Add to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.bmw_wallbox: debug
    ocpp: debug
    websockets: debug
```

---

## Troubleshooting

### Wallbox not connecting

1. **Verify DNS resolution:** On a device in your network, ping `local.yourdomain.com` - it should resolve to your Home Assistant IP
2. **Check certificate validity:** Ensure Let's Encrypt add-on ran successfully
3. **Verify port is open:** Home Assistant must be reachable on port 9000
4. **Check Charge Point ID:** Must match exactly between HA config and wallbox config (including asterisks)

### Certificate renewal

Let's Encrypt certificates expire every 90 days. The add-on handles renewal automatically, but ensure:
- The add-on is set to auto-start
- Home Assistant can reach the internet for renewals

### Cloudflare proxy status

If you accidentally enabled the proxy (orange cloud):
1. Go to Cloudflare DNS settings
2. Click the orange cloud icon to toggle it to gray (DNS only)
3. Wait a few minutes for DNS to propagate
4. Restart the wallbox or wait for it to reconnect

---

## Compatible Hardware

This SSL setup works with:

- **BMW Wallbox** (EIAW-E22KTSE6B04)
- **Mini Wallbox Plus** (EIAW-E22KTSE6B15)
- Other Delta Electronics OCPP 2.0.1 wallboxes

These are essentially the same hardware with different branding.

---

## Related Resources

- [Cloudflare DNS Documentation](https://developers.cloudflare.com/dns/)
- [Let's Encrypt Add-on Documentation](https://github.com/home-assistant/addons/tree/master/letsencrypt)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
