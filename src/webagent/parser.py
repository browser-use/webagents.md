"""Parse webagents.md Markdown into structured Manifest objects."""

from __future__ import annotations

import re
from pathlib import Path

from webagent.types import Manifest, Param, Tool

# Matches a param line: - `name` (type, required|optional, default=val): description
_PARAM_RE = re.compile(
    r"^-\s+`(\w+)`"  # - `name`
    r"\s*\(([^)]+)\)"  # (type, required|optional, default=val)
    r"\s*:\s*(.+)$",  # : description
)

# Matches a fenced code block
_CODE_BLOCK_RE = re.compile(r"```\w*\n(.*?)```", re.DOTALL)

# Matches `tool: funcName(params)` compact syntax
_TOOL_HEADER_RE = re.compile(r"^tool:\s+(\w+)\(([^)]*)\)\s*$")


def parse(markdown: str) -> Manifest:
    """Parse a webagents.md Markdown string into a Manifest.

    Supports two formats:

    **Heading format:**
        # Site Name
        Description...

        ## tool_name
        Tool description...

        ### Params
        - `query` (string, required): The search query.

        ### Sample Code
        ```js
        const r = await global.tool_name(query);
        ```

    **Compact format (tool: syntax):**
        tool: searchProducts(query)
          description: |
            Search products by query.
          params:
            query: string (max 200 chars)
          sample_code:
            ```js
            const r = await global.searchProducts(query);
            ```
    """
    markdown = markdown.strip()
    if not markdown:
        return Manifest()

    # Detect format: if any line starts with "tool:" use compact parser
    if re.search(r"^tool:\s+", markdown, re.MULTILINE):
        manifest = _parse_compact(markdown)
    else:
        manifest = _parse_heading(markdown)

    # Preserve the full raw markdown
    manifest.content = markdown
    return manifest


def parse_file(path: str | Path) -> Manifest:
    """Parse a webagents.md file from disk."""
    text = Path(path).read_text(encoding="utf-8")
    return parse(text)


# ---------------------------------------------------------------------------
# Heading-based format (## tool_name)
# ---------------------------------------------------------------------------


def _parse_heading(markdown: str) -> Manifest:
    # Split into level-2 sections
    parts = re.split(r"(?m)^## ", markdown)
    header = parts[0]
    tool_sections = parts[1:]

    name, description = _parse_manifest_header(header)
    tools = [_parse_heading_tool(section) for section in tool_sections]

    return Manifest(name=name, description=description, tools=tools)


def _parse_manifest_header(header: str) -> tuple[str, str]:
    lines = header.strip().splitlines()
    name = ""
    desc_lines: list[str] = []
    for line in lines:
        if line.startswith("# "):
            name = line.removeprefix("# ").strip()
        elif name:
            desc_lines.append(line)
    description = "\n".join(desc_lines).strip()
    return name, description


def _parse_heading_tool(section: str) -> Tool:
    # The section text starts right after "## " was split off
    sub_parts = re.split(r"(?m)^### ", section)
    header = sub_parts[0]
    sub_sections = {
        s.split("\n", 1)[0].strip().lower(): s.split("\n", 1)[1] if "\n" in s else "" for s in sub_parts[1:]
    }

    lines = header.strip().splitlines()
    tool_name = lines[0].strip() if lines else ""
    tool_desc = "\n".join(lines[1:]).strip()

    params: list[Param] = []
    if "params" in sub_sections:
        params = _parse_params_block(sub_sections["params"])

    sample_code = ""
    if "sample code" in sub_sections:
        sample_code = _extract_code_block(sub_sections["sample code"])

    returns = ""
    for key in ("output", "returns"):
        if key in sub_sections:
            returns = _extract_code_block(sub_sections[key])
            break

    return Tool(name=tool_name, description=tool_desc, params=params, returns=returns, sample_code=sample_code)


# ---------------------------------------------------------------------------
# Compact format (tool: funcName(args))
# ---------------------------------------------------------------------------


def _parse_compact(markdown: str) -> Manifest:
    # Extract top-level description (lines before first tool:)
    lines = markdown.splitlines()
    preamble_lines: list[str] = []
    name = ""
    for line in lines:
        if line.startswith("# "):
            name = line.removeprefix("# ").strip()
        elif _TOOL_HEADER_RE.match(line):
            break
        else:
            preamble_lines.append(line)

    description = "\n".join(preamble_lines).strip()

    # Split into tool blocks
    tool_blocks = re.split(r"(?m)^tool:\s+", markdown)
    tools: list[Tool] = []
    for block in tool_blocks[1:]:  # skip preamble
        tools.append(_parse_compact_tool(block))

    return Manifest(name=name, description=description, tools=tools)


def _apply_section(
    key: str,
    lines: list[str],
    raw_params_str: str,
    description: str,
    params: list[Param],
    returns: str,
    sample_code: str,
) -> tuple[str, list[Param], str, str]:
    """Apply a parsed compact-format section to the running tool state."""
    if key == "description":
        description = "\n".join(line.strip() for line in lines).strip()
    elif key == "params":
        params = _parse_compact_params(lines, raw_params_str)
    elif key in ("output", "returns"):
        code_text = "\n".join(lines)
        returns = _extract_code_block(code_text) if "```" in code_text else code_text.strip()
    elif key == "sample_code":
        code_text = "\n".join(lines)
        sample_code = _extract_code_block(code_text) if "```" in code_text else code_text.strip()
    return description, params, returns, sample_code


def _parse_compact_tool(block: str) -> Tool:
    lines = block.strip().splitlines()
    if not lines:
        raise ValueError("Empty tool block")

    # First line: funcName(param1, param2 = "default")
    header_match = _TOOL_HEADER_RE.match("tool: " + lines[0])
    if not header_match:
        # Try just the function name
        tool_name = lines[0].split("(")[0].strip()
        raw_params_str = ""
    else:
        tool_name = header_match.group(1)
        raw_params_str = header_match.group(2)

    description = ""
    params: list[Param] = []
    returns = ""
    sample_code = ""

    # Parse indented key: value sections
    current_key = ""
    current_lines: list[str] = []

    for line in lines[1:]:
        stripped = line.strip()
        # Check for section keys at 2-space indent
        if re.match(r"^\s{2}\w+:", line) and not line.startswith("    "):
            if current_key:
                description, params, returns, sample_code = _apply_section(
                    current_key, current_lines, raw_params_str, description, params, returns, sample_code
                )
            current_key = stripped.split(":")[0].strip()
            rest = stripped[len(current_key) + 1 :].strip()
            current_lines = [rest] if rest and rest != "|" else []
        else:
            current_lines.append(line)

    # Process last section
    if current_key:
        description, params, returns, sample_code = _apply_section(
            current_key, current_lines, raw_params_str, description, params, returns, sample_code
        )

    # If no params section but there are inline params in the header
    if not params and raw_params_str:
        params = _params_from_signature(raw_params_str)

    return Tool(name=tool_name, description=description, params=params, returns=returns, sample_code=sample_code)


def _parse_compact_params(lines: list[str], raw_params_str: str) -> list[Param]:
    """Parse compact-format params (indented key: type lines)."""
    params: list[Param] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Format: param_name: type_info
        if ":" in stripped:
            pname, ptype = stripped.split(":", 1)
            pname = pname.strip()
            ptype = ptype.strip()
            # Check for default in the header signature
            default = None
            required = True
            for part in raw_params_str.split(","):
                part = part.strip()
                if "=" in part and part.split("=")[0].strip() == pname:
                    default = part.split("=", 1)[1].strip().strip("'\"")
                    required = False
            params.append(Param(name=pname, type=ptype, description="", required=required, default=default))
    return params


def _params_from_signature(sig: str) -> list[Param]:
    """Create basic Param objects from a function signature string like 'query, limit = 10'."""
    params: list[Param] = []
    for part in sig.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            name, default = part.split("=", 1)
            default_val = default.strip().strip("'\"")
            params.append(Param(name=name.strip(), required=False, default=default_val, description=""))
        else:
            params.append(Param(name=part.strip(), description=""))
    return params


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _parse_params_block(text: str) -> list[Param]:
    """Parse a heading-format params section into Param objects.

    Expected line format:
        - `name` (type, required|optional, default=val): Description.
    """
    params: list[Param] = []
    for line in text.strip().splitlines():
        line = line.strip()
        m = _PARAM_RE.match(line)
        if not m:
            continue
        name = m.group(1)
        modifiers = m.group(2)
        desc = m.group(3).strip()

        ptype = "string"
        required = True
        default = None

        for mod in (s.strip() for s in modifiers.split(",")):
            if mod == "optional":
                required = False
            elif mod == "required":
                required = True
            elif mod.startswith("default="):
                default = mod.removeprefix("default=").strip()
                required = False
            elif mod in ("string", "number", "boolean", "object", "array"):
                ptype = mod
            else:
                # Treat unknown modifiers as type hints (e.g. '"light" | "full"')
                ptype = mod

        params.append(Param(name=name, type=ptype, description=desc, required=required, default=default))
    return params


def _extract_code_block(text: str) -> str:
    """Extract the content of the first fenced code block."""
    m = _CODE_BLOCK_RE.search(text)
    return m.group(1).strip() if m else text.strip()
