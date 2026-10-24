"""
Gemma PR Swarm — the engine.
Fetches a GitHub PR, runs specialist Gemma 4 agents in parallel, then a Judge
agent cross-checks their findings and writes the final review.
"""
from __future__ import annotations

import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

import requests
import yaml
from google import genai
from google.genai import types

ROOT = Path(__file__).parent
MODEL = os.getenv("GEMMA_MODEL", "gemma-4-31b-it")
MAX_DIFF_CHARS = int(os.getenv("MAX_DIFF_CHARS", "60000"))


# ---------------------------------------------------------------- GitHub
@dataclass
class PullRequest:
    url: str
    title: str
    body: str
    author: str
    files_changed: int
    additions: int
    deletions: int
    diff: str
    truncated: bool = False


PR_RE = re.compile(r"github\.com/([^/]+)/([^/]+)/pull/(\d+)")


def fetch_pr(url: str, token: str | None = None) -> PullRequest:
    m = PR_RE.search(url)
    if not m:
        raise ValueError("Paste a link like https://github.com/owner/repo/pull/123")
    owner, repo, num = m.groups()
    api = f"https://api.github.com/repos/{owner}/{repo}/pulls/{num}"
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    meta = requests.get(api, headers=headers, timeout=20)
    meta.raise_for_status()
    meta = meta.json()

    diff = requests.get(api, headers={**headers, "Accept": "application/vnd.github.v3.diff"}, timeout=30)
    diff.raise_for_status()
    text = diff.text
    truncated = len(text) > MAX_DIFF_CHARS

    return PullRequest(
        url=url,
        title=meta.get("title") or "",
        body=meta.get("body") or "",
        author=(meta.get("user") or {}).get("login", "unknown"),
        files_changed=meta.get("changed_files", 0),
        additions=meta.get("additions", 0),
        deletions=meta.get("deletions", 0),
        diff=text[:MAX_DIFF_CHARS],
        truncated=truncated,
    )


# ---------------------------------------------------------------- Agents
def load_agents() -> list[dict]:
    """Every YAML file in agents/ is one agent. Add a file = add an agent."""
    return [yaml.safe_load(f.read_text(encoding="utf-8")) for f in sorted((ROOT / "agents").glob("*.yaml"))]


@dataclass
class AgentResult:
    name: str
    emoji: str
    score: int = 0
    summary: str = ""
    findings: list = field(default_factory=list)
    error: str = ""
    seconds: float = 0.0


AGENT_FORMAT = """
Reply with ONLY a JSON object, no markdown fences:
{"score": <1-10, 10 = no problems in your area>,
 "summary": "<one sentence>",
 "findings": [{"severity": "high|medium|low", "file": "<path or ''>",
               "issue": "<what is wrong>", "fix": "<how to fix>"}]}
Only report problems you can point to in the diff. If nothing is wrong, return an empty findings list.
"""


def pr_context(pr: PullRequest) -> str:
    return (
        f"PR TITLE: {pr.title}\nAUTHOR: {pr.author}\n"
        f"STATS: {pr.files_changed} files, +{pr.additions} / -{pr.deletions}\n"
        f"DESCRIPTION:\n{pr.body[:3000] or '(empty)'}\n\n"
        f"DIFF{' (truncated)' if pr.truncated else ''}:\n{pr.diff}"
    )


def parse_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            return json.loads(m.group(0))
        raise


def call_gemma(client: genai.Client, parts: list, retries: int = 5) -> str:
    for attempt in range(retries):
        try:
            r = client.models.generate_content(model=MODEL, contents=parts)
            return r.text or ""
        except Exception as e:  # free-tier rate limits (429) → back off and retry
            if attempt == retries - 1:
                raise
            wait = 3 * (attempt + 1)
            if any(x in str(e) for x in ("429", "RESOURCE_EXHAUSTED", "500", "INTERNAL", "503", "UNAVAILABLE")):
                wait = 15 * (attempt + 1)
            time.sleep(wait)
    return ""


def run_agent(client, agent: dict, pr: PullRequest, images: list[tuple[bytes, str]]) -> AgentResult:
    start = time.time()
    res = AgentResult(name=agent["name"], emoji=agent.get("emoji", "🤖"))
    try:
        prompt = f"{agent['instruction']}\n{AGENT_FORMAT}\n\n{pr_context(pr)}"
        parts = [types.Part.from_bytes(data=b, mime_type=m) for b, m in images] if agent.get("needs_image") else []
        data = parse_json(call_gemma(client, parts + [prompt]))
        res.score = int(data.get("score", 0))
        res.summary = data.get("summary", "")
        res.findings = data.get("findings", []) or []
    except Exception as e:
        res.error = str(e)[:300]
    res.seconds = round(time.time() - start, 1)
    return res


def run_swarm(api_key: str, pr: PullRequest, images=None, on_done=None) -> list[AgentResult]:
    """Run all specialist agents in parallel. on_done(result) is called as each finishes."""
    images = images or []
    client = genai.Client(api_key=api_key)
    agents = [a for a in load_agents() if images or not a.get("needs_image")]
    results = []
    workers = int(os.getenv("SWARM_WORKERS", "3"))  # free tier: ~3 parallel calls is safe
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = []
        for i, a in enumerate(agents):
            futures.append(pool.submit(run_agent, client, a, pr, images))
            time.sleep(1.5)  # stagger starts so they don't all hit the API in the same second
        for f in as_completed(futures):
            r = f.result()
            results.append(r)
            if on_done:
                on_done(r)
    return results


# ---------------------------------------------------------------- Judge
JUDGE_PROMPT = """You are the JUDGE of a code-review swarm. Specialist agents reviewed a
GitHub pull request. Your job:
1. CROSS-CHECK every finding against the diff. Drop findings that are not
   supported by the diff (hallucinations) or are duplicates.
2. Decide ONE verdict: "MERGE", "CHANGES REQUESTED", or "LIKELY SPAM".
3. Write a friendly, encouraging GitHub review comment in Markdown for the PR author
   (the author may be a first-time contributor). Use headings, a short summary,
   a checklist of required fixes (most important first), and optional nice-to-haves.

Reply with ONLY a JSON object, no markdown fences:
{"verdict": "...", "confidence": <1-10>, "dropped_findings": <number>,
 "comment": "<markdown review comment>"}

SPECIALIST REPORTS:
{reports}

{context}
"""


def run_judge(api_key: str, pr: PullRequest, results: list[AgentResult]) -> dict:
    client = genai.Client(api_key=api_key)
    reports = json.dumps(
        [{"agent": r.name, "score": r.score, "summary": r.summary, "findings": r.findings}
         for r in results if not r.error],
        ensure_ascii=False, indent=1,
    )
    prompt = JUDGE_PROMPT.replace("{reports}", reports).replace("{context}", pr_context(pr))
    text = call_gemma(client, [prompt])
    try:
        return parse_json(text)
    except Exception:
        return {"verdict": "CHANGES REQUESTED", "confidence": 0, "dropped_findings": 0, "comment": text}
