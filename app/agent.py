from __future__ import annotations

import importlib
import inspect
import logging
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI

from app.config import settings

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@dataclass(frozen=True)
class ToolSpec:
    name: str
    docstring: str


INTEGRATIONS_PACKAGE = "app.integrations"
INTEGRATIONS_DIR = Path(__file__).parent / "integrations"


def parse_tool_spec(func) -> ToolSpec:
    doc = inspect.getdoc(func) or ""
    cleaned_doc = "\n".join(line.rstrip() for line in doc.splitlines()) if doc else ""
    if not cleaned_doc:
        cleaned_doc = f"{func.__name__}: No description"
    return ToolSpec(name=func.__name__, docstring=cleaned_doc)


def discover_tools_and_specs() -> tuple[list[Any], list[ToolSpec]]:
    tools: list[Any] = []
    specs: list[ToolSpec] = []

    if not INTEGRATIONS_DIR.exists():
        logger.warning("Integrations directory not found: %s", INTEGRATIONS_DIR)
        return tools, specs

    for path in sorted(INTEGRATIONS_DIR.glob("*.py")):
        if path.name.startswith("__"):
            continue

        module_name = f"{INTEGRATIONS_PACKAGE}.{path.stem}"
        try:
            module = importlib.import_module(module_name)
        except Exception:
            logger.exception("Failed to import module %s", module_name)
            continue

        for _, func in inspect.getmembers(module, inspect.isfunction):
            if not func.__name__.startswith("tool_"):
                continue

            tools.append(func)
            specs.append(parse_tool_spec(func))
            logger.info("Discovered tool %s from %s", func.__name__, module_name)

    return tools, specs


def build_system_prompt(tool_specs: list[ToolSpec]) -> str:
    tools_block = [spec.docstring for spec in tool_specs]

    return (
        "You are a local AI assistant orchestrator inspired by deepagents.\n"
        "You MUST select tools only from the provided tool registry.\n"
        "For each user request, choose tools by their description and args schema, call them when needed, then produce the final user-facing reply.\n"
        "Never output planning JSON, tool call plans, or internal chain-of-thought.\n"
        "Always return a plain, concise final answer for the user in Russian.\n\n"
        "Tool Registry:\n" + "\n\n".join(tools_block)
    ).strip()


TOOLS, TOOL_SPECS = discover_tools_and_specs()


def _wrap_tool_with_logging(func):
    if inspect.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger.info("Tool call: %s args=%s kwargs=%s", func.__name__, args, kwargs)
            try:
                result = await func(*args, **kwargs)
                logger.info("Tool result: %s -> %s", func.__name__, str(result)[:1000])
                return result
            except Exception:
                logger.exception("Tool error: %s", func.__name__)
                raise

        return async_wrapper

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        logger.info("Tool call: %s args=%s kwargs=%s", func.__name__, args, kwargs)
        try:
            result = func(*args, **kwargs)
            logger.info("Tool result: %s -> %s", func.__name__, str(result)[:1000])
            return result
        except Exception:
            logger.exception("Tool error: %s", func.__name__)
            raise

    return sync_wrapper


LOGGED_TOOLS = [_wrap_tool_with_logging(tool) for tool in TOOLS]
SYSTEM_PROMPT = build_system_prompt(TOOL_SPECS)


class AssistantAgent:
    def __init__(self):
        self.tools = LOGGED_TOOLS
        self.tool_specs = TOOL_SPECS
        logger.info(
            "AssistantAgent initialized with %d tools: %s",
            len(self.tools),
            [tool.__name__ for tool in self.tools],
        )
        logger.info("AssistantAgent system prompt: %s", SYSTEM_PROMPT)
        self.deep_agent = create_deep_agent(
            model=ChatOpenAI(
                model=settings.ai_model,
                api_key=settings.ai_api_key,
                base_url=settings.ai_base_url,
            ),
            tools=self.tools,
            system_prompt=SYSTEM_PROMPT,
        )

    async def run(
        self, user_message: str, history: list[dict[str, str]]
    ) -> tuple[str, list[dict[str, Any]]]:
        logger.info(
            "User request: %s | history_len=%d", user_message, len(history or [])
        )
        payload_messages: list[dict[str, str]] = [
            {"role": msg.get("role", "user"), "content": msg.get("content", "")}
            for msg in history
            if msg.get("content")
        ]
        payload_messages.append({"role": "user", "content": user_message})

        logger.info("LLM request payload: %s", payload_messages)

        result = await self._invoke_deep_agent(payload_messages)
        logger.info("LLM response payload: %s", result)
        answer = self._extract_answer(result)
        trace = self._extract_tool_trace(result)
        return answer, trace

    async def _invoke_deep_agent(self, messages: list[dict[str, str]]) -> Any:
        if hasattr(self.deep_agent, "ainvoke"):
            return await self.deep_agent.ainvoke({"messages": messages})
        if hasattr(self.deep_agent, "invoke"):
            maybe = self.deep_agent.invoke({"messages": messages})
            if inspect.isawaitable(maybe):
                return await maybe
            return maybe
        raise RuntimeError("deepagents agent does not expose invoke/ainvoke")

    @staticmethod
    def _extract_answer(result: Any) -> str:
        text = AssistantAgent._extract_text_block(result)
        if text:
            return text
        return "Готово"

    @staticmethod
    def _extract_text_block(payload: Any) -> str | None:
        if isinstance(payload, str):
            return payload.strip() or None

        if isinstance(payload, list):
            for item in reversed(payload):
                text = AssistantAgent._extract_text_block(item)
                if text:
                    return text
            return None

        if isinstance(payload, dict):
            if "messages" in payload:
                text = AssistantAgent._extract_text_block(payload["messages"])
                if text:
                    return text
            for key in ("answer", "output", "content", "text"):
                if key in payload:
                    text = AssistantAgent._extract_text_block(payload[key])
                    if text:
                        return text
            return None

        content_attr = getattr(payload, "content", None)
        if content_attr is not None:
            text = AssistantAgent._extract_text_block(content_attr)
            if text:
                return text

        text_attr = getattr(payload, "text", None)
        if isinstance(text_attr, str) and text_attr.strip():
            return text_attr.strip()

        if isinstance(content_attr, list):
            chunks: list[str] = []
            for part in content_attr:
                if isinstance(part, str):
                    chunks.append(part)
                elif isinstance(part, dict):
                    if isinstance(part.get("text"), str):
                        chunks.append(part["text"])
                    elif isinstance(part.get("content"), str):
                        chunks.append(part["content"])
            joined = "\n".join(
                chunk.strip() for chunk in chunks if chunk and chunk.strip()
            )
            return joined or None

        return None

    @staticmethod
    def _extract_tool_trace(payload: Any) -> list[dict[str, Any]]:
        messages: list[Any] = []
        if isinstance(payload, dict) and isinstance(payload.get("messages"), list):
            messages = payload["messages"]
        elif isinstance(payload, list):
            messages = payload
        elif hasattr(payload, "messages") and isinstance(
            getattr(payload, "messages"), list
        ):
            messages = getattr(payload, "messages")

        trace: list[dict[str, Any]] = []
        for msg in messages:
            if isinstance(msg, dict):
                calls = msg.get("tool_calls")
                if isinstance(calls, list):
                    for call in calls:
                        if isinstance(call, dict):
                            trace.append(
                                {
                                    "phase": "call",
                                    "tool": call.get("name")
                                    or call.get("tool")
                                    or "unknown",
                                    "args": call.get("args")
                                    or call.get("arguments")
                                    or {},
                                }
                            )

                msg_type = msg.get("type") or msg.get("role")
                if msg_type == "tool":
                    trace.append(
                        {
                            "phase": "result",
                            "tool": msg.get("name") or msg.get("tool_name") or "tool",
                            "content": str(msg.get("content", ""))[:2000],
                        }
                    )
                continue

            calls = getattr(msg, "tool_calls", None)
            if isinstance(calls, list):
                for call in calls:
                    if isinstance(call, dict):
                        trace.append(
                            {
                                "phase": "call",
                                "tool": call.get("name")
                                or call.get("tool")
                                or "unknown",
                                "args": call.get("args") or call.get("arguments") or {},
                            }
                        )

            msg_type = getattr(msg, "type", None) or getattr(msg, "role", None)
            if msg_type == "tool":
                trace.append(
                    {
                        "phase": "result",
                        "tool": getattr(msg, "name", None)
                        or getattr(msg, "tool_name", None)
                        or "tool",
                        "content": str(getattr(msg, "content", ""))[:2000],
                    }
                )

        return trace
