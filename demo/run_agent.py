"""
Demo: AI web agent for the bookstore.

  pip install -r requirements.txt && playwright install chromium
  Set API key in .env (GEMINI_API_KEY, etc.)
  python run_agent.py [task] [--model MODEL]
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

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
DEFAULT_TASK = (
    "Search for books by Tolkien, tell me what you find, "
    "then add The Hobbit to the basket and show me what's in the basket."
)


def parse_args():
    model = DEFAULT_MODEL
    task_parts = []
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--model" and i + 1 < len(sys.argv):
            model = sys.argv[i + 1]
            i += 2
        else:
            task_parts.append(sys.argv[i])
            i += 1
    task = " ".join(task_parts) if task_parts else DEFAULT_TASK
    return model, task


def start_server():
    """Start a local file server serving the demo directory."""
    server = subprocess.Popen(
        ["python", "-m", "http.server", "8080"],
        cwd=_demo_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(0.5)
    if server.poll() is not None:
        print("ERROR: Could not start local server on port 8080.")
        sys.exit(1)
    return server


async def main():
    model, task = parse_args()
    server = start_server()

    try:
        # 1. Discover tools from the running demo site
        print("=== Discovering webagents.md ===")
        async with AgentClient() as agent:
            manifest = await agent.detect(SITE_URL)
            if not manifest:
                print("ERROR: Could not find webagents.md at", SITE_URL)
                sys.exit(1)

            print(f"Site: {manifest.name}")
            print(f"Tools: {agent.list_tools()}\n")

            # Everything the agent needs comes from the SDK
            prompt = agent.system_prompt()
            tool = agent.execute_tool()

            # 2. Launch browser
            print("=== Launching browser ===")
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=False)
                page = await browser.new_page()
                await page.goto(SITE_URL)
                print(f"Navigated to {SITE_URL}\n")

                # 3. Agent loop
                print(f"=== Task: {task} ===")
                print(f"=== Model: {model} ===\n")

                messages = [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": task},
                ]

                while True:
                    response = litellm.completion(
                        model=model,
                        messages=messages,
                        tools=[tool],
                        max_tokens=1024,
                    )

                    choice = response.choices[0]
                    assistant_msg = choice.message
                    messages.append(assistant_msg)

                    if assistant_msg.content:
                        print(f"Agent: {assistant_msg.content}\n")

                    if not assistant_msg.tool_calls:
                        break

                    for tool_call in assistant_msg.tool_calls:
                        code = json.loads(tool_call.function.arguments).get("code", "")
                        print(f"  -> Executing JS:\n     {code}\n")

                        result = await agent.execute(page, code)
                        print(f"     Result: {result}\n")

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result,
                        })

                    if choice.finish_reason == "stop":
                        break

                print("=== Done. Browser will stay open 10 seconds... ===")
                await asyncio.sleep(10)
                await browser.close()
    finally:
        server.terminate()
        server.wait()

    print("=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
