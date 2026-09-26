import warnings

warnings.filterwarnings("ignore", module="langchain_core._api.deprecation")

import argparse
import asyncio
import contextlib
import os
import sys
import warnings
from pathlib import Path

# Suppress Pydantic v1 compatibility warnings from langchain on Python 3.14+
warnings.filterwarnings("ignore", message=".*Pydantic V1.*", category=UserWarning)

from rich.text import Text

from deepagents_cli._version import __version__

# Now safe to import agent (which imports LangChain modules)
from deepagents_cli.agent import create_cli_agent, list_agents, reset_agent

# CRITICAL: Import config FIRST to set LANGSMITH_PROJECT before LangChain loads
from deepagents_cli.config import (
    console,
    create_model,
    settings,
)
from deepagents_cli.integrations.sandbox_factory import create_sandbox
from deepagents_cli.sessions import (
    delete_thread_command,
    generate_thread_id,
    get_checkpointer,
    get_most_recent,
    get_thread_agent,
    list_threads_command,
    thread_exists,
)
from deepagents_cli.skills import execute_skills_command, setup_skills_parser
from deepagents_cli.tools import fetch_url, http_request, web_search
from deepagents_cli.ui import show_help

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from rich.markdown import Markdown
from rich.panel import Panel
from rich.live import Live
from rich.console import Group
from rich.status import Status

from dotenv import load_dotenv
load_dotenv()

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="DeepAgents - AI Coding Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"deepagents {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # List command
    subparsers.add_parser("list", help="List all available agents")

    # Help command
    subparsers.add_parser("help", help="Show help information")

    # Reset command
    reset_parser = subparsers.add_parser("reset", help="Reset an agent")
    reset_parser.add_argument("--agent", required=True, help="Name of agent to reset")
    reset_parser.add_argument(
        "--target", dest="source_agent", help="Copy prompt from another agent"
    )

    # Skills command - setup delegated to skills module
    setup_skills_parser(subparsers)

    # Threads command
    threads_parser = subparsers.add_parser("threads", help="Manage conversation threads")
    threads_sub = threads_parser.add_subparsers(dest="threads_command")

    # threads list
    threads_list = threads_sub.add_parser("list", help="List threads")
    threads_list.add_argument(
        "--agent", default=None, help="Filter by agent name (default: show all)"
    )
    threads_list.add_argument("--limit", type=int, default=20, help="Max threads (default: 20)")

    # threads delete
    threads_delete = threads_sub.add_parser("delete", help="Delete a thread")
    threads_delete.add_argument("thread_id", help="Thread ID to delete")

    # Default interactive mode
    parser.add_argument(
        "--agent",
        default="agent",
        help="Agent identifier for separate memory stores (default: agent).",
    )

    # Thread resume argument - matches PR #638: -r for most recent, -r <ID> for specific
    parser.add_argument(
        "-r",
        "--resume",
        dest="resume_thread",
        nargs="?",
        const="__MOST_RECENT__",
        default=None,
        help="Resume thread: -r for most recent, -r <ID> for specific thread",
    )

    # Initial prompt - auto-submit when session starts
    parser.add_argument(
        "-m",
        "--message",
        dest="initial_prompt",
        help="Initial prompt to auto-submit when session starts",
    )

    parser.add_argument(
        "--model",
        help="Model to use (e.g., claude-sonnet-4-5-20250929, gpt-5-mini). "
        "Provider is auto-detected from model name.",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Auto-approve tool usage without prompting (disables human-in-the-loop)",
    )
    parser.add_argument(
        "--sandbox",
        choices=["none", "modal", "daytona", "runloop"],
        default="none",
        help="Remote sandbox for code execution (default: none - local only)",
    )
    parser.add_argument(
        "--sandbox-id",
        help="Existing sandbox ID to reuse (skips creation and cleanup)",
    )
    parser.add_argument(
        "--sandbox-setup",
        help="Path to setup script to run in sandbox after creation",
    )
    return parser.parse_args()


async def run_textual_cli_async(
    assistant_id: str,
    *,
    auto_approve: bool = False,
    sandbox_type: str = "none",
    sandbox_id: str | None = None,
    model_name: str | None = None,
    thread_id: str | None = None,
    is_resumed: bool = False,
    initial_prompt: str | None = None,
) -> None:
    """Run the CLI interface with Rich UI in a while loop (No Textual)."""
    model = create_model(model_name_override="gemini-3-pro-preview")

    # Sessiya haqida ma'lumot
    if is_resumed:
        console.print(Panel(f"[bold green]Suhbat tiklandi[/bold green]\nThread ID: [cyan]{thread_id}[/cyan]", title="DeepAgents CLI"))
    else:
        console.print(Panel(f"[bold blue]Yangi sessiya[/bold blue]\nThread ID: [cyan]{thread_id}[/cyan]", title="DeepAgents CLI"))

    # Checkpointer bilan ishlash
    async with get_checkpointer() as checkpointer:
        # Tools sozlash
        tools = [http_request, fetch_url]
        if settings.has_tavily:
            tools.append(web_search)

        # Sandbox sozlash
        sandbox_backend = None
        sandbox_cm = None

        if sandbox_type != "none":
            try:
                console.print(f"[yellow]Sandbox ({sandbox_type}) ishga tushirilmoqda...[/yellow]")
                sandbox_cm = create_sandbox(sandbox_type, sandbox_id=sandbox_id)
                sandbox_backend = sandbox_cm.__enter__()
                console.print(f"[green]Sandbox ulandi![/green]")
            except Exception as e:
                console.print(f"[bold red]Sandbox xatoligi:[/bold red] {e}")
                sys.exit(1)

        try:
            # Agentni yaratish
            agent, _ = create_cli_agent(
                model=model,
                assistant_id=assistant_id,
                tools=tools,
                sandbox=sandbox_backend,
                sandbox_type=sandbox_type if sandbox_type != "none" else None,
                auto_approve=auto_approve,
                checkpointer=checkpointer,
            )

            config = {"configurable": {"thread_id": thread_id}}

            # --- Yordamchi funksiya: Javobni Stream qilish ---
            async def process_input(user_input: str):
                console.print(f"\n[bold blue]Siz:[/bold blue] {user_input}")
                
                from langgraph.types import Command
                
                # Input for the agent
                current_input = {"messages": [HumanMessage(content=user_input)]}
                
                while True:
                    # Stream uchun o'zgaruvchilar
                    current_tool = None
                    full_response = ""
                    tool_call_id = None
                    
                    # rich.Live orqali jonli yangilanish
                    with Live(console=console, refresh_per_second=10) as live:
                        async for event in agent.astream_events(
                            current_input,
                            config,
                            version="v1"
                        ):
                            kind = event["event"]
                            
                            # 1. Agent Tool ishlatmoqchi bo'lsa
                            if kind == "on_tool_start":
                                current_tool = event["name"]
                                data = event.get("data")
                                inputs = data.get("input") if isinstance(data, dict) else str(data)
                                live.update(Panel(f"🛠️ [cyan]{current_tool}[/cyan] ishlatilmoqda...\nInput: {inputs}", style="yellow"))
                            
                            # 2. Tool ishlab bo'lgach
                            elif kind == "on_tool_end":
                                data = event.get("data")
                                output = str(data.get("output")) if isinstance(data, dict) else str(data)
                                # Agar output juda uzun bo'lsa qisqartiramiz
                                display_output = (output[:200] + "...") if len(output) > 200 else output
                                console.print(f"[dim]✅ Tool ({event['name']}) natijasi: {display_output}[/dim]")
                                live.update(Text("Agent o'ylamoqda...", style="green"))

                            # 3. Agent javob yozayotganda (Token stream)
                            elif kind == "on_chat_model_stream":
                                data = event.get("data")
                                if isinstance(data, dict):
                                    chunk = data.get("chunk")
                                    content = chunk.content if hasattr(chunk, "content") else str(chunk)
                                    if content:
                                        if isinstance(content, list):
                                            # Handle list content (e.g. from Gemini)
                                            text_parts = []
                                            for item in content:
                                                if isinstance(item, dict) and "text" in item:
                                                    text_parts.append(item["text"])
                                                elif isinstance(item, str):
                                                    text_parts.append(item)
                                                else:
                                                    text_parts.append(str(item))
                                            content = "".join(text_parts)
                                        full_response += content
                                        # Markdown formatida jonli ko'rsatish
                                        live.update(Markdown(full_response))

                    # Yakuniy javobni chiroyli chiqarish (Live tugagach)
                    if full_response:
                        console.print(Panel(Markdown(full_response), title="Agent", border_style="green"))
                    
                    # Check for interrupts (HITL)
                    snapshot = await agent.aget_state(config)
                    if snapshot.next:
                        # Agent to'xtab qoldi (permission kutyapti)
                        console.print("\n[bold yellow]⚠️  Agent ruxsat so'ramoqda:[/bold yellow]")
                        
                        # Inspect interrupts to get ID and details
                        # We assume the first interrupt is the one we care about for now
                        interrupt_id = None
                        try:
                            for task in snapshot.tasks:
                                if task.interrupts:
                                    for interrupt in task.interrupts:
                                        interrupt_id = interrupt.id
                                        # Optional: Inspect interrupt.value for more details
                                        break
                                if interrupt_id:      
                                    break
                        except Exception as e:
                            console.print(f"[red]Interruptni o'qishda xatolik: {e}[/red]")

                        decision = console.input("[bold yellow]Tasdiqlaysizmi? (y/n) > [/bold yellow]").lower().strip()
                        
                        action_type = "approve" if decision in ["y", "yes", "ha", "h"] else "reject"
                        
                        if action_type == "approve":
                            console.print("[green]Tasdiqlandi ✅[/green]")
                        else:
                            console.print("[red]Rad etildi ❌[/red]")
                        
                        # Construct payload expected by deepagents logic
                        # Based on textual_adapter.py: {"decisions": [{"type": "approve"}]}
                        # Note: If multiple tool calls are pending, we might need multiple decisions in the list.
                        # For simple runner, we assume one 'approve' applies to the batch or the single interrupt.
                        
                        # We specifically need to match the structure deepagents expects.
                        # If interrupt_id is found, we should key by it.
                        resume_payload = {"decisions": [{"type": action_type}]} 
                        
                        if interrupt_id:
                            # If LangGraph expects {interrupt_id: value}
                            current_input = Command(resume={interrupt_id: resume_payload})
                        else:
                            # Fallback if no ID found (unlikely if interrupted)
                            current_input = Command(resume=resume_payload)
                        
                        # Loop continues with new input (Command)
                        continue
                    else:
                        # Agent o'z ishini tugatdi
                        break

            # --- Boshlang'ich promptni ishlash ---
            if initial_prompt:
                await process_input(initial_prompt)

            # --- ASOSIY WHILE LOOP ---
            while True:
                try:
                    query = console.input("\n[bold yellow]Buyruq kiritish > [/bold yellow]")
                    
                    # Chiqish komandalari
                    if query.lower().strip() in ["exit", "quit", "q", "/quit"]:
                        console.print("[bold red]Xayr![/bold red]")
                        break
                    
                    if not query.strip():
                        continue

                    # Buyruqni qayta ishlash
                    await process_input(query)

                except KeyboardInterrupt:
                    console.print("\n[yellow]To'xtatildi. Chiqish uchun 'exit' deb yozing.[/yellow]")
                    continue
                except Exception as e:
                    console.print(f"[bold red]Xatolik yuz berdi:[/bold red] {e}")

        except Exception as e:
            console.print(f"[bold red]Agentni yaratishda xatolik:[/bold red] {e}")
            sys.exit(1)
        finally:
            if sandbox_cm is not None:
                with contextlib.suppress(Exception):
                    sandbox_cm.__exit__(None, None, None)

def cli_main() -> None:
    """Entry point for console script."""
    # Fix for gRPC fork issue on macOS
    # https://github.com/grpc/grpc/issues/37642
    if sys.platform == "darwin":
        os.environ["GRPC_ENABLE_FORK_SUPPORT"] = "0"


    try:
        args = parse_args()

        if args.command == "help":
            show_help()
        elif args.command == "list":
            list_agents()
        elif args.command == "reset":
            reset_agent(args.agent, args.source_agent)
        elif args.command == "skills":
            execute_skills_command(args)
        elif args.command == "threads":
            if args.threads_command == "list":
                asyncio.run(
                    list_threads_command(
                        agent_name=getattr(args, "agent", None),
                        limit=getattr(args, "limit", 20),
                    )
                )
            elif args.threads_command == "delete":
                asyncio.run(delete_thread_command(args.thread_id))
            else:
                console.print("[yellow]Usage: deepagents threads <list|delete>[/yellow]")
        else:
            # Interactive mode - handle thread resume
            thread_id = None
            is_resumed = False

            if args.resume_thread == "__MOST_RECENT__":
                # -r (no ID): Get most recent thread
                # If --agent specified, filter by that agent; otherwise get most recent overall
                agent_filter = args.agent if args.agent != "agent" else None
                thread_id = asyncio.run(get_most_recent(agent_filter))
                if thread_id:
                    is_resumed = True
                    agent_name = asyncio.run(get_thread_agent(thread_id))
                    if agent_name:
                        args.agent = agent_name
                else:
                    if agent_filter:
                        msg = Text("No previous thread for '", style="yellow")
                        msg.append(args.agent)
                        msg.append("', starting new.", style="yellow")
                    else:
                        msg = Text("No previous threads, starting new.", style="yellow")
                    console.print(msg)

            elif args.resume_thread:
                # -r <ID>: Resume specific thread
                if asyncio.run(thread_exists(args.resume_thread)):
                    thread_id = args.resume_thread
                    is_resumed = True
                    if args.agent == "agent":
                        agent_name = asyncio.run(get_thread_agent(thread_id))
                        if agent_name:
                            args.agent = agent_name
                else:
                    error_msg = Text("Thread '", style="red")
                    error_msg.append(args.resume_thread)
                    error_msg.append("' not found.", style="red")
                    console.print(error_msg)
                    console.print(
                        "[dim]Use 'deepagents threads list' to see available threads.[/dim]"
                    )
                    sys.exit(1)

            # Generate new thread ID if not resuming
            if thread_id is None:
                thread_id = generate_thread_id()

            # Run Textual CLI
            asyncio.run(
                run_textual_cli_async(
                    assistant_id=args.agent,
                    auto_approve=args.auto_approve,  # Use args.auto_approve instead of hardcoded True
                    sandbox_type=args.sandbox,
                    sandbox_id=args.sandbox_id,
                    model_name="gemini-3-pro-preview",
                    thread_id=thread_id,
                    is_resumed=is_resumed,
                    initial_prompt=getattr(args, "initial_prompt", None),
                )
            )
    except KeyboardInterrupt:
        # Clean exit on Ctrl+C - suppress ugly traceback
        console.print("\n\n[yellow]Interrupted[/yellow]")
        sys.exit(0)


if __name__ == "__main__":
    cli_main()
