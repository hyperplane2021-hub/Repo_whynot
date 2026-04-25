# Repo_whynot

This repo is the v0.3 MVP for a small read-only maintainer history tool.

Guidelines for future agents:

- Keep the app runnable without an LLM API key.
- Preserve evidence metadata in all user-facing answers.
- Keep LLM reasoning inside explicit graph nodes with deterministic fallbacks.
- Do not add write actions against GitHub or remote repositories without an approval gate.
- Keep read-only tools path-safe and bounded.
- Prefer small, testable modules over prompt-only workflows.
