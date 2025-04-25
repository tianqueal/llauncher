import json
import os
import subprocess
import uuid
from pathlib import Path
import stat

from src.config.constants import (
    ASSETS_DIR,
    GAME_DIR,
    CLIENT_JAR,
    LIBRARIES_DIR,
    MANIFEST_JSON,
    NATIVES_DIR,
    OS_NAME,
)
from src.config.settings import get_setting
from src.utils.logging import log
from src.downloader.downloader import is_download_complete


def find_java_path():
    """Encuentra la ruta a la instalación de Java"""
    # 1. Primero usar la ruta configurada por el usuario si existe
    user_java_path = get_setting("java_path")
    if user_java_path and user_java_path != "java":
        # Verificar si la ruta existe y es ejecutable
        java_path = Path(user_java_path)
        if java_path.exists():
            log(f"Usando ruta de Java configurada por el usuario: {user_java_path}")
            return str(java_path)
        else:
            log(
                f"La ruta de Java configurada ({user_java_path}) no existe. Buscando alternativas.",
                error=True,
            )

    # 2. Intentar con la variable de entorno JAVA_HOME
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        java_bin = "java.exe" if OS_NAME == "windows" else "java"
        java_path = Path(java_home) / "bin" / java_bin
        if java_path.exists():
            return str(java_path)

    # 3. Rutas comunes según el sistema operativo
    if OS_NAME == "windows":
        common_paths = [
            # Instalaciones estándar
            r"C:\Program Files\Java\jre*\bin\java.exe",
            r"C:\Program Files\Java\jdk*\bin\java.exe",
            r"C:\Program Files (x86)\Java\jre*\bin\java.exe",
            # Instalaciones con winget (OpenJDK)
            r"C:\Program Files\Eclipse Adoptium\jdk-*\bin\java.exe",
            r"C:\Program Files\Microsoft\jdk-*\bin\java.exe",
            r"C:\Program Files\Eclipse Foundation\jdk-*\bin\java.exe",
            r"C:\Program Files\BellSoft\LibericaJDK-*\bin\java.exe",
            r"C:\Program Files\Amazon Corretto\*\bin\java.exe",
            r"C:\Program Files\ojdkbuild\*\bin\java.exe",
            r"C:\Program Files\Zulu\*\bin\java.exe",
            # Ubicaciones de AppData (algunas instalaciones de winget las usan)
            r"C:\Users\*\AppData\Local\Programs\Eclipse Adoptium\jdk-*\bin\java.exe",
            r"C:\Users\*\AppData\Local\Programs\Microsoft\jdk-*\bin\java.exe",
        ]

        # Primero buscar en rutas sin comodines
        for pattern in common_paths:
            if "*" not in pattern:
                if Path(pattern).exists():
                    return pattern

        # Luego buscar con comodines
        for pattern in common_paths:
            if "*" in pattern:
                try:
                    # Determinar la unidad y la ruta base para glob
                    if pattern.startswith("C:"):
                        base_path = Path("C:/")
                        glob_pattern = pattern[3:]  # Quitar "C:\"
                    else:
                        base_path = Path("/")
                        glob_pattern = pattern

                    paths = list(base_path.glob(glob_pattern))
                    if paths:
                        # Ordenar por versión (asumiendo que la más reciente está al final)
                        paths.sort()
                        return str(paths[-1])  # Devolver la última versión encontrada
                except Exception as e:
                    log(
                        f"Error al buscar Java en {pattern}: {e}",
                        error=True,
                        console_output=False,
                    )

        # Buscar en el registro de Windows (puede contener rutas de instalaciones de winget)
        try:
            import winreg

            reg_paths = [
                r"SOFTWARE\JavaSoft\Java Runtime Environment",
                r"SOFTWARE\JavaSoft\Java Development Kit",
                r"SOFTWARE\Eclipse Adoptium",
                r"SOFTWARE\Microsoft\JDK",
            ]

            for reg_path in reg_paths:
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
                        current_version, _ = winreg.QueryValueEx(key, "CurrentVersion")
                        with winreg.OpenKey(
                            winreg.HKEY_LOCAL_MACHINE, f"{reg_path}\\{current_version}"
                        ) as subkey:
                            java_home, _ = winreg.QueryValueEx(subkey, "JavaHome")
                            java_path = Path(java_home) / "bin" / "java.exe"
                            if java_path.exists():
                                return str(java_path)
                except:
                    pass  # Ignorar errores de registro y continuar buscando
        except ImportError:
            log("Módulo winreg no disponible.", error=True, console_output=False)
        except Exception as e:
            log(
                f"Error al buscar Java en el registro de Windows: {e}",
                error=True,
                console_output=False,
            )

    elif OS_NAME == "darwin":
        common_paths = [
            # Homebrew paths (más comunes en macOS moderno)
            "/opt/homebrew/opt/openjdk/bin/java",
            "/usr/local/opt/openjdk/bin/java",
            "/opt/homebrew/Cellar/openjdk/*/bin/java",
            "/usr/local/Cellar/openjdk/*/bin/java",
            # Rutas de sistema
            "/Library/Java/JavaVirtualMachines/*/Contents/Home/bin/java",
            "/System/Library/Frameworks/JavaVM.framework/Versions/*/Commands/java",
            "/usr/bin/java",
        ]
        for pattern in common_paths:
            try:
                # Si la ruta no contiene comodines, verificarla directamente
                if "*" not in pattern:
                    if Path(pattern).exists():
                        return pattern
                else:
                    # Si tiene comodines, usar glob
                    paths = list(Path("/").glob(pattern[1:]))  # Quitar "/" del patrón
                    if paths:
                        return str(paths[0])
            except Exception as e:
                log(
                    f"Error al buscar Java en {pattern}: {e}",
                    error=True,
                    console_output=False,
                )
    elif OS_NAME == "linux":
        common_paths = [
            "/usr/bin/java",
            "/usr/lib/jvm/*/bin/java",
            "/opt/java/bin/java",
            # Instalaciones de snap
            "/snap/*/current/jre/bin/java",
        ]
        for pattern in common_paths:
            try:
                if "*" not in pattern:
                    if Path(pattern).exists():
                        return pattern
                else:
                    paths = list(Path("/").glob(pattern[1:]))  # Quitar "/" del patrón
                    if paths:
                        return str(paths[0])
            except:
                pass

    # 4. Verificar si 'java' está disponible en el PATH
    try:
        # Verificar si el comando java está disponible en el PATH
        if OS_NAME == "windows":
            result = subprocess.run(
                ["where", "java"], capture_output=True, text=True, check=False
            )
        else:
            result = subprocess.run(
                ["which", "java"], capture_output=True, text=True, check=False
            )

        if result.returncode == 0 and result.stdout.strip():
            java_in_path = result.stdout.strip().split("\n")[
                0
            ]  # Tomar la primera coincidencia
            log(f"Java encontrado en PATH: {java_in_path}")
            return java_in_path
    except:
        pass

    # 5. Si no encontramos nada, devolver "java" para usar el que esté en PATH (o fallar explícitamente)
    log(
        "No se encontró instalación de Java. Se intentará usar 'java' del PATH.",
        error=True,
    )
    return "java"


def verify_permissions(path):
    """Verifica y corrige los permisos de la carpeta natives"""
    try:
        path = Path(path)
        # Si el directorio no existe, crear con permisos correctos
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)

        # En Unix (Linux/macOS) establecer permisos seguros
        if OS_NAME != "windows":
            # 0o755 = rwxr-xr-x (propietario: lectura/escritura/ejecución, grupo/otros: lectura/ejecución)
            os.chmod(
                path,
                stat.S_IRWXU
                | stat.S_IRGRP
                | stat.S_IXGRP
                | stat.S_IROTH
                | stat.S_IXOTH,
            )

            # Verificar permisos de los archivos dentro del directorio
            for file_path in path.glob("*"):
                if file_path.is_file():
                    # 0o644 = rw-r--r-- para archivos
                    os.chmod(
                        file_path,
                        stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH,
                    )
                elif file_path.is_dir():
                    # Recursivamente verificar subdirectorios
                    verify_permissions(file_path)

        return True
    except Exception as e:
        log(f"Error al verificar/corregir permisos: {e}", error=True)
        return False


def get_required_libraries(manifest):
    """Filtra las bibliotecas necesarias para el SO actual"""
    required_libs = []

    # Si no hay manifest, usar una búsqueda de archivos
    if not manifest:
        return list(LIBRARIES_DIR.rglob("*.jar"))

    libraries = manifest.get("libraries", [])

    # Definir mapeo de sistemas operativos para filtrado
    os_mapping = {
        "windows": ["windows", "win"],
        "linux": ["linux", "unix"],
        "darwin": ["osx", "mac", "macos", "darwin"],
    }

    current_os_aliases = os_mapping.get(OS_NAME, [OS_NAME])

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
                else:
                    # Regla general
                    should_include = action

        # Si la biblioteca debe incluirse
        if should_include:
            downloads = lib.get("downloads", {})
            # Biblioteca normal
            if "artifact" in downloads:
                artifact = downloads["artifact"]
                path = LIBRARIES_DIR / artifact["path"]
                if path.exists():
                    # Resolver path para evitar problemas de path traversal
                    resolved_path = path.resolve()
                    # Verificar que el archivo está dentro del directorio de bibliotecas
                    if str(resolved_path).startswith(str(LIBRARIES_DIR.resolve())):
                        required_libs.append(resolved_path)

            # Biblioteca native para el SO actual
            native_key = None
            if OS_NAME == "windows":
                native_key = "natives-windows"
            elif OS_NAME == "linux":
                native_key = "natives-linux"
            elif OS_NAME == "darwin":
                native_key = "natives-osx"

            classifiers = downloads.get("classifiers", {})
            if native_key and native_key in classifiers:
                native_info = classifiers[native_key]
                path = LIBRARIES_DIR / native_info["path"]
                if path.exists():
                    # Resolver path para evitar problemas de path traversal
                    resolved_path = path.resolve()
                    # Verificar que el archivo está dentro del directorio de bibliotecas
                    if str(resolved_path).startswith(str(LIBRARIES_DIR.resolve())):
                        required_libs.append(resolved_path)

    # Si no encontramos nada (quizás por un error en las reglas),
    # incluir todas las bibliotecas descargadas
    if not required_libs:
        log(
            "No se encontraron bibliotecas específicas. Usando todas las disponibles.",
            error=True,
        )
        return list(LIBRARIES_DIR.rglob("*.jar"))

    return required_libs


def launch_minecraft(username):
    """Lanza Minecraft con el usuario especificado"""
    if not is_download_complete():
        log("Primero debes descargar Minecraft.", error=True)
        return False

    # Verificar y corregir permisos del directorio de natives
    verify_permissions(NATIVES_DIR)

    # Leer manifest para obtener asset_index_id y bibliotecas requeridas
    manifest = None
    try:
        with open(MANIFEST_JSON, "r") as f:
            manifest = json.load(f)
            asset_index_id = manifest.get("assetIndex", {}).get("id", "1.21.5")
    except Exception as e:
        log(f"Error al leer el manifest: {e}", error=True)
        asset_index_id = "1.21.5"  # Valor por defecto

    # Encontrar Java automáticamente
    java_path = find_java_path()
    log(f"Usando Java en: {java_path}")

    # Generar UUID y token ficticio
    player_uuid = str(uuid.uuid4())
    access_token = str(uuid.uuid4())

    # Construir classpath con solo las bibliotecas necesarias
    classpath_separator = ";" if OS_NAME == "windows" else ":"
    library_paths = get_required_libraries(manifest)
    log(f"Usando {len(library_paths)} bibliotecas para el classpath")

    classpath = f"{CLIENT_JAR}{classpath_separator}{classpath_separator.join([str(path) for path in library_paths])}"

    # Construir argumentos
    args = [java_path]

    # Opciones de memoria optimizadas (usar configuración del usuario)
    memory_mb = str(get_setting("memory_mb", 2048))
    args.extend([f"-Xmx{memory_mb}M", f"-Xms{memory_mb}M"])

    # Opciones de seguridad adicionales
    args.append(
        "-Djava.security.egd=file:/dev/./urandom"
    )  # Mejor fuente de aleatoriedad en Unix

    # Optimizaciones generales
    args.extend(
        [
            "-XX:+UseG1GC",  # Usar el recolector de basura G1
            "-XX:+ParallelRefProcEnabled",  # Procesamiento de referencias en paralelo
            "-XX:MaxGCPauseMillis=200",  # Limitar pausas de GC
            "-XX:+UnlockExperimentalVMOptions",
            "-XX:+DisableExplicitGC",  # Evitar GC explícito
        ]
    )

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
        # Usar subprocess con restricciones de seguridad adicionales
        subprocess.run(
            args,
            check=False,  # No levantar excepción si el comando falla
            timeout=None,  # Sin límite de tiempo para la ejecución
        )
        return True
    except FileNotFoundError:
        log("Java no está instalado o no está en PATH.", error=True)
        print("\n❌ ERROR: Java no está instalado o no está en PATH.")
        print(f"Intentamos usar Java en: {java_path}")
        print(
            "Por favor, instala Java y asegúrate de que esté en tu PATH o establece JAVA_HOME."
        )
        return False
    except Exception as e:
        log(f"Error al iniciar Minecraft: {e}", error=True)
        print(f"\n❌ ERROR al iniciar Minecraft: {e}")
        return False


def is_java_available():
    """Verifica si Java está disponible en el sistema"""
    java_path = find_java_path()

    try:
        # Intentar ejecutar 'java -version' para comprobar si Java funciona
        process = subprocess.run(
            [java_path, "-version"], capture_output=True, text=True, check=False
        )

        # Si el comando se ejecuta correctamente (return code 0)
        if process.returncode == 0:
            # Extraer la versión de Java del output (generalmente en stderr)
            version_output = process.stderr if process.stderr else process.stdout
            log(f"Java disponible: {version_output.splitlines()[0]}")
            return True
        else:
            log(f"Error al verificar Java: {process.stderr}", error=True)
            return False
    except Exception as e:
        log(f"Error al verificar Java: {e}", error=True)
        return False
