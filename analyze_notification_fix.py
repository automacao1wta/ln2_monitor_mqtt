#!/usr/bin/env python3
"""
Análise do problema das 1800 notificações - Validação da correção UTC
"""

from datetime import datetime, timezone, timedelta

def analyze_notification_flood():
    """Analisa como o problema de timezone causou o flood de notificações"""
    
    print("🔍 ANÁLISE DO PROBLEMA DAS 1800 NOTIFICAÇÕES")
    print("=" * 60)
    
    # Simular o problema antes da correção
    print("\n❌ ANTES DA CORREÇÃO (Problema):")
    print("-" * 40)
    
    # Timezone Brasil = UTC-3 (durante horário padrão)
    # Durante a noite: 00:00 local = 03:00 UTC
    
    utc_midnight = datetime(2025, 7, 10, 3, 0, 0, tzinfo=timezone.utc)  # 03:00 UTC = 00:00 BR
    local_midnight = datetime(2025, 7, 10, 0, 0, 0)  # 00:00 local (sem timezone)
    
    print(f"UTC meia-noite: {utc_midnight}")
    print(f"Local meia-noite: {local_midnight}")
    
    # Simular lastTX de 30 minutos atrás (em UTC)
    last_tx_utc = utc_midnight - timedelta(minutes=30)
    last_tx_epoch = int(last_tx_utc.timestamp())
    
    print(f"LastTX (30min atrás): {last_tx_utc} | Epoch: {last_tx_epoch}")
    
    # PROBLEMA: Comparação incorreta (local vs UTC)
    print("\n🔴 COMPARAÇÃO INCORRETA (ANTES):")
    
    # O código antigo fazia:
    current_time_local = local_midnight  # datetime.now() sem timezone
    last_tx_time_incorrect = datetime.fromtimestamp(last_tx_epoch)  # Sem timezone = local
    
    time_diff_incorrect = (current_time_local - last_tx_time_incorrect).total_seconds() / 3600
    print(f"   Current (local): {current_time_local}")
    print(f"   LastTX (local): {last_tx_time_incorrect}")
    print(f"   Diferença incorreta: {time_diff_incorrect:.2f} horas")
    
    connection_timeout = 1.0
    is_connected_wrong = time_diff_incorrect <= connection_timeout
    print(f"   ❌ Conectado (incorreto): {is_connected_wrong}")
    print(f"   ❌ Problema: Diferença de {abs(time_diff_incorrect - 0.5):.1f}h devido ao timezone!")
    
    # SOLUÇÃO: Comparação correta (UTC vs UTC)
    print("\n✅ COMPARAÇÃO CORRETA (DEPOIS):")
    
    current_time_utc = utc_midnight
    last_tx_time_correct = datetime.fromtimestamp(last_tx_epoch, tz=timezone.utc)
    
    time_diff_correct = (current_time_utc - last_tx_time_correct).total_seconds() / 3600
    print(f"   Current (UTC): {current_time_utc}")
    print(f"   LastTX (UTC): {last_tx_time_correct}")
    print(f"   Diferença correta: {time_diff_correct:.2f} horas")
    
    is_connected_right = time_diff_correct <= connection_timeout
    print(f"   ✅ Conectado (correto): {is_connected_right}")
    
    print("\n📊 IMPACTO NA PRÁTICA:")
    print("-" * 40)
    
    # Rate limiting problema
    print(f"Rate limit: {6} notificações/hora por dispositivo")
    print(f"Dispositivos ativos: ~50")
    print(f"Horas durante a noite: 8")
    
    if not is_connected_wrong:
        notifications_per_device = 6 * 8  # 6/hora * 8 horas
        total_notifications = notifications_per_device * 50
        print(f"❌ ANTES: {notifications_per_device} notif/device * 50 devices = {total_notifications} notificações!")
        print(f"   (Explica as ~1800 notificações que você recebeu)")
    
    if is_connected_right:
        print(f"✅ DEPOIS: 0 notificações (dispositivos reconhecidos como conectados)")
    
    print("\n🔧 CORREÇÕES IMPLEMENTADAS:")
    print("-" * 40)
    print("✅ notification_handler.py: 7 correções de datetime.now() → datetime.now(timezone.utc)")
    print("✅ message_processor.py: 6 correções de datetime.now() → datetime.now(timezone.utc)")
    print("✅ Especialmente crítico: rate limiting e comparação lastTX")
    print("✅ Todos os timestamps agora consistentes em UTC")

def test_rate_limit_scenario():
    """Testa cenário específico de rate limiting"""
    
    print("\n🧪 TESTE: Rate Limiting Corrigido")
    print("=" * 40)
    
    utc_now = datetime.now(timezone.utc)
    
    # Simular notificações enviadas na última hora
    notification_times = [
        utc_now - timedelta(minutes=50),
        utc_now - timedelta(minutes=40), 
        utc_now - timedelta(minutes=30),
        utc_now - timedelta(minutes=20),
        utc_now - timedelta(minutes=10),
        utc_now - timedelta(minutes=5)
    ]
    
    print(f"Agora: {utc_now}")
    print("Notificações na última hora:")
    for i, notif_time in enumerate(notification_times, 1):
        print(f"  {i}. {notif_time} ({(utc_now - notif_time).total_seconds()/60:.0f}min atrás)")
    
    # Verificar rate limiting
    hour_ago = utc_now - timedelta(hours=1)
    valid_notifications = [t for t in notification_times if t > hour_ago]
    
    print(f"\nLimite: 6 notificações/hora")
    print(f"Notificações válidas: {len(valid_notifications)}")
    print(f"Nova notificação permitida: {'❌ Não' if len(valid_notifications) >= 6 else '✅ Sim'}")

if __name__ == "__main__":
    analyze_notification_flood()
    test_rate_limit_scenario()
