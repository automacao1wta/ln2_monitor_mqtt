#!/usr/bin/env python3
"""
Teste para validar as atualizações do Realtime Database
- Versão do firmware (versionFW)
- Porcentagem da bateria (pBat) com tratamento hex para int
- Nível de LN2 (LN2Level) com valor completo
- Tampa (tankLid) com valor completo
- MAC address formatado
- Otimização de writes
"""

import sys
import os
from datetime import datetime, timezone

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_firmware_version():
    """Testa construção da versão do firmware"""
    print("🧪 Teste 1: Versão do Firmware")
    print("-" * 40)
    
    test_cases = [
        {
            "fw_version_prefix": "00",
            "fw_version_major": "00", 
            "fw_version_minor": "00",
            "fw_version_patch": "01",
            "fw_version_build": "04",
            "expected": "v0.0.1.4"
        },
        {
            "fw_version_prefix": "FF",
            "fw_version_major": "0A", 
            "fw_version_minor": "0F",
            "fw_version_patch": "10",
            "fw_version_build": "20",
            "expected": "v10.15.16.32"
        },
        {
            "fw_version_prefix": None,
            "fw_version_major": None, 
            "fw_version_minor": None,
            "fw_version_patch": None,
            "fw_version_build": None,
            "expected": "v0.0.0.0"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"   Caso {i}:")
        print(f"     Input: prefix={case['fw_version_prefix']}, major={case['fw_version_major']}, minor={case['fw_version_minor']}, patch={case['fw_version_patch']}, build={case['fw_version_build']}")
        
        # Simular lógica da função
        fw_prefix = case.get('fw_version_prefix', '00')
        fw_major = case.get('fw_version_major', '0') 
        fw_minor = case.get('fw_version_minor', '0')
        fw_patch = case.get('fw_version_patch', '0')
        fw_build = case.get('fw_version_build', '0')
        
        try:
            major = str(int(fw_major, 16)) if fw_major else '0'
            minor = str(int(fw_minor, 16)) if fw_minor else '0'
            patch = str(int(fw_patch, 16)) if fw_patch else '0'
            build = str(int(fw_build, 16)) if fw_build else '0'
            version_fw = f"v{major}.{minor}.{patch}.{build}"
            
            result = "✅" if version_fw == case['expected'] else "❌"
            print(f"     Output: {version_fw}")
            print(f"     Expected: {case['expected']}")
            print(f"     Result: {result}")
            
        except Exception as e:
            print(f"     ❌ Erro: {e}")
        
        print()

def test_battery_percentage():
    """Testa conversão da porcentagem da bateria"""
    print("🧪 Teste 2: Porcentagem da Bateria (pBat)")
    print("-" * 40)
    
    test_cases = [
        {"hex": "65", "expected": 101, "clamped": 100},  # 101 > 100, deveria virar 100
        {"hex": "64", "expected": 100, "clamped": 100},  # 100 = 100
        {"hex": "32", "expected": 50, "clamped": 50},    # 50 normal
        {"hex": "00", "expected": 0, "clamped": 0},      # 0 normal
        {"hex": "FF", "expected": 255, "clamped": 100},  # 255 > 100, deveria virar 100
        {"hex": "-5", "expected": -5, "clamped": 0},     # Negativo deveria virar 0
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"   Caso {i}:")
        print(f"     Input hex: '{case['hex']}'")
        
        try:
            # Simular lógica da função
            batt_percent_int = int(case['hex'], 16)
            batt_percent_clamped = max(0, min(100, batt_percent_int))
            
            print(f"     Converted: {batt_percent_int}")
            print(f"     Clamped: {batt_percent_clamped}")
            print(f"     Expected clamped: {case['clamped']}")
            
            result = "✅" if batt_percent_clamped == case['clamped'] else "❌"
            print(f"     Result: {result}")
            
        except Exception as e:
            print(f"     ❌ Erro na conversão: {e}")
        
        print()

def test_status_fields():
    """Testa campos de status com valores completos"""
    print("🧪 Teste 3: Campos de Status")
    print("-" * 40)
    
    test_cases = [
        {
            "ln2_level_status": "10 - Low",
            "ln2_angle_status": "3 - Tampa aberto",
            "expected_level": "10 - Low",
            "expected_lid": "3 - Tampa aberto",
            "expected_cover": True
        },
        {
            "ln2_level_status": "4 - Good",
            "ln2_angle_status": "2 - Tampa fechada",
            "expected_level": "4 - Good", 
            "expected_lid": "2 - Tampa fechada",
            "expected_cover": False
        },
        {
            "ln2_level_status": "6 - Very High",
            "ln2_angle_status": "5 - Unknown",
            "expected_level": "6 - Very High",
            "expected_lid": "5 - Unknown",
            "expected_cover": None  # Status desconhecido
        }
    ]
    
    def extract_status_code(status_str):
        """Função auxiliar para extrair código de status"""
        if isinstance(status_str, str) and " - " in status_str:
            try:
                return int(status_str.split(" - ")[0])
            except (ValueError, IndexError):
                return None
        elif isinstance(status_str, str):
            try:
                return int(status_str)
            except ValueError:
                return None
        return status_str
    
    for i, case in enumerate(test_cases, 1):
        print(f"   Caso {i}:")
        print(f"     LN2 Level: '{case['ln2_level_status']}'")
        print(f"     Angle Status: '{case['ln2_angle_status']}'")
        
        # Simular lógica da função
        ln2_level = case['ln2_level_status']
        tank_lid = case['ln2_angle_status']
        
        # Cover boolean baseado no código de status
        status_code = extract_status_code(case['ln2_angle_status'])
        if status_code == 2:
            cover = False
        elif status_code == 3:
            cover = True
        else:
            cover = None
        
        print(f"     Resultado LN2Level: '{ln2_level}'")
        print(f"     Resultado tankLid: '{tank_lid}'")
        print(f"     Resultado cover: {cover}")
        
        level_ok = ln2_level == case['expected_level']
        lid_ok = tank_lid == case['expected_lid']
        cover_ok = cover == case['expected_cover']
        
        print(f"     ✅ LN2Level: {'✅' if level_ok else '❌'}")
        print(f"     ✅ tankLid: {'✅' if lid_ok else '❌'}")
        print(f"     ✅ cover: {'✅' if cover_ok else '❌'}")
        print()

def test_mac_formatting():
    """Testa formatação do MAC address"""
    print("🧪 Teste 4: Formatação MAC Address")
    print("-" * 40)
    
    test_cases = [
        {"beacon_serial": "90395E0AB284", "expected": "90:39:5E:0A:B2:84"},
        {"beacon_serial": "CC5CC7447C01", "expected": "CC:5C:C7:44:7C:01"},
        {"beacon_serial": "AABBCCDDEEFF", "expected": "AA:BB:CC:DD:EE:FF"},
    ]
    
    def format_mac_address(beacon_serial):
        """Função auxiliar para formatar MAC"""
        if len(beacon_serial) == 12:
            return ':'.join([beacon_serial[i:i+2] for i in range(0, 12, 2)])
        return beacon_serial
    
    for i, case in enumerate(test_cases, 1):
        print(f"   Caso {i}:")
        print(f"     Beacon Serial: '{case['beacon_serial']}'")
        
        mac_formatted = format_mac_address(case['beacon_serial'])
        
        print(f"     MAC Formatted: '{mac_formatted}'")
        print(f"     Expected: '{case['expected']}'")
        
        result = "✅" if mac_formatted == case['expected'] else "❌"
        print(f"     Result: {result}")
        print()

def test_write_optimization():
    """Testa otimização de writes (comparação de valores)"""
    print("🧪 Teste 5: Otimização de Writes")
    print("-" * 40)
    
    # Simular dados atuais no Realtime DB
    current_realtime = {
        'tempPT100': 25.5,
        'pBat': 80,
        'LN2Level': "4 - Good",
        'tankLid': "2 - Tampa fechada"
    }
    
    # Simular novos dados
    new_realtime = {
        'tempPT100': 25.5,      # Mesmo valor - não deve escrever
        'pBat': 85,             # Valor diferente - deve escrever
        'LN2Level': "4 - Good", # Mesmo valor - não deve escrever
        'tankLid': "3 - Tampa aberto"  # Valor diferente - deve escrever
    }
    
    print("   Dados atuais:", current_realtime)
    print("   Novos dados:", new_realtime)
    
    # Simular lógica de otimização
    updates = {}
    for key, new_value in new_realtime.items():
        current_value = current_realtime.get(key)
        if current_value != new_value:
            updates[key] = new_value
    
    print("   Updates necessários:", updates)
    
    expected_updates = {'pBat': 85, 'tankLid': '3 - Tampa aberto'}
    result = "✅" if updates == expected_updates else "❌"
    print(f"   Expected: {expected_updates}")
    print(f"   Result: {result}")

if __name__ == "__main__":
    print("🔍 TESTES DE ATUALIZAÇÃO DO REALTIME DATABASE")
    print("=" * 60)
    print()
    
    test_firmware_version()
    test_battery_percentage() 
    test_status_fields()
    test_mac_formatting()
    test_write_optimization()
    
    print("✅ Todos os testes concluídos!")
