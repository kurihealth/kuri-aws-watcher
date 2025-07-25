#!/usr/bin/env python3
"""
Lambda Watcher V2 - Sistema avançado de monitoramento de logs Lambda
Suporte a múltiplas funções, filtros de erro, interface CLI interativa e saída JSON estruturada
"""

import argparse
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from typing import Any

import boto3
from dotenv import load_dotenv

from config_utils import LambdaConfig

load_dotenv()


class MultiLambdaWatcher:
    """
    Classe principal para monitoramento de múltiplas funções Lambda
    """

    def __init__(self, region: str = 'us-east-1'):
        """
        Inicializa o watcher com configuração AWS

        Args:
            region (str): Região AWS (padrão: us-east-1)
        """
        self.region = region
        self.session = boto3.Session(
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_DEFAULT_REGION", region),
        )
        self.logs_client = self.session.client('logs')

        # Palavras-chave para detecção de erros
        self.error_keywords = [
            'error',
            'exception',
            'traceback',
            'failed',
            'timeout',
            'fatal',
            'critical',
            'panic',
            'abort',
            'crash',
        ]

    def get_function_logs(
        self, function_name: str, hours_back: int = 4, errors_only: bool = True
    ) -> dict[str, Any]:
        """
        Recupera logs de uma função Lambda específica

        Args:
            function_name (str): Nome da função Lambda
            hours_back (int): Horas atrás para buscar logs
            errors_only (bool): Se deve filtrar apenas erros

        Returns:
            Dict com logs formatados e metadados
        """
        log_group_name = f"/aws/lambda/{function_name}"

        # Calcular timestamps
        end_time = datetime.now(tz=UTC)
        start_time = end_time - timedelta(hours=hours_back)

        start_timestamp = int(start_time.timestamp() * 1000)
        end_timestamp = int(end_time.timestamp() * 1000)

        print(f"🔍 Processando função '{function_name}'...")

        try:
            # Buscar eventos com paginação
            events = []
            response = self.logs_client.filter_log_events(
                logGroupName=log_group_name,
                startTime=start_timestamp,
                endTime=end_timestamp,
            )

            events.extend(response.get('events', []))

            # Continuar paginação se necessário
            while 'nextToken' in response:
                response = self.logs_client.filter_log_events(
                    logGroupName=log_group_name,
                    startTime=start_timestamp,
                    endTime=end_timestamp,
                    nextToken=response['nextToken'],
                )
                events.extend(response.get('events', []))

            # Processar eventos
            processed_logs = []
            error_count = 0
            total_events = len(events)

            for event in events:
                timestamp = datetime.fromtimestamp(
                    event['timestamp'] / 1000, tz=UTC
                )
                message = event['message'].strip()

                # Detectar se é erro
                is_error = any(
                    keyword in message.lower() for keyword in self.error_keywords
                )

                if is_error:
                    error_count += 1

                # Aplicar filtro de erros se solicitado
                if errors_only and not is_error:
                    continue

                # Estruturar log
                log_entry = {
                    'timestamp': timestamp.isoformat(),
                    'timestamp_ms': event['timestamp'],
                    'message': message,
                    'log_stream': event.get('logStreamName', ''),
                    'is_error': is_error,
                    'level': 'ERROR' if is_error else 'INFO',
                }

                processed_logs.append(log_entry)

            # Ordenar por timestamp (mais recente primeiro)
            processed_logs.sort(key=lambda x: x['timestamp_ms'], reverse=True)

            return {
                'function_name': function_name,
                'log_group': log_group_name,
                'query_info': {
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'hours_back': hours_back,
                    'errors_only': errors_only,
                    'region': self.region,
                },
                'statistics': {
                    'total_events': total_events,
                    'displayed_events': len(processed_logs),
                    'error_count': error_count,
                    'info_count': total_events - error_count,
                },
                'logs': processed_logs,
                'status': 'success',
            }

        except Exception as e:
            error_msg = str(e)
            print(f"❌ Erro ao processar '{function_name}': {error_msg}")

            return {
                'function_name': function_name,
                'log_group': log_group_name,
                'query_info': {
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'hours_back': hours_back,
                    'errors_only': errors_only,
                    'region': self.region,
                },
                'statistics': {
                    'total_events': 0,
                    'displayed_events': 0,
                    'error_count': 0,
                    'info_count': 0,
                },
                'logs': [],
                'status': 'error',
                'error_message': error_msg,
            }

    def get_multiple_functions_logs(
        self, function_names: list[str], hours_back: int = 4, errors_only: bool = True
    ) -> dict[str, Any]:
        """
        Recupera logs de múltiplas funções Lambda

        Args:
            function_names (List[str]): Lista de nomes das funções
            hours_back (int): Horas atrás para buscar logs
            errors_only (bool): Se deve filtrar apenas erros

        Returns:
            Dict estruturado com logs de todas as funções
        """
        print(f"🚀 Iniciando coleta de logs para {len(function_names)} função(ões)")
        print(f"📅 Período: últimas {hours_back} horas")
        print(f"🔍 Filtro: {'Apenas erros' if errors_only else 'Todos os logs'}")
        print("=" * 80)

        results = {}
        summary = {
            'total_functions': len(function_names),
            'successful_functions': 0,
            'failed_functions': 0,
            'total_events': 0,
            'total_errors': 0,
        }

        for function_name in function_names:
            function_result = self.get_function_logs(
                function_name=function_name,
                hours_back=hours_back,
                errors_only=errors_only,
            )

            results[function_name] = function_result

            # Atualizar estatísticas gerais
            if function_result['status'] == 'success':
                summary['successful_functions'] += 1
                summary['total_events'] += function_result['statistics']['total_events']
                summary['total_errors'] += function_result['statistics']['error_count']
            else:
                summary['failed_functions'] += 1

        # Estrutura final do JSON
        output = {
            'metadata': {
                'generated_at': datetime.now(tz=UTC).isoformat(),
                'query_parameters': {
                    'function_names': function_names,
                    'hours_back': hours_back,
                    'errors_only': errors_only,
                    'region': self.region,
                },
                'summary': summary,
            },
            'functions': results,
        }

        return output

    def save_to_json(self, data: dict[str, Any], filename: str | None = None) -> str:
        """
        Salva dados em arquivo JSON

        Args:
            data (Dict): Dados para salvar
            filename (str, opcional): Nome do arquivo

        Returns:
            str: Nome do arquivo salvo
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"lambda_logs_multi_{timestamp}.json"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"💾 Logs salvos em: {filename}")
            return filename

        except Exception as e:
            print(f"❌ Erro ao salvar arquivo: {e}")
            return ""

    def print_summary(self, data: dict[str, Any]) -> None:
        """
        Exibe resumo formatado dos dados coletados

        Args:
            data (Dict): Dados dos logs coletados
        """
        metadata = data['metadata']
        summary = metadata['summary']

        print("\n" + "=" * 80)
        print("📊 RESUMO GERAL")
        print("=" * 80)
        print(f"🕐 Gerado em: {metadata['generated_at']}")
        print(f"📋 Funções processadas: {summary['total_functions']}")
        print(f"✅ Sucessos: {summary['successful_functions']}")
        print(f"❌ Falhas: {summary['failed_functions']}")
        print(f"📝 Total de eventos: {summary['total_events']}")
        print(f"🚨 Total de erros: {summary['total_errors']}")

        print("\n📋 DETALHES POR FUNÇÃO:")
        print("-" * 80)

        for func_name, func_data in data['functions'].items():
            status_icon = "✅" if func_data['status'] == 'success' else "❌"
            stats = func_data['statistics']

            print(f"{status_icon} {func_name}:")
            print(f"   • Eventos totais: {stats['total_events']}")
            print(f"   • Eventos exibidos: {stats['displayed_events']}")
            print(f"   • Erros: {stats['error_count']}")

            if func_data['status'] == 'error':
                print(f"   • Erro: {func_data.get('error_message', 'Desconhecido')}")

            print()


class InteractiveCLI:
    """
    Interface CLI interativa para configuração de parâmetros
    """

    def __init__(self):
        # Usar o utilitário de configuração para carregar funções
        self.lambda_config = LambdaConfig()
        self.default_functions = self.lambda_config.get_default_functions()

    def get_time_range(self) -> int:
        """Solicita intervalo de tempo ao usuário"""
        print("\n⏰ SELEÇÃO DE INTERVALO DE TEMPO")
        print("1. 1 hora")
        print("2. 4 horas (recomendado)")
        print("3. 12 horas")
        print("4. 24 horas")
        print("5. Personalizado")

        while True:
            try:
                choice = input("\nEscolha uma opção (1-5): ").strip()

                if choice == "1":
                    return 1
                elif choice == "2":
                    return 4
                elif choice == "3":
                    return 12
                elif choice == "4":
                    return 24
                elif choice == "5":
                    hours = int(input("Digite o número de horas: "))
                    if hours > 0:
                        return hours
                    else:
                        print("❌ Número de horas deve ser positivo")
                else:
                    print("❌ Opção inválida. Escolha entre 1-5.")

            except ValueError:
                print("❌ Entrada inválida. Digite um número.")
            except KeyboardInterrupt:
                print("\n\n👋 Operação cancelada pelo usuário.")
                sys.exit(0)

    def get_error_filter(self) -> bool:
        """Solicita configuração de filtro de erros"""
        print("\n🔍 FILTRO DE LOGS")
        print("1. Apenas erros (recomendado)")
        print("2. Todos os logs")

        while True:
            try:
                choice = input("\nEscolha uma opção (1-2): ").strip()

                if choice == "1":
                    return True
                elif choice == "2":
                    return False
                else:
                    print("❌ Opção inválida. Escolha 1 ou 2.")

            except KeyboardInterrupt:
                print("\n\n👋 Operação cancelada pelo usuário.")
                sys.exit(0)

    def get_output_format(self) -> str:
        """Solicita formato de saída"""
        print("\n💾 FORMATO DE SAÍDA")
        print("1. JSON (recomendado)")
        print("2. Apenas console")

        while True:
            try:
                choice = input("\nEscolha uma opção (1-2): ").strip()

                if choice == "1":
                    return "json"
                elif choice == "2":
                    return "console"
                else:
                    print("❌ Opção inválida. Escolha 1 ou 2.")

            except KeyboardInterrupt:
                print("\n\n👋 Operação cancelada pelo usuário.")
                sys.exit(0)

    def get_lambda_functions(self) -> list[str]:
        """Solicita seleção de funções Lambda"""
        print("\n🔧 SELEÇÃO DE FUNÇÕES LAMBDA")
        print("1. Usar funções padrão (context, kamis, validator)")
        print("2. Selecionar funções específicas")
        print("3. Inserir lista personalizada")

        while True:
            try:
                choice = input("\nEscolha uma opção (1-3): ").strip()

                if choice == "1":
                    return self.default_functions
                elif choice == "2":
                    return self._select_specific_functions()
                elif choice == "3":
                    return self._get_custom_functions()
                else:
                    print("❌ Opção inválida. Escolha entre 1-3.")

            except KeyboardInterrupt:
                print("\n\n👋 Operação cancelada pelo usuário.")
                sys.exit(0)

    def _select_specific_functions(self) -> list[str]:
        """Permite seleção específica de funções"""
        # Usar o utilitário de configuração para obter todas as funções disponíveis
        available_functions = self.lambda_config.get_all_available_functions()

        print("\nFunções disponíveis:")
        for i, func in enumerate(available_functions, 1):
            print(f"{i}. {func}")

        selected = []
        print("\nDigite os números das funções desejadas (separados por vírgula):")
        print("Exemplo: 1,2,3")

        while True:
            try:
                choices = input("Sua escolha: ").strip().split(',')

                for choice in choices:
                    idx = int(choice.strip()) - 1
                    if 0 <= idx < len(available_functions):
                        func_name = available_functions[idx]
                        if func_name not in selected:
                            selected.append(func_name)

                if selected:
                    return selected
                else:
                    print("❌ Nenhuma função válida selecionada.")

            except ValueError:
                print("❌ Formato inválido. Use números separados por vírgula.")

    def _get_custom_functions(self) -> list[str]:
        """Permite inserção de lista personalizada"""
        print("\nDigite os nomes das funções Lambda (separados por vírgula):")
        print("Exemplo: minha-funcao-1,minha-funcao-2,outra-funcao")

        while True:
            try:
                functions_input = input("Funções: ").strip()

                if not functions_input:
                    print("❌ Lista não pode estar vazia.")
                    continue

                functions = [f.strip() for f in functions_input.split(',')]
                functions = [f for f in functions if f]  # Remove strings vazias

                if functions:
                    return functions
                else:
                    print("❌ Nenhuma função válida encontrada.")

            except KeyboardInterrupt:
                print("\n\n👋 Operação cancelada pelo usuário.")
                sys.exit(0)

    def run_interactive_mode(self) -> dict[str, Any]:
        """Executa modo interativo completo"""
        print("🚀 LAMBDA WATCHER V2 - MODO INTERATIVO")
        print("=" * 80)

        # Coletar configurações
        hours_back = self.get_time_range()
        errors_only = self.get_error_filter()
        output_format = self.get_output_format()
        function_names = self.get_lambda_functions()

        return {
            'hours_back': hours_back,
            'errors_only': errors_only,
            'output_format': output_format,
            'function_names': function_names,
        }


def main():
    """Função principal com suporte a CLI e modo interativo"""
    parser = argparse.ArgumentParser(
        description='Lambda Watcher V2 - Monitoramento avançado de logs Lambda',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:

  # Modo padrão (4h, apenas erros, JSON, funções padrão)
  python lambda_watcher_v2.py --default

  # Modo interativo
  python lambda_watcher_v2.py

  # Modo CLI com parâmetros específicos
  python lambda_watcher_v2.py --functions context,kamis --hours 8 --all-logs

  # Salvar com nome específico
  python lambda_watcher_v2.py --default --output meus_logs.json
        """,
    )

    parser.add_argument(
        '--default',
        action='store_true',
        help='Usar configurações padrão (4h, apenas erros, JSON, funções padrão)',
    )

    parser.add_argument(
        '--functions',
        type=str,
        help='Lista de funções Lambda separadas por vírgula (ex: context,kamis,validator)',
    )

    parser.add_argument(
        '--hours', type=int, default=4, help='Horas atrás para buscar logs (padrão: 4)'
    )

    parser.add_argument(
        '--all-logs',
        action='store_true',
        help='Incluir todos os logs (não apenas erros)',
    )

    parser.add_argument(
        '--console-only',
        action='store_true',
        help='Exibir apenas no console (não salvar JSON)',
    )

    parser.add_argument('--output', type=str, help='Nome do arquivo de saída JSON')

    parser.add_argument(
        '--region', type=str, default='us-east-1', help='Região AWS (padrão: us-east-1)'
    )

    args = parser.parse_args()

    # Verificar credenciais AWS
    try:
        session = boto3.Session()
        credentials = session.get_credentials()
        if not credentials:
            print("❌ Credenciais AWS não encontradas.")
            print("💡 Configure com: aws configure ou arquivo .env")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Erro com credenciais AWS: {str(e)}")
        sys.exit(1)

    # Inicializar watcher
    watcher = MultiLambdaWatcher(region=args.region)

    # Usar o utilitário de configuração para carregar funções padrão
    lambda_config = LambdaConfig()
    default_functions = lambda_config.get_default_functions()

    # Determinar configurações
    if args.default:
        # Modo padrão
        config = {
            'hours_back': 4,
            'errors_only': True,
            'output_format': 'json',
            'function_names': default_functions,
        }
        print("🚀 LAMBDA WATCHER V2 - MODO PADRÃO")
        print("=" * 80)

    elif any([args.functions, args.hours != 4, args.all_logs, args.console_only]):
        # Modo CLI com parâmetros
        function_names = (
            args.functions.split(',') if args.functions else default_functions
        )
        function_names = [f.strip() for f in function_names]

        config = {
            'hours_back': args.hours,
            'errors_only': not args.all_logs,
            'output_format': 'console' if args.console_only else 'json',
            'function_names': function_names,
        }
        print("🚀 LAMBDA WATCHER V2 - MODO CLI")
        print("=" * 80)

    else:
        # Modo interativo
        cli = InteractiveCLI()
        config = cli.run_interactive_mode()

    # Executar coleta de logs
    try:
        print("\n🔄 Coletando logs...")

        results = watcher.get_multiple_functions_logs(
            function_names=config['function_names'],
            hours_back=config['hours_back'],
            errors_only=config['errors_only'],
        )

        # Exibir resumo
        watcher.print_summary(results)

        # Salvar em JSON se solicitado
        if config['output_format'] == 'json':
            filename = args.output if args.output else None
            saved_file = watcher.save_to_json(results, filename)

            if saved_file:
                print(f"\n✅ Processo concluído! Arquivo salvo: {saved_file}")
            else:
                print("\n⚠️ Processo concluído, mas houve erro ao salvar arquivo.")
        else:
            print("\n✅ Processo concluído!")

    except KeyboardInterrupt:
        print("\n\n👋 Operação interrompida pelo usuário.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erro durante execução: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
