import json
import platform
import subprocess
import uuid

from src.config.constants import (
    ASSETS_DIR,
    GAME_DIR,
    CLIENT_JAR,
    LIBRARIES_DIR,
    MANIFEST_JSON,
    NATIVES_DIR,
    OS_NAME,
)
from src.utils.logging import log
from src.downloader.downloader import is_download_complete


def launch_minecraft(username):
    """Lanza Minecraft con el usuario especificado"""
    if not is_download_complete():
        log("Primero debes descargar Minecraft.", error=True)
        return False

    # Leer manifest para obtener asset_index_id
    try:
        with open(MANIFEST_JSON, "r") as f:
            manifest = json.load(f)
            asset_index_id = manifest.get("assetIndex", {}).get("id", "1.21.5")
    except Exception as e:
        log(f"Error al leer el manifest: {e}", error=True)
        return False

    # Generar UUID y token ficticio
    player_uuid = str(uuid.uuid4())
    access_token = str(uuid.uuid4())

    java_path = "java"

    # Construir classpath
    classpath_separator = ";" if platform.system().lower() == "windows" else ":"

    # Recopilar todas las bibliotecas
    library_paths = list(LIBRARIES_DIR.rglob("*.jar"))
    classpath = f"{CLIENT_JAR}{classpath_separator}{classpath_separator.join([str(path) for path in library_paths])}"

    # Construir argumentos
    args = [java_path]

    # Agregar '-XstartOnFirstThread' solo si es macOS
    if OS_NAME == "darwin":
        args.append("-XstartOnFirstThread")

    # Argumentos comunes
    args.extend(
        [
            f"-Djava.library.path={NATIVES_DIR}",
            "-cp",
            classpath,
            "net.minecraft.client.main.Main",
            "--username",
            username,
            "--version",
            "1.21.5",
            "--gameDir",
            str(GAME_DIR),
            "--assetsDir",
            str(ASSETS_DIR),
            "--assetIndex",
            asset_index_id,
            "--uuid",
            player_uuid,
            "--accessToken",
            access_token,
        ]
    )

    log(f"Lanzando Minecraft con usuario: {username}")
    log(f"Comando: {' '.join(str(arg) for arg in args)}")

    try:
        print("\nIniciando Minecraft... 🚀")
        subprocess.run(args)
        return True
    except FileNotFoundError:
        log("Java no está instalado o no está en PATH.", error=True)
        print("\n❌ ERROR: Java no está instalado o no está en PATH.")
        print("Por favor, instala Java y asegúrate de que esté en tu PATH.")
        return False
    except Exception as e:
        log(f"Error al iniciar Minecraft: {e}", error=True)
        print(f"\n❌ ERROR al iniciar Minecraft: {e}")
        return False
