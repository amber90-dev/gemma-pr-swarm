"""Command line / CI usage:  python cli.py https://github.com/owner/repo/pull/123

Writes the final review to review.md. In GitHub Actions it also exposes the
verdict as a step output, and can fail the check (block the merge) if you set
FAIL_ON="LIKELY SPAM" or FAIL_ON="LIKELY SPAM,CHANGES REQUESTED".
"""
import os
import sys

from dotenv import load_dotenv

import swarm

load_dotenv()

if len(sys.argv) < 2:
    sys.exit("Usage: python cli.py <github-pr-url>")

key = os.environ["GEMINI_API_KEY"]
pr = swarm.fetch_pr(sys.argv[1], os.getenv("GITHUB_TOKEN"))
print(f"Reviewing: {pr.title}  (+{pr.additions}/-{pr.deletions})\n")
results = swarm.run_swarm(
    key, pr,
    on_done=lambda r: print(f"{r.emoji} {r.name}: {r.error or f'{r.score}/10 - {r.summary}'}"),
)
verdict = swarm.run_judge(key, pr, results)
v = verdict.get("verdict", "UNKNOWN")

scores = " · ".join(f"{r.emoji} {r.name} {r.score}/10" for r in results if not r.error)
review = (
    f"## 🐝 Gemma PR Swarm verdict: **{v}**\n\n"
    f"<sub>{scores}</sub>\n\n{verdict.get('comment', '')}\n\n"
    f"---\n<sub>Reviewed by a swarm of Gemma 4 agents · "
    f"[Gemma PR Swarm](https://github.com/) · AI review, a human maintainer makes the final call.</sub>\n"
)
with open("review.md", "w", encoding="utf-8") as f:
    f.write(review)
print(f"\n=== VERDICT: {v} ===\n\n{verdict.get('comment', '')}")

if os.getenv("GITHUB_OUTPUT"):
    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        f.write(f"verdict={v}\n")

fail_on = [x.strip() for x in os.getenv("FAIL_ON", "").split(",") if x.strip()]
if v in fail_on:
    sys.exit(f"Failing check because verdict is {v}")
