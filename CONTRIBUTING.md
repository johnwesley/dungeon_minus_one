# Contributing to Dungeon Minus One

Thanks for your interest in contributing! This guide will help you get started.

## Quick Start

```bash
git clone https://github.com/johnwesley/dungeon_minus_one.git
cd dungeon_minus_one
make setup
make db-up
cp .env.example .env  # Add your ANTHROPIC_API_KEY
make dev-full          # Backend + frontend with hot reload
```

Access at `http://localhost:5173`.

## What to Contribute

- **Bug fixes** - Found something broken? Fix it!
- **New locations** - Add JSON files to `data/locations/`
- **New skills** - Add game mechanics in `skills/`
- **Frontend improvements** - UI/UX enhancements in `frontend/`
- **Documentation** - Improve clarity or fill gaps

## Pull Request Process

1. **Branch** from `main`
2. **Test** locally with `make dev-full`
3. **Run** `make verify-movement` if you touched game logic or locations
4. **Submit** a PR with a clear description of what and why
5. **Respond** to any review feedback

## Code Style

- Follow existing patterns in the codebase
- Keep changes focused — one concern per PR
- See `CLAUDE.md` and `app/CLAUDE.md` for architecture details

## Code of Conduct

This project follows the [Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you are expected to uphold this code. Report issues via [GitHub Issues](https://github.com/johnwesley/dungeon_minus_one/issues).

## Questions?

Open an issue — happy to help!
