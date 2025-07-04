# MQTT Client

Este repositório contém o código para o recebimento dos dados do projeto IoC via MQTT.

## Configuração

O script pode ser executado com o Docker (`docker compose up --build`) ou com uma instalação local do python.

Caso utilize a instalação local, lembre-se de instalar os pré-requisitos (`pip install -r requirements.txt`), também é recomendável que se utilize um ambiente virtual para isolar as dependências.

Independentemente do método utilizado, siga os seguintes passos:

1. Edite o arquivo `config.yaml` com as informações do cenário (gateways, taxa de amostragem, broker, etc).

2. Execute o script com um dos seguintes comandos (a depender do método escolhido):
    - `python main.py`
    - `docker compose up --build`

Os dados serão printados no terminal e, paralelamente, serão salvos os arquivos JSON na pasta `/output`