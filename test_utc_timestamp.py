#!/usr/bin/env python3
"""
Teste para verificar se os timestamps UTC estão sendo gerados corretamente.
"""

from datetime import datetime, timezone
import time

def test_utc_timestamp():
    """Testa a geração de timestamps UTC."""
    print("Testando geração de timestamps UTC...")
    
    # Método correto - datetime.now(timezone.utc)
    current_time_utc = datetime.now(timezone.utc)
    epoch_timestamp_utc = str(int(current_time_utc.timestamp()))
    
    # Método antigo (potencialmente incorreto se timezone local != UTC)
    current_time_local = datetime.now()
    epoch_timestamp_local = str(int(current_time_local.replace(tzinfo=timezone.utc).timestamp()))
    
    # Timestamp atual real para comparação
    real_utc_timestamp = str(int(time.time()))
    
    print(f"Método UTC correto: {epoch_timestamp_utc}")
    print(f"Método local->UTC: {epoch_timestamp_local}")
    print(f"time.time() real:   {real_utc_timestamp}")
    
    # Diferença em segundos
    diff_utc = abs(int(epoch_timestamp_utc) - int(real_utc_timestamp))
    diff_local = abs(int(epoch_timestamp_local) - int(real_utc_timestamp))
    
    print(f"\nDiferença UTC correto: {diff_utc} segundos")
    print(f"Diferença local->UTC:  {diff_local} segundos")
    
    # Verificar se estão próximos (dentro de 1 segundo)
    if diff_utc <= 1:
        print("✅ Método UTC correto está funcionando!")
    else:
        print("❌ Método UTC correto tem problema!")
        
    if diff_local <= 1:
        print("✅ Método local->UTC está funcionando!")
    else:
        print("❌ Método local->UTC tem problema!")
    
    # Mostrar as datas para comparação visual
    print(f"\nData UTC correta: {current_time_utc.isoformat()}")
    print(f"Data local:       {current_time_local.isoformat()}")
    print(f"Data UTC real:    {datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat()}")

if __name__ == "__main__":
    test_utc_timestamp()
