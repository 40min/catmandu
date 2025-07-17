---
layer: integration
owner: '@catmandu-devs'
version: v1
status: current
created: 2025-07-16
updated: 2025-07-16
tags: [cattackle, mcp, spec, toml]
depends_on: []
referenced_by: []
---
# ARCH-cattackle-spec-v1

## Overview
This document specifies the contract and expected behavior for cattackles within the Catmandu framework. It defines the structure of cattackle configurations, the interface for cattackle implementations, and the communication protocols they adhere to.

## Cattackle Configuration (TOML)
Cattackles are configured using TOML files. The specification defines the required and optional fields within these files, ensuring consistency and enabling dynamic loading.

### Required Fields
- `id`: Unique identifier for the cattackle.
- `name`: Human-readable name of the cattackle.
- `version`: Version of the cattackle.
- `description`: A brief description of the cattackle's functionality.
- `module`: The Python module path to the cattackle implementation.

### Optional Fields
- `tags`: List of tags for categorization.
- `dependencies`: List of other cattackles this cattackle depends on.
- `settings`: Configuration settings specific to the cattackle.

## Cattackle Interface
Cattackle implementations must adhere to a defined interface, allowing the core system to interact with them uniformly. This typically involves methods for initialization, execution, and shutdown.

## MCP Integration
Cattackles that interact with the Model Context Protocol (MCP) must conform to specific integration patterns, ensuring seamless communication with MCP servers and services.

## Evolution
### Planned
- Define a schema for cattackle settings to enforce structure and validation.
- Establish guidelines for versioning cattackles.
