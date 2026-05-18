from langchain_tavily import TavilyExtract, TavilySearch


def make_web_search_tool() -> TavilySearch:
    return TavilySearch(max_results=5)


def make_web_extract_tool() -> TavilyExtract:
    return TavilyExtract(extract_depth="basic")
