---
description: How to push code to GitHub
---

// turbo-all

## Steps

1. Review `AGENTS.md` and update it to reflect any project changes since its last update, if needed.

2. Run linter:
```bash
uv run ruff check .
```

3. Run format check:
```bash
uv run ruff format --check .
```

4. Run tests:
```bash
uv run pytest -v
```

5. Only if all checks pass, push to GitHub:
```bash
git push origin main
```
