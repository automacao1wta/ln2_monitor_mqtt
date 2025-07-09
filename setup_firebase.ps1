# Script PowerShell para configurar o ambiente Firebase na máquina virtual
# Execute este script após fazer git pull

Write-Host "=== Configuração do Firebase para LN2 Monitor ===" -ForegroundColor Green
Write-Host

# Verificar se o arquivo .env já existe
if (Test-Path ".env") {
    Write-Host "⚠️  Arquivo .env já existe!" -ForegroundColor Yellow
    $response = Read-Host "Deseja sobrescrevê-lo? (y/N)"
    if ($response -ne "y" -and $response -ne "Y") {
        Write-Host "Configuração cancelada." -ForegroundColor Red
        exit 1
    }
}

# Copiar o arquivo de exemplo
if (Test-Path ".env.example") {
    Copy-Item ".env.example" ".env"
    Write-Host "✅ Arquivo .env criado a partir do .env.example" -ForegroundColor Green
} else {
    Write-Host "❌ Arquivo .env.example não encontrado!" -ForegroundColor Red
    exit 1
}

Write-Host
Write-Host "📝 Agora você precisa editar o arquivo .env com suas credenciais do Firebase:" -ForegroundColor Cyan
Write-Host "   - FIREBASE_PRIVATE_KEY_ID"
Write-Host "   - FIREBASE_PRIVATE_KEY"
Write-Host "   - FIREBASE_CLIENT_EMAIL"
Write-Host "   - FIREBASE_CLIENT_ID"
Write-Host "   - FIREBASE_CLIENT_X509_CERT_URL"
Write-Host
Write-Host "Comandos úteis:" -ForegroundColor Yellow
Write-Host "   notepad .env      # Editar com Notepad"
Write-Host "   code .env         # Editar com VS Code"
Write-Host
Write-Host "Após editar o arquivo .env, execute:" -ForegroundColor Cyan
Write-Host "   docker-compose up --build"
Write-Host
Write-Host "📖 Para mais informações, consulte: FIREBASE_SETUP.md" -ForegroundColor Blue
