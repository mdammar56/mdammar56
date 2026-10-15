"""Rewrites the dynamic sections of README.md (recent repos + recent activity)."""
import json
import os
import re
import urllib.request
from datetime import datetime, timezone

USER = "mdammar56"
README = "README.md"
TOKEN = os.environ.get("GITHUB_TOKEN")
MAX_REPOS = 6
MAX_EVENTS = 8


def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}")
    req.add_header("Accept", "application/vnd.github+json")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def ago(iso):
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    days = (datetime.now(timezone.utc) - dt).days
    if days <= 0:
        return "today"
    if days < 30:
        return f"{days}d ago"
    if days < 365:
        return f"{days // 30}mo ago"
    return f"{days // 365}y ago"


def repos_block():
    repos = api(f"/users/{USER}/repos?sort=pushed&per_page=30&type=owner")
    repos = [r for r in repos if not r["fork"] and r["name"] != USER][:MAX_REPOS]
    if not repos:
        return "_No public repositories yet, stay tuned!_"
    rows = ["| Project | Description | Language | ⭐ | Updated |", "|---|---|---|---|---|"]
    for r in repos:
        desc = (r["description"] or "—").replace("|", "\\|")
        rows.append(
            f"| [**{r['name']}**]({r['html_url']}) | {desc} | {r['language'] or '—'} "
            f"| {r['stargazers_count']} | {ago(r['pushed_at'])} |"
        )
    return "\n".join(rows)


def describe(e):
    repo = e["repo"]["name"]
    link = f"[{repo}](https://github.com/{repo})"
    p, t = e["payload"], e["type"]
    if t == "PushEvent":
        n = len(p.get("commits", [])) or p.get("size", 1)
        return f"⬆️ Pushed {n} commit{'s' if n != 1 else ''} to {link}"
    if t == "CreateEvent":
        return f"🆕 Created {p.get('ref_type', 'repository')} in {link}"
    if t == "PullRequestEvent":
        return f"🔀 {p['action'].capitalize()} a PR in {link}"
    if t == "IssuesEvent":
        return f"🐛 {p['action'].capitalize()} an issue in {link}"
    if t == "WatchEvent":
        return f"⭐ Starred {link}"
    if t == "ForkEvent":
        return f"🍴 Forked {link}"
    return None


def activity_block():
    lines = []
    for e in api(f"/users/{USER}/events/public?per_page=50"):
        text = describe(e)
        if text:
            lines.append(f"- {text} · _{ago(e['created_at'])}_")
        if len(lines) >= MAX_EVENTS:
            break
    return "\n".join(lines) or "_No recent public activity._"


def replace(text, tag, body):
    pat = re.compile(rf"(<!--{tag}:START-->)(.*?)(<!--{tag}:END-->)", re.S)
    return pat.sub(lambda m: f"{m.group(1)}\n{body}\n{m.group(3)}", text)


def main():
    with open(README, encoding="utf-8") as f:
        text = f.read()
    text = replace(text, "RECENT_REPOS", repos_block())
    text = replace(text, "RECENT_ACTIVITY", activity_block())
    stamp = datetime.now(timezone.utc).strftime("%d %b %Y")
    text = re.sub(r"<!--UPDATED-->.*?<!--/UPDATED-->", f"<!--UPDATED-->{stamp}<!--/UPDATED-->", text)
    with open(README, "w", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    main()
