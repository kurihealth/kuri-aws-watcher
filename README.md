# SQS Viewer & Lambda Watcher

Uma suíte de scripts Python para monitoramento e observabilidade de serviços AWS, incluindo filas Amazon SQS (com foco em Dead Letter Queues) e funções Lambda através do CloudWatch.

## 🚀 Funcionalidades

- **Monitoramento SQS**: Contagem em tempo real de mensagens em filas SQS
- **Análise de DLQs**: Listagem detalhada de mensagens em Dead Letter Queues
- **Monitoramento Lambda**: Coleta de métricas e logs do CloudWatch
- **Configuração Flexível**: Todas as filas e funções configuráveis via variáveis de ambiente
- **Exportação de Dados**: Salvamento em JSON para análise posterior
- **Interface Interativa**: CLI amigável para configuração de parâmetros

## 📋 Pré-requisitos

- Python 3.7+
- Credenciais AWS configuradas
- Dependências Python (ver `requirements.txt`)

## ⚙️ Instalação

1. Clone o repositório:
```bash
git clone <repository-url>
cd sqs_viewer
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Configure as variáveis de ambiente:
```bash
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

## 🔧 Configuração

### Variáveis de Ambiente Obrigatórias

```env
# Credenciais AWS
AWS_ACCESS_KEY_ID=sua_access_key_aqui
AWS_SECRET_ACCESS_KEY=sua_secret_key_aqui
AWS_DEFAULT_REGION=us-east-1
AWS_ACCOUNT_ID=seu_account_id_aqui
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
LAMBDA_TRIGGER_FUNCTION_NAME=trigger
LAMBDA_CONTEXT_FUNCTION_NAME=context
LAMBDA_VALIDATOR_FUNCTION_NAME=validator
LAMBDA_KAMIS_FUNCTION_NAME=kamis

# Lista padrão para monitoramento (separadas por vírgula)
LAMBDA_DEFAULT_FUNCTIONS=context,kamis,validator

# Funções adicionais disponíveis
LAMBDA_ADDITIONAL_FUNCTIONS=processor,handler,worker,scheduler,notifier
```

### Configurações de Logging

```env
LOG_INTERVAL_SECONDS=60
LOG_FILE_PATH=sqs_monitoring.log
SAVE_TO_LOG=false
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
- Contadores em tempo real

### 2. Listagem Detalhada de DLQs

```bash
python list_dlq_items.py
```

**Funcionalidades**:
- Lista conteúdo completo das mensagens em DLQs
- Formatação JSON legível
- Exportação para arquivo JSON
- Truncamento de dados sensíveis

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

### 4. Utilitário de Configuração

```bash
python config_utils.py
```

**Funcionalidades**:
- Validação de configurações
- Resumo de filas e funções configuradas
- Teste de conectividade
- Diagnóstico de problemas

## 🏗️ Arquitetura

### Componentes Principais

1. **`count_sqs_queue_itens.py`**: Monitoramento contínuo em tempo real
2. **`list_dlq_items.py`**: Análise detalhada de mensagens em DLQs
3. **`lambda_logs.py`**: Monitoramento de funções Lambda AWS
4. **`config_utils.py`**: Utilitário centralizado de configuração

### Classes Principais

- **`ConfigManager`**: Gerenciamento centralizado de configurações
- **`SQSConfig`**: Configuração específica de filas SQS
- **`LambdaConfig`**: Configuração específica de funções Lambda
- **`DLQItemsLister`**: Listagem e análise de DLQs
- **`MultiLambdaWatcher`**: Monitoramento de múltiplas funções Lambda
- **`InteractiveCLI`**: Interface interativa para configuração

## 📁 Estrutura de Arquivos

```
sqs_viewer/
├── count_sqs_queue_itens.py    # Monitoramento contínuo de filas
├── list_dlq_items.py           # Listagem detalhada de DLQs
├── lambda_logs.py              # Monitoramento de funções Lambda
├── config_utils.py             # Utilitário de configuração
├── requirements.txt            # Dependências Python
├── .env.example               # Exemplo de configuração
├── .gitignore                 # Arquivos ignorados pelo Git
└── README.md                  # Esta documentação
```

## 🔍 Exemplos de Uso

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

### Uso Programático

```python
from list_dlq_items import DLQItemsLister
from lambda_logs import MultiLambdaWatcher

# Listar mensagens DLQ
lister = DLQItemsLister()
data = lister.list_all_dlq_items(max_messages_per_queue=5)
lister.print_summary(data)

# Monitorar Lambda
watcher = MultiLambdaWatcher()
results = watcher.get_multiple_functions_logs(
    function_names=['context', 'kamis'],
    hours_back=4,
    errors_only=True
)
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

## 🚨 Limitações Conhecidas

### AWS SQS
- Máximo 10 mensagens por chamada `receive_message`
- Mensagens ficam temporariamente invisíveis após leitura
- `ApproximateNumberOfMessages` pode ter delay de até 1 minuto

### AWS CloudWatch
- Delay de 1-2 minutos para métricas
- Máximo 10.000 eventos por chamada de logs
- Métricas agregadas em períodos mínimos de 60 segundos

## 🔒 Segurança

- **Credenciais**: Carregadas via variáveis de ambiente
- **Receipt Handles**: Truncados na exibição e removidos dos arquivos salvos
- **Arquivo .env**: Protegido pelo `.gitignore`
- **URLs Dinâmicas**: Construídas automaticamente para evitar hardcoding

## 🛠️ Troubleshooting

### Problemas Comuns

1. **Credenciais AWS não encontradas**:
   ```bash
   # Verificar arquivo .env
   cat .env
   
   # Ou configurar AWS CLI
   aws configure
   ```

2. **Fila não encontrada**:
   ```bash
   # Verificar configuração
   python config_utils.py
   ```

3. **Função Lambda não existe**:
   ```bash
   # Listar funções disponíveis
   aws lambda list-functions --region us-east-1
   ```

### Validação de Configuração

```bash
# Executar validação completa
python config_utils.py

# Testar scripts individualmente
python -c "from count_sqs_queue_itens import queue_url_list; print(f'Filas: {len(queue_url_list)}')"
python -c "from list_dlq_items import dlq_list; print(f'DLQs: {len(dlq_list)}')"
python -c "from lambda_logs import LambdaConfig; print(f'Funções: {LambdaConfig().get_default_functions()}')"
```

## 📈 Melhorias Futuras

- [ ] Interface web para visualização
- [ ] Alertas automáticos via Slack/Email
- [ ] Dashboard unificado
- [ ] Suporte a múltiplas regiões AWS
- [ ] Testes unitários automatizados
- [ ] Métricas customizadas
- [ ] Cache de resultados
- [ ] API REST para integração

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## 📞 Suporte

Para suporte e dúvidas:
- Abra uma issue no GitHub
- Consulte a documentação técnica em `.kilocode/rules/memory-bank/`
- Verifique o troubleshooting guide

---

**Desenvolvido com ❤️ para melhorar a observabilidade de serviços AWS**