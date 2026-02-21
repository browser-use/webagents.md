"""High-level client for AI agents to detect, interact with, and use webagents.md."""

from __future__ import annotations

import json
from typing import Any

import httpx

from webagent.codegen import generate_typescript
from webagent.discovery import discover, discover_manifest_url, fetch_manifest
from webagent.types import Manifest, Tool


class AgentClient:
    """Client for AI agents to discover and use webagents.md tool manifests.

    Provides the full agent-side workflow: detect a manifest on a website,
    list available tools, generate TypeScript declarations for the LLM,
    and get the full context needed for code generation.

    Usage::

        async with AgentClient() as agent:
            # 1. Detect webagents.md on a website
            manifest = await agent.detect("https://shop.example.com")

            # 2. Get TypeScript declarations to pass to the LLM
            ts = agent.typescript()

            # 3. Or get full LLM context (TypeScript + raw markdown)
            context = agent.context_for_llm()
    """

    def __init__(self, *, timeout: float = 30.0) -> None:
        self._http = httpx.AsyncClient(timeout=timeout, follow_redirects=True)
        self._manifest: Manifest | None = None

    # ----- Discovery -----

    async def detect(self, page_url: str) -> Manifest | None:
        """Detect and load a webagents.md manifest from a website.

        Looks for ``<meta name="webagents-md" content="/webagents.md">`` in the page,
        fetches the manifest, and stores it for subsequent operations.

        Returns:
            The parsed Manifest, or None if no webagents.md was found.
        """
        self._manifest = await discover(page_url, client=self._http)
        return self._manifest

    async def detect_url(self, page_url: str) -> str | None:
        """Detect the webagents.md URL from a page without fetching the manifest."""
        return await discover_manifest_url(page_url, client=self._http)

    async def load(self, manifest_url: str) -> Manifest:
        """Load a manifest directly from a known URL.

        Use this when you already know the webagents.md URL.
        """
        self._manifest = await fetch_manifest(manifest_url, client=self._http)
        return self._manifest

    def load_manifest(self, manifest: Manifest) -> None:
        """Load a pre-parsed manifest directly."""
        self._manifest = manifest

    # ----- Tool access -----

    @property
    def manifest(self) -> Manifest | None:
        """The currently loaded manifest, or None."""
        return self._manifest

    def list_tools(self) -> list[str]:
        """List the names of all tools in the loaded manifest.

        Raises:
            RuntimeError: If no manifest has been loaded yet.
        """
        if self._manifest is None:
            raise RuntimeError("No manifest loaded. Call detect() or load() first.")
        return self._manifest.tool_names

    def get_tool(self, name: str) -> Tool:
        """Get a tool by name from the loaded manifest.

        Args:
            name: The tool name (e.g. ``"searchProducts"``).

        Raises:
            RuntimeError: If no manifest has been loaded yet.
            KeyError: If the tool name is not found.
        """
        if self._manifest is None:
            raise RuntimeError("No manifest loaded. Call detect() or load() first.")
        tool = self._manifest.get_tool(name)
        if tool is None:
            raise KeyError(f"Tool '{name}' not found. Available: {self._manifest.tool_names}")
        return tool

    # ----- LLM integration -----

    def system_prompt(self, *, task: str = "") -> str:
        """Return a complete system prompt for the LLM.

        Includes the site name, TypeScript API declarations, raw markdown
        context, and instructions for using the ``execute_js`` tool.

        For simple agents this is all you need. For complex agents with
        their own prompt structure, use :meth:`context_for_llm` or
        :meth:`typescript` to get just the API context.

        Args:
            task: Optional task description to append to the prompt.

        Raises:
            RuntimeError: If no manifest has been loaded yet.
        """
        if self._manifest is None:
            raise RuntimeError("No manifest loaded. Call detect() or load() first.")
        name = self._manifest.name or "this website"
        context = self.context_for_llm()
        prompt = (
            f"You are interacting with a website called '{name}'. "
            "You have access to the following TypeScript API that runs in the browser:\n\n"
            f"{context}\n\n"
            "Use the execute_js tool to write JavaScript code that calls these functions. "
            "Use `await` for async calls and `return` the final result. "
            "Chain multiple calls in a single code block when needed. "
            "Avoid asking the user for clarification. If you need information to complete a request, "
            "use the available tools to look it up yourself whenever possible. "
            "When you're done, briefly summarize what you did."
        )
        if task:
            prompt += f"\n\nTask: {task}"
        return prompt

    def execute_tool(self) -> dict:
        """Return a generic ``execute_js`` tool schema for LLM tool-calling.

        This is the only tool the agent needs. The LLM writes JavaScript
        code using the ``global.*`` functions from the TypeScript context,
        and the agent runtime executes it in the browser.

        The returned dict is in OpenAI function-calling format, which is
        also accepted by LiteLLM, Anthropic, and most LLM providers.
        """
        return {
            "type": "function",
            "function": {
                "name": "execute_js",
                "description": (
                    "Execute JavaScript code in the browser. "
                    "Use the global.* functions from the TypeScript API. "
                    "Use `await` for async calls and `return` the final result. "
                    "You can chain multiple calls in one code block."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "JavaScript code to execute in the browser.",
                        },
                    },
                    "required": ["code"],
                },
            },
        }

    def typescript(self) -> str:
        """Generate TypeScript declarations for all tools.

        Returns a ``declare const global: { ... }`` block with JSDoc
        comments, typed parameters, and return types.  Pass this to the
        LLM so it can write code against the API.

        Raises:
            RuntimeError: If no manifest has been loaded yet.
        """
        if self._manifest is None:
            raise RuntimeError("No manifest loaded. Call detect() or load() first.")
        return generate_typescript(self._manifest)

    def context_for_llm(self) -> str:
        """Return the full context to pass to an LLM.

        Combines the TypeScript declarations (the API the LLM writes code
        against) with the raw markdown content (instructions, resources,
        workflows, auth guidance — everything the website author wrote).

        Raises:
            RuntimeError: If no manifest has been loaded yet.
        """
        if self._manifest is None:
            raise RuntimeError("No manifest loaded. Call detect() or load() first.")
        ts = generate_typescript(self._manifest)
        md = self._manifest.content
        if md:
            return f"{ts}\n/*\n{md}\n*/\n"
        return ts

    # ----- Browser execution -----

    async def execute(self, page: Any, code: str) -> str:
        """Execute JavaScript code in the browser and return the result.

        Wraps the code in an async IIFE and aliases ``global`` to
        ``globalThis`` so that LLM-generated code using ``global.*``
        works correctly in the browser.

        Args:
            page: A Playwright page (or any object with an ``evaluate`` method).
            code: JavaScript code to execute.

        Returns:
            The result as a string, or a JSON error object if execution failed.
        """
        wrapped = f"(async () => {{ const global = globalThis; {code} }})()"
        try:
            result = await page.evaluate(wrapped)
            if result is None:
                return "undefined"
            return str(result) if isinstance(result, str) else json.dumps(result)
        except Exception as e:
            return json.dumps({"error": str(e)})

    # ----- Lifecycle -----

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._http.aclose()

    async def __aenter__(self) -> AgentClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()
