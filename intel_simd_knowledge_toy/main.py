import os
from dotenv import load_dotenv
import asyncio
import tempfile
import functools
import pprint

from autogen_core import CancellationToken
from autogen_core.models import SystemMessage, UserMessage
from autogen_core.tools import FunctionTool
from autogen_core.model_context import BufferedChatCompletionContext
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMessageTermination
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.models.cache import ChatCompletionCache, CHAT_CACHE_VALUE_TYPE
from autogen_ext.cache_store.diskcache import DiskCacheStore
from diskcache import Cache

from misc.simd_spellcheck import SimdSpellcheck

@functools.cache
def get_simd_spellcheck():
    return SimdSpellcheck()

async def simd_keywords_list(start: int, max_to_return: int) -> str:
    """List SIMD keywords from the specified range.
    Args:
        start (int): The starting index. The first keyword has index 0.
        max_to_return (int): The maximum number of keywords to return. Must be at least 1.
    """
    try:
        if isinstance(start, str):
            start = int(start)
        if isinstance(max_to_return, str):
            max_to_return = int(max_to_return)
        if start < 0:
            return "Start index must be a non-negative integer. This tool does not support Python-style negative indexing."
        if max_to_return < 1:
            return "Max-to-return must be a positive integer. This tool does not support Python-style negative indexing."
        spellcheck = get_simd_spellcheck()
        full_count = len(spellcheck)
        keywords = spellcheck[start:start + max_to_return]
        keyword_count = len(keywords)
        if keyword_count == 0:
            return f"No SIMD keywords found in the specified range. There are a total of {full_count} SIMD keywords."
        lines = list[str]()
        lines.append(f"Listing SIMD keywords from ({start}) to ({start+keyword_count-1}) inclusive:")
        lines.append("")
        for offset, keyword in enumerate(keywords):
            lines.append(f"- {start+offset}. {keyword}")
        lines.append("")
        lines.append("End of listing.")
        return "\n".join(lines)
    except Exception as exc:
        return f"An error occurred: {exc}"

async def simd_keyword_find(pattern: str) -> str:
    """Find SIMD keywords matching the specified pattern.
    Args:
        pattern (str): The pattern to match. This can include the wildcard characters '?' (matching a single character) and '*' (matching a sequence of characters).
    """
    try:
        spellcheck = get_simd_spellcheck()
        keywords = spellcheck.wildcard(pattern)
        keyword_count = len(keywords)
        if keyword_count == 0:
            return f"No SIMD keywords found matching the pattern \'{pattern}\'."
        lines = list[str]()
        lines.append(f"Listing SIMD keywords matching the pattern \'{pattern}\':")
        lines.append("")
        for keyword in keywords:
            lines.append(f"- {keyword}")
        lines.append("")
        lines.append("End of listing.")
        return "\n".join(lines)
    except Exception as exc:
        return f"An error occurred: {exc}"


async def main():
    with tempfile.TemporaryDirectory() as tmpdirname:
        # model = "gpt-4o"
        # model = "gpt-4o-mini"
        # model = "o1" ### DOES NOT SUPPORT TOOL
        # model = "o1-mini"
        model = "o3-mini" ### Answered without using any tool
        client = OpenAIChatCompletionClient(model=model)
        cache_store = DiskCacheStore[CHAT_CACHE_VALUE_TYPE](Cache(tmpdirname))
        cache_client = ChatCompletionCache(client, cache_store)

        tool_simd_keywords_list = FunctionTool(simd_keywords_list, description=simd_keywords_list.__doc__.splitlines()[0])
        tool_simd_keyword_find = FunctionTool(simd_keyword_find, description=simd_keyword_find.__doc__.splitlines()[0])
        # pprint.pprint(tool_simd_keywords_list.schema)

        buffered_context = BufferedChatCompletionContext(buffer_size=100)
        system_content = """
Typically, the names of SIMD instructions are constructed with a prefix, an action, and a suffix.
The prefix may indicate the instruction set, such as SSE, AVX, or AVX-512.
The action may indicate the operation, such as add, multiply, or shuffle.
The suffix may indicate the data type, such as integer or floating-point.
Keep in mind that SIMD instructions may use abbreviations or short forms in names.
You have been provided with tools to explore SIMD keywords.
In order to use the keyword find tool, the pattern must be correctly spelled the same way as they are in SIMD instructions.
Therefore, be familiar with the SIMD keywords before using the tool.
"""
        await buffered_context.add_message(SystemMessage(content=system_content))

        simd_agent = AssistantAgent(
            name="simd_agent",
            model_client=cache_client,
            model_context=buffered_context,
            description="A toy agent for exploring SIMD knowledge.",
            tools=[tool_simd_keywords_list, tool_simd_keyword_find],
            system_message="Use tools to solve tasks."
        )

        termination_condition = TextMessageTermination("simd_agent")

        team = RoundRobinGroupChat(
            [simd_agent],
            termination_condition=termination_condition,
        )

        task = "Which of the SIMD shuffle instructions work on 8-bit integers? "

        async for message in team.run_stream(task=task):
            print("======", type(message).__name__, "======")
            print(dir(message))
            print('-' * 20)
            pprint.pprint(message)

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())
