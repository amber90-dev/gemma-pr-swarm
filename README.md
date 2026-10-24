# 🐝 Gemma PR Swarm

**A swarm of Gemma 4 agents that reviews GitHub pull requests: free, open source, and built for Hacktoberfest maintainers.**

## The problem

Every October, open-source maintainers get flooded with pull requests. Many come from first-time contributors who deserve kind, useful feedback. Many others are low-effort spam, like a whitespace change or a name added to a list. Reviewing them all by hand burns maintainers out.

AI review tools do exist, but most are **paid, closed-source, send your code to someone else's servers, and rely on one AI's single opinion**.

## The solution

Paste a PR link and a **swarm of specialist Gemma 4 agents** reviews it **in parallel**:

| Agent | Looks for |
|---|---|
| 🔒 Security | secrets, injection, XSS, unsafe code |
| ⚡ Performance | N+1 queries, slow loops, heavy dependencies |
| 🧪 Tests | missing tests and edge cases |
| 📖 Readability | naming, duplication, dead code |
| 🎃 Hacktoberfest Spam Guard | low-effort or spam PRs |
| 👁️ UI Vision | *(multimodal)* checks screenshots of the change for broken layouts |

Then a **👨‍⚖️ Judge agent** cross-checks every finding against the diff, **drops hallucinated or duplicate findings**, gives a verdict (**MERGE / CHANGES REQUESTED / LIKELY SPAM**), and writes a friendly GitHub review comment that's ready to paste.

## 🧠 How Gemma 4 does the work

All the reviewing is done by **Gemma 4** (`gemma-4-31b-it`) through the Gemini API:

- **Reasoning over code:** each agent reads the diff with its own expert instructions
- **Multimodal:** the UI Vision agent reads screenshots and compares them with the code
- **Self-checking:** the Judge is Gemma 4 too. It verifies the other agents' claims, which makes the result more reliable than a single model call
- **Why Gemma 4 for a swarm?** A swarm makes 6–7 model calls per review. Gemma 4 is **open-weights and affordable**, so multi-agent review becomes practical for small projects. It can even run fully on your own machine, so private code never has to leave it.

The engine is in [`swarm.py`](swarm.py). Look at `run_swarm()` (parallel agents) and `run_judge()` (cross-check).

## 🚀 Quick start

```bash
git clone https://github.com/<your-username>/gemma-pr-swarm.git && cd gemma-pr-swarm
pip install -r requirements.txt
cp .env.example .env          # add your free key from https://aistudio.google.com
streamlit run app.py          # web UI
python cli.py https://github.com/owner/repo/pull/123   # or the command line
```

## 🧩 Add your own agent in 30 seconds

Every agent is one YAML file in [`agents/`](agents/):

```yaml
name: Accessibility
emoji: "♿"
instruction: |
  You are an accessibility reviewer. Look for missing alt text and aria labels...
```

You don't need to change any Python. See [CONTRIBUTING.md](CONTRIBUTING.md) for agent ideas. **Hacktoberfest PRs are welcome!**

## 🗺️ Roadmap

- [ ] GitHub Action that auto-reviews every new PR
- [ ] Post the review to GitHub directly
- [ ] Run fully local with Gemma 4 + Ollama
- [ ] Per-file review for very large PRs

## 📜 License

[MIT](LICENSE). Built at **Hacktoberfest Hack Day Karachi × AWS User Community 2026** by Amber Abbasi ([IRT Solutions](https://irt.solutions)).
