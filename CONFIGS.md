# AgentOS Configuration

AgentOS creates configuration files in two locations to manage both system-wide and project-specific settings.

## Base Configuration (`~/.agent-os/`)

The base configuration directory contains system-wide AgentOS settings:

- `config.yml` - Core AgentOS configuration
- Agent templates and shared resources
- System-wide defaults and preferences

This configuration is shared across all projects and provides the foundation for AgentOS functionality.

## Project Configuration (`.agent-os/`)

Each project can have its own AgentOS configuration directory containing:

- `CLAUDE.md` - Claude Code instructions (if Claude Code integration is enabled)
- `.cursorrules` - Cursor rules file (if Cursor integration is enabled)
- Project-specific agent configurations
- Custom templates and overrides

## Agent Integration Files

### Claude Code Integration
When Claude Code integration is enabled, AgentOS creates:
- `.agent-os/CLAUDE.md` - Project-specific instructions for Claude Code

### Cursor Integration  
When Cursor integration is enabled, AgentOS creates:
- `.agent-os/.cursorrules` - Cursor-specific rules and configurations

## Configuration Management

### Viewing Current Configuration
```bash
# Show current installation status and configuration
agentos version
```

### Updating Configuration
```bash
# Update base configuration
agentos update

# Update project configuration
agentos update --project
```

### Overwriting Configuration
```bash
# Overwrite existing project instructions/configuration
agentos install --project --overwrite-instructions
```

## Project Type Detection

AgentOS automatically detects your project type based on files present in your project directory:

- Presence of `pyproject.toml`, `requirements.txt`, or `setup.py` indicates Python projects
- Presence of `package.json` indicates JavaScript/Node.js projects  
- Presence of `Cargo.toml` indicates Rust projects
- And so on for other supported project types

You can also explicitly specify a project type during installation:
```bash
agentos install --project --project-type python-modern
```