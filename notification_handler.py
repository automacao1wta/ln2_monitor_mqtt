"""
Notification Handler para Sistema LN2 Monitor
Gerencia notificações inteligentes baseadas em mudanças de estado dos dispositivos.

Características:
- Toggle entre Listener (tempo real) e Polling (periódico)
- Configurações ajustáveis via arquivo
- Agrupamento de notificações por dispositivo
- Detecção de conexão via lastTX
- Notificações de recuperação
- Rate limiting de segurança
"""

import json
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import threading
import time
from logger_config import setup_logger


class NotificationMode(Enum):
    LISTENER = "listener"
    POLLING = "polling"


class NotificationSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class NotificationConfig:
    """Configurações do sistema de notificações"""
    
    # Modo de operação
    mode: NotificationMode = NotificationMode.POLLING
    polling_interval_minutes: int = 10
    
    # Conexão/LastTX
    connection_timeout_hours: float = 1.0
    connection_check_enabled: bool = True
    
    # Rate limiting de segurança
    max_notifications_per_device_per_hour: int = 20
    
    # Notificações de recuperação
    recovery_notifications_enabled: bool = True
    
    # Valores normais por campo
    normal_status_values: Dict[str, str] = None
    
    # Severidades por campo
    field_severities: Dict[str, NotificationSeverity] = None
    
    # Agrupamento
    group_notifications_same_device: bool = True
    max_group_delay_seconds: int = 30  # Tempo para agrupar notificações do mesmo device
    
    def __post_init__(self):
        if self.normal_status_values is None:
            self.normal_status_values = {
                "ln2_level_status": "04",     # Valor decimal normalizado (4 = Good)
                "ln2_angle_status": "04",     # Valor decimal normalizado (4 = Good)  
                "ln2_battery_status": "04",   # Valor decimal normalizado (4 = Good)
                "ln2_foam_status": "04",      # Valor decimal normalizado (4 = Good)
            }
        
        if self.field_severities is None:
            self.field_severities = {
                "ln2_level_status": NotificationSeverity.HIGH,
                "ln2_angle_status": NotificationSeverity.LOW,
                "ln2_battery_status": NotificationSeverity.HIGH,
                "ln2_foam_status": NotificationSeverity.LOW,
                "connection": NotificationSeverity.HIGH,  # Para lastTX
            }


@dataclass
class DeviceStatus:
    """Status atual de um dispositivo"""
    device_id: str
    last_status_values: Dict[str, str]  # field_name -> last_value
    last_notification_timestamps: Dict[str, datetime]  # notification_type -> timestamp
    last_seen: datetime
    pending_notifications: List[Dict[str, Any]]  # Notificações pendentes para agrupamento


class NotificationHandler:
    """
    Gerenciador de notificações inteligente para o sistema LN2 Monitor
    """
    
    def __init__(self, config: NotificationConfig = None, realtime_db=None, message_processor=None):
        self.config = config or NotificationConfig()
        self.realtime_db = realtime_db
        self.message_processor = message_processor
        self.logger = setup_logger(__name__)
        
        # Cache de estados dos dispositivos
        self.device_cache: Dict[str, DeviceStatus] = {}
        
        # Controle de threads
        self._stop_event = threading.Event()
        self._polling_thread = None
        self._listener_thread = None
        self._grouping_thread = None
        
        # Cache de notificações ativas (para detecção de remoção)
        self.active_notifications_cache: Dict[str, Dict[str, Any]] = {}  # device_id -> {notification_id: data}
        
        # Cargar configurações do arquivo se existir
        self._load_config_from_file()
        
        self.logger.info(f"NotificationHandler inicializado em modo {self.config.mode.value}")
        
    def _load_config_from_file(self):
        """Carrega configurações do arquivo notification_config.json se existir"""
        config_file = "notification_config.json"
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # Atualizar configurações
                if 'mode' in config_data:
                    self.config.mode = NotificationMode(config_data['mode'])
                if 'polling_interval_minutes' in config_data:
                    self.config.polling_interval_minutes = config_data['polling_interval_minutes']
                if 'connection_timeout_hours' in config_data:
                    self.config.connection_timeout_hours = config_data['connection_timeout_hours']
                if 'connection_check_enabled' in config_data:
                    self.config.connection_check_enabled = config_data['connection_check_enabled']
                if 'max_notifications_per_device_per_hour' in config_data:
                    self.config.max_notifications_per_device_per_hour = config_data['max_notifications_per_device_per_hour']
                if 'recovery_notifications_enabled' in config_data:
                    self.config.recovery_notifications_enabled = config_data['recovery_notifications_enabled']
                if 'group_notifications_same_device' in config_data:
                    self.config.group_notifications_same_device = config_data['group_notifications_same_device']
                if 'max_group_delay_seconds' in config_data:
                    self.config.max_group_delay_seconds = config_data['max_group_delay_seconds']
                if 'normal_status_values' in config_data:
                    self.config.normal_status_values.update(config_data['normal_status_values'])
                if 'field_severities' in config_data:
                    severities = {}
                    for field, sev in config_data['field_severities'].items():
                        severities[field] = NotificationSeverity(sev)
                    self.config.field_severities.update(severities)
                
                self.logger.info(f"Configurations loaded from {config_file}")
                self.logger.info(f"Rate limit configured: {self.config.max_notifications_per_device_per_hour} notifications/hour")
        except Exception as e:
            self.logger.error(f"Error loading configurations: {e}")
    
    def save_config_to_file(self):
        """Salva configurações atuais no arquivo"""
        config_file = "notification_config.json"
        try:
            config_data = {
                'mode': self.config.mode.value,
                'polling_interval_minutes': self.config.polling_interval_minutes,
                'connection_timeout_hours': self.config.connection_timeout_hours,
                'connection_check_enabled': self.config.connection_check_enabled,
                'max_notifications_per_device_per_hour': self.config.max_notifications_per_device_per_hour,
                'recovery_notifications_enabled': self.config.recovery_notifications_enabled,
                'normal_status_values': self.config.normal_status_values,
                'field_severities': {k: v.value for k, v in self.config.field_severities.items()},
                'group_notifications_same_device': self.config.group_notifications_same_device,
                'max_group_delay_seconds': self.config.max_group_delay_seconds,
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Configurations saved to {config_file}")
        except Exception as e:
            self.logger.error(f"Error saving configurations: {e}")
    
    def start(self):
        """Inicia o handler de notificações"""
        if not self.realtime_db:
            self.logger.error("Realtime Database not configured")
            return
        
        # Iniciar thread de agrupamento
        self._grouping_thread = threading.Thread(target=self._grouping_worker, daemon=True)
        self._grouping_thread.start()
        
        if self.config.mode == NotificationMode.POLLING:
            self._start_polling()
        else:
            self._start_listener()
        
        self.logger.info("NotificationHandler iniciado")
    
    def stop(self):
        """Para o handler de notificações"""
        self._stop_event.set()
        if self._polling_thread:
            self._polling_thread.join(timeout=5)
        if self._listener_thread:
            self._listener_thread.join(timeout=5)
        if self._grouping_thread:
            self._grouping_thread.join(timeout=5)
        
        self.logger.info("NotificationHandler parado")
    
    def _start_polling(self):
        """Inicia modo polling"""
        self._polling_thread = threading.Thread(target=self._polling_worker, daemon=True)
        self._polling_thread.start()
        self.logger.info(f"Polling iniciado (intervalo: {self.config.polling_interval_minutes} min)")
    
    def _start_listener(self):
        """Inicia modo listener"""
        self._listener_thread = threading.Thread(target=self._listener_worker, daemon=True)
        self._listener_thread.start()
        self.logger.info("Listener iniciado")
    
    def _polling_worker(self):
        """Worker para modo polling"""
        while not self._stop_event.is_set():
            try:
                self._check_notification_removals()
                time.sleep(self.config.polling_interval_minutes * 60)
            except Exception as e:
                self.logger.error(f"Error in polling worker: {e}")
                time.sleep(30)  # Espera 30s antes de tentar novamente
    
    def _listener_worker(self):
        """Worker para modo listener"""
        # TODO: Implementar Firebase listener
        # Por enquanto, fazer polling mais frequente como fallback
        self.logger.warning("Listener mode not implemented yet, using fast polling as fallback")
        while not self._stop_event.is_set():
            try:
                self._check_notification_removals()
                time.sleep(60)  # Check a cada minuto no modo listener
            except Exception as e:
                self.logger.error(f"Error in listener worker: {e}")
                time.sleep(30)
    
    def _grouping_worker(self):
        """Worker para agrupar notificações pendentes"""
        while not self._stop_event.is_set():
            try:
                current_time = datetime.now(timezone.utc)
                for device_id, device_status in self.device_cache.items():
                    if device_status.pending_notifications:
                        # Verificar se há notificações pendentes antigas o suficiente para enviar
                        oldest_notification = min(device_status.pending_notifications, 
                                                key=lambda x: x.get('created_at', current_time))
                        time_since_oldest = (current_time - oldest_notification.get('created_at', current_time)).total_seconds()
                        
                        if time_since_oldest >= self.config.max_group_delay_seconds:
                            self._send_grouped_notifications(device_id)
                
                time.sleep(5)  # Check a cada 5 segundos
            except Exception as e:
                self.logger.error(f"Error in grouping worker: {e}")
                time.sleep(10)
    
    def process_mqtt_data(self, equipment_id: str, message_dict: Dict[str, Any]):
        """
        Processa dados MQTT e gera notificações se necessário
        
        Args:
            equipment_id: ID do equipamento (ex: LN2-00100)
            message_dict: Dados do MQTT parseados
        """
        if not equipment_id or not message_dict:
            return
        
        # Garantir que temos o device no cache
        if equipment_id not in self.device_cache:
            self.device_cache[equipment_id] = DeviceStatus(
                device_id=equipment_id,
                last_status_values={},
                last_notification_timestamps={},
                last_seen=datetime.now(timezone.utc),
                pending_notifications=[]
            )
        
        device_status = self.device_cache[equipment_id]
        device_status.last_seen = datetime.now(timezone.utc)
        
        notifications_to_add = []
        
        # 1. Verificar mudanças de status dos campos monitorados
        for field_name, normal_value in self.config.normal_status_values.items():
            current_value = message_dict.get(field_name)
            if current_value is None:
                continue
            
            # Normalizar valores para comparação (extrair código numérico)
            normalized_current = self._normalize_status_value(current_value)
            normalized_normal = self._normalize_status_value(normal_value)
            
            last_value = device_status.last_status_values.get(field_name)
            normalized_last = self._normalize_status_value(last_value) if last_value else None
            
            # Detectar mudança de estado
            if normalized_last != normalized_current:
                notification = self._create_status_notification(
                    equipment_id, field_name, normalized_current, normalized_normal, normalized_last
                )
                if notification:
                    notifications_to_add.append(notification)
                
                # Atualizar cache com valor normalizado
                device_status.last_status_values[field_name] = normalized_current
        
        # 2. Verificar conexão (lastTX) se habilitado
        if self.config.connection_check_enabled:
            connection_notification = self._check_connection_status(equipment_id, message_dict)
            if connection_notification:
                notifications_to_add.append(connection_notification)
        
        # 3. Adicionar notificações à lista de agrupamento ou enviar imediatamente
        if notifications_to_add:
            if self.config.group_notifications_same_device and len(notifications_to_add) > 1:
                # Adicionar timestamp de criação
                for notif in notifications_to_add:
                    notif['created_at'] = datetime.now(timezone.utc)
                device_status.pending_notifications.extend(notifications_to_add)
            else:
                # Enviar imediatamente
                for notification in notifications_to_add:
                    self._send_notification(equipment_id, notification)
    
    def _create_status_notification(self, equipment_id: str, field_name: str, current_value: str, 
                                  normal_value: str, last_value: str) -> Optional[Dict[str, Any]]:
        """Cria notificação baseada em mudança de status"""
        
        # Verificar rate limiting ANTES de qualquer processamento
        if not self._check_rate_limit(equipment_id, field_name):
            self.logger.debug(f"Rate limit blocked notification for {equipment_id} ({field_name})")
            return None
        
        # Normalizar valores para comparação
        normalized_current = self._normalize_status_value(current_value)
        normalized_normal = self._normalize_status_value(normal_value)
        normalized_last = self._normalize_status_value(last_value) if last_value else None
        
        current_is_normal = normalized_current == normalized_normal
        last_was_normal = normalized_last == normalized_normal if normalized_last else True
        
        # Casos para notificação:
        # 1. Normal -> Anormal: Alerta
        # 2. Anormal -> Normal: Recuperação (se habilitado)
        # 3. Anormal -> Anormal (diferente): Mudança de problema
        
        notification_type = None
        message = None
        
        if last_was_normal and not current_is_normal:
            # Normal -> Anormal: ALERTA
            notification_type = f"{field_name}_alert"
            message = self._get_status_alert_message(field_name, normalized_current)
        
        elif not last_was_normal and current_is_normal and self.config.recovery_notifications_enabled:
            # Anormal -> Normal: RECUPERAÇÃO
            notification_type = f"{field_name}_recovery"
            message = self._get_status_recovery_message(field_name)
        
        elif not last_was_normal and not current_is_normal and normalized_last and normalized_current != normalized_last:
            # Anormal -> Anormal (diferente): MUDANÇA
            notification_type = f"{field_name}_change"
            message = self._get_status_change_message(field_name, normalized_current, normalized_last)
        
        if not notification_type or not message:
            return None
        
        severity = self.config.field_severities.get(field_name, NotificationSeverity.MEDIUM)
        
        return {
            "type": notification_type,
            "field_name": field_name,
            "message": message,
            "deviceId": equipment_id,
            "current_value": normalized_current,
            "previous_value": normalized_last,
            "severity": severity.value,
            "timestamp_emitted": datetime.now(timezone.utc).isoformat(),
            "status": "active",
            "view_status": "unread"
        }
    
    def _check_connection_status(self, equipment_id: str, message_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Verifica status de conexão baseado em lastTX"""
        
        # Obter lastTX do Realtime Database (não dos dados MQTT)
        try:
            device_data = self.realtime_db.child(equipment_id).child('STATUS').get()
            if not device_data or 'lastTX' not in device_data:
                return None
            
            last_tx_epoch = int(device_data['lastTX'])
            last_tx_time = datetime.fromtimestamp(last_tx_epoch, tz=timezone.utc)
            current_time = datetime.now(timezone.utc)
            
            time_diff_hours = (current_time - last_tx_time).total_seconds() / 3600
            
            device_status = self.device_cache[equipment_id]
            was_disconnected = device_status.last_status_values.get('connection_status') == 'disconnected'
            
            if time_diff_hours > self.config.connection_timeout_hours:
                # Dispositivo desconectado
                if not was_disconnected:  # Só notificar na primeira vez
                    device_status.last_status_values['connection_status'] = 'disconnected'
                    
                    if self._check_rate_limit(equipment_id, 'connection'):                    return {
                        "type": "connection_lost",
                        "field_name": "connection",
                        "message": f"No communication with device for {time_diff_hours:.1f} hours",
                        "deviceId": equipment_id,
                        "last_seen": last_tx_time.isoformat(),
                        "hours_offline": round(time_diff_hours, 1),
                        "severity": self.config.field_severities.get('connection', NotificationSeverity.HIGH).value,
                        "timestamp_emitted": current_time.isoformat(),
                        "status": "active",
                        "view_status": "unread"
                    }
            else:
                # Dispositivo conectado
                if was_disconnected and self.config.recovery_notifications_enabled:
                    device_status.last_status_values['connection_status'] = 'connected'
                    
                    return {
                        "type": "connection_recovered",
                        "field_name": "connection",
                        "message": "Communication with device has been restored",
                        "deviceId": equipment_id,
                        "severity": self.config.field_severities.get('connection', NotificationSeverity.HIGH).value,
                        "timestamp_emitted": current_time.isoformat(),
                        "status": "active",
                        "view_status": "unread"
                    }
        
        except Exception as e:
            self.logger.error(f"Error checking connection for {equipment_id}: {e}")
        
        return None
    
    def _get_status_alert_message(self, field_name: str, value: str) -> str:
        """Gera mensagem de alerta baseada no campo e valor"""
        
        # Obter descrição do status usando a função do message_processor
        if self.message_processor and hasattr(self.message_processor, '_get_status_comment'):
            try:
                # Converter valor normalizado (string) para int
                status_comment = self.message_processor._get_status_comment(int(value))
                description = status_comment.split(" - ", 1)[-1]  # Pegar apenas a descrição
            except:
                description = f"Status {value}"
        else:
            description = f"Status {value}"
        
        field_messages = {
            "ln2_level_status": f"LN2 Level: {description}",
            "ln2_angle_status": f"Device angle: {description}",
            "ln2_battery_status": f"Battery status: {description}",
            "ln2_foam_status": f"Foam status: {description}",
        }
        
        return field_messages.get(field_name, f"{field_name}: {description}")
    
    def _get_status_recovery_message(self, field_name: str) -> str:
        """Gera mensagem de recuperação"""
        field_messages = {
            "ln2_level_status": "LN2 level normalized",
            "ln2_angle_status": "Device angle normalized",
            "ln2_battery_status": "Battery status normalized",
            "ln2_foam_status": "Foam status normalized",
        }
        
        return field_messages.get(field_name, f"{field_name} normalizado")
    
    def _get_status_change_message(self, field_name: str, current_value: str, previous_value: str) -> str:
        """Gera mensagem de mudança de status"""
        
        # Obter descrições
        current_desc = previous_desc = ""
        if self.message_processor and hasattr(self.message_processor, '_get_status_comment'):
            try:
                current_desc = self.message_processor._get_status_comment(int(current_value)).split(" - ", 1)[-1]
                previous_desc = self.message_processor._get_status_comment(int(previous_value)).split(" - ", 1)[-1]
            except Exception as e:
                self.logger.debug(f"Error getting descriptions: {e}")
                current_desc = f"Status {current_value}"
                previous_desc = f"Status {previous_value}"
        
        field_messages = {
            "ln2_level_status": f"LN2 level changed: {previous_desc} → {current_desc}",
            "ln2_angle_status": f"Angle changed: {previous_desc} → {current_desc}",
            "ln2_battery_status": f"Battery changed: {previous_desc} → {current_desc}",
            "ln2_foam_status": f"Foam changed: {previous_desc} → {current_desc}",
        }
        
        return field_messages.get(field_name, f"{field_name}: {previous_desc} → {current_desc}")
    
    def _check_rate_limit(self, equipment_id: str, notification_type: str) -> bool:
        """Verifica se pode enviar notificação (rate limiting)"""
        device_status = self.device_cache.get(equipment_id)
        if not device_status:
            return True
        
        current_time = datetime.now(timezone.utc)
        hour_ago = current_time - timedelta(hours=1)
        
        # Contar TODAS as notificações na última hora (independente do tipo)
        notifications_last_hour = sum(
            1 for timestamp in device_status.last_notification_timestamps.values()
            if timestamp > hour_ago
        )
        
        if notifications_last_hour >= self.config.max_notifications_per_device_per_hour:
            self.logger.warning(f"Rate limit reached for {equipment_id}: {notifications_last_hour} notifications in the last hour (limit: {self.config.max_notifications_per_device_per_hour})")
            return False
        
        return True
    
    def _send_grouped_notifications(self, equipment_id: str):
        """Envia notificações agrupadas para um dispositivo"""
        device_status = self.device_cache.get(equipment_id)
        if not device_status or not device_status.pending_notifications:
            return
        
        notifications = device_status.pending_notifications.copy()
        device_status.pending_notifications.clear()
        
        if len(notifications) == 1:
            # Apenas uma notificação, enviar normalmente
            self._send_notification(equipment_id, notifications[0])
        else:
            # Agrupar múltiplas notificações
            grouped_notification = self._create_grouped_notification(equipment_id, notifications)
            self._send_notification(equipment_id, grouped_notification)
    
    def _create_grouped_notification(self, equipment_id: str, notifications: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Cria uma notificação agrupada"""
        
        # Determinar severidade mais alta
        severities = [NotificationSeverity(n.get('severity', 'medium')) for n in notifications]
        max_severity = max(severities, key=lambda x: ['low', 'medium', 'high'].index(x.value))
        
        # Criar mensagem agrupada
        messages = [n['message'] for n in notifications]
        grouped_message = f"Multiple alerts: {'; '.join(messages)}"
        
        # Criar tipos agrupados
        types = [n['type'] for n in notifications]
        grouped_type = f"multiple_alerts"
        
        return {
            "type": grouped_type,
            "field_name": "multiple",
            "message": grouped_message,
            "deviceId": equipment_id,
            "alert_count": len(notifications),
            "alert_types": types,
            "individual_notifications": notifications,
            "severity": max_severity.value,
            "timestamp_emitted": datetime.now(timezone.utc).isoformat(),
            "status": "active",
            "view_status": "unread"
        }
    
    def _send_notification(self, equipment_id: str, notification: Dict[str, Any]):
        """Envia uma notificação para o Realtime Database"""
        
        if not self.realtime_db:
            self.logger.error("Realtime Database not available")
            return
        
        try:
            # Gerar ID único para a notificação
            notification_id = f"{notification['type']}_{uuid.uuid4().hex[:8]}"
            
            # Atualizar timestamps de rate limiting
            device_status = self.device_cache.get(equipment_id)
            if device_status:
                device_status.last_notification_timestamps[notification['type']] = datetime.now(timezone.utc)
            
            # Preparar notificação para envio (converter TODOS os valores datetime recursivamente)
            notification_to_send = self._serialize_notification_data(notification)
            
            # Enviar para o Realtime Database
            notification_path = f"{equipment_id}/NOTIFICATIONS/{notification_id}"
            self.realtime_db.child(notification_path).set(notification_to_send)
            
            # Atualizar cache de notificações ativas
            if equipment_id not in self.active_notifications_cache:
                self.active_notifications_cache[equipment_id] = {}
            self.active_notifications_cache[equipment_id][notification_id] = notification_to_send
            
            self.logger.info(f"Notificação enviada para {equipment_id}: {notification['type']} - {notification['message']}")
            
        except Exception as e:
            self.logger.error(f"Error sending notification for {equipment_id}: {e}")
    
    def _serialize_notification_data(self, data: Any) -> Any:
        """Serializa recursivamente dados de notificação, convertendo datetime para strings"""
        if isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, dict):
            result = {}
            for key, value in data.items():
                # Pular campos internos de controle
                if key in ['created_at']:
                    continue
                result[key] = self._serialize_notification_data(value)
            return result
        elif isinstance(data, list):
            return [self._serialize_notification_data(item) for item in data]
        else:
            return data
    
    def _check_notification_removals(self):
        """Checks if notifications were removed by user (polling/listener)"""
        
        if not self.realtime_db:
            return
        
        try:
            for equipment_id in self.active_notifications_cache.keys():
                try:
                    # Buscar notificações atuais no Realtime Database
                    current_notifications = self.realtime_db.child(f"{equipment_id}/NOTIFICATIONS").get() or {}
                    current_ids = set(current_notifications.keys())
                    cached_ids = set(self.active_notifications_cache[equipment_id].keys())
                    
                    # Identificar notificações removidas
                    removed_ids = cached_ids - current_ids
                    
                    for removed_id in removed_ids:
                        removed_notification = self.active_notifications_cache[equipment_id].pop(removed_id, None)
                        if removed_notification:
                            self.logger.info(f"Notification removed by user: {equipment_id}/{removed_id}")
                            # Here can implement additional logic when notification is removed
                
                except Exception as e:
                    self.logger.error(f"Error checking removals for {equipment_id}: {e}")
        
        except Exception as e:
            self.logger.error(f"General error checking notification removals: {e}")
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Retorna resumo do status do sistema de notificações"""
        return {
            "mode": self.config.mode.value,
            "devices_monitored": len(self.device_cache),
            "total_active_notifications": sum(len(notifs) for notifs in self.active_notifications_cache.values()),
            "polling_interval_minutes": self.config.polling_interval_minutes,
            "connection_timeout_hours": self.config.connection_timeout_hours,
            "last_check": datetime.now(timezone.utc).isoformat()
        }
    
    def toggle_mode(self, new_mode: NotificationMode):
        """Alterna entre modo Listener e Polling"""
        if self.config.mode == new_mode:
            return
        
        self.logger.info(f"Alternando modo de {self.config.mode.value} para {new_mode.value}")
        
        # Parar modo atual
        self.stop()
        
        # Atualizar configuração
        self.config.mode = new_mode
        self.save_config_to_file()
        
        # Reiniciar com novo modo
        self.start()
    
    def update_config(self, **kwargs):
        """Atualiza configurações do sistema"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                self.logger.info(f"Configuração atualizada: {key} = {value}")
        
        # Salvar configurações
        self.save_config_to_file()
    
    def _normalize_status_value(self, value):
        """Normaliza valores de status para comparação consistente"""
        if value is None:
            return None
        
        # Converter para string se necessário
        value_str = str(value)
        
        # Se contém " - ", extrair apenas o código (já processado pelo message_processor)
        if " - " in value_str:
            code_str = value_str.split(" - ")[0]
            try:
                decimal_value = int(code_str)
                return f"{decimal_value:02d}"  # Formato com 2 dígitos: 04, 10, etc.
            except ValueError:
                pass
        
        # Se já é decimal de 1-3 dígitos, formatar com 2 dígitos
        try:
            decimal_value = int(value_str)
            return f"{decimal_value:02d}"
        except ValueError:
            pass
        
        # Se é hexadecimal (2 caracteres), converter para decimal e depois para string com 2 dígitos
        # IMPORTANTE: Só tratar como hex se for EXATAMENTE 2 caracteres e for hex válido SEM ser decimal válido
        if (len(value_str) == 2 and 
            all(c in '0123456789ABCDEFabcdef' for c in value_str) and
            any(c in 'ABCDEFabcdef' for c in value_str)):  # Deve conter pelo menos uma letra hex
            try:
                decimal_value = int(value_str, 16)
                return f"{decimal_value:02d}"  # Formato com 2 dígitos: 04, 10, etc.
            except ValueError:
                pass
        
        # Retornar valor original se não conseguir normalizar
        return value_str
