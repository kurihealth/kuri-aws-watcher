import boto3
import json
import os
from datetime import datetime
from typing import List, Dict, Any
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

# Obter lista de DLQs usando o utilitário de configuração
dlq_list = config_manager.sqs_config.get_dlq_list()


class DLQItemsLister:
    """Classe para listar itens das Dead Letter Queues"""

    def __init__(self):
        self.sqs = sqs
        self.dlq_list = dlq_list

    def get_messages_from_queue(
        self, queue_url: str, max_messages: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Recupera mensagens de uma fila específica

        Args:
            queue_url: URL da fila SQS
            max_messages: Número máximo de mensagens para recuperar (1-10)

        Returns:
            Lista de mensagens da fila
        """
        try:
            response = self.sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=min(max_messages, 10),
                WaitTimeSeconds=1,
                MessageAttributeNames=['All'],
                AttributeNames=['All'],
            )

            return response.get('Messages', [])

        except Exception as e:
            print(f"❌ Erro ao acessar fila {queue_url}: {str(e)}")
            return []

    def format_message(
        self, message: Dict[str, Any], queue_name: str
    ) -> Dict[str, Any]:
        """
        Formata uma mensagem para exibição

        Args:
            message: Mensagem da fila SQS
            queue_name: Nome da fila

        Returns:
            Dicionário com dados formatados da mensagem
        """
        try:
            # Tenta fazer parse do JSON do corpo da mensagem
            body = json.loads(message.get('Body', '{}'))
        except json.JSONDecodeError:
            body = message.get('Body', '')

        return {
            'queue_name': queue_name,
            'message_id': message.get('MessageId', 'N/A'),
            'receipt_handle': message.get('ReceiptHandle', 'N/A')[:50]
            + '...',  # Trunca para exibição
            'body': body,
            'attributes': message.get('Attributes', {}),
            'message_attributes': message.get('MessageAttributes', {}),
            'md5_of_body': message.get('MD5OfBody', 'N/A'),
        }

    def list_all_dlq_items(
        self, max_messages_per_queue: int = 10
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Lista todos os itens de todas as DLQs

        Args:
            max_messages_per_queue: Número máximo de mensagens por fila

        Returns:
            Dicionário com mensagens organizadas por fila
        """
        all_messages = {}

        print("🔍 Listando itens das Dead Letter Queues...")
        print("=" * 60)

        for queue_name, queue_url in self.dlq_list:
            print(f"\n📋 Processando: {queue_name.upper()}")
            print("-" * 40)

            messages = self.get_messages_from_queue(queue_url, max_messages_per_queue)

            if not messages:
                print("✅ Nenhuma mensagem encontrada")
                all_messages[queue_name] = []
                continue

            formatted_messages = []
            for i, message in enumerate(messages, 1):
                formatted_msg = self.format_message(message, queue_name)
                formatted_messages.append(formatted_msg)
                print(f"  📨 Mensagem {i}: {formatted_msg['message_id']}")

            all_messages[queue_name] = formatted_messages
            print(f"  📊 Total: {len(formatted_messages)} mensagens")

        return all_messages

    def save_to_json(
        self, data: Dict[str, List[Dict[str, Any]]], filename: str = None
    ) -> str:
        """
        Salva os dados em um arquivo JSON

        Args:
            data: Dados das mensagens
            filename: Nome do arquivo (opcional)

        Returns:
            Nome do arquivo salvo
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"dlq_items_{timestamp}.json"

        # Remove receipt_handle dos dados salvos por segurança
        clean_data = {}
        for queue_name, messages in data.items():
            clean_messages = []
            for msg in messages:
                clean_msg = msg.copy()
                clean_msg.pop('receipt_handle', None)
                clean_messages.append(clean_msg)
            clean_data[queue_name] = clean_messages

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(clean_data, f, indent=2, ensure_ascii=False, default=str)

            print(f"\n💾 Dados salvos em: {filename}")
            return filename

        except Exception as e:
            print(f"❌ Erro ao salvar arquivo: {str(e)}")
            return ""

    def print_summary(self, data: Dict[str, List[Dict[str, Any]]]) -> None:
        """
        Exibe um resumo dos dados coletados

        Args:
            data: Dados das mensagens
        """
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        print("\n" + "=" * 60)
        print(f"📊 RESUMO DLQ ITEMS - {timestamp}")
        print("=" * 60)

        total_messages = 0
        for queue_name, messages in data.items():
            count = len(messages)
            total_messages += count
            status = "⚠️" if count > 0 else "✅"
            print(f"  {status} {queue_name.upper():<20} | {count} mensagens")

        print(f"\n📈 TOTAL DE MENSAGENS LISTADAS: {total_messages}")
        print("=" * 60)


def main():
    """Função principal"""
    print("🚀 Iniciando listagem de itens das DLQs...")

    try:
        lister = DLQItemsLister()

        # Lista todas as mensagens das DLQs
        dlq_data = lister.list_all_dlq_items(max_messages_per_queue=10)

        # Exibe resumo
        lister.print_summary(dlq_data)

        # Pergunta se deseja salvar em arquivo
        save_option = (
            input("\n💾 Deseja salvar os dados em arquivo JSON? (s/n): ")
            .lower()
            .strip()
        )

        if save_option in ['s', 'sim', 'y', 'yes']:
            filename = lister.save_to_json(dlq_data)
            if filename:
                print(f"✅ Arquivo salvo com sucesso!")

        print("\n✨ Listagem concluída!")

    except KeyboardInterrupt:
        print("\n\n👋 Operação interrompida pelo usuário.")
    except Exception as e:
        print(f"\n❌ Erro durante execução: {str(e)}")


if __name__ == "__main__":
    main()
