# Sistema de Notificações LN2 Monitor

Sistema inteligente de notificações para o monitoramento de dispositivos LN2, com detecção de mudanças de estado, notificações de recuperação e verificação de conexão.

## 🚀 Características Principais

- **🔄 Toggle Listener/Polling**: Escolha entre detecção em tempo real ou verificação periódica
- **⚡ Detecção Inteligente**: Só notifica em mudanças de estado, evitando spam
- **📱 Notificações Agrupadas**: Múltiplos problemas = 1 notificação unificada
- **🔧 Configurações Flexíveis**: Todos os parâmetros ajustáveis
- **💾 Rate Limiting**: Proteção contra spam de notificações
- **🔌 Verificação de Conexão**: Monitora lastTX para detectar dispositivos offline
- **✅ Notificações de Recuperação**: Alerta quando problemas são resolvidos

## 📋 Tipos de Notificação Monitorados

| Campo | Valor Normal | Severidade | Descrição |
|-------|--------------|------------|-----------|
| `ln2_level_status` | "04" | Alta | Nível de LN2 |
| `ln2_angle_status` | "04" | Baixa | Ângulo do dispositivo |
| `ln2_battery_status` | "04" | Alta | Status da bateria |
| `ln2_foam_status` | "08" | Baixa | Status da espuma |
| `connection` | - | Alta | Conexão via lastTX |

## 🛠️ Configuração

### Modo de Operação

#### Polling (Recomendado para produção)
```python
# Configuração conservadora de recursos
processor.toggle_notification_mode("polling")
processor.update_notification_config(polling_interval_minutes=10)
```

#### Listener (Tempo real)
```python
# Detecção imediata, maior uso de recursos
processor.toggle_notification_mode("listener")
```

### Configurações Principais

```python
# Timeouts e intervalos
processor.update_notification_config(
    polling_interval_minutes=5,        # Intervalo do polling
    connection_timeout_hours=1.0,      # Timeout para conexão
    max_group_delay_seconds=30         # Delay para agrupar notificações
)

# Rate limiting
processor.update_notification_config(
    max_notifications_per_device_per_hour=20  # Limite por dispositivo
)

# Recursos
processor.update_notification_config(
    recovery_notifications_enabled=True,      # Notificações de recuperação
    connection_check_enabled=True,            # Verificar conexão
    group_notifications_same_device=True      # Agrupar notificações
)
```

### Arquivo de Configuração

Copie `notification_config.json.example` para `notification_config.json` e edite:

```json
{
  "mode": "polling",
  "polling_interval_minutes": 10,
  "connection_timeout_hours": 1.0,
  "normal_status_values": {
    "ln2_level_status": "04",
    "ln2_angle_status": "04", 
    "ln2_battery_status": "04",
    "ln2_foam_status": "08"
  },
  "field_severities": {
    "ln2_level_status": "high",
    "ln2_angle_status": "low",
    "ln2_battery_status": "high", 
    "ln2_foam_status": "low",
    "connection": "high"
  }
}
```

## 📊 Estrutura das Notificações

### Notificação de Alerta
```json
{
  "type": "ln2_level_status_alert",
  "field_name": "ln2_level_status",
  "message": "Nível de LN2: Bad",
  "deviceId": "LN2-00100",
  "current_value": "06",
  "previous_value": "04",
  "severity": "high",
  "timestamp_emitted": "2025-07-09T15:30:00Z",
  "status": "active",
  "view_status": "unread"
}
```

### Notificação de Recuperação
```json
{
  "type": "ln2_level_status_recovery",
  "field_name": "ln2_level_status", 
  "message": "Nível de LN2 normalizado",
  "deviceId": "LN2-00100",
  "severity": "high",
  "timestamp_emitted": "2025-07-09T16:00:00Z",
  "status": "active",
  "view_status": "unread"
}
```

### Notificação de Conexão
```json
{
  "type": "connection_lost",
  "field_name": "connection",
  "message": "Sem comunicação com o dispositivo há 1.2 horas",
  "deviceId": "LN2-00100",
  "last_seen": "2025-07-09T14:00:00Z",
  "hours_offline": 1.2,
  "severity": "high",
  "timestamp_emitted": "2025-07-09T15:12:00Z",
  "status": "active", 
  "view_status": "unread"
}
```

### Notificação Agrupada
```json
{
  "type": "multiple_alerts",
  "field_name": "multiple",
  "message": "Múltiplos alertas: Nível de LN2: Bad; Status da bateria: Warning",
  "deviceId": "LN2-00100",
  "alert_count": 2,
  "alert_types": ["ln2_level_status_alert", "ln2_battery_status_alert"],
  "severity": "high",
  "timestamp_emitted": "2025-07-09T15:30:00Z",
  "status": "active",
  "view_status": "unread"
}
```

## 🔄 Lógica de Notificação

### Estados de Transição

| Transição | Ação | Exemplo |
|-----------|------|---------|
| Normal → Anormal | ✅ Gera alerta | "04" → "06": "Nível de LN2: Bad" |
| Anormal → Normal | ✅ Gera recuperação | "06" → "04": "Nível de LN2 normalizado" |
| Anormal → Anormal (mesmo) | ❌ Ignora | "06" → "06": Sem notificação |
| Anormal → Anormal (diferente) | ✅ Gera mudança | "06" → "05": "Mudou: Bad → Warning" |

### Rate Limiting

- **Limite por dispositivo**: 20 notificações/hora (configurável)
- **Agrupamento**: Múltiplos problemas em 30s = 1 notificação
- **Deduplicação**: Não notifica mesmo estado repetidas vezes

## 💻 Integração com MessageProcessor

O sistema é automaticamente integrado ao `MessageProcessor`:

```python
from message_processor import MessageProcessor
from queue import Queue

# Inicialização automática
message_queue = Queue()
processor = MessageProcessor(message_queue)  # Notificações inicializadas automaticamente

# Verificar status
status = processor.get_notification_status()
print(status)

# Alterar configurações em runtime
processor.toggle_notification_mode("polling")
processor.update_notification_config(polling_interval_minutes=5)

# Cleanup ao finalizar
processor.cleanup()
```

## 🔍 Monitoramento e Debug

### Verificar Status
```python
status = processor.get_notification_status()
# Retorna: mode, devices_monitored, total_active_notifications, etc.
```

### Logs
O sistema registra logs detalhados em:
- Mudanças de estado detectadas
- Notificações enviadas
- Rate limiting aplicado
- Erros de conexão

### Arquivo de Cache
- `mac_equipment_cache.json`: Cache MAC → Equipment ID
- `notification_config.json`: Configurações persistentes

## ⚠️ Considerações de Performance

### Modo Polling (Recomendado)
- **✅ Menor custo**: Controla quando consultar Firebase
- **✅ Menor CPU/Memória**: Não mantém conexões ativas
- **❌ Delay**: 5-10 min para detectar remoção de notificações

### Modo Listener
- **✅ Tempo real**: Detecção imediata de mudanças
- **❌ Maior custo**: Mais operações no Firebase
- **❌ Maior recursos**: Mantém conexões ativas

### Configuração Recomendada para Produção
```json
{
  "mode": "polling",
  "polling_interval_minutes": 10,
  "connection_timeout_hours": 1.0,
  "max_notifications_per_device_per_hour": 15,
  "group_notifications_same_device": true,
  "max_group_delay_seconds": 30
}
```

## 🧪 Teste e Exemplo

Execute o arquivo de exemplo:
```bash
python notification_example.py
```

Este arquivo demonstra:
- Configuração básica
- Alteração entre modos
- Simulação de dados MQTT
- Todas as configurações disponíveis

## 🔧 Troubleshooting

### Notificações não são geradas
1. Verificar se `realtime_db` está conectado
2. Confirmar que valores "normais" estão corretos
3. Verificar rate limiting nos logs

### Sistema não inicia
1. Verificar credenciais do Firebase
2. Confirmar arquivo de configuração válido
3. Verificar permissões de escrita

### Performance lenta
1. Aumentar `polling_interval_minutes`
2. Reduzir `max_notifications_per_device_per_hour`
3. Considerar usar modo polling em vez de listener

---

**Desenvolvido para o LN2 Monitor System**  
Sistema robusto e configurável para monitoramento em tempo real de dispositivos LN2.
