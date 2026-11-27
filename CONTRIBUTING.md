# Contributing

## Branch and pull request

1. Create a feature branch from `main`:

```bash
git checkout main
git pull
git checkout -b feat/your-change
```

2. Make focused changes with tests. Prefer small PRs that explain **why** the change belongs in this repository.

3. Run the suite:

```bash
uv sync --group dev
uv run pytest
```

4. Push and open a pull request:

```bash
git push -u origin HEAD
gh pr create --title "feat: short why" --body "$(cat <<'EOF'
## Summary
- Why this change should land in ucm-mcp

## Test plan
- [ ] uv run pytest
- [ ] Manual Cursor tool smoke test if CUCM-reachable

EOF
)"
```

## Guidelines

- Do not commit `.env` or live CUCM credentials.
- Mutating tools stay behind `UCM_ALLOW_*` gates.
- Prefer mocked HTTP/SOAP in tests; never require a live cluster in CI.
- Keep AXL coverage via `axl_call` discovery rather than one MCP tool per method.
