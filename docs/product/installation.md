# RE:Track Installation Guide

**Document Type**: Product Installation & Setup Guide  
**Version**: 0.1.0 (Phase 9B Release Baseline)  

---

## 1. System Requirements

- **Python**: `>=3.11, <3.14` (Python 3.12 recommended)
- **Operating Systems**: Linux (x86_64, aarch64), macOS (Apple Silicon / Intel), Windows 11 (x64)
- **RAM**: Minimum 8GB (Recommended 16GB)
- **Storage**: ~500MB for core application and local SQLite/Kùzu metadata

---

## 2. Installation Methods

### Method A: Pip / Wheel Installation (Recommended for End-Users)

```bash
# Install the built wheel
pip install retrack-ai

# Or with uv tool:
uv tool install retrack-ai
```

### Method B: Developer Mode (Editable Install from Git Repository)

```bash
# Clone the repository
git clone https://github.com/NotBhan/re-track.git
cd re-track/backend

# Create virtual environment and install in editable mode
uv sync
uv pip install -e .
```

---

## 3. First-Run Bootstrap & Initialization

After installing `retrack-ai`, run the initialization command to configure local storage and verify provider connectivity:

```bash
retrack init
```

### What `retrack init` does:
1. Creates the canonical storage root at `~/.retrack/`.
2. Initializes subdirectories:
   - `~/.retrack/manifests/` (cached AST architectural manifests)
   - `~/.retrack/cache/` (AST fingerprints & context chunk hashes)
   - `~/.retrack/backups/` (automated pre-migration & pre-reset snapshots)
   - `~/.retrack/logs/` (runtime diagnostic logs)
3. Creates default configuration (`~/.retrack/settings.json`), repository store (`~/.retrack/indexed_repos.json`), and package store (`~/.retrack/context_packages.json`).
4. Non-destructively preserves any existing user files.
5. Checks local LLM provider connectivity (Ollama / LM Studio on `localhost:11434`).
6. Detects legacy `~/.andes/` data and alerts you if migration is available.

---

## 4. Configuring MCP in AI Coding Agents

RE:Track exposes a standard Model Context Protocol (MCP) server over standard I/O (JSON-RPC).

### Claude Desktop Configuration (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "retrack": {
      "command": "retrack-mcp",
      "args": [],
      "env": {
        "RETRACK_WORKSPACE_ROOTS": "/path/to/your/projects"
      }
    }
  }
}
```

### Cursor MCP Configuration

Add a new MCP server in Cursor settings:
- **Name**: `retrack`
- **Type**: `command`
- **Command**: `retrack-mcp`

### Python Module Syntax (Alternative)

If using a specific virtual environment:
```json
{
  "mcpServers": {
    "retrack": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "app.mcp"],
      "env": {
        "RETRACK_WORKSPACE_ROOTS": "/path/to/your/projects"
      }
    }
  }
}
```

---

## 5. Verification Commands

Verify that the CLI and MCP server are operating correctly:

```bash
# Check version
retrack --version

# Check system health
retrack health

# Check configuration status
retrack status
```
