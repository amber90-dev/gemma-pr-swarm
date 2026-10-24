"""Command line: python cli.py https://github.com/owner/repo/pull/123"""
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
print(f"\n=== VERDICT: {verdict.get('verdict')} ===\n")
print(verdict.get("comment", ""))
