from __future__ import annotations

import base64
import os
import re

import httpx
from langchain_core.tools import tool


_GITHUB_API = "https://api.github.com"


def _parse_repo_url(url: str) -> tuple[str, str]:
    match = re.search(r"github\.com/([^/]+)/([^/?.#]+)", url)
    if not match:
        raise ValueError(f"Cannot parse GitHub repo URL: {url}")
    owner, repo = match.group(1), match.group(2).removesuffix(".git")
    return owner, repo


@tool
async def github_fetch(repo_url: str) -> dict[str, str]:
    """Fetch README and file tree from a GitHub repo URL."""
    return await fetch_repo_info(repo_url)


async def fetch_repo_info(repo_url: str) -> dict[str, str]:
    owner, repo = _parse_repo_url(repo_url)
    token = os.environ["GITHUB_PAT"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    async with httpx.AsyncClient(headers=headers, timeout=30) as client:
        readme_resp, tree_resp = await _fetch_both(client, owner, repo)

    readme = _decode_readme(readme_resp)
    file_tree = _build_tree(tree_resp)
    return {"readme": readme, "file_tree": file_tree}


async def _fetch_both(client: httpx.AsyncClient, owner: str, repo: str):
    import asyncio

    readme_task = client.get(f"{_GITHUB_API}/repos/{owner}/{repo}/readme")
    tree_task = client.get(
        f"{_GITHUB_API}/repos/{owner}/{repo}/git/trees/HEAD",
        params={"recursive": "1"},
    )
    return await asyncio.gather(readme_task, tree_task)


def _decode_readme(resp: httpx.Response) -> str:
    if resp.status_code == 404:
        return "(no README found)"
    resp.raise_for_status()
    data = resp.json()
    content = data.get("content", "")
    return base64.b64decode(content).decode("utf-8", errors="replace")


def _build_tree(resp: httpx.Response) -> str:
    resp.raise_for_status()
    items = resp.json().get("tree", [])
    paths = [item["path"] for item in items if item.get("type") != "commit"]
    return "\n".join(paths)
