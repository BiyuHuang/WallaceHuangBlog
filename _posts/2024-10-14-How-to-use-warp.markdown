---
layout: post
title: "How to use warp"
date: 2024-10-14 10:39:00 +0800
description: How to use warp
img: warp.png
tags: Network
---

# How to use warp

1. Install warp client and Connect warp
   ```bash
   # Install Warp
   apt install cloudflare-warp
   # Register device
   warp-cli registration new
   # Set warp mode
   warp-cli mode warp
   # Set the listening port for WARP proxy
   warp-cli proxy port 40000
   # Connect Warp
   warp-cli connect
   # Warp Status
   warp-cli status
   ```

2. Verify warp service status
   ```bash
   # It returns an available IP4 provided by Cloudflare
   curl ifconfig.me --proxy socks5://127.0.0.1:40000
   
   # Get more details
   curl -x "socks5://127.0.0.1:40000" ipinfo.io
   ```

3. Integration with Xray
   ```Json
   {
    "log":
        {
            "access": "/var/log/xray/access.log",
            "error": "/var/log/xray/error.log",
            "loglevel": "warning"
        },
        "outbounds":
        [
            {
                "protocol": "blackhole",
                "tag": "blocked"
            },
            {
                "protocol": "socks",
                "settings":
                {
                    "servers":
                    [
                        {
                            "address": "127.0.0.1",
                            "port": 40000
                        }
                    ]
                },
                "tag": "warp"
            }
        ],
        "dns":
        {
            "servers":
            [
                "8.8.8.8",
                "8.8.4.4",
                "1.1.1.1",
                "1.0.0.1",
                "localhost",
                "https+local://dns.google/dns-query",
                "https+local://1.1.1.1/dns-query"
            ]
        },
        "routing":
        {
            "domainStrategy": "AsIs",
            "rules":
            [
                // first rule: block Ads
                {
                    "type": "field",
                    "domain":
                    [
                        "geosite:category-ads-all"
                    ],
                    "outboundTag": "blocked"
                },
                // Second rule: access specified domains by warp
                {
                    "type": "field",
                    "outboundTag": "warp",
                    "domain":
                    [
                        "domain1.com",
                        "domain2.com"
                    ]
                }
                // Other routing rules as follow
            ]
        }
   }
   ```