import json
import os
import platform
import requests
import subprocess
import sys
import uuid
import zipfile
from pathlib import Path

# Configuraciones iniciales
MANIFEST_FILE = "1.21.5.json"
MANIFEST_URL = "https://piston-meta.mojang.com/v1/packages/a0645da8cf4e89da6baaab8e08b7ca64b7f4b0cf/1.21.5.json"
BASE_DIR = Path("minecraft_1.21.5")
LIBRARIES_DIR = BASE_DIR / "libraries"
ASSETS_DIR = BASE_DIR / "assets"
NATIVES_DIR = BASE_DIR / "natives"
CLIENT_JAR = BASE_DIR / "client.jar"


def prompt_yes_no(message):
    """Pregunta clásica de sí/no"""
    while True:
        answer = input(message + " (y/n): ").lower()
        if answer in ("y", "n"):
            return answer == "y"
        print("Por favor responde 'y' o 'n'.")


def download_file(url, dest):
    """Descargar un archivo desde una URL"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(response.content)
        print(f"✅ Descargado {dest}")
    except requests.RequestException as e:
        print(f"❌ Error al descargar {url}: {e}")
        sys.exit(1)


def extract_natives(jar_path):
    """Extrae el contenido de un JAR de natives"""
    try:
        with zipfile.ZipFile(jar_path, "r") as jar:
            for file in jar.namelist():
                if file.startswith("META-INF/"):
                    continue
                jar.extract(file, NATIVES_DIR)
        print(f"📦 Extraído {jar_path.name} en {NATIVES_DIR}")
    except zipfile.BadZipFile:
        print(f"❌ Error: {jar_path} no es un archivo ZIP válido.")


def main():
    print("🚀 Inicio de descarga y preparación de Minecraft")

    # Crear carpetas
    BASE_DIR.mkdir(exist_ok=True)
    LIBRARIES_DIR.mkdir(parents=True, exist_ok=True)
    NATIVES_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    # Descargar manifest si no existe
    if not Path(MANIFEST_FILE).exists():
        print(f"Descargando el archivo manifest desde {MANIFEST_URL}...")
        download_file(MANIFEST_URL, Path(MANIFEST_FILE))
    else:
        print(f"Manifest {MANIFEST_FILE} ya existe, omitiendo descarga.")

    # Leer manifest
    try:
        with open(MANIFEST_FILE, "r") as f:
            manifest = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"❌ Error al leer el manifest: {e}")
        sys.exit(1)

    # Descargar client.jar
    client_url = manifest["downloads"]["client"]["url"]
    print("📥 Descargando client.jar...")
    download_file(client_url, CLIENT_JAR)

    # Descargar librerías
    print("📚 Descargando librerías y natives...")
    libraries = manifest.get("libraries", [])
    os_name = platform.system().lower()  # windows, linux, darwin

    for lib in libraries:
        downloads = lib.get("downloads", {})
        # Descargar librería normal
        if "artifact" in downloads:
            artifact = downloads["artifact"]
            url = artifact["url"]
            path = LIBRARIES_DIR / artifact["path"]
            download_file(url, path)

        # Descargar librería native (si aplica)
        classifiers = downloads.get("classifiers", {})
        native_key = None
        if os_name == "windows":
            native_key = "natives-windows"
        elif os_name == "linux":
            native_key = "natives-linux"
        elif os_name == "darwin":
            native_key = "natives-osx"

        if native_key and native_key in classifiers:
            native = classifiers[native_key]
            url = native["url"]
            path = LIBRARIES_DIR / native["path"]
            download_file(url, path)
            extract_natives(path)

    # Descargar assets
    print("🎨 Descargando assets...")
    asset_index = manifest["assetIndex"]
    asset_index_url = asset_index["url"]
    asset_index_id = asset_index["id"]
    asset_index_path = ASSETS_DIR / "indexes" / f"{asset_index_id}.json"

    # Descargar el índice de assets
    download_file(asset_index_url, asset_index_path)

    # Leer asset index
    try:
        with open(asset_index_path, "r") as f:
            asset_manifest = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"❌ Error al leer el asset index: {e}")
        sys.exit(1)

    objects = asset_manifest.get("objects", {})

    for asset_name, asset_info in objects.items():
        hash_value = asset_info["hash"]
        subdir = hash_value[:2]
        asset_url = f"https://resources.download.minecraft.net/{subdir}/{hash_value}"
        asset_path = ASSETS_DIR / "objects" / subdir / hash_value

        if not asset_path.exists():
            download_file(asset_url, asset_path)

    print("✅ Todo descargado correctamente.")

    # Preguntar si lanzar el juego
    if prompt_yes_no("¿Quieres lanzar el juego ahora?"):
        java_path = "java"  # O la ruta completa a Java si prefieres
        username = input("Introduce tu nombre de usuario: ") or "Player"
        asset_index_id = manifest.get("assetIndex", {}).get("id", "1.21.5")

        # Generar UUID y token ficticio
        player_uuid = str(uuid.uuid4())
        access_token = str(uuid.uuid4())

        # Construir classpath
        classpath = f"{CLIENT_JAR}:{':'.join(str(path) for path in LIBRARIES_DIR.rglob('*.jar'))}"

        # Detectar sistema operativo y añadir el parámetro necesario
        args = [java_path]

        # Agregar '-XstartOnFirstThread' solo si es macOS
        if os_name == "darwin":
            args.append("-XstartOnFirstThread")

        # Agregar los parámetros de Java
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
                str(BASE_DIR),
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

        print("🛠️ Lanzando el juego...")
        try:
            subprocess.run(args)
        except FileNotFoundError:
            print("❌ Error: Java no está instalado o no está en PATH.")


if __name__ == "__main__":
    main()
