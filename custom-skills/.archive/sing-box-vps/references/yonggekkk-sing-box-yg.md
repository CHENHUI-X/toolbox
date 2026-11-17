# yonggekkk/sing-box-yg — Reference

**Repo**: https://github.com/yonggekkk/sing-box-yg  
**Stars**: 8847  
**Author**: 甬哥侃侃侃 (yonggekkk)  
**YouTube**: https://youtube.com/@ygkkk  
**TG Group**: https://t.me/ygkkktg  
**Blog**: https://ygkkk.blogspot.com  

## Repo Structure

| File | Purpose |
|------|---------|
| `sb.sh` | Main VPS install script |
| `kp.sh` | Keep-alive / management |
| `serv00.sh` | Serv00/Hostuno edition |
| `version` / `sversion` | Version tracking |
| `app.js` / `index.html` | Web panel assets |
| `sb.txt` | Config / notes |
| `workers_keep.js` | Cloudflare Workers keepalive |

## VPS Install Command

```bash
bash <(wget -qO- https://raw.githubusercontent.com/yonggekkk/sing-box-yg/main/sb.sh)
# or
bash <(curl -Ls https://raw.githubusercontent.com/yonggekkk/sing-box-yg/main/sb.sh)
```

## Serv00 Install Command

```bash
bash <(curl -Ls https://raw.githubusercontent.com/yonggekkk/sing-box-yg/main/serv00.sh)
```

## Video Tutorials (from author)

1. SFA/SFI/SFW client config, Argo tunnel, dual cert, domain routing
2. Pure IPv6 VPS, CDN优选IP setup
3. GitLab private subscription sync, WARP ChatGPT分流
4. Vmess CDN优选IP multi-mode
5. Oblivion WARP + Psiphon VPN (30 countries)
6. AnyTLS protocol, Clash/Mihomo subscription update

## System Requirements

- **OS**: Ubuntu/Debian/CentOS (Alpine partially supported)
- **Arch**: amd64, arm64, armv7
- **Virt**: Not OpenVZ/LXC
- **User**: root (`EUID -ne 0` check)
- **Init**: systemd

## Quick Facts

- "回车三次就安装完成" — three enters to install
- Local subscription generation only (no third-party converters)
- SFW (Windows client) supports subscription links
- Post-install shortcut: `sb`
- Config files: `/etc/s-box/sb.json`, `/etc/s-box/sb10.json`, `/etc/s-box/sb11.json`
