from __future__ import annotations

import asyncio
import pprint

from config import settings
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main() -> None:
    url = settings.telemetry_mcp_url
    async with streamable_http_client(url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(
                "query_telemetry",
                arguments={
                    "time_range_start": "2025-02-14T09:00:00Z",
                    "time_range_end": "2025-02-14T11:00:00Z",
                    "channels": ["bus_voltage"],
                },
            )
    print("Result type:", type(result))
    print("isError:", getattr(result, "isError", None))
    print("dir(result):")
    pprint.pp(dir(result))
    print("structuredContent:", getattr(result, "structuredContent", None))
    print("content:", getattr(result, "content", None))
    if getattr(result, "content", None):
        print("First content part type:", type(result.content[0]))
        print("First content part dir:")
        pprint.pp(dir(result.content[0]))
        if hasattr(result.content[0], "__dict__"):
            print("First content part __dict__:")
            pprint.pp(result.content[0].__dict__)


if __name__ == "__main__":
    asyncio.run(main())
