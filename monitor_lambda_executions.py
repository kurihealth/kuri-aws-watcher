#!/usr/bin/env python3
"""
Monitor de Execuções Lambda em Tempo Real
Monitora execuções ativas, métricas e status das funções Lambda em tempo real
"""

import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import boto3
from dotenv import load_dotenv

from config_utils import ConfigManager

load_dotenv()


class LambdaExecutionMonitor:
    """
    Classe principal para monitoramento de execuções Lambda em tempo real
    """

    def __init__(self, region: str = 'us-east-1'):
        """
        Inicializa o monitor com configuração AWS

        Args:
            region (str): Região AWS (padrão: us-east-1)
        """
        self.region = region
        self.session = boto3.Session(
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_DEFAULT_REGION", region),
        )

        # Clientes AWS
        self.cloudwatch = self.session.client('cloudwatch')
        self.lambda_client = self.session.client('lambda')

        # Configuração
        self.config_manager = ConfigManager()
        self.lambda_config = self.config_manager.lambda_config

        # Configurações de monitoramento
        self.update_interval = int(os.getenv("LAMBDA_MONITOR_INTERVAL_SECONDS", "10"))
        self.metric_period = int(os.getenv("LAMBDA_METRIC_PERIOD_MINUTES", "5"))

        # Cache para comparação
        self.previous_metrics = {}

    def get_function_metrics(self, function_name: str) -> dict[str, Any]:
        """
        Coleta métricas de uma função Lambda específica

        Args:
            function_name (str): Nome da função Lambda

        Returns:
            Dict com métricas da função
        """
        end_time = datetime.now(tz=UTC)
        start_time = end_time - timedelta(minutes=self.metric_period)

        metrics = {
            'function_name': function_name,
            'timestamp': end_time.isoformat(),
            'status': 'unknown',
            'invocations': 0,
            'duration_avg': 0.0,
            'errors': 0,
            'throttles': 0,
            'concurrent_executions': 0,
            'success_rate': 0.0,
            'is_executing': False,
            'error_rate': 0.0,
        }

        try:
            # Verificar se a função existe
            try:
                self.lambda_client.get_function(FunctionName=function_name)
                metrics['status'] = 'active'
            except self.lambda_client.exceptions.ResourceNotFoundException:
                metrics['status'] = 'not_found'
                return metrics
            except Exception:
                metrics['status'] = 'error'
                return metrics

            # Coletar métricas do CloudWatch
            metric_queries = [
                {
                    'Id': 'invocations',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/Lambda',
                            'MetricName': 'Invocations',
                            'Dimensions': [
                                {'Name': 'FunctionName', 'Value': function_name}
                            ],
                        },
                        'Period': 60,
                        'Stat': 'Sum',
                    },
                },
                {
                    'Id': 'duration',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/Lambda',
                            'MetricName': 'Duration',
                            'Dimensions': [
                                {'Name': 'FunctionName', 'Value': function_name}
                            ],
                        },
                        'Period': 60,
                        'Stat': 'Average',
                    },
                },
                {
                    'Id': 'errors',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/Lambda',
                            'MetricName': 'Errors',
                            'Dimensions': [
                                {'Name': 'FunctionName', 'Value': function_name}
                            ],
                        },
                        'Period': 60,
                        'Stat': 'Sum',
                    },
                },
                {
                    'Id': 'throttles',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/Lambda',
                            'MetricName': 'Throttles',
                            'Dimensions': [
                                {'Name': 'FunctionName', 'Value': function_name}
                            ],
                        },
                        'Period': 60,
                        'Stat': 'Sum',
                    },
                },
                {
                    'Id': 'concurrent',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/Lambda',
                            'MetricName': 'ConcurrentExecutions',
                            'Dimensions': [
                                {'Name': 'FunctionName', 'Value': function_name}
                            ],
                        },
                        'Period': 60,
                        'Stat': 'Maximum',
                    },
                },
            ]

            # Executar consulta de métricas
            response = self.cloudwatch.get_metric_data(
                MetricDataQueries=metric_queries, StartTime=start_time, EndTime=end_time
            )

            # Processar resultados
            for result in response['MetricDataResults']:
                if result['Values']:
                    latest_value = result['Values'][-1]

                    if result['Id'] == 'invocations':
                        metrics['invocations'] = int(latest_value)
                    elif result['Id'] == 'duration':
                        metrics['duration_avg'] = round(latest_value, 2)
                    elif result['Id'] == 'errors':
                        metrics['errors'] = int(latest_value)
                    elif result['Id'] == 'throttles':
                        metrics['throttles'] = int(latest_value)
                    elif result['Id'] == 'concurrent':
                        metrics['concurrent_executions'] = int(latest_value)

            # Calcular métricas derivadas
            if metrics['invocations'] > 0:
                metrics['success_rate'] = round(
                    (
                        (metrics['invocations'] - metrics['errors'])
                        / metrics['invocations']
                    )
                    * 100,
                    1,
                )
                metrics['error_rate'] = round(
                    (metrics['errors'] / metrics['invocations']) * 100, 1
                )

            # Detectar se está executando (baseado em execuções concorrentes)
            metrics['is_executing'] = metrics['concurrent_executions'] > 0

            return metrics

        except Exception as e:
            metrics['status'] = 'error'
            metrics['error_message'] = str(e)
            return metrics

    def get_all_functions_metrics(self) -> dict[str, Any]:
        """
        Coleta métricas de todas as funções configuradas

        Returns:
            Dict com métricas de todas as funções
        """
        functions = self.lambda_config.get_all_available_functions()

        results = {
            'timestamp': datetime.now(tz=UTC).isoformat(),
            'total_functions': len(functions),
            'monitoring_period_minutes': self.metric_period,
            'functions': {},
            'summary': {
                'active_functions': 0,
                'executing_functions': 0,
                'total_invocations': 0,
                'total_errors': 0,
                'functions_with_errors': 0,
                'functions_with_throttles': 0,
            },
        }

        for function_name in functions:
            metrics = self.get_function_metrics(function_name)
            results['functions'][function_name] = metrics

            # Atualizar resumo
            if metrics['status'] == 'active':
                results['summary']['active_functions'] += 1

            if metrics['is_executing']:
                results['summary']['executing_functions'] += 1

            results['summary']['total_invocations'] += metrics['invocations']
            results['summary']['total_errors'] += metrics['errors']

            if metrics['errors'] > 0:
                results['summary']['functions_with_errors'] += 1

            if metrics['throttles'] > 0:
                results['summary']['functions_with_throttles'] += 1

        return results

    def print_monitoring_display(self, data: dict[str, Any]) -> None:
        """
        Exibe dados de monitoramento formatados no console

        Args:
            data (Dict): Dados das métricas coletadas
        """
        # Limpar tela (funciona no Linux/Mac e Windows)
        os.system(command='clear' if os.name == 'posix' else 'cls')

        # Cabeçalho
        print("=" * 100)
        print("🚀 MONITOR DE EXECUÇÕES LAMBDA EM TEMPO REAL")
        print("=" * 100)
        print(f"🕐 Atualização: {datetime.now().strftime('%H:%M:%S')}")
        print(f"📊 Período de métricas: {self.metric_period} minutos")
        print(f"🔄 Próxima atualização em: {self.update_interval} segundos")
        print()

        # Resumo geral
        summary = data['summary']
        print("📋 RESUMO GERAL:")
        print(
            f"   • Funções ativas: {summary['active_functions']}/{data['total_functions']}"
        )
        print(f"   • Executando agora: {summary['executing_functions']} ⚡")
        print(f"   • Total invocações: {summary['total_invocations']}")
        print(f"   • Total erros: {summary['total_errors']}")
        print(f"   • Funções com erro: {summary['functions_with_errors']}")
        print(f"   • Funções com throttle: {summary['functions_with_throttles']}")
        print()

        # Separar funções por status
        executing_functions = []
        active_functions = []
        inactive_functions = []

        for func_name, metrics in data['functions'].items():
            if metrics['is_executing']:
                executing_functions.append((func_name, metrics))
            elif metrics['status'] == 'active':
                active_functions.append((func_name, metrics))
            else:
                inactive_functions.append((func_name, metrics))

        # Mostrar funções executando
        if executing_functions:
            print("⚡ EXECUTANDO AGORA:")
            print("-" * 80)
            for func_name, metrics in executing_functions:
                status_icon = self._get_status_icon(metrics)
                concurrent = metrics['concurrent_executions']
                duration = metrics['duration_avg']

                print(f"{status_icon} {func_name}")
                print(f"   🔥 Execuções simultâneas: {concurrent}")
                print(f"   ⏱️  Duração média: {duration}ms")
                print(
                    f"   📈 Invocações: {metrics['invocations']} | Erros: {metrics['errors']}"
                )
                if metrics['success_rate'] > 0:
                    print(f"   ✅ Taxa sucesso: {metrics['success_rate']}%")
                print()

        # Mostrar funções ativas (mas não executando)
        if active_functions:
            print("✅ ATIVAS (sem execução atual):")
            print("-" * 80)
            for func_name, metrics in active_functions:
                status_icon = self._get_status_icon(metrics)

                print(f"{status_icon} {func_name}")
                print(
                    f"   📊 Invocações: {metrics['invocations']} | Erros: {metrics['errors']} | Throttles: {metrics['throttles']}"
                )
                if metrics['invocations'] > 0:
                    print(
                        f"   📈 Taxa sucesso: {metrics['success_rate']}% | Duração média: {metrics['duration_avg']}ms"
                    )
                print()

        # Mostrar funções inativas ou com erro
        if inactive_functions:
            print("⚠️  INATIVAS/ERRO:")
            print("-" * 80)
            for func_name, metrics in inactive_functions:
                status_icon = "❌" if metrics['status'] == 'not_found' else "🔧"
                status_text = (
                    "Não encontrada" if metrics['status'] == 'not_found' else "Erro"
                )

                print(f"{status_icon} {func_name} - {status_text}")
                if 'error_message' in metrics:
                    print(f"   ⚠️  {metrics['error_message']}")
                print()

        print("=" * 100)
        print("Pressione Ctrl+C para sair")

    def _get_status_icon(self, metrics: dict[str, Any]) -> str:
        """
        Retorna ícone baseado no status da função

        Args:
            metrics (Dict): Métricas da função

        Returns:
            str: Ícone apropriado
        """
        if metrics['is_executing']:
            return "🔥"
        elif metrics['errors'] > 0:
            return "⚠️"
        elif metrics['throttles'] > 0:
            return "🚫"
        elif metrics['invocations'] > 0:
            return "✅"
        else:
            return "💤"

    def save_monitoring_log(self, data: dict[str, Any]) -> None:
        """
        Salva dados de monitoramento em arquivo JSON

        Args:
            data (Dict): Dados para salvar
        """
        save_to_log = os.getenv("SAVE_TO_LOG", "false").lower() == "true"

        if not save_to_log:
            return

        log_file_path = os.getenv("LOG_FILE_PATH", "lambda_monitoring.log")

        try:
            # Preparar entrada de log
            log_entry = {
                'timestamp': data['timestamp'],
                'summary': data['summary'],
                'executing_functions': [
                    name
                    for name, metrics in data['functions'].items()
                    if metrics['is_executing']
                ],
            }

            # Adicionar ao arquivo de log
            with open(log_file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

        except Exception as e:
            print(f"⚠️  Erro ao salvar log: {e}")

    def start_monitoring(self) -> None:
        """
        Inicia o monitoramento contínuo das execuções Lambda
        """
        print("🚀 Iniciando monitor de execuções Lambda...")
        print(f"🔄 Intervalo de atualização: {self.update_interval} segundos")
        print(f"📊 Período de métricas: {self.metric_period} minutos")
        print()

        # Validar configurações
        validation = self.config_manager.validate_all_configs()
        if not validation['valid']:
            print("❌ Erro nas configurações:")
            for error in validation['aws']['errors']:
                print(f"   • {error}")
            sys.exit(1)

        functions = self.lambda_config.get_all_available_functions()
        print(f"📋 Monitorando {len(functions)} funções: {', '.join(functions)}")
        print("Pressione Ctrl+C para sair\n")

        try:
            while True:
                # Coletar métricas
                metrics_data = self.get_all_functions_metrics()

                # Exibir no console
                self.print_monitoring_display(metrics_data)

                # Salvar log se configurado
                self.save_monitoring_log(metrics_data)

                # Aguardar próxima atualização
                time.sleep(self.update_interval)

        except KeyboardInterrupt:
            print("\n\n👋 Monitor interrompido pelo usuário.")
            print("✅ Sessão de monitoramento finalizada.")
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ Erro durante monitoramento: {str(e)}")
            sys.exit(1)


def main():
    """Função principal com suporte a argumentos CLI"""
    parser = argparse.ArgumentParser(
        description='Monitor de Execuções Lambda em Tempo Real - Mostra quais funções estão executando no momento',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:

  # Monitoramento padrão (todas as funções configuradas)
  python monitor_lambda_executions.py

  # Configurar intervalo personalizado (30 segundos)
  python monitor_lambda_executions.py --interval 30

  # Configurar período de métricas (10 minutos)
  python monitor_lambda_executions.py --period 10

  # Habilitar salvamento em log
  python monitor_lambda_executions.py --save-log

  # Combinar opções
  python monitor_lambda_executions.py --interval 15 --period 5 --save-log
        """,
    )

    parser.add_argument(
        '--interval',
        type=int,
        help=f'Intervalo de atualização em segundos (padrão: {os.getenv("LAMBDA_MONITOR_INTERVAL_SECONDS", "10")})',
    )

    parser.add_argument(
        '--period',
        type=int,
        help=f'Período de métricas em minutos (padrão: {os.getenv("LAMBDA_METRIC_PERIOD_MINUTES", "5")})',
    )

    parser.add_argument(
        '--region',
        type=str,
        help=f'Região AWS (padrão: {os.getenv("AWS_DEFAULT_REGION", "us-east-1")})',
    )

    parser.add_argument(
        '--save-log',
        action='store_true',
        help='Habilitar salvamento em arquivo de log (sobrescreve SAVE_TO_LOG do .env)',
    )

    parser.add_argument(
        '--log-file',
        type=str,
        help=f'Caminho do arquivo de log (padrão: {os.getenv("LOG_FILE_PATH", "lambda_monitoring.log")})',
    )

    args = parser.parse_args()

    try:
        # Verificar credenciais AWS
        session = boto3.Session()
        credentials = session.get_credentials()
        if not credentials:
            print("❌ Credenciais AWS não encontradas.")
            print("💡 Configure com: aws configure ou arquivo .env")
            sys.exit(1)

        # Configurar parâmetros
        region = args.region or os.getenv("AWS_DEFAULT_REGION", "us-east-1")

        # Inicializar monitor
        monitor = LambdaExecutionMonitor(region=region)

        # Aplicar configurações CLI
        if args.interval:
            monitor.update_interval = args.interval

        if args.period:
            monitor.metric_period = args.period

        if args.save_log:
            os.environ["SAVE_TO_LOG"] = "true"

        if args.log_file:
            os.environ["LOG_FILE_PATH"] = args.log_file

        # Iniciar monitoramento
        monitor.start_monitoring()

    except KeyboardInterrupt:
        print("\n\n👋 Monitor interrompido pelo usuário.")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Erro ao inicializar monitor: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
