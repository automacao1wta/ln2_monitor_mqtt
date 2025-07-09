"""
Exemplo de uso do Sistema de Notificações LN2 Monitor

Este arquivo demonstra como utilizar e configurar o sistema de notificações.
"""

from message_processor import MessageProcessor
from notification_handler import NotificationMode
from queue import Queue
import time

def exemplo_uso_basico():
    """Exemplo básico de uso do sistema de notificações"""
    
    # Criar MessageProcessor (que automaticamente inicializa as notificações)
    message_queue = Queue()
    processor = MessageProcessor(message_queue)
    
    # Verificar status do sistema de notificações
    status = processor.get_notification_status()
    print("Status das notificações:", status)
    
    # Aguardar um pouco para demonstração
    time.sleep(2)
    
    # Finalizar
    processor.cleanup()

def exemplo_configuracao_avancada():
    """Exemplo de configuração avançada do sistema"""
    
    message_queue = Queue()
    processor = MessageProcessor(message_queue)
    
    # Alterar para modo listener
    print("Alternando para modo listener...")
    processor.toggle_notification_mode("listener")
    
    # Atualizar configurações
    print("Atualizando configurações...")
    processor.update_notification_config(
        polling_interval_minutes=5,  # Polling a cada 5 minutos
        connection_timeout_hours=0.5,  # Timeout de conexão em 30 minutos
        max_notifications_per_device_per_hour=30  # Mais notificações por hora
    )
    
    # Verificar status atualizado
    status = processor.get_notification_status()
    print("Status após configuração:", status)
    
    # Voltar para modo polling
    print("Voltando para modo polling...")
    processor.toggle_notification_mode("polling")
    
    # Finalizar
    processor.cleanup()

def exemplo_simulacao_mqtt():
    """Simula recebimento de dados MQTT com diferentes status"""
    
    message_queue = Queue()
    processor = MessageProcessor(message_queue)
    
    # Simular dados MQTT com status anormal
    mqtt_data_anormal = {
        'beacon_serial': '90395E0AE8A7',
        'ln2_level_status': '06',  # Bad (anormal)
        'ln2_angle_status': '04',  # Good (normal)
        'ln2_battery_status': '05',  # Warning (anormal)
        'ln2_foam_status': '08',   # Normal para foam
        'temp_pt100': 25.5,
        'temp_ambient': 28.3,
        'vbat_mv': 3200,
        'package_id': 12345,
    }
    
    # Simular dados MQTT com status normal (recuperação)
    mqtt_data_normal = {
        'beacon_serial': '90395E0AE8A7',
        'ln2_level_status': '04',  # Good (recuperado)
        'ln2_angle_status': '04',  # Good
        'ln2_battery_status': '04',  # Good (recuperado)
        'ln2_foam_status': '08',   # Normal
        'temp_pt100': 25.8,
        'temp_ambient': 28.1,
        'vbat_mv': 3300,
        'package_id': 12346,
    }
    
    print("Simulando dados com problemas...")
    # Simular o processo que normalmente seria feito após salvar no Firestore
    if hasattr(processor, 'notification_handler') and processor.notification_handler:
        # Assumindo que temos um equipamento LN2-00100
        processor.notification_handler.process_mqtt_data("LN2-00100", mqtt_data_anormal)
    
    time.sleep(2)
    
    print("Simulando dados de recuperação...")
    if hasattr(processor, 'notification_handler') and processor.notification_handler:
        processor.notification_handler.process_mqtt_data("LN2-00100", mqtt_data_normal)
    
    # Verificar status
    status = processor.get_notification_status()
    print("Status após simulação:", status)
    
    # Finalizar
    processor.cleanup()

if __name__ == "__main__":
    print("=== Exemplo de Uso do Sistema de Notificações ===\n")
    
    print("1. Exemplo básico:")
    exemplo_uso_basico()
    
    print("\n2. Exemplo de configuração avançada:")
    exemplo_configuracao_avancada()
    
    print("\n3. Exemplo de simulação MQTT:")
    exemplo_simulacao_mqtt()
    
    print("\n=== Configurações Disponíveis ===")
    print("""
    Configurações que podem ser ajustadas:
    
    1. Modo de operação:
       - "polling": Verifica remoções periodicamente
       - "listener": Verifica em tempo real (implementação futura)
    
    2. Timeouts e intervalos:
       - polling_interval_minutes: Intervalo do polling (padrão: 10 min)
       - connection_timeout_hours: Timeout para conexão (padrão: 1 hora)
       - max_group_delay_seconds: Delay para agrupar notificações (padrão: 30s)
    
    3. Rate limiting:
       - max_notifications_per_device_per_hour: Limite por dispositivo (padrão: 20)
    
    4. Recursos:
       - recovery_notifications_enabled: Notificações de recuperação (padrão: true)
       - connection_check_enabled: Verificar conexão via lastTX (padrão: true)
       - group_notifications_same_device: Agrupar notificações (padrão: true)
    
    5. Valores normais por campo:
       - ln2_level_status: "04"
       - ln2_angle_status: "04"
       - ln2_battery_status: "04"
       - ln2_foam_status: "08"
    
    6. Severidades por campo:
       - ln2_level_status: "high"
       - ln2_angle_status: "low"
       - ln2_battery_status: "high"
       - ln2_foam_status: "low"
       - connection: "high"
    
    Para alterar configurações, edite o arquivo 'notification_config.json'
    ou use os métodos programáticos do MessageProcessor.
    """)
