AUTOCODE

An AI research assistant with github and web retrieval capabilities

Version v0 flow

User Query
↓
Intent Parser (is this a web task or GitHub task?)
↓
Retriever (fetch raw content)
↓
Context Builder (chunk + trim to fit context window)
↓
LLM (synthesize answer)
↓
Response with sources

Command to run (w/o Docker)

.\venv\Scripts\uvicorn app.main:app --reload
