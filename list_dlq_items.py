import boto3
import json
import os
import logging
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
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

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dlq_items_filtering.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class FilterCriteria:
    """Classe para definir critérios de filtro"""
    
    def __init__(self):
        self.filters: List[Callable[[Dict[str, Any]], bool]] = []
        self.filter_descriptions: List[str] = []
    
    def add_filter(self, filter_func: Callable[[Dict[str, Any]], bool], description: str):
        """Adiciona um filtro com sua descrição"""
        self.filters.append(filter_func)
        self.filter_descriptions.append(description)
    
    def apply_filters(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Aplica todos os filtros às mensagens"""
        if not self.filters:
            return messages
        
        filtered_messages = []
        for message in messages:
            passes_all_filters = True
            for filter_func in self.filters:
                if not filter_func(message):
                    passes_all_filters = False
                    break
            
            if passes_all_filters:
                filtered_messages.append(message)
        
        return filtered_messages


class DLQItemsLister:
    """Classe aprimorada para listar itens das Dead Letter Queues com filtragem avançada"""

    def __init__(self):
        self.sqs = sqs
        self.dlq_list = dlq_list
        self.filter_criteria = FilterCriteria()
        self.selected_queues: Optional[List[str]] = None
        self.max_messages_per_queue = 10
        self.filtered_results: Dict[str, List[Dict[str, Any]]] = {}

    def select_queues_interactively(self) -> List[str]:
        """
        Permite ao usuário selecionar filas específicas interativamente
        
        Returns:
            Lista de nomes das filas selecionadas
        """
        print("📋 Filas DLQ disponíveis:")
        print("-" * 40)
        
        for i, (queue_name, _) in enumerate(self.dlq_list, 1):
            print(f"  {i}. {queue_name}")
        
        print(f"  {len(self.dlq_list) + 1}. Todas as filas")
        
        try:
            selection = input("\n🔸 Selecione as filas (números separados por vírgula): ").strip()
            
            if not selection:
                return [name for name, _ in self.dlq_list]
            
            selected_indices = [int(x.strip()) for x in selection.split(',')]
            selected_queues = []
            
            for idx in selected_indices:
                if idx == len(self.dlq_list) + 1:
                    # Todas as filas
                    return [name for name, _ in self.dlq_list]
                elif 1 <= idx <= len(self.dlq_list):
                    selected_queues.append(self.dlq_list[idx - 1][0])
                else:
                    print(f"⚠️ Índice {idx} inválido, ignorando...")
            
            logger.info(f"Filas selecionadas: {selected_queues}")
            return selected_queues
            
        except ValueError:
            print("❌ Entrada inválida. Usando todas as filas.")
            return [name for name, _ in self.dlq_list]

    def configure_max_messages(self) -> int:
        """
        Permite ao usuário configurar o número máximo de mensagens por fila
        
        Returns:
            Número máximo de mensagens configurado
        """
        print("\n📊 Configuração do número máximo de mensagens por fila")
        print("(Padrão: 10, mínimo: 1, máximo: 100)")
        
        try:
            max_messages = input("🔸 Digite o número máximo de mensagens por fila: ").strip()
            
            if not max_messages:
                return 10
            
            max_messages = int(max_messages)
            
            if max_messages < 1:
                print("⚠️ Número muito baixo, usando 1")
                return 1
            elif max_messages > 100:
                print("⚠️ Número muito alto, usando 100")
                return 100
            
            logger.info(f"Número máximo de mensagens configurado: {max_messages}")
            return max_messages
            
        except ValueError:
            print("❌ Entrada inválida. Usando padrão (10).")
            return 10

    def setup_predefined_filters(self):
        """
        Configura filtros predefinidos baseados na entrada do usuário
        """
        print("\n🔍 Configuração de Filtros Predefinidos")
        print("=" * 50)
        print("1. Mensagens com descrições vazias")
        print("2. Mensagens com ID específico")
        print("3. Mensagens com campo customizado")
        print("4. Mensagens por período de tempo")
        print("5. Pular configuração de filtros")
        
        filter_choice = input("\n🔸 Escolha um filtro (1-5): ").strip()
        
        if filter_choice == "1":
            self._setup_empty_description_filter()
        elif filter_choice == "2":
            self._setup_specific_id_filter()
        elif filter_choice == "3":
            self._setup_custom_field_filter()
        elif filter_choice == "4":
            self._setup_time_period_filter()
        else:
            print("⏭️ Pulando configuração de filtros")

    def _setup_empty_description_filter(self):
        """Configura filtro para mensagens com descrições vazias"""
        def empty_description_filter(message: Dict[str, Any]) -> bool:
            body = message.get('body', {})
            if isinstance(body, dict):
                description = body.get('description', '')
                return description == '' or description is None
            return False
        
        self.filter_criteria.add_filter(
            empty_description_filter,
            "Mensagens com campo 'description' vazio"
        )
        print("✅ Filtro para descrições vazias configurado")

    def _setup_specific_id_filter(self):
        """Configura filtro para IDs específicos"""
        target_id = input("🔸 Digite o ID que deseja filtrar: ").strip()
        
        def specific_id_filter(message: Dict[str, Any]) -> bool:
            body = message.get('body', {})
            if isinstance(body, dict):
                # Procura em vários campos possíveis de ID
                for field in ['id', 'messageId', 'requestId', 'userId', 'itemId']:
                    if str(body.get(field, '')) == target_id:
                        return True
            return False
        
        self.filter_criteria.add_filter(
            specific_id_filter,
            f"Mensagens com ID '{target_id}'"
        )
        print(f"✅ Filtro para ID '{target_id}' configurado")

    def _setup_custom_field_filter(self):
        """Configura filtro para campo customizado"""
        field_name = input("🔸 Digite o nome do campo: ").strip()
        field_value = input("🔸 Digite o valor do campo: ").strip()
        
        def custom_field_filter(message: Dict[str, Any]) -> bool:
            body = message.get('body', {})
            if isinstance(body, dict):
                return str(body.get(field_name, '')) == field_value
            return False
        
        self.filter_criteria.add_filter(
            custom_field_filter,
            f"Mensagens onde campo '{field_name}' = '{field_value}'"
        )
        print(f"✅ Filtro para campo '{field_name}' = '{field_value}' configurado")

    def _setup_time_period_filter(self):
        """Configura filtro por período de tempo"""
        print("🕒 Filtro por período de tempo")
        print("Formato: YYYY-MM-DD HH:MM (exemplo: 2024-01-15 14:30)")
        
        start_time = input("🔸 Data/hora inicial (deixe vazio para ignorar): ").strip()
        end_time = input("🔸 Data/hora final (deixe vazio para ignorar): ").strip()
        
        start_dt = None
        end_dt = None
        
        try:
            if start_time:
                start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M")
            if end_time:
                end_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M")
        except ValueError:
            print("❌ Formato de data inválido. Filtro de tempo não será aplicado.")
            return
        
        def time_period_filter(message: Dict[str, Any]) -> bool:
            try:
                # Tenta obter timestamp da mensagem dos atributos
                attributes = message.get('attributes', {})
                sent_timestamp = attributes.get('SentTimestamp')
                
                if not sent_timestamp:
                    return True  # Se não há timestamp, passa o filtro
                
                # Converte timestamp Unix para datetime
                msg_time = datetime.fromtimestamp(int(sent_timestamp) / 1000)
                
                if start_dt and msg_time < start_dt:
                    return False
                if end_dt and msg_time > end_dt:
                    return False
                
                return True
            except:
                return True  # Em caso de erro, passa o filtro
        
        description = f"Mensagens entre {start_time or 'início'} e {end_time or 'fim'}"
        self.filter_criteria.add_filter(time_period_filter, description)
        print(f"✅ Filtro de período configurado: {description}")

    def get_messages_from_queue(
        self, queue_url: str, max_messages: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Recupera mensagens de uma fila específica com paginação para números maiores

        Args:
            queue_url: URL da fila SQS
            max_messages: Número máximo de mensagens para recuperar

        Returns:
            Lista de mensagens da fila
        """
        try:
            all_messages = []
            messages_received = 0

            while messages_received < max_messages:
                # SQS permite no máximo 10 mensagens por requisição
                batch_size = min(10, max_messages - messages_received)

                response = self.sqs.receive_message(
                    QueueUrl=queue_url,
                    MaxNumberOfMessages=batch_size,
                    WaitTimeSeconds=1,
                    MessageAttributeNames=['All'],
                    AttributeNames=['All'],
                )

                messages = response.get('Messages', [])

                if not messages:
                    # Não há mais mensagens disponíveis
                    break

                all_messages.extend(messages)
                messages_received += len(messages)

                logger.info(
                    f"Recuperadas {len(messages)} mensagens da fila {queue_url}"
                )

            return all_messages

        except Exception as e:
            print(f"❌ Erro ao acessar fila {queue_url}: {str(e)}")
            logger.error(f"Erro ao acessar fila {queue_url}: {str(e)}")
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

    def list_dlq_items_with_filters(
        self, max_messages_per_queue: int = None, selected_queues: List[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Lista itens das DLQs com filtros aplicados e seleção de filas

        Args:
            max_messages_per_queue: Número máximo de mensagens por fila
            selected_queues: Lista de filas selecionadas

        Returns:
            Dicionário com mensagens filtradas organizadas por fila
        """
        if max_messages_per_queue is None:
            max_messages_per_queue = self.max_messages_per_queue
        
        if selected_queues is None:
            selected_queues = self.selected_queues or [name for name, _ in self.dlq_list]

        all_messages = {}
        total_retrieved = 0
        total_after_filter = 0

        print("🔍 Listando itens das Dead Letter Queues com filtragem avançada...")
        print("=" * 60)
        
        # Log dos critérios de filtragem
        if self.filter_criteria.filters:
            print("🔎 Filtros aplicados:")
            for i, description in enumerate(self.filter_criteria.filter_descriptions, 1):
                print(f"  {i}. {description}")
                logger.info(f"Filtro {i}: {description}")
            print("-" * 60)
        else:
            print("📝 Nenhum filtro aplicado")

        # Filtra apenas as filas selecionadas
        selected_dlqs = [(name, url) for name, url in self.dlq_list if name in selected_queues]

        for queue_name, queue_url in selected_dlqs:
            print(f"\n📋 Processando: {queue_name.upper()}")
            print("-" * 40)

            messages = self.get_messages_from_queue(queue_url, max_messages_per_queue)
            total_retrieved += len(messages)

            if not messages:
                print("✅ Nenhuma mensagem encontrada")
                all_messages[queue_name] = []
                continue

            # Formatar mensagens
            formatted_messages = []
            for message in messages:
                formatted_msg = self.format_message(message, queue_name)
                formatted_messages.append(formatted_msg)

            # Aplicar filtros
            if self.filter_criteria.filters:
                filtered_messages = self.filter_criteria.apply_filters(formatted_messages)
                print(f"  📊 Mensagens recuperadas: {len(formatted_messages)}")
                print(f"  🔍 Após filtros: {len(filtered_messages)}")
                
                logger.info(f"Fila {queue_name}: {len(formatted_messages)} -> {len(filtered_messages)} após filtros")
            else:
                filtered_messages = formatted_messages
                print(f"  📊 Total: {len(filtered_messages)} mensagens")

            total_after_filter += len(filtered_messages)

            # Exibir IDs das mensagens filtradas
            for i, msg in enumerate(filtered_messages, 1):
                print(f"  📨 Mensagem {i}: {msg['message_id']}")

            all_messages[queue_name] = filtered_messages

        # Log do resumo
        logger.info(f"Total recuperado: {total_retrieved}, após filtros: {total_after_filter}")
        
        print(f"\n📊 RESUMO DE FILTRAGEM:")
        print(f"  📥 Total recuperado: {total_retrieved}")
        print(f"  ✅ Após filtros: {total_after_filter}")
        
        # Armazenar resultados filtrados
        self.filtered_results = all_messages
        
        return all_messages

    def list_all_dlq_items(
        self, max_messages_per_queue: int = 10
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Lista todos os itens de todas as DLQs (método legado mantido para compatibilidade)

        Args:
            max_messages_per_queue: Número máximo de mensagens por fila

        Returns:
            Dicionário com mensagens organizadas por fila
        """
        return self.list_dlq_items_with_filters(max_messages_per_queue, None)

    def save_filtered_results_to_json(self, filename: str = None) -> str:
        """
        Salva os resultados filtrados em um arquivo JSON com metadados

        Args:
            filename: Nome do arquivo (opcional)

        Returns:
            Nome do arquivo salvo
        """
        if not self.filtered_results:
            print("❌ Nenhum resultado filtrado disponível para salvar")
            return ""

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"dlq_filtered_items_{timestamp}.json"

        # Criar dados com metadados
        export_data = {
            "metadata": {
                "export_timestamp": datetime.now().isoformat(),
                "filters_applied": self.filter_criteria.filter_descriptions,
                "total_queues": len(self.filtered_results),
                "selected_queues": list(self.filtered_results.keys())
            },
            "results": {}
        }

        # Remove receipt_handle dos dados salvos por segurança
        for queue_name, messages in self.filtered_results.items():
            clean_messages = []
            for msg in messages:
                clean_msg = msg.copy()
                clean_msg.pop('receipt_handle', None)
                clean_messages.append(clean_msg)
            export_data["results"][queue_name] = clean_messages

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)

            print(f"\n💾 Resultados filtrados salvos em: {filename}")
            logger.info(f"Resultados filtrados exportados para: {filename}")
            return filename

        except Exception as e:
            print(f"❌ Erro ao salvar arquivo: {str(e)}")
            logger.error(f"Erro ao salvar arquivo: {str(e)}")
            return ""

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

    def run_interactive_mode(self):
        """
        Executa o modo interativo com todas as funcionalidades avançadas
        """
        print("🚀 DLQ Items Lister - Modo Interativo Avançado")
        print("=" * 60)
        
        # 1. Seleção de filas
        self.selected_queues = self.select_queues_interactively()
        
        # 2. Configuração do número máximo de mensagens
        self.max_messages_per_queue = self.configure_max_messages()
        
        # 3. Configuração de filtros
        self.setup_predefined_filters()
        
        # 4. Execução da listagem
        print("\n🔍 Iniciando processamento...")
        dlq_data = self.list_dlq_items_with_filters()
        
        # 5. Exibir resumo
        self.print_summary(dlq_data)
        
        # 6. Opções de salvamento
        if dlq_data and any(len(messages) > 0 for messages in dlq_data.values()):
            print("\n💾 Opções de Salvamento:")
            print("1. Salvar resultados filtrados (com metadados)")
            print("2. Salvar dados brutos")
            print("3. Não salvar")
            
            save_option = input("\n🔸 Escolha uma opção (1-3): ").strip()
            
            if save_option == "1":
                filename = self.save_filtered_results_to_json()
                if filename:
                    print("✅ Resultados filtrados salvos com sucesso!")
            elif save_option == "2":
                filename = self.save_to_json(dlq_data)
                if filename:
                    print("✅ Dados brutos salvos com sucesso!")
            else:
                print("📝 Dados não foram salvos")
        
        print("\n✨ Processamento concluído!")


def parse_cli_arguments():
    """
    Parse argumentos da linha de comando para modo CLI
    """
    parser = argparse.ArgumentParser(
        description="Lista e filtra itens das Dead Letter Queues"
    )
    
    parser.add_argument(
        "--max-messages",
        type=int,
        default=10,
        help="Número máximo de mensagens por fila (padrão: 10)"
    )
    
    parser.add_argument(
        "--queues",
        type=str,
        help="Filas específicas separadas por vírgula"
    )
    
    parser.add_argument(
        "--filter-empty-description",
        action="store_true",
        help="Filtrar mensagens com descrição vazia"
    )
    
    parser.add_argument(
        "--filter-id",
        type=str,
        help="Filtrar mensagens por ID específico"
    )
    
    parser.add_argument(
        "--filter-field",
        type=str,
        help="Filtro de campo customizado no formato 'campo:valor'"
    )
    
    parser.add_argument(
        "--save-filtered",
        action="store_true",
        help="Salvar resultados filtrados automaticamente"
    )
    
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Executar em modo interativo"
    )
    
    return parser.parse_args()


def main():
    """Função principal com suporte a CLI e modo interativo"""
    args = parse_cli_arguments()
    
    try:
        lister = DLQItemsLister()
        
        if args.interactive:
            # Modo interativo
            lister.run_interactive_mode()
        else:
            # Modo CLI
            print("🚀 Iniciando listagem de itens das DLQs...")
            
            # Configurar parâmetros do CLI
            max_messages = args.max_messages
            selected_queues = None
            
            if args.queues:
                selected_queues = [q.strip() for q in args.queues.split(',')]
            
            # Configurar filtros do CLI
            if args.filter_empty_description:
                def empty_desc_filter(message: Dict[str, Any]) -> bool:
                    body = message.get('body', {})
                    if isinstance(body, dict):
                        description = body.get('description', '')
                        return description == '' or description is None
                    return False
                
                lister.filter_criteria.add_filter(
                    empty_desc_filter,
                    "Mensagens com campo 'description' vazio (CLI)"
                )
            
            if args.filter_id:
                def id_filter(message: Dict[str, Any]) -> bool:
                    body = message.get('body', {})
                    if isinstance(body, dict):
                        for field in ['id', 'messageId', 'requestId', 'userId', 'itemId']:
                            if str(body.get(field, '')) == args.filter_id:
                                return True
                    return False
                
                lister.filter_criteria.add_filter(
                    id_filter,
                    f"Mensagens com ID '{args.filter_id}' (CLI)"
                )
            
            if args.filter_field:
                try:
                    field_name, field_value = args.filter_field.split(':', 1)
                    
                    def field_filter(message: Dict[str, Any]) -> bool:
                        body = message.get('body', {})
                        if isinstance(body, dict):
                            return str(body.get(field_name, '')) == field_value
                        return False
                    
                    lister.filter_criteria.add_filter(
                        field_filter,
                        f"Mensagens onde '{field_name}' = '{field_value}' (CLI)"
                    )
                except ValueError:
                    print("❌ Formato de filtro de campo inválido. Use 'campo:valor'")
            
            # Executar listagem
            dlq_data = lister.list_dlq_items_with_filters(max_messages, selected_queues)
            
            # Exibir resumo
            lister.print_summary(dlq_data)
            
            # Salvar se solicitado
            if args.save_filtered:
                filename = lister.save_filtered_results_to_json()
                if filename:
                    print("✅ Resultados filtrados salvos automaticamente!")
            else:
                # Modo legado - pergunta se deseja salvar
                save_option = (
                    input("\n💾 Deseja salvar os dados em arquivo JSON? (s/n): ")
                    .lower()
                    .strip()
                )
                
                if save_option in ['s', 'sim', 'y', 'yes']:
                    filename = lister.save_to_json(dlq_data)
                    if filename:
                        print("✅ Arquivo salvo com sucesso!")
        
        print("\n✨ Listagem concluída!")

    except KeyboardInterrupt:
        print("\n\n👋 Operação interrompida pelo usuário.")
    except Exception as e:
        print(f"\n❌ Erro durante execução: {str(e)}")
        logger.error(f"Erro durante execução: {str(e)}")


if __name__ == "__main__":
    main()
