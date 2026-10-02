#!/bin/bash

# Claude Plugin Fixer Script
# Helps fix plugin issues and manually uninstall plugins when Claude CLI fails

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BOLD}🔧 Claude Plugin Fixer${NC}"
echo "======================="
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if jq is installed
if ! command_exists jq; then
    echo -e "${RED}❌ Error: jq is not installed${NC}"
    echo "Please install jq: apt/brew/yum install jq"
    exit 1
fi

# Settings and plugin files
SETTINGS_FILE="$HOME/.claude/settings.json"
INSTALLED_PLUGINS_FILE="$HOME/.claude/plugins/installed_plugins.json"
PLUGINS_DIR="$HOME/.claude/plugins"

# Function to list plugins
list_plugins() {
    echo -e "${BOLD}Current Plugins:${NC}"
    echo "----------------"
    
    if [ -f "$SETTINGS_FILE" ]; then
        local plugins=$(jq -r '.enabledPlugins | to_entries[] | "\(.key) = \(.value)"' "$SETTINGS_FILE" 2>/dev/null)
        if [ -n "$plugins" ]; then
            echo "$plugins" | while IFS= read -r plugin; do
                echo "  • $plugin"
            done
        else
            echo -e "  ${YELLOW}No plugins in settings${NC}"
        fi
    else
        echo -e "  ${YELLOW}Settings file not found${NC}"
    fi
    echo ""
}

# Function to manually uninstall a plugin
uninstall_plugin() {
    local plugin_key="$1"
    
    echo -e "${BOLD}Uninstalling: $plugin_key${NC}"
    echo "----------------------------"
    
    # Remove from settings.json
    if [ -f "$SETTINGS_FILE" ]; then
        echo "  Removing from settings.json..."
        jq "del(.enabledPlugins[\"$plugin_key\"])" "$SETTINGS_FILE" > /tmp/settings.json && \
        mv /tmp/settings.json "$SETTINGS_FILE"
        echo -e "  ${GREEN}✓${NC} Removed from settings"
    fi
    
    # Remove from installed_plugins.json
    if [ -f "$INSTALLED_PLUGINS_FILE" ]; then
        echo "  Removing from installed_plugins.json..."
        jq "del(.plugins[\"$plugin_key\"])" "$INSTALLED_PLUGINS_FILE" > /tmp/installed_plugins.json && \
        mv /tmp/installed_plugins.json "$INSTALLED_PLUGINS_FILE"
        echo -e "  ${GREEN}✓${NC} Removed from installed plugins"
    fi
    
    echo -e "${GREEN}✓ Plugin uninstalled successfully${NC}"
    echo ""
}

# Function to fix common issues
fix_issues() {
    echo -e "${BOLD}Fixing Common Issues:${NC}"
    echo "---------------------"
    
    # Ensure directories exist
    mkdir -p "$PLUGINS_DIR"
    echo -e "  ${GREEN}✓${NC} Plugin directories verified"
    
    # Ensure settings.json exists with proper structure
    if [ ! -f "$SETTINGS_FILE" ]; then
        echo '{"enabledPlugins":{}}' | jq '.' > "$SETTINGS_FILE"
        echo -e "  ${GREEN}✓${NC} Created settings.json"
    else
        # Ensure enabledPlugins exists
        jq '.enabledPlugins // {} | {enabledPlugins: .}' "$SETTINGS_FILE" > /tmp/settings.json && \
        mv /tmp/settings.json "$SETTINGS_FILE"
        echo -e "  ${GREEN}✓${NC} Settings structure verified"
    fi
    
    # Ensure installed_plugins.json exists
    if [ ! -f "$INSTALLED_PLUGINS_FILE" ]; then
        echo '{"version":1,"plugins":{}}' | jq '.' > "$INSTALLED_PLUGINS_FILE"
        echo -e "  ${GREEN}✓${NC} Created installed_plugins.json"
    fi
    
    echo ""
}

# Main menu
show_menu() {
    echo -e "${BOLD}Options:${NC}"
    echo "--------"
    echo "  1. List current plugins"
    echo "  2. Manually uninstall a plugin"
    echo "  3. Fix common plugin issues"
    echo "  4. Clean all plugins (full reset)"
    echo "  5. Exit"
    echo ""
    read -p "Select option (1-5): " choice
    
    case $choice in
        1)
            list_plugins
            ;;
        2)
            list_plugins
            read -p "Enter plugin key to uninstall (e.g., plugin-name@marketplace): " plugin_key
            if [ -n "$plugin_key" ]; then
                uninstall_plugin "$plugin_key"
            else
                echo -e "${RED}No plugin key provided${NC}"
            fi
            ;;
        3)
            fix_issues
            ;;
        4)
            echo -e "${YELLOW}⚠ This will remove ALL plugins and reset to clean state${NC}"
            read -p "Are you sure? (y/N): " confirm
            if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
                echo '{"enabledPlugins":{}}' | jq '.' > "$SETTINGS_FILE"
                echo '{"version":1,"plugins":{}}' | jq '.' > "$INSTALLED_PLUGINS_FILE"
                echo -e "${GREEN}✓ All plugins removed${NC}"
            else
                echo "Cancelled"
            fi
            ;;
        5)
            echo "Exiting..."
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid option${NC}"
            ;;
    esac
}

# If plugin key provided as argument, uninstall directly
if [ $# -eq 1 ]; then
    uninstall_plugin "$1"
    exit 0
fi

# Interactive mode
while true; do
    show_menu
    echo ""
    read -p "Press Enter to continue..."
    echo ""
done
