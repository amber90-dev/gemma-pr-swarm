# Contributing to Gemma PR Swarm 🐝

Happy Hacktoberfest! (Our own 🎃 Spam Guard agent will review your PR, so make it count.)

## Add a new agent (no Python needed)

Create `agents/<number>_<name>.yaml`:

```yaml
name: Accessibility
emoji: "♿"
needs_image: false   # true = only runs when the user uploads screenshots
instruction: |
  You are an accessibility reviewer. Look for missing alt text, aria labels,
  keyboard traps, and low colour contrast in the changed HTML/JSX/CSS.
```

Restart the app and your agent will join the swarm.

## Agent ideas we'd love

- ♿ Accessibility
- 📦 Dependency & licence checker
- 🌍 i18n / hard-coded strings
- 🗄️ Database migration safety
- 📝 Docs & changelog
- 🐍/☕/🦀 Language-specific experts (Python, Java, Rust, Go…)

## Code ideas

- **GitHub Action:** run the swarm automatically on every PR and post the comment
- Post the review straight to GitHub using the token
- Split huge diffs per file instead of truncating them
- Local mode: run Gemma 4 through Ollama, with no API at all
- Tests for `parse_json` and `fetch_pr`

## How to submit

1. Fork the repo and create a branch
2. Test with `streamlit run app.py` or `python cli.py <pr-url>`
3. Open a PR with a screenshot of your agent's output
