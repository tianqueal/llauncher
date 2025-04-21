# LLauncher

Este proyecto es un lanzador personalizado para Minecraft. Permite gestionar y lanzar el juego de manera sencilla, todo dentro de un entorno controlado. Está diseñado para ser fácil de usar y personalizar, y está optimizado para el desarrollo de nuevas características y mejoras.

## Requisitos

### Requisitos generales
Para ejecutar este proyecto correctamente, necesitarás tener instalado **Python 3.13+** y los siguientes paquetes:

- `art`: Para generar arte de texto decorativo.
- `requests`: Para realizar peticiones HTTP.
- `rich`: Para mostrar información bonita y formateada en la terminal.
- `psutil`: Para verificar el uso de recursos del sistema.

### Requisitos de desarrollo
Si eres desarrollador y quieres contribuir o trabajar en el código fuente, necesitas instalar los siguientes paquetes:

- `black`: Formateador de código automático para mantener el estilo consistente.
- `pyinstaller`: Para crear ejecutables a partir del código Python.

## Instalación

### 1. Clona el repositorio

Primero, clona el repositorio en tu máquina:

```bash
git clone https://github.com/tianqueal/llauncher.git
cd llauncher
```

### 2. Crea y activa un entorno virtual

Es altamente recomendable usar un entorno virtual para gestionar las dependencias del proyecto sin interferir con otros proyectos de Python en tu máquina.

- En Linux/MacOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

- En Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

### 3. Instala las dependencias

Para instalar las dependencias principales:

```bash
pip install -r requirements.txt
```

Para instalar las dependencias de desarrollo (si vas a trabajar en el código):

```bash
pip install -r requirements-dev.txt
```

## Uso

### Lanzar el proyecto

Una vez que las dependencias estén instaladas, puedes ejecutar el lanzador de Minecraft con el siguiente comando:

```bash
python main.py
```

### Generar ejecutable

Si quieres generar un archivo ejecutable para el lanzador, puedes usar PyInstaller con las siguientes opciones recomendadas:

```bash
# Para Linux/macOS
pyinstaller --clean --onefile --name llauncher main.py

# Para Windows
pyinstaller --clean --onefile --name llauncher.exe main.py
```

Estas opciones crearán un único archivo ejecutable (`--onefile`) que será más fácil de distribuir, y limpiará archivos temporales de compilaciones anteriores (`--clean`).

Si necesitas compilar para plataformas específicas:

```bash
# Para macOS (binario universal)
# Requiere macOS con chip Apple Silicon
arch -arm64 pyinstaller --clean --onefile --distpath dist/arm64 --name llauncher_macos_arm64 main.py
arch -x86_64 pyinstaller --clean --onefile --distpath dist/x86_64 --name llauncher_macos_x64 main.py
lipo -create dist/x86_64/llauncher_macos_x64 dist/arm64/llauncher_macos_arm64 -output dist/universal/llauncher_macos_universal
```

También puedes usar el script `build_all.sh` incluido para generar ejecutables para todas las plataformas soportadas.

Los ejecutables se generarán en el directorio `dist/`.

## Contribuciones

Las contribuciones son bienvenidas. Si quieres añadir nuevas características o corregir errores, por favor abre un Pull Request o un Issue en GitHub. Antes de hacer un Pull Request, asegúrate de que el código está correctamente formateado y que pase todas las pruebas (si las hay).

## Licencia

Este proyecto está bajo la Licencia MIT, lo que significa que puedes usar, copiar, modificar, fusionar, publicar, distribuir, sublicenciar y/o vender copias del software, siempre que incluyas el aviso de copyright y la exención de responsabilidad en todas las copias o partes sustanciales del software.

### Exención de Responsabilidad

El software se proporciona “TAL CUAL”, sin ninguna garantía, explícita o implícita, incluyendo pero no limitado a las garantías de comercialización, idoneidad para un propósito particular y no infracción. En ningún caso los autores o titulares del copyright serán responsables de cualquier reclamación, daño o responsabilidad, ya sea en una acción de contrato, agravio u otra, que surja de o en conexión con el uso del software.
