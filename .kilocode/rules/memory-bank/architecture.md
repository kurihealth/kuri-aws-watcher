# Architecture - Arquitetura do Sistema

## Visão Geral

O Kuri AWS Watcher & Lambda Watcher é uma suíte de scripts Python independentes que compartilham uma arquitetura modular baseada em configuração centralizada.

## Estrutura de Arquivos

```
kuri-aws-watcher/
├── config_utils.py              # Módulo central de configuração
├── count_sqs_queue_itens.py    # Monitor contínuo de filas SQS
├── list_dlq_items.py           # Analisador de Dead Letter Queues
├── lambda_logs.py              # Monitor de logs Lambda
├── list_lambda_functions.py    # Listagem de funções Lambda
├── monitor_lambda_executions.py # Monitor de execuções Lambda em tempo real
├── requirements.txt            # Dependências Python
├── ruff.toml                   # Configuração de linting e formatação
├── .env.example               # Template de configuração
├── .gitignore                 # Arquivos ignorados
└── README.md                  # Documentação principal
```

## Componentes Principais

### 1. ConfigManager (config_utils.py)
- **Responsabilidade**: Centralizar toda lógica de configuração
- **Classes**:
  - `AWSConfig`: Gerencia credenciais e região AWS
  - `SQSConfig`: Constrói URLs de filas dinamicamente
  - `LambdaConfig`: Gerencia funções Lambda disponíveis
  - `ConfigManager`: Orquestra todas as configurações
- **Padrão**: Singleton implícito via importação

### 2. Monitor de Filas SQS (count_sqs_queue_itens.py)
- **Responsabilidade**: Monitoramento contínuo em tempo real
- **Características**:
  - Loop infinito com atualização a cada 10 segundos
  - Separação visual entre DLQs e filas normais
  - Salvamento opcional em log JSON
- **Dependências**: `ConfigManager` para obter lista de filas

### 3. Analisador de DLQs (list_dlq_items.py)
- **Responsabilidade**: Análise detalhada de mensagens em DLQs
- **Classes**:
  - `DLQItemsLister`: Encapsula lógica de listagem
- **Características**:
  - Recupera até 10 mensagens por fila
  - Formata e trunca dados sensíveis
  - Exporta para JSON sem receipt handles

### 4. Monitor Lambda (lambda_logs.py)
- **Responsabilidade**: Coleta e análise de logs do CloudWatch
- **Classes**:
  - `MultiLambdaWatcher`: Gerencia coleta de logs
  - `InteractiveCLI`: Interface interativa
- **Modos de operação**:
  - Default: Configurações padrão
  - CLI: Parâmetros via linha de comando
  - Interativo: Menu guiado

### 5. Listagem de Funções Lambda (list_lambda_functions.py)
- **Responsabilidade**: Descoberta e catalogação de funções Lambda
- **Classes**:
  - `LambdaFunctionLister`: Gerencia listagem e análise de funções
- **Características**:
  - Lista todas as funções Lambda da conta
  - Coleta informações detalhadas (runtime, tamanho, configuração)
  - Filtragem por runtime, nome, estado e arquitetura
  - Geração de estatísticas agregadas
- **Dependências**: `ConfigManager` para configuração AWS

### 6. Monitor de Execuções Lambda (monitor_lambda_executions.py)
- **Responsabilidade**: Monitoramento em tempo real de execuções Lambda
- **Classes**:
  - `LambdaExecutionMonitor`: Coleta métricas e execuções ativas
- **Características**:
  - Monitoramento contínuo com atualizações em tempo real
  - Detecção de funções em execução via métricas CloudWatch
  - Display visual com cores e ícones informativos
  - Coleta de métricas de performance (duração, taxa de erro, throttles)
- **Dependências**: `ConfigManager` para configuração e CloudWatch para métricas

## Padrões de Design

### 1. Configuração Centralizada
- Todas as configurações em variáveis de ambiente
- Módulo `config_utils.py` como ponto único de acesso
- Construção dinâmica de URLs e recursos

### 2. Separação de Responsabilidades
- Cada script tem um propósito específico
- Classes encapsulam lógica relacionada
- Métodos pequenos e focados

### 3. Interface Consistente
- Uso padronizado de emojis para feedback visual
- Formatação similar entre scripts
- Tratamento de erros uniforme

### 4. Flexibilidade de Uso
- Scripts podem ser executados independentemente
- Múltiplos modos de operação
- Configuração via ambiente ou parâmetros

## Fluxo de Dados

### Monitor SQS
```
ConfigManager → Lista de Filas → boto3.SQS → Contagem → Console/Log
```

### Analisador DLQ
```
ConfigManager → Lista DLQs → boto3.SQS → Mensagens → Formatação → JSON/Console
```

### Monitor Lambda
```
LambdaConfig → Funções → boto3.CloudWatch → Logs → Filtros → JSON/Console
```

### Listagem de Funções Lambda
```
ConfigManager → boto3.Lambda → Lista de Funções → Processamento → Estatísticas → JSON/Console
```

### Monitor de Execuções Lambda
```
LambdaConfig → Funções → boto3.CloudWatch → Métricas → Análise → Display Tempo Real
```

## Decisões Técnicas

### 1. Scripts Independentes vs Aplicação Monolítica
- **Escolha**: Scripts independentes
- **Razão**: Simplicidade, flexibilidade, fácil manutenção

### 2. Configuração via Variáveis de Ambiente
- **Escolha**: dotenv + variáveis de ambiente
- **Razão**: Segurança, portabilidade, padrão DevOps

### 3. Saída Estruturada JSON
- **Escolha**: Todos os scripts exportam JSON
- **Razão**: Integração com outras ferramentas, análise posterior

### 4. Interface Visual com Emojis
- **Escolha**: Uso extensivo de emojis Unicode
- **Razão**: Feedback visual imediato, melhor UX em terminal

## Decisões Técnicas Adicionais

### 5. Padrão de Configuração CLI
- **Escolha**: ArgumentParser com flags opcionais em todos os scripts
- **Razão**: Flexibilidade entre uso programático e linha de comando

### 6. Monitoramento Tempo Real
- **Escolha**: Polling de métricas do CloudWatch a cada 10 segundos
- **Razão**: Balance entre responsividade e limites de API

### 7. Formatação de Código
- **Escolha**: Ruff como linter/formatter
- **Razão**: Performance, configurabilidade e compatibilidade Python moderno

## Pontos de Extensão

1. **Novos Tipos de Fila**: Adicionar em `SQSConfig`
2. **Novas Funções Lambda**: Configurar via variáveis de ambiente
3. **Novos Formatos de Saída**: Estender métodos de exportação
4. **Integração com Alertas**: Hooks nos pontos de detecção de erro
5. **Filtros Avançados**: Implementar em `LambdaFunctionLister`
6. **Métricas Customizadas**: Extensão de `LambdaExecutionMonitor`

## Limitações Arquiteturais

1. **Sem Persistência**: Dados não são armazenados em banco
2. **Sem Interface Web**: Apenas CLI/terminal
3. **Região Única**: Não suporta múltiplas regiões simultaneamente
4. **Polling vs Eventos**: Usa polling ao invés de eventos AWS