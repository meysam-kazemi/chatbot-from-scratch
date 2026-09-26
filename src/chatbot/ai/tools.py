import json
import os
import subprocess
import urllib.request
import uuid
from pathlib import Path
from typing import TypedDict

from langchain.tools import ToolRuntime, tool
from psycopg_pool import AsyncConnectionPool

from chatbot.config import settings
from chatbot.repositories import conversations


class ToolContext(TypedDict):
    user_id: str
    conversation_id: str
    db: AsyncConnectionPool


def _workspace(context: ToolContext) -> Path:
    root = Path(settings.tool_workspace).resolve()
    workspace = root / context["user_id"] / context["conversation_id"]
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def _safe_path(workspace: Path, path: str) -> Path:
    if not path or Path(path).is_absolute():
        raise ValueError("Use a non-empty relative path")
    resolved = (workspace / path).resolve()
    if not resolved.is_relative_to(workspace):
        raise ValueError("Path must stay inside the conversation workspace")
    return resolved


@tool
def web_search(query: str) -> str:
    """Search the web for current information and return sourced results."""
    query = query.strip()
    if not query or len(query) > 500:
        return "Search queries must contain between 1 and 500 characters."
    if not settings.tavily_api_key:
        return "Web search is unavailable: TAVILY_API_KEY is not configured."
    request = urllib.request.Request(
        "https://api.tavily.com/search",
        data=json.dumps(
            {
                "api_key": settings.tavily_api_key,
                "query": query,
                "search_depth": "basic",
                "max_results": 5,
            }
        ).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            results = json.load(response).get("results", [])
    except Exception as exc:
        return f"Web search failed: {exc}"
    return "\n\n".join(
        f"{item['title']}\n{item['url']}\n{item.get('content', '')}"
        for item in results
    ) or "No results found."


@tool
def run_python(code: str) -> str:
    """Run Python code in an isolated container without network access."""
    if len(code) > 50_000:
        return "Python code exceeds the 50,000 character limit."
    command = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "--read-only",
        "--memory",
        "128m",
        "--cpus",
        "0.5",
        "--pids-limit",
        "64",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=32m,mode=1777",
        "--tmpfs",
        "/workspace:rw,nosuid,size=32m,mode=1777",
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "--workdir",
        "/workspace",
        settings.python_image,
        "python",
        "-I",
        "-c",
        code,
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=settings.python_timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return f"Python execution timed out after {settings.python_timeout_seconds}s."
    except OSError as exc:
        return f"Python execution is unavailable: {exc}"
    output = (result.stdout + result.stderr).strip()
    return (output or f"Process exited with code {result.returncode}.")[-20_000:]


@tool
def read_file(path: str, runtime: ToolRuntime[ToolContext]) -> str:
    """Read a UTF-8 text file from this conversation's private workspace."""
    try:
        with _safe_path(_workspace(runtime.context), path).open() as source:
            content = source.read(100_001)
        if len(content) > 100_000:
            return content[:100_000] + "\n[truncated]"
        return content
    except (OSError, UnicodeError, ValueError) as exc:
        return f"Could not read file: {exc}"


@tool
def write_file(
    path: str, content: str, runtime: ToolRuntime[ToolContext]
) -> str:
    """Create or replace a UTF-8 text file in this conversation's workspace."""
    if len(content) > 100_000:
        return "Could not write file: content exceeds 100,000 characters."
    try:
        destination = _safe_path(_workspace(runtime.context), path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content)
        return f"Wrote {len(content)} characters to {path}."
    except (OSError, UnicodeError, ValueError) as exc:
        return f"Could not write file: {exc}"


@tool
async def rename_conversation(
    title: str, runtime: ToolRuntime[ToolContext]
) -> str:
    """Rename the current conversation when the user asks for a new title."""
    title = title.strip()
    if not title or len(title) > 100:
        return "The title must contain between 1 and 100 characters."
    context = runtime.context
    conversation = await conversations.update(
        context["db"],
        uuid.UUID(context["conversation_id"]),
        uuid.UUID(context["user_id"]),
        title,
    )
    if conversation:
        return f'Conversation renamed to "{title}".'
    return "Conversation not found."


assistant_tools = [
    web_search,
    run_python,
    read_file,
    write_file,
    rename_conversation,
]
