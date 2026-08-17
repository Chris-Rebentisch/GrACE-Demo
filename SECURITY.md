# Security

GrACE-Demo is a local classroom demo. It runs on your machine and talks to exactly one
external service: the cloud LLM vendor you configure. There is no hosted instance.

## Reporting a vulnerability

Please open a GitHub issue titled `security:` **without** exploit details, or use
GitHub's private vulnerability reporting on this repository if enabled. We will follow
up for details privately.

## What to keep in mind when running it

- Your API key lives only in `.env` (gitignored). The `set-api-key.sh` helper never
  echoes it; `GET /api/llm/config` masks it. Do not paste keys into issues or chats.
- ArcadeDB ships with the dev credentials `root` / `gracedev` and binds to loopback only.
  Rotate `ARCADE_PASSWORD` in `.env` before exposing anything beyond localhost.
- The API listens on `localhost:8000` with no admin key by default (`GRACE_ADMIN_KEY`
  empty → localhost-only bypass). Set `GRACE_ADMIN_KEY` and `GRACE_CORS_ORIGINS` if you
  ever bind it to a network interface.
- Documents you process are stored in your local Postgres/ArcadeDB and their text is sent
  to the LLM vendor you chose. Do not feed it documents you are not allowed to process.
- Live mail connectors (Gmail / IMAP / Exchange) are read-only and opt-in.
