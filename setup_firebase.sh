#!/bin/bash

# Script para configurar o ambiente Firebase na máquina virtual
# Execute este script após fazer git pull

echo "=== Configuração do Firebase para LN2 Monitor ==="
echo

# Verificar se o arquivo .env já existe
if [ -f ".env" ]; then
    echo "⚠️  Arquivo .env já existe!"
    read -p "Deseja sobrescrevê-lo? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Configuração cancelada."
        exit 1
    fi
fi

# Copiar o arquivo de exemplo
if [ -f ".env.example" ]; then
    cp .env.example .env
    echo "✅ Arquivo .env criado a partir do .env.example"
else
    echo "❌ Arquivo .env.example não encontrado!"
    exit 1
fi

echo
echo "📝 Agora você precisa editar o arquivo .env com suas credenciais do Firebase:"
echo "   - FIREBASE_PRIVATE_KEY_ID"
echo "   - FIREBASE_PRIVATE_KEY"
echo "   - FIREBASE_CLIENT_EMAIL"
echo "   - FIREBASE_CLIENT_ID"
echo "   - FIREBASE_CLIENT_X509_CERT_URL"
echo
echo "Comandos úteis:"
echo "   nano .env     # Editar com nano"
echo "   vim .env      # Editar com vim"
echo
echo "Após editar o arquivo .env, execute:"
echo "   docker-compose up --build"
echo
echo "📖 Para mais informações, consulte: FIREBASE_SETUP.md"
