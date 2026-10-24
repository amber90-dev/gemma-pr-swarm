"""Gemma PR Swarm — Streamlit UI."""
import os

import streamlit as st
from dotenv import load_dotenv

import swarm

load_dotenv()

st.set_page_config(page_title="Gemma PR Swarm", page_icon="🐝", layout="wide")
st.title("🐝 Gemma PR Swarm")
st.caption(
    f"A swarm of **Gemma 4** agents (`{swarm.MODEL}`) reviews any GitHub pull request: "
    "security, performance, tests, readability, and a Hacktoberfest spam guard. "
    "Then a Judge agent cross-checks them all."
)

with st.sidebar:
    api_key = os.getenv("GEMINI_API_KEY") or st.text_input("Gemini API key", type="password")
    gh_token = os.getenv("GITHUB_TOKEN") or st.text_input(
        "GitHub token (optional)", type="password", help="Only needed for private repos or rate limits"
    )
    st.markdown("**Agents in the swarm**")
    for a in swarm.load_agents():
        st.markdown(f"{a.get('emoji','🤖')} {a['name']}" + (" *(needs screenshot)*" if a.get("needs_image") else ""))

url = st.text_input("GitHub Pull Request URL", placeholder="https://github.com/owner/repo/pull/123")
shots = st.file_uploader(
    "Optional: UI screenshots of the change (enables the 👁️ UI Vision agent)",
    type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True,
)

if st.button("Release the swarm 🐝", type="primary", disabled=not (url and api_key)):
    try:
        with st.spinner("Fetching PR from GitHub…"):
            pr = swarm.fetch_pr(url, gh_token or None)
    except Exception as e:
        st.error(f"Could not fetch PR: {e}")
        st.stop()

    st.subheader(f"#{url.rstrip('/').split('/')[-1]} · {pr.title}")
    st.caption(f"by @{pr.author} · {pr.files_changed} files · +{pr.additions} / -{pr.deletions}"
               + (" · diff truncated" if pr.truncated else ""))

    images = [(f.getvalue(), f.type) for f in (shots or [])]
    agents = [a for a in swarm.load_agents() if images or not a.get("needs_image")]

    st.markdown("### 🐝 Agents working in parallel")
    cols = st.columns(len(agents))
    boxes = {}
    for col, a in zip(cols, agents):
        with col:
            boxes[a["name"]] = st.empty()
            boxes[a["name"]].info(f"{a.get('emoji','🤖')} **{a['name']}**\n\nthinking…")

    def show(r):
        box = boxes[r.name]
        if r.error:
            box.error(f"{r.emoji} **{r.name}**\n\nerror: {r.error}")
            return
        msg = f"{r.emoji} **{r.name}** · {r.score}/10\n\n{r.summary}\n\n_{len(r.findings)} findings · {r.seconds}s_"
        (box.success if r.score >= 8 else box.warning if r.score >= 5 else box.error)(msg)

    results = swarm.run_swarm(api_key, pr, images, on_done=show)

    with st.expander("All raw findings"):
        for r in results:
            st.markdown(f"**{r.emoji} {r.name}**")
            for f in r.findings:
                st.markdown(f"- `{f.get('severity','?')}` {f.get('file','')} — {f.get('issue','')}  \n  ➜ {f.get('fix','')}")

    st.markdown("### 👨‍⚖️ Judge (cross-checking every finding)")
    with st.spinner("Judge is removing hallucinations and writing the final review…"):
        verdict = swarm.run_judge(api_key, pr, results)

    v = verdict.get("verdict", "?")
    color = {"MERGE": "green", "CHANGES REQUESTED": "orange", "LIKELY SPAM": "red"}.get(v, "gray")
    st.markdown(f"## :{color}[{v}]")
    c1, c2 = st.columns(2)
    c1.metric("Judge confidence", f"{verdict.get('confidence', '?')}/10")
    c2.metric("Hallucinated / duplicate findings dropped", verdict.get("dropped_findings", 0))

    comment = verdict.get("comment", "")
    st.markdown(comment)
    st.code(comment, language="markdown")
    st.download_button("Download review.md", comment, file_name="review.md")
