from pathlib import Path
import shutil
import tempfile
import os

from src.utils.logging import log


def prompt_yes_no(message):
    """Pregunta clásica de sí/no"""
    while True:
        answer = input(message + " (y/n): ").lower()
        if answer in ("y", "n"):
            return answer == "y"
        print("Por favor responde 'y' o 'n'.")


def remove_directory_recursively(path):
    """Elimina un directorio y todo su contenido de forma recursiva"""
    path = Path(path)  # Asegurarse de que es un objeto Path

    if path.is_file() or path.is_symlink():
        path.unlink()
    elif path.is_dir():
        for child in path.iterdir():
            remove_directory_recursively(child)
        path.rmdir()

    return True


def safe_write_file(file_path, content, mode="w"):
    """Escribe contenido en un archivo de manera segura, usando un archivo temporal"""
    file_path = Path(file_path)

    # Crear directorio si no existe
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Usar archivo temporal para escritura atómica
    with tempfile.NamedTemporaryFile(
        mode=mode, delete=False, dir=file_path.parent
    ) as temp_file:
        temp_file.write(content)
        temp_path = temp_file.name

    # Mover el archivo temporal sobre el archivo final (operación atómica)
    try:
        shutil.move(temp_path, file_path)
        return True
    except Exception as e:
        log(f"Error al escribir archivo {file_path}: {e}", error=True)
        try:
            os.remove(temp_path)  # Limpiar archivo temporal en caso de error
        except:
            pass
        return False


def safe_read_file(file_path, mode="r", default=None):
    """Lee un archivo de manera segura"""
    try:
        with open(file_path, mode) as f:
            return f.read()
    except Exception as e:
        log(f"Error al leer archivo {file_path}: {e}", error=True)
        return default
