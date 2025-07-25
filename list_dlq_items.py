import argparse
import json
import logging
import os
from collections.abc import Callable
from datetime import datetime
from typing import Any

import boto3
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
    handlers=[logging.FileHandler('dlq_items_filtering.log'), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class FilterCriteria:
    """Classe para definir critérios de filtro"""

    def __init__(self):
        self.filters: list[Callable[[dict[str, Any]], bool]] = []
        self.filter_descriptions: list[str] = []

    def add_filter(
        self, filter_func: Callable[[dict[str, Any]], bool], description: str
    ):
        """Adiciona um filtro com sua descrição"""
        self.filters.append(filter_func)
        self.filter_descriptions.append(description)

    def apply_filters(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
        self.selected_queues: list[str] | None = None
        self.max_messages_per_queue = 10
        self.filtered_results: dict[str, list[dict[str, Any]]] = {}

    def select_queues_interactively(self) -> list[str]:
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
            selection = input(
                "\n🔸 Selecione as filas (números separados por vírgula): "
            ).strip()

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
            max_messages = input(
                "🔸 Digite o número máximo de mensagens por fila: "
            ).strip()

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

        def empty_description_filter(message: dict[str, Any]) -> bool:
            body = message.get('body', {})
            if isinstance(body, dict):
                description = body.get('description', '')
                return description == '' or description is None
            return False

        self.filter_criteria.add_filter(
            empty_description_filter, "Mensagens com campo 'description' vazio"
        )
        print("✅ Filtro para descrições vazias configurado")

    def _setup_specific_id_filter(self):
        """Configura filtro para IDs específicos"""
        target_id = input("🔸 Digite o ID que deseja filtrar: ").strip()

        def specific_id_filter(message: dict[str, Any]) -> bool:
            body = message.get('body', {})
            if isinstance(body, dict):
                # Procura em vários campos possíveis de ID
                for field in ['id', 'messageId', 'requestId', 'userId', 'itemId']:
                    if str(body.get(field, '')) == target_id:
                        return True
            return False

        self.filter_criteria.add_filter(
            specific_id_filter, f"Mensagens com ID '{target_id}'"
        )
        print(f"✅ Filtro para ID '{target_id}' configurado")

    def _setup_custom_field_filter(self):
        """Configura filtro para campo customizado"""
        field_name = input("🔸 Digite o nome do campo: ").strip()
        field_value = input("🔸 Digite o valor do campo: ").strip()

        def custom_field_filter(message: dict[str, Any]) -> bool:
            body = message.get('body', {})
            if isinstance(body, dict):
                return str(body.get(field_name, '')) == field_value
            return False

        self.filter_criteria.add_filter(
            custom_field_filter,
            f"Mensagens onde campo '{field_name}' = '{field_value}'",
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

        def time_period_filter(message: dict[str, Any]) -> bool:
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
    ) -> list[dict[str, Any]]:
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
        self, message: dict[str, Any], queue_name: str
    ) -> dict[str, Any]:
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

    def _safe_compare_values(self, value1: Any, value2: Any) -> bool:
        """
        Compara dois valores de forma segura, considerando diferentes tipos de dados

        Args:
            value1: Primeiro valor para comparação
            value2: Segundo valor para comparação

        Returns:
            True se os valores são equivalentes, False caso contrário
        """
        try:
            # Se ambos são None, são iguais
            if value1 is None and value2 is None:
                return True

            # Se um é None e outro não, são diferentes
            if value1 is None or value2 is None:
                return False

            # Conversão para string para comparação flexível
            str_value1 = str(value1).strip()
            str_value2 = str(value2).strip()

            # Comparação case-insensitive para strings
            if str_value1.lower() == str_value2.lower():
                return True

            # Tentativa de comparação numérica
            try:
                if float(str_value1) == float(str_value2):
                    return True
            except (ValueError, TypeError):
                pass

            # Comparação booleana
            try:
                bool_value1 = str_value1.lower() in ['true', '1', 'yes', 'sim']
                bool_value2 = str_value2.lower() in ['true', '1', 'yes', 'sim']
                if bool_value1 == bool_value2:
                    return True
            except:
                pass

            return False

        except Exception as e:
            logger.debug(f"Erro na comparação de valores: {e}")
            return False

    def count_messages_by_field(
        self,
        queue_name_or_url: str,
        field_name: str,
        field_value: Any,
        max_messages: int | None = None,
    ) -> int:
        """
        Conta mensagens em uma fila DLQ que possuem um campo específico com valor específico

        Args:
            queue_name_or_url: Nome da fila ou URL da fila SQS
            field_name: Nome do campo JSON a verificar
            field_value: Valor esperado do campo
            max_messages: Limite máximo de mensagens a processar (None = sem limite)

        Returns:
            Número inteiro de mensagens que atendem ao critério
        """
        logger.info(
            f"Iniciando contagem de mensagens: campo '{field_name}' = '{field_value}' na fila '{queue_name_or_url}'"
        )

        # Resolver URL da fila
        queue_url = self._resolve_queue_url(queue_name_or_url)
        if not queue_url:
            logger.error(
                f"Não foi possível resolver URL para fila: {queue_name_or_url}"
            )
            return 0

        total_count = 0
        total_processed = 0
        messages_with_json_errors = 0
        messages_without_field = 0

        print(f"🔍 Contando mensagens na fila: {queue_name_or_url}")
        print(f"📋 Critério: campo '{field_name}' = '{field_value}'")
        print("-" * 60)

        try:
            while True:
                # Se há limite e já processamos o suficiente, parar
                if max_messages and total_processed >= max_messages:
                    logger.info(f"Limite de {max_messages} mensagens atingido")
                    break

                # Calcular quantas mensagens buscar neste lote
                batch_size = 10
                if max_messages:
                    remaining = max_messages - total_processed
                    batch_size = min(10, remaining)

                # Buscar mensagens da fila
                response = self.sqs.receive_message(
                    QueueUrl=queue_url,
                    MaxNumberOfMessages=batch_size,
                    WaitTimeSeconds=1,
                    MessageAttributeNames=['All'],
                    AttributeNames=['All'],
                )

                messages = response.get('Messages', [])

                if not messages:
                    logger.info("Não há mais mensagens disponíveis na fila")
                    break

                # Processar cada mensagem no lote
                for message in messages:
                    total_processed += 1

                    try:
                        # Parse do JSON do corpo da mensagem
                        body_raw = message.get('Body', '{}')
                        body = json.loads(body_raw)

                        if not isinstance(body, dict):
                            logger.debug(
                                f"Corpo da mensagem não é um dicionário: {type(body)}"
                            )
                            messages_with_json_errors += 1
                            continue

                        # Verificar se o campo existe
                        if field_name not in body:
                            messages_without_field += 1
                            logger.debug(
                                f"Campo '{field_name}' não encontrado na mensagem {message.get('MessageId', 'N/A')}"
                            )
                            continue

                        # Obter valor do campo
                        field_actual_value = body[field_name]

                        # Comparar valores usando comparação segura
                        if self._safe_compare_values(field_actual_value, field_value):
                            total_count += 1
                            logger.debug(
                                f"Match encontrado: {field_name}={field_actual_value} na mensagem {message.get('MessageId', 'N/A')}"
                            )

                    except json.JSONDecodeError as e:
                        messages_with_json_errors += 1
                        logger.debug(
                            f"Erro de JSON na mensagem {message.get('MessageId', 'N/A')}: {e}"
                        )
                        continue
                    except Exception as e:
                        logger.error(
                            f"Erro processando mensagem {message.get('MessageId', 'N/A')}: {e}"
                        )
                        continue

                # Feedback de progresso
                if total_processed % 50 == 0:
                    print(
                        f"  📊 Processadas: {total_processed}, Matches: {total_count}"
                    )

                logger.info(
                    f"Lote processado: {len(messages)} mensagens, {total_count} matches até agora"
                )

        except Exception as e:
            logger.error(f"Erro durante contagem: {e}")
            print(f"❌ Erro durante processamento: {str(e)}")
            return total_count

        # Log final detalhado
        logger.info(
            f"Contagem finalizada - Total processado: {total_processed}, Matches: {total_count}"
        )
        logger.info(
            f"Estatísticas - JSON errors: {messages_with_json_errors}, Campo ausente: {messages_without_field}"
        )

        # Exibir resultado final
        print("\n📊 RESULTADO DA CONTAGEM:")
        print(f"  📥 Mensagens processadas: {total_processed}")
        print(f"  ✅ Matches encontrados: {total_count}")
        print(f"  ❌ Erros de JSON: {messages_with_json_errors}")
        print(f"  ⚠️ Campo '{field_name}' ausente: {messages_without_field}")
        print("-" * 60)

        return total_count

    def _resolve_queue_url(self, queue_name_or_url: str) -> str | None:
        """
        Resolve nome da fila para URL completa ou valida URL existente

        Args:
            queue_name_or_url: Nome da fila ou URL completa

        Returns:
            URL da fila ou None se não encontrada
        """
        # Se já é uma URL válida, retornar diretamente
        if queue_name_or_url.startswith('https://'):
            return queue_name_or_url

        # Procurar nas DLQs configuradas
        for queue_name, queue_url in self.dlq_list:
            if queue_name.lower() == queue_name_or_url.lower():
                return queue_url

        # Procurar nas filas normais também (caso seja especificada)
        try:
            all_queues = config_manager.sqs_config.get_all_queues()
            for queue_name, queue_url in all_queues:
                if queue_name.lower() == queue_name_or_url.lower():
                    return queue_url
        except Exception as e:
            logger.debug(f"Erro ao buscar filas normais: {e}")

        logger.error(f"Fila não encontrada: {queue_name_or_url}")
        return None

    def list_dlq_items_with_filters(
        self, max_messages_per_queue: int = None, selected_queues: list[str] = None
    ) -> dict[str, list[dict[str, Any]]]:
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
            selected_queues = self.selected_queues or [
                name for name, _ in self.dlq_list
            ]

        all_messages = {}
        total_retrieved = 0
        total_after_filter = 0

        print("🔍 Listando itens das Dead Letter Queues com filtragem avançada...")
        print("=" * 60)

        # Log dos critérios de filtragem
        if self.filter_criteria.filters:
            print("🔎 Filtros aplicados:")
            for i, description in enumerate(
                self.filter_criteria.filter_descriptions, 1
            ):
                print(f"  {i}. {description}")
                logger.info(f"Filtro {i}: {description}")
            print("-" * 60)
        else:
            print("📝 Nenhum filtro aplicado")

        # Filtra apenas as filas selecionadas
        selected_dlqs = [
            (name, url) for name, url in self.dlq_list if name in selected_queues
        ]

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
                filtered_messages = self.filter_criteria.apply_filters(
                    formatted_messages
                )
                print(f"  📊 Mensagens recuperadas: {len(formatted_messages)}")
                print(f"  🔍 Após filtros: {len(filtered_messages)}")

                logger.info(
                    f"Fila {queue_name}: {len(formatted_messages)} -> {len(filtered_messages)} após filtros"
                )
            else:
                filtered_messages = formatted_messages
                print(f"  📊 Total: {len(filtered_messages)} mensagens")

            total_after_filter += len(filtered_messages)

            # Exibir IDs das mensagens filtradas
            for i, msg in enumerate(filtered_messages, 1):
                print(f"  📨 Mensagem {i}: {msg['message_id']}")

            all_messages[queue_name] = filtered_messages

        # Log do resumo
        logger.info(
            f"Total recuperado: {total_retrieved}, após filtros: {total_after_filter}"
        )

        print("\n📊 RESUMO DE FILTRAGEM:")
        print(f"  📥 Total recuperado: {total_retrieved}")
        print(f"  ✅ Após filtros: {total_after_filter}")

        # Armazenar resultados filtrados
        self.filtered_results = all_messages

        return all_messages

    def list_all_dlq_items(
        self, max_messages_per_queue: int = 10
    ) -> dict[str, list[dict[str, Any]]]:
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
                "selected_queues": list(self.filtered_results.keys()),
            },
            "results": {},
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
        self, data: dict[str, list[dict[str, Any]]], filename: str = None
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

    def print_summary(self, data: dict[str, list[dict[str, Any]]]) -> None:
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

    def run_interactive_count_mode(self):
        """
        Executa o modo interativo de contagem de mensagens por campo-valor
        """
        print("🔢 DLQ Items Counter - Modo Interativo de Contagem")
        print("=" * 60)

        # 1. Solicitar campo a ser verificado
        field_name = input("🔸 Digite o nome do campo JSON a verificar: ").strip()
        if not field_name:
            print("❌ Campo é obrigatório.")
            return

        # 2. Solicitar valor esperado
        field_value = input(
            f"🔸 Digite o valor esperado para o campo '{field_name}': "
        ).strip()
        if not field_value:
            print("❌ Valor é obrigatório.")
            return

        # 3. Seleção de filas
        print("\n📋 Selecione as filas para contagem:")
        selected_queues = self.select_queues_interactively()

        # 4. Configurar limite de mensagens
        print("\n📊 Configuração do limite de mensagens")
        print("(Digite 0 para processar todas as mensagens disponíveis)")

        try:
            max_input = input(
                "🔸 Número máximo de mensagens a processar (padrão: 0): "
            ).strip()
            max_messages = int(max_input) if max_input else 0
            max_messages = None if max_messages == 0 else max_messages
        except ValueError:
            print("❌ Entrada inválida. Usando sem limite.")
            max_messages = None

        # 5. Executar contagem
        print("\n🎯 Iniciando contagem de mensagens:")
        print(f"📋 Campo: '{field_name}' = '{field_value}'")
        print(f"🏷️ Filas: {', '.join(selected_queues)}")
        print(f"📊 Limite: {'Sem limite' if max_messages is None else max_messages}")
        print("-" * 60)

        total_count = 0

        for queue_name in selected_queues:
            if queue_name in [name for name, _ in self.dlq_list]:
                print(f"\n{'='*60}")
                count = self.count_messages_by_field(
                    queue_name, field_name, field_value, max_messages
                )
                total_count += count
                print(f"✅ {queue_name}: {count} mensagens")
            else:
                print(f"⚠️ Fila '{queue_name}' não encontrada nas DLQs configuradas")

        print(f"\n🎉 RESULTADO FINAL: {total_count} mensagens encontradas")
        print(f"📋 Critério: {field_name} = {field_value}")
        print(f"🏷️ Filas processadas: {len(selected_queues)}")
        print("\n✨ Contagem concluída!")


def count_messages_by_field_standalone(
    queue_name: str,
    field_name: str,
    field_value: Any,
    max_messages: int | None = None,
) -> int:
    """
    Função wrapper standalone para contar mensagens por campo-valor

    Args:
        queue_name: Nome da fila DLQ
        field_name: Nome do campo JSON a verificar
        field_value: Valor esperado do campo
        max_messages: Limite máximo de mensagens a processar (opcional)

    Returns:
        Número inteiro de mensagens que atendem ao critério

    Example:
        count = count_messages_by_field_standalone("trigger-dlq", "table_code", "HM")
        print(f"Encontradas {count} mensagens com table_code=HM")
    """
    try:
        lister = DLQItemsLister()
        return lister.count_messages_by_field(
            queue_name, field_name, field_value, max_messages
        )
    except Exception as e:
        logger.error(f"Erro na contagem standalone: {e}")
        print(f"❌ Erro durante contagem: {str(e)}")
        return 0


def parse_cli_arguments():
    """
    Parse argumentos da linha de comando para modo CLI
    """
    parser = argparse.ArgumentParser(
        description="Lista e filtra itens das Dead Letter Queues ou conta mensagens por campo-valor"
    )

    parser.add_argument(
        "--max-messages",
        type=int,
        default=10,
        help="Número máximo de mensagens por fila (padrão: 10, 0 = sem limite)",
    )

    parser.add_argument(
        "--queues", type=str, help="Filas específicas separadas por vírgula"
    )

    parser.add_argument(
        "--filter-empty-description",
        action="store_true",
        help="Filtrar mensagens com descrição vazia",
    )

    parser.add_argument(
        "--filter-id", type=str, help="Filtrar mensagens por ID específico"
    )

    parser.add_argument(
        "--filter-field",
        type=str,
        help="Filtro de campo customizado no formato 'campo:valor'",
    )

    parser.add_argument(
        "--save-filtered",
        action="store_true",
        help="Salvar resultados filtrados automaticamente",
    )

    parser.add_argument(
        "--interactive", action="store_true", help="Executar em modo interativo"
    )

    # Novos argumentos para contagem de mensagens por campo
    parser.add_argument(
        "--count",
        action="store_true",
        help="Ativar modo contagem de mensagens por campo-valor (requer --field e --value)",
    )

    parser.add_argument(
        "--field", type=str, help="Nome do campo JSON a verificar (usado com --count)"
    )

    parser.add_argument(
        "--value", type=str, help="Valor esperado do campo (usado com --count)"
    )

    parser.add_argument(
        "--queue",
        type=str,
        help="Fila específica para contagem (usado com --count, padrão: todas as DLQs)",
    )

    return parser.parse_args()


def main():
    """Função principal com suporte a CLI e modo interativo"""
    args = parse_cli_arguments()

    try:
        lister = DLQItemsLister()

        # Modo contagem de mensagens por campo-valor
        if args.count:
            # Se --field e --value não foram fornecidos, entrar em modo interativo
            if not args.field or not args.value:
                print("🔢 Modo contagem ativo - Iniciando modo interativo")
                lister.run_interactive_count_mode()
                return

            # Determinar limite de mensagens
            max_messages = None if args.max_messages == 0 else args.max_messages

            # Determinar filas a processar
            if args.queue:
                # Fila específica
                print(f"🎯 Modo Contagem - Fila específica: {args.queue}")
                count = lister.count_messages_by_field(
                    args.queue, args.field, args.value, max_messages
                )
                print(f"\n🎉 RESULTADO FINAL: {count} mensagens encontradas")
            else:
                # Todas as DLQs
                print("🎯 Modo Contagem - Todas as DLQs")
                total_count = 0

                for queue_name, _ in lister.dlq_list:
                    print(f"\n{'='*60}")
                    count = lister.count_messages_by_field(
                        queue_name, args.field, args.value, max_messages
                    )
                    total_count += count
                    print(f"✅ {queue_name}: {count} mensagens")

                print(
                    f"\n🎉 RESULTADO FINAL: {total_count} mensagens encontradas em todas as DLQs"
                )

            return

        if args.interactive:
            # Modo interativo
            lister.run_interactive_mode()
        else:
            # Modo CLI tradicional (listagem/filtragem)
            print("🚀 Iniciando listagem de itens das DLQs...")

            # Configurar parâmetros do CLI
            max_messages = args.max_messages
            selected_queues = None

            if args.queues:
                selected_queues = [q.strip() for q in args.queues.split(',')]

            # Configurar filtros do CLI
            if args.filter_empty_description:

                def empty_desc_filter(message: dict[str, Any]) -> bool:
                    body = message.get('body', {})
                    if isinstance(body, dict):
                        description = body.get('description', '')
                        return description == '' or description is None
                    return False

                lister.filter_criteria.add_filter(
                    empty_desc_filter, "Mensagens com campo 'description' vazio (CLI)"
                )

            if args.filter_id:

                def id_filter(message: dict[str, Any]) -> bool:
                    body = message.get('body', {})
                    if isinstance(body, dict):
                        for field in [
                            'id',
                            'messageId',
                            'requestId',
                            'userId',
                            'itemId',
                        ]:
                            if str(body.get(field, '')) == args.filter_id:
                                return True
                    return False

                lister.filter_criteria.add_filter(
                    id_filter, f"Mensagens com ID '{args.filter_id}' (CLI)"
                )

            if args.filter_field:
                try:
                    field_name, field_value = args.filter_field.split(':', 1)

                    def field_filter(message: dict[str, Any]) -> bool:
                        body = message.get('body', {})
                        if isinstance(body, dict):
                            return str(body.get(field_name, '')) == field_value
                        return False

                    lister.filter_criteria.add_filter(
                        field_filter,
                        f"Mensagens onde '{field_name}' = '{field_value}' (CLI)",
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
