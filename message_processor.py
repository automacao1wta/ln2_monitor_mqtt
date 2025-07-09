import json
import yaml
from logger_config import setup_logger
from datetime import datetime, timedelta
import os
from paho.mqtt.client import MQTTMessage
from collections import deque, defaultdict
from queue import Queue
import struct
import psycopg2
import psycopg2
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()


# Load constants from config file
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)['message_processor']
OUTPUT_PATH = config['output_path']
SAMPLE_RATE_MS = config['sample_rate_ms']
NUM_IDS_TO_STORE_PER_BEACON = config['num_ids_to_store_per_beacon']
BEACONS = config['beacons']


class MessageProcessor:
    def __init__(self, message_queue: Queue[tuple[datetime, MQTTMessage]]) -> None:
        timestamp_now = datetime.now()
        self.messages = []  # Lista de pacotes "normais" a serem enviados a cada 5 min
        self.last_messages_reset_timestamp = timestamp_now
        self.messages_reset_interval = timedelta(minutes=5)
        self.duplicates_dict = defaultdict(lambda: deque(maxlen=NUM_IDS_TO_STORE_PER_BEACON))
        self.sample_rate_ms = SAMPLE_RATE_MS
        self.logger = setup_logger(__name__)
        self.output_path = OUTPUT_PATH
        self.message_queue = message_queue
        self.schema = self._load_schema()

        # Armazenar o último pacote "normal" de cada beacon
        self.last_beacon_data = {}  # beacon_serial -> (timestamp, message_dict, hex_payload, topic)

        # Controle de alertas por beacon
        self.alerts_per_beacon = defaultdict(list)  # beacon_serial -> [timestamps dos alertas enviados na última hora]
        self.ALERTS_PER_HOUR_LIMIT = 120  # Limite de alertas por hora por beacon (ajustável)
        self.ALERT_STATUS_VALUE = "04"  # Valor considerado "normal" para status

        # PostgreSQL connection (Cloud SQL)
        try:
            self.db_conn = psycopg2.connect(
                dbname="ln2-monitor-postgresql",
                user="postgres",
                password="wta@2025",
                host="34.31.34.87", # 34.31.34.87 #
                port=5432
            ) 
            self.db_cursor = self.db_conn.cursor()
        except Exception as e:
            self.logger.error(f"Erro ao conectar ao PostgreSQL: {e}")
            self.db_conn = None
            self.db_cursor = None

        # Firestore connection
        try:
            if not firebase_admin._apps:
                # Usar credenciais das variáveis de ambiente
                firebase_credentials = {
                    "type": "service_account",
                    "project_id": os.getenv("FIREBASE_PROJECT_ID", "coral-ring-463120-e6"),
                    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
                    "private_key": os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n'),
                    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL"),
                    "universe_domain": "googleapis.com"
                }
                
                # Verificar se as credenciais estão disponíveis
                if not firebase_credentials["private_key_id"] or not firebase_credentials["private_key"]:
                    raise ValueError("Credenciais do Firebase não encontradas nas variáveis de ambiente")
                
                cred = credentials.Certificate(firebase_credentials)
                firebase_admin.initialize_app(cred)
            self.firestore_db = firestore.client()
            self.logger.info("Conectado ao Firestore com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao conectar ao Firestore: {e}")
            self.firestore_db = None

    def save_message_to_db(self, topic, message_dict):
        import math
        # Mapeamento explícito para garantir nomes idênticos ao banco
        def normalize_keys(d):
            mapping = {
                "topic": "topic",
                "start_flag": "start_flag",
                "package_type": "package_type",
                "beacon_serial": "beacon_serial",
                # "vccbat": "vccbat",
                "epochtime_b": "epochtime_b",
                "epochtime_btx": "epochtime_btx",
                "epochtime_g": "epochtime_g",
                "crc": "crc",
                "rssi": "rssi",
                "package_id": "package_id",
                "tempa": "tempa",
                "r1": "r1",
                "r2": "r2",
                "r3": "r3",
                "r4": "r4",
                "r5": "r5",
                "r6": "r6",
                "r7": "r7",
                "r8": "r8",
                "r9": "r9",
                "r10": "r10",
                "r11": "r11",
                "sensor_data_def_id": "sensor_data_def_id",
                "fw_version_prefix": "fw_version_prefix",
                "fw_version_major": "fw_version_major",
                "fw_version_minor": "fw_version_minor",
                "fw_version_patch": "fw_version_patch",
                "fw_version_build": "fw_version_build",
                "acc_mode_full": "acc_mode_full",
                "ton_toff": "ton_toff",
                "ln2_level_status": "ln2_level_status",
                "ln2_angle_status": "ln2_angle_status",
                "ln2_battery_status": "ln2_battery_status",
                "batt_percent": "batt_percent",
                "ln2_foam_status": "ln2_foam_status",
                "ln2_general_status": "ln2_general_status",
                "status_osc_cnt": "status_osc_cnt",
                "ln2_acc_data_available": "ln2_acc_data_available",
                "ln2_tx_cause_status": "ln2_tx_cause_status",
                "temp_pt100": "temp_pt100",
                "temp_ambient": "temp_ambient",
                "angle_to_horizontal": "angle_to_horizontal",
                "vbat_mv": "vbat_mv",
                "original_payload": "original_payload",
            }
            normalized = {}
            for k, v in d.items():
                key = k.lower().replace("-", "_")
                if key in mapping:
                    normalized[mapping[key]] = v
                elif key.upper() in mapping:
                    normalized[mapping[key.upper()]] = v
                else:
                    normalized[key] = v
            return normalized
        message_dict = normalize_keys(message_dict)
        if not self.db_cursor:
            self.logger.error("Sem conexão com o banco de dados!")
            return
        sql = (
            "INSERT INTO mqtt_messages ("
            "topic, start_flag, package_type, beacon_serial, epochtime_b, epochtime_btx, epochtime_g, crc, package_id, tempa, "
            "r1, r2, r3, r4, r5, r6, r7, r8, r9, r10, r11, "
            "sensor_data_def_id, fw_version_prefix, fw_version_major, fw_version_minor, fw_version_patch, fw_version_build, "
            "acc_mode_full, ton_toff, ln2_level_status, ln2_angle_status, ln2_battery_status, batt_percent, ln2_foam_status, ln2_general_status, "
            "status_osc_cnt, ln2_acc_data_available, ln2_tx_cause_status, temp_pt100, temp_ambient, angle_to_horizontal, vbat_mv, rssi, original_payload"
            ") VALUES ("
            + ",".join(["%s"] * 44) + ")"
        )
        def safe_float(val):
            try:
                if val is None or (isinstance(val, float) and math.isnan(val)):
                    return None
                return float(val)
            except Exception:
                return None
        def safe_int(val):
            try:
                if val is None or (isinstance(val, float) and math.isnan(val)):
                    return None
                return int(val)
            except Exception:
                return None
        values = (
            topic,  # 1
            message_dict.get("start_flag"),  # 2
            message_dict.get("package_type"),  # 3
            message_dict.get("beacon_serial"),  # 4
            # safe_float(message_dict.get("vccbat")),  # 5
            message_dict.get("epochtime_b"),  # 6
            message_dict.get("epochtime_btx"),  # 7
            message_dict.get("epochtime_g"),  # 8
            message_dict.get("crc"),  # 9
            safe_int(message_dict.get("package_id")),  # 10
            safe_float(message_dict.get("tempa")),  # 11
            message_dict.get("r1"),  # 12
            message_dict.get("r2"),  # 13
            message_dict.get("r3"),  # 14
            message_dict.get("r4"),  # 15
            message_dict.get("r5"),  # 16
            message_dict.get("r6"),  # 17
            message_dict.get("r7"),  # 18
            message_dict.get("r8"),  # 19
            message_dict.get("r9"),  # 20
            message_dict.get("r10"),  # 21
            message_dict.get("r11"),  # 22
            message_dict.get("sensor_data_def_id"),  # 23
            message_dict.get("fw_version_prefix"),  # 24
            message_dict.get("fw_version_major"),  # 25
            message_dict.get("fw_version_minor"),  # 26
            message_dict.get("fw_version_patch"),  # 27
            message_dict.get("fw_version_build"),  # 28
            message_dict.get("acc_mode_full"),  # 29
            message_dict.get("ton_toff"),  # 30
            message_dict.get("ln2_level_status"),  # 31
            message_dict.get("ln2_angle_status"),  # 32
            message_dict.get("ln2_battery_status"),  # 33
            message_dict.get("batt_percent"),  # 34
            message_dict.get("ln2_foam_status"),  # 35
            message_dict.get("ln2_general_status"),  # 36
            message_dict.get("status_osc_cnt"),  # 37
            message_dict.get("ln2_acc_data_available"),  # 38
            message_dict.get("ln2_tx_cause_status"),  # 39
            safe_float(message_dict.get("temp_pt100")),  # 40
            safe_float(message_dict.get("temp_ambient")),  # 41
            safe_float(message_dict.get("angle_to_horizontal")),  # 42
            safe_float(message_dict.get("vbat_mv")),  # 43
            safe_int(message_dict.get("rssi")),
            message_dict.get("original_payload"),  # 44
        )
        try:
            # Debug: conferir número de argumentos e tipos
            # print(len(values), values)
            # print("JSON enviado:", json.dumps(message_dict, indent=4, ensure_ascii=False))
            print("Valores enviados para o banco:", values)
            # print("Nº de %s no SQL:", sql.count('%s'))
            # print("Nº de valores:", len(values))
            self.db_cursor.execute(sql, list(values))
            self.db_conn.commit()
            print(f"Mensagem publicada no SQL para o beacon {message_dict.get('beacon_serial')} (package_id={message_dict.get('package_id')}) no tópico '{topic}' em {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            self.logger.error(f"Erro ao inserir no banco: {e}")
        
        # Também salvar no Firestore
        self.save_message_to_firestore(topic, message_dict)
        
    def save_message_to_firestore(self, topic, message_dict):
        """
        Salva dados específicos no Firestore seguindo a estrutura solicitada
        """
        if not self.firestore_db:
            self.logger.error("Sem conexão com o Firestore!")
            return
            
        try:
            # Extrair beacon_serial (equipamentID)
            equipment_id = message_dict.get('beacon_serial')
            if not equipment_id:
                self.logger.error("Beacon serial não encontrado para salvar no Firestore")
                return
            
            # Data formatada para a coleção (formato YYYY-MM-DD)
            now = datetime.now()
            formatted_date = now.strftime('%Y-%m-%d')
            formatted_time = now.strftime('%H-%M-%S')
            
            # Extrair e converter os valores específicos solicitados
            def safe_float_convert(val):
                try:
                    if val is None:
                        return None
                    return float(val)
                except (ValueError, TypeError):
                    return None
            
            # Mapeamento dos dados para o Firestore
            firestore_data = {
                'humidity': None,  # Não temos esse campo nos dados atuais, definindo como None
                'pBat': safe_float_convert(message_dict.get('batt_percent')),  # Porcentagem da bateria
                'tempAmbient': safe_float_convert(message_dict.get('temp_ambient')),  # Temperatura ambiente
                'tempPT100': safe_float_convert(message_dict.get('temp_pt100')),  # Temperatura PT100
                'vBat': safe_float_convert(message_dict.get('vbat_mv')) / 1000.0 if message_dict.get('vbat_mv') else None,  # Converter mV para V
                'timestamp': now,  # Timestamp da mensagem
                'package_id': message_dict.get('package_id'),  # ID do pacote para referência
            }
            
            # Remover valores None para não salvar campos vazios
            firestore_data = {k: v for k, v in firestore_data.items() if v is not None}
            
            # Estrutura: LN2-00002 (Collection) > data (Document) > 2025-06-09 (Collection) > 09-45-00 (Document) > firestore_data
            collection_ref = self.firestore_db.collection(equipment_id)
            data_doc_ref = collection_ref.document('data')
            date_collection_ref = data_doc_ref.collection(formatted_date)
            time_doc_ref = date_collection_ref.document(formatted_time)
            
            # Salvar no Firestore
            time_doc_ref.set(firestore_data)
            
            self.logger.info(f"Dados salvos no Firestore: {equipment_id}/data/{formatted_date}/{formatted_time} - {firestore_data}")
            print(f"Mensagem publicada no Firestore para o beacon {equipment_id} em {formatted_date} às {formatted_time}")
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar no Firestore: {e}")
        
    def _twos_comp(self, val, bits):
        """compute the 2's complement of int value val"""
        if (val & (1 << (bits - 1))) != 0:
            val = val - (1 << bits)
        return val
    

    def _load_schema(self) -> list[dict]:
        schema = [
            {"name": "start_flag", "start_idx": 0, "end_idx": 2},            # [0]
            {"name": "package_type", "start_idx": 2, "end_idx": 4},          # [1]
            {"name": "beacon_serial", "start_idx": 4, "end_idx": 16},        # [2-7]
            # {"name": "vccbat", "start_idx": 16, "end_idx": 20},              # [8-9]
            {"name": "epochtime_b", "start_idx": 20, "end_idx": 28},         # [10-13]
            {"name": "epochtime_btx", "start_idx": 74, "end_idx": 82},       # [37-40] Beacon Tx Time
            {"name": "epochtime_g", "start_idx": 28, "end_idx": 36},         # [14-17]
            {"name": "crc", "start_idx": 36, "end_idx": 38},                 # [18]
            {"name": "package_id", "start_idx": 38, "end_idx": 42},          # [19-20]
            {"name": "tempa", "start_idx": 42, "end_idx": 46},               # [21-22]
            # r1 a r11 intactos
            *[{"name": f"r{i}", "start_idx": 46 + (i - 1) * 4, "end_idx": 46 + (i - 1) * 4 + 4} for i in range(1, 12)],
            # Campos específicos mapeados nos mesmos offsets
            {"name": "sensor_data_def_id", "start_idx": 50, "end_idx": 52},  # [25]
            {"name": "fw_version_prefix", "start_idx": 52, "end_idx": 54},   # [26]
            {"name": "fw_version_major", "start_idx": 54, "end_idx": 56},    # [27]
            {"name": "fw_version_minor", "start_idx": 56, "end_idx": 58},    # [28]
            {"name": "fw_version_patch", "start_idx": 58, "end_idx": 60},    # [29]
            {"name": "fw_version_build", "start_idx": 60, "end_idx": 62},    # [30]
            {"name": "acc_mode_full", "start_idx": 82, "end_idx": 86},       # [41-42]
            {"name": "ton_toff", "start_idx": 86, "end_idx": 90},             # [43-44]
            {"name": "ln2_level_status", "start_idx": 90, "end_idx": 92},      # [45]
            {"name": "ln2_angle_status", "start_idx": 92, "end_idx": 94},      # [46]
            {"name": "ln2_battery_status", "start_idx": 94, "end_idx": 96},    # [47]
            {"name": "batt_percent", "start_idx": 96, "end_idx": 98},         # [48]
            {"name": "ln2_foam_status", "start_idx": 98, "end_idx": 100},      # [49]
            {"name": "ln2_general_status", "start_idx": 100, "end_idx": 102},  # [50]
            {"name": "status_osc_cnt", "start_idx": 102, "end_idx": 106},      # [51-52]
            {"name": "ln2_acc_data_available", "start_idx": 106, "end_idx": 108},# [53]
            {"name": "ln2_tx_cause_status", "start_idx": 108, "end_idx": 110},  # [54]
            {"name": "temp_pt100", "start_idx": 112, "end_idx": 116},         # [56-57]
            {"name": "temp_ambient", "start_idx": 116, "end_idx": 120},       # [58-59]
            {"name": "angle_to_horizontal", "start_idx": 120, "end_idx": 124}, # [60-61]
            {"name": "vbat_mv", "start_idx": 124, "end_idx": 128},           # [62-63]
            {"name": "rssi", "start_idx": 486, "end_idx": 488},                # [62-63]
        ]
        return schema

    
    def _get_status_comment(self, value: int) -> str:
        status_comments = {
            -2: "Sem informação",
            -1: "Dado inválido",
            0: "Ligado",
            1: "Desligado",
            2: "Tampa fechada",
            3: "Tampa aberto",
            4: "Good",
            5: "Warning",
            6: "Bad",
            7: "Present",
            8: "Absent",
            9: "Very Low",
            10: "Low",
            11: "High",
            12: "Very High",
            13: "Uncalibrated",
            14: "Calibrated",
            15: "Status Change",
            16: "Change rate limit",
            17: "Tx Period Elapsed",
            18: "Forced Tx"
        }
        label = status_comments.get(value, f"Desconhecido ({value})")
        return f"{value} - {label}"


    def _parse_hex_string(self, hex_string: str, timestamp: datetime) -> dict:
        values = {field['name']: hex_string[field['start_idx']: field['end_idx']] for field in self.schema}
        parsed_hex = {}

        for k, v in values.items():
            if k in ['temp_pt100', 'temp_ambient']:
                # Interpretar como int16_t em centésimos de grau Celsius
                try:
                    raw_bytes = bytes.fromhex(v)
                    parsed_hex[k] = struct.unpack('>h', raw_bytes)[0] / 100
                except Exception:
                    parsed_hex[k] = v  # fallback para depuração se falhar
            elif k == 'vbat_mv':
                raw_bytes = bytes.fromhex(v)
                vbat = struct.unpack('>H', raw_bytes)[0]
                parsed_hex[k] = vbat
            elif k == 'angle_to_horizontal':
                raw_bytes = bytes.fromhex(v)
                angle = struct.unpack('>H', raw_bytes)[0]
                parsed_hex[k] = angle
            elif 'rssi' in k:
                parsed_hex[k] = self._twos_comp(int(v, 16), 8)
            elif 'epochtime' in k:
                parsed_hex[k] = int(v, 16)
                parsed_hex[k] = datetime.fromtimestamp(parsed_hex[k]).strftime("%Y-%m-%d %H-%M-%S.%f")[:-3]
            elif 'package_id' in k:
                parsed_hex[k] = int(v, 16)
            elif 'vccbat' in k:
                parsed_hex[k] = int(v, 16) / 1000
            elif 'tempa' in k:
                parsed_hex[k] = int(v, 16) / 100
            elif k.endswith('Status'):
                try:
                    # Tenta converter para int (pode ser signed ou unsigned)
                    status_val = int(v, 16)
                    # Ajusta para signed se necessário (assume 8 bits)
                    if status_val >= 0x80:
                        status_val -= 0x100
                    parsed_hex[k] = self._get_status_comment(status_val)
                except Exception:
                    parsed_hex[k] = v
            else:
                parsed_hex[k] = v

        return parsed_hex


    def _convert_hex_to_float(self, hex_char, bits, desired_range:tuple=(-4, 4)):
        int_value = int(hex_char, 16)
        signed_value = self._twos_comp(int_value, bits=bits)
        increments = (desired_range[1] - desired_range[0]) / (2**bits)
        float_value = signed_value * increments
        return float_value


    def save_messages(self) -> None:
        """Saves messages into JSON file and resets self.messages
        """
        # Get fname from data
        timestamp_str = self.messages[-1]['epochtime_b']
        fname = f"{timestamp_str}.json"
        outpath = os.path.join(self.output_path, fname)

        # Comentar esta linha se quiser não salvar em JSON
        # with open(outpath, "w") as f:
        #     json.dump(self.messages, f)

        self.logger.info(f"Saving messages into {fname}")

        self.messages = []
        


    def add_message(self, message_dict:dict, hex_payload:str, topic:str=None):
        """
        Acumula mensagens por beacon_serial para envio a cada 5 minutos.
        Se detectar condição de alerta, envia imediatamente (respeitando o limite de alertas por hora).
        """
        print(hex_payload)
        print(json.dumps(message_dict, indent=4))
        print('-' * 20, '\n')

        message_dict['original_payload'] = hex_payload
        beacon_serial = message_dict.get('beacon_serial')
        now = datetime.now()

        # --- Verificação de condição de alerta ---
        # Se qualquer status for diferente de ALERT_STATUS_VALUE, é alerta
        is_alert = False
        for status_field in ["ln2_general_status"]: # "ln2_level_status", "ln2_angle_status", "ln2_battery_status", "ln2_foam_status"
            val = message_dict.get(status_field)
            if val is not None and val != self.ALERT_STATUS_VALUE:
                is_alert = True
                break

        if is_alert:
            # Limpeza dos alertas antigos (mais de 1h)
            self.alerts_per_beacon[beacon_serial] = [t for t in self.alerts_per_beacon[beacon_serial] if (now - t).total_seconds() < 3600]
            if len(self.alerts_per_beacon[beacon_serial]) < self.ALERTS_PER_HOUR_LIMIT:
                # Envia alerta imediatamente
                if topic is not None:
                    self.save_message_to_db(topic, message_dict)
                self.alerts_per_beacon[beacon_serial].append(now)
                self.logger.info(f"Alerta enviado para {beacon_serial} em {now} (total na última hora: {len(self.alerts_per_beacon[beacon_serial])})")
            else:
                self.logger.info(f"Alerta descartado para {beacon_serial} (limite de {self.ALERTS_PER_HOUR_LIMIT} por hora atingido)")
            return  # Não armazena para envio normal

        # --- Acumulação normal: só armazena o primeiro pacote do beacon até o próximo ciclo de 5 min ---
        if beacon_serial not in self.last_beacon_data:
            self.last_beacon_data[beacon_serial] = (now, message_dict, hex_payload, topic)
        # Se já existe, descarta os demais até o próximo ciclo

    def flush_beacon_data(self):
        """
        Envia para o banco o último pacote "normal" de cada beacon e limpa o cache.
        """
        for beacon_serial, (ts, message_dict, hex_payload, topic) in self.last_beacon_data.items():
            if topic is not None:
                self.save_message_to_db(topic, message_dict)
        self.last_beacon_data.clear()

    def is_duplicate(self, message_dict:dict) -> bool:
        return message_dict['package_id'] in self.duplicates_dict[message_dict['beacon_serial']]
    

    def _load_message(self, message:MQTTMessage, timestamp:datetime) -> tuple[str, dict]:
        """Loads a MQTTMessage into a dict

        Parameters
        ----------
        message : MQTTMessage

        Returns
        -------
        tuple[str, dict] | None
            Tuple containing gateway_serial and message_dict
        """
        topic = message.topic
        gateway_serial = topic[3:-4].lower()
        
        try:
            decoded_payload = message.payload.decode()
        except UnicodeDecodeError:
            self.logger.exception("Failed decoding payload %s", message.payload)
        
        message_dict = self._parse_hex_string(decoded_payload, timestamp)

        self.logger.debug(f"Message dict: {message_dict}")
        
        return gateway_serial, message_dict
    


    def run(self):
        while True:
            try:
                message_timestamp, message = self.message_queue.get()
                # Beacon messages
                if 'Pub' in message.topic:
                    gateway_serial, message_dict = self._load_message(message, message_timestamp)

                    # Filter beacons
                    # if BEACONS and message_dict['beacon_serial'] not in BEACONS:
                    #     continue

                    # Filter out duplicates
                    #if self.is_duplicate(message_dict):
                    #    continue

                    self.add_message(message_dict, message.payload.decode(), topic=message.topic)

                    self.duplicates_dict[message_dict['beacon_serial']].append(message_dict['package_id'])

                    # A cada ciclo de 5 minutos, envia o último pacote normal de cada beacon
                    timestamp_now = datetime.now()
                    if timestamp_now - self.last_messages_reset_timestamp >= self.messages_reset_interval:
                        self.flush_beacon_data()
                        self.last_messages_reset_timestamp = timestamp_now

                # Gateway messages
                if 'tempHum' in message.topic:
                    continue

            except Exception as e:
                self.logger.exception("Error in message processing loop: %s", str(e))
