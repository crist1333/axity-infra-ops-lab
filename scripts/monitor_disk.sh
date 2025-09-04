#!/bin/bash

# Disk Space Monitor Script for Axity Infrastructure
# Alerts if disk usage exceeds threshold

set -euo pipefail

# Configuration
THRESHOLD=${DISK_THRESHOLD:-85}
MOUNT_POINT=${MOUNT_POINT:-"/"}
SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL:-""}
GLPI_WEBHOOK_URL=${GLPI_WEBHOOK_URL:-"http://localhost:5000/alert"}
HOSTNAME=$(hostname)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Function to log messages
log() {
    echo "[$TIMESTAMP] $1"
}

# Function to send alert to webhook
send_alert() {
    local usage=$1
    local message="CRITICAL: Disk usage on $HOSTNAME ($MOUNT_POINT) is at ${usage}% (threshold: ${THRESHOLD}%)"
    
    if [[ -n "$GLPI_WEBHOOK_URL" ]]; then
        log "Sending alert to GLPI webhook..."
        curl -s -X POST "$GLPI_WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "{
                \"alert\": \"disk_space\",
                \"severity\": \"critical\",
                \"hostname\": \"$HOSTNAME\",
                \"mount_point\": \"$MOUNT_POINT\",
                \"usage_percent\": $usage,
                \"threshold\": $THRESHOLD,
                \"message\": \"$message\",
                \"timestamp\": \"$TIMESTAMP\"
            }" 2>/dev/null || log "Failed to send alert to GLPI webhook"
    fi
    
    if [[ -n "$SLACK_WEBHOOK_URL" ]]; then
        log "Sending alert to Slack webhook..."
        curl -s -X POST "$SLACK_WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "{\"text\": \"$message\"}" 2>/dev/null || log "Failed to send alert to Slack webhook"
    fi
}

# Function to check disk usage
check_disk_usage() {
    local usage
    usage=$(df "$MOUNT_POINT" | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [[ -z "$usage" ]] || ! [[ "$usage" =~ ^[0-9]+$ ]]; then
        log "${RED}ERROR: Could not determine disk usage for $MOUNT_POINT${NC}"
        exit 1
    fi
    
    log "Current disk usage for $MOUNT_POINT: ${usage}%"
    
    if (( usage >= THRESHOLD )); then
        log "${RED}CRITICAL: Disk usage ${usage}% exceeds threshold ${THRESHOLD}%${NC}"
        send_alert "$usage"
        return 1
    elif (( usage >= THRESHOLD - 10 )); then
        log "${YELLOW}WARNING: Disk usage ${usage}% is approaching threshold ${THRESHOLD}%${NC}"
        return 0
    else
        log "${GREEN}OK: Disk usage ${usage}% is within acceptable limits${NC}"
        return 0
    fi
}

# Function to show disk info
show_disk_info() {
    log "Disk information for $MOUNT_POINT:"
    df -h "$MOUNT_POINT"
    echo
    log "Top 10 largest directories:"
    du -h "$MOUNT_POINT" 2>/dev/null | sort -hr | head -10 2>/dev/null || true
}

# Main execution
main() {
    log "Starting disk space monitoring for $MOUNT_POINT (threshold: ${THRESHOLD}%)"
    
    if [[ "${1:-}" == "--info" ]]; then
        show_disk_info
        exit 0
    fi
    
    check_disk_usage
    exit_code=$?
    
    if [[ $exit_code -eq 0 ]]; then
        log "Disk monitoring completed successfully"
    else
        log "Disk monitoring completed with alerts"
    fi
    
    exit $exit_code
}

# Help function
show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
  --info        Show detailed disk information
  --help        Show this help message

Environment Variables:
  DISK_THRESHOLD    Threshold percentage (default: 85)
  MOUNT_POINT      Mount point to monitor (default: /)
  GLPI_WEBHOOK_URL Webhook URL for GLPI alerts
  SLACK_WEBHOOK_URL Webhook URL for Slack alerts

Examples:
  $0                    # Monitor disk with default settings
  $0 --info             # Show disk information
  DISK_THRESHOLD=90 $0  # Monitor with 90% threshold
  MOUNT_POINT=/var $0   # Monitor /var mount point
EOF
}

# Check command line arguments
case "${1:-}" in
    --help|-h)
        show_help
        exit 0
        ;;
    *)
        main "${1:-}"
        ;;
esac