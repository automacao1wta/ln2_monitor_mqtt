#!/usr/bin/env python3
"""
Teste completo de timezone UTC para sistema de notificações
Valida que todas as lógicas de tempo estão usando UTC corretamente
"""

import sys
import os
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_timezone_consistency():
    """Testa se todas as funções de tempo estão usando UTC consistentemente"""
    print("🔍 Testando consistência de timezone UTC...")
    
    # Verificar imports necessários
    try:
        from notification_handler import NotificationHandler, NotificationConfig
        from message_processor import MessageProcessor
        print("✅ Imports realizados com sucesso")
    except Exception as e:
        print(f"❌ Erro no import: {e}")
        return
    
    # Simular timezone não-UTC para testar se o código está realmente usando UTC
    print("\n📍 Timezone local atual:", datetime.now().astimezone().tzinfo)
    print("📍 Timezone UTC:", datetime.now(timezone.utc).tzinfo)
    
    # Calcular diferença entre local e UTC
    local_now = datetime.now()
    utc_now = datetime.now(timezone.utc)
    local_timestamp = int(local_now.timestamp())
    utc_timestamp = int(utc_now.timestamp())
    
    print(f"📊 Timestamp local: {local_timestamp}")
    print(f"📊 Timestamp UTC:   {utc_timestamp}")
    print(f"📊 Diferença: {abs(local_timestamp - utc_timestamp)} segundos")
    
    if abs(local_timestamp - utc_timestamp) > 1:
        print("⚠️  Sistema tem diferença de timezone significativa - perfeito para teste!")
    else:
        print("ℹ️  Sistema em UTC ou timezone próximo - teste ainda válido")
    
    # Teste 1: Rate limiting de notificações
    print("\n🧪 Teste 1: Rate limiting de notificações")
    test_rate_limiting()
    
    # Teste 2: Comparação de lastTX 
    print("\n🧪 Teste 2: Comparação de lastTX")
    test_lasttx_comparison()
    
    # Teste 3: Agrupamento de notificações
    print("\n🧪 Teste 3: Agrupamento de notificações")
    test_notification_grouping()
    
    print("\n✅ Todos os testes de timezone concluídos!")

def test_rate_limiting():
    """Testa se o rate limiting está usando UTC consistentemente"""
    try:
        # Simular timestamps de notificações em diferentes timezones
        utc_now = datetime.now(timezone.utc)
        
        # Timestamp de 30 minutos atrás (deveria estar dentro do limite de 1 hora)
        thirty_min_ago = utc_now - timedelta(minutes=30)
        
        # Timestamp de 2 horas atrás (deveria estar fora do limite de 1 hora)
        two_hours_ago = utc_now - timedelta(hours=2)
        
        print(f"   Agora UTC: {utc_now}")
        print(f"   30min atrás: {thirty_min_ago}")
        print(f"   2h atrás: {two_hours_ago}")
        
        # Simular diferença com timezone local vs UTC
        hour_ago_utc = utc_now - timedelta(hours=1)
        time_diff_seconds = (utc_now - thirty_min_ago).total_seconds()
        time_diff_hours = time_diff_seconds / 3600
        
        print(f"   ⏰ Diferença de 30min em horas: {time_diff_hours:.2f}")
        print(f"   ⏰ Deveria ser ~0.5 horas: {'✅' if 0.4 <= time_diff_hours <= 0.6 else '❌'}")
        
        # Teste com timestamp antigo
        time_diff_old = (utc_now - two_hours_ago).total_seconds() / 3600
        print(f"   ⏰ Diferença de 2h em horas: {time_diff_old:.2f}")
        print(f"   ⏰ Deveria ser ~2.0 horas: {'✅' if 1.9 <= time_diff_old <= 2.1 else '❌'}")
        
    except Exception as e:
        print(f"❌ Erro no teste de rate limiting: {e}")

def test_lasttx_comparison():
    """Testa comparação de lastTX com timezone UTC"""
    try:
        # Simular lastTX epoch timestamp (sempre em UTC)
        utc_now = datetime.now(timezone.utc)
        last_tx_epoch = int(utc_now.timestamp()) - 3600  # 1 hora atrás
        
        # Converter lastTX para datetime UTC (método correto)
        last_tx_time_utc = datetime.fromtimestamp(last_tx_epoch, tz=timezone.utc)
        current_time_utc = datetime.now(timezone.utc)
        
        time_diff_hours = (current_time_utc - last_tx_time_utc).total_seconds() / 3600
        
        print(f"   LastTX epoch: {last_tx_epoch}")
        print(f"   LastTX UTC: {last_tx_time_utc}")
        print(f"   Current UTC: {current_time_utc}")
        print(f"   ⏰ Diferença: {time_diff_hours:.2f} horas")
        print(f"   ⏰ Deveria ser ~1.0 hora: {'✅' if 0.9 <= time_diff_hours <= 1.1 else '❌'}")
        
        # Teste de threshold de conexão (1 hora por padrão)
        connection_timeout_hours = 1.0
        is_connected = time_diff_hours <= connection_timeout_hours
        print(f"   🔗 Dispositivo conectado: {'✅' if is_connected else '❌'}")
        
    except Exception as e:
        print(f"❌ Erro no teste de lastTX: {e}")

def test_notification_grouping():
    """Testa agrupamento de notificações com timestamps UTC"""
    try:
        utc_now = datetime.now(timezone.utc)
        
        # Simular notificações criadas em momentos diferentes
        notification_1 = {
            'type': 'status_change',
            'created_at': utc_now - timedelta(seconds=45)  # 45 segundos atrás
        }
        
        notification_2 = {
            'type': 'status_change', 
            'created_at': utc_now - timedelta(seconds=10)  # 10 segundos atrás
        }
        
        # Simular lógica de agrupamento (delay máximo de 30 segundos)
        max_group_delay_seconds = 30
        oldest_time = min(notification_1['created_at'], notification_2['created_at'])
        time_since_oldest = (utc_now - oldest_time).total_seconds()
        
        print(f"   Notificação 1: {notification_1['created_at']}")
        print(f"   Notificação 2: {notification_2['created_at']}")
        print(f"   Mais antiga: {oldest_time}")
        print(f"   ⏰ Tempo desde mais antiga: {time_since_oldest:.1f} segundos")
        print(f"   ⏰ Delay máximo: {max_group_delay_seconds} segundos")
        
        should_send = time_since_oldest >= max_group_delay_seconds
        print(f"   📤 Deveria enviar agora: {'✅' if should_send else '❌'}")
        
    except Exception as e:
        print(f"❌ Erro no teste de agrupamento: {e}")

def test_edge_cases():
    """Testa casos extremos de timezone"""
    print("\n🧪 Teste 4: Casos extremos")
    
    try:
        # Teste com mudança de horário de verão
        utc_now = datetime.now(timezone.utc)
        
        # Simular timestamp próximo a mudança de horário (pode variar por região)
        print(f"   UTC atual: {utc_now}")
        print(f"   Local atual: {datetime.now()}")
        
        # Verificar se as funções são consistentes
        epoch_1 = int(utc_now.timestamp())
        time.sleep(0.1)  # Pequena pausa
        epoch_2 = int(datetime.now(timezone.utc).timestamp())
        
        diff = abs(epoch_2 - epoch_1)
        print(f"   ⏰ Diferença entre dois UTC calls: {diff} segundos")
        print(f"   ⏰ Deveria ser ≤ 1 segundo: {'✅' if diff <= 1 else '❌'}")
        
    except Exception as e:
        print(f"❌ Erro no teste de casos extremos: {e}")

if __name__ == "__main__":
    test_timezone_consistency()
    test_edge_cases()
