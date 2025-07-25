#!/usr/bin/env python3
"""
Lambda Functions Lister - Lista todas as funções Lambda disponíveis na conta AWS
Fornece informações detalhadas sobre configuração, runtime, tamanho e última modificação
"""

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from typing import Any

import boto3
from dotenv import load_dotenv

from config_utils import ConfigManager

load_dotenv()


class LambdaFunctionLister:
    """
    Classe principal para listar e analisar funções Lambda
    """

    def __init__(self, region: str = 'us-east-1'):
        """
        Inicializa o lister com configuração AWS

        Args:
            region (str): Região AWS (padrão: us-east-1)
        """
        self.region = region
        self.session = boto3.Session(
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_DEFAULT_REGION", region),
        )
        self.lambda_client = self.session.client('lambda')
        self.config_manager = ConfigManager()

    def list_all_functions(self, include_details: bool = True) -> dict[str, Any]:
        """
        Lista todas as funções Lambda disponíveis na conta

        Args:
            include_details (bool): Se deve incluir detalhes completos de cada função

        Returns:
            Dict com informações estruturadas das funções
        """
        print("🔍 Buscando funções Lambda na conta...")

        try:
            functions = []
            paginator = self.lambda_client.get_paginator('list_functions')

            # Usar paginação para listar todas as funções
            for page in paginator.paginate():
                for function in page['Functions']:
                    function_info = self._process_function_info(
                        function, include_details
                    )
                    functions.append(function_info)

            # Ordenar por nome da função
            functions.sort(key=lambda x: x['function_name'].lower())

            # Calcular estatísticas
            statistics = self._calculate_statistics(functions)

            return {
                'metadata': {
                    'generated_at': datetime.now(tz=UTC).isoformat(),
                    'region': self.region,
                    'account_id': self.config_manager.aws_config.account_id,
                    'include_details': include_details,
                },
                'statistics': statistics,
                'functions': functions,
                'status': 'success',
            }

        except Exception as e:
            error_msg = str(e)
            print(f"❌ Erro ao listar funções Lambda: {error_msg}")

            return {
                'metadata': {
                    'generated_at': datetime.now(tz=UTC).isoformat(),
                    'region': self.region,
                    'account_id': self.config_manager.aws_config.account_id,
                    'include_details': include_details,
                },
                'statistics': {
                    'total_functions': 0,
                    'by_runtime': {},
                    'by_architecture': {},
                    'total_code_size': 0,
                    'average_timeout': 0,
                    'average_memory': 0,
                },
                'functions': [],
                'status': 'error',
                'error_message': error_msg,
            }

    def _process_function_info(
        self, function: dict[str, Any], include_details: bool
    ) -> dict[str, Any]:
        """
        Processa informações de uma função Lambda

        Args:
            function (Dict): Dados brutos da função do boto3
            include_details (bool): Se deve incluir detalhes completos

        Returns:
            Dict com informações processadas da função
        """
        # Informações básicas sempre incluídas
        function_info = {
            'function_name': function['FunctionName'],
            'runtime': function.get('Runtime', 'N/A'),
            'handler': function.get('Handler', 'N/A'),
            'code_size': function.get('CodeSize', 0),
            'last_modified': function.get('LastModified', ''),
            'version': function.get('Version', '$LATEST'),
            'state': function.get('State', 'Active'),
            'architecture': (
                function.get('Architectures', ['x86_64'])[0]
                if function.get('Architectures')
                else 'x86_64'
            ),
        }

        # Detalhes adicionais se solicitado
        if include_details:
            function_info.update(
                {
                    'description': function.get('Description', ''),
                    'timeout': function.get('Timeout', 3),
                    'memory_size': function.get('MemorySize', 128),
                    'package_type': function.get('PackageType', 'Zip'),
                    'code_sha256': function.get('CodeSha256', ''),
                    'role': function.get('Role', ''),
                    'environment_variables': len(
                        function.get('Environment', {}).get('Variables', {})
                    ),
                    'layers': len(function.get('Layers', [])),
                    'vpc_config': (
                        {
                            'vpc_id': function.get('VpcConfig', {}).get('VpcId', ''),
                            'subnet_ids_count': len(
                                function.get('VpcConfig', {}).get('SubnetIds', [])
                            ),
                            'security_group_ids_count': len(
                                function.get('VpcConfig', {}).get(
                                    'SecurityGroupIds', []
                                )
                            ),
                        }
                        if function.get('VpcConfig', {}).get('VpcId')
                        else None
                    ),
                    'dead_letter_config': function.get('DeadLetterConfig', {}).get(
                        'TargetArn', ''
                    ),
                    'kms_key_arn': function.get('KMSKeyArn', ''),
                    'tracing_config': function.get('TracingConfig', {}).get(
                        'Mode', 'PassThrough'
                    ),
                    'revision_id': function.get('RevisionId', ''),
                    'file_system_configs': len(function.get('FileSystemConfigs', [])),
                    'image_config': function.get('ImageConfig', {}),
                    'ephemeral_storage': function.get('EphemeralStorage', {}).get(
                        'Size', 512
                    ),
                }
            )

        return function_info

    def _calculate_statistics(self, functions: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Calcula estatísticas das funções Lambda

        Args:
            functions (List[Dict]): Lista de funções processadas

        Returns:
            Dict com estatísticas calculadas
        """
        if not functions:
            return {
                'total_functions': 0,
                'by_runtime': {},
                'by_architecture': {},
                'by_state': {},
                'total_code_size': 0,
                'average_timeout': 0,
                'average_memory': 0,
            }

        # Contadores
        by_runtime = {}
        by_architecture = {}
        by_state = {}
        total_code_size = 0
        total_timeout = 0
        total_memory = 0
        functions_with_details = 0

        for func in functions:
            # Runtime
            runtime = func.get('runtime', 'N/A')
            by_runtime[runtime] = by_runtime.get(runtime, 0) + 1

            # Arquitetura
            arch = func.get('architecture', 'x86_64')
            by_architecture[arch] = by_architecture.get(arch, 0) + 1

            # Estado
            state = func.get('state', 'Active')
            by_state[state] = by_state.get(state, 0) + 1

            # Tamanho do código
            total_code_size += func.get('code_size', 0)

            # Timeout e memória (apenas se detalhes estão incluídos)
            if 'timeout' in func and 'memory_size' in func:
                total_timeout += func['timeout']
                total_memory += func['memory_size']
                functions_with_details += 1

        return {
            'total_functions': len(functions),
            'by_runtime': dict(sorted(by_runtime.items())),
            'by_architecture': dict(sorted(by_architecture.items())),
            'by_state': dict(sorted(by_state.items())),
            'total_code_size': total_code_size,
            'total_code_size_mb': round(total_code_size / (1024 * 1024), 2),
            'average_timeout': (
                round(total_timeout / functions_with_details, 1)
                if functions_with_details > 0
                else 0
            ),
            'average_memory': (
                round(total_memory / functions_with_details, 1)
                if functions_with_details > 0
                else 0
            ),
        }

    def filter_functions(
        self, data: dict[str, Any], filters: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Aplica filtros aos dados das funções

        Args:
            data (Dict): Dados originais das funções
            filters (Dict): Filtros a serem aplicados

        Returns:
            Dict com dados filtrados
        """
        if data['status'] != 'success':
            return data

        filtered_functions = data['functions'].copy()

        # Filtro por runtime
        if filters.get('runtime'):
            runtime_filter = filters['runtime'].lower()
            filtered_functions = [
                f
                for f in filtered_functions
                if runtime_filter in f.get('runtime', '').lower()
            ]

        # Filtro por nome (substring)
        if filters.get('name'):
            name_filter = filters['name'].lower()
            filtered_functions = [
                f
                for f in filtered_functions
                if name_filter in f.get('function_name', '').lower()
            ]

        # Filtro por estado
        if filters.get('state'):
            state_filter = filters['state']
            filtered_functions = [
                f
                for f in filtered_functions
                if f.get('state', '').lower() == state_filter.lower()
            ]

        # Filtro por arquitetura
        if filters.get('architecture'):
            arch_filter = filters['architecture']
            filtered_functions = [
                f
                for f in filtered_functions
                if f.get('architecture', '').lower() == arch_filter.lower()
            ]

        # Recalcular estatísticas para dados filtrados
        filtered_statistics = self._calculate_statistics(filtered_functions)

        # Criar nova estrutura com dados filtrados
        filtered_data = data.copy()
        filtered_data['functions'] = filtered_functions
        filtered_data['statistics'] = filtered_statistics
        filtered_data['metadata']['filters_applied'] = filters
        filtered_data['metadata']['original_count'] = data['statistics'][
            'total_functions'
        ]
        filtered_data['metadata']['filtered_count'] = len(filtered_functions)

        return filtered_data

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
            filename = f"lambda_functions_{timestamp}.json"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"💾 Lista de funções salva em: {filename}")
            return filename

        except Exception as e:
            print(f"❌ Erro ao salvar arquivo: {e}")
            return ""

    def print_summary(self, data: dict[str, Any]) -> None:
        """
        Exibe resumo formatado dos dados coletados

        Args:
            data (Dict): Dados das funções coletadas
        """
        if data['status'] != 'success':
            print(f"❌ Erro: {data.get('error_message', 'Erro desconhecido')}")
            return

        metadata = data['metadata']
        statistics = data['statistics']

        print("\n" + "=" * 80)
        print("📊 RESUMO DAS FUNÇÕES LAMBDA")
        print("=" * 80)
        print(f"🕐 Gerado em: {metadata['generated_at']}")
        print(f"🌍 Região: {metadata['region']}")
        print(f"🏢 Account ID: {metadata['account_id']}")

        if metadata.get('filters_applied'):
            print(f"🔍 Filtros aplicados: {metadata['filters_applied']}")
            print(f"📊 Funções originais: {metadata['original_count']}")
            print(f"📊 Funções filtradas: {metadata['filtered_count']}")

        print("\n📋 ESTATÍSTICAS GERAIS:")
        print(f"   • Total de funções: {statistics['total_functions']}")
        print(f"   • Tamanho total do código: {statistics['total_code_size_mb']} MB")

        if statistics['average_timeout'] > 0:
            print(f"   • Timeout médio: {statistics['average_timeout']}s")
            print(f"   • Memória média: {statistics['average_memory']} MB")

        print("\n🔧 POR RUNTIME:")
        for runtime, count in statistics['by_runtime'].items():
            print(f"   • {runtime}: {count}")

        print("\n🏗️ POR ARQUITETURA:")
        for arch, count in statistics['by_architecture'].items():
            print(f"   • {arch}: {count}")

        print("\n📊 POR ESTADO:")
        for state, count in statistics['by_state'].items():
            print(f"   • {state}: {count}")

        print("\n📋 LISTA DE FUNÇÕES:")
        print("-" * 80)

        for func in data['functions']:
            state_icon = "✅" if func.get('state') == 'Active' else "⚠️"
            print(f"{state_icon} {func['function_name']}")
            print(f"   • Runtime: {func['runtime']}")
            print(f"   • Tamanho: {round(func['code_size'] / (1024 * 1024), 2)} MB")
            print(f"   • Última modificação: {func['last_modified']}")

            if metadata.get('include_details') and 'timeout' in func:
                print(
                    f"   • Timeout: {func['timeout']}s | Memória: {func['memory_size']} MB"
                )

            print()

        print("=" * 80)


def main():
    """Função principal com suporte a CLI"""
    parser = argparse.ArgumentParser(
        description='Lambda Functions Lister - Lista funções Lambda da conta AWS',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:

  # Listar todas as funções com detalhes completos
  python list_lambda_functions.py

  # Listar apenas informações básicas
  python list_lambda_functions.py --basic

  # Filtrar por runtime Python
  python list_lambda_functions.py --runtime python

  # Filtrar por nome contendo "api"
  python list_lambda_functions.py --name api

  # Salvar com nome específico
  python list_lambda_functions.py --output minhas_funcoes.json

  # Apenas exibir no console
  python list_lambda_functions.py --console-only
        """,
    )

    parser.add_argument(
        '--basic',
        action='store_true',
        help='Exibir apenas informações básicas (mais rápido)',
    )

    parser.add_argument(
        '--runtime', type=str, help='Filtrar por runtime (ex: python, nodejs, java)'
    )

    parser.add_argument(
        '--name', type=str, help='Filtrar por nome da função (substring)'
    )

    parser.add_argument(
        '--state',
        type=str,
        choices=['Active', 'Pending', 'Inactive', 'Failed'],
        help='Filtrar por estado da função',
    )

    parser.add_argument(
        '--architecture',
        type=str,
        choices=['x86_64', 'arm64'],
        help='Filtrar por arquitetura',
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

    # Inicializar lister
    try:
        lister = LambdaFunctionLister(region=args.region)

        print("🚀 LAMBDA FUNCTIONS LISTER")
        print("=" * 80)

        # Listar funções
        include_details = not args.basic
        print(
            f"🔄 Coletando {'informações detalhadas' if include_details else 'informações básicas'}..."
        )

        results = lister.list_all_functions(include_details=include_details)

        if results['status'] != 'success':
            print(
                f"❌ Erro ao listar funções: {results.get('error_message', 'Erro desconhecido')}"
            )
            sys.exit(1)

        # Aplicar filtros se especificados
        filters = {}
        if args.runtime:
            filters['runtime'] = args.runtime
        if args.name:
            filters['name'] = args.name
        if args.state:
            filters['state'] = args.state
        if args.architecture:
            filters['architecture'] = args.architecture

        if filters:
            print(f"🔍 Aplicando filtros: {filters}")
            results = lister.filter_functions(results, filters)

        # Exibir resumo
        lister.print_summary(results)

        # Salvar em JSON se solicitado
        if not args.console_only:
            filename = args.output if args.output else None
            saved_file = lister.save_to_json(results, filename)

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
