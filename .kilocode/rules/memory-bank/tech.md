# Tech Stack - Tecnologias e Configuração

## Tecnologias Principais

### Python
- **Versão**: 3.7+
- **Paradigma**: Orientado a objetos com scripts executáveis
- **Estilo**: PEP 8 com docstrings descritivas

### Dependências Python
- **boto3**: >= 1.26.0 - SDK AWS para Python
- **python-dotenv**: >= 1.0.0 - Carregamento de variáveis de ambiente

### AWS Services
- **Amazon SQS**: Sistema de filas para mensageria
- **AWS Lambda**: Funções serverless
- **CloudWatch Logs**: Armazenamento e análise de logs
- **IAM**: Gerenciamento de credenciais e permissões

## Setup de Desenvolvimento

### 1. Instalação de Dependências
```bash
pip install -r requirements.txt
```

### 2. Configuração de Ambiente
```bash
cp .env.example .env
# Editar .env com credenciais AWS e configurações
```

### 3. Validação de Configuração
```bash
python config_utils.py
```

## Variáveis de Ambiente Obrigatórias

### Credenciais AWS
- `AWS_ACCESS_KEY_ID`: Chave de acesso AWS
- `AWS_SECRET_ACCESS_KEY`: Chave secreta AWS
- `AWS_DEFAULT_REGION`: Região AWS (padrão: us-east-1)
- `AWS_ACCOUNT_ID`: ID da conta AWS

### Configuração de Filas SQS
- `SQS_TRIGGER_DLQ_NAME`: Nome da DLQ do trigger
- `SQS_CONTEXT_DLQ_NAME`: Nome da DLQ do context
- `SQS_VALIDATOR_DLQ_NAME`: Nome da DLQ do validator
- `SQS_KAMIS_DLQ_NAME`: Nome da DLQ do kamis
- `SQS_TRIGGER_QUEUE_NAME`: Nome da fila principal do trigger
- `SQS_CONTEXT_QUEUE_NAME`: Nome da fila principal do context
- `SQS_VALIDATOR_QUEUE_NAME`: Nome da fila principal do validator
- `SQS_KAMIS_QUEUE_NAME`: Nome da fila principal do kamis

### Configuração de Funções Lambda
- `LAMBDA_TRIGGER_FUNCTION_NAME`: Nome da função trigger
- `LAMBDA_CONTEXT_FUNCTION_NAME`: Nome da função context
- `LAMBDA_VALIDATOR_FUNCTION_NAME`: Nome da função validator
- `LAMBDA_KAMIS_FUNCTION_NAME`: Nome da função kamis
- `LAMBDA_DEFAULT_FUNCTIONS`: Lista de funções padrão (separadas por vírgula)
- `LAMBDA_ADDITIONAL_FUNCTIONS`: Funções adicionais disponíveis

### Configuração de Logging
- `LOG_INTERVAL_SECONDS`: Intervalo para salvar logs (padrão: 60)
- `LOG_FILE_PATH`: Caminho do arquivo de log (padrão: sqs_monitoring.log)
- `SAVE_TO_LOG`: Habilitar salvamento em log (true/false)

## Padrões de Código

### Estrutura de Classes
- Classes com responsabilidade única
- Métodos com docstrings explicativas
- Type hints para parâmetros e retornos

### Tratamento de Erros
- Try/except em todas as operações AWS
- Mensagens de erro descritivas
- Fallback gracioso em caso de falha

### Formatação de Saída
- Emojis Unicode para feedback visual
- Timestamps em formato ISO 8601
- JSON com indentação para legibilidade

## Limitações Técnicas

### AWS SQS
- Máximo 10 mensagens por `receive_message`
- Visibility timeout padrão de 30 segundos
- Delay de até 1 minuto em métricas

### CloudWatch Logs
- Máximo 10.000 eventos por chamada
- Delay de 1-2 minutos para logs
- Limite de rate para API calls

### Python
- GIL limita paralelismo real
- Memória limitada pelo sistema
- Timeout de rede configurável

## Segurança

### Credenciais
- Nunca hardcoded no código
- Carregadas via variáveis de ambiente
- Suporte a AWS CLI profiles

### Dados Sensíveis
- Receipt handles truncados na exibição
- Removidos completamente dos exports
- Logs sem informações sensíveis

### Permissões AWS Necessárias
- `sqs:GetQueueAttributes`
- `sqs:ReceiveMessage`
- `logs:FilterLogEvents`
- `logs:DescribeLogGroups`
- `logs:DescribeLogStreams`

## Performance

### Otimizações
- Paginação automática para grandes volumes
- Cache implícito via ConfigManager
- Processamento assíncrono não implementado

### Monitoramento
- Logs estruturados para análise
- Métricas de execução nos outputs
- Timestamps para rastreamento