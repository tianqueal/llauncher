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
        table.add_row(
            "4",
            "Calidad gráfica",
            settings.get("graphics_quality", "high"),
            "Nivel de calidad gráfica (low, medium, high)",
        )
        table.add_row(
            "5",
            "Memoria para Minecraft",
            f"{settings.get('memory_mb', 2048)} MB",
            "Cantidad de RAM para Minecraft (512-8192 MB)",
        )
        table.add_row(
            "6",
            "Ruta de Java",
            settings.get("java_path", "java"),
            "Ruta al ejecutable de Java",
        )
        table.add_row("7", "Volver al menú principal", "", "")

        console.print(table)

        # Importar la función para verificar Java (mostrando estado actual)
        from src.launcher.game_launcher import is_java_available, find_java_path

        java_path = find_java_path()
        java_status = "Disponible ✅" if is_java_available() else "No disponible ❌"
        console.print(
            f"[cyan]Estado actual de Java: [{'green' if is_java_available() else 'red'}]{java_status}"
        )
        console.print(f"[cyan]Ruta actual: [yellow]{java_path}")

        # Solicitar la opción al usuario
        option = Prompt.ask(
            "Selecciona una opción para modificar",
            choices=["1", "2", "3", "4", "5", "6", "7"],
            default="7",
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
            # Modificar calidad gráfica
            current = settings.get("graphics_quality", "high")
            quality_options = ["low", "medium", "high"]

            table = Table(title="Niveles de Calidad Gráfica")
            table.add_column("Nivel", style="cyan")
            table.add_column("Descripción", style="yellow")
            table.add_column("Tamaño", style="green")

            table.add_row(
                "low",
                "Texturas básicas, sin sonidos ambientales ni música",
                "~40% menos de espacio",
            )
            table.add_row(
                "medium",
                "Casi todas las texturas, menos efectos avanzados",
                "~20% menos de espacio",
            )
            table.add_row(
                "high", "Todas las texturas, efectos y sonidos", "Instalación completa"
            )

            console.print(table)
            console.print(
                "[yellow]Nota: Cambiar esta configuración afectará a la próxima descarga."
            )

            new_quality = Prompt.ask(
                "Selecciona el nivel de calidad gráfica",
                choices=quality_options,
                default=current,
            )

            settings["graphics_quality"] = new_quality

        elif option == "5":
            # Modificar memoria para Minecraft
            current = settings.get("memory_mb", 2048)

            # Detectar memoria disponible en el sistema
            try:
                import psutil

                total_ram = psutil.virtual_memory().total // (1024 * 1024)  # En MB
                max_suggested = min(
                    8192, int(total_ram * 0.75)
                )  # 75% del total o 8GB max

                console.print(f"[cyan]Memoria RAM total detectada: {total_ram} MB")
                console.print(f"[green]Recomendada: {max_suggested} MB (75% del total)")
            except ImportError:
                max_suggested = 4096
                console.print(
                    "[yellow]No se pudo detectar la memoria del sistema. psutil no está disponible."
                )
                console.print(
                    "[yellow]Si necesitas asignar más memoria, instala psutil: pip install psutil"
                )

            while True:
                try:
                    value = int(
                        Prompt.ask(
                            f"Ingresa la cantidad de RAM para Minecraft (512-{max_suggested} MB)",
                            default=str(current),
                        )
                    )
                    if 512 <= value <= max_suggested:
                        settings["memory_mb"] = value
                        break
                    else:
                        console.print(
                            f"[bold red]El valor debe estar entre 512 y {max_suggested} MB."
                        )
                except ValueError:
                    console.print("[bold red]Por favor, ingresa un número válido.")

        elif option == "6":
            # Configurar ruta de Java
            current = settings.get("java_path", "java")
            console.print("[bold cyan]Configuración de Java[/bold cyan]")
            console.print(
                "[yellow]Deja el campo vacío para usar 'java' del PATH del sistema."
            )

            if current != "java":
                console.print(f"[green]Ruta actual: {current}")
            else:
                console.print(
                    f"[yellow]Actualmente usando 'java' del PATH del sistema."
                )

            # Mostrar sugerencias de rutas comunes para Java según el SO
            import platform

            system = platform.system().lower()

            if system == "darwin":  # macOS
                console.print("[bold cyan]Rutas típicas de Java en macOS:[/bold cyan]")
                console.print(
                    "  • [yellow]/opt/homebrew/opt/openjdk/bin/java[/yellow] (Homebrew en Apple Silicon)"
                )
                console.print(
                    "  • [yellow]/usr/local/opt/openjdk/bin/java[/yellow] (Homebrew en Intel Mac)"
                )
                console.print(
                    "  • [yellow]/Library/Java/JavaVirtualMachines/<version>/Contents/Home/bin/java[/yellow]"
                )

                # Intentar detectar instalaciones de Java con Homebrew
                import subprocess

                try:
                    # Verificar Homebrew
                    brew_paths = []
                    brew_process = subprocess.run(
                        ["brew", "--prefix", "openjdk"],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if brew_process.returncode == 0:
                        brew_path = brew_process.stdout.strip()
                        if brew_path:
                            java_path = f"{brew_path}/bin/java"
                            from pathlib import Path

                            if Path(java_path).exists():
                                brew_paths.append(java_path)
                                console.print(
                                    f"[green]✓ Detectada instalación de Java con Homebrew: {java_path}"
                                )

                    if brew_paths:
                        console.print(
                            "[yellow]Puedes usar una de las rutas detectadas o ingresar otra manualmente."
                        )
                except:
                    pass

            elif system == "windows":
                console.print(
                    "[bold cyan]Rutas típicas de Java en Windows:[/bold cyan]"
                )
                console.print(
                    "  • [yellow]C:\\Program Files\\Java\\jre<version>\\bin\\java.exe[/yellow] (Oracle Java)"
                )
                console.print(
                    "  • [yellow]C:\\Program Files\\Java\\jdk<version>\\bin\\java.exe[/yellow] (Oracle JDK)"
                )

                # Añadir información específica para winget
                console.print(
                    "\n[bold cyan]Rutas típicas de instalaciones con winget:[/bold cyan]"
                )
                console.print(
                    "  • [yellow]C:\\Program Files\\Eclipse Adoptium\\jdk-<version>\\bin\\java.exe[/yellow] (Eclipse Temurin)"
                )
                console.print(
                    "  • [yellow]C:\\Program Files\\Microsoft\\jdk-<version>\\bin\\java.exe[/yellow] (Microsoft OpenJDK)"
                )
                console.print(
                    "  • [yellow]C:\\Program Files\\BellSoft\\LibericaJDK-<version>\\bin\\java.exe[/yellow] (Liberica JDK)"
                )
                console.print(
                    "  • [yellow]C:\\Program Files\\Amazon Corretto\\<version>\\bin\\java.exe[/yellow] (Amazon Corretto)"
                )

                # Intentar detectar instalaciones típicas de winget
                import subprocess

                try:
                    # Verificar si winget está disponible
                    winget_process = subprocess.run(
                        ["where", "winget"], capture_output=True, text=True, check=False
                    )

                    if winget_process.returncode == 0:
                        console.print("[green]✓ Winget detectado en el sistema")

                        # Intentar listar las instalaciones de Java mediante winget
                        winget_list = subprocess.run(
                            [
                                "winget",
                                "list",
                                "--query",
                                "java",
                                "--accept-source-agreements",
                            ],
                            capture_output=True,
                            text=True,
                            check=False,
                        )

                        if (
                            winget_list.returncode == 0
                            and "adoptium" in winget_list.stdout.lower()
                        ):
                            console.print(
                                "[green]✓ Detectada instalación de Java con winget (Eclipse Adoptium/Temurin)"
                            )

                        if (
                            winget_list.returncode == 0
                            and "microsoft" in winget_list.stdout.lower()
                        ):
                            console.print(
                                "[green]✓ Detectada instalación de Java con winget (Microsoft OpenJDK)"
                            )

                        if (
                            winget_list.returncode == 0
                            and "corretto" in winget_list.stdout.lower()
                        ):
                            console.print(
                                "[green]✓ Detectada instalación de Java con winget (Amazon Corretto)"
                            )

                        if (
                            winget_list.returncode == 0
                            and "liberica" in winget_list.stdout.lower()
                            or "bellsoft" in winget_list.stdout.lower()
                        ):
                            console.print(
                                "[green]✓ Detectada instalación de Java con winget (Liberica JDK)"
                            )
                except:
                    pass  # No mostrar errores si winget no está disponible

            elif system == "linux":
                console.print("[bold cyan]Rutas típicas de Java en Linux:[/bold cyan]")
                console.print("  • [yellow]/usr/bin/java[/yellow]")
                console.print("  • [yellow]/usr/lib/jvm/<version>/bin/java[/yellow]")

            # Solicitar la nueva ruta
            new_path = Prompt.ask(
                "Ingresa la ruta completa al ejecutable de Java", default=current
            )

            # Si el usuario ingresó algo, verificar que exista
            if new_path and new_path != "java":
                from pathlib import Path

                java_exists = Path(new_path).exists()

                if java_exists:
                    settings["java_path"] = new_path
                    console.print(f"[green]✓ Ruta configurada: {new_path}")

                    # Verificar si es ejecutable
                    try:
                        from src.launcher.game_launcher import is_java_available

                        old_path = settings["java_path"]
                        settings["java_path"] = new_path
                        set_setting(
                            "java_path", new_path
                        )  # Guardar temporalmente para probar

                        if is_java_available():
                            console.print("[green]✓ ¡Java verificado correctamente!")
                        else:
                            console.print(
                                "[bold yellow]⚠️ La ruta existe pero Java no responde correctamente."
                            )
                            if Confirm.ask(
                                "[yellow]¿Quieres usar esta ruta de todas formas?"
                            ):
                                console.print("[yellow]Se usará la ruta especificada.")
                            else:
                                settings["java_path"] = old_path
                                set_setting("java_path", old_path)
                                console.print("[yellow]Se mantendrá la ruta anterior.")
                    except Exception as e:
                        console.print(f"[bold red]Error al verificar Java: {e}")
                else:
                    if Confirm.ask(
                        f"[bold yellow]⚠️ La ruta '{new_path}' no existe. ¿Deseas usarla de todas formas?"
                    ):
                        settings["java_path"] = new_path
                        console.print(
                            f"[yellow]Se usará la ruta especificada aunque no existe actualmente."
                        )
                    else:
                        console.print("[yellow]Se mantendrá la ruta anterior.")
            else:
                # Si el usuario dejó vacío o "java", usar el valor predeterminado
                settings["java_path"] = "java"
                console.print("[green]✓ Se usará 'java' del PATH del sistema.")

        elif option == "7":
            # Guardar los cambios y volver al menú principal
            for key in [
                "max_workers",
                "logs_to_keep",
                "username",
                "graphics_quality",
                "memory_mb",
                "java_path",
            ]:
                if key in settings:
                    set_setting(key, settings[key])
            console.print("[bold green]✅ Configuración guardada correctamente.")
            break

        # Guardar después de cada cambio
        for key in [
            "max_workers",
            "logs_to_keep",
            "username",
            "graphics_quality",
            "memory_mb",
            "java_path",
        ]:
            if key in settings:
                set_setting(key, settings[key])

    input("\nPresiona Enter para continuar...")
