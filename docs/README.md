# Documentation

This folder holds screenshots, recorded sessions, and longer-form
documentation that would clutter the main README.

## Files

- `banner.png` — the startup banner in a real terminal (placeholder,
  see "Adding a screenshot" below)
- `session.png` — the agent in flight: user asks a question, agent
  calls tools, returns an answer (placeholder)

## Adding a screenshot

The repo ships without screenshots because capturing them requires
running the agent on your machine. To add one:

1. Run `python agent.py` interactively.
2. Press `Win+Shift+S` (Windows) or `Cmd+Shift+4` (macOS) to capture.
3. Save into this folder as `docs/banner.png` or `docs/session.png`.
4. Commit and push.

GitHub renders PNGs inline in the README, so a single image link makes
the project feel concrete to a visitor.

## Why a docs/ folder?

The README is the *first impression* and should be short. Anything
visual or long-form — screenshots, recorded sessions, design notes,
postmortems — lives in `docs/`. This keeps the README scannable and
the visual content one click away.
