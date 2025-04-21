"""
Elementos visuales reutilizables para la interfaz de usuario
"""

import platform
from datetime import datetime

from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.text import Text
from rich import box
from art import text2art

from src.downloader.downloader import is_download_complete
from src.config.constants import CLIENT_JAR, MAX_WORKERS
from src.config.settings import get_setting

# Colores y estilos
THEME = {
    "title": "bright_cyan",
    "subtitle": "bright_green",
    "highlight": "bright_yellow",
    "info": "bright_white",
    "success": "green",
    "error": "red",
    "menu_item": "cyan",
    "menu_selected": "bright_yellow",
    "border": "bright_blue",
    "minecraft_green": "#44FF44",  # Color verde Minecraft
    "minecraft_brown": "#825432",  # Color marrón Minecraft
    "progress_bar_bg": "grey23",
    "progress_bar_complete": "green",
}


def get_launcher_logo():
    """Genera un logo colorido del launcher en ASCII art"""
    # Usamos un estilo más legible y distintivo
    logo_text = text2art("LLauncher", font="small")
    logo_colored = Text(logo_text)
    logo_colored.stylize(THEME["minecraft_green"])

    # Obtener el nombre de usuario de la configuración
    username = get_setting("username", "Player")
    subtitle = Text(f"\n🎮 Bienvenid@, {username}! 🚀\n")
    subtitle.stylize(THEME["subtitle"])

    full_logo = Text.assemble(logo_colored, subtitle)
    return Panel(full_logo, title="[bold cyan]LLauncher", border_style=THEME["border"])


def create_status_panel():
    """Crear panel con información de estado del sistema"""
    table = Table(show_header=False, box=box.SIMPLE)

    # Verificar si Minecraft está instalado
    minecraft_status = (
        "[bold green]✓ Instalado"
        if is_download_complete()
        else "[bold red]✗ No instalado"
    )

    # Obtener info del sistema
    system_info = platform.system()
    cpu_info = platform.processor() or "Desconocido"

    # Obtener uso de memoria RAM
    try:
        import psutil

        ram_percent = psutil.virtual_memory().percent
        ram_info = f"[{'green' if ram_percent < 70 else 'yellow' if ram_percent < 90 else 'red'}]{ram_percent}%"
    except:
        ram_info = "N/A"

    # Crear tabla
    table.add_column("Propiedad", style="bright_cyan")
    table.add_column("Valor")

    table.add_row("Estado Minecraft", minecraft_status)
    table.add_row("Sistema", f"[cyan]{system_info}")
    table.add_row(
        "CPU", f"[cyan]{cpu_info[:40]+'...' if len(cpu_info) > 40 else cpu_info}"
    )
    table.add_row("Uso RAM", ram_info)
    table.add_row("Hora", f"[cyan]{datetime.now().strftime('%H:%M:%S')}")

    return Panel(
        table, title="[bold cyan]Estado del Sistema", border_style=THEME["border"]
    )


def create_menu_panel(options, menu_title="Menú Principal"):
    """Crear panel con opciones del menú estilizadas"""
    menu_text = ""
    for i, option in enumerate(options, 1):
        menu_text += f"[{THEME['menu_item']}]{i}. {option}[/{THEME['menu_item']}]\n"

    return Panel(
        menu_text, title=f"[bold cyan]{menu_title}", border_style=THEME["border"]
    )


def create_info_panel():
    """Crear panel con información general"""
    info_text = (
        "[cyan]LLauncher[/cyan] - Versión [bright_cyan]1.21.5[/bright_cyan]\n\n"
        "Ingresa el [bright_yellow]número[/bright_yellow] de la opción deseada "
        "y presiona [bright_yellow]Enter[/bright_yellow] para seleccionar.\n\n"
        "Presiona [bright_yellow]Ctrl+C[/bright_yellow] para salir."
    )
    return Panel(
        info_text, title="[bold cyan]Información", border_style=THEME["border"]
    )


def create_main_layout():
    """Crea el layout principal de la interfaz"""
    layout = Layout()
    layout.split_column(
        Layout(name="logo"),
        Layout(name="body"),
        # Layout(name="footer")
    )

    # Split body en dos columnas
    layout["body"].split_row(
        Layout(name="menu", ratio=2), Layout(name="sidebar", ratio=1)
    )

    # Split sidebar en dos
    layout["sidebar"].split_column(Layout(name="status"), Layout(name="info"))

    return layout


def create_footer_panel():
    """Crea el panel de pie de página"""
    footer_text = (
        f"[{THEME['info']}]LLauncher v1.21.5 | Python {platform.python_version()}"
    )
    return Panel(footer_text, border_style=THEME["border"])
