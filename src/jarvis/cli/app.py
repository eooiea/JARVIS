import sys
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from jarvis.brain.planner import TaskPlan, PlanStep
from jarvis.utils.config import JarvisConfig, load_config

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

console = Console(legacy_windows=False)


class JarvisCLI:
    """Provides high-aesthetic terminal interactions using Rich."""

    def __init__(self, config: Optional[JarvisConfig] = None):
        self.config = config or load_config()

    def print_banner(self):
        """Display JARVIS startup banner and active environment details."""
        banner_text = (
            "[bold cyan]🤖 JARVIS AI Desktop Assistant (v0.1.0)[/]\n"
            "[dim]Windows Personal Autonomous Automation System[/]\n"
            f"[dim]• Cloud Model:[/] [green]{self.config.llm.gemini.model}[/]\n"
            f"[dim]• Local Model:[/] [yellow]{self.config.llm.ollama.model}[/]\n"
            f"[dim]• Output Dir :[/] [blue]{self.config.system.output_dir}/[/]"
        )
        console.print(Panel(banner_text, border_style="cyan", expand=False))

    def render_plan(self, plan: TaskPlan):
        """Render structured task plan report with engine choices."""
        table = Table(title="📋 [JARVIS] 작업 계획 보고서", title_style="bold green", show_lines=True)
        table.add_column("단계", justify="center", style="bold cyan", width=8)
        table.add_column("작업 내용", style="white", width=32)
        table.add_column("처리 엔진 선택지", style="yellow")

        for step in plan.steps:
            options_str = []
            for opt in step.options:
                rec_badge = " [bold green][권장][/]" if opt.recommended else ""
                options_str.append(f"({opt.id}) {opt.name}{rec_badge}\n    [dim]- {opt.description}[/]")
            
            table.add_row(
                f"[{step.step_num}단계]",
                f"[bold]{step.title}[/]\n[dim]{step.description}[/]",
                "\n".join(options_str)
            )

        console.print(table)

    def prompt_step_options(self, plan: TaskPlan, auto_confirm: bool = False) -> TaskPlan:
        """Prompt user to choose engine options for each step."""
        if auto_confirm:
            return plan

        for step in plan.steps:
            default_id = 1
            for opt in step.options:
                if opt.recommended:
                    default_id = opt.id
                    break

            prompt_msg = f"\n👉 [{step.step_num}단계] 어떤 방식으로 진행할까요? (기본값: {default_id})"
            choice_str = Prompt.ask(prompt_msg, default=str(default_id))
            try:
                step.selected_option_id = int(choice_str)
            except ValueError:
                step.selected_option_id = default_id

        return plan

    def print_success(self, title: str, details: str):
        """Print success result card."""
        console.print(Panel(f"[bold green]✔ {title}[/]\n\n{details}", border_style="green", expand=False))

    def print_error(self, title: str, error_msg: str):
        """Print error message card."""
        console.print(Panel(f"[bold red]✘ {title}[/]\n\n{error_msg}", border_style="red", expand=False))
