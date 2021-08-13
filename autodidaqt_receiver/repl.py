import asyncio
import sys


def hotfix_prompt_toolkit_windows():
    if sys.version_info[0] == 3 and sys.version_info[1] >= 8 and sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
