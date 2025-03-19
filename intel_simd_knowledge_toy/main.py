from pathlib import Path
from dotenv import load_dotenv
import asyncio
import tempfile
import functools
import pprint
import re

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

from intel_simd_knowledge_toy.data_tools.pdf_files.textball import TextBall

@functools.cache
def get_simd_spellcheck():
    return SimdSpellcheck()

@functools.cache
def get_simd_textball():
    cwd = Path.cwd()
    text_path = cwd / "intel_simd_knowledge_toy" / "data" / "downloads" / "325383-sdm-vol-2abcd-dec-24.txt"
    textball = TextBall(text_path=text_path)
    return textball

@functools.cache
def get_simd_textball_page_count():
    textball = get_simd_textball()
    page_count = len(textball)
    return page_count

@functools.cache
def get_simd_textball_pages():
    textball = get_simd_textball()
    textball_pages = textball.get_pages()
    page_count = len(textball_pages)
    textball_pages = [textball_pages[page_idx] for page_idx in range(page_count)]
    return textball_pages

@functools.cache
def get_simd_textball_page_lines(page_idx: int):
    textball_pages = get_simd_textball_pages()
    page = textball_pages[page_idx]
    page_lines = [str(page[line_idx]) for line_idx in range(len(page))]
    return page_lines

@functools.cache
def get_dotspace_re_repl() -> tuple[re.Pattern, str]:
    _RE_DOTSPACE = re.compile(r"(?:\.\s){8,}+\.{0,}+")
    _REPL_DOTSPACE = r"  ...  "
    return _RE_DOTSPACE, _REPL_DOTSPACE

def replace_dotspace(line):
    """Replaces excessively long sequences of alternating dots and spaces with an ellipsis."""
    _RE_DOTSPACE, _REPL_DOTSPACE = get_dotspace_re_repl()
    line = _RE_DOTSPACE.sub(_REPL_DOTSPACE, line)
    return line


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

async def simd_keyword_morphemes() -> str:
    """Lists all of the morphemes found in SIMD keywords. Morphemes refer to the alphanumeric parts of the keywords, separated by underscores
    """
    def add_hdiv(lines: list[str]):
        lines.append("")
        lines.append("-" * 4)
        lines.append("")
    try:
        spellcheck = get_simd_spellcheck()
        morphemes = spellcheck.list_morphemes()
        lines = list[str]()
        lines.append(f"Listing morphemes found in SIMD keywords:")
        add_hdiv(lines)
        lines.append(", ".join(morphemes))
        add_hdiv(lines)
        lines.append("End of listing.")
        return "\n".join(lines)
    except Exception as exc:
        return f"An error occurred: {exc}"

async def simd_doc_page(page_idx: int) -> str:
    """Get the text content of a page from the Intel SIMD documentation.
    Args:
        page_idx (int): The zero-based index of the page to retrieve.
    """
    def add_hdiv(lines: list[str]):
        lines.append("")
        lines.append("-" * 4)
        lines.append("")
    try:
        page_count = get_simd_textball_page_count()
        if page_idx < 0 or page_idx >= page_count:
            return f"Page index must be in the range [0, {page_count})."
        page_lines = get_simd_textball_page_lines(page_idx)
        lines = list[str]()
        lines.append(f"Listing text content of page {page_idx}:")
        add_hdiv(lines)
        lines.extend((line for line in page_lines))
        add_hdiv(lines)
        lines.append("End of listing.")
        return "\n".join(lines)
    except Exception as exc:
        return f"An error occurred: {exc}"

async def simd_doc_table_of_contents() -> str:
    """Get the table of contents from the Intel SIMD documentation.
    """
    def add_hdiv(lines: list[str]):
        lines.append("")
        lines.append("-" * 4)
        lines.append("")
    try:
        page_first = 3
        page_last = 28
        lines = list[str]()
        lines.append(f"Listing the table of contents from pages {page_first} to {page_last} inclusive:")
        add_hdiv(lines)
        for page_idx in range(page_first, page_last + 1):
            page_lines = get_simd_textball_page_lines(page_idx)
            for line_idx, line in enumerate(page_lines):
                line = replace_dotspace(line)
                lines.append(f"Page {page_idx:5d}, Line {line_idx:5d}: {line}")
        add_hdiv(lines)
        lines.append("End of listing.")
        return "\n".join(lines)
    except Exception as exc:
        return f"An error occurred: {exc}"

async def main():
    with tempfile.TemporaryDirectory() as tmpdirname:
        # model = "gpt-4o"
        model = "gpt-4o-mini"
        # model = "o1" ### DOES NOT SUPPORT TOOL
        # model = "o1-mini"
        # model = "o3-mini" ### Answered without using any tool
        client = OpenAIChatCompletionClient(model=model)
        cache_store = DiskCacheStore[CHAT_CACHE_VALUE_TYPE](Cache(tmpdirname))
        cache_client = ChatCompletionCache(client, cache_store)

        tool_simd_keywords_list = FunctionTool(simd_keywords_list, description=simd_keywords_list.__doc__.splitlines()[0])
        tool_simd_keyword_find = FunctionTool(simd_keyword_find, description=simd_keyword_find.__doc__.splitlines()[0])
        tool_simd_keyword_morphemes = FunctionTool(simd_keyword_morphemes, description=simd_keyword_morphemes.__doc__.splitlines()[0])
        tool_simd_doc_page = FunctionTool(simd_doc_page, description=simd_doc_page.__doc__.splitlines()[0])
        tool_simd_doc_table_of_contents = FunctionTool(simd_doc_table_of_contents, description=simd_doc_table_of_contents.__doc__.splitlines()[0])
        # pprint.pprint(tool_simd_keywords_list.schema)

        tools = [
            tool_simd_keywords_list, 
            tool_simd_keyword_find, 
            tool_simd_keyword_morphemes,
            tool_simd_doc_page,
            tool_simd_doc_table_of_contents,
        ]

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
            tools=tools,
            system_message="Use tools to solve tasks."
        )

        termination_condition = TextMessageTermination("simd_agent")

        team = RoundRobinGroupChat(
            [simd_agent],
            termination_condition=termination_condition,
        )

        # task = "Which of the SIMD shuffle instructions work on 8-bit integers? "
        task = "On which page can I find the documentation for the ORPS instruction?"

        async for message in team.run_stream(task=task):
            print("======", type(message).__name__, "======")
            print(dir(message))
            print('-' * 20)
            pprint.pprint(message)

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())
