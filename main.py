import json
import os
import platform
import requests
import subprocess
import sys
import uuid
import zipfile
import threading
import time
import concurrent.futures
from pathlib import Path
from datetime import datetime

# Configuraciones iniciales
MANIFEST_FILE = "1.21.5.json"
MANIFEST_URL = "https://piston-meta.mojang.com/v1/packages/a0645da8cf4e89da6baaab8e08b7ca64b7f4b0cf/1.21.5.json"
BASE_DIR = Path("minecraft_1.21.5")
LIBRARIES_DIR = BASE_DIR / "libraries"
ASSETS_DIR = BASE_DIR / "assets"
NATIVES_DIR = BASE_DIR / "natives"
CLIENT_JAR = BASE_DIR / "client.jar"

# Variables globales
download_complete = False
download_in_progress = False
progress_thread = None
should_exit = False

# Configuración de descargas paralelas
MAX_WORKERS = 10  # Número máximo de descargas simultáneas
download_counter = 0
download_lock = threading.Lock()
total_downloads = 0

# Crear directorio y archivo de registro
LOGS_DIR = Path("minecraft_logs")
LOGS_DIR.mkdir(exist_ok=True)
log_filename = (
    LOGS_DIR / f'minecraft_downloader_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
)
log_file = open(log_filename, "w")
log_lock = threading.Lock()  # Para evitar conflictos al escribir en el log


def log(message, error=False):
    """Registra un mensaje en el archivo de registro y lo imprime en la consola"""
    with log_lock:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"{timestamp} - {'ERROR' if error else 'INFO'} - {message}"
        log_file.write(log_message + "\n")
        log_file.flush()

        # Si es un error, imprimir en stderr
        if error:
            print(f"\033[91m{message}\033[0m", file=sys.stderr)
        else:
            print(message)


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
    """Muestra una animación de progreso en la terminal"""
    animation = "|/-\\"
    idx = 0
    while not should_exit:
        with download_lock:
            current = download_counter
            total = total_downloads

        if total > 0:
            percent = min(int(current * 100 / total), 100)
            print(
                f"\rDescargando... {percent}% [{current}/{total}] {animation[idx % len(animation)]}",
                end="",
            )
        else:
            print(f"\rDescargando... {animation[idx % len(animation)]}", end="")

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

        # Crear carpetas
        BASE_DIR.mkdir(exist_ok=True)
        LIBRARIES_DIR.mkdir(parents=True, exist_ok=True)
        NATIVES_DIR.mkdir(parents=True, exist_ok=True)
        ASSETS_DIR.mkdir(parents=True, exist_ok=True)

        # Descargar manifest si no existe
        if not Path(MANIFEST_FILE).exists():
            log(f"Descargando el archivo manifest desde {MANIFEST_URL}...")
            if not download_file(MANIFEST_URL, Path(MANIFEST_FILE)):
                should_exit = True
                log("Error al descargar el manifest", error=True)
                return
        else:
            log(f"Manifest {MANIFEST_FILE} ya existe, omitiendo descarga.")

        # Leer manifest
        try:
            with open(MANIFEST_FILE, "r") as f:
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

        os_name = platform.system().lower()  # windows, linux, darwin
        log(f"Sistema operativo detectado: {os_name}")

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
                max_workers=MAX_WORKERS
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

        print("\r" + " " * 70 + "\r", end="")  # Limpiar la línea de animación

        if download_complete:
            print("\n¡Descarga completada exitosamente! 🎮")
        else:
            print(
                "\nLa descarga no se completó correctamente. Revisa el log para más detalles."
            )


def launch_minecraft(username):
    """Lanza Minecraft con el usuario especificado"""
    if not download_complete:
        log("Primero debes descargar Minecraft.", error=True)
        return False

    # Leer manifest para obtener asset_index_id
    try:
        with open(MANIFEST_FILE, "r") as f:
            manifest = json.load(f)
            asset_index_id = manifest.get("assetIndex", {}).get("id", "1.21.5")
    except Exception as e:
        log(f"Error al leer el manifest: {e}", error=True)
        return False

    # Generar UUID y token ficticio
    player_uuid = str(uuid.uuid4())
    access_token = str(uuid.uuid4())

    java_path = "java"  # O la ruta completa a Java si prefieres

    # Construir classpath
    classpath_separator = ";" if platform.system().lower() == "windows" else ":"

    # Recopilar todas las bibliotecas
    library_paths = list(LIBRARIES_DIR.rglob("*.jar"))
    classpath = f"{CLIENT_JAR}{classpath_separator}{classpath_separator.join([str(path) for path in library_paths])}"

    # Detectar sistema operativo
    os_name = platform.system().lower()

    # Construir argumentos
    args = [java_path]

    # Agregar '-XstartOnFirstThread' solo si es macOS
    if os_name == "darwin":
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


def show_menu():
    """Muestra el menú principal"""
    global download_complete

    while True:
        print("\n" + "=" * 60)
        print("📥 LLauncher (versión 1.21.5) 📥".center(60))
        print("=" * 60)
        print("\nOpciones:")
        print("1. Descargar Minecraft 1.21.5")
        print("2. Iniciar Minecraft")
        print("3. Eliminar archivos de instalación")
        print("4. Ver registro")
        print("5. Configuración")
        print("6. Salir")

        if download_complete:
            print("\n✅ Minecraft está descargado y listo para jugar!")

        try:
            option = input("\nElige una opción (1-6): ")

            if option == "1":
                if not download_in_progress and not download_complete:
                    download_thread = threading.Thread(target=download_minecraft)
                    download_thread.daemon = True
                    download_thread.start()
                    # Esperar a que termine
                    while download_thread.is_alive():
                        time.sleep(0.1)
                elif download_in_progress:
                    print("\n⏳ Descarga en progreso, por favor espera...")
                else:
                    if prompt_yes_no(
                        "\nMinecraft ya está descargado. ¿Descargar de nuevo?"
                    ):
                        download_complete = False
                        download_thread = threading.Thread(target=download_minecraft)
                        download_thread.daemon = True
                        download_thread.start()
                        # Esperar a que termine
                        while download_thread.is_alive():
                            time.sleep(0.1)

            elif option == "2":
                if CLIENT_JAR.exists():
                    username = input(
                        "\nIngresa tu nombre de usuario (o presiona Enter para usar 'Player'): "
                    ).strip()
                    if not username:
                        username = "Player"

                    if not download_complete:
                        # Si parece que ya hay archivos pero no completamos la descarga en esta sesión
                        print(
                            "\nParece que Minecraft ya está descargado de una sesión anterior."
                        )
                        download_complete = True

                    launch_minecraft(username)
                else:
                    print("\n❌ Primero debes descargar Minecraft (opción 1).")

            elif option == "3":
                if CLIENT_JAR.exists() or BASE_DIR.exists():
                    if prompt_yes_no("\n¿Eliminar archivos de instalación?"):
                        try:
                            log("Iniciando limpieza de archivos de instalación")
                            remove_directory_recursively(BASE_DIR)
                            print("\n✅ Archivos de instalación eliminados.")
                            download_complete = False
                            if Path(MANIFEST_FILE).exists():
                                Path(MANIFEST_FILE).unlink()
                                log(f"Archivo manifest {MANIFEST_FILE} eliminado")
                        except Exception as e:
                            log(f"Error al eliminar archivos: {e}", error=True)
                            print(f"\n❌ Error al eliminar archivos: {e}")
                else:
                    print("\n❌ No hay archivos de instalación para eliminar.")

            elif option == "4":
                print("\n" + "=" * 60)
                print("REGISTRO DE ACTIVIDAD".center(60))
                print("=" * 60)
                print(f"Archivo de registro: {log_filename}")

                try:
                    with open(log_filename, "r") as f:
                        log_content = f.readlines()
                        last_entries = (
                            log_content[-20:] if len(log_content) > 20 else log_content
                        )
                        print("\n".join(last_entries))
                except Exception as e:
                    print(f"\n❌ Error al leer el archivo de registro: {e}")

                print("\nPresiona Enter para continuar...")
                input()

            elif option == "5":
                global MAX_WORKERS
                print("\n" + "=" * 60)
                print("CONFIGURACIÓN".center(60))
                print("=" * 60)
                print(f"\nNúmero actual de descargas paralelas: {MAX_WORKERS}")

                try:
                    new_workers = int(
                        input("Ingrese el nuevo número de descargas paralelas (3-20): ")
                    )
                    if 3 <= new_workers <= 20:
                        MAX_WORKERS = new_workers
                        print(
                            f"\n✅ Número de descargas paralelas actualizado a: {MAX_WORKERS}"
                        )
                    else:
                        print("\n❌ El valor debe estar entre 3 y 20.")
                except ValueError:
                    print("\n❌ Por favor ingrese un número válido.")

            elif option == "6":
                print("\n¡Gracias por usar LLauncher! 👋")
                break

            else:
                print("\n❌ Opción no válida. Por favor, elige una opción del 1 al 6.")

        except KeyboardInterrupt:
            print("\n\n¡Proceso interrumpido! Saliendo...")
            break
        except Exception as e:
            print(f"\n❌ Error inesperado: {e}")


def main():
    """Función principal"""
    try:
        # Mostrar información del sistema
        log(f"Sistema: {platform.system()} {platform.release()}")
        log(f"Python: {sys.version}")
        log(f"Directorio actual: {os.getcwd()}")

        # Verificar descarga existente
        global download_complete
        if CLIENT_JAR.exists() and LIBRARIES_DIR.exists() and ASSETS_DIR.exists():
            log("Instalación existente de Minecraft detectada")
            download_complete = True

        # Mostrar menú
        show_menu()

    except Exception as e:
        log(f"Error crítico: {e}", error=True)
    finally:
        log("Aplicación finalizada")
        log_file.close()


def remove_directory_recursively(path):
    """Elimina un directorio y todo su contenido de forma recursiva"""
    path = Path(path)  # Asegurarse de que es un objeto Path

    if path.is_file() or path.is_symlink():
        path.unlink()
    elif path.is_dir():
        for child in path.iterdir():
            remove_directory_recursively(child)
        path.rmdir()


if __name__ == "__main__":
    main()
