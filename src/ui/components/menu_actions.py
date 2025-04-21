"""
Módulo para las funciones que manejan las acciones del menú
"""

import os
import threading
import time

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.prompt import Confirm, Prompt
from rich import box

from src.config.constants import CLIENT_JAR, GAME_DIR
from src.config.settings import get_setting, set_setting, load_settings
from src.downloader.downloader import (
    download_minecraft,
    is_download_complete,
    set_download_complete,
)
from src.launcher.game_launcher import launch_minecraft
from src.utils.io import remove_directory_recursively
from src.utils.logging import log, get_log_content

# Consola para mostrar mensajes
console = Console()


def clear_screen():
    """Limpia la pantalla de manera compatible con varios sistemas"""
    os.system("cls" if os.name == "nt" else "clear")


def show_animation(text, duration=3):
    """Muestra una animación de carga con texto"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"[cyan]{text}", total=None)
        time.sleep(duration)


def handle_download():
    """Gestiona la descarga de Minecraft"""
    if not is_download_complete():
        show_download_progress()
    else:
        if Confirm.ask("[yellow]Minecraft ya está descargado. ¿Descargar de nuevo?"):
            set_download_complete(False)
            show_download_progress()


def show_download_progress():
    """Muestra animación mientras se descarga Minecraft"""
    console.print(
        Panel(
            "[cyan]Iniciando descarga de Minecraft...",
            title="[bold green]DESCARGA",
            border_style="green",
        )
    )

    # Iniciar la descarga en un hilo
    max_workers = get_setting("max_workers", 10)  # Usar el valor de la configuración
    download_thread = threading.Thread(target=download_minecraft)
    download_thread.daemon = True
    download_thread.start()

    # Mostrar una animación mientras se descarga
    try:
        with Progress(
            SpinnerColumn(spinner_name="dots12"),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[cyan]Descargando archivos de Minecraft...", total=None
            )

            # Esperar a que termine la descarga
            while download_thread.is_alive():
                progress.update(
                    task, description=f"[cyan]Descargando archivos de Minecraft..."
                )
                time.sleep(0.1)

    except KeyboardInterrupt:
        console.print("[yellow]Descarga interrumpida por el usuario.")
        return

    # Verificar si la descarga fue exitosa
    if is_download_complete():
        console.print("[bold green]¡Descarga completada exitosamente! 🎮")
    else:
        console.print(
            "[bold red]La descarga no se completó correctamente. Revisa el registro para más detalles."
        )

    input("\nPresiona Enter para continuar...")


def handle_launch():
    """Gestiona el lanzamiento de Minecraft"""
    if CLIENT_JAR.exists():
        # Usar el nombre de usuario guardado en la configuración
        default_username = get_setting("username", "Player")
        username = Prompt.ask(
            "\nIngresa tu nombre de usuario", default=default_username
        )

        # Guardar el nombre de usuario en la configuración
        set_setting("username", username)

        if not is_download_complete():
            console.print(
                "[yellow]Parece que Minecraft ya está descargado de una sesión anterior."
            )
            set_download_complete(True)

        console.print(
            Panel(
                f"[bright_green]¡Lanzando Minecraft con el usuario [bold]{username}[/bold]!",
                title="[bold cyan]INICIANDO JUEGO",
                border_style="green",
            )
        )

        launch_minecraft(username)

    else:
        console.print(
            Panel(
                "[bold red]Primero debes descargar Minecraft (opción 1).",
                title="[bold red]ERROR",
                border_style="red",
            )
        )
        input("\nPresiona Enter para continuar...")


def handle_cleanup():
    """Gestiona la eliminación de archivos"""
    if CLIENT_JAR.exists() or GAME_DIR.exists():
        if Confirm.ask("[yellow]¿Eliminar archivos de instalación?"):
            try:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                ) as progress:
                    task = progress.add_task("[cyan]Eliminando archivos...", total=None)
                    log("Iniciando limpieza de archivos")
                    remove_directory_recursively(GAME_DIR)
                    time.sleep(1)  # Dar tiempo para ver la animación

                console.print("[bold green]✅ Archivos de instalación eliminados.")
                set_download_complete(False)
            except Exception as e:
                log(f"Error al eliminar los archivos: {e}", error=True)
                console.print(f"[bold red]❌ Error al eliminar los archivos: {e}")
    else:
        console.print("[bold yellow]No hay archivos de instalación para eliminar.")

    input("\nPresiona Enter para continuar...")


def handle_logs():
    """Muestra el registro de actividad"""
    console.print(
        Panel("[bold cyan]REGISTRO DE ACTIVIDAD".center(50), border_style="blue")
    )

    # Obtener la cantidad de logs a mostrar desde la configuración
    logs_to_keep = get_setting("logs_to_keep", 20)
    log_entries = get_log_content(logs_to_keep)

    for entry in log_entries:
        if "ERROR" in entry or "error" in entry.lower():
            console.print(f"[red]{entry}")
        elif "warn" in entry.lower():
            console.print(f"[yellow]{entry}")
        else:
            console.print(f"[bright_white]{entry}")

    input("\nPresiona Enter para continuar...")


def handle_config():
    """Gestiona la configuración"""
    settings = load_settings()

    while True:
        clear_screen()

        # Mostrar la configuración actual en una tabla
        table = Table(title="Configuración Actual", box=box.ROUNDED)
        table.add_column("ID", style="cyan", width=5)
        table.add_column("Parámetro", style="bright_cyan")
        table.add_column("Valor", style="green")
        table.add_column("Descripción", style="yellow")

        # Añadir filas con las configuraciones disponibles
        table.add_row(
            "1",
            "Descargas Paralelas",
            str(settings.get("max_workers", 10)),
            "Número de archivos que se descargan simultáneamente (3-20)",
        )
        table.add_row(
            "2",
            "Logs a mostrar",
            str(settings.get("logs_to_keep", 20)),
            "Cantidad de líneas de registro a mostrar (5-100)",
        )
        table.add_row(
            "3",
            "Usuario por defecto",
            settings.get("username", "Player"),
            "Nombre de usuario predeterminado",
        )
        table.add_row("4", "Volver al menú principal", "", "")

        console.print(table)

        # Solicitar la opción al usuario
        option = Prompt.ask(
            "Selecciona una opción para modificar",
            choices=["1", "2", "3", "4"],
            default="4",
        )

        if option == "1":
            # Modificar max_workers (validar entre 3 y 20)
            current = settings.get("max_workers", 10)
            while True:
                try:
                    value = int(
                        Prompt.ask(
                            "Ingresa el nuevo número de descargas paralelas (3-20)",
                            default=str(current),
                        )
                    )
                    if 3 <= value <= 20:
                        settings["max_workers"] = value
                        break
                    else:
                        console.print("[bold red]El valor debe estar entre 3 y 20.")
                except ValueError:
                    console.print("[bold red]Por favor, ingresa un número válido.")

        elif option == "2":
            # Modificar logs_to_keep (validar entre 5 y 100)
            current = settings.get("logs_to_keep", 20)
            while True:
                try:
                    value = int(
                        Prompt.ask(
                            "Ingresa la cantidad de líneas de registro a mostrar (5-100)",
                            default=str(current),
                        )
                    )
                    if 5 <= value <= 100:
                        settings["logs_to_keep"] = value
                        break
                    else:
                        console.print("[bold red]El valor debe estar entre 5 y 100.")
                except ValueError:
                    console.print("[bold red]Por favor, ingresa un número válido.")

        elif option == "3":
            # Modificar usuario predeterminado
            current = settings.get("username", "Player")
            new_username = Prompt.ask(
                "Ingresa el nombre de usuario predeterminado", default=current
            )
            settings["username"] = new_username

        elif option == "4":
            # Guardar los cambios y volver al menú principal
            set_setting("max_workers", settings.get("max_workers", 10))
            set_setting("logs_to_keep", settings.get("logs_to_keep", 20))
            set_setting("username", settings.get("username", "Player"))
            console.print("[bold green]✅ Configuración guardada correctamente.")
            break

        # Guardar después de cada cambio
        set_setting("max_workers", settings.get("max_workers", 10))
        set_setting("logs_to_keep", settings.get("logs_to_keep", 20))
        set_setting("username", settings.get("username", "Player"))

    input("\nPresiona Enter para continuar...")
