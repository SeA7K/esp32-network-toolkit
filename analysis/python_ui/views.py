# python_ui/views.py

from rich.panel import Panel
from rich.table import Table
from rich.console import Console
from config import COLORS

console = Console()

def title(text: str):
    console.print(Panel(text, style=COLORS["title"]))

def message(text: str, level="info"):
    console.print(f"[{COLORS[level]}]{text}[/]")

def show_logs(files: list[str]):
    table = Table(title="Letzte Logs")
    table.add_column("Datei", style="cyan")

    for f in files:
        table.add_row(f)

    console.print(table)
