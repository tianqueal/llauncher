import platform
from pathlib import Path

# Configuraciones iniciales
MANIFEST_FILE = "1.21.5.json"
MANIFEST_URL = "https://piston-meta.mojang.com/v1/packages/a0645da8cf4e89da6baaab8e08b7ca64b7f4b0cf/1.21.5.json"
BASE_DIR = Path("llauncher")
GAME_DIR = BASE_DIR / Path(".minecraft")
MANIFEST_DIR = GAME_DIR / "manifest"
MANIFEST_JSON = MANIFEST_DIR / MANIFEST_FILE
LIBRARIES_DIR = GAME_DIR / "libraries"
ASSETS_DIR = GAME_DIR / "assets"
NATIVES_DIR = GAME_DIR / "natives"
CLIENT_JAR = GAME_DIR / "client.jar"
LOGS_DIR = BASE_DIR / "ll_logs"
CONFIG_DIR = BASE_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "settings.json"

# Configuración de descargas paralelas
MAX_WORKERS = 10  # Número máximo de descargas simultáneas

# Información del sistema
OS_NAME = platform.system().lower()  # windows, linux, darwin
