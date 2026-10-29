import json
import logging
from collections.abc import AsyncIterator

from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.core.prompts import SYSTEM_PROMPT
from app.core.tools import TOOL_MAP, TOOLS, set_current_user

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 4


class ChatAgent:
    """无状态 Agent：历史由 service 从 MySQL 读取后传进来"""

    def __init__(self) -> None:
        self._model = ChatOpenAI(
            model=settings.DEEPSEEK_MODEL,
            api_key=settings.DEEPSEEK_APIKEY,
            base_url=settings.DEEPSEEK_BASE_URL,
        )
        self._model_with_tools = self._model.bind_tools(TOOLS)

    async def astream(
        self, user_id: int, history: list[BaseMessage], message: str
    ) -> AsyncIterator[str]:
        """流式产出回答；模型要调工具就先执行工具，再继续生成"""
        messages: list[BaseMessage] = [
            SystemMessage(content=SYSTEM_PROMPT),
            *history,
            HumanMessage(content=message),
        ]

        # 工具自己查库，这里只告诉它当前用户是谁
        set_current_user(user_id)

        answer: list[str] = []

        for _ in range(MAX_TOOL_ROUNDS):
            gathered: AIMessageChunk | None = None

            async for chunk in self._model_with_tools.astream(messages):
                gathered = chunk if gathered is None else gathered + chunk
                if chunk.content:
                    answer.append(chunk.content)
                    yield chunk.content

            if gathered is None or not gathered.tool_calls:
                break

            messages.append(AIMessage(content=gathered.content, tool_calls=gathered.tool_calls))

            for call in gathered.tool_calls:
                logger.info("调用工具 %s，参数 %s", call["name"], call["args"])
                result = await self._run_tool(call["name"], call["args"])
                messages.append(ToolMessage(content=result, tool_call_id=call["id"]))

    async def _run_tool(self, name: str, args: dict) -> str:
        tool = TOOL_MAP.get(name)
        if tool is None:
            return json.dumps(
                {"status": "error", "message": f"不存在的工具：{name}"},
                ensure_ascii=False,
            )

        try:
            return await tool.ainvoke(args)
        except Exception:
            logger.exception("工具 %s 执行失败", name)
            return json.dumps({"status": "error", "message": "工具执行失败"}, ensure_ascii=False)


_agent: ChatAgent | None = None


def init_agent() -> None:
    """服务器启动时调用一次"""
    global _agent
    _agent = ChatAgent()


def get_agent() -> ChatAgent:
    if _agent is None:
        raise RuntimeError("Agent 尚未初始化")
    return _agent
