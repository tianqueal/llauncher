import sys
import threading
from datetime import datetime
from pathlib import Path

from src.config.constants import LOGS_DIR

# Variables globales para logging
log_filename = None
log_file = None
log_lock = threading.Lock()  # Para evitar conflictos al escribir en el log


def initialize_logging():
    """Inicializa el sistema de logging"""
    global log_filename, log_file

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_filename = LOGS_DIR / f'll_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    log_file = open(log_filename, "w")

    return log_filename


def log(message, error=False):
    """Registra un mensaje en el archivo de registro y lo imprime en la consola"""
    with log_lock:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"{timestamp} - {'ERROR' if error else 'INFO'} - {message}"

        if log_file:
            log_file.write(log_message + "\n")
            log_file.flush()

        # Si es un error, imprimir en stderr
        if error:
            print(f"\033[91m{message}\033[0m", file=sys.stderr)
        else:
            print(message)


def close_log():
    """Cierra el archivo de log"""
    global log_file
    if log_file:
        log_file.close()
        log_file = None


def get_log_content(num_lines=20):
    """Obtiene las últimas líneas del archivo de log"""
    try:
        with open(log_filename, "r") as f:
            log_content = f.readlines()
            return (
                log_content[-num_lines:]
                if len(log_content) > num_lines
                else log_content
            )
    except Exception as e:
        return [f"Error al leer el archivo de registro: {e}"]
