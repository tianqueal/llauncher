import concurrent.futures
import json
import threading
import time
import zipfile
import shutil  # Para obtener el ancho de la terminal

import requests

from src.config.constants import (
    ASSETS_DIR,
    BASE_DIR,
    GAME_DIR,
    CLIENT_JAR,
    LIBRARIES_DIR,
    MANIFEST_DIR,
    MANIFEST_JSON,
    MANIFEST_URL,
    NATIVES_DIR,
    OS_NAME,
)
from src.config.settings import get_setting
from src.utils.logging import log

# Variables globales para descargas
download_complete = False
download_in_progress = False
progress_thread = None
should_exit = False
download_counter = 0
download_lock = threading.Lock()
total_downloads = 0
current_file = ""  # Archivo actualmente en descarga
current_file_lock = threading.Lock()  # Lock para actualizar el archivo actual


def download_file(url, dest):
    """Descargar un archivo desde una URL"""
    try:
        # Actualizar el archivo actual que se está descargando
        global current_file
        with current_file_lock:
            current_file = dest.name

        response = requests.get(url, stream=True)
        response.raise_for_status()

        # Obtener el tamaño total si está disponible
        total_size = int(response.headers.get("content-length", 0))

        # Asegurar que el directorio padre existe
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Descargar el archivo
        downloaded = 0
        with open(dest, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

        # Actualizar contador global de descargas
        global download_counter
        with download_lock:
            download_counter += 1
            current = download_counter

        log(
            f"Descargado {dest.name} [{current}/{total_downloads if total_downloads > 0 else '?'}]"
        )
        return True
    except requests.RequestException as e:
        log(f"Error al descargar {url}: {e}", error=True)
        return False


def extract_natives(jar_path):
    """Extrae el contenido de un JAR de natives"""
    try:
        with zipfile.ZipFile(jar_path, "r") as jar:
            for file in jar.namelist():
                if file.startswith("META-INF/"):
                    continue
                jar.extract(file, NATIVES_DIR)
        log(f"Extraído {jar_path.name} en {NATIVES_DIR}")
        return True
    except zipfile.BadZipFile:
        log(f"Error: {jar_path} no es un archivo ZIP válido.", error=True)
        return False


def show_progress_animation():
    """Muestra una animación de progreso en la terminal con una barra visual"""
    animation = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"  # Spinner más estético
    idx = 0
    try:
        terminal_width = shutil.get_terminal_size().columns
    except:
        terminal_width = (
            80  # Valor por defecto si no podemos obtener el ancho de la terminal
        )

    while not should_exit:
        with download_lock:
            current = download_counter
            total = total_downloads

        with current_file_lock:
            file_name = current_file

        if total > 0:
            percent = min(int(current * 100 / total), 100)

            # Calcular cuánto espacio tenemos para la barra de progreso
            info_text = f" {percent}% [{current}/{total}] "
            spinner = animation[idx % len(animation)]
            file_text = f" {file_name}"

            # Espacio disponible para la barra después de mostrar toda la información
            available_width = max(
                10, terminal_width - len(info_text) - len(file_text) - 4
            )

            # Calcular la longitud de la barra de progreso
            bar_length = available_width
            filled_length = int(bar_length * percent // 100)

            # Crear la barra de progreso
            bar = "█" * filled_length + "░" * (bar_length - filled_length)

            # Limitar la longitud del nombre del archivo si es necesario
            max_file_length = terminal_width - len(info_text) - len(bar) - 5
            if len(file_name) > max_file_length:
                file_display = file_name[: max_file_length - 3] + "..."
            else:
                file_display = file_name

            # Mostrar la barra de progreso con toda la información
            print(f"\r{spinner} [{bar}]{info_text}| {file_display}", end="")
        else:
            # Si no conocemos el total, mostrar solo el spinner
            print(
                f"\r{animation[idx % len(animation)]} Descargando... {file_name}",
                end="",
            )

        idx += 1
        time.sleep(0.1)


def download_minecraft():
    """Descarga Minecraft y sus dependencias usando descargas paralelas"""
    global download_complete, download_in_progress, should_exit, progress_thread
    global download_counter, total_downloads

    if download_in_progress:
        log("Descarga ya en progreso, espere...", error=True)
        return

    download_in_progress = True
    download_counter = 0
    total_downloads = 0

    # Iniciar animación de progreso
    progress_thread = threading.Thread(target=show_progress_animation)
    progress_thread.daemon = True
    progress_thread.start()

    try:
        log("Iniciando descarga y preparación de Minecraft (con descargas paralelas)")

        # Obtener el número máximo de workers desde la configuración
        max_workers = get_setting("max_workers", 10)
        log(f"Usando {max_workers} workers para descargas paralelas")

        # Crear carpetas
        BASE_DIR.mkdir(exist_ok=True)
        GAME_DIR.mkdir(parents=True, exist_ok=True)
        MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
        LIBRARIES_DIR.mkdir(parents=True, exist_ok=True)
        NATIVES_DIR.mkdir(parents=True, exist_ok=True)
        ASSETS_DIR.mkdir(parents=True, exist_ok=True)

        # Descargar manifest si no existe
        if not MANIFEST_JSON.exists():
            log(f"Descargando el archivo manifest desde {MANIFEST_URL}...")
            if not download_file(MANIFEST_URL, MANIFEST_JSON):
                should_exit = True
                log("Error al descargar el manifest", error=True)
                return
        else:
            log(f"Manifest ya existe, omitiendo descarga.")

        # Leer manifest
        try:
            with open(MANIFEST_JSON, "r") as f:
                manifest = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            should_exit = True
            log(f"Error al leer el manifest: {e}", error=True)
            return

        # Descargar client.jar
        client_url = manifest["downloads"]["client"]["url"]
        log("Descargando client.jar...")
        if not download_file(client_url, CLIENT_JAR):
            should_exit = True
            log("Error al descargar client.jar", error=True)
            return

        # Preparar descargas de librerías y natives
        download_tasks = []

        log(f"Sistema operativo detectado: {OS_NAME}")

        # Recopilar las librerías a descargar
        libraries = manifest.get("libraries", [])
        for lib in libraries:
            downloads = lib.get("downloads", {})

            # Librería normal
            if "artifact" in downloads:
                artifact = downloads["artifact"]
                url = artifact["url"]
                path = LIBRARIES_DIR / artifact["path"]
                if not path.exists():
                    download_tasks.append((url, path))

            # Librería native (si aplica)
            classifiers = downloads.get("classifiers", {})
            native_key = None
            if OS_NAME == "windows":
                native_key = "natives-windows"
            elif OS_NAME == "linux":
                native_key = "natives-linux"
            elif OS_NAME == "darwin":
                native_key = "natives-osx"

            if native_key and native_key in classifiers:
                native = classifiers[native_key]
                url = native["url"]
                path = LIBRARIES_DIR / native["path"]
                if not path.exists():
                    download_tasks.append((url, path))

        # Preparar la descarga de assets
        log("Preparando descarga de assets...")
        asset_index = manifest["assetIndex"]
        asset_index_url = asset_index["url"]
        asset_index_id = asset_index["id"]
        asset_index_path = ASSETS_DIR / "indexes" / f"{asset_index_id}.json"

        # Descargar el índice de assets primero (no en paralelo)
        if not download_file(asset_index_url, asset_index_path):
            should_exit = True
            log("Error al descargar el índice de assets", error=True)
            return

        # Leer asset index
        try:
            with open(asset_index_path, "r") as f:
                asset_manifest = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            should_exit = True
            log(f"Error al leer el asset index: {e}", error=True)
            return

        # Recopilar assets a descargar
        objects = asset_manifest.get("objects", {})
        for asset_name, asset_info in objects.items():
            hash_value = asset_info["hash"]
            subdir = hash_value[:2]
            asset_url = (
                f"https://resources.download.minecraft.net/{subdir}/{hash_value}"
            )
            asset_path = ASSETS_DIR / "objects" / subdir / hash_value

            if not asset_path.exists():
                download_tasks.append((asset_url, asset_path))

        # Actualizar contador total de descargas
        total_downloads = len(download_tasks)
        log(f"Se van a descargar {total_downloads} archivos en paralelo")

        # Ejecutar descargas en paralelo
        if download_tasks:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=max_workers
            ) as executor:
                # Crear un diccionario para almacenar los futures y sus paths correspondientes
                future_to_path = {
                    executor.submit(download_file, url, path): path
                    for url, path in download_tasks
                }

                # Procesar los resultados a medida que se completan
                for future in concurrent.futures.as_completed(future_to_path):
                    path = future_to_path[future]
                    try:
                        success = future.result()

                        # Si es un archivo nativo, extraerlo
                        if (
                            success
                            and str(path).endswith(".jar")
                            and "-natives-" in str(path)
                        ):
                            extract_natives(path)
                    except Exception as e:
                        log(f"Error al procesar {path}: {e}", error=True)

        # Verificar si todas las descargas se completaron
        if download_counter >= total_downloads:
            log(
                f"Todas las descargas completadas: {download_counter}/{total_downloads}"
            )
            download_complete = True
        else:
            log(
                f"No se completaron todas las descargas: {download_counter}/{total_downloads}",
                error=True,
            )

    except Exception as e:
        log(f"Error durante la descarga: {e}", error=True)
    finally:
        download_in_progress = False
        should_exit = True
        if progress_thread and progress_thread.is_alive():
            progress_thread.join(0.5)  # Esperar a que termine la animación

        try:
            # Obtener el ancho de la terminal para limpiar toda la línea
            terminal_width = shutil.get_terminal_size().columns
            print("\r" + " " * terminal_width + "\r", end="")
        except:
            # Si no podemos obtener el ancho, usar un valor grande
            print("\r" + " " * 100 + "\r", end="")

        if download_complete:
            print("\n✅ ¡Descarga completada exitosamente! 🎮")
            print(f"   Se descargaron {download_counter} archivos.")
        else:
            print("\n❌ La descarga no se completó correctamente.")
            print(
                f"   Solo se descargaron {download_counter} de {total_downloads} archivos."
            )
            print("   Revisa el log para más detalles.")

    return download_complete


def is_download_complete():
    """Retorna si la descarga está completa"""
    return download_complete


def set_download_complete(value):
    """Establece el estado de la descarga"""
    global download_complete
    download_complete = value
