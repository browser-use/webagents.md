"""Pydantic models for the webagents.md specification."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Param(BaseModel):
    """A single parameter for a tool."""

    name: str = Field(description="Parameter name.")
    type: str = Field(default="string", description="Type hint: string, number, boolean, object, array.")
    description: str = Field(default="", description="Human-readable description.")
    required: bool = Field(default=True, description="Whether the parameter is required.")
    default: str | None = Field(default=None, description="Default value as a string literal, if any.")


class Tool(BaseModel):
    """A single tool declared in a webagents.md manifest."""

    name: str = Field(description="Tool identifier, e.g. 'searchProducts'.")
    description: str = Field(default="", description="Natural-language description of the tool.")
    params: list[Param] = Field(default_factory=list, description="Ordered list of parameters.")
    returns: str = Field(default="", description="TypeScript return type, e.g. '{ products: Product[] }'.")
    sample_code: str = Field(default="", description="Example JS snippet showing how the tool is called.")


class Manifest(BaseModel):
    """A parsed webagents.md manifest representing a website's AI-accessible tools."""

    name: str = Field(default="", description="Site or service name.")
    description: str = Field(default="", description="Overall description of the API surface.")
    version: str = Field(default="0.1", description="Manifest version.")
    tools: list[Tool] = Field(default_factory=list, description="All tools declared in the manifest.")
    content: str = Field(default="", description="Full raw markdown content of the manifest.")

    def get_tool(self, name: str) -> Tool | None:
        """Look up a tool by name."""
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None

    @property
    def tool_names(self) -> list[str]:
        """Return all tool names."""
        return [t.name for t in self.tools]
