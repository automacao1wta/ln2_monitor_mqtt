# Configuração do Firebase

## Pré-requisitos

Para que a integração com o Firestore funcione, você precisa:

1. **Criar uma conta de serviço no Firebase**:
   - Acesse o [Console do Firebase](https://console.firebase.google.com)
   - Selecione o projeto `ln2monitor-flutter`
   - Vá em "Configurações do projeto" > "Contas de serviço"
   - Clique em "Gerar nova chave privada"
   - Baixe o arquivo JSON

2. **Configurar variáveis de ambiente**:
   - Copie o arquivo `.env.example` para `.env`
   - Abra o arquivo JSON baixado do Firebase
   - Preencha as variáveis no arquivo `.env` com os valores correspondentes:
     ```
     FIREBASE_PROJECT_ID=ln2monitor-flutter
     FIREBASE_PRIVATE_KEY_ID=valor_do_private_key_id
     FIREBASE_PRIVATE_KEY=valor_da_private_key_completa
     FIREBASE_CLIENT_EMAIL=valor_do_client_email
     FIREBASE_CLIENT_ID=valor_do_client_id
     FIREBASE_CLIENT_X509_CERT_URL=valor_da_client_x509_cert_url
     ```

3. **Configurar permissões do Firestore**:
   - No Console do Firebase, vá em "Firestore Database"
   - Configure as regras de segurança conforme necessário para sua aplicação

## ⚠️ IMPORTANTE - Segurança

- **NUNCA** commite o arquivo `.env` ou `firebase-config.json` no repositório Git
- O arquivo `.gitignore` já está configurado para ignorar esses arquivos
- Use sempre variáveis de ambiente para credenciais sensíveis

## Estrutura dos Dados no Firestore

Os dados são salvos na seguinte estrutura:
```
{equipamentID}/
  data/
    {YYYY-MM-DD}/
      {documentId}/
        - humidity: number (currently null - not available in current data)
        - pBat: number (battery percentage)
        - tempAmbient: number (ambient temperature)
        - tempPT100: number (PT100 temperature)
        - vBat: number (battery voltage in volts)
        - timestamp: timestamp
        - package_id: number (for reference)
```

## Variáveis Salvas

- **humidity**: 32.8 (number) - Atualmente não disponível nos dados, será null
- **pBat**: 84.6 (number) - Porcentagem da bateria
- **tempAmbient**: 17.22 (number) - Temperatura ambiente
- **tempPT100**: -178.39 (number) - Temperatura do sensor PT100
- **vBat**: 2.85 (number) - Tensão da bateria em volts

## Configurações do Projeto Firebase

- **Nome do projeto**: LN2Monitor-flutter
- **ID do projeto**: ln2monitor-flutter
- **Número do projeto**: 434082419488
- **Chave de API da Web**: AIzaSyDVczNtRga9TRheYULI2HIruV8KYtdmduw
- **Realtime Database URL**: https://ln2monitor-flutter-default-rtdb.firebaseio.com

## Para Máquina Virtual / Produção

### Opção 1: Arquivo .env (Recomendado)
1. Na máquina virtual, após fazer `git pull`, copie o arquivo `.env.example` para `.env`
2. Edite o arquivo `.env` com as credenciais reais:
   ```bash
   cp .env.example .env
   nano .env  # ou vim .env
   ```
3. Execute o Docker: `docker-compose up --build`

### Opção 2: Variáveis de ambiente do sistema
1. Defina as variáveis diretamente no sistema:
   ```bash
   export FIREBASE_PROJECT_ID="ln2monitor-flutter"
   export FIREBASE_PRIVATE_KEY_ID="sua_key_id"
   # ... outras variáveis
   ```
2. Execute o Docker: `docker-compose up --build`

### Opção 3: Docker Secrets (Produção)
Para ambientes de produção, considere usar Docker Secrets ou ferramentas como HashiCorp Vault.

## Como Executar

1. Configure o arquivo `.env` conforme descrito acima
2. Execute com Docker: `docker-compose up --build`
3. Ou execute localmente: `python main.py`
