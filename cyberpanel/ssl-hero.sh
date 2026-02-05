#!/bin/bash
# ============================================================================
# CyberPanel SSL Hero - Comprehensive SSL Repair Utility
# Author: Don (Mocky Digital)
# GitHub: https://github.com/onyangodonomondi/cyberpanel-ssl-hero
# 
# Usage (Single Domain):
#   curl -sL https://raw.githubusercontent.com/onyangodonomondi/SSL-Cyberpanel/main/ssl-hero.sh | sudo bash
#
# Usage (Batch Mode - All Domains):
#   curl -sL https://raw.githubusercontent.com/onyangodonomondi/SSL-Cyberpanel/main/ssl-hero.sh | sudo bash -s -- --all
#
# Usage (Specific Domain):
#   curl -sL https://raw.githubusercontent.com/onyangodonomondi/SSL-Cyberpanel/main/ssl-hero.sh | sudo bash -s -- -d example.com
# ============================================================================

set -e

# Colors for output
RED='\e[31m'
GREEN='\e[32m'
YELLOW='\e[33m'
BLUE='\e[34m'
CYAN='\e[36m'
BOLD='\e[1m'
NC='\e[0m' # No Color

# Global counters for batch mode
TOTAL_DOMAINS=0
SUCCESS_COUNT=0
FAILED_COUNT=0
SKIPPED_COUNT=0
FORCE_MODE=false
declare -a FAILED_DOMAINS
declare -a SUCCESS_DOMAINS
declare -a SKIPPED_DOMAINS

# Banner
show_banner() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║           CyberPanel SSL Hero - SSL Repair Utility            ║"
    echo "║                   Author: Don (Mocky Digital)                 ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Help message
show_help() {
    echo "Usage: ssl-hero.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -d, --domain DOMAIN    Fix SSL for a specific domain"
    echo "  -a, --all              Fix SSL for ALL domains on this VPS"
    echo "  -f, --force            Force reissue even if certificate is valid"
    echo "  -l, --list             List all domains on this VPS"
    echo "  -s, --status           Show SSL status for all domains"
    echo "  -h, --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  ssl-hero.sh                     Interactive mode (prompts for domain)"
    echo "  ssl-hero.sh -d example.com      Fix SSL for example.com"
    echo "  ssl-hero.sh --all               Fix only domains needing renewal"
    echo "  ssl-hero.sh --all --force       Force reissue ALL certificates"
    echo "  ssl-hero.sh --list              List all CyberPanel domains"
    echo "  ssl-hero.sh --status            Check SSL expiry for all domains"
}

# Detect all CyberPanel domains
get_all_domains() {
    local domains=()
    
    # Method 1: Check /home directory for domain folders
    for dir in /home/*/public_html; do
        if [ -d "$dir" ]; then
            domain=$(basename $(dirname "$dir"))
            # Skip system directories
            if [[ "$domain" != "cyberpanel" && "$domain" != "vmail" && "$domain" != "lscpd" ]]; then
                domains+=("$domain")
            fi
        fi
    done
    
    # Method 2: Also check CyberPanel's website list if available
    if [ -f "/usr/local/CyberCP/websites.json" ]; then
        while IFS= read -r line; do
            domain=$(echo "$line" | grep -oP '"domain":\s*"\K[^"]+')
            if [ -n "$domain" ] && [[ ! " ${domains[@]} " =~ " ${domain} " ]]; then
                domains+=("$domain")
            fi
        done < "/usr/local/CyberCP/websites.json"
    fi
    
    # Return unique domains
    printf '%s\n' "${domains[@]}" | sort -u
}

# List all domains
list_domains() {
    echo -e "${BLUE}Domains found on this VPS:${NC}"
    echo ""
    local count=0
    while IFS= read -r domain; do
        if [ -n "$domain" ]; then
            count=$((count + 1))
            echo -e "  ${CYAN}$count.${NC} $domain"
        fi
    done <<< "$(get_all_domains)"
    
    if [ $count -eq 0 ]; then
        echo -e "${YELLOW}No domains found in /home/*/public_html${NC}"
    else
        echo ""
        echo -e "${GREEN}Total: $count domain(s)${NC}"
    fi
}

# Check SSL status for all domains
check_ssl_status() {
    echo -e "${BLUE}SSL Status for all domains:${NC}"
    echo ""
    printf "%-35s %-15s %-25s\n" "DOMAIN" "STATUS" "EXPIRES"
    printf "%-35s %-15s %-25s\n" "------" "------" "-------"
    
    while IFS= read -r domain; do
        if [ -n "$domain" ]; then
            cert_file="/etc/letsencrypt/live/$domain/fullchain.pem"
            if [ -f "$cert_file" ]; then
                expiry=$(openssl x509 -enddate -noout -in "$cert_file" 2>/dev/null | cut -d= -f2)
                expiry_epoch=$(date -d "$expiry" +%s 2>/dev/null || echo 0)
                now_epoch=$(date +%s)
                days_left=$(( (expiry_epoch - now_epoch) / 86400 ))
                
                if [ $days_left -lt 0 ]; then
                    status="${RED}EXPIRED${NC}"
                elif [ $days_left -lt 7 ]; then
                    status="${RED}CRITICAL${NC}"
                elif [ $days_left -lt 30 ]; then
                    status="${YELLOW}WARNING${NC}"
                else
                    status="${GREEN}OK${NC}"
                fi
                printf "%-35s %-15b %-25s\n" "$domain" "$status" "$expiry ($days_left days)"
            else
                printf "%-35s %-15b %-25s\n" "$domain" "${YELLOW}NO CERT${NC}" "N/A"
            fi
        fi
    done <<< "$(get_all_domains)"
    echo ""
}

# Fix SSL for a single domain
fix_domain_ssl() {
    local DOMAIN="$1"
    local BATCH_MODE="${2:-false}"
    
    # Strip any www. prefix if user included it
    DOMAIN=$(echo "$DOMAIN" | sed 's/^www\.//')
    
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  Processing: ${BOLD}$DOMAIN${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # Check if certificate is still valid (in batch mode, skip if > 30 days remaining)
    if [ "$BATCH_MODE" = "true" ] && [ "$FORCE_MODE" = "false" ]; then
        local cert_file="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"
        if [ -f "$cert_file" ]; then
            local expiry=$(openssl x509 -enddate -noout -in "$cert_file" 2>/dev/null | cut -d= -f2)
            local expiry_epoch=$(date -d "$expiry" +%s 2>/dev/null || echo 0)
            local now_epoch=$(date +%s)
            local days_left=$(( (expiry_epoch - now_epoch) / 86400 ))
            
            if [ $days_left -gt 30 ]; then
                echo -e "${GREEN}✓ Certificate valid for $days_left more days - SKIPPING${NC}"
                SKIPPED_DOMAINS+=("$DOMAIN")
                SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
                return 0
            elif [ $days_left -gt 0 ]; then
                echo -e "${YELLOW}Certificate expires in $days_left days - will renew${NC}"
            else
                echo -e "${RED}Certificate expired - will renew${NC}"
            fi
        else
            echo -e "${YELLOW}No certificate found - will issue new one${NC}"
        fi
    fi
    
    # Detect Webroot (CyberPanel Standard)
    WEBROOT="/home/$DOMAIN/public_html"
    if [ ! -d "$WEBROOT" ]; then
        echo -e "${YELLOW}Warning: Standard webroot not found. Checking alternative paths...${NC}"
        DOMAIN_SHORT=$(echo "$DOMAIN" | cut -d'.' -f1)
        if [ -d "/home/$DOMAIN_SHORT/public_html" ]; then
            WEBROOT="/home/$DOMAIN_SHORT/public_html"
            echo -e "${GREEN}Found webroot at: $WEBROOT${NC}"
        else
            WEBROOT="/usr/local/lsws/Example/html"
            echo -e "${YELLOW}Defaulting to OLS Example root: $WEBROOT${NC}"
        fi
    fi
    
    echo -e "Webroot: $WEBROOT"
    
    # Check DNS Resolution
    echo -e "${GREEN}[1/5] Checking DNS resolution...${NC}"
    SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s icanhazip.com 2>/dev/null || echo "unknown")
    DOMAIN_IP=$(dig +short "$DOMAIN" A 2>/dev/null | head -1)
    
    if [ -z "$DOMAIN_IP" ]; then
        echo -e "${YELLOW}Warning: Could not resolve $DOMAIN.${NC}"
        if [ "$BATCH_MODE" = "true" ]; then
            echo -e "${YELLOW}Skipping $DOMAIN in batch mode...${NC}"
            SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
            return 1
        fi
    elif [ "$DOMAIN_IP" != "$SERVER_IP" ]; then
        echo -e "${YELLOW}Warning: $DOMAIN resolves to $DOMAIN_IP, but this server is $SERVER_IP${NC}"
        if [ "$BATCH_MODE" = "true" ]; then
            echo -e "${YELLOW}Skipping $DOMAIN in batch mode...${NC}"
            SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
            return 1
        else
            read -p "Continue anyway? (y/n): " CONTINUE
            if [ "$CONTINUE" != "y" ]; then
                echo -e "${RED}Aborted.${NC}"
                return 1
            fi
        fi
    else
        echo -e "${GREEN}✓ DNS looks good: $DOMAIN -> $DOMAIN_IP${NC}"
    fi
    
    # Check www subdomain
    WWW_IP=$(dig +short "www.$DOMAIN" A 2>/dev/null | head -1)
    INCLUDE_WWW=true
    if [ -z "$WWW_IP" ]; then
        echo -e "${YELLOW}Note: www.$DOMAIN has no A record. Will issue cert for main domain only.${NC}"
        INCLUDE_WWW=false
    elif [ "$WWW_IP" != "$SERVER_IP" ]; then
        echo -e "${YELLOW}Note: www.$DOMAIN points elsewhere. Will issue cert for main domain only.${NC}"
        INCLUDE_WWW=false
    fi
    
    # Cleanup old certificates
    echo -e "${GREEN}[2/5] Cleaning up old certificate files...${NC}"
    rm -rf /etc/letsencrypt/live/$DOMAIN/ 2>/dev/null || true
    rm -rf /root/.acme.sh/${DOMAIN}_ecc/ 2>/dev/null || true
    rm -rf /root/.acme.sh/${DOMAIN}/ 2>/dev/null || true
    mkdir -p /etc/letsencrypt/live/$DOMAIN/
    echo -e "${GREEN}✓ Old certificates cleaned${NC}"
    
    # Issue certificate
    echo -e "${GREEN}[3/5] Requesting new certificate (Let's Encrypt)...${NC}"
    
    if [ "$INCLUDE_WWW" = true ]; then
        DOMAIN_ARGS="-d $DOMAIN -d www.$DOMAIN"
        echo "Issuing certificate for: $DOMAIN and www.$DOMAIN"
    else
        DOMAIN_ARGS="-d $DOMAIN"
        echo "Issuing certificate for: $DOMAIN only"
    fi
    
    local ISSUE_SUCCESS=false
    if /root/.acme.sh/acme.sh --issue $DOMAIN_ARGS -w $WEBROOT --force --server letsencrypt 2>/dev/null; then
        echo -e "${GREEN}✓ Certificate issued successfully${NC}"
        ISSUE_SUCCESS=true
    else
        echo -e "${YELLOW}Webroot mode failed. Trying standalone mode...${NC}"
        systemctl stop lsws 2>/dev/null || true
        if /root/.acme.sh/acme.sh --issue $DOMAIN_ARGS --standalone --force --server letsencrypt 2>/dev/null; then
            echo -e "${GREEN}✓ Certificate issued successfully (standalone mode)${NC}"
            ISSUE_SUCCESS=true
        fi
        systemctl start lsws 2>/dev/null || true
    fi
    
    if [ "$ISSUE_SUCCESS" = false ]; then
        echo -e "${RED}✗ Certificate issuance failed for $DOMAIN${NC}"
        FAILED_DOMAINS+=("$DOMAIN")
        FAILED_COUNT=$((FAILED_COUNT + 1))
        return 1
    fi
    
    # Install certificate
    echo -e "${GREEN}[4/5] Installing certificate to server paths...${NC}"
    /root/.acme.sh/acme.sh --install-cert -d $DOMAIN \
        --cert-file /etc/letsencrypt/live/$DOMAIN/cert.pem \
        --key-file /etc/letsencrypt/live/$DOMAIN/privkey.pem \
        --fullchain-file /etc/letsencrypt/live/$DOMAIN/fullchain.pem \
        --reloadcmd "systemctl restart lsws" 2>/dev/null
    
    echo -e "${GREEN}✓ Certificate installed${NC}"
    
    # Verification
    echo -e "${GREEN}[5/5] Verifying certificate...${NC}"
    
    if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
        NEW_DATE=$(openssl x509 -enddate -noout -in /etc/letsencrypt/live/$DOMAIN/fullchain.pem | cut -d= -f2)
        echo -e "${GREEN}✓ $DOMAIN - Expires: $NEW_DATE${NC}"
        SUCCESS_DOMAINS+=("$DOMAIN")
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        return 0
    else
        echo -e "${RED}✗ Certificate file not found after installation${NC}"
        FAILED_DOMAINS+=("$DOMAIN")
        FAILED_COUNT=$((FAILED_COUNT + 1))
        return 1
    fi
}

# Setup ACME (run once before batch processing)
setup_acme() {
    echo -e "${GREEN}Setting up ACME client...${NC}"
    
    if [ ! -f "/root/.acme.sh/acme.sh" ]; then
        echo "Installing acme.sh..."
        curl -s https://get.acme.sh | sh -s email=admin@localhost >/dev/null 2>&1
    else
        echo "Upgrading acme.sh..."
        /root/.acme.sh/acme.sh --upgrade --auto-upgrade >/dev/null 2>&1
    fi
    
    # Open ports if UFW is active
    if command -v ufw &> /dev/null && ufw status | grep -q "Status: active"; then
        ufw allow 80/tcp > /dev/null 2>&1
        ufw allow 443/tcp > /dev/null 2>&1
        echo -e "${GREEN}✓ Firewall ports 80 and 443 are open${NC}"
    fi
    
    echo -e "${GREEN}✓ ACME setup complete${NC}"
}

# Batch mode - fix all domains
fix_all_domains() {
    echo -e "${BLUE}Starting batch SSL fix for ALL domains...${NC}"
    echo ""
    
    # Get all domains
    local domains_list=$(get_all_domains)
    TOTAL_DOMAINS=$(echo "$domains_list" | grep -c . || echo 0)
    
    if [ "$TOTAL_DOMAINS" -eq 0 ]; then
        echo -e "${YELLOW}No domains found on this VPS.${NC}"
        exit 1
    fi
    
    echo -e "Found ${BOLD}$TOTAL_DOMAINS${NC} domain(s) to process."
    echo -e "${CYAN}Processing will begin immediately...${NC}"
    echo ""
    
    # Setup ACME once
    setup_acme
    
    # Process each domain
    local current=0
    while IFS= read -r domain; do
        if [ -n "$domain" ]; then
            current=$((current + 1))
            echo ""
            echo -e "${CYAN}[$current/$TOTAL_DOMAINS] Processing $domain...${NC}"
            fix_domain_ssl "$domain" "true" || true
        fi
    done <<< "$domains_list"
    
    # Restart LiteSpeed once at the end
    echo ""
    echo -e "${GREEN}Restarting OpenLiteSpeed...${NC}"
    systemctl restart lsws
    
    # Show summary
    show_batch_summary
}

# Show batch summary
show_batch_summary() {
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}                    ${GREEN}BATCH PROCESSING COMPLETE${NC}                   ${BLUE}║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "Total Domains:    ${BOLD}$TOTAL_DOMAINS${NC}"
    echo -e "Successful:       ${GREEN}$SUCCESS_COUNT${NC}"
    echo -e "Failed:           ${RED}$FAILED_COUNT${NC}"
    echo -e "Skipped:          ${YELLOW}$SKIPPED_COUNT${NC}"
    echo ""
    
    if [ ${#SUCCESS_DOMAINS[@]} -gt 0 ]; then
        echo -e "${GREEN}✓ Successfully fixed:${NC}"
        for domain in "${SUCCESS_DOMAINS[@]}"; do
            echo -e "  - $domain"
        done
        echo ""
    fi
    
    if [ ${#FAILED_DOMAINS[@]} -gt 0 ]; then
        echo -e "${RED}✗ Failed domains:${NC}"
        for domain in "${FAILED_DOMAINS[@]}"; do
            echo -e "  - $domain"
        done
        echo ""
        echo -e "${YELLOW}Tip: Run the script individually for failed domains to see detailed errors.${NC}"
    fi
    
    if [ ${#SKIPPED_DOMAINS[@]} -gt 0 ]; then
        echo -e "${CYAN}○ Skipped (valid certs):${NC}"
        for domain in "${SKIPPED_DOMAINS[@]}"; do
            echo -e "  - $domain"
        done
        echo ""
        echo -e "${YELLOW}Tip: Use --force to renew these certificates anyway.${NC}"
    fi
}

# Main execution
main() {
    show_banner
    
    # Prerequisites: Ensure running as root
    if [ "$EUID" -ne 0 ]; then 
        echo -e "${RED}Error: Please run as root (use sudo).${NC}"
        exit 1
    fi
    
    # --- CORE RECOVERY BLOCK ---
    # Fixes the "Fatal error in configuration: No listener available for admin"
    echo -e "\e[32m[0/6] Checking LiteSpeed Admin Core...\e[0m"
    ADMIN_CERT="/usr/local/lsws/admin/conf/webadmin.crt"
    if [ ! -f "$ADMIN_CERT" ]; then
        echo -e "\e[33mWarning: Admin certificate missing. Regenerating core...\e[0m"
        # Only proceed if directory exists to avoid errors in dev environments
        if [ -d "/usr/local/lsws/admin/conf/" ]; then
            cd /usr/local/lsws/admin/conf/
            openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout webadmin.key -out webadmin.crt \
            -subj "/C=KE/ST=Nairobi/L=Nairobi/O=CyberPanel/CN=Admin"
            chown lsadm:lsadm webadmin.key webadmin.crt
            chmod 600 webadmin.key
            # Return to previous directory
            cd - > /dev/null
        else
            echo -e "\e[31mError: LiteSpeed conf directory not found. Skipping core recovery.\e[0m"
        fi
    fi
    
    # Parse arguments
    case "${1:-}" in
        -h|--help)
            show_help
            exit 0
            ;;
        -l|--list)
            list_domains
            exit 0
            ;;
        -s|--status)
            check_ssl_status
            exit 0
            ;;
        -a|--all)
            # Check for additional flags
            shift
            while [ $# -gt 0 ]; do
                case "$1" in
                    -f|--force)
                        FORCE_MODE=true
                        echo -e "${YELLOW}Force mode enabled - will renew ALL certificates${NC}"
                        ;;
                esac
                shift
            done
            fix_all_domains
            exit 0
            ;;
        -d|--domain)
            if [ -z "${2:-}" ]; then
                echo -e "${RED}Error: Please specify a domain with -d option${NC}"
                exit 1
            fi
            setup_acme
            fix_domain_ssl "$2" "false"
            systemctl restart lsws
            echo ""
            echo -e "${GREEN}Done! Test your site: https://$2${NC}"
            exit 0
            ;;
        "")
            # Interactive mode
            read -p "Enter the domain to fix (e.g., example.com): " DOMAIN
            if [ -z "$DOMAIN" ]; then
                echo -e "${RED}Domain cannot be empty.${NC}"
                exit 1
            fi
            setup_acme
            fix_domain_ssl "$DOMAIN" "false"
            systemctl restart lsws
            
            echo ""
            echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
            echo -e "${BLUE}║${NC}              ${GREEN}✓ SSL REPAIR COMPLETE${NC}                          ${BLUE}║${NC}"
            echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
            echo ""
            echo -e "Test your site: ${BOLD}https://$DOMAIN${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
