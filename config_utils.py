#!/usr/bin/env python3
"""
Utilitários de configuração para SQS Viewer & Lambda Watcher
Centraliza a lógica de construção de URLs e configurações usando variáveis de ambiente
"""

import os
from typing import List, Tuple, Dict, Any
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()


class AWSConfig:
    """Classe para gerenciar configurações AWS"""

    def __init__(self):
        self.account_id = os.getenv("AWS_ACCOUNT_ID")
        self.region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

        if not self.account_id:
            raise ValueError(
                "AWS_ACCOUNT_ID não está definido nas variáveis de ambiente"
            )

    def validate_config(self) -> Dict[str, Any]:
        """
        Valida as configurações AWS necessárias

        Returns:
            Dict com status da validação
        """
        validation_result = {"valid": True, "errors": [], "warnings": []}

        # Verificar configurações obrigatórias
        required_vars = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_ACCOUNT_ID"]

        for var in required_vars:
            if not os.getenv(var):
                validation_result["valid"] = False
                validation_result["errors"].append(
                    f"Variável obrigatória {var} não está definida"
                )

        # Verificar configurações opcionais
        if not os.getenv("AWS_DEFAULT_REGION"):
            validation_result["warnings"].append(
                "AWS_DEFAULT_REGION não definida, usando padrão: us-east-1"
            )

        return validation_result


class SQSConfig:
    """Classe para gerenciar configurações de filas SQS"""

    def __init__(self, aws_config: AWSConfig):
        self.aws_config = aws_config

    def get_dlq_list(self) -> List[Tuple[str, str]]:
        """
        Constrói a lista de DLQs usando variáveis de ambiente

        Returns:
            List[Tuple[str, str]]: Lista de tuplas (nome_amigavel, url_fila)
        """
        dlq_configs = [
            ("trigger dlq", os.getenv("SQS_TRIGGER_DLQ_NAME", "prd-trigger-atena-dlq")),
            ("context dlq", os.getenv("SQS_CONTEXT_DLQ_NAME", "prd-context-dlq")),
            ("validator dlq", os.getenv("SQS_VALIDATOR_DLQ_NAME", "prd-validator-dlq")),
            ("kamis dlq", os.getenv("SQS_KAMIS_DLQ_NAME", "prd-kamis-dlq")),
        ]

        return self._build_queue_urls(dlq_configs)

    def get_main_queue_list(self) -> List[Tuple[str, str]]:
        """
        Constrói a lista de filas principais usando variáveis de ambiente

        Returns:
            List[Tuple[str, str]]: Lista de tuplas (nome_amigavel, url_fila)
        """
        queue_configs = [
            (
                "trigger queue",
                os.getenv("SQS_TRIGGER_QUEUE_NAME", "prd-trigger-atena-queue"),
            ),
            ("context queue", os.getenv("SQS_CONTEXT_QUEUE_NAME", "prd-context-queue")),
            (
                "validator queue",
                os.getenv("SQS_VALIDATOR_QUEUE_NAME", "prd-validator-queue"),
            ),
            ("kamis queue", os.getenv("SQS_KAMIS_QUEUE_NAME", "prd-kamis-queue")),
        ]

        return self._build_queue_urls(queue_configs)

    def get_all_queue_list(self) -> List[Tuple[str, str]]:
        """
        Constrói a lista completa de filas (DLQs + principais)

        Returns:
            List[Tuple[str, str]]: Lista de tuplas (nome_amigavel, url_fila)
        """
        return self.get_dlq_list() + self.get_main_queue_list()

    def _build_queue_urls(
        self, queue_configs: List[Tuple[str, str]]
    ) -> List[Tuple[str, str]]:
        """
        Constrói URLs das filas a partir das configurações

        Args:
            queue_configs: Lista de tuplas (nome_amigavel, nome_fila)

        Returns:
            Lista de tuplas (nome_amigavel, url_fila)
        """
        queue_url_list = []

        for friendly_name, queue_name in queue_configs:
            if queue_name:  # Só adiciona se o nome da fila estiver definido
                url = f"https://sqs.{self.aws_config.region}.amazonaws.com/{self.aws_config.account_id}/{queue_name}"
                queue_url_list.append((friendly_name, url))

        return queue_url_list

    def get_queue_config_summary(self) -> Dict[str, Any]:
        """
        Retorna um resumo das configurações de filas

        Returns:
            Dict com resumo das configurações
        """
        dlqs = self.get_dlq_list()
        main_queues = self.get_main_queue_list()

        return {
            "total_queues": len(dlqs) + len(main_queues),
            "dlq_count": len(dlqs),
            "main_queue_count": len(main_queues),
            "dlqs": [name for name, _ in dlqs],
            "main_queues": [name for name, _ in main_queues],
            "region": self.aws_config.region,
            "account_id": self.aws_config.account_id,
        }


class LambdaConfig:
    """Classe para gerenciar configurações de funções Lambda"""

    def __init__(self):
        pass

    def get_default_functions(self) -> List[str]:
        """
        Retorna lista de funções Lambda padrão das variáveis de ambiente

        Returns:
            List[str]: Lista de nomes de funções
        """
        default_functions_env = os.getenv(
            "LAMBDA_DEFAULT_FUNCTIONS", "context,kamis,validator"
        )
        return [f.strip() for f in default_functions_env.split(",") if f.strip()]

    def get_additional_functions(self) -> List[str]:
        """
        Retorna lista de funções Lambda adicionais das variáveis de ambiente

        Returns:
            List[str]: Lista de nomes de funções adicionais
        """
        additional_functions_env = os.getenv(
            "LAMBDA_ADDITIONAL_FUNCTIONS", "processor,handler,worker,scheduler,notifier"
        )
        return [f.strip() for f in additional_functions_env.split(",") if f.strip()]

    def get_all_available_functions(self) -> List[str]:
        """
        Retorna lista completa de funções disponíveis (padrão + adicionais)

        Returns:
            List[str]: Lista de todas as funções disponíveis
        """
        default_functions = self.get_default_functions()
        additional_functions = self.get_additional_functions()

        # Combinar sem duplicatas, mantendo ordem
        return list(dict.fromkeys(default_functions + additional_functions))

    def get_function_by_service(self, service: str) -> str:
        """
        Retorna o nome da função Lambda para um serviço específico

        Args:
            service: Nome do serviço (trigger, context, validator, kamis)

        Returns:
            Nome da função Lambda
        """
        service_mapping = {
            "trigger": os.getenv("LAMBDA_TRIGGER_FUNCTION_NAME", "trigger"),
            "context": os.getenv("LAMBDA_CONTEXT_FUNCTION_NAME", "context"),
            "validator": os.getenv("LAMBDA_VALIDATOR_FUNCTION_NAME", "validator"),
            "kamis": os.getenv("LAMBDA_KAMIS_FUNCTION_NAME", "kamis"),
        }

        return service_mapping.get(service.lower(), service)

    def get_lambda_config_summary(self) -> Dict[str, Any]:
        """
        Retorna um resumo das configurações de Lambda

        Returns:
            Dict com resumo das configurações
        """
        default_functions = self.get_default_functions()
        additional_functions = self.get_additional_functions()
        all_functions = self.get_all_available_functions()

        return {
            "default_functions": default_functions,
            "additional_functions": additional_functions,
            "total_available": len(all_functions),
            "all_functions": all_functions,
            "service_mappings": {
                "trigger": self.get_function_by_service("trigger"),
                "context": self.get_function_by_service("context"),
                "validator": self.get_function_by_service("validator"),
                "kamis": self.get_function_by_service("kamis"),
            },
        }


class ConfigManager:
    """Classe principal para gerenciar todas as configurações"""

    def __init__(self):
        self.aws_config = AWSConfig()
        self.sqs_config = SQSConfig(self.aws_config)
        self.lambda_config = LambdaConfig()

    def validate_all_configs(self) -> Dict[str, Any]:
        """
        Valida todas as configurações

        Returns:
            Dict com resultado da validação
        """
        aws_validation = self.aws_config.validate_config()

        validation_result = {
            "valid": aws_validation["valid"],
            "aws": aws_validation,
            "sqs_summary": self.sqs_config.get_queue_config_summary(),
            "lambda_summary": self.lambda_config.get_lambda_config_summary(),
        }

        return validation_result

    def print_config_summary(self) -> None:
        """Exibe um resumo formatado de todas as configurações"""
        validation = self.validate_all_configs()

        print("=" * 80)
        print("📋 RESUMO DAS CONFIGURAÇÕES")
        print("=" * 80)

        # Status geral
        status_icon = "✅" if validation["valid"] else "❌"
        print(
            f"{status_icon} Status geral: {'Válido' if validation['valid'] else 'Inválido'}"
        )

        # Configurações AWS
        print(f"\n🔧 AWS:")
        print(f"   • Região: {self.aws_config.region}")
        print(f"   • Account ID: {self.aws_config.account_id}")

        # Erros e avisos
        if validation["aws"]["errors"]:
            print(f"\n❌ Erros:")
            for error in validation["aws"]["errors"]:
                print(f"   • {error}")

        if validation["aws"]["warnings"]:
            print(f"\n⚠️ Avisos:")
            for warning in validation["aws"]["warnings"]:
                print(f"   • {warning}")

        # Configurações SQS
        sqs_summary = validation["sqs_summary"]
        print(f"\n📬 SQS:")
        print(f"   • Total de filas: {sqs_summary['total_queues']}")
        print(f"   • DLQs: {sqs_summary['dlq_count']}")
        print(f"   • Filas principais: {sqs_summary['main_queue_count']}")

        # Configurações Lambda
        lambda_summary = validation["lambda_summary"]
        print(f"\n⚡ Lambda:")
        print(f"   • Funções padrão: {', '.join(lambda_summary['default_functions'])}")
        print(f"   • Total disponível: {lambda_summary['total_available']}")

        print("=" * 80)


def main():
    """Função principal para testar as configurações"""
    try:
        config_manager = ConfigManager()
        config_manager.print_config_summary()

        # Testar algumas funcionalidades
        print("\n🧪 TESTE DAS CONFIGURAÇÕES:")
        print("-" * 40)

        # Testar SQS
        dlqs = config_manager.sqs_config.get_dlq_list()
        print(f"✅ DLQs carregadas: {len(dlqs)}")

        # Testar Lambda
        default_functions = config_manager.lambda_config.get_default_functions()
        print(f"✅ Funções Lambda padrão: {', '.join(default_functions)}")

        print("\n✨ Teste concluído com sucesso!")

    except Exception as e:
        print(f"❌ Erro durante teste: {str(e)}")


if __name__ == "__main__":
    main()
