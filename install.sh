#!/bin/sh
#####################################################
# CyberPanel Free - One-Click Installer
# https://github.com/onyangodonomondi/cyberpanel-free
#####################################################

echo "Starting CyberPanel Free Installer..."

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo ""
    echo "============================================================"
    echo "          CyberPanel Free Installer"
    echo "     Premium Features Unlocked - SSL Hero Included"
    echo "============================================================"
    echo ""
}

print_step() {
    echo "[OK] $1"
}

print_warning() {
    echo "[WARNING] $1"
}

print_error() {
    echo "[ERROR] $1"
}

# Check if running as root
check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        print_error "This script must be run as root"
        echo "Please run: sudo su - (then run the installer again)"
        exit 1
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
        apt-get update -qq >/dev/null 2>&1 || true
        apt-get install -y -qq git python3 python3-pip python3-venv python3-dev wget curl >/dev/null 2>&1 || true
    else
        yum update -y >/dev/null 2>&1 || true
        yum install -y git python3 python3-pip wget curl >/dev/null 2>&1 || true
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
    
    # Clone to temp directory first, then move contents properly
    TEMP_DIR="/tmp/cyberpanel-free-$$"
    git clone https://github.com/onyangodonomondi/cyberpanel-free.git "$TEMP_DIR"
    
    # Move cyberpanel directory contents to install dir (so CyberCP/ is at the right level)
    mv "$TEMP_DIR/cyberpanel" "$INSTALL_DIR"
    rm -rf "$TEMP_DIR"
    
    # Create virtualenv in /usr/local/CyberCP which will create bin/python
    print_step "Setting up Python virtual environment..."
    python3 -m venv --system-site-packages "$INSTALL_DIR"
    
    # Activate virtualenv and install requirements
    . "$INSTALL_DIR/bin/activate"
    
    # Upgrade pip and install wheel first
    pip install --upgrade pip wheel >/dev/null 2>&1 || true
    
    # Install requirements if file exists
    if [ -f "$INSTALL_DIR/requirements.txt" ]; then
        print_step "Installing Python dependencies..."
        pip install --ignore-installed -r "$INSTALL_DIR/requirements.txt" >/dev/null 2>&1 || true
    fi
    
    print_step "Starting CyberPanel installation..."
    cd "$INSTALL_DIR"
    
    # Detect public IP
    if [ -z "$SERVER_IP" ]; then
        SERVER_IP=$(curl -s https://api.ipify.org 2>/dev/null || wget -qO- https://api.ipify.org 2>/dev/null || echo "")
    fi
    
    # Fallback: Prompt user if IP detection failed
    if [ -z "$SERVER_IP" ]; then
        printf "Unable to automatically detect your server's public IP.\n"
        printf "Please enter your server's public IP address: "
        read -r SERVER_IP
    fi
    
    # Validate IP
    if [ -z "$SERVER_IP" ]; then
         echo "Error: Public IP is required to proceed."
         exit 1
    fi
    
    echo "Using Server IP: $SERVER_IP"
    
    # Run the Python installer with the required IP argument
    python3 install/install.py "$SERVER_IP"
}

# Main
main() {
    print_header
    check_root
    check_os
    check_requirements
    
    INSTALL_DIR="/usr/local/CyberCP"
    
    # Ensure fresh code if repo exists
    if [ -d "$INSTALL_DIR" ]; then
        rm -rf "$INSTALL_DIR"
    fi
    
    echo ""
    echo "This will install CyberPanel Free on your server."
    echo ""
    printf "Press ENTER to continue with installation... "
    read -r ignored_var
    
    install_dependencies
    install_cyberpanel
    
    echo ""
    echo "============================================================"
    echo "          Installation Complete!"
    echo "============================================================"
    echo ""
    echo "Access CyberPanel at: https://$(hostname -I | awk '{print $1}'):8090"
    echo ""
}

main "$@"
