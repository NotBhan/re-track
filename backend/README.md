# RE:Track (RefinedEngine Track)

Persistent repository memory, deterministic AST call graphs, architectural summaries, and high-precision context packages for AI coding agents.

## Installation

```bash
pip install retrack-ai
# or with uv:
uv tool install retrack-ai
```

## Quick Start

### 1. Initialize RE:Track
```bash
retrack init
```

### 2. Verify System Health
```bash
retrack health
retrack status
```

### 3. Launch Model Context Protocol (MCP) Server
```bash
retrack mcp
# or dedicated standalone launcher:
retrack-mcp
```

### 4. Headless Repository Indexing & Context
```bash
retrack index /path/to/repo --dataset my-repo
retrack context -q "How does authentication work?" -d my-repo
```
