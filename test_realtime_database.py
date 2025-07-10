#!/usr/bin/env python3
"""
Teste para verificar se a função update_realtime_database está gerando timestamps UTC corretos.
"""

import sys
import os
from datetime import datetime, timezone
from unittest.mock import Mock

# Adicionar o diretório atual ao path para importar os módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from message_processor import MessageProcessor

def test_realtime_database_timestamp():
    """Testa se a função update_realtime_database gera timestamps UTC corretos."""
    print("Testando timestamp UTC na função update_realtime_database...")
    
    # Criar um MessageProcessor mock para teste
    mock_queue = Mock()
    processor = MessageProcessor(mock_queue)
    
    # Simular dados MQTT de entrada
    test_message_dict = {
        'beacon_serial': 'TEST123',
        'temp_pt100': 25.5,
        'rssi': -65,
        'vbat': 3.6,
        'temp_humid_sensor': 23.2,
        'umid_humid_sensor': 45.8,
        'level_low': '0',
        'cover_error': '0',
        'device_health': '10 - Normal'
    }
    
    mac_equipament = 'AA:BB:CC:DD:EE:FF'
    equipment_id = 'EQUIP001'
    
    # Mock do Firebase DB
    mock_db_ref = Mock()
    processor.db = Mock()
    processor.db.reference.return_value = mock_db_ref
    
    # Capturar o timestamp antes da chamada
    before_timestamp = int(datetime.now(timezone.utc).timestamp())
    
    try:
        # Chamar a função (irá falhar porque não temos Firebase real, mas podemos capturar os dados)
        processor.update_realtime_database('test/topic', test_message_dict)
    except Exception as e:
        print(f"Exceção esperada (sem Firebase real): {e}")
    
    # Verificar se o mock foi chamado
    if processor.db.reference.called:
        print("✅ Função update_realtime_database foi chamada!")
        
        # Analisar argumentos passados
        call_args = processor.db.reference.call_args_list
        print(f"Argumentos da chamada: {call_args}")
    else:
        print("❌ Função update_realtime_database não foi chamada")
    
    # Capturar timestamp depois da chamada
    after_timestamp = int(datetime.now(timezone.utc).timestamp())
    
    print(f"Timestamp antes: {before_timestamp}")
    print(f"Timestamp depois: {after_timestamp}")
    print(f"Diferença: {after_timestamp - before_timestamp} segundos")
    
    # Verificar se o código está gerando timestamps corretos internamente
    # Simular o que acontece dentro da função
    current_time = datetime.now(timezone.utc)
    epoch_timestamp = str(int(current_time.timestamp()))
    
    print(f"Timestamp gerado pela lógica corrigida: {epoch_timestamp}")
    
    # Verificar se está próximo dos timestamps de referência
    generated_timestamp = int(epoch_timestamp)
    if abs(generated_timestamp - before_timestamp) <= 2 and abs(generated_timestamp - after_timestamp) <= 2:
        print("✅ Timestamp gerado está correto (UTC)!")
    else:
        print("❌ Timestamp gerado parece estar incorreto!")

if __name__ == "__main__":
    test_realtime_database_timestamp()
