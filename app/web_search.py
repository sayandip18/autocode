import httpx
import os

async def web_search(query: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": os.environ["TAVILY_KEY"],
                "query": query,
                "max_results": 5,
                "include_raw_content": True
            }
        )
        return r.json()["results"]  # [{url, title, content}, ...]