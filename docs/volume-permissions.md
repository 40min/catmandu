# Docker Volume Permissions Guide

## The Problem

When using bind mounts in Docker, permission mismatches can occur between the host filesystem and container processes. This commonly manifests as:

```
Failed to save offset          error=PermissionError(13, 'Permission denied')
```

## Root Cause

- **Container Process**: Runs as `catmandu` user (UID 1000)
- **Host Directory**: Owned by host user (different UID)
- **Bind Mount**: Maps host directory directly into container, preserving host ownership

## Solutions

### Option 1: Fix Host Permissions (Recommended for QNAP)

```bash
# Set correct ownership on host
sudo chown -R 1000:1000 ./.data

# Verify permissions
ls -la ./.data
```

### Option 2: Use Named Volumes (Recommended for Development)

Named volumes are managed by Docker and handle permissions automatically:

```yaml
volumes:
  - update_data:/app/.data # Named volume (good)
  # vs
  - ./.data:/app/.data # Bind mount (can cause issues)
```

### Option 3: Run Container as Host User

```yaml
services:
  catmandu-core:
    user: "${UID}:${GID}" # Use host user ID
```

## Why Bind Mounts Are Used

### QNAP Deployment (`docker-compose.qnap.yaml`)

- **Direct filesystem access** for easier backup/restore
- **NAS integration** with existing backup systems
- **Troubleshooting** - can directly inspect files on host

### Development (`docker-compose.override.yml`)

- **Live code reloading** - changes reflected immediately
- **Debugging** - can edit files with host tools

## Best Practices

1. **Production**: Use named volumes for better security and portability
2. **Development**: Use bind mounts for source code, named volumes for data
3. **QNAP/NAS**: Use bind mounts with proper permissions for data persistence

## Backup Strategies

### Named Volumes

```bash
# Backup named volume
docker run --rm -v catmandu-update-data:/data -v $(pwd):/backup alpine tar czf /backup/update_data_backup.tar.gz -C /data .

# Restore named volume
docker run --rm -v catmandu-update-data:/data -v $(pwd):/backup alpine tar xzf /backup/update_data_backup.tar.gz -C /data
```

### Bind Mounts

```bash
# Already accessible on host filesystem
cp -r ./.data ./backup/data-$(date +%Y%m%d)
```
