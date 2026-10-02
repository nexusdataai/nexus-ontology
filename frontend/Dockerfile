# ========================================
# Multi-stage Dockerfile for Nexus Telco UI
# Optimized for ECS/EKS/K8s deployment
# ========================================

# ----------------------------------------
# Stage 1: Build Stage
# ----------------------------------------
FROM node:20-alpine AS builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apk add --no-cache \
    python3 \
    make \
    g++ \
    && rm -rf /var/cache/apk/*

# Copy package files for dependency installation
# This layer will be cached unless package files change
COPY package.json package-lock.json ./

# Install dependencies (npm install tolerates lock drift during monorepo migration)
RUN npm install --no-audit --no-fund

# Copy source code
COPY . .

# Build the application for production
RUN npm run build:prod

# Remove development dependencies to reduce size
RUN npm prune --omit=dev

# ----------------------------------------
# Stage 2: Production Stage
# ----------------------------------------
FROM nginx:1.25-alpine AS production

# Security: Create non-root user
RUN addgroup -g 1001 -S nginx-app && \
    adduser -S -D -H -u 1001 -h /var/cache/nginx -s /sbin/nologin -G nginx-app -g nginx-app nginx-app

# Remove default nginx config and html
RUN rm -rf /etc/nginx/conf.d/default.conf /usr/share/nginx/html/*

# Copy custom nginx configuration
COPY --chown=nginx-app:nginx-app nginx.conf /etc/nginx/nginx.conf

# Copy built assets from builder stage
COPY --from=builder --chown=nginx-app:nginx-app /app/dist /usr/share/nginx/html

# Copy MkDocs pre-built site (populated by deploy-app-changes.sh)
COPY --chown=nginx-app:nginx-app docs-site/ /usr/share/nginx/docs/

# Create necessary directories with proper permissions
RUN mkdir -p /var/cache/nginx /var/log/nginx /var/run /tmp && \
    chown -R nginx-app:nginx-app /var/cache/nginx /var/log/nginx /var/run /usr/share/nginx/html /usr/share/nginx/docs /tmp && \
    chmod -R 755 /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/docs && \
    chmod 1777 /tmp

# Security: Remove unnecessary packages and files
RUN apk --no-cache upgrade && \
    rm -rf /var/cache/apk/* /tmp/* /var/tmp/*

# Expose port (non-privileged port)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:8080/ || exit 1

# Switch to non-root user
USER nginx-app

# Start nginx in foreground
CMD ["nginx", "-g", "daemon off;"]

# Labels for metadata
LABEL maintainer="Nexus Team" \
      description="Nexus Telco QA Dashboard - Containerized React UI" \
      version="0.0.1" \
      org.opencontainers.image.source="https://github.com/nexus/qa-dashboard"
