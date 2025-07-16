# Product Overview - Kuri AWS Watcher & Lambda Watcher

## Por que este projeto existe?

Este projeto foi criado para resolver problemas críticos de observabilidade em ambientes AWS, especificamente:

1. **Falta de visibilidade em tempo real**: Dificuldade em monitorar filas SQS e funções Lambda sem acessar múltiplas interfaces AWS
2. **Análise de falhas complexa**: Mensagens em DLQs são difíceis de analisar através do console AWS
3. **Fragmentação de logs**: Logs do CloudWatch são dispersos e difíceis de correlacionar
4. **Automação limitada**: Necessidade de scripts customizados para tarefas operacionais recorrentes

## Problemas que resolve

### 1. Monitoramento de Filas SQS
- **Problema**: Verificar manualmente o número de mensagens em múltiplas filas é tedioso
- **Solução**: Monitoramento contínuo e automático com atualização a cada 10 segundos

### 2. Análise de Dead Letter Queues
- **Problema**: Mensagens em DLQs indicam falhas críticas mas são difíceis de investigar
- **Solução**: Listagem detalhada com exportação JSON para análise profunda

### 3. Observabilidade de Funções Lambda
- **Problema**: Logs dispersos no CloudWatch dificultam troubleshooting
- **Solução**: Agregação inteligente com filtros de erro e análise temporal

### 4. Operações Manuais Repetitivas
- **Problema**: Tarefas como contar mensagens ou exportar logs consomem tempo valioso
- **Solução**: Automação completa com interface CLI intuitiva

## Como deve funcionar

### Princípios de Design
1. **Simplicidade**: Comandos diretos sem configurações complexas
2. **Flexibilidade**: Todas as configurações via variáveis de ambiente
3. **Eficiência**: Execução rápida com feedback visual imediato
4. **Confiabilidade**: Tratamento robusto de erros com mensagens claras

### Fluxo de Trabalho Típico

1. **Setup Inicial**
   - Copiar `.env.example` para `.env`
   - Configurar credenciais AWS e nomes das filas/funções
   - Validar configuração com `config_utils.py`

2. **Monitoramento Contínuo**
   - Executar `count_sqs_queue_itens.py` em terminal dedicado
   - Observar contadores em tempo real
   - Logs salvos automaticamente conforme configurado

3. **Investigação de Problemas**
   - Detectar mensagens em DLQs através do monitoramento
   - Executar `list_dlq_items.py` para análise detalhada
   - Exportar dados para investigação offline

4. **Análise de Lambda**
   - Executar `lambda_logs.py` com parâmetros apropriados
   - Filtrar por erros ou período específico
   - Correlacionar com eventos nas filas

## Experiência do Usuário

### Interface Visual
- **Emojis informativos**: 🚨 para alertas, ✅ para status OK, 📊 para dados
- **Formatação clara**: Separação visual entre DLQs e filas normais
- **Feedback imediato**: Indicadores de progresso e status

### Modos de Operação
1. **Modo Default**: Configurações padrão para uso rápido
2. **Modo CLI**: Parâmetros via linha de comando para automação
3. **Modo Interativo**: Menus guiados para usuários menos técnicos

### Saídas Estruturadas
- **Console**: Informações formatadas para leitura humana
- **JSON**: Dados estruturados para processamento automatizado
- **Logs**: Histórico persistente para auditoria

## Casos de Uso Principais

1. **Operações Diárias**
   - Verificar saúde do sistema pela manhã
   - Monitorar picos de tráfego
   - Identificar gargalos rapidamente

2. **Troubleshooting**
   - Investigar falhas em produção
   - Analisar padrões de erro
   - Rastrear mensagens problemáticas

3. **Relatórios e Métricas**
   - Gerar dados para dashboards
   - Criar relatórios de incidentes
   - Análise de tendências

4. **Automação DevOps**
   - Integrar em pipelines CI/CD
   - Criar alertas customizados
   - Automatizar respostas a incidentes