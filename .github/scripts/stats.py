"""Generate stats.svg (GitHub stats card) from the GitHub API."""
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

USER = os.environ.get("GH_USER", "yassinechouk")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = os.environ.get("OUT", "stats.svg")


def gql(query):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "User-Agent": "stats-card"},
    )
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    if "errors" in data:
        sys.exit(f"GraphQL error: {data['errors']}")
    return data["data"]["user"]


def fetch():
    since = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")
    stars, cursor = 0, None
    while True:
        after = f', after: "{cursor}"' if cursor else ""
        u = gql(f"""{{ user(login: "{USER}") {{
            name
            repositories(first: 100, ownerAffiliations: OWNER, isFork: false{after}) {{
              nodes {{ stargazerCount }} pageInfo {{ hasNextPage endCursor }} }}
        }} }}""")
        repos = u["repositories"]
        stars += sum(n["stargazerCount"] for n in repos["nodes"])
        if not repos["pageInfo"]["hasNextPage"]:
            break
        cursor = repos["pageInfo"]["endCursor"]
    u = gql(f"""{{ user(login: "{USER}") {{
        name
        pullRequests {{ totalCount }}
        issues {{ totalCount }}
        repositoriesContributedTo(first: 1, contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]) {{ totalCount }}
        contributionsCollection(from: "{since}") {{ totalCommitContributions }}
    }} }}""")
    return {
        "name": u["name"] or USER,
        "stars": stars,
        "commits": u["contributionsCollection"]["totalCommitContributions"],
        "prs": u["pullRequests"]["totalCount"],
        "issues": u["issues"]["totalCount"],
        "contrib": u["repositoriesContributedTo"]["totalCount"],
    }


def render(s):
    rows = [
        ("Total Stars Earned", s["stars"]),
        ("Total Commits (last year)", s["commits"]),
        ("Total PRs", s["prs"]),
        ("Total Issues", s["issues"]),
        ("Contributed to", s["contrib"]),
    ]
    lines = "".join(
        f'<text x="25" y="{70 + i * 25}" class="l">{label}:</text>'
        f'<text x="260" y="{70 + i * 25}" class="v">{value}</text>'
        for i, (label, value) in enumerate(rows)
    )
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    name = s["name"].replace("&", "&amp;").replace("<", "&lt;")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="400" height="215" viewBox="0 0 400 215" role="img" aria-label="GitHub stats">
<style>
.t{{font:600 18px 'Segoe UI',Ubuntu,sans-serif;fill:#00D9FF}}
.l{{font:600 14px 'Segoe UI',Ubuntu,sans-serif;fill:#C9D1D9}}
.v{{font:600 14px 'Segoe UI',Ubuntu,sans-serif;fill:#C9D1D9}}
.u{{font:11px 'Segoe UI',Ubuntu,sans-serif;fill:#6E7681}}
</style>
<rect x="0.5" y="0.5" width="399" height="214" rx="6" fill="#0D1117" stroke="#0D1117"/>
<text x="25" y="35" class="t">{name}'s GitHub Stats</text>
{lines}
<text x="25" y="203" class="u">Updated {updated}</text>
</svg>
"""


if __name__ == "__main__":
    if os.environ.get("MOCK"):
        stats = {"name": "Yassine Chouk", "stars": 43, "commits": 283, "prs": 7, "issues": 0, "contrib": 3}
    else:
        stats = fetch()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(render(stats))
    print(stats)
