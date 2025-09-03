# AgentOS Setup Guide

## Installation

### From PyPI (Recommended)

```bash
pip install agentos
```

### From Source

```bash
git clone https://github.com/buildermethods/agent-os.git
cd agent-os
uv sync --all-extras
uv run agentos --help
```

## Quick Start

### 1. Install Base System

```bash
# Install AgentOS base system (includes core configurations)
agentos install

# Follow the interactive prompt to also install project configuration
```

### 2. Install to Current Project

```bash
# Install AgentOS configuration to current project
agentos install --project --claude-code

# Or with specific project type
agentos install --project --claude-code --project-type python-web
```

### 3. Check Installation Status

```bash
# View current installations and system status
agentos version
```

## Usage

### Installation Commands

#### Install Base System
```bash
# Install base AgentOS configuration to ~/.agent-os/
agentos install
```

#### Install to Project
```bash
# Install to current project directory
agentos install --project

# Install with Claude Code integration
agentos install --project --claude-code

# Install with Cursor integration  
agentos install --project --cursor

# Install with both agents
agentos install --project --claude-code --cursor

# Specify project type explicitly
agentos install --project --project-type python-modern --claude-code

# Overwrite existing files
agentos install --project --claude-code --overwrite-instructions
```

#### Supported Project Types
- `python` - Basic Python projects
- `python-modern` - Modern Python with pyproject.toml
- `python-poetry` - Poetry-managed Python projects  
- `python-uv` - uv-managed Python projects
- `javascript` - Basic JavaScript/Node.js projects
- `javascript-react` - React applications
- `javascript-nextjs` - Next.js applications
- `rust` - Rust projects
- `go` - Go projects
- `java-maven` - Maven-based Java projects
- `java-gradle` - Gradle-based Java projects
- `cpp` - C++ projects
- `web` - Static HTML/CSS/JS projects
- `default` - Generic project type

### Update Commands

```bash
# Update base installation
agentos update

# Update project installation only
agentos update --project
```

### Uninstall Commands

```bash
# Remove base installation
agentos uninstall

# Remove project installation only  
agentos uninstall --project
```

### Version & Status

```bash
# Show version and installation status
agentos version

# Example output:
# 🤖 AgentOS CLI v1.4.3 - Phase 2 Complete
# 
# Base Installation: ✅ Installed (v1.4.3) at /Users/you/.agent-os
# Project Installation: ✅ Installed at /Users/you/project/.agent-os
#   Agents: claude_code, cursor
#   Project Type: python-modern
```