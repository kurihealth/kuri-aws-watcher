# Kuri AWS Watcher & Lambda Watcher

Uma suíte completa de scripts Python para monitoramento e observabilidade de serviços AWS, incluindo filas Amazon SQS (com foco em Dead Letter Queues) e funções Lambda através do CloudWatch.

## 🚀 Funcionalidades

- **Monitoramento SQS**: Contagem em tempo real de mensagens em filas SQS
- **Análise de DLQs**: Listagem detalhada de mensagens em Dead Letter Queues
- **Monitoramento Lambda**: Coleta de métricas e logs do CloudWatch
- **Execuções Lambda em Tempo Real**: Monitor que mostra quais funções estão executando no momento
- **Listagem de Funções Lambda**: Descoberta e catalogação completa de funções Lambda
- **Configuração Flexível**: Todas as filas e funções configuráveis via variáveis de ambiente
- **Exportação de Dados**: Salvamento em JSON para análise posterior
- **Interface Interativa**: CLI amigável para configuração de parâmetros
- **Filtragem Avançada**: Sistema de filtros por runtime, nome, estado e arquitetura

## 📋 Pré-requisitos

- **Python**: 3.7+ (recomendado 3.12+ para melhor compatibilidade com Ruff)
- **Credenciais AWS**: Configuradas via AWS CLI ou variáveis de ambiente
- **Permissões AWS**: Acesso às APIs do SQS, Lambda e CloudWatch

### Permissões AWS Necessárias

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "sqs:GetQueueAttributes",
                "sqs:ReceiveMessage",
                "lambda:ListFunctions",
                "lambda:GetFunction",
                "logs:FilterLogEvents",
                "logs:DescribeLogGroups",
                "logs:DescribeLogStreams",
                "cloudwatch:GetMetricData"
            ],
            "Resource": "*"
        }
    ]
}
```

## ⚙️ Instalação

1. Clone o repositório:
```bash
git clone <repository-url>
cd kuri-aws-watcher
```

2. Instale as dependências exatas:
```bash
pip install -r requirements.txt
```

3. Configure as variáveis de ambiente:
```bash
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

4. Valide a configuração:
```bash
python config_utils.py
```

## 📦 Dependências

O projeto utiliza as seguintes dependências com versões específicas:

```txt
boto3==1.39.6
botocore==1.39.6
jmespath==1.0.1
python-dateutil==2.9.0.post0
python-dotenv==1.1.1
ruff==0.12.5
s3transfer==0.13.0
six==1.17.0
urllib3==2.5.0
```

## 🔧 Configuração

### Variáveis de Ambiente Obrigatórias

```env
# Credenciais AWS
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key_here
AWS_DEFAULT_REGION=us-east-1
AWS_ACCOUNT_ID=your_account_id_here
```

### Configuração de Filas SQS

Todas as filas são configuráveis via variáveis de ambiente:

```env
# Dead Letter Queues (DLQs)
SQS_TRIGGER_DLQ_NAME=prd-trigger-atena-dlq
SQS_CONTEXT_DLQ_NAME=prd-context-dlq
SQS_VALIDATOR_DLQ_NAME=prd-validator-dlq
SQS_KAMIS_DLQ_NAME=prd-kamis-dlq

# Filas Principais
SQS_TRIGGER_QUEUE_NAME=prd-trigger-atena-queue
SQS_CONTEXT_QUEUE_NAME=prd-context-queue
SQS_VALIDATOR_QUEUE_NAME=prd-validator-queue
SQS_KAMIS_QUEUE_NAME=prd-kamis-queue
```

### Configuração de Funções Lambda

```env
# Funções Lambda individuais
LAMBDA_TRIGGER_FUNCTION_NAME=prd-trigger-atena
LAMBDA_CONTEXT_FUNCTION_NAME=context
LAMBDA_VALIDATOR_FUNCTION_NAME=validator
LAMBDA_KAMIS_FUNCTION_NAME=kamis

# Lista padrão para monitoramento (separadas por vírgula)
LAMBDA_DEFAULT_FUNCTIONS=context,kamis,validator

# Funções adicionais disponíveis
LAMBDA_ADDITIONAL_FUNCTIONS=processor,handler,worker,scheduler,notifier
```

### Configurações de Monitoramento

```env
# Configurações gerais de logging
LOG_INTERVAL_SECONDS=60
LOG_FILE_PATH=sqs_monitoring.log
SAVE_TO_LOG=false

# Configurações do monitor Lambda
LAMBDA_MONITOR_INTERVAL_SECONDS=10
LAMBDA_METRIC_PERIOD_MINUTES=5

# Configurações do monitor SQS
REFRESH_INTERVAL=10
CHANGES_LOG_FILE_PATH=sqs_changes.log
```

## 📊 Uso

### 1. Monitoramento Contínuo de Filas SQS

```bash
python count_sqs_queue_itens.py
```

**Funcionalidades**:
- Atualização a cada 10 segundos
- Separação visual entre DLQs e filas principais
- Salvamento opcional em log
- Detecta mudanças e destaca alterações

### 2. Listagem Detalhada de DLQs

```bash
python list_dlq_items.py
```

**Funcionalidades**:
- Lista conteúdo completo das mensagens em DLQs
- Formatação JSON legível
- Exportação para arquivo JSON
- Truncamento automático de dados sensíveis
- Remoção de receipt handles dos exports

### 3. Monitoramento de Funções Lambda

```bash
# Modo padrão (4h, apenas erros, JSON)
python lambda_logs.py --default

# Modo interativo
python lambda_logs.py

# Modo CLI com parâmetros específicos
python lambda_logs.py --functions context,kamis --hours 8 --all-logs

# Salvar com nome específico
python lambda_logs.py --default --output meus_logs.json
```

**Funcionalidades**:
- Coleta de métricas do CloudWatch
- Análise de logs com filtros de erro
- Suporte a múltiplas funções
- Interface CLI interativa
- Exportação JSON estruturada

### 4. Monitor de Execuções Lambda em Tempo Real

```bash
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
```

**Funcionalidades**:
- Monitoramento em tempo real de execuções ativas
- Separação visual entre funções executando e inativas
- Métricas de invocações, erros e throttles
- Detecção automática de execuções concorrentes
- Interface com atualização automática
- Salvamento opcional em arquivo de log

### 5. Listagem de Funções Lambda

```bash
# Listar todas as funções com detalhes completos
python list_lambda_functions.py

# Listar apenas informações básicas (mais rápido)
python list_lambda_functions.py --basic

# Filtrar por runtime Python
python list_lambda_functions.py --runtime python

# Filtrar por nome contendo "api"
python list_lambda_functions.py --name api

# Filtrar por arquitetura ARM64
python list_lambda_functions.py --architecture arm64

# Salvar com nome específico
python list_lambda_functions.py --output minhas_funcoes.json

# Apenas exibir no console
python list_lambda_functions.py --console-only

# Combinar filtros
python list_lambda_functions.py --runtime python --state Active --name api
```

**Funcionalidades**:
- Lista todas as funções Lambda da conta
- Informações detalhadas de configuração, runtime e tamanho
- Sistema avançado de filtros (runtime, nome, estado, arquitetura)
- Estatísticas agregadas automáticas
- Suporte a paginação para contas com muitas funções
- Exportação JSON estruturada

### 6. Utilitário de Configuração

```bash
python config_utils.py
```

**Funcionalidades**:
- Validação completa de configurações
- Resumo de filas e funções configuradas
- Teste de conectividade AWS
- Diagnóstico de problemas de configuração
- Verificação de permissões

## 🏗️ Arquitetura

### Componentes Principais

1. **[`count_sqs_queue_itens.py`](count_sqs_queue_itens.py)**: Monitoramento contínuo em tempo real
2. **[`list_dlq_items.py`](list_dlq_items.py)**: Análise detalhada de mensagens em DLQs
3. **[`lambda_logs.py`](lambda_logs.py)**: Monitoramento de logs de funções Lambda
4. **[`monitor_lambda_executions.py`](monitor_lambda_executions.py)**: Monitor de execuções Lambda em tempo real
5. **[`list_lambda_functions.py`](list_lambda_functions.py)**: Descoberta e catalogação de funções Lambda
6. **[`config_utils.py`](config_utils.py)**: Utilitário centralizado de configuração

### Classes Principais

- **`ConfigManager`**: Gerenciamento centralizado de configurações
- **`AWSConfig`**: Configuração específica de credenciais AWS
- **`SQSConfig`**: Configuração específica de filas SQS
- **`LambdaConfig`**: Configuração específica de funções Lambda
- **`DLQItemsLister`**: Listagem e análise de DLQs
- **`MultiLambdaWatcher`**: Monitoramento de múltiplas funções Lambda
- **`LambdaExecutionMonitor`**: Monitor de execuções Lambda em tempo real
- **`LambdaFunctionLister`**: Listagem e análise de funções Lambda
- **`InteractiveCLI`**: Interface interativa para configuração

## 📁 Estrutura de Arquivos

```
kuri-aws-watcher/
├── count_sqs_queue_itens.py      # Monitoramento contínuo de filas
├── list_dlq_items.py             # Listagem detalhada de DLQs
├── lambda_logs.py                # Monitoramento de logs Lambda
├── monitor_lambda_executions.py  # Monitor execuções Lambda em tempo real
├── list_lambda_functions.py      # Listagem e catalogação de funções Lambda
├── config_utils.py               # Utilitário centralizado de configuração
├── requirements.txt              # Dependências Python com versões específicas
├── ruff.toml                     # Configuração de linting e formatação
├── .env.example                  # Template completo de configuração
├── .gitignore                    # Arquivos ignorados pelo Git
└── README.md                     # Esta documentação
```

## 🔍 Exemplos de Uso Programático

### Monitoramento Básico

```python
from config_utils import ConfigManager

# Inicializar configuração
config_manager = ConfigManager()

# Obter filas configuradas
dlqs = config_manager.sqs_config.get_dlq_list()
all_queues = config_manager.sqs_config.get_all_queue_list()

# Obter funções Lambda
lambda_functions = config_manager.lambda_config.get_default_functions()
```

### Análise de DLQs

```python
from list_dlq_items import DLQItemsLister

# Listar mensagens DLQ
lister = DLQItemsLister()
data = lister.list_all_dlq_items(max_messages_per_queue=5)
lister.print_summary(data)

# Salvar em JSON
lister.save_to_json(data, "dlq_analysis.json")
```

### Monitoramento Lambda

```python
from lambda_logs import MultiLambdaWatcher
from monitor_lambda_executions import LambdaExecutionMonitor

# Monitorar logs Lambda
watcher = MultiLambdaWatcher()
results = watcher.get_multiple_functions_logs(
    function_names=['context', 'kamis'],
    hours_back=4,
    errors_only=True
)

# Monitor de execuções em tempo real
monitor = LambdaExecutionMonitor()
metrics = monitor.get_all_functions_metrics()
monitor.print_monitoring_display(metrics)
```

### Listagem de Funções Lambda

```python
from list_lambda_functions import LambdaFunctionLister

# Listar todas as funções
lister = LambdaFunctionLister()
results = lister.list_all_functions(include_details=True)

# Aplicar filtros
filters = {
    'runtime': 'python',
    'state': 'Active',
    'name': 'api'
}
filtered_results = lister.filter_functions(results, filters)

# Exibir estatísticas
lister.print_summary(filtered_results)
```

### Configuração Personalizada

```python
from config_utils import LambdaConfig

# Configurar funções personalizadas
lambda_config = LambdaConfig()
custom_functions = lambda_config.get_all_available_functions()

# Adicionar função específica
service_function = lambda_config.get_function_by_service('context')
```

## 🛠️ Desenvolvimento

### Formatação de Código

O projeto utiliza **Ruff** para linting e formatação de código:

```bash
# Executar linting
ruff check .

# Aplicar correções automáticas
ruff check . --fix

# Formatação de código
ruff format .
```

### Configuração do Ruff

- **Target**: Python 3.12
- **Line length**: 120 caracteres
- **Quote style**: Double quotes
- **Regras ativas**: Pycodestyle (E,W), Pyflakes (F), Import sorting (I), Naming (N), Python upgrades (UP)

### Estrutura de Classes

- Classes com responsabilidade única
- Métodos com docstrings explicativas
- Type hints para parâmetros e retornos
- Tratamento robusto de erros

## 🚨 Limitações Conhecidas

### AWS SQS
- Máximo 10 mensagens por chamada `receive_message`
- Mensagens ficam temporariamente invisíveis após leitura (visibility timeout)
- `ApproximateNumberOfMessages` pode ter delay de até 1 minuto
- Receipt handles são sensíveis e não devem ser expostos

### AWS CloudWatch
- Delay de 1-2 minutos para métricas aparecerem
- Máximo 10.000 eventos por chamada de logs
- Métricas agregadas em períodos mínimos de 60 segundos
- Rate limits para chamadas frequentes da API

### Limitações Gerais
- **Região única**: Não suporta múltiplas regiões simultaneamente
- **Sem persistência**: Dados não são armazenados em banco de dados
- **Polling**: Usa polling ao invés de eventos AWS em tempo real
- **Memória**: Limitada pelo sistema para grandes volumes de dados

## 🔒 Segurança

### Proteção de Credenciais
- **Credenciais**: Carregadas via variáveis de ambiente
- **Receipt Handles**: Truncados na exibição e removidos dos arquivos salvos
- **Arquivo .env**: Protegido pelo `.gitignore`
- **URLs Dinâmicas**: Construídas automaticamente para evitar hardcoding

### Dados Sensíveis
- Mensagens SQS podem conter dados sensíveis - são truncadas na exibição
- Receipt handles são removidos completamente dos exports JSON
- Logs não contêm informações de credenciais ou tokens

## 🛠️ Troubleshooting

### Problemas Comuns

#### 1. Credenciais AWS não encontradas
```bash
# Verificar arquivo .env
cat .env

# Ou configurar AWS CLI
aws configure

# Testar credenciais
aws sts get-caller-identity
```

#### 2. Fila SQS não encontrada
```bash
# Verificar configuração
python config_utils.py

# Listar filas disponíveis
aws sqs list-queues --region us-east-1
```

#### 3. Função Lambda não existe
```bash
# Listar funções disponíveis
aws lambda list-functions --region us-east-1

# Usar o script específico
python list_lambda_functions.py --basic
```

#### 4. Erro de permissões AWS
```bash
# Verificar permissões do usuário
aws iam get-user

# Verificar políticas anexadas
aws iam list-attached-user-policies --user-name SEU_USUARIO
```

#### 5. Timeout ou rate limiting
- Reduza a frequência de polling nos scripts
- Use `--basic` nos scripts que suportam para coleta mais rápida
- Verifique se não há muitas instâncias rodando simultaneamente

#### 6. Problemas de formatação no terminal
- Certifique-se que o terminal suporta emojis Unicode
- Use terminais modernos (Terminal.app, iTerm2, VS Code terminal)
- Em ambientes sem Unicode, desabilite emojis nos scripts

### Validação de Configuração

```bash
# Executar validação completa
python config_utils.py

# Testar scripts individualmente
python -c "from count_sqs_queue_itens import queue_url_list; print(f'Filas: {len(queue_url_list)}')"
python -c "from list_dlq_items import dlq_list; print(f'DLQs: {len(dlq_list)}')"
python -c "from lambda_logs import LambdaConfig; print(f'Funções: {LambdaConfig().get_default_functions()}')"
```

### Logs de Debug

Para debug mais detalhado, habilite logs do boto3:

```python
import boto3
import logging

# Habilitar logs do boto3
boto3.set_stream_logger('botocore', logging.DEBUG)
```

## ⚡ Performance

### Otimizações Implementadas
- **Paginação automática** para grandes volumes de dados
- **Cache implícito** via ConfigManager
- **Polling inteligente** com intervalos configuráveis
- **Filtragem no cliente** para reduzir chamadas API
- **Processamento assíncrono** não implementado (pode ser adicionado)

### Recomendações de Uso
- Use `--basic` quando possível para coleta mais rápida
- Configure intervalos apropriados para evitar rate limiting
- Execute scripts em horários de menor uso para melhor performance
- Monitore uso de API calls para evitar custos excessivos

## 📈 Melhorias Futuras

### Planejadas
- [ ] Interface web para visualização
- [ ] Alertas automáticos via Slack/Email
- [ ] Dashboard unificado com métricas em tempo real
- [ ] Suporte a múltiplas regiões AWS simultaneamente
- [ ] Testes unitários automatizados
- [ ] Cache de resultados com Redis/Memcached
- [ ] API REST para integração externa
- [ ] Modo daemon para execução contínua

### Avançadas
- [ ] Integração com Prometheus/Grafana
- [ ] Suporte a AWS Organizations (multi-account)
- [ ] Machine Learning para detecção de anomalias
- [ ] Compressão e arquivamento automático de logs
- [ ] Suporte a EventBridge para eventos em tempo real
- [ ] Interface móvel/PWA

## 🤝 Contribuição

### Como Contribuir

1. **Fork** o projeto
2. Crie uma **branch** para sua feature (`git checkout -b feature/AmazingFeature`)
3. **Configure** o ambiente de desenvolvimento:
   ```bash
   pip install -r requirements.txt
   ruff check . --fix
   ```
4. **Commit** suas mudanças (`git commit -m 'Add some AmazingFeature'`)
5. **Push** para a branch (`git push origin feature/AmazingFeature`)
6. Abra um **Pull Request**

### Padrões de Código

- Siga as configurações do **Ruff** definidas em `ruff.toml`
- Use **type hints** para todos os parâmetros e retornos
- Adicione **docstrings** descritivas para classes e métodos
- Mantenha **responsabilidade única** para cada classe
- Inclua **tratamento de erro** robusto
- Use **emojis Unicode** para feedback visual consistente

### Estrutura de Commits

```
feat: adiciona nova funcionalidade
fix: corrige bug específico
docs: atualiza documentação
style: mudanças de formatação
refactor: refatoração sem mudança de funcionalidade
test: adiciona ou modifica testes
chore: tarefas de manutenção
```

## 📄 Licença

Este projeto está sob a licença **MIT**. Veja o arquivo `LICENSE` para mais detalhes.

## 📞 Suporte

### Canais de Suporte

- **Issues**: Abra uma issue no GitHub para bugs ou feature requests
- **Documentação**: Consulte a documentação técnica em `.kilocode/rules/memory-bank/`
- **Troubleshooting**: Consulte a seção de troubleshooting neste README

### Informações Úteis

- **Região padrão**: us-east-1
- **Intervalo padrão de monitoramento**: 10 segundos
- **Período padrão de métricas**: 5 minutos
- **Timeout padrão**: 30 segundos
- **Formato de timestamp**: ISO 8601 UTC

---

**Desenvolvido com ❤️ para melhorar a observabilidade de serviços AWS**

*Versão atualizada em 2025-07-25*