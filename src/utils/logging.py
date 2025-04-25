import sys
import threading
import os
from datetime import datetime, timedelta
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

    # Limpiar logs antiguos (más de 7 días)
    cleanup_old_logs()

    return log_filename


def log(message, error=False, console_output=True):
    """Registra un mensaje en el archivo de registro y lo imprime en la consola si console_output es True"""
    with log_lock:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"{timestamp} - {'ERROR' if error else 'INFO'} - {message}"

        if log_file:
            log_file.write(log_message + "\n")
            log_file.flush()

        # Solo mostrar en la consola si console_output es True
        if console_output:
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
        if not log_filename or not log_filename.exists():
            return ["No hay archivo de registro disponible"]

        with open(log_filename, "r") as f:
            log_content = f.readlines()
            return (
                log_content[-num_lines:]
                if len(log_content) > num_lines
                else log_content
            )
    except Exception as e:
        return [f"Error al leer el archivo de registro: {e}"]


def cleanup_old_logs(days_to_keep=7):
    """Elimina archivos de logs más antiguos que el número de días especificado"""
    try:
        now = datetime.now()
        cutoff_date = now - timedelta(days=days_to_keep)

        # Patrones de archivos de log a limpiar
        log_patterns = ["ll_*.log", "*.log.gz", "20??-??-??-?.log.gz"]

        for pattern in log_patterns:
            for log_file in LOGS_DIR.glob(pattern):
                try:
                    # Para archivos con formato ll_YYYYMMDD_HHMMSS.log
                    if log_file.name.startswith("ll_"):
                        file_date_str = log_file.stem.split("_")[1]
                        file_date = datetime.strptime(file_date_str, "%Y%m%d")
                    # Para archivos con formato YYYY-MM-DD-N.log.gz
                    elif "-" in log_file.name:
                        date_part = log_file.name.split("-")
                        if len(date_part) >= 3:
                            try:
                                year = int(date_part[0])
                                month = int(date_part[1])
                                day = int(date_part[2].split(".")[0])
                                file_date = datetime(year, month, day)
                            except (ValueError, IndexError):
                                continue
                    else:
                        # No podemos determinar la fecha, ignorar
                        continue

                    if file_date < cutoff_date:
                        log_file.unlink()
                        log(f"Eliminado log antiguo: {log_file.name}")
                except (IndexError, ValueError):
                    # Si el formato del nombre no coincide, ignoramos el archivo
                    continue
    except Exception as e:
        log(f"Error al limpiar logs antiguos: {e}", error=True)
