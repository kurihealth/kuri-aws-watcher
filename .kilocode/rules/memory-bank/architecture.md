# Architecture - Arquitetura do Sistema

## Visão Geral

O Kuri AWS Watcher & Lambda Watcher é uma suíte de scripts Python independentes que compartilham uma arquitetura modular baseada em configuração centralizada.

## Estrutura de Arquivos

```
sqs_viewer/
├── config_utils.py              # Módulo central de configuração
├── count_sqs_queue_itens.py    # Monitor contínuo de filas SQS
├── list_dlq_items.py           # Analisador de Dead Letter Queues
├── lambda_logs.py              # Monitor de logs Lambda
├── requirements.txt            # Dependências Python
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

## Pontos de Extensão

1. **Novos Tipos de Fila**: Adicionar em `SQSConfig`
2. **Novas Funções Lambda**: Configurar via variáveis de ambiente
3. **Novos Formatos de Saída**: Estender métodos de exportação
4. **Integração com Alertas**: Hooks nos pontos de detecção de erro

## Limitações Arquiteturais

1. **Sem Persistência**: Dados não são armazenados em banco
2. **Sem Interface Web**: Apenas CLI/terminal
3. **Região Única**: Não suporta múltiplas regiões simultaneamente
4. **Polling vs Eventos**: Usa polling ao invés de eventos AWS