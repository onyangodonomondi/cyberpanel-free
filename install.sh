#!/bin/sh
#####################################################
# CyberPanel Free - One-Click Installer
# https://github.com/onyangodonomondi/cyberpanel-free
#####################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    printf "${BLUE}\n"
    printf "╔═══════════════════════════════════════════════════════════════╗\n"
    printf "║                                                               ║\n"
    printf "║           🚀 CyberPanel Free Installer 🚀                     ║\n"
    printf "║                                                               ║\n"
    printf "║     Premium Features Unlocked • SSL Hero Included             ║\n"
    printf "║                                                               ║\n"
    printf "╚═══════════════════════════════════════════════════════════════╝\n"
    printf "${NC}\n"
}

print_step() {
    printf "${GREEN}[✓]${NC} %s\n" "$1"
}

print_warning() {
    printf "${YELLOW}[!]${NC} %s\n" "$1"
}

print_error() {
    printf "${RED}[✗]${NC} %s\n" "$1"
}

# Check if running as root
check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        if command -v sudo >/dev/null 2>&1; then
            printf "${YELLOW}[!] Not running as root. Attempting to elevate with sudo...${NC}\n"
            # Download the script again to a temp file since we might be running from a pipe
            if command -v curl >/dev/null 2>&1; then
                curl -sL "https://raw.githubusercontent.com/onyangodonomondi/cyberpanel-free/main/install.sh?v=$(date +%s)" > /tmp/cyberpanel_install.sh
            else
                wget -qO /tmp/cyberpanel_install.sh "https://raw.githubusercontent.com/onyangodonomondi/cyberpanel-free/main/install.sh?v=$(date +%s)"
            fi
            
            exec sudo sh /tmp/cyberpanel_install.sh "$@"
        else
            print_error "This script must be run as root"
            echo "Please run: sudo su -"
            exit 1
        fi
    fi
}

# Check OS compatibility
check_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VERSION=$VERSION_ID
    else
        print_error "Cannot detect operating system"
        exit 1
    fi

    case $OS in
        ubuntu)
            if [ "$VERSION" != "18.04" ] && [ "$VERSION" != "20.04" ] && [ "$VERSION" != "22.04" ] && [ "$VERSION" != "24.04" ]; then
                print_warning "Ubuntu $VERSION may not be fully tested"
            fi
            print_step "Detected Ubuntu $VERSION"
            ;;
        centos|almalinux|rocky|cloudlinux|openeuler)
            print_step "Detected $OS $VERSION"
            ;;
        *)
            print_error "Unsupported OS: $OS"
            echo "Supported: Ubuntu 18.04/20.04/22.04/24.04, CentOS 7/8, AlmaLinux, Rocky Linux, CloudLinux, openEuler"
            exit 1
            ;;
    esac
}

# Check system requirements
check_requirements() {
    print_step "Checking system requirements..."
    
    # Check RAM
    TOTAL_RAM=$(free -m | awk '/^Mem:/{print $2}')
    if [ "$TOTAL_RAM" -lt 1024 ]; then
        print_warning "Low RAM detected: ${TOTAL_RAM}MB (minimum 1GB recommended)"
    else
        print_step "RAM: ${TOTAL_RAM}MB"
    fi
    
    # Check disk space
    DISK_FREE=$(df -P / | awk 'NR==2 {print $4}')
    # Convert blocks to GB (approximate, assuming 1K blocks)
    DISK_FREE_GB=$((DISK_FREE / 1024 / 1024))
    
    if [ "$DISK_FREE_GB" -lt 10 ]; then
        print_error "Insufficient disk space: ${DISK_FREE_GB}GB (minimum 10GB required)"
        exit 1
    else
        print_step "Disk space: ${DISK_FREE_GB}GB available"
    fi
}

# Install dependencies
install_dependencies() {
    print_step "Installing dependencies..."
    
    if [ "$OS" = "ubuntu" ]; then
        apt-get update -qq >/dev/null
        apt-get install -y -qq git python3 python3-pip wget curl >/dev/null
    else
        # RHEL/CentOS/Alma/Rocky
        yum update -y >/dev/null
        yum install -y git python3 python3-pip wget curl >/dev/null
    fi
}

# Clone and install
install_cyberpanel() {
    print_step "Cloning CyberPanel Free repository..."
    
    INSTALL_DIR="/usr/local/CyberCP"
    
    if [ -d "$INSTALL_DIR" ]; then
        print_warning "CyberPanel already installed at $INSTALL_DIR"
        printf "Do you want to reinstall? (y/n) "
        read -r REPLY
        case "$REPLY" in
            [yY]*) 
                rm -rf "$INSTALL_DIR"
                ;;
            *)
                echo "Installation cancelled"
                exit 0
                ;;
        esac
    fi
    
    git clone https://github.com/onyangodonomondi/cyberpanel-free.git "$INSTALL_DIR"
    
    print_step "Starting CyberPanel installation..."
    cd "$INSTALL_DIR/cyberpanel"
    
    # Run the Python installer
    # Detect public IP
    if [ -z "$SERVER_IP" ]; then
        SERVER_IP=$(curl -s https://api.ipify.org || wget -qO- https://api.ipify.org)
    fi
    
    # Run the Python installer with the required IP argument
    python3 install/install.py "$SERVER_IP"
}

# Main
main() {
    print_header
    check_root
    check_os
    check_requirements
    
    echo ""
    printf "${YELLOW}This will install CyberPanel Free on your server.${NC}\n"
    echo ""
    printf "Press ENTER to continue with installation... "
    read -r ignored_var
    
    install_dependencies
    install_cyberpanel
    
    echo ""
    printf "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}\n"
    printf "${GREEN}║           Installation Complete! 🎉                           ║${NC}\n"
    printf "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}\n"
    echo ""
    printf "Access CyberPanel at: https://%s:8090\n" "$(hostname -I | awk '{print $1}')"
    echo ""
}

main "$@"

