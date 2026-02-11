"""Helpers for website developers to create and serve webagents.md manifests.

This module provides utilities for the website-developer side of webagents.md:
building manifests programmatically, generating the HTML meta tag for
discovery, and validating manifests.
"""

from __future__ import annotations

from webagent.parser import parse
from webagent.serializer import to_markdown, write_file
from webagent.types import Manifest, Param, Tool


def meta_tag(path: str = "/webagents.md") -> str:
    """Generate the HTML ``<meta>`` tag for webagents.md discovery.

    Website developers add this to their ``<head>`` so AI agents can find
    the manifest.

    Args:
        path: URL path to the webagents.md file (default ``"/webagents.md"``).

    Returns:
        An HTML meta tag string.

    Example::

        >>> meta_tag()
        '<meta name="webagents-md" content="/webagents.md">'
        >>> meta_tag("/api/webagents.md")
        '<meta name="webagents-md" content="/api/webagents.md">'
    """
    return f'<meta name="webagents-md" content="{path}">'


def validate(manifest: Manifest) -> list[str]:
    """Validate a manifest and return a list of warnings.

    Returns an empty list if the manifest is valid.

    Checks:
        - Manifest has a name.
        - Manifest has at least one tool.
        - Each tool has a name and description.
        - Each tool has at least one param or sample_code.
        - No duplicate tool names.
    """
    warnings: list[str] = []

    if not manifest.name:
        warnings.append("Manifest has no name.")
    if not manifest.tools:
        warnings.append("Manifest has no tools.")

    seen_names: set[str] = set()
    for tool in manifest.tools:
        if not tool.name:
            warnings.append("A tool has no name.")
        elif tool.name in seen_names:
            warnings.append(f"Duplicate tool name: '{tool.name}'.")
        else:
            seen_names.add(tool.name)

        if not tool.description:
            warnings.append(f"Tool '{tool.name}' has no description.")
        if not tool.params and not tool.sample_code:
            warnings.append(f"Tool '{tool.name}' has no params and no sample_code.")

    return warnings


def validate_markdown(markdown: str) -> list[str]:
    """Parse and validate a webagents.md Markdown string.

    Returns a list of warnings (empty if valid).
    """
    manifest = parse(markdown)
    return validate(manifest)


def build_manifest(
    name: str,
    description: str = "",
    tools: list[Tool] | None = None,
) -> Manifest:
    """Build a Manifest object.

    A convenience constructor for website developers.

    Args:
        name: Site or service name.
        description: Overall description.
        tools: List of Tool objects.
    """
    return Manifest(name=name, description=description, tools=tools or [])


def build_tool(
    name: str,
    description: str = "",
    params: list[tuple[str, str, str]] | None = None,
    sample_code: str = "",
) -> Tool:
    """Build a Tool from simple arguments.

    Args:
        name: Tool identifier.
        description: What the tool does.
        params: List of ``(name, type, description)`` tuples. All are required
            by default. Use :class:`Param` directly for optional params.
        sample_code: JavaScript snippet showing invocation.

    Example::

        tool = build_tool(
            "searchProducts",
            "Search the product catalog.",
            params=[("query", "string", "Search query text.")],
            sample_code="const r = await global.searchProducts(query);",
        )
    """
    param_objs = [Param(name=n, type=t, description=d) for n, t, d in (params or [])]
    return Tool(name=name, description=description, params=param_objs, sample_code=sample_code)


__all__ = [
    "build_manifest",
    "build_tool",
    "meta_tag",
    "to_markdown",
    "validate",
    "validate_markdown",
    "write_file",
]
