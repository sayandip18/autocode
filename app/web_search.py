from langchain_tavily import TavilySearch


def make_web_search_tool() -> TavilySearch:
    return TavilySearch(max_results=5)
