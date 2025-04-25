import concurrent.futures
import json
import threading
import time
import zipfile
import shutil
import hashlib  # Para verificación de integridad
import platform

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
current_file = ""
current_file_lock = threading.Lock()

# Añadir un nuevo lock para proteger la extracción de natives
extract_lock = threading.Lock()


def download_file(url, dest, expected_hash=None):
    """Descargar un archivo desde una URL con verificación de integridad opcional"""
    # Declarar todas las variables globales al inicio de la función
    global current_file
    global download_counter

    try:
        # Actualizar el archivo actual que se está descargando
        with current_file_lock:
            current_file = dest.name

        # Si el archivo ya existe y tiene el hash esperado, omitir descarga
        if expected_hash and dest.exists():
            if verify_file_hash(dest, expected_hash):
                # Solo registrar en el archivo de log, no en la consola
                log(
                    f"Omitiendo descarga de {dest.name} (ya existe y es válido)",
                    console_output=False,
                )

                # Actualizar contador global de descargas
                with download_lock:
                    download_counter += 1
                    current = download_counter

                return True

        # Realizar la descarga
        response = requests.get(url, stream=True)
        response.raise_for_status()

        # Obtener el tamaño total si está disponible
        total_size = int(response.headers.get("content-length", 0))

        # Asegurar que el directorio padre existe
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Descargar el archivo
        downloaded = 0
        sha1_hash = hashlib.sha1()

        with open(dest, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    if expected_hash:
                        sha1_hash.update(chunk)
                    downloaded += len(chunk)

        # Verificar hash si se especificó
        if expected_hash and expected_hash != sha1_hash.hexdigest():
            log(
                f"Error de verificación para {dest.name} (hash no coincide)", error=True
            )
            return False

        # Actualizar contador global de descargas
        with download_lock:
            download_counter += 1
            current = download_counter

        # Solo registrar en el archivo de log, no en la consola
        log(
            f"Descargado {dest.name} [{current}/{total_downloads if total_downloads > 0 else '?'}]",
            console_output=False,
        )
        return True
    except requests.RequestException as e:
        log(f"Error al descargar {url}: {e}", error=True)
        return False


def verify_file_hash(file_path, expected_hash):
    """Verifica el hash SHA1 de un archivo"""
    try:
        sha1_hash = hashlib.sha1()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                sha1_hash.update(chunk)

        return sha1_hash.hexdigest() == expected_hash
    except Exception as e:
        log(f"Error al verificar hash de {file_path}: {e}", error=True)
        return False


def extract_natives(jar_path):
    """Extrae el contenido de un JAR de natives"""
    # Usar lock para evitar extracciones concurrentes que podrían interferir entre sí
    with extract_lock:
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
        except PermissionError:
            log(f"Error de permisos al extraer {jar_path}", error=True)
            return False
        except Exception as e:
            log(
                f"Error inesperado al extraer {jar_path}: {e.__class__.__name__}: {e}",
                error=True,
            )
            return False


def show_progress_animation():
    """Muestra una animación de progreso en la terminal con una barra visual mejorada"""
    animation = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"  # Spinner más estético
    idx = 0
    last_percent = -1
    last_file_displayed = ""
    update_counter = 0

    try:
        terminal_width = shutil.get_terminal_size().columns
    except:
        terminal_width = 80  # Valor por defecto

    # Mostrar cabecera inicial
    print("\n📥 Progreso de descarga:")

    while not should_exit:
        with download_lock:
            current = download_counter
            total = total_downloads

        with current_file_lock:
            file_name = current_file

        if total > 0:
            percent = min(int(current * 100 / total), 100)

            # Evitar actualizaciones excesivas de la consola
            # Solo actualizar si:
            # 1. El porcentaje ha cambiado
            # 2. El archivo ha cambiado
            # 3. Han pasado 10 ciclos (para mantener el spinner animado)
            if (
                percent != last_percent
                or file_name != last_file_displayed
                or update_counter >= 10
            ):
                update_counter = 0
                last_percent = percent
                last_file_displayed = file_name

                # Calcular espacio para la barra de progreso
                spinner = animation[idx % len(animation)]
                info_text = f" {percent}% [{current}/{total}] "

                # Espacio disponible para la barra después de mostrar la información
                available_width = max(20, terminal_width - len(info_text) - 6)

                # Calcular la longitud de la barra de progreso (75% del espacio disponible)
                bar_length = int(available_width * 0.75)
                filled_length = int(bar_length * percent // 100)

                # Crear la barra de progreso con colores
                bar = "█" * filled_length + "░" * (bar_length - filled_length)

                # Mostrar información del archivo actual en una segunda línea
                # pero solo mostrar el nombre del archivo (sin la ruta)
                file_display = (
                    file_name.split("/")[-1] if "/" in file_name else file_name
                )

                # Limitar longitud del nombre del archivo
                max_file_length = terminal_width - 20
                if len(file_display) > max_file_length:
                    file_display = file_display[: max_file_length - 3] + "..."

                # Limpiar líneas anteriores y mostrar la barra de progreso
                print(f"\r{spinner} [{bar}]{info_text}", end="")
                print(f"\n📄 Archivo actual: {file_display}", end="\r\033[A")
            else:
                update_counter += 1
        else:
            # Si no conocemos el total, mostrar solo el spinner
            spinner = animation[idx % len(animation)]
            print(f"\r{spinner} Preparando descarga...", end="")

            # Mostrar el archivo actual si hay uno
            if file_name:
                file_display = (
                    file_name.split("/")[-1] if "/" in file_name else file_name
                )
                print(f"\n📄 {file_display}", end="\r\033[A")

        idx += 1
        time.sleep(0.1)


def download_minecraft():
    """Descarga Minecraft y sus dependencias usando descargas paralelas con verificación de integridad"""
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
        # Obtener el nivel de calidad gráfica (afecta a qué assets se descargan)
        graphics_quality = get_setting(
            "graphics_quality", "high"
        )  # valores: low, medium, high
        log(f"Usando {max_workers} workers y calidad gráfica: {graphics_quality}")

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

        # Descargar client.jar con verificación de hash
        client_info = manifest["downloads"]["client"]
        client_url = client_info["url"]
        client_sha1 = client_info["sha1"]

        log("Descargando client.jar...")
        if not download_file(client_url, CLIENT_JAR, client_sha1):
            should_exit = True
            log("Error al descargar client.jar", error=True)
            return

        # Preparar descargas de librerías y natives
        download_tasks = []

        log(f"Sistema operativo detectado: {OS_NAME}")

        # Recopilar las librerías a descargar
        libraries = manifest.get("libraries", [])

        # Definir mapeo de sistemas operativos para filtrado
        os_mapping = {
            "windows": ["windows", "win"],
            "linux": ["linux", "unix"],
            "darwin": ["osx", "mac", "macos", "darwin"],
        }

        current_os_aliases = os_mapping.get(OS_NAME, [OS_NAME])
        log(f"Filtrando bibliotecas para: {current_os_aliases}")

        for lib in libraries:
            # Verificar reglas de inclusión/exclusión
            should_include = True
            if "rules" in lib:
                should_include = False  # Default para bibliotecas con reglas
                for rule in lib.get("rules", []):
                    action = rule.get("action", "allow") == "allow"

                    # Verificar regla específica de SO
                    if "os" in rule:
                        os_rule = rule["os"]
                        os_name = os_rule.get("name", "").lower()

                        # Comprobar si la regla aplica al SO actual
                        if any(alias == os_name for alias in current_os_aliases):
                            should_include = action
                            break
                    else:
                        # Regla general
                        should_include = action

            # Si la biblioteca debe excluirse, saltarla
            if not should_include:
                lib_name = lib.get("name", "Desconocida")
                log(f"Omitiendo biblioteca no requerida: {lib_name}")
                continue

            downloads = lib.get("downloads", {})

            # Librería normal
            if "artifact" in downloads:
                artifact = downloads["artifact"]
                url = artifact["url"]
                path = LIBRARIES_DIR / artifact["path"]
                # Incluir el SHA1 para verificación
                sha1 = artifact.get("sha1")
                if not path.exists() or (sha1 and not verify_file_hash(path, sha1)):
                    download_tasks.append((url, path, sha1))

            # Librería native (si aplica)
            classifiers = downloads.get("classifiers", {})
            native_key = None
            if OS_NAME == "windows":
                native_key = "natives-windows"
            elif OS_NAME == "linux":
                native_key = "natives-linux"
            elif OS_NAME == "darwin":
                native_key = "natives-osx"

            # Solo descargar natives para el SO actual
            if native_key and native_key in classifiers:
                native = classifiers[native_key]
                url = native["url"]
                path = LIBRARIES_DIR / native["path"]
                sha1 = native.get("sha1")
                if not path.exists() or (sha1 and not verify_file_hash(path, sha1)):
                    download_tasks.append((url, path, sha1))
                    # Marcar esta biblioteca para extracción posterior
                    log(f"Marcada para extracción: {path.name}")
            # IMPORTANTE: No descargar ni siquiera las natives para otros sistemas

        # Preparar la descarga de assets
        log("Preparando descarga de assets...")
        asset_index = manifest["assetIndex"]
        asset_index_url = asset_index["url"]
        asset_index_id = asset_index["id"]
        asset_index_path = ASSETS_DIR / "indexes" / f"{asset_index_id}.json"

        # Descargar el índice de assets primero (no en paralelo)
        asset_index_sha1 = asset_index.get("sha1")
        if not download_file(asset_index_url, asset_index_path, asset_index_sha1):
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

        # Recopilar assets a descargar (filtrados por calidad gráfica)
        objects = asset_manifest.get("objects", {})

        # Definir categorías de assets y filtros según calidad gráfica
        asset_categories = {
            "textures": ["textures/", ".png", ".jpg", ".jpeg", ".tga"],
            "sounds": ["sounds/", ".ogg", ".mp3", ".wav"],
            "music": ["music/", "records/", "sounds/music/", "sounds/records/"],
            "languages": ["lang/", "texts/", "realms/lang/"],
            "fonts": ["font/", "fonts/", "unicode/"],
            "models": ["models/", ".json"],
        }

        # Configuración de filtrado según calidad
        quality_filters = {
            "low": {
                "textures": lambda name: not any(
                    x in name.lower()
                    for x in ["hd", "4k", "high", "normal", "rain", "detailed"]
                ),
                "sounds": lambda name: not any(
                    x in name.lower()
                    for x in ["ambience", "ambient", "environment", "weather"]
                ),
                "music": lambda _: False,  # Sin música en calidad baja
                "languages": lambda name: "en_us" in name.lower()
                or "es_" in name.lower(),  # Solo inglés y español
                "fonts": lambda _: True,  # Siempre descargar fuentes
                "models": lambda name: "item" in name.lower()
                or "block" in name.lower(),  # Solo modelos esenciales
                "misc": lambda _: True,  # Otros assets esenciales
            },
            "medium": {
                "textures": lambda name: not any(
                    x in name.lower() for x in ["4k", "ultra", "parallax"]
                ),
                "sounds": lambda name: not "ambient/"
                in name.lower(),  # Algunos sonidos ambientales
                "music": lambda name: "menu" in name.lower()
                or "game" in name.lower(),  # Música básica
                "languages": lambda _: True,  # Todos los idiomas
                "fonts": lambda _: True,
                "models": lambda _: True,
                "misc": lambda _: True,
            },
            "high": {
                "textures": lambda _: True,
                "sounds": lambda _: True,
                "music": lambda _: True,
                "languages": lambda _: True,
                "fonts": lambda _: True,
                "models": lambda _: True,
                "misc": lambda _: True,
            },
        }

        # Función para determinar la categoría de un asset
        def get_asset_category(asset_name):
            for category, markers in asset_categories.items():
                if any(marker in asset_name.lower() for marker in markers):
                    return category
            return "misc"

        # Contadores para estadísticas
        skipped_assets = 0
        downloaded_assets = 0
        categories_stats = {
            category: {"total": 0, "skipped": 0} for category in asset_categories.keys()
        }
        categories_stats["misc"] = {"total": 0, "skipped": 0}

        # Procesar cada asset
        for asset_name, asset_info in objects.items():
            # Categorizar el asset
            category = get_asset_category(asset_name)
            categories_stats[category]["total"] += 1

            # Determinar si debe descargarse según la configuración de calidad
            filter_func = quality_filters[graphics_quality][category]
            should_download = filter_func(asset_name)

            if should_download:
                hash_value = asset_info["hash"]
                subdir = hash_value[:2]
                asset_url = (
                    f"https://resources.download.minecraft.net/{subdir}/{hash_value}"
                )
                asset_path = ASSETS_DIR / "objects" / subdir / hash_value

                if not asset_path.exists() or not verify_file_hash(
                    asset_path, hash_value
                ):
                    download_tasks.append((asset_url, asset_path, hash_value))
                    downloaded_assets += 1
            else:
                skipped_assets += 1
                categories_stats[category]["skipped"] += 1
                log(f"Omitiendo asset [{category}]: {asset_name}")

        # Mostrar estadísticas de filtrado
        log(f"Assets para descargar: {downloaded_assets}, Omitidos: {skipped_assets}")
        for category, stats in categories_stats.items():
            if stats["total"] > 0:
                percentage = (stats["skipped"] / stats["total"]) * 100
                log(
                    f"  {category}: {stats['skipped']}/{stats['total']} omitidos ({percentage:.1f}%)"
                )

        log(f"Estimación de ahorro de espacio: ~{skipped_assets * 15 / 1024:.1f} MB")

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
                    executor.submit(download_file, url, path, sha1): path
                    for url, path, sha1 in download_tasks
                }

                # Procesar los resultados a medida que se completan
                for future in concurrent.futures.as_completed(future_to_path):
                    path = future_to_path[future]
                    try:
                        success = future.result()

                        # Si es un archivo nativo, verificar que corresponda al SO actual antes de extraerlo
                        if success and str(path).endswith(".jar"):
                            # Determinar a qué SO corresponde esta native
                            native_so_markers = {
                                "windows": [
                                    "natives-windows",
                                    "natives-windows-x86",
                                    "natives-windows-arm64",
                                ],
                                "linux": ["natives-linux"],
                                "darwin": [
                                    "natives-osx",
                                    "natives-macos",
                                    "natives-macos-arm64",
                                    "natives-macos-patch",
                                ],
                                "macos": [
                                    "natives-osx",
                                    "natives-macos",
                                    "natives-macos-arm64",
                                    "natives-macos-patch",
                                ],
                                "macosx": [
                                    "natives-osx",
                                    "natives-macos",
                                    "natives-macos-arm64",
                                    "natives-macos-patch",
                                ],
                            }

                            # Extracción selectiva de natives según el SO
                            path_str = str(path).lower()
                            current_os_markers = native_so_markers.get(OS_NAME, [])

                            # Verificar si alguno de los marcadores del SO actual está en la ruta
                            is_compatible = any(
                                marker in path_str for marker in current_os_markers
                            )

                            # En macOS ARM, priorizar natives-macos-arm64 sobre natives-macos
                            if (
                                OS_NAME in ["darwin", "macos", "macosx"]
                                and platform.machine() == "arm64"
                            ):
                                if "natives-macos-arm64" in path_str:
                                    is_compatible = True
                                    log(
                                        f"Extrayendo native ARM64 para {OS_NAME}: {path.name}"
                                    )
                                    extract_natives(path)
                                elif any(
                                    marker in path_str
                                    for marker in [
                                        "natives-macos",
                                        "natives-osx",
                                        "natives-macos-patch",
                                    ]
                                ):
                                    # En ARM64, también extraemos versiones normales de macOS para compatibilidad
                                    is_compatible = True
                                    log(
                                        f"Extrayendo native compatible para {OS_NAME} ARM64: {path.name}"
                                    )
                                    extract_natives(path)
                            # Para el resto de configuraciones, usar el marcador estándar
                            elif is_compatible:
                                log(f"Extrayendo native para {OS_NAME}: {path.name}")
                                extract_natives(path)
                            elif "-natives-" in path_str:
                                # Es una native pero de otro SO, no la extraemos
                                log(
                                    f"Omitiendo extracción de native no compatible: {path.name}"
                                )

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
