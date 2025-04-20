#!/bin/bash

# Crear carpeta de dist si no existe
mkdir -p dist

echo "=== Compilando LLauncher para múltiples plataformas ==="

# Comprobar si docker está instalado
if ! command -v docker &> /dev/null; then
    echo "Error: Docker no está instalado. Por favor, instala Docker para continuar."
    exit 1
fi

# Comprobar si docker-compose está instalado
if ! command -v docker-compose &> /dev/null; then
    echo "Error: Docker Compose no está instalado. Por favor, instala Docker Compose para continuar."
    exit 1
fi

# Compilar versiones de Linux
echo "Compilando versión para Linux x64..."
docker-compose up --build linux-x64
echo "Compilando versión para Linux ARM64..."
docker-compose up --build linux-arm64

# Compilar versión de Windows (requiere Docker con soporte para contenedores Windows)
echo "Compilando versión para Windows x64..."
docker-compose up --build windows-x64

echo ""
echo "Nota: Para compilar versiones de macOS, necesitas una máquina con macOS."
echo "En una máquina macOS, ejecuta:"
echo "pyinstaller --clean --onefile --name llauncher_mac_\$(uname -m) main.py"

echo ""
echo "Ejecutables generados en la carpeta dist:"
ls -la dist/

echo ""
echo "¡Compilación completada!"
