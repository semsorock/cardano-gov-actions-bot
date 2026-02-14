---
description: How to push code to GitHub
---

// turbo-all

## Steps

1. Run linter:
```bash
uv run ruff check .
```

2. Run format check:
```bash
uv run ruff format --check .
```

3. Run tests:
```bash
uv run pytest -v
```

4. Only if all checks pass, push to GitHub:
```bash
git push origin main
```
