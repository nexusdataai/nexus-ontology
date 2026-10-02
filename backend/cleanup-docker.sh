#!/bin/bash

#==============================================================================
# AI Job Engine - Docker Environment Cleanup Script
#==============================================================================
# This script provides comprehensive cleanup of Docker containers and images
# related to the AI Job Engine project. Use this to clean up your Docker
# environment before rebuilding or when troubleshooting issues.
#==============================================================================

# Don't exit on error to handle cleanup gracefully

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
CONTAINER_NAME="ai-job-engine"
IMAGE_NAME="ai-job-engine"
IMAGE_TAG="latest"
NETWORK_NAME="ai-job-engine-network"  # If using custom network

# Default options
CLEAN_IMAGES=${CLEAN_IMAGES:-false}
CLEAN_VOLUMES=${CLEAN_VOLUMES:-false}
CLEAN_ALL=${CLEAN_ALL:-false}
FORCE=${FORCE:-false}
QUIET=${QUIET:-false}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --images)
            CLEAN_IMAGES=true
            shift
            ;;
        --volumes)
            CLEAN_VOLUMES=true
            shift
            ;;
        --all)
            CLEAN_ALL=true
            CLEAN_IMAGES=true
            CLEAN_VOLUMES=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --quiet|-q)
            QUIET=true
            shift
            ;;
        --help|-h)
            echo "AI Job Engine Docker Cleanup Script"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --images    Also remove Docker images"
            echo "  --volumes   Also remove Docker volumes"
            echo "  --all       Remove everything (containers, images, volumes)"
            echo "  --force     Force removal without confirmation"
            echo "  --quiet,-q  Minimal output"
            echo "  --help,-h   Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  CONTAINER_NAME  Container name to clean (default: ai-job-engine)"
            echo "  IMAGE_NAME      Image name to clean (default: ai-job-engine)"
            echo ""
            echo "Examples:"
            echo "  $0                    # Clean containers only"
            echo "  $0 --images           # Clean containers and images"
            echo "  $0 --all              # Clean everything"
            echo "  $0 --force --quiet    # Force clean with minimal output"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Function to print colored output
print_color() {
    local color=$1
    local message=$2
    if [ "$QUIET" != "true" ]; then
        echo -e "${color}${message}${NC}"
    fi
}

# Function to print section headers
print_header() {
    local title=$1
    if [ "$QUIET" != "true" ]; then
        echo ""
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${BLUE}  ${title}${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    fi
}

# Function to confirm action
confirm_action() {
    local message=$1
    if [ "$FORCE" = "true" ]; then
        return 0
    fi
    
    echo -e "${YELLOW}${message}${NC}"
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_color $YELLOW "Cancelled by user"
        exit 0
    fi
}

# Count statistics
count_containers=0
count_removed=0
count_orphaned=0
count_images_removed=0
count_volumes_removed=0
size_freed="0B"

# Main cleanup starts here
print_color $CYAN "🧹 AI Job Engine Docker Cleanup Tool"
print_color $CYAN "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Get initial disk usage
if command -v docker &> /dev/null; then
    initial_usage=$(docker system df --format "{{.Size}}" | head -1 2>/dev/null || echo "0B")
fi

# Step 1: Stop running containers
print_header "Stopping Running Containers"

# Find all running containers with our name pattern
running_containers=$(docker ps -q -f name=$CONTAINER_NAME 2>/dev/null || true)
if [ ! -z "$running_containers" ]; then
    print_color $YELLOW "Found running containers:"
    if [ "$QUIET" != "true" ]; then
        docker ps -f name=$CONTAINER_NAME --format "table {{.ID}}\t{{.Names}}\t{{.Status}}" 2>/dev/null || true
    fi
    
    if [ "$FORCE" != "true" ] && [ "$QUIET" != "true" ]; then
        confirm_action "Stop these containers?"
    fi
    
    while IFS= read -r container_id; do
        if [ ! -z "$container_id" ]; then
            container_name=$(docker inspect --format='{{.Name}}' $container_id | sed 's/^\/\+//')
            print_color $CYAN "  Stopping container: $container_name ($container_id)"
            docker stop $container_id > /dev/null 2>&1 || true
            count_containers=$((count_containers + 1))
        fi
    done <<< "$running_containers"
    
    print_color $GREEN "✅ Stopped $count_containers running container(s)"
else
    print_color $BLUE "ℹ️  No running containers found"
fi

# Step 2: Remove all containers (stopped and running)
print_header "Removing Containers"

all_containers=$(docker ps -aq -f name=$CONTAINER_NAME 2>/dev/null || true)
if [ ! -z "$all_containers" ]; then
    print_color $YELLOW "Found containers to remove:"
    if [ "$QUIET" != "true" ]; then
        docker ps -a -f name=$CONTAINER_NAME --format "table {{.ID}}\t{{.Names}}\t{{.Status}}" 2>/dev/null || true
    fi
    
    if [ "$FORCE" != "true" ] && [ "$QUIET" != "true" ]; then
        confirm_action "Remove these containers?"
    fi
    
    count_removed=0
    while IFS= read -r container_id; do
        if [ ! -z "$container_id" ]; then
            container_name=$(docker inspect --format='{{.Name}}' $container_id 2>/dev/null | sed 's/^\/\+//' || echo "unknown")
            print_color $CYAN "  Removing container: $container_name ($container_id)"
            docker rm -f $container_id > /dev/null 2>&1 || true
            count_removed=$((count_removed + 1))
        fi
    done <<< "$all_containers"
    
    print_color $GREEN "✅ Removed $count_removed container(s)"
else
    print_color $BLUE "ℹ️  No containers to remove"
fi

# Step 3: Clean up orphaned containers (containers from our image but with different names)
print_header "Cleaning Orphaned Containers"

orphaned=$(docker ps -aq -f ancestor=$IMAGE_NAME:$IMAGE_TAG --no-trunc 2>/dev/null || true)
if [ ! -z "$orphaned" ]; then
    count_orphaned=0
    print_color $YELLOW "Found orphaned containers from $IMAGE_NAME:$IMAGE_TAG"
    
    while IFS= read -r container_id; do
        if [ ! -z "$container_id" ]; then
            container_name=$(docker inspect --format='{{.Name}}' $container_id 2>/dev/null | sed 's/^\/\+//' || echo "unknown")
            # Skip if it's our main container (already handled)
            if [ "$container_name" != "$CONTAINER_NAME" ]; then
                print_color $CYAN "  Removing orphaned: $container_name ($container_id)"
                docker rm -f $container_id > /dev/null 2>&1 || true
                count_orphaned=$((count_orphaned + 1))
            fi
        fi
    done <<< "$orphaned"
    
    if [ $count_orphaned -gt 0 ]; then
        print_color $GREEN "✅ Removed $count_orphaned orphaned container(s)"
    else
        print_color $BLUE "ℹ️  No orphaned containers to remove"
    fi
else
    print_color $BLUE "ℹ️  No orphaned containers found"
fi

# Step 4: Remove Docker images (optional)
if [ "$CLEAN_IMAGES" = "true" ]; then
    print_header "Removing Docker Images"
    
    images=$(docker images -q $IMAGE_NAME 2>/dev/null || true)
    if [ ! -z "$images" ]; then
        print_color $YELLOW "Found images to remove:"
        docker images $IMAGE_NAME --format "table {{.Repository}}:{{.Tag}}\t{{.ID}}\t{{.Size}}" 2>/dev/null || true
        
        if [ "$FORCE" != "true" ] && [ "$QUIET" != "true" ]; then
            confirm_action "Remove these images?"
        fi
        
        count_images_removed=0
        while IFS= read -r image_id; do
            if [ ! -z "$image_id" ]; then
                print_color $CYAN "  Removing image: $image_id"
                docker rmi -f $image_id > /dev/null 2>&1 || true
                count_images_removed=$((count_images_removed + 1))
            fi
        done <<< "$images"
        
        print_color $GREEN "✅ Removed $count_images_removed image(s)"
        
        # Also clean up dangling images
        dangling=$(docker images -f "dangling=true" -q 2>/dev/null || true)
        if [ ! -z "$dangling" ]; then
            print_color $CYAN "  Removing dangling images..."
            docker rmi $dangling > /dev/null 2>&1 || true
            print_color $GREEN "✅ Removed dangling images"
        fi
    else
        print_color $BLUE "ℹ️  No images to remove"
    fi
fi

# Step 5: Remove Docker volumes (optional)
if [ "$CLEAN_VOLUMES" = "true" ]; then
    print_header "Removing Docker Volumes"
    
    # Look for volumes with our container name pattern
    volumes=$(docker volume ls -q -f name=$CONTAINER_NAME 2>/dev/null || true)
    if [ ! -z "$volumes" ]; then
        print_color $YELLOW "Found volumes to remove:"
        docker volume ls -f name=$CONTAINER_NAME 2>/dev/null || true
        
        if [ "$FORCE" != "true" ] && [ "$QUIET" != "true" ]; then
            confirm_action "Remove these volumes? (This will delete all data!)"
        fi
        
        count_volumes_removed=0
        while IFS= read -r volume_name; do
            if [ ! -z "$volume_name" ]; then
                print_color $CYAN "  Removing volume: $volume_name"
                docker volume rm -f $volume_name > /dev/null 2>&1 || true
                count_volumes_removed=$((count_volumes_removed + 1))
            fi
        done <<< "$volumes"
        
        print_color $GREEN "✅ Removed $count_volumes_removed volume(s)"
    else
        print_color $BLUE "ℹ️  No volumes to remove"
    fi
fi

# Step 6: Clean up networks (if any custom networks)
print_header "Cleaning Networks"

custom_networks=$(docker network ls -q -f name=$NETWORK_NAME 2>/dev/null || true)
if [ ! -z "$custom_networks" ]; then
    print_color $CYAN "  Removing custom networks..."
    docker network rm $NETWORK_NAME > /dev/null 2>&1 || true
    print_color $GREEN "✅ Removed custom network"
else
    print_color $BLUE "ℹ️  No custom networks to remove"
fi

# Step 7: Optional system prune
if [ "$CLEAN_ALL" = "true" ]; then
    print_header "System Prune"
    
    if [ "$FORCE" != "true" ] && [ "$QUIET" != "true" ]; then
        confirm_action "Run Docker system prune? (This removes all unused data)"
    fi
    
    print_color $CYAN "  Running Docker system prune..."
    if [ "$FORCE" = "true" ]; then
        docker system prune -af --volumes > /dev/null 2>&1
    else
        docker system prune -a --volumes
    fi
    print_color $GREEN "✅ System prune completed"
fi

# Calculate space freed
if command -v docker &> /dev/null; then
    final_usage=$(docker system df --format "{{.Size}}" | head -1 2>/dev/null || echo "0B")
    # Note: This is a simplified calculation
    print_header "Cleanup Summary"
    print_color $GREEN "✨ Cleanup completed successfully!"
    print_color $BLUE "  • Containers stopped: $count_containers"
    total_removed=$((count_removed + count_orphaned))
    print_color $BLUE "  • Containers removed: $total_removed"
    if [ "$CLEAN_IMAGES" = "true" ]; then
        print_color $BLUE "  • Images removed: $count_images_removed"
    fi
    if [ "$CLEAN_VOLUMES" = "true" ]; then
        print_color $BLUE "  • Volumes removed: $count_volumes_removed"
    fi
fi

# Show next steps
print_header "Next Steps"
print_color $CYAN "You can now:"
print_color $BLUE "  • Rebuild: ./rebuild-and-test.sh"
print_color $BLUE "  • Start fresh: docker run -d --name $CONTAINER_NAME -p 8000:8000 $IMAGE_NAME:$IMAGE_TAG"
print_color $BLUE "  • Check status: docker ps -a | grep $CONTAINER_NAME"

# Exit successfully
exit 0
