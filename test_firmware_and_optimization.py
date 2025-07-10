#!/usr/bin/env python3
"""
Teste para validar a construção da versão do firmware e otimizações do Realtime Database
"""

def test_firmware_version_construction():
    """Testa a construção da versão do firmware a partir dos campos MQTT"""
    
    print("🔍 Testando construção da versão do firmware...")
    
    # Casos de teste
    test_cases = [
        {
            "name": "Firmware versão normal",
            "input": {
                "fw_version_prefix": "00",
                "fw_version_major": "00", 
                "fw_version_minor": "00",
                "fw_version_patch": "00",
                "fw_version_build": "04"
            },
            "expected": "v0.0.0.4"
        },
        {
            "name": "Firmware com valores hex",
            "input": {
                "fw_version_prefix": "01",
                "fw_version_major": "02",
                "fw_version_minor": "0A", 
                "fw_version_patch": "FF",
                "fw_version_build": "10"
            },
            "expected": "v2.10.255.16"
        },
        {
            "name": "Firmware com campos ausentes",
            "input": {
                "fw_version_major": "01",
                "fw_version_minor": "05"
            },
            "expected": "v1.5.0.0"
        },
        {
            "name": "Firmware com valores inválidos",
            "input": {
                "fw_version_prefix": "XX",
                "fw_version_major": "01",
                "fw_version_minor": "02",
                "fw_version_patch": "03",
                "fw_version_build": "04"
            },
            "expected_fallback": True
        }
    ]
    
    for test_case in test_cases:
        print(f"\n📝 {test_case['name']}:")
        message_dict = test_case['input']
        
        # Implementar a lógica de construção da versão
        fw_prefix = message_dict.get('fw_version_prefix', '00')
        fw_major = message_dict.get('fw_version_major', '0')
        fw_minor = message_dict.get('fw_version_minor', '0')
        fw_patch = message_dict.get('fw_version_patch', '0')
        fw_build = message_dict.get('fw_version_build', '0')
        
        try:
            major = str(int(fw_major, 16)) if fw_major else '0'
            minor = str(int(fw_minor, 16)) if fw_minor else '0'
            patch = str(int(fw_patch, 16)) if fw_patch else '0'
            build = str(int(fw_build, 16)) if fw_build else '0'
            version_fw = f"v{major}.{minor}.{patch}.{build}"
            
            print(f"   Input: {message_dict}")
            print(f"   Output: {version_fw}")
            
            if 'expected' in test_case:
                if version_fw == test_case['expected']:
                    print(f"   ✅ Correto!")
                else:
                    print(f"   ❌ Esperado: {test_case['expected']}")
            else:
                print(f"   ✅ Processado sem erro")
                
        except (ValueError, TypeError) as e:
            # Fallback
            fallback_version = f"v{fw_major}.{fw_major}.{fw_minor}.{fw_patch}.{fw_build}"
            print(f"   Input: {message_dict}")
            print(f"   Erro: {e}")
            print(f"   Fallback: {fallback_version}")
            
            if test_case.get('expected_fallback'):
                print(f"   ✅ Fallback funcionando")
            else:
                print(f"   ❌ Erro inesperado")

def test_mac_formatting():
    """Testa a formatação do MAC address"""
    
    print("\n🔍 Testando formatação do MAC address...")
    
    test_cases = [
        {
            "beacon_serial": "90395E0AB284",
            "expected_mac": "90:39:5E:0A:B2:84"
        },
        {
            "beacon_serial": "AABBCCDDEEFF", 
            "expected_mac": "AA:BB:CC:DD:EE:FF"
        },
        {
            "beacon_serial": "123456789ABC",
            "expected_mac": "12:34:56:78:9A:BC"
        }
    ]
    
    for test_case in test_cases:
        beacon_serial = test_case['beacon_serial']
        expected = test_case['expected_mac']
        
        # Implementar a formatação do MAC
        if len(beacon_serial) == 12:
            formatted_mac = ':'.join([beacon_serial[i:i+2] for i in range(0, 12, 2)])
        else:
            formatted_mac = beacon_serial
        
        print(f"   Beacon Serial: {beacon_serial}")
        print(f"   MAC Formatado: {formatted_mac}")
        print(f"   Esperado: {expected}")
        print(f"   {'✅ Correto!' if formatted_mac == expected else '❌ Incorreto!'}")

def test_optimization_logic():
    """Testa a lógica de otimização de writes no Realtime Database"""
    
    print("\n🔍 Testando lógica de otimização de writes...")
    
    # Simular dados atuais no banco
    current_status = {
        'lastTX': '1752147600',
        'rssi': -65,
        'deviceConnected': True,
        'mac': '90:39:5E:0A:B2:84',
        'versionFW': 'v0.0.0.4'
    }
    
    # Simular novos dados
    test_scenarios = [
        {
            "name": "Nenhuma mudança",
            "new_data": {
                'lastTX': '1752147600',
                'rssi': -65,
                'deviceConnected': True,
                'mac': '90:39:5E:0A:B2:84',
                'versionFW': 'v0.0.0.4'
            },
            "should_update": False
        },
        {
            "name": "Apenas lastTX mudou",
            "new_data": {
                'lastTX': '1752147660',  # Mudou
                'rssi': -65,
                'deviceConnected': True,
                'mac': '90:39:5E:0A:B2:84',
                'versionFW': 'v0.0.0.4'
            },
            "should_update": True
        },
        {
            "name": "RSSI e versão mudaram",
            "new_data": {
                'lastTX': '1752147600',
                'rssi': -70,  # Mudou
                'deviceConnected': True,
                'mac': '90:39:5E:0A:B2:84',
                'versionFW': 'v0.0.0.5'  # Mudou
            },
            "should_update": True
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\n📝 {scenario['name']}:")
        new_data = scenario['new_data']
        
        # Implementar lógica de comparação
        updates_needed = {}
        for key, new_value in new_data.items():
            current_value = current_status.get(key)
            if current_value != new_value:
                updates_needed[key] = new_value
        
        has_updates = len(updates_needed) > 0
        
        print(f"   Dados atuais: {current_status}")
        print(f"   Novos dados: {new_data}")
        print(f"   Updates necessários: {updates_needed}")
        print(f"   Deve atualizar: {has_updates}")
        print(f"   {'✅ Correto!' if has_updates == scenario['should_update'] else '❌ Incorreto!'}")

if __name__ == "__main__":
    test_firmware_version_construction()
    test_mac_formatting()
    test_optimization_logic()
