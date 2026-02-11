"""Serialize Manifest objects back to webagents.md Markdown format."""

from __future__ import annotations

from pathlib import Path

from webagent.types import Manifest, Param, Tool


def to_markdown(manifest: Manifest) -> str:
    """Serialize a Manifest to webagents.md Markdown (heading format).

    Args:
        manifest: The manifest to serialize.

    Returns:
        A Markdown string suitable for writing to a webagents.md file.
    """
    lines: list[str] = []

    if manifest.name:
        lines.append(f"# {manifest.name}")
    if manifest.description:
        lines.append(manifest.description)
    if lines:
        lines.append("")

    for tool in manifest.tools:
        lines.extend(_serialize_tool(tool))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_file(manifest: Manifest, path: str | Path) -> None:
    """Write a Manifest to a webagents.md file on disk.

    Args:
        manifest: The manifest to write.
        path: Filesystem path (e.g. ``"./webagents.md"``).
    """
    Path(path).write_text(to_markdown(manifest), encoding="utf-8")


def _serialize_tool(tool: Tool) -> list[str]:
    lines: list[str] = []
    lines.append(f"## {tool.name}")
    if tool.description:
        lines.append(tool.description)
    lines.append("")

    if tool.params:
        lines.append("### Params")
        for param in tool.params:
            lines.append(_serialize_param(param))
        lines.append("")

    if tool.returns:
        lines.append("### Output")
        lines.append("```typescript")
        lines.append(tool.returns)
        lines.append("```")
        lines.append("")

    if tool.sample_code:
        lines.append("### Sample Code")
        lines.append("```javascript")
        lines.append(tool.sample_code)
        lines.append("```")

    return lines


def _serialize_param(param: Param) -> str:
    modifiers = [param.type]
    modifiers.append("required" if param.required else "optional")
    if param.default is not None:
        modifiers.append(f"default={param.default}")
    mod_str = ", ".join(modifiers)
    desc = f": {param.description}" if param.description else ""
    return f"- `{param.name}` ({mod_str}){desc}"
