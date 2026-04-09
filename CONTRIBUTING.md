# Contributing to AI News Radar

Thank you for your interest in contributing!

## How to Contribute

1. **Open an issue first** — Describe what you'd like to add or fix before submitting a PR
2. **Fork the repository** and create a branch from `main`
3. **Make your changes** with clear, focused commits
4. **Run tests** before submitting:
   ```bash
   cd backend && pytest          # 84+ tests
   cd dashboard && npm test      # 17+ tests
   ```
5. **Submit a Pull Request** with a clear description of what changed and why

## Development Setup

See [README.md](README.md) — Option B (Local Dev) for setup instructions.

## Areas Where Help Is Welcome

- Additional data sources (official AI changelogs, newsletters)
- Improving relevance scoring accuracy
- Dashboard UI improvements
- Documentation and translations
- Bug reports and reproducible test cases

## Code Style

- Python: follow existing conventions, run `ruff` if available
- TypeScript: follow existing ESLint config (`eslint-config-next`)
- Keep functions small and focused
- Add tests for new functionality
