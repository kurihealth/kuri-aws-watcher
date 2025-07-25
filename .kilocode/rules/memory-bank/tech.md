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

### Configuração de Monitoramento Lambda
- `LAMBDA_MONITOR_INTERVAL_SECONDS`: Intervalo de atualização do monitor (padrão: 10)
- `LAMBDA_METRIC_PERIOD_MINUTES`: Período de coleta de métricas (padrão: 5)

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

### Linting e Formatação (Ruff)
- **Arquivo**: `ruff.toml`
- **Target**: Python 3.12
- **Line length**: 120 caracteres
- **Rules**: Pycodestyle (E,W), Pyflakes (F), Import sorting (I), Naming (N), Python upgrades (UP)
- **Formatação**: Double quotes, espaços para indentação

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
- `lambda:ListFunctions`
- `lambda:GetFunction`
- `cloudwatch:GetMetricData`

## Performance

### Otimizações
- Paginação automática para grandes volumes
- Cache implícito via ConfigManager
- Processamento assíncrono não implementado
- Polling inteligente com intervalo configurável

### Monitoramento
- Logs estruturados para análise
- Métricas de execução nos outputs
- Timestamps para rastreamento
- Monitoramento em tempo real com display visual
- Coleta automática de métricas CloudWatch

## Ferramentas de Desenvolvimento

### Ruff (Linter/Formatter)
- **Performance**: Muito mais rápido que ferramentas tradicionais (Black, Flake8)
- **Compatibilidade**: Python 3.12+ com suporte a recursos modernos
- **Configuração**: Centralizada em `ruff.toml`
- **Regras**: Combination de múltiplas ferramentas em uma só

### Estruturas de Dados Modernas
- **Type hints**: Utilizados extensivamente (dict[str, Any], list[dict])
- **Pattern matching**: Não utilizado mas suportado
- **Dataclasses**: Não utilizado atualmente, mas poderia ser implementado

## Capacidades Específicas dos Scripts

### list_lambda_functions.py
- **Paginação**: Suporte a contas com muitas funções Lambda
- **Filtragem**: Por runtime, nome, estado, arquitetura
- **Análise**: Estatísticas detalhadas de uso e configuração
- **Export**: JSON estruturado com metadados completos

### monitor_lambda_executions.py
- **Tempo Real**: Atualização automática a cada 10 segundos
- **Métricas CloudWatch**: Coleta automática de invocações, erros, throttles
- **Display Visual**: Interface colorida com ícones informativos
- **Detecção de Execução**: Identifica funções executando via execuções concorrentes