from __future__ import annotations

import json
import inspect
from dataclasses import dataclass
from typing import Any

from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from app.config import settings
from app.integrations.calendar import GoogleCalendarTool
from app.integrations.gmail import GmailTool
from app.integrations.notion import NotionTool
from app.integrations.tavily import TavilyTool
from app.integrations.todoist import TodoistTool
from app.integrations.weather import OpenWeatherTool


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    args_schema: dict[str, str]


TOOL_SPECS: list[ToolSpec] = [
    ToolSpec(
        name="notion_search",
        description="Search notes, documents and knowledge base in Notion workspace.",
        args_schema={"query": "string, required. Search text."},
    ),
    ToolSpec(
        name="notion_create_note",
        description="Create a quick note page in Notion from plain text content.",
        args_schema={
            "content": "string, required. Note body text.",
        },
    ),
    ToolSpec(
        name="weather_current_weather",
        description="Get current weather in a specific city for planning decisions.",
        args_schema={
            "city": "string, required. City name.",
            "units": "string, optional. metric/imperial. Default metric.",
            "lang": "string, optional. Response language. Default ru.",
        },
    ),
    ToolSpec(
        name="tavily_search",
        description="Search web for fresh public information.",
        args_schema={
            "query": "string, required. What to search on the web.",
            "max_results": "integer, optional. Default 5.",
        },
    ),
    ToolSpec(
        name="todoist_list_tasks",
        description="List current Todoist tasks.",
        args_schema={},
    ),
    ToolSpec(
        name="todoist_create_task",
        description="Create a new task in Todoist.",
        args_schema={
            "content": "string, required. Task title.",
            "due_string": "string, optional. Natural language due date.",
            "due_date": "string, optional. Due date in YYYY-MM-DD.",
            "description": "string, optional. Task description/details.",
        },
    ),
    ToolSpec(
        name="gmail_list_messages",
        description="List Gmail messages by query filter.",
        args_schema={
            "query": "string, optional. Gmail search query.",
            "max_results": "integer, optional. Default 10.",
        },
    ),
    ToolSpec(
        name="gmail_send_message",
        description="Send Gmail message from structured fields; backend builds RFC2822/base64 payload internally.",
        args_schema={
            "to_email": "string, required. Recipient email.",
            "subject": "string, required. Email subject.",
            "body": "string, required. Plain text body.",
            "from_email": "string, required. Sender email used in From header.",
        },
    ),
    ToolSpec(
        name="calendar_list_events",
        description="List upcoming Google Calendar events.",
        args_schema={
            "max_results": "integer, optional. Default 10.",
            "include_past": "boolean, optional. Default false (only upcoming events).",
        },
    ),
    ToolSpec(
        name="calendar_create_event",
        description="Create Google Calendar event with ISO datetimes.",
        args_schema={
            "summary": "string, required. Event title.",
            "start_iso": "string, required. ISO datetime start.",
            "end_iso": "string, required. ISO datetime end.",
        },
    ),
]


def build_system_prompt() -> str:
    tools_block = []
    for idx, spec in enumerate(TOOL_SPECS, start=1):
        args_str = json.dumps(spec.args_schema, ensure_ascii=False)
        tools_block.append(f"{idx}. {spec.name}: {spec.description}; args={args_str}")

    return (
        "You are a local AI assistant orchestrator inspired by deepagents.\n"
        "You MUST select tools only from the provided tool registry.\n"
        "For each user request, choose tools by their description and args schema, call them when needed, then produce the final user-facing reply.\n"
        "Never output planning JSON, tool call plans, or internal chain-of-thought.\n"
        "Always return a plain, concise final answer for the user in Russian.\n\n"
        "Tool Registry:\n"
        + "\n".join(tools_block)
    ).strip()


SYSTEM_PROMPT = build_system_prompt()


class AssistantAgent:
    def __init__(self):
        self.notion = NotionTool()
        self.weather = OpenWeatherTool()
        self.tavily = TavilyTool()
        self.todoist = TodoistTool()
        self.gmail = GmailTool()
        self.calendar = GoogleCalendarTool()

        model_name = settings.openai_model if ":" in settings.openai_model else f"openai:{settings.openai_model}"
        tools = self._build_deepagents_tools()
        self.deep_agent = create_deep_agent(
            model=init_chat_model(model_name),
            tools=list(tools.values()),
            subagents=self._build_subagents(tools),
            system_prompt=SYSTEM_PROMPT,
        )

    def _build_deepagents_tools(self):
        @tool("notion_search")
        async def notion_search(query: str) -> str:
            """Search notes/documents in Notion knowledge base by query."""
            return json.dumps(await self.notion.search(query=query), ensure_ascii=False)

        @tool("notion_create_note")
        async def notion_create_note(content: str) -> str:
            """Create a quick Notion note page from plain text."""
            return json.dumps(
                await self.notion.create_note(content=content),
                ensure_ascii=False,
            )

        @tool("weather_current_weather")
        async def weather_current_weather(city: str, units: str = "metric", lang: str = "ru") -> str:
            """Get current weather in city for planning decisions."""
            return json.dumps(
                await self.weather.current_weather(city=city, units=units, lang=lang),
                ensure_ascii=False,
            )

        @tool("tavily_search")
        async def tavily_search(query: str, max_results: int = 5) -> str:
            """Search public web information via Tavily."""
            return json.dumps(await self.tavily.search(query=query, max_results=max_results), ensure_ascii=False)

        @tool("todoist_list_tasks")
        async def todoist_list_tasks() -> str:
            """List Todoist tasks."""
            return json.dumps(await self.todoist.list_tasks(), ensure_ascii=False)

        @tool("todoist_create_task")
        async def todoist_create_task(
            content: str,
            due_string: str = "",
            due_date: str = "",
            description: str = "",
        ) -> str:
            """Create Todoist task with optional due date and description."""
            return json.dumps(
                await self.todoist.create_task(
                    content=content,
                    due_string=due_string or None,
                    due_date=due_date or None,
                    description=description or None,
                ),
                ensure_ascii=False,
            )

        @tool("gmail_list_messages")
        async def gmail_list_messages(query: str = "", max_results: int = 10) -> str:
            """List Gmail messages by query."""
            return json.dumps(
                await self.gmail.list_messages(query=query or None, max_results=max_results),
                ensure_ascii=False,
            )

        @tool("gmail_send_message")
        async def gmail_send_message(to_email: str, subject: str, body: str, from_email: str) -> str:
            """Send Gmail message from structured fields; MIME/base64 payload is built in backend."""
            return json.dumps(
                await self.gmail.send_message(
                    to_email=to_email,
                    subject=subject,
                    body=body,
                    from_email=from_email,
                ),
                ensure_ascii=False,
            )

        @tool("calendar_list_events")
        async def calendar_list_events(max_results: int = 10, include_past: bool = False) -> str:
            """List upcoming Google Calendar events."""
            return json.dumps(
                await self.calendar.list_events(max_results=max_results, include_past=include_past),
                ensure_ascii=False,
            )

        @tool("calendar_create_event")
        async def calendar_create_event(summary: str, start_iso: str, end_iso: str) -> str:
            """Create Google Calendar event from ISO datetime range."""
            return json.dumps(
                await self.calendar.create_event(summary=summary, start_iso=start_iso, end_iso=end_iso),
                ensure_ascii=False,
            )

        return {
            "notion_search": notion_search,
            "notion_create_note": notion_create_note,
            "weather_current_weather": weather_current_weather,
            "tavily_search": tavily_search,
            "todoist_list_tasks": todoist_list_tasks,
            "todoist_create_task": todoist_create_task,
            "gmail_list_messages": gmail_list_messages,
            "gmail_send_message": gmail_send_message,
            "calendar_list_events": calendar_list_events,
            "calendar_create_event": calendar_create_event,
        }

    @staticmethod
    def _build_subagents(tools: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            {
                "name": "research-agent",
                "description": "Research internet and knowledge base for additional context.",
                "system_prompt": "You are a research specialist. Focus on concise facts and sources.",
                "tools": [tools["tavily_search"], tools["notion_search"], tools["notion_create_note"]],
            },
            {
                "name": "mail-agent",
                "description": "Handle email checks and message operations.",
                "system_prompt": "You are an email operations specialist. Extract actionable items from emails.",
                "tools": [tools["gmail_list_messages"], tools["gmail_send_message"]],
            },
            {
                "name": "planning-agent",
                "description": "Create calendar events and task plans.",
                "system_prompt": "You are a planning assistant. Convert intent into tasks and events.",
                "tools": [
                    tools["calendar_list_events"],
                    tools["calendar_create_event"],
                    tools["todoist_list_tasks"],
                    tools["todoist_create_task"],
                ],
            },
            {
                "name": "weather-agent",
                "description": "Analyze weather impact on schedule.",
                "system_prompt": "You evaluate weather risks and propose plan adjustments.",
                "tools": [tools["weather_current_weather"]],
            },
        ]

    async def run(self, user_message: str, history: list[dict[str, str]]) -> tuple[str, list[dict[str, Any]]]:
        payload_messages: list[dict[str, str]] = [
            {"role": msg.get("role", "user"), "content": msg.get("content", "")}
            for msg in history
            if msg.get("content")
        ]
        payload_messages.append({"role": "user", "content": user_message})

        result = await self._invoke_deep_agent(payload_messages)
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
            joined = "\n".join(chunk.strip() for chunk in chunks if chunk and chunk.strip())
            return joined or None

        return None

    @staticmethod
    def _extract_tool_trace(payload: Any) -> list[dict[str, Any]]:
        messages: list[Any] = []
        if isinstance(payload, dict) and isinstance(payload.get("messages"), list):
            messages = payload["messages"]
        elif isinstance(payload, list):
            messages = payload
        elif hasattr(payload, "messages") and isinstance(getattr(payload, "messages"), list):
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
                                    "tool": call.get("name") or call.get("tool") or "unknown",
                                    "args": call.get("args") or call.get("arguments") or {},
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
                                "tool": call.get("name") or call.get("tool") or "unknown",
                                "args": call.get("args") or call.get("arguments") or {},
                            }
                        )

            msg_type = getattr(msg, "type", None) or getattr(msg, "role", None)
            if msg_type == "tool":
                trace.append(
                    {
                        "phase": "result",
                        "tool": getattr(msg, "name", None) or getattr(msg, "tool_name", None) or "tool",
                        "content": str(getattr(msg, "content", ""))[:2000],
                    }
                )

        return trace

