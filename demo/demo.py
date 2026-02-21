"""
Interactive demo: AI web agent for the bookstore.

  pip install -r requirements.txt && playwright install chromium
  Set API key in .env (GEMINI_API_KEY, etc.)
  python demo.py [--model MODEL]

Flow:
  1. Opens browser with the bookstore (position your window for recording)
  2. Press Enter -> discovers webagents.md and displays it
  3. Type a task -> agent writes JS and executes it in the browser
"""

import asyncio
import json
import os
import subprocess
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message="Pydantic serializer warnings")

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

import litellm
from playwright.async_api import async_playwright

# Import the webagent SDK from the local source
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from webagent import AgentClient

_demo_dir = Path(__file__).resolve().parent
load_dotenv(_demo_dir / ".env")
if not os.environ.get("GEMINI_API_KEY") and os.environ.get("GOOGLE_API_KEY"):
    os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]

SITE_URL = "http://localhost:8080"
DEFAULT_MODEL = "gemini/gemini-2.0-flash"

console = Console()


def parse_args():
    model = DEFAULT_MODEL
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--model" and i + 1 < len(sys.argv):
            model = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    return model


def start_server():
    server = subprocess.Popen(
        ["python", "-m", "http.server", "8080"],
        cwd=_demo_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(0.5)
    if server.poll() is not None:
        console.print("[red]ERROR: Could not start local server on port 8080.[/red]")
        sys.exit(1)
    return server


async def async_input(prompt: str = "") -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, input, prompt)


def _param_sig(tool):
    """Build a compact param signature like (query, limit?)."""
    parts = []
    for p in tool.params:
        s = p.name
        if not p.required:
            s += "?"
        parts.append(s)
    return f"({', '.join(parts)})"


async def display_discovery(agent, manifest):
    """Display the discovered manifest — minimal and streamed."""
    delay = 0.06

    console.print()
    console.print(f"  [dim]Found[/dim] [bold cyan]webagents.md[/bold cyan] [dim]on[/dim] [bold]{manifest.name}[/bold]")
    console.print()
    await asyncio.sleep(delay * 3)

    # Tool table — one row per tool, streams in
    table = Table(
        show_header=True,
        header_style="bold dim",
        border_style="dim",
        padding=(0, 2),
        expand=False,
    )
    table.add_column("Tool", style="bold cyan", no_wrap=True)
    table.add_column("Description", style="white")

    for tool in manifest.tools:
        sig = Text.assemble(
            (tool.name, "bold cyan"),
            (_param_sig(tool), "dim"),
        )
        table.add_row(sig, tool.description)

    console.print(table)
    console.print()
    await asyncio.sleep(delay * 5)

    # TypeScript declarations — what the LLM actually receives
    ts = agent.typescript()
    console.print(Panel(
        Syntax(ts, "typescript", theme="monokai", line_numbers=False),
        title="[bold green]Generated TypeScript → LLM[/bold green]",
        border_style="dim",
        padding=(1, 2),
    ))
    console.print()


async def run_task(agent, page, model, task):
    """Run one agent task and display results."""
    console.rule(f"[bold yellow]Task: {task}[/bold yellow]")
    console.print()

    prompt = agent.system_prompt()
    tool = agent.execute_tool()
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": task},
    ]

    step = 0
    while True:
        response = litellm.completion(
            model=model,
            messages=messages,
            tools=[tool],
            max_tokens=1024,
        )

        choice = response.choices[0]
        msg = choice.message
        messages.append(msg)

        if msg.content:
            console.print(Panel(msg.content, title="[bold blue]Agent[/bold blue]", border_style="blue"))

        if not msg.tool_calls:
            break

        for tc in msg.tool_calls:
            step += 1
            code = json.loads(tc.function.arguments).get("code", "")

            console.print(Panel(
                Syntax(code, "javascript", theme="monokai", line_numbers=False),
                title=f"[bold green]execute_js (step {step})[/bold green]",
                border_style="green",
            ))

            result = await agent.execute(page, code)

            try:
                result_display = json.dumps(json.loads(result), indent=2)
            except (json.JSONDecodeError, TypeError):
                result_display = result

            console.print(f"  [dim]→[/dim] {result_display}\n")

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

        if choice.finish_reason == "stop":
            break

    console.print()


async def main():
    model = parse_args()
    server = start_server()

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=False,
                args=["--window-size=960,1080", "--window-position=960,0"],
            )
            page = await browser.new_page(viewport={"width": 960, "height": 1000})
            await page.goto(SITE_URL)

            # Clear screen and move cursor to top
            os.system("clear")

            # Stage 1: Browser is open — wait for user
            console.print()
            console.print("[dim]Press Enter to discover tools...[/dim]", end="")
            await async_input()

            # Stage 2: Discover and display webagents.md
            async with AgentClient() as agent:
                manifest = await agent.detect(SITE_URL)
                if not manifest:
                    console.print("[red]ERROR: Could not find webagents.md[/red]")
                    sys.exit(1)

                await display_discovery(agent, manifest)

                # Stage 3: Interactive task loop
                while True:
                    try:
                        console.print("[bold]What should the agent do?[/bold]")
                        task = (await async_input("  > ")).strip()
                    except (EOFError, KeyboardInterrupt):
                        break
                    if not task:
                        continue
                    if task.lower() in ("quit", "exit", "q"):
                        break
                    console.print()
                    await run_task(agent, page, model, task)

            await browser.close()
    finally:
        server.terminate()
        server.wait()


if __name__ == "__main__":
    asyncio.run(main())
