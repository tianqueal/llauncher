"""
Menú principal del launcher
"""

import os
from rich.console import Console
from rich.prompt import Prompt

from src.config.constants import CLIENT_JAR
from src.config.settings import load_settings, set_setting, get_setting
from src.utils.logging import log, get_log_content
from src.ui.components import (
    get_launcher_logo,
    create_status_panel,
    create_menu_panel,
    create_info_panel,
    create_main_layout,
    create_footer_panel,
    handle_download,
    handle_launch,
    handle_cleanup,
    handle_logs,
    handle_config,
    clear_screen,
)

# Inicializar la consola Rich
console = Console()


def show_menu():
    """Muestra el menú principal interactivo"""
    # Asegurar que la configuración existe
    load_settings()

    # Opciones del menú principal con iconos
    menu_options = [
        "🎮 Descargar Minecraft 1.21.5",
        "🚀 Iniciar Minecraft",
        "🗑️ Eliminar archivos de instalación",
        "📋 Ver registro de actividad",
        "⚙️ Configuración",
        "🚪 Salir",
    ]

    running = True

    while running:
        try:
            clear_screen()

            # Crear layout principal
            layout = create_main_layout()

            # Asignar componentes
            layout["logo"].update(get_launcher_logo())
            layout["menu"].update(create_menu_panel(menu_options))
            layout["status"].update(create_status_panel())
            layout["info"].update(create_info_panel())
            # layout["footer"].update(create_footer_panel())

            # Renderizar layout
            console.print(layout)

            # Método de entrada utilizando prompts de Rich
            try:
                option = Prompt.ask(
                    "Elige una opción",
                    choices=["1", "2", "3", "4", "5", "6"],
                    show_choices=True,
                )

                if option == "1":
                    handle_download()
                elif option == "2":
                    handle_launch()
                elif option == "3":
                    handle_cleanup()
                elif option == "4":
                    handle_logs()
                elif option == "5":
                    handle_config()
                elif option == "6":
                    console.print("[bright_green]¡Gracias por usar LLauncher! 👋")
                    running = False

            except KeyboardInterrupt:
                console.print("\n[bright_green]¡Gracias por usar LLauncher! 👋")
                running = False

        except KeyboardInterrupt:
            console.print("\n[bright_green]¡Gracias por usar LLauncher! 👋")
            running = False
        except Exception as e:
            console.print(f"[bold red]❌ Error inesperado: {e}")
            log(f"Error en el menú principal: {e}", error=True)
            input("\nPresiona Enter para continuar...")
