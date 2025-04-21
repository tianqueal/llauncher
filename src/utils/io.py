from pathlib import Path

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
