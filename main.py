#!/usr/bin/env python
"""
LLauncher - Un lanzador de Minecraft simple y personalizable
"""
import os
import platform
import sys

from src.config.constants import CLIENT_JAR, LIBRARIES_DIR, ASSETS_DIR
from src.utils.logging import initialize_logging, log, close_log
from src.ui.menu import show_menu
from src.downloader.downloader import set_download_complete


def main():
    """Función principal que inicia el lanzador"""
    try:
        # Inicializar sistema de logging
        log_filename = initialize_logging()

        # Mostrar información del sistema
        log(f"Sistema: {platform.system()} {platform.release()}")
        log(f"Python: {sys.version}")
        log(f"Directorio actual: {os.getcwd()}")

        # Verificar descarga existente
        if CLIENT_JAR.exists() and LIBRARIES_DIR.exists() and ASSETS_DIR.exists():
            log("Instalación existente de Minecraft detectada")
            set_download_complete(True)

        # Mostrar menú principal
        show_menu()

    except Exception as e:
        log(f"Error crítico: {e}", error=True)
    finally:
        log("Aplicación finalizada")
        close_log()


if __name__ == "__main__":
    main()
