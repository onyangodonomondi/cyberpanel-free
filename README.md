# 🚀 CyberPanel Free

**A free, community-maintained fork of CyberPanel with premium features unlocked and enhanced SSL management.**

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔓 **Premium Unlocked** | All premium features available for free |
| 🔒 **SSL Hero** | One-click SSL fix for all domains on your VPS |
| 🌐 **OpenLiteSpeed** | High-performance web server included |
| 📧 **Email Server** | Full email stack with Postfix & Dovecot |
| 🔥 **Firewall** | Built-in CSF/FirewallD integration |
| 📊 **DNS Management** | PowerDNS for domain management |

## 📦 Installation

### One-Line Install (Recommended)

```bash
sh <(curl -sL https://raw.githubusercontent.com/onyangodonomondi/cyberpanel-free/main/install.sh || wget -qO - https://raw.githubusercontent.com/onyangodonomondi/cyberpanel-free/main/install.sh)
```

### Manual Installation

```bash
git clone https://github.com/onyangodonomondi/cyberpanel-free.git
cd cyberpanel-free/cyberpanel
sudo python3 install/install.py
```

### Requirements

- **OS**: Ubuntu 20.04/22.04 or CentOS 7/8
- **RAM**: Minimum 1GB (2GB+ recommended)
- **Storage**: 10GB+ free disk space
- **Access**: Root/sudo privileges

## 🔒 SSL Hero - Fix SSL for All Domains

After installation, use the built-in SSL Hero tool to fix SSL certificates:

### Fix ALL Domains on VPS
```bash
cd /usr/local/CyberCP
sudo bash ssl-hero.sh --all
```

### Fix Specific Domain
```bash
sudo bash ssl-hero.sh -d example.com
```

### Check SSL Status
```bash
sudo bash ssl-hero.sh --status
```

## 🛠️ What's Different from Official CyberPanel?

| Official | This Fork |
|----------|-----------|
| Premium features require license | All features unlocked |
| Limited SSL troubleshooting | SSL Hero batch fix tool |
| Standard installation | Community maintained |

## 📁 Directory Structure

```
cyberpanel-free/
├── cyberpanel/          # Main Django application
│   ├── install/         # Installation scripts
│   ├── ssl-hero.sh      # SSL batch fix tool
│   ├── manageSSL/       # SSL management module
│   └── ...
└── README.md
```

## 🔧 Post-Installation

After installation, access CyberPanel at:
- **URL**: `https://your-server-ip:8090`
- **Default User**: admin
- **Password**: Set during installation

## 🆘 Troubleshooting

### SSL Issues
```bash
# Check SSL status for all domains
sudo bash /usr/local/CyberCP/ssl-hero.sh --status

# Force fix all SSL certificates
sudo bash /usr/local/CyberCP/ssl-hero.sh --all --force
```

### Admin Panel Access Issues
If you see `SSL_ERROR_RX_RECORD_TOO_LONG` or cannot access port 8090, run the script to auto-repair the admin certificate:
```bash
sudo bash /usr/local/CyberCP/ssl-hero.sh
```

### Service Issues
```bash
# Restart CyberPanel services
sudo systemctl restart lscpd
sudo systemctl restart lsws
```

## 👤 Author

**Don (Mocky Digital)**

## 📄 License

This project is based on CyberPanel (GPLv3). Modifications licensed under MIT.

---

⭐ If this project helps you, consider giving it a star!
