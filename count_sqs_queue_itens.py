import time
import boto3
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from config_utils import ConfigManager

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Configuração da sessão AWS usando variáveis de ambiente
session = boto3.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
)

sqs = session.client("sqs")

# Inicializar gerenciador de configuração
config_manager = ConfigManager()

# Obter lista de filas usando o utilitário de configuração
queue_url_list = config_manager.sqs_config.get_all_queue_list()

REFRESH_INTERVAL = int(os.getenv("REFRESH_INTERVAL", 10))
# Configuração do logging
LOG_INTERVAL_SECONDS = int(
    os.getenv("LOG_INTERVAL_SECONDS", "60")
)  # Padrão: 60 segundos
LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "sqs_monitoring.log")
SAVE_TO_LOG = True if os.getenv("SAVE_TO_LOG", "false") == "true" else False


class QueueChangeTracker:
    """Classe para rastrear mudanças nas contagens das filas SQS"""

    def __init__(self):
        self.previous_counts = {}
        self.changes_log_file = os.getenv("CHANGES_LOG_FILE_PATH", "sqs_changes.log")

    def detect_changes(self, current_counts: dict) -> dict:
        """Detecta mudanças entre contagens atual e anterior"""
        changes = {}

        for queue_name, current_count in current_counts.items():
            # Ignorar valores de erro
            if not isinstance(current_count, int):
                continue

            previous_count = self.previous_counts.get(queue_name, None)

            # Se é a primeira execução, apenas armazena o valor
            if previous_count is None:
                self.previous_counts[queue_name] = current_count
                continue

            # Calcular delta
            delta = current_count - previous_count

            # Se houve mudança, registrar
            if delta != 0:
                changes[queue_name] = {
                    'previous_count': previous_count,
                    'current_count': current_count,
                    'delta': delta,
                    'change_type': 'increase' if delta > 0 else 'decrease',
                }

            # Atualizar contagem anterior
            self.previous_counts[queue_name] = current_count

        return changes

    def log_changes(self, changes: dict) -> None:
        """Registra mudanças detectadas em arquivo de log"""
        if not SAVE_TO_LOG:
            return
        if not changes:
            return

        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            for queue_name, change_data in changes.items():
                log_entry = {
                    "timestamp": timestamp,
                    "queue_name": queue_name,
                    "previous_count": change_data['previous_count'],
                    "current_count": change_data['current_count'],
                    "delta": change_data['delta'],
                    "change_type": change_data['change_type'],
                }

                # Salvar no arquivo de mudanças
                with open(self.changes_log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

            # Feedback visual
            total_changes = len(changes)
            print(
                f"🔄 {total_changes} mudança(s) detectada(s) e registrada(s) em: {self.changes_log_file}"
            )

            # Mostrar resumo das mudanças
            for queue_name, change_data in changes.items():
                delta = change_data['delta']
                icon = "📈" if delta > 0 else "📉"
                sign = "+" if delta > 0 else ""
                print(
                    f"   {icon} {queue_name}: {change_data['previous_count']} → {change_data['current_count']} ({sign}{delta})"
                )

        except Exception as e:
            print(f"❌ Erro ao registrar mudanças: {str(e)}")


def save_to_log(data: dict, log_file: str = LOG_FILE_PATH) -> None:
    """Salva os dados de monitoramento em arquivo de log"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Preparar dados para log
        log_entry = {
            "timestamp": timestamp,
            "data": data,
            "total_messages": sum(v for v in data.values() if isinstance(v, int)),
        }

        # Salvar no arquivo de log
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        print(f"💾 Dados salvos no log: {log_file}")

    except Exception as e:
        print(f"❌ Erro ao salvar no log: {str(e)}")


def run() -> dict:
    messages_per_queue = {}
    for name, url in queue_url_list:
        try:
            response = sqs.get_queue_attributes(
                QueueUrl=url, AttributeNames=["ApproximateNumberOfMessages"]
            )
            messages = response["Attributes"]["ApproximateNumberOfMessages"]
            messages_per_queue[name] = int(messages)
        except Exception as e:
            messages_per_queue[name] = f"Erro: {str(e)}"

    return messages_per_queue


def format_output(data: dict) -> None:
    """Formata e exibe os dados das filas de forma mais apresentável"""
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    print("=" * 60)
    print(f"📊 MONITORAMENTO SQS - {timestamp}")
    print("=" * 60)

    # Separar DLQs das filas normais
    dlqs = {k: v for k, v in data.items() if "dlq" in k.lower()}
    queues = {k: v for k, v in data.items() if "dlq" not in k.lower()}

    if dlqs:
        print("\n🚨 DEAD LETTER QUEUES:")
        print("-" * 30)
        for name, count in dlqs.items():
            status = "⚠️" if isinstance(count, int) and count > 0 else "✅"
            print(f"  {status} {name.upper():<20} | {count} mensagens")

    if queues:
        print("\n📬 FILAS PRINCIPAIS:")
        print("-" * 30)
        for name, count in queues.items():
            status = "📨" if isinstance(count, int) and count > 0 else "📭"
            print(f"  {status} {name.upper():<20} | {count} mensagens")

    total_messages = sum(v for v in data.values() if isinstance(v, int))
    print(f"\n📈 TOTAL DE MENSAGENS: {total_messages}")
    print("=" * 60)


if __name__ == "__main__":
    # Inicializar tracker de mudanças
    change_tracker = QueueChangeTracker()

    print("🚀 Iniciando monitoramento SQS...")
    print(f"⏰ Atualizações a cada {REFRESH_INTERVAL} segundos")
    print(f"💾 Salvamento em log a cada {LOG_INTERVAL_SECONDS} segundos")
    print(f"📁 Arquivo de log: {LOG_FILE_PATH}")
    print(f"🔄 Arquivo de mudanças: {change_tracker.changes_log_file}")
    print("🛑 Pressione Ctrl+C para parar\n")

    try:
        last_log_time = time.time()

        while True:
            response = run()
            os.system(command='clear' if os.name == 'posix' else 'cls')
            format_output(response)

            changes = change_tracker.detect_changes(response)
            if SAVE_TO_LOG and changes:
                change_tracker.log_changes(changes)
                save_to_log(response)

            time.sleep(REFRESH_INTERVAL)
    except KeyboardInterrupt:
        print("\n\n👋 Monitoramento interrompido pelo usuário.")
    except Exception as e:
        print(f"\n❌ Erro durante execução: {str(e)}")
