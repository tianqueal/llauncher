#!/bin/bash

# ===================================================================
# Script de compilación multiplataforma para LLauncher
# Soporta las siguientes plataformas y arquitecturas:
#   - macOS: x86_64 (Intel), arm64 (Apple Silicon), Universal
#   - Linux: x86_64, ARM64
#   - Windows: x86_64, ARM64
# ===================================================================

# Colores para mensajes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # Sin color

# Función para mostrar ayuda
show_help() {
  echo -e "${BOLD}Uso:${NC} $0 [opciones]"
  echo -e ""
  echo -e "Este script compila LLauncher para múltiples plataformas y arquitecturas."
  echo -e ""
  echo -e "${BOLD}Opciones:${NC}"
  echo -e "  -h, --help         Muestra esta ayuda"
  echo -e "  --macos-intel      Compila solo para macOS Intel (x86_64)"
  echo -e "  --macos-arm        Compila solo para macOS Apple Silicon (ARM64)"
  echo -e "  --macos-universal  Compila un binario universal para macOS (requiere Apple Silicon)"
  echo -e "  --linux-x64        Compila solo para Linux x86_64 (requiere Docker)"
  echo -e "  --linux-arm        Compila solo para Linux ARM64 (requiere Docker)"
  echo -e "  --windows-x64      Compila solo para Windows x86_64 (requiere Docker)"
  echo -e "  --windows-arm      Compila solo para Windows ARM64 (requiere Docker)"
  echo -e "  --all              Compila todas las plataformas posibles para tu equipo"
  echo -e ""
  echo -e "Si no se especifica ninguna opción, se compilarán todas las versiones compatibles con tu sistema."
}

# Procesamiento de argumentos
MACOS_INTEL=0
MACOS_ARM=0
MACOS_UNIVERSAL=0
LINUX_X64=0
LINUX_ARM=0
WINDOWS_X64=0
WINDOWS_ARM=0
ALL=0

if [ $# -eq 0 ]; then
  ALL=1
else
  for arg in "$@"; do
    case $arg in
      -h|--help)
        show_help
        exit 0
        ;;
      --macos-intel)
        MACOS_INTEL=1
        ;;
      --macos-arm)
        MACOS_ARM=1
        ;;
      --macos-universal)
        MACOS_UNIVERSAL=1
        ;;
      --linux-x64)
        LINUX_X64=1
        ;;
      --linux-arm)
        LINUX_ARM=1
        ;;
      --windows-x64)
        WINDOWS_X64=1
        ;;
      --windows-arm)
        WINDOWS_ARM=1
        ;;
      --all)
        ALL=1
        ;;
      *)
        echo -e "${RED}Opción desconocida: $arg${NC}"
        show_help
        exit 1
        ;;
    esac
  done
fi

# Crear carpeta de dist si no existe
mkdir -p dist

echo -e "${BOLD}${BLUE}=== Compilando LLauncher para múltiples plataformas ===${NC}"

# Detectar el sistema operativo y arquitectura
OS=$(uname -s)
ARCH=$(uname -m)

echo -e "${BOLD}Sistema detectado:${NC} $OS $ARCH"
echo ""

# Función para compilar versiones de macOS
build_macos() {
  # Crear directorios para los binarios
  mkdir -p dist/x86_64
  mkdir -p dist/arm64
  mkdir -p dist/universal
  
  # Verificar disponibilidad de Python y PyInstaller
  if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 no está instalado.${NC}"
    return 1
  fi
  
  # Instalar PyInstaller si no está instalado
  python3 -c "import PyInstaller" &> /dev/null || {
    echo -e "${YELLOW}Instalando PyInstaller...${NC}"
    python3 -m pip install pyinstaller
  }
  
  # Compilar según las opciones y capacidades del sistema
  if [[ "$ARCH" == "arm64" ]]; then
    # En un Mac con Apple Silicon
    if [[ "$ALL" == "1" || "$MACOS_ARM" == "1" || "$MACOS_UNIVERSAL" == "1" ]]; then
      echo -e "${GREEN}Compilando versión para macOS ARM64...${NC}"
      arch -arm64 python3 -m PyInstaller --clean --onefile --distpath dist/arm64 --name llauncher_macos_arm64 main.py
      echo -e "${GREEN}✓ Compilación para macOS ARM64 completada${NC}"
    fi
    
    if [[ "$ALL" == "1" || "$MACOS_INTEL" == "1" || "$MACOS_UNIVERSAL" == "1" ]]; then
      echo -e "${GREEN}Compilando versión para macOS x64 mediante Rosetta 2...${NC}"
      arch -x86_64 python3 -m PyInstaller --clean --onefile --distpath dist/x86_64 --name llauncher_macos_x64 main.py
      echo -e "${GREEN}✓ Compilación para macOS Intel x64 completada${NC}"
    fi
    
    if [[ "$ALL" == "1" || "$MACOS_UNIVERSAL" == "1" ]]; then
      if [[ -f "dist/x86_64/llauncher_macos_x64" && -f "dist/arm64/llauncher_macos_arm64" ]]; then
        echo -e "${GREEN}Creando binario universal...${NC}"
        lipo -create dist/x86_64/llauncher_macos_x64 dist/arm64/llauncher_macos_arm64 -output dist/universal/llauncher_macos_universal
        echo -e "${GREEN}✓ Binario universal para macOS creado${NC}"
      else
        echo -e "${YELLOW}Advertencia: No se pudo crear el binario universal porque faltan las compilaciones de Intel o ARM64.${NC}"
      fi
    fi
  elif [[ "$ARCH" == "x86_64" ]]; then
    # En un Mac con Intel
    if [[ "$ALL" == "1" || "$MACOS_INTEL" == "1" ]]; then
      echo -e "${GREEN}Compilando versión para macOS x64...${NC}"
      python3 -m PyInstaller --clean --onefile --distpath dist/x86_64 --name llauncher_macos_x64 main.py
      echo -e "${GREEN}✓ Compilación para macOS Intel x64 completada${NC}"
    fi
    
    if [[ "$MACOS_ARM" == "1" ]]; then
      echo -e "${YELLOW}Advertencia: No se puede compilar para ARM64 en un Mac con Intel.${NC}"
    fi
    
    if [[ "$MACOS_UNIVERSAL" == "1" ]]; then
      echo -e "${YELLOW}Advertencia: No se puede crear un binario universal en un Mac con Intel.${NC}"
      echo -e "${YELLOW}Se necesita un Mac con Apple Silicon para compilar todas las arquitecturas.${NC}"
    fi
  fi
}

# Función para compilar versiones de Linux/Windows usando Docker
build_with_docker() {
  # Comprobar si docker está instalado
  if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker no está instalado. Por favor, instala Docker para continuar.${NC}"
    return 1
  fi

  # Comprobar si docker-compose está instalado
  if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: Docker Compose no está instalado. Por favor, instala Docker Compose para continuar.${NC}"
    return 1
  fi

  # Compilar versiones de Linux
  if [[ "$ALL" == "1" || "$LINUX_X64" == "1" ]]; then
    echo -e "${GREEN}Compilando versión para Linux x64...${NC}"
    docker-compose up --build linux-x64
    echo -e "${GREEN}✓ Compilación para Linux x64 completada${NC}"
  fi
  
  if [[ "$ALL" == "1" || "$LINUX_ARM" == "1" ]]; then
    echo -e "${GREEN}Compilando versión para Linux ARM64...${NC}"
    docker-compose up --build linux-arm64
    echo -e "${GREEN}✓ Compilación para Linux ARM64 completada${NC}"
  fi

  # Compilar versiones de Windows
  if [[ "$ALL" == "1" || "$WINDOWS_X64" == "1" ]]; then
    echo -e "${GREEN}Compilando versión para Windows x64...${NC}"
    docker-compose up --build windows-x64
    echo -e "${GREEN}✓ Compilación para Windows x64 completada${NC}"
  fi
  
  if [[ "$ALL" == "1" || "$WINDOWS_ARM" == "1" ]]; then
    echo -e "${GREEN}Compilando versión para Windows ARM64...${NC}"
    docker-compose up --build windows-arm
    echo -e "${GREEN}✓ Compilación para Windows ARM64 completada${NC}"
  fi
}

# Compilar según el sistema operativo
if [[ "$OS" == "Darwin" ]]; then
  # Estamos en macOS
  echo -e "${BLUE}Detectado macOS. Compilando versiones nativas...${NC}"
  build_macos
  
  # Verificar si también se solicitan compilaciones con Docker
  if [[ "$ALL" == "1" || "$LINUX_X64" == "1" || "$LINUX_ARM" == "1" || "$WINDOWS_X64" == "1" || "$WINDOWS_ARM" == "1" ]]; then
    echo -e "${BLUE}Compilando versiones adicionales con Docker...${NC}"
    build_with_docker
  fi
else
  # Estamos en otro sistema operativo (Linux, Windows con WSL, etc.)
  if [[ "$MACOS_INTEL" == "1" || "$MACOS_ARM" == "1" || "$MACOS_UNIVERSAL" == "1" ]]; then
    echo -e "${YELLOW}Advertencia: Para compilar versiones de macOS, necesitas una máquina con macOS.${NC}"
  fi
  
  echo -e "${BLUE}Compilando versiones para Linux y Windows usando Docker...${NC}"
  build_with_docker
fi

# Mostrar resultados
echo ""
echo -e "${BOLD}${GREEN}¡Compilación completada!${NC}"
echo ""
echo -e "${BOLD}Ejecutables generados:${NC}"
find dist -type f -not -path "*/\.*" | sort

echo ""
echo -e "${BLUE}Puedes encontrar todos los ejecutables en la carpeta ${BOLD}dist/${NC}"
