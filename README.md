# webagents.md

This is a proposed spec and Python SDK that lets websites expose tools for AI agents to call directly in the browser. A site publishes a Markdown file describing its tools, and any agent can discover and use them.

If adopted broadly, `webagents.md` is how AI agents navigate the web autonomously--not by clicking through interfaces built for humans, but by calling functions that websites explicitly provide to them.

**How it works:** A website publishes a `webagents.md` file listing its tools and adds a `<meta>` tag for discovery. The SDK detects the tag, parses the manifest, and converts the tools into TypeScript declarations. The LLM gets those declarations as context plus a single `execute_js` tool.

The agent writes code like `await global.searchProducts("red shoes")`, and the runtime executes it in the browser via Playwright. Multiple calls can be chained in one shot.

**What the SDK provides:**
- For builders of AI agents, it detects a site's manifest, parses the tools, generates TypeScript declarations for the LLM, and executes LLM-written code in the browser.
- For website developers, it lets them build and validate manifests programmatically.

## Why `webagents.md` exists

Most web agents today behave in one of two ways:

- They view websites and **simulate clicks and keystrokes**, pretending to be a human. This is not deterministic and can be time-consuming, token-intensive, and prone to failure.
- They rely on **backend-only integrations** (MCP servers, custom APIs, OpenAPI specs) that are fragmented and require configuration.

At the same time, we've learned a few key things about LLMs:

- LLMs are **[much better at writing code](https://blog.cloudflare.com/code-mode)** than at making tool calls. They've seen millions of TypeScript APIs in training, but only a smaller set of contrived tool-calling examples.
- When an LLM can write code, it can chain multiple calls in one shot. It can also branch on results, looping over items, transforming data, handling errors, etc.

`webagents.md` is a simple answer to this:

- It's **framework-agnostic**: one Markdown file works with any LLM that can write TypeScript.
- It's **code-first**: the SDK converts tool declarations into TypeScript interfaces that LLMs write code against.
- It's **website-owned**: the site itself declares what tools exist and how they should be used.

It's like a **robots.txt for AI tools**: instead of telling crawlers which URLs to avoid, it tells agents which functions they can call.

## High-level overview

There are two audiences:

- **Agent developers**
  - Detect `webagents.md` on any site.
  - Parse the tools into TypeScript declarations.
  - Pass them to an LLM, which writes code that calls the tools directly in the browser.

- **Website developers**  
  - Define tools in a Markdown file (`webagents.md`).  
  - Optionally generate and validate that file using this SDK.  
  - Implement the corresponding JavaScript functions on their site.

At a high level:

1. A site adds **`webagents.md`** and a `<meta>` tag.
2. An agent runtime detects it.
3. The SDK converts the manifest into TypeScript declarations.
4. The LLM writes code like `const results = await global.searchProducts("red shoes");`.
5. The runtime executes that code in the browser, where the `global.*` functions already exist.

## Example

A website publishes a `webagents.md` file listing tools AI agents can use, and adds a `<meta>` tag to `<head>` for discovery:

```html
<meta name="webagents-md" content="/webagents.md">
```

Here's what that file looks like:

``````markdown
# Example Store

Simple online store for shoes and accessories.

## Important
- User must be logged in for cart operations.
- searchProducts is rate-limited to 10 calls/minute.

## searchProducts
Search the product catalog by keyword.

### Params
- `query` (string, required): Search query text.
- `limit` (number, optional, default=20): Maximum results.

### Output
```typescript
{ products: Array<{ id: string; name: string; price: number }>; total: number }
```

### Sample Code
```js
const results = await global.searchProducts(query);
```

## addToCart
Add a product to the shopping cart.

### Params
- `productId` (string, required): Unique product ID.
- `quantity` (number, optional, default=1): Quantity to add.

### Output
```typescript
{ cartId: string; items: Array<{ productId: string; quantity: number }> }
```

### Sample Code
```js
await global.addToCart(productId, quantity);
```
``````

That's it.

The SDK converts this into TypeScript declarations the LLM writes code against:

```typescript
declare const global: {
  /** Search the product catalog by keyword. */
  searchProducts(query: string, limit?: number): Promise<{
    products: Array<{ id: string; name: string; price: number }>;
    total: number;
  }>;
  /** Add a product to the shopping cart. */
  addToCart(productId: string, quantity?: number): Promise<{
    cartId: string;
    items: Array<{ productId: string; quantity: number }>;
  }>;
};
```

The LLM then writes code like:

```typescript
const results = await global.searchProducts("red shoes");
const top = results.products[0];
await global.addToCart(top.id, 2);
console.log(`Added ${top.name} to cart`);
```

## Why Markdown?

Everything in `webagents.md` is context for the LLM:

- **Tool declarations** → converted to TypeScript declarations the LLM writes code against.
- **`### Output` blocks** → become return types in the TypeScript, so the LLM knows what it gets back.
- **`### Sample Code` blocks** → documentation showing calling conventions.
- **Everything else** (instructions, rate limits, workflows, resources) → passed as-is to the LLM alongside the TypeScript.

The manifest serves as documentation, prompt, and tool definition all at once.

## Installation

```bash
pip install webagents-md
```

## For agent developers

### Detect and get TypeScript declarations

```python
import asyncio
from webagent import AgentClient

async def main():
    async with AgentClient() as agent:
        # Detect webagents.md on a website (via <meta name="webagents-md">)
        await agent.detect("https://shop.example.com")

        # Get TypeScript declarations — pass this to your LLM
        ts = agent.typescript()
        # => 'declare const global: { searchProducts(...): Promise<...>; ... };'

        # Or get full LLM context (TypeScript + raw markdown instructions)
        context = agent.context_for_llm()

asyncio.run(main())
```

### Build an agent loop

`AgentClient` provides everything needed for a full agent loop — system prompt, tool schema, and browser execution:

```python
import asyncio
from webagent import AgentClient

async def main():
    async with AgentClient() as agent:
        await agent.detect("https://shop.example.com")

        # List available tools
        print(agent.list_tools())  # ['searchProducts', 'addToCart', ...]

        # Get a complete system prompt (TypeScript API + instructions for the LLM)
        prompt = agent.system_prompt(task="Find red shoes and add them to cart")

        # Get the generic execute_js tool schema (OpenAI function-calling format)
        tool = agent.execute_tool()

        # Execute LLM-generated JavaScript in the browser (via a Playwright page)
        result = await agent.execute(page, 'return await global.searchProducts("red shoes")')

asyncio.run(main())
```

You can also load a manifest directly from a known URL (skipping `<meta>` tag detection):

```python
await agent.load("https://shop.example.com/webagents.md")
```

## For website developers

You can build and validate a `webagents.md` manifest programmatically:

```python
from webagent import Param, build_manifest, build_tool, meta_tag, to_markdown, validate, write_file

# Define tools
search = build_tool(
    name="searchProducts",
    description="Search the product catalog.",
    params=[
        ("query", "string", "Search query text."),
    ],
    sample_code="const results = await global.searchProducts(query);",
)

# For optional params, use Param directly
snapshot = build_tool(
    name="getPageSnapshot",
    description="Return a structured snapshot of current page state.",
    params=[],
    sample_code="const snapshot = await global.getPageSnapshot(mode);",
)
snapshot.params = [
    Param(name="mode", type="string", description='Snapshot mode.', required=False, default="full"),
]

# Build a manifest
manifest = build_manifest("My Store", tools=[search, snapshot])

# Validate it (checks names, descriptions, params, duplicates)
warnings = validate(manifest)
if warnings:
    print("Warnings:", warnings)

# Serialize to Markdown
md = to_markdown(manifest)
print(md)

# Or write directly to a file
write_file(manifest, "./webagents.md")

# Generate the HTML meta tag for discovery
print(meta_tag())  # <meta name="webagents-md" content="/webagents.md">
```

> **Note:** `build_tool` creates all params as required by default. For optional params with defaults, use the `Param` class directly as shown above.

And then:

1. Save `md` as `/webagents.md` on your site.
2. Add the `<meta name="webagents-md" content="/webagents.md">` tag to `<head>`.
3. Implement the corresponding JavaScript functions:

```js
// On the website:
global.searchProducts = async (query, limit = 20) => {
  const resp = await fetch(`/api/search?q=${encodeURIComponent(query)}&limit=${limit}`);
  if (!resp.ok) throw new Error("Search failed");
  return await resp.json();
};
```

## Manifest formats

The SDK can parse two formats. Both are valid Markdown, and both produce the same internal `Tool` objects.

### Heading format (recommended)

This is the format shown throughout this README. Tools are `##` headings, with `### Params`, `### Output`, and `### Sample Code` subsections. It's designed to be written by hand and read like documentation. The `### Output` section is optional. When present, it becomes the return type in the TypeScript declaration, and when absent the return type defaults to `Promise<any>`.

Any `##` section that isn't a tool (like `## Important` with instructions or rate limits) is preserved in `manifest.content` and included when you call `context_for_llm()`, so the LLM sees it as context alongside the TypeScript declarations.

### Compact format

An alternative format that's closer to a config file. Instead of headings, each tool starts with `tool:` followed by its signature, with indented `description`, `params`, `output`, and `sample_code` fields:

``````
tool: searchProducts(query, limit=20)
  description: |
    Search products by keyword.
  params:
    query: string
    limit: number?
  output:
    ```typescript
    { products: Array<{ id: string; name: string; price: number }>; total: number }
    ```
  sample_code:
    ```js
    const results = await global.searchProducts(query, limit);
    ```

tool: addToCart(productId, quantity=1)
  description: |
    Add a product to the cart.
  params:
    productId: string
    quantity: number?
  sample_code:
    ```js
    await global.addToCart(productId, quantity);
    ```
``````

Default values and optional params are expressed in the signature (`limit=20`) and type (`number?`) rather than in prose.

## Auth and security

`webagents.md` does **not** define authentication; it assumes:

- Tools run in the **context of the browser**,  
- Which means they can use:
  - the current user’s logged-in session (cookies/tokens),  
  - or any existing API keys/headers the site already uses.

A typical pattern:

```js
global.getUserProfile = async () => {
  const resp = await fetch("/api/user/me");  // browser sends cookies/headers as usual
  if (resp.status === 401) throw new Error("Not logged in");
  return await resp.json();
};
```

From the agent’s perspective, calling `getUserProfile()` is just:

```js
const profile = await global.getUserProfile();
```

If the user isn’t authenticated, the tool fails like it would for any other unauthenticated request. No secrets or tokens need to be embedded in `webagents.md`.

For cases where the agent isn't riding on an existing user session, websites can expose authentication tools in the manifest itself. For example, a `login` or `getAgentToken` tool could issue a scoped token for the agent to use in subsequent calls.

## Public API

Everything is importable from `webagent`:

| Function / Class | Description |
|---|---|
| `AgentClient` | High-level async client: detect, load, get TypeScript, execute JS in browser |
| `parse(markdown)` | Parse a `webagents.md` string into a `Manifest` |
| `parse_file(path)` | Parse a `webagents.md` file from disk |
| `generate_typescript(manifest)` | Generate `declare const global: { ... }` TypeScript declarations |
| `discover(url)` | Discover and parse a manifest from a web page |
| `discover_manifest_url(url)` | Get the manifest URL from a page's `<meta>` tag |
| `fetch_manifest(url)` | Fetch and parse a manifest from a direct URL |
| `build_manifest(name, ...)` | Build a `Manifest` programmatically |
| `build_tool(name, ...)` | Build a `Tool` from simple arguments |
| `validate(manifest)` | Validate a manifest, returns list of warnings |
| `to_markdown(manifest)` | Serialize a `Manifest` back to markdown |
| `write_file(manifest, path)` | Write a manifest to disk as markdown |
| `meta_tag(path)` | Generate the HTML `<meta>` discovery tag |
| `Manifest`, `Tool`, `Param` | Pydantic models |

## Architecture

Internally, `webagent` is:

```text
src/webagent/
├── __init__.py
├── types.py        # Pydantic models: Param, Tool, Manifest
├── parser.py       # Parse webagents.md → Manifest
├── discovery.py    # Discover webagents.md via <meta name="webagents-md">
├── client.py       # AgentClient (agent developer API)
├── codegen.py      # Generate TypeScript declarations from tools
├── serializer.py   # Manifest → webagents.md Markdown
└── site.py         # Website developer helpers (build, validate, meta_tag)
```

You can use just the building blocks you need:

- Only `parser.py` + `types.py` if you're writing your own runtime.
- Or `client.py` if you want an all-in-one agent-side helper.

## Demo

The [`demo/`](demo/) directory contains a working end-to-end example: a bookstore website ("Books to Browse") that declares tools via `webagents.md`, and a Python script that runs an AI agent against it.

```bash
cd demo
pip install -r requirements.txt
playwright install chromium
python run_agent.py
```

The script starts a local server, discovers the site's tools, and runs an AI agent that writes and executes JavaScript in the browser. See [`demo/README.md`](demo/README.md) for details.

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check src/ tests/
```

## License

MIT