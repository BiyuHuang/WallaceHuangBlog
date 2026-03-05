---
title: "How to Use Cloudflare WARP as a Proxy"
date: 2024-10-14 10:39:00 +0800
description: Set up Cloudflare WARP as a SOCKS5 proxy on Linux, verify it works, integrate with Xray for selective routing, and troubleshoot common issues.
image: /assets/img/warp.png
tags: [Network]
categories: [Tech]
---

*Written by Biyu Huang, with [Cursor](https://www.cursor.com/) as co-author.*

---

[Cloudflare WARP](https://1.1.1.1/) is a free VPN-like service built on WireGuard. On Linux servers, it runs as a SOCKS5 proxy — useful for routing specific traffic through Cloudflare's network to get a clean IP, bypass geo-restrictions, or add a layer of privacy.

This guide covers setup, verification, Xray integration for selective routing, and common pitfalls.

---

## 1. Install and Connect

```bash
# Install WARP client (Debian/Ubuntu)
apt install cloudflare-warp

# Register your device with Cloudflare
warp-cli registration new

# Set WARP mode (proxy mode — doesn't hijack all traffic)
warp-cli mode warp

# Set the local SOCKS5 proxy port
warp-cli proxy port 40000

# Connect to Cloudflare's network
warp-cli connect

# Verify connection status
warp-cli status
```

**Mode choices:**
- `warp` — Routes traffic through Cloudflare's network via WireGuard. This is the standard mode.
- `doh` — DNS-over-HTTPS only, no traffic routing.
- `warp+doh` — Both traffic routing and DNS encryption.
- `proxy` — Exposes a local SOCKS5 proxy without system-wide routing (useful on servers).

For server use, `warp` mode with a proxy port is the most flexible — it gives you a local SOCKS5 endpoint you can selectively route traffic through.

---

## 2. Verify the Proxy

```bash
# Check your exit IP through WARP (should return a Cloudflare IP)
curl ifconfig.me --proxy socks5://127.0.0.1:40000

# Get detailed IP info (location, ASN, etc.)
curl -x "socks5://127.0.0.1:40000" ipinfo.io
```

If working correctly, the IP returned should belong to Cloudflare (ASN 13335) and may show a different geographic location than your server.

**Quick test without proxy (for comparison):**

```bash
# Your server's real IP
curl ifconfig.me

# Compare with WARP IP
curl ifconfig.me --proxy socks5://127.0.0.1:40000
```

---

## 3. Integration with Xray

WARP becomes powerful when combined with a proxy tool like [Xray](https://github.com/XTLS/Xray-core) for selective routing — route specific domains through WARP while blocking ads and letting other traffic flow directly.

### Xray Outbound Configuration

Add WARP as a SOCKS5 outbound in your Xray config:

```json
{
  "log": {
    "access": "/var/log/xray/access.log",
    "error": "/var/log/xray/error.log",
    "loglevel": "warning"
  },
  "outbounds": [
    {
      "protocol": "blackhole",
      "tag": "blocked"
    },
    {
      "protocol": "socks",
      "settings": {
        "servers": [
          {
            "address": "127.0.0.1",
            "port": 40000
          }
        ]
      },
      "tag": "warp"
    }
  ],
  "dns": {
    "servers": [
      "8.8.8.8",
      "8.8.4.4",
      "1.1.1.1",
      "1.0.0.1",
      "localhost",
      "https+local://dns.google/dns-query",
      "https+local://1.1.1.1/dns-query"
    ]
  },
  "routing": {
    "domainStrategy": "AsIs",
    "rules": [
      {
        "type": "field",
        "domain": [
          "geoip:cn",
          "geoip:private",
          "geosite:category-ads-all"
        ],
        "outboundTag": "blocked"
      },
      {
        "type": "field",
        "outboundTag": "warp",
        "domain": [
          "domain1.com",
          "domain2.com"
        ]
      }
    ]
  }
}
```

### How the Routing Works

The routing rules are evaluated **in order**:

1. **Block rule**: Traffic to Chinese IPs, private IPs, and known ad domains → blackhole (dropped)
2. **WARP rule**: Traffic to specified domains → routed through WARP's SOCKS5 proxy on port 40000
3. **Default**: Everything else follows the default outbound (typically direct or your primary proxy)

This pattern is useful when certain services block your server's IP but accept Cloudflare IPs, or when you need a different exit IP for specific destinations.

---

## 4. Auto-Start on Boot

Ensure WARP reconnects after server restarts:

```bash
# Enable WARP service
systemctl enable warp-svc

# Verify it's running
systemctl status warp-svc
```

WARP remembers your registration and settings across restarts. If the connection drops, it auto-reconnects.

---

## 5. Useful Commands

```bash
# Check current connection status
warp-cli status

# Disconnect temporarily
warp-cli disconnect

# Reconnect
warp-cli connect

# View current settings
warp-cli settings

# Check WARP account info
warp-cli registration show

# Reset registration (if issues persist)
warp-cli registration delete
warp-cli registration new
```

---

## 6. Troubleshooting

### WARP Won't Connect

```bash
# Check if the daemon is running
systemctl status warp-svc

# Restart the service
systemctl restart warp-svc

# Re-register if needed
warp-cli registration delete
warp-cli registration new
warp-cli connect
```

### Proxy Returns Server's Real IP

This usually means WARP is in the wrong mode or not connected:

```bash
warp-cli status       # Should show "Connected"
warp-cli mode warp    # Ensure correct mode
warp-cli connect      # Reconnect if needed
```

### Port Conflict

If port 40000 is already in use:

```bash
# Check what's using the port
ss -tlnp | grep 40000

# Change to a different port
warp-cli proxy port 41000
```

### DNS Resolution Issues

If DNS queries fail through WARP, ensure your Xray DNS config has fallback servers (like in the config above). WARP's DNS (1.1.1.1) should work, but having Google DNS (8.8.8.8) as backup prevents single-point failures.

---

## Summary

| Component | Role |
|-----------|------|
| **WARP** | Provides a clean Cloudflare IP via local SOCKS5 proxy |
| **Xray** | Routes selected traffic through WARP based on domain rules |
| **Routing rules** | Block ads/unwanted → WARP for specific domains → direct for the rest |

This setup gives you fine-grained control over which traffic exits through Cloudflare, without affecting your server's other services.
