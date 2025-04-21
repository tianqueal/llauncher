import json
import os
from pathlib import Path

from src.config.constants import CONFIG_DIR, CONFIG_FILE
from src.utils.logging import log

# Valores predeterminados de configuración
DEFAULT_SETTINGS = {
    "max_workers": 10,
    "theme": "default",
    "logs_to_keep": 20,
    "username": "Player",
}


def ensure_config_dir():
    """Asegura que el directorio de configuración exista"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_settings():
    """Carga la configuración del archivo. Si no existe, crea un archivo con valores predeterminados."""
    ensure_config_dir()

    if not CONFIG_FILE.exists():
        log(
            "Archivo de configuración no encontrado. Creando uno con valores predeterminados."
        )
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)

        # Asegurar que todas las claves necesarias estén presentes
        for key, default_value in DEFAULT_SETTINGS.items():
            if key not in settings:
                settings[key] = default_value

        return settings
    except (json.JSONDecodeError, IOError) as e:
        log(f"Error al cargar la configuración: {e}", error=True)
        log("Restaurando valores predeterminados")
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()


def save_settings(settings):
    """Guarda la configuración en el archivo"""
    ensure_config_dir()

    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
        log("Configuración guardada correctamente")
        return True
    except IOError as e:
        log(f"Error al guardar la configuración: {e}", error=True)
        return False


def get_setting(key, default=None):
    """Obtiene un valor específico de la configuración"""
    settings = load_settings()
    return settings.get(key, default)


def set_setting(key, value):
    """Establece un valor específico en la configuración y lo guarda"""
    settings = load_settings()
    settings[key] = value
    return save_settings(settings)
