# Context - Estado Atual do Projeto

## Foco Atual
- Suíte completa de 6 scripts Python para observabilidade AWS
- Ferramentas maduras e prontas para uso em produção
- Arquitetura modular bem estabelecida com configuração centralizada
- Sistema de monitoramento em tempo real implementado

## Mudanças Recentes
- Memory Bank atualizado em 25/07/2025
- Identificados 2 novos scripts principais:
  - `list_lambda_functions.py`: Listagem e análise detalhada de funções Lambda
  - `monitor_lambda_executions.py`: Monitoramento em tempo real de execuções Lambda
- Configuração de linting/formatação com Ruff implementada
- Arquitetura expandida para 6 componentes principais

## Próximos Passos
- Sistema funcionalmente completo
- Melhorias futuras opcionais listadas no README:
  - Interface web para visualização
  - Alertas automáticos via Slack/Email
  - Dashboard unificado
  - Suporte a múltiplas regiões AWS
  - Testes unitários automatizados
  - Cache de resultados
  - API REST para integração

## Estado Atual dos Scripts
- `count_sqs_queue_itens.py`: Funcional, monitora filas em tempo real
- `list_dlq_items.py`: Funcional, lista e exporta mensagens de DLQs
- `lambda_logs.py`: Funcional, coleta logs com múltiplos modos de operação
- `list_lambda_functions.py`: Funcional, descoberta e catalogação de funções Lambda
- `monitor_lambda_executions.py`: Funcional, monitoramento em tempo real de execuções
- `config_utils.py`: Funcional, centraliza configurações e validações

## Ferramentas de Desenvolvimento
- `ruff.toml`: Configuração de linting e formatação Python moderna
- `.env.example`: Template completo de configuração
- Estrutura de projeto bem organizada e documentada

## Observações
- Todos os scripts seguem padrões consistentes de configuração e interface
- Suporte robusto a CLI com argumentos flexíveis
- Interface visual unificada com emojis informativos
- Tratamento de erros consistente implementado
- Exportação JSON padronizada em todos os scripts
- Sistema de filtering avançado implementado nos novos scripts