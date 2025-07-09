#!/usr/bin/env python3
"""
Script de teste para verificar a integração com o Firestore
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from message_processor import MessageProcessor
from queue import Queue
from datetime import datetime

def test_firestore_integration():
    """
    Testa a integração com o Firestore usando dados de exemplo
    """
    # Criar um MessageProcessor
    message_queue = Queue()
    processor = MessageProcessor(message_queue)
    
    # Dados de exemplo simulando uma mensagem MQTT
    test_message_dict = {
        'beacon_serial': 'TEST_BEACON_001',
        'package_id': 12345,
        'batt_percent': 84.6,
        'temp_ambient': 17.22,
        'temp_pt100': -178.39,
        'vbat_mv': 2850,  # 2850 mV = 2.85 V
        'topic': 'test/topic'
    }
    
    print("Testando integração com Firestore...")
    print(f"Dados de teste: {test_message_dict}")
    
    try:
        # Testar apenas a função do Firestore
        processor.save_message_to_firestore('test/topic', test_message_dict)
        print("✅ Teste de Firestore executado com sucesso!")
        print("Verifique no console do Firebase se os dados foram salvos.")
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")

if __name__ == "__main__":
    test_firestore_integration()
