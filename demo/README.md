# Demo: Books to Browse

A working demo of the `webagents.md` spec: a mock bookstore website with AI-accessible tools, plus a script that runs an AI agent against it.

## What's here

| File | Description |
|------|-------------|
| `index.html` | Self-contained bookstore (HTML/CSS/JS, no build step, no dependencies) |
| `webagents.md` | The webagent manifest declaring 6 tools |
| `run_agent.py` | AI agent that discovers the tools and uses them to complete a task |
| `demo.py` | Interactive demo — opens browser, displays discovered tools, then lets you type tasks |

## Quick start

```bash
cd demo
pip install -r requirements.txt
playwright install chromium
```

Set your API key in `.env` (or export it):

```
GEMINI_API_KEY=your-key-here
```

Run the agent:

```bash
python run_agent.py
```

The script starts a local server automatically, discovers the site's `webagents.md`, and runs the agent.

> The webagent SDK is imported directly from `../src` — no `pip install` needed for it.

### Interactive demo

`demo.py` is an interactive version. It opens the browser, discovers `webagents.md`, displays the tools and TypeScript declarations, then prompts you for tasks.

```bash
python demo.py [--model MODEL]
```

### Custom tasks and models

```bash
python run_agent.py "Find mystery books under $14 and add them all to the basket"
python run_agent.py --model gemini/gemini-3-flash "What's the most expensive book?"
```

Any model supported by [LiteLLM](https://docs.litellm.ai/docs/providers) works. Set the corresponding API key (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, etc.).

## How it works

### The website

The bookstore is a single `index.html` with 24 hardcoded books across 5 categories. It exposes 6 JavaScript functions on `globalThis` that match the tools declared in `webagents.md`:

| Tool | Description |
|------|-------------|
| `searchBooks(query)` | Search by title or author |
| `getBookDetails(bookId)` | Get full details for a book |
| `filterByCategory(category)` | Filter books by genre |
| `addToBasket(bookId, quantity?)` | Add to shopping basket |
| `getBasket()` | View basket contents |
| `removeFromBasket(bookId)` | Remove from basket |

The `<meta name="webagents-md" content="/webagents.md">` tag in the HTML `<head>` enables automatic discovery.

### The agent

`run_agent.py` follows the code-first webagent workflow:

1. **Start server**: launches a local HTTP server serving the demo directory
2. **Discover**: uses `AgentClient.detect()` to find and parse `webagents.md`
3. **Get prompt + tool**: `system_prompt()` returns the full LLM context, `execute_tool()` returns the generic tool schema
4. **Launch browser**: opens the site in Chromium via Playwright
5. **Agent loop**: sends the prompt + task to an LLM, which writes JavaScript code; `execute()` runs it in the browser, returns results, and repeats until done

The LLM can chain multiple `global.*` calls in a single code block.