"""Core tests for the webagent SDK."""

import textwrap

from webagent.codegen import generate_typescript
from webagent.parser import parse
from webagent.serializer import to_markdown
from webagent.types import Manifest, Param, Tool


def test_parse_heading_format():
    md = textwrap.dedent("""\
        # My Store

        ## search
        Search products.

        ### Params
        - `query` (string, required): Search query.
        - `limit` (number, optional, default=20): Max results.

        ### Output
        ```typescript
        { results: Array<{ id: string; name: string }>; total: number }
        ```

        ### Sample Code
        ```js
        const r = await global.search(query, limit);
        ```

        ## getBasket
        View basket contents.

        ### Params
    """)
    m = parse(md)
    assert m.name == "My Store"
    assert len(m.tools) == 2

    search = m.get_tool("search")
    assert search.params[0].name == "query"
    assert search.params[0].required is True
    assert search.params[1].name == "limit"
    assert search.params[1].required is False
    assert search.params[1].default == "20"
    assert search.returns == "{ results: Array<{ id: string; name: string }>; total: number }"
    assert "global.search" in search.sample_code

    assert m.get_tool("getBasket") is not None


def test_parse_compact_format():
    md = textwrap.dedent("""\
        # Site

        tool: search(query)
          description: |
            Search products.
          params:
            query: string
          sample_code:
            ```js
            const r = await global.search(query);
            ```
    """)
    m = parse(md)
    assert m.get_tool("search") is not None
    assert m.tools[0].params[0].name == "query"


def test_generate_typescript():
    manifest = Manifest(
        tools=[
            Tool(
                name="search",
                description="Search products.",
                params=[
                    Param(name="query"),
                    Param(name="limit", type="number", required=False, default="20"),
                ],
                returns="{ results: Array<{ id: string }>; total: number }",
            ),
            Tool(name="getBasket", description="View basket."),
        ],
    )
    ts = generate_typescript(manifest)
    assert "declare const global: {" in ts
    assert "search(query: string, limit?: number): Promise<{ results: Array<{ id: string }>; total: number }>;" in ts
    assert "getBasket(): Promise<any>;" in ts


def test_serializer_roundtrip():
    manifest = Manifest(
        name="Test",
        tools=[
            Tool(
                name="search",
                description="Search.",
                params=[
                    Param(name="q", type="string", required=True, description="The query."),
                    Param(name="limit", type="number", required=False, default="10", description="Max results."),
                ],
                sample_code="const r = await global.search(q);",
            ),
        ],
    )
    reparsed = parse(to_markdown(manifest))
    assert reparsed.name == "Test"
    assert reparsed.tools[0].name == "search"
    assert len(reparsed.tools[0].params) == 2
    assert reparsed.tools[0].params[1].required is False


def test_content_preserved():
    md = "# Store\nDescription.\n\n## Important\n- Rate limit: 10/min.\n\n## search\nSearch.\n"
    m = parse(md)
    assert "Rate limit: 10/min." in m.content
