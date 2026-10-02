#!/bin/bash

# Claude Plugin Listing Script - Enhanced Version
# Lists all installed Claude plugins with detailed information

# Don't exit on error to allow full script execution
set +e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m' # No Color

echo -e "${BOLD}📦 Claude Plugin Manager - Enhanced${NC}"
echo "====================================="
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if Claude CLI is installed
if ! command_exists claude; then
    echo -e "${RED}❌ Error: Claude CLI is not installed${NC}"
    echo "Please install Claude CLI first: https://claude.ai/download"
    exit 1
fi

# Settings and plugin locations
SETTINGS_FILE="$HOME/.claude/settings.json"
PLUGINS_DIR="$HOME/.claude/plugins"
MARKETPLACES_DIR="$HOME/.claude/plugins/marketplaces"
INSTALLED_PLUGINS_FILE="$PLUGINS_DIR/installed_plugins.json"

# Function to get detailed plugin information
get_plugin_details() {
    local plugin_key="$1"
    local plugin_name="$2"
    local marketplace="$3"
    
    # Get actual install path from installed_plugins.json if available
    local plugin_path=""
    if [ -f "$INSTALLED_PLUGINS_FILE" ]; then
        plugin_path=$(jq -r ".plugins[\"$plugin_key\"].installPath // empty" "$INSTALLED_PLUGINS_FILE" 2>/dev/null)
    fi
    
    # Fallback to common plugin paths
    if [ -z "$plugin_path" ] || [ ! -d "$plugin_path" ]; then
        if [ -d "$PLUGINS_DIR/$plugin_name" ]; then
            plugin_path="$PLUGINS_DIR/$plugin_name"
        elif [ -d "$MARKETPLACES_DIR/$marketplace/plugins/$plugin_name" ]; then
            plugin_path="$MARKETPLACES_DIR/$marketplace/plugins/$plugin_name"
        elif [ -d "$MARKETPLACES_DIR/$marketplace/$plugin_name" ]; then
            plugin_path="$MARKETPLACES_DIR/$marketplace/$plugin_name"
        elif [ -d "$MARKETPLACES_DIR/$marketplace/sample-plugin" ]; then
            plugin_path="$MARKETPLACES_DIR/$marketplace/sample-plugin"
        fi
    fi
    
    # Find and read manifest file
    local manifest_file=""
    local possible_manifests=(
        "$plugin_path/.claude-plugin/plugin.json"
        "$plugin_path/plugin.json"
        "$plugin_path/manifest.json"
        "$plugin_path/package.json"
        "$plugin_path/.mcp.json"
    )
    
    for mf in "${possible_manifests[@]}"; do
        if [ -f "$mf" ]; then
            manifest_file="$mf"
            break
        fi
    done
    
    if [ -n "$manifest_file" ] && [ -f "$manifest_file" ] && command_exists jq; then
        # Extract basic information
        local version=$(jq -r '.version // "unknown"' "$manifest_file" 2>/dev/null)
        local author=$(jq -r '.author // "Unknown"' "$manifest_file" 2>/dev/null)
        local description=$(jq -r '.description // "No description"' "$manifest_file" 2>/dev/null)
        local license=$(jq -r '.license // "Unknown"' "$manifest_file" 2>/dev/null)
        local repository=$(jq -r '.repository // ""' "$manifest_file" 2>/dev/null)
        
        # Display basic information
        echo -e "    ${DIM}Version:${NC} $version"
        echo -e "    ${DIM}Author:${NC} $author"
        echo -e "    ${DIM}License:${NC} $license"
        if [ -n "$repository" ] && [ "$repository" != "null" ]; then
            echo -e "    ${DIM}Repository:${NC} $repository"
        fi
        echo -e "    ${DIM}Description:${NC}"
        echo "$description" | fold -w 70 | sed 's/^/      /'
        echo ""
        
        # Extract and display AGENTS
        echo -e "    ${CYAN}🤖 Agents:${NC}"
        local agents=""
        local agents_dir=$(jq -r '.agents.directory // empty' "$manifest_file" 2>/dev/null)
        
        if [ -n "$agents_dir" ] && [ -d "$plugin_path/$agents_dir" ]; then
            # List actual agent files from directory
            agents=$(find "$plugin_path/$agents_dir" \( -name "*.md" -o -name "*.yaml" -o -name "*.yml" -o -name "*.json" \) 2>/dev/null | \
                    while read -r file; do
                        basename "$file" | sed 's/\.[^.]*$//'
                    done | sort | uniq)
        fi
        
        # Also check for agents defined in manifest
        if [ -z "$agents" ]; then
            agents=$(jq -r '.agents[]? // .capabilities.agents[]? // empty' "$manifest_file" 2>/dev/null)
        fi
        
        if [ -n "$agents" ]; then
            local agent_count=0
            echo "$agents" | while IFS= read -r agent; do
                if [ -n "$agent" ]; then
                    echo -e "       • ${agent}"
                    agent_count=$((agent_count + 1))
                    # Show up to 15 agents
                    [ $agent_count -eq 15 ] && echo "       ..." && break
                fi
            done
        else
            echo -e "       ${DIM}No agents defined${NC}"
        fi
        echo ""
        
        # Extract and display COMMANDS
        echo -e "    ${MAGENTA}⚡ Commands:${NC}"
        local commands=""
        local commands_dir=$(jq -r '.commands.directory // empty' "$manifest_file" 2>/dev/null)
        local commands_prefix=$(jq -r '.commands.prefix // empty' "$manifest_file" 2>/dev/null)
        
        if [ -n "$commands_dir" ] && [ -d "$plugin_path/$commands_dir" ]; then
            # List actual command files from directory
            commands=$(find "$plugin_path/$commands_dir" \( -name "*.md" -o -name "*.sh" -o -name "*.js" -o -name "*.py" \) 2>/dev/null | \
                      while read -r file; do
                          basename "$file" | sed 's/\.[^.]*$//'
                      done | sort | uniq)
            
            # Add prefix if specified
            if [ -n "$commands_prefix" ] && [ "$commands_prefix" != "null" ] && [ -n "$commands" ]; then
                commands=$(echo "$commands" | sed "s/^/${commands_prefix}:/")
            fi
        fi
        
        # Also check for commands defined in manifest
        if [ -z "$commands" ]; then
            commands=$(jq -r '.commands[]? // .capabilities.commands[]? // empty | if type == "object" then .name // .id else . end' "$manifest_file" 2>/dev/null)
        fi
        
        if [ -n "$commands" ]; then
            local cmd_count=0
            echo "$commands" | while IFS= read -r cmd; do
                if [ -n "$cmd" ]; then
                    # Check if command file exists and show description if available
                    echo -e "       • ${cmd}"
                    cmd_count=$((cmd_count + 1))
                    [ $cmd_count -eq 15 ] && echo "       ..." && break
                fi
            done
        else
            echo -e "       ${DIM}No commands defined${NC}"
        fi
        echo ""
        
        # Extract and display SKILLS
        echo -e "    ${YELLOW}🎯 Skills:${NC}"
        local skills=""
        
        # First try to get from registry with descriptions
        local skills_from_registry=$(jq -r '.skills.registry[]? | "\(.name) - \(.description // "")"' "$manifest_file" 2>/dev/null)
        
        if [ -n "$skills_from_registry" ]; then
            skills="$skills_from_registry"
        else
            # Check skills directory
            local skills_dir=$(jq -r '.skills.directory // empty' "$manifest_file" 2>/dev/null)
            if [ -n "$skills_dir" ] && [ -d "$plugin_path/$skills_dir" ]; then
                skills=$(find "$plugin_path/$skills_dir" -type d -mindepth 1 -maxdepth 1 2>/dev/null | \
                        while read -r dir; do
                            basename "$dir"
                        done | sort)
            fi
        fi
        
        # Also check for skills defined directly
        if [ -z "$skills" ]; then
            skills=$(jq -r '.skills[]? // .capabilities.skills[]? // empty | if type == "object" then .name // .id else . end' "$manifest_file" 2>/dev/null)
        fi
        
        if [ -n "$skills" ]; then
            local skill_count=0
            echo "$skills" | while IFS= read -r skill; do
                if [ -n "$skill" ]; then
                    echo -e "       • ${skill}"
                    skill_count=$((skill_count + 1))
                    [ $skill_count -eq 15 ] && echo "       ..." && break
                fi
            done
        else
            echo -e "       ${DIM}No skills defined${NC}"
        fi
        echo ""
        
        # Show HOOKS if enabled
        local hooks_enabled=$(jq -r '.hooks.enabled // false' "$manifest_file" 2>/dev/null)
        if [ "$hooks_enabled" = "true" ]; then
            echo -e "    ${DIM}🔗 Hooks:${NC}"
            local hook_files=$(jq -r '.hooks.configFiles[]? // empty' "$manifest_file" 2>/dev/null)
            if [ -n "$hook_files" ]; then
                echo "$hook_files" | while IFS= read -r hook; do
                    [ -n "$hook" ] && echo -e "       • $(basename "$hook")"
                done
            else
                echo -e "       ${DIM}Enabled but no config files specified${NC}"
            fi
            echo ""
        fi
        
        # Show PERMISSIONS
        local permissions=$(jq -r '.permissions[]? // empty' "$manifest_file" 2>/dev/null)
        if [ -n "$permissions" ]; then
            echo -e "    ${DIM}🔐 Permissions:${NC}"
            echo "$permissions" | head -10 | while IFS= read -r perm; do
                [ -n "$perm" ] && echo -e "       • $perm"
            done
            echo ""
        fi
        
        # Show DEPENDENCIES
        local deps=$(jq -r '.dependencies // {} | to_entries[] | "\(.key): \(.value)"' "$manifest_file" 2>/dev/null)
        if [ -n "$deps" ]; then
            echo -e "    ${DIM}📦 Dependencies:${NC}"
            echo "$deps" | while IFS= read -r dep; do
                [ -n "$dep" ] && echo -e "       • $dep"
            done
            echo ""
        fi
        
        # Show MCP status
        local mcp_enabled=$(jq -r '.mcp.enabled // false' "$manifest_file" 2>/dev/null)
        if [ "$mcp_enabled" = "true" ]; then
            local mcp_config=$(jq -r '.mcp.configFile // ".mcp.json"' "$manifest_file" 2>/dev/null)
            echo -e "    ${DIM}📡 MCP:${NC} Enabled (config: $mcp_config)"
            echo ""
        fi
        
    else
        echo -e "    ${YELLOW}⚠ Plugin details not available${NC}"
        if [ -n "$plugin_path" ]; then
            echo -e "    ${DIM}Path: $plugin_path${NC}"
        fi
        echo -e "    ${DIM}Manifest not found${NC}"
        echo ""
    fi
}

# Function to count capabilities
count_capabilities() {
    local plugin_key="$1"
    local plugin_name="$2"
    local marketplace="$3"
    
    # Get actual install path
    local plugin_path=""
    if [ -f "$INSTALLED_PLUGINS_FILE" ]; then
        plugin_path=$(jq -r ".plugins[\"$plugin_key\"].installPath // empty" "$INSTALLED_PLUGINS_FILE" 2>/dev/null)
    fi
    
    if [ -z "$plugin_path" ] || [ ! -d "$plugin_path" ]; then
        if [ -d "$MARKETPLACES_DIR/$marketplace/sample-plugin" ]; then
            plugin_path="$MARKETPLACES_DIR/$marketplace/sample-plugin"
        fi
    fi
    
    # Find manifest file
    local manifest_file=""
    for mf in "$plugin_path/.claude-plugin/plugin.json" "$plugin_path/plugin.json" "$plugin_path/manifest.json"; do
        if [ -f "$mf" ]; then
            manifest_file="$mf"
            break
        fi
    done
    
    if [ -n "$manifest_file" ] && command_exists jq; then
        local agent_count=0
        local command_count=0
        local skill_count=0
        
        # Count agents
        local agents_dir=$(jq -r '.agents.directory // empty' "$manifest_file" 2>/dev/null)
        if [ -n "$agents_dir" ] && [ -d "$plugin_path/$agents_dir" ]; then
            agent_count=$(find "$plugin_path/$agents_dir" -name "*.md" -o -name "*.yaml" -o -name "*.yml" 2>/dev/null | wc -l)
        fi
        
        # Count commands
        local commands_dir=$(jq -r '.commands.directory // empty' "$manifest_file" 2>/dev/null)
        if [ -n "$commands_dir" ] && [ -d "$plugin_path/$commands_dir" ]; then
            command_count=$(find "$plugin_path/$commands_dir" -name "*.md" -o -name "*.sh" -o -name "*.js" 2>/dev/null | wc -l)
        fi
        
        # Count skills
        local skills_registry_count=$(jq '.skills.registry | length // 0' "$manifest_file" 2>/dev/null)
        skill_count=$skills_registry_count
        
        echo "${GREEN}[$agent_count agents, $command_count commands, $skill_count skills]${NC}"
    else
        echo ""
    fi
}

# Main: List installed plugins
echo -e "${BOLD}Installed Plugins:${NC}"
echo "==================="

if [ -f "$SETTINGS_FILE" ] && command_exists jq; then
    plugins=$(jq -r '.enabledPlugins | to_entries[] | "\(.key)"' "$SETTINGS_FILE" 2>/dev/null)
    
    if [ -n "$plugins" ]; then
        plugin_count=0
        while IFS= read -r plugin_key; do
            plugin_count=$((plugin_count + 1))
            
            # Extract plugin name and marketplace
            plugin_name=$(echo "$plugin_key" | cut -d'@' -f1)
            marketplace=$(echo "$plugin_key" | cut -d'@' -f2)
            
            # Check if enabled
            enabled=$(jq -r ".enabledPlugins[\"$plugin_key\"]" "$SETTINGS_FILE" 2>/dev/null)
            
            if [ "$enabled" = "true" ]; then
                status="${GREEN}✅ Enabled${NC}"
            else
                status="${RED}❌ Disabled${NC}"
            fi
            
            # Get capability summary
            caps=$(count_capabilities "$plugin_key" "$plugin_name" "$marketplace")
            
            echo ""
            echo -e "${BOLD}$plugin_count.${NC} ${BLUE}$plugin_name${NC} @ ${DIM}$marketplace${NC} - $status $caps"
            echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            
            # Get detailed plugin information
            get_plugin_details "$plugin_key" "$plugin_name" "$marketplace"
            
        done <<< "$plugins"
        
        echo -e "${BOLD}Total: $plugin_count plugin(s) installed${NC}"
    else
        echo -e "${YELLOW}No plugins installed${NC}"
        echo ""
        echo "To install a plugin, use:"
        echo "  claude plugin install <plugin-name>"
        echo "  claude plugin install <plugin-name>@<marketplace>"
    fi
else
    if ! command_exists jq; then
        echo -e "${YELLOW}⚠ Install 'jq' for detailed plugin information${NC}"
        echo "  Install: apt/brew/yum install jq"
    fi
    if [ ! -f "$SETTINGS_FILE" ]; then
        echo -e "${YELLOW}No Claude settings file found${NC}"
    fi
fi

echo ""
echo -e "${DIM}────────────────────────────────────────────────────────────${NC}"
echo ""

# Show statistics
if [ -f "$SETTINGS_FILE" ] && command_exists jq; then
    total_plugins=$(jq -r '.enabledPlugins | length' "$SETTINGS_FILE" 2>/dev/null || echo "0")
    enabled_plugins=$(jq -r '.enabledPlugins | to_entries | map(select(.value == true)) | length' "$SETTINGS_FILE" 2>/dev/null || echo "0")
    disabled_plugins=$((total_plugins - enabled_plugins))
    
    echo -e "${BOLD}Statistics:${NC}"
    echo "============"
    echo -e "  ${GREEN}✓${NC} Enabled:  $enabled_plugins"
    echo -e "  ${RED}✗${NC} Disabled: $disabled_plugins" 
    echo -e "  ${BLUE}Σ${NC} Total:    $total_plugins"
    echo ""
fi

# List configured marketplaces
echo -e "${BOLD}Configured Marketplaces:${NC}"
echo "========================"

marketplace_output=$(claude plugin marketplace list 2>&1)

if echo "$marketplace_output" | grep -q "Configured marketplaces:"; then
    echo "$marketplace_output" | tail -n +2 | sed 's/^/  /'
else
    echo -e "  ${YELLOW}No marketplaces configured${NC}"
fi

echo ""

# Show quick commands
echo -e "${BOLD}Quick Commands:${NC}"
echo "==============="
echo -e "  ${DIM}Install:${NC}     claude plugin install <plugin-name>"
echo -e "  ${DIM}Enable:${NC}      claude plugin enable <plugin-name>"
echo -e "  ${DIM}Disable:${NC}     claude plugin disable <plugin-name>"
echo -e "  ${DIM}Uninstall:${NC}   claude plugin uninstall <plugin-name>"
echo -e "  ${DIM}Info:${NC}        claude plugin info <plugin-name>"
echo -e "  ${DIM}Validate:${NC}    claude plugin validate <path>"
echo ""

echo -e "${BOLD}Marketplace Commands:${NC}"
echo "====================="
echo -e "  ${DIM}Add:${NC}         claude plugin marketplace add <source>"
echo -e "  ${DIM}Remove:${NC}      claude plugin marketplace remove <name>"
echo -e "  ${DIM}Update:${NC}      claude plugin marketplace update"
echo -e "  ${DIM}List:${NC}        claude plugin marketplace list"
echo ""

# Show locations
echo -e "${BOLD}Important Locations:${NC}"
echo "===================="
echo -e "  ${DIM}Settings:${NC}     $SETTINGS_FILE"
echo -e "  ${DIM}Plugins:${NC}      $PLUGINS_DIR"
echo -e "  ${DIM}Marketplaces:${NC} $MARKETPLACES_DIR"
echo -e "  ${DIM}Logs:${NC}         $HOME/.claude/logs/"
echo ""

# System check
echo -e "${BOLD}System Check:${NC}"
echo "============="

if command_exists jq; then
    echo -e "  ${GREEN}✓${NC} jq installed (required for detailed info)"
else
    echo -e "  ${RED}✗${NC} jq not installed"
    echo -e "     Install: apt/brew/yum install jq"
fi

claude_version=$(claude --version 2>/dev/null | head -1)
if [ -n "$claude_version" ]; then
    echo -e "  ${GREEN}✓${NC} Claude CLI: $claude_version"
else
    echo -e "  ${YELLOW}⚠${NC} Could not determine Claude CLI version"
fi

if [ -d "$PLUGINS_DIR" ]; then
    if [ -w "$PLUGINS_DIR" ]; then
        echo -e "  ${GREEN}✓${NC} Plugin directory writable"
    else
        echo -e "  ${RED}✗${NC} Plugin directory not writable"
    fi
else
    echo -e "  ${YELLOW}⚠${NC} Plugin directory does not exist yet"
fi

echo ""
echo -e "${DIM}For issues with plugins, use: ./scripts/claude/fix-plugin.sh${NC}"
echo ""