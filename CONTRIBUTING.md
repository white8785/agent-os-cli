# Contributing to AgentOS

We welcome contributions to AgentOS! This document outlines the process for contributing to the project.

## Getting Started

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Run the test suite: `make pre-ci`
5. Commit your changes: `git commit -m 'Add amazing feature'`
6. Push to the branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

## Development Setup

See [DEV.md](DEV.md) for detailed development environment setup instructions.

## Code Quality Requirements

Before submitting a pull request, ensure your code meets these standards:

- **Type Safety**: 100% mypy coverage required
- **Test Coverage**: >90% test coverage required  
- **Code Style**: Black formatting and Ruff linting required
- **Security**: All user inputs validated, safe subprocess execution

Run `make pre-ci` to verify all requirements are met.

## Testing

All new features and bug fixes should include appropriate tests. Run the full test suite with:

```bash
make test
```

For coverage reports:

```bash
make coverage
```

## Submitting Changes

1. Ensure all tests pass
2. Update documentation if needed
3. Add a clear commit message describing your changes
4. Submit a pull request with a detailed description

## Support

- 📋 Report bugs and request features: [GitHub Issues](https://github.com/buildermethods/agent-os/issues)
- 💬 Get help: [GitHub Discussions](https://github.com/buildermethods/agent-os/discussions)
- 📧 Contact: brian@buildermethods.com