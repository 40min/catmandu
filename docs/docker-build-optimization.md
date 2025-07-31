# Docker Build Optimization Guide

This document outlines the build optimizations implemented for the Catmandu project to achieve maximum cache reuse, minimal image sizes, and fast build times.

## Optimization Strategies

### 1. Multi-Stage Build Architecture

Both Dockerfiles use optimized multi-stage builds:

```
base → deps → development
            → production
```

**Benefits:**

- **Base Stage**: Common system dependencies and user setup
- **Deps Stage**: Isolated dependency installation with aggressive caching
- **Development Stage**: Includes dev tools and volume mount support
- **Production Stage**: Minimal runtime environment

### 2. Layer Caching Optimization

#### Dependency Layer Caching

- Copy dependency files (`pyproject.toml`, `uv.lock`, `requirements.txt`) before source code
- Use cache mounts for package managers: `--mount=type=cache,target=/tmp/uv-cache`
- Install dependencies in separate layers from application code

#### System Dependencies

- Install system packages in single `RUN` command with `--no-install-recommends`
- Clean package cache in same layer: `rm -rf /var/lib/apt/lists/*`
- Separate uv installation for better caching

### 3. Build Cache Mounts

Enable BuildKit cache mounts for package managers:

```dockerfile
RUN --mount=type=cache,target=/tmp/uv-cache \
    uv sync --frozen --no-dev --link-mode=copy
```

**Benefits:**

- Persistent cache across builds
- Faster dependency resolution
- Reduced network usage

### 4. Image Size Optimization

#### Production Stage Optimization

- Copy only virtual environment from deps stage
- Exclude development dependencies
- Use minimal base images (python:3.13-slim)
- Exclude test files and documentation via .dockerignore

#### .dockerignore Optimization

- Exclude test files, documentation, and development tools
- Exclude cache directories and temporary files
- Exclude version control and IDE files

### 5. Development vs Production Targets

#### Development Target Features

- Includes development dependencies
- Volume mount support for live reloading
- Debug logging enabled
- Enhanced error reporting

#### Production Target Features

- Minimal dependencies
- Optimized for size and security
- Health checks enabled
- Production logging levels

## Build Performance Testing

Use the provided script to test build performance:

```bash
./scripts/test-build-performance.sh
```

### Test Categories

1. **Individual Build Tests**: Measure each stage build time
2. **Cache Effectiveness**: Compare cold vs warm cache builds
3. **Incremental Builds**: Test source code change impact
4. **Image Size Analysis**: Compare stage sizes
5. **Docker Compose Performance**: Test multi-service builds

## Build Commands

### Development Build

```bash
# Build development images with cache
docker-compose -f docker-compose.yml -f docker-compose.override.yml build

# Build with BuildKit cache
DOCKER_BUILDKIT=1 docker-compose build
```

### Production Build

```bash
# Build production images
docker-compose build

# Build specific service
docker-compose build catmandu-core
```

### Cache Management

```bash
# Prune build cache
docker builder prune

# View cache usage
docker system df
```

## Performance Metrics

### Expected Build Times (approximate)

| Stage       | Cold Cache | Warm Cache | Incremental |
| ----------- | ---------- | ---------- | ----------- |
| Base        | 30-60s     | 5-10s      | 5-10s       |
| Deps        | 60-120s    | 10-20s     | 10-20s      |
| Production  | 90-150s    | 15-30s     | 20-40s      |
| Development | 100-180s   | 20-40s     | 25-50s      |

### Image Size Targets

| Image       | Target Size | Notes                     |
| ----------- | ----------- | ------------------------- |
| Base        | ~200MB      | Python 3.13 + system deps |
| Production  | ~300-400MB  | Runtime dependencies only |
| Development | ~400-500MB  | Includes dev tools        |

## Optimization Best Practices

### 1. Dockerfile Layer Order

1. System dependencies (rarely change)
2. Package manager setup (rarely change)
3. User creation (rarely change)
4. Dependency files (change occasionally)
5. Dependency installation (change occasionally)
6. Application code (change frequently)

### 2. Cache Mount Usage

- Use cache mounts for package managers (uv, pip, npm)
- Mount to temporary directories that don't persist in final image
- Combine with `--link-mode=copy` for better container performance

### 3. Multi-Architecture Considerations

- Use `--platform` flag for cross-platform builds
- Consider separate Dockerfiles for different architectures if needed
- Test on both amd64 and arm64 platforms

### 4. CI/CD Optimization

- Use registry cache: `--cache-from` and `--cache-to`
- Build stages in parallel where possible
- Use BuildKit for advanced caching features

## Troubleshooting

### Slow Builds

1. Check cache mount configuration
2. Verify layer order optimization
3. Review .dockerignore exclusions
4. Enable BuildKit if not already enabled

### Large Images

1. Review production stage dependencies
2. Check for unnecessary files in final stage
3. Use `docker history` to analyze layer sizes
4. Consider using distroless base images for ultra-minimal size

### Cache Misses

1. Verify dependency files are copied before source code
2. Check for file timestamp changes
3. Review .dockerignore patterns
4. Use `--no-cache` to test clean builds

## Monitoring and Metrics

### Build Performance Monitoring

- Track build times in CI/CD pipeline
- Monitor cache hit rates
- Measure image sizes over time
- Alert on significant performance regressions

### Tools for Analysis

- `docker history <image>` - Analyze layer sizes
- `docker system df` - View cache usage
- `docker buildx du` - BuildKit cache usage
- Build performance testing script

## Future Optimizations

### Potential Improvements

1. **Distroless Images**: Consider distroless base images for production
2. **Multi-Architecture**: Native builds for arm64 and amd64
3. **Registry Cache**: Implement registry-based cache for CI/CD
4. **Dependency Pinning**: More aggressive dependency caching strategies
5. **Build Parallelization**: Parallel builds for independent services

### Experimental Features

- Docker BuildKit experimental features
- Cache import/export for CI/CD
- Remote cache backends
- Build secrets management
