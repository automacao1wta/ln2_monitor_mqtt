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
        self.messages = []
        self.last_messages_reset_timestamp = timestamp_now
        self.messages_reset_interval = timedelta(minutes=5)
        self.duplicates_dict = defaultdict(lambda: deque(maxlen=NUM_IDS_TO_STORE_PER_BEACON))
        self.sample_rate_ms = SAMPLE_RATE_MS
        self.logger = setup_logger(__name__)
        self.output_path = OUTPUT_PATH
        self.message_queue = message_queue
        self.schema = self._load_schema()

        # PostgreSQL connection (Cloud SQL)
        try:
            self.db_conn = psycopg2.connect(
                dbname="ln2-monitor-postgresql",
                user="postgres",
                password="wta@2025",
                host="127.0.0.1", # 34.31.34.87
                port=5432
            ) 
            self.db_cursor = self.db_conn.cursor()
        except Exception as e:
            self.logger.error(f"Erro ao conectar ao PostgreSQL: {e}")
            self.db_conn = None
            self.db_cursor = None

    def save_message_to_db(self, topic, message_dict):
        import math
        # Mapeamento explícito para garantir nomes idênticos ao banco
        def normalize_keys(d):
            mapping = {
                # Mapeamento para nomes exatos do banco
                "battpercent": "batt_percent",
                "beacon_serial": "beacon_serial",
                "crc": "crc",
                "epochtime_b": "epochtime_b",
                "epochtime_g": "epochtime_g",
                "fw_version_build": "fw_version_build",
                "fw_version_major": "fw_version_major",
                "fw_version_minor": "fw_version_minor",
                "fw_version_patch": "fw_version_patch",
                "fw_version_prefix": "fw_version_prefix",
                "id": "id",
                "ln2accdataavailable": "ln2_acc_data_available",
                "ln2anglestatus": "ln2_angle_status",
                "ln2batterystatus": "ln2_battery_status",
                "ln2foamstatus": "ln2_foam_status",
                "ln2generalstatus": "ln2_general_status",
                "ln2levelstatus": "ln2_level_status",
                "ln2txcausestatus": "ln2_tx_cause_status",
                "original_payload": "original_payload",
                "package_id": "package_id",
                "package_type": "package_type",
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
                "rssi": "rssi",
                "sensor_data_def_id": "sensor_data_def_id",
                "start_flag": "start_flag",
                "statusosccnt_lsb": "status_osc_cnt_lsb",
                "statusosccnt_msb": "status_osc_cnt_msb",
                "temp2": "temp2",
                "topic": "topic",
                "vccbat": "vccbat",
            }
            normalized = {}
            for k, v in d.items():
                key = k.lower().replace("-", "_")
                # Permite mapear chaves em maiúsculas/minúsculas
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
            "topic, start_flag, package_type, beacon_serial, vccbat, epochtime_b, epochtime_g, crc, package_id, temp2, "
            "r1, r2, r3, r4, r5, r6, r7, r8, r9, r10, r11, "
            "sensor_data_def_id, fw_version_prefix, fw_version_major, fw_version_minor, fw_version_patch, fw_version_build, "
            "ln2_level_status, ln2_angle_status, ln2_battery_status, batt_percent, ln2_foam_status, ln2_general_status, "
            "status_osc_cnt_msb, status_osc_cnt_lsb, ln2_acc_data_available, ln2_tx_cause_status, rssi, original_payload"
            ") VALUES ("
            + ",".join(["%s"] * 39) + ")"
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
            safe_float(message_dict.get("vccbat")),  # 5
            message_dict.get("epochtime_b"),  # 6
            message_dict.get("epochtime_g"),  # 7
            message_dict.get("crc"),  # 8
            safe_int(message_dict.get("package_id")),  # 9
            safe_float(message_dict.get("temp2")),  # 10
            message_dict.get("r1"),  # 11
            message_dict.get("r2"),  # 12
            message_dict.get("r3"),  # 13
            message_dict.get("r4"),  # 14
            message_dict.get("r5"),  # 15
            message_dict.get("r6"),  # 16
            message_dict.get("r7"),  # 17
            message_dict.get("r8"),  # 18
            message_dict.get("r9"),  # 19
            message_dict.get("r10"),  # 20
            message_dict.get("r11"),  # 21
            message_dict.get("sensor_data_def_id"),  # 22
            message_dict.get("fw_version_prefix"),  # 23
            message_dict.get("fw_version_major"),  # 24
            message_dict.get("fw_version_minor"),  # 25
            message_dict.get("fw_version_patch"),  # 26
            message_dict.get("fw_version_build"),  # 27
            message_dict.get("ln2_level_status"),  # 28
            message_dict.get("ln2_angle_status"),  # 29
            message_dict.get("ln2_battery_status"),  # 30
            message_dict.get("batt_percent"),  # 31
            message_dict.get("ln2_foam_status"),  # 32
            message_dict.get("ln2_general_status"),  # 33
            message_dict.get("status_osc_cnt_msb"),  # 34
            message_dict.get("status_osc_cnt_lsb"),  # 35
            message_dict.get("ln2_acc_data_available"),  # 36
            message_dict.get("ln2_tx_cause_status"),  # 37
            safe_int(message_dict.get("rssi")),  # 38
            message_dict.get("original_payload"),  # 39 REMOVIDO!
        )
        try:
            # Debug: conferir número de argumentos e tipos
            # print(len(values), values)
            print("JSON enviado:", json.dumps(message_dict, indent=4, ensure_ascii=False))
            print("Valores enviados para o banco:", values)
            print("Nº de %s no SQL:", sql.count('%s'))
            print("Nº de valores:", len(values))
            self.db_cursor.execute(sql, list(values))
            self.db_conn.commit()
        except Exception as e:
            self.logger.error(f"Erro ao inserir no banco: {e}")
        
    def _twos_comp(self, val, bits):
        """compute the 2's complement of int value val"""
        if (val & (1 << (bits - 1))) != 0:
            val = val - (1 << bits)
        return val
    

    def _load_schema(self) -> list[dict]:
        schema = [
            {"name": "start_flag", "start_idx": 0, "end_idx": 2},
            {"name": "package_type", "start_idx": 2, "end_idx": 4},
            {"name": "beacon_serial", "start_idx": 4, "end_idx": 16},
            {"name": "vccBat", "start_idx": 16, "end_idx": 20},
            {"name": "epochtime_b", "start_idx": 20, "end_idx": 28},
            {"name": "epochtime_g", "start_idx": 28, "end_idx": 36},
            {"name": "crc", "start_idx": 36, "end_idx": 38},
            {"name": "package_id", "start_idx": 38, "end_idx": 42},
            {"name": "temp2", "start_idx": 42, "end_idx": 46},

            # Reserved fields
            *[{"name": f"r{i}", "start_idx": 46 + (i - 1) * 2, "end_idx": 46 + i * 2} for i in range(1, 12)],
            # {"name": "r1", "start_idx": 46, "end_idx": 48},

            {"name": "SENSOR_DATA_DEF_ID", "start_idx": 50, "end_idx": 52},
            {"name": "FW_VERSION_PREFIX", "start_idx": 52, "end_idx": 54},

            {"name": "FW_VERSION_MAJOR", "start_idx": 54, "end_idx": 56},
            {"name": "FW_VERSION_MINOR", "start_idx": 56, "end_idx": 58},
            {"name": "FW_VERSION_PATCH", "start_idx": 58, "end_idx": 60},
            {"name": "FW_VERSION_BUILD", "start_idx": 60, "end_idx": 62},
            # {"name": "BEHAVIOR_OUT", "start_idx": 56, "end_idx": 58},
            # *[{"name": f"r{i}", "start_idx": 46 + (i - 1) * 4, "end_idx": 46 + i * 4} for i in range(7, 12)]

            {"name": "Ln2LevelStatus", "start_idx": 90, "end_idx": 92},
            {"name": "LN2AngleStatus", "start_idx": 92, "end_idx": 94},
            {"name": "LN2BatteryStatus", "start_idx": 94, "end_idx": 96},
            {"name": "BattPercent", "start_idx": 96, "end_idx": 98},
            {"name": "LN2FoamStatus", "start_idx": 98, "end_idx": 100},
            {"name": "LN2GeneralStatus", "start_idx": 100, "end_idx": 102},
            {"name": "StatusOscCnt_MSB", "start_idx": 102, "end_idx": 104},
            {"name": "StatusOscCnt_LSB", "start_idx": 104, "end_idx": 106},
            {"name": "LN2AccDataAvailable", "start_idx": 106, "end_idx": 108},
            {"name": "LN2TxCauseStatus", "start_idx": 108, "end_idx": 110},
            # Adicione outros campos conforme necessário
        ]

        # Sensor data
        start_idx = 90
        sensor_iterations = 0 #4
        idx = start_idx

        for i in range(sensor_iterations):
            # In each iteration, we have 3 sets of x, y, z
            for j in range(1, 16):
                schema.append({
                    "name": f"x{15 * i + j}",
                    "start_idx": idx,
                    "end_idx": idx + 2
                })
                idx += 2

                schema.append({
                    "name": f"y{15 * i + j}",
                    "start_idx": idx,
                    "end_idx": idx + 2
                })
                idx += 2

                schema.append({
                    "name": f"z{15 * i + j}",
                    "start_idx": idx,
                    "end_idx": idx + 2
                })
                idx += 2

            # After each block of 9 (x, y, z) fields (3 × 3), we have a temp reading
            schema.append({
                "name": f"--- temp{i + 1} ---",
                "start_idx": idx,
                "end_idx": idx + 4
            })
            idx += 4


        # RSSI
        schema.append({"name": "rssi", "start_idx": 486, "end_idx": 488})
        
        return schema

    
    def _get_status_comment(self, value: int) -> str:
        status_comments = {
            -2: "Unknown",
            -1: "Invalid",
            0: "Off",
            1: "On",
            2: "Closed",
            3: "Open",
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
            if k in ['tempPT100', 'tempAmbient']:
                # Interpretar como int16_t em centésimos de grau Celsius
                try:
                    raw_bytes = bytes.fromhex(v)
                    parsed_hex[k] = struct.unpack('>h', raw_bytes)[0] / 100
                except Exception:
                    parsed_hex[k] = v  # fallback para depuração se falhar
            elif k == 'Vbat_mV':
                raw_bytes = bytes.fromhex(v)
                vbat = struct.unpack('>H', raw_bytes)[0]
                parsed_hex[k] = vbat
            elif k == 'AngleToHorizontal':
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
            elif 'vccBat' in k:
                parsed_hex[k] = int(v, 16) / 1000
            elif 'temp' in k:
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
        with open(outpath, "w") as f:
            json.dump(self.messages, f)

        self.logger.info(f"Saving messages into {fname}")

        self.messages = []
        

    def add_message(self, message_dict:dict, hex_payload:str, topic:str=None):
        """Accumulate messages on self.messages and save to PostgreSQL."""
        print(hex_payload)
        print(json.dumps(message_dict, indent=4))
        print('-' * 20, '\n')

        message_dict['original_payload'] = hex_payload
        self.messages.append(message_dict)
        # Salva no banco de dados
        if topic is not None:
            self.save_message_to_db(topic, message_dict)

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
                    if BEACONS and message_dict['beacon_serial'] not in BEACONS:
                        continue

                    # Filter out duplicates
                    #if self.is_duplicate(message_dict):
                    #    continue

                    self.add_message(message_dict, message.payload.decode(), topic=message.topic)

                    self.duplicates_dict[message_dict['beacon_serial']].append(message_dict['package_id'])

                    # Save messages if messages_reset_interval was met
                    timestamp_now = datetime.now()
                    if timestamp_now - self.last_messages_reset_timestamp >= self.messages_reset_interval:
                        self.save_messages()
                        self.last_messages_reset_timestamp = timestamp_now

                # Gateway messages
                if 'tempHum' in message.topic:
                    continue

            except Exception as e:
                self.logger.exception("Error in message processing loop: %s", str(e))
