#!/bin/bash
# Build script for MyFinca Pro Android App

set -e

echo "🐄 MyFinca Pro - Android Build Script"
echo "====================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js no está instalado. Instálalo primero.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Node.js $(node --version) encontrado${NC}"

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ npm no está instalado.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ npm $(npm --version) encontrado${NC}"

# Install Capacitor dependencies
echo -e "\n${YELLOW}📦 Instalando dependencias de Capacitor...${NC}"
npm install

# Initialize Capacitor if not already done
if [ ! -f "capacitor.config.ts" ]; then
    echo -e "${YELLOW}⚙️ Inicializando Capacitor...${NC}"
    npx cap init "MyFinca Pro" com.myfinca.pro --web-dir=dist
fi

# Add Android platform if not exists
if [ ! -d "android" ]; then
    echo -e "${YELLOW}📱 Agregando plataforma Android...${NC}"
    npx cap add android
fi

# Sync web assets
echo -e "${YELLOW}🔄 Sincronizando assets web...${NC}"
npx cap sync

echo -e "\n${GREEN}✅ Setup completado!${NC}"
echo -e "\n${YELLOW}Próximos pasos:${NC}"
echo "1. Abrir Android Studio: npx cap open android"
echo "2. En Android Studio: Build > Build Bundle(s) / APK(s) > Build APK(s)"
echo "3. El APK se generará en: android/app/build/outputs/apk/debug/app-debug.apk"
echo ""
echo -e "${YELLOW}Para release firmado:${NC}"
echo "1. En Android Studio: Build > Generate Signed Bundle / APK"
echo "2. Crear keystore si no existe"
echo "3. Seleccionar release y firmar"
echo ""
echo -e "${GREEN}URL de la app (para PWA):${NC} https://qxnkuzzckpmvyoqqyjcp.supabase.co"
