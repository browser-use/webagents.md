"""webagent — Parse, discover, and use webagents.md tool manifests for AI agents."""

# Agent-side API (for agent developers)
from webagent.client import AgentClient
from webagent.codegen import generate_typescript
from webagent.discovery import discover, discover_manifest_url, fetch_manifest
from webagent.parser import parse, parse_file

# Site-side API (for website developers)
from webagent.serializer import to_markdown, write_file
from webagent.site import build_manifest, build_tool, meta_tag, validate
from webagent.types import Manifest, Param, Tool

__all__ = [
    # Types
    "Manifest",
    "Param",
    "Tool",
    # Agent-side
    "AgentClient",
    "discover",
    "discover_manifest_url",
    "fetch_manifest",
    "generate_typescript",
    "parse",
    "parse_file",
    # Site-side
    "build_manifest",
    "build_tool",
    "meta_tag",
    "to_markdown",
    "validate",
    "write_file",
]
