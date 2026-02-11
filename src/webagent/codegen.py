"""Generate TypeScript declarations from webagents.md manifests.

This is the primary way to present tools to an LLM.  The manifest's tools
are converted into a ``declare const global: { ... }`` TypeScript block
with JSDoc comments, typed parameters, and return types.  The LLM writes
code against these declarations; the agent runtime executes that code in
the browser where the ``global.*`` functions already exist.
"""

from __future__ import annotations

from webagent.types import Manifest, Param, Tool

_TS_TYPE_MAP: dict[str, str] = {
    "string": "string",
    "number": "number",
    "boolean": "boolean",
    "object": "Record<string, unknown>",
    "array": "unknown[]",
}


def generate_typescript(manifest: Manifest) -> str:
    """Generate TypeScript declarations for all tools in a manifest.

    Returns a ``declare const global`` block ready to inject into an
    LLM's context.

    Example output::

        declare const global: {
          /** Search the product catalog. */
          searchProducts(query: string, limit?: number): Promise<...>;
        };
    """
    if not manifest.tools:
        return "declare const global: {};\n"

    tool_decls = [_tool_declaration(tool) for tool in manifest.tools]
    inner = "\n\n".join(tool_decls)
    return f"declare const global: {{\n{inner}\n}};\n"


def _tool_declaration(tool: Tool) -> str:
    """Generate a single tool's TypeScript declaration with JSDoc."""
    lines: list[str] = []

    # JSDoc
    lines.append("  /**")
    if tool.description:
        for desc_line in tool.description.splitlines():
            lines.append(f"   * {desc_line}")
    if tool.params:
        if tool.description:
            lines.append("   *")
        for param in tool.params:
            desc = f" {param.description}" if param.description else ""
            default = f" (default: {param.default})" if param.default else ""
            lines.append(f"   * @param {param.name} -{desc}{default}")
    lines.append("   */")

    # Function signature
    params_str = ", ".join(_param_to_ts(p) for p in tool.params)
    return_type = tool.returns if tool.returns else "any"
    lines.append(f"  {tool.name}({params_str}): Promise<{return_type}>;")

    return "\n".join(lines)


def _param_to_ts(param: Param) -> str:
    """Convert a Param to a TypeScript parameter string."""
    ts_type = _TS_TYPE_MAP.get(param.type, param.type)
    optional = "?" if not param.required else ""
    return f"{param.name}{optional}: {ts_type}"
