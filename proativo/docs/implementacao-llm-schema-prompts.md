# Sistema de Prompts com Schema Completo para LLM SQL

## Visão Geral

O `LLMSchemaPrompts` é um sistema **elaborado e contextualizado** de prompts para geração de SQL via LLM, projetado especificamente para o domínio de manutenção de equipamentos elétricos.

## Características Principais

### 1. Schema Detalhado do Banco
- **4 tabelas** completamente mapeadas: `equipments`, `maintenances`, `data_history`, `user_feedback`
- **22+ colunas** em equipments com descrições detalhadas
- **Relacionamentos** claramente definidos (1:N entre equipments e maintenances/data_history)
- **Regras de negócio** específicas do domínio

### 2. Contexto Rico do Domínio
```
CONTEXTO DO DOMÍNIO - MANUTENÇÃO DE EQUIPAMENTOS ELÉTRICOS:
- Tipos de Equipamentos: Transformadores, Disjuntores, Motores, Geradores
- Criticidade: Critical, High, Medium, Low
- Tipos de Manutenção: Preventiva, Corretiva, Preditiva, Emergência
- Métricas: MTBF, MTTR, Disponibilidade, Custo/MVA
- Normas: NBR 5356, NBR 7118, NR-10, ONS
- Sazonalidade: Maior demanda no verão, manutenções no inverno
```

### 3. Categorização Inteligente de Queries

O sistema detecta automaticamente 8 categorias de consultas:

| Categoria | Palavras-chave | Exemplo |
|-----------|----------------|---------|
| **STATUS** | status, situação, operacional | "Equipamentos críticos em manutenção" |
| **MAINTENANCE** | manutenção, preventiva, corretiva | "Próximas manutenções programadas" |
| **ANALYSIS** | análise, tendência, temperatura | "Evolução de temperatura dos transformadores" |
| **COSTS** | custo, gasto, economia | "Quanto gastamos em manutenção?" |
| **TIMELINE** | histórico, cronograma | "Timeline do transformador TR-001" |
| **RANKING** | ranking, top, maiores | "Top 10 equipamentos com mais falhas" |
| **PREDICTIVE** | previsão, risco, futuro | "Previsão de falhas próximo mês" |
| **AUDIT** | auditoria, compliance | "Conformidade com NR-10" |

### 4. Prompts Especializados por Categoria

Cada categoria tem:
- **Contexto específico** sobre o que considerar
- **Exemplos relevantes** do domínio
- **Melhores práticas** SQL adaptadas

### 5. Few-Shot Learning Integrado

Exemplos específicos incluídos nos prompts:
```sql
-- Equipamentos críticos em manutenção
SELECT COUNT(*) as total 
FROM equipments e 
WHERE e.criticality = 'Critical' 
AND e.status = 'Maintenance';

-- Custo de manutenção por tipo
SELECT m.maintenance_type as tipo_manutencao,
       COUNT(*) as quantidade,
       SUM(m.actual_cost) as custo_total
FROM maintenances m
WHERE EXTRACT(YEAR FROM m.completion_date) = EXTRACT(YEAR FROM CURRENT_DATE)
GROUP BY m.maintenance_type
ORDER BY custo_total DESC;
```

## Arquitetura da Implementação

```python
class LLMSchemaPrompts:
    def __init__(self):
        self.schema_tables = self._build_schema_tables()      # Schema completo
        self.domain_context = self._build_domain_context()    # Contexto do domínio
        self.category_prompts = self._build_category_prompts() # Prompts por categoria
        self.sql_best_practices = self._build_sql_best_practices() # Melhores práticas
    
    def get_enhanced_prompt(query: str) -> str:
        # 1. Detecta categoria automaticamente
        # 2. Adiciona contexto específico
        # 3. Inclui exemplos relevantes
        # 4. Retorna prompt otimizado
```

## Melhores Práticas SQL Incluídas

### 1. Joins Eficientes
- Aliases significativos: `e = equipments`, `m = maintenances`
- LEFT JOIN quando relação opcional
- INNER JOIN apenas quando obrigatória

### 2. Filtros Temporais
- `CURRENT_DATE` para comparações
- `EXTRACT(YEAR FROM date)` para anos
- `AGE(CURRENT_DATE, date)` para idade

### 3. Formatação Brasileira
- `TO_CHAR(date, 'DD/MM/YYYY')` para datas
- `ROUND(numeric, 2)` para valores monetários
- `COALESCE(field, 'N/A')` para nulos

## Resultados dos Testes

### Detecção de Categorias
- **Taxa de acerto**: 100% (9/9 testes)
- **Priorização inteligente**: Termos financeiros têm boost sobre "manutenção"

### Qualidade dos Prompts
- **Tamanho base**: ~5.3KB
- **Tamanho enhanced**: ~6.6KB (com contexto e exemplos)
- **Elementos essenciais**: 100% presentes

### Geração SQL
- **Taxa de sucesso**: 83.3% (5/6 queries complexas)
- **Tempo médio**: 1670ms
- **Categorias detectadas**: 100% corretas

## Integração com LLMSQLGenerator

```python
class LLMSQLGenerator:
    def __init__(self):
        # Sistema de prompts integrado
        self.schema_prompts = LLMSchemaPrompts()
    
    async def generate_sql(self, user_question: str):
        # Usa prompt enhanced com contexto completo
        prompt = self.schema_prompts.get_enhanced_prompt(user_question)
        
        # Detecta categoria para logging
        category = self.schema_prompts._detect_category(user_question)
        
        # Gera SQL com Gemini
        response = self._model.generate_content(prompt)
```

## Melhorias em Relação ao Sistema Anterior

| Aspecto | Antes | Depois |
|---------|-------|--------|
| **Schema** | Simplificado, 2 tabelas | Completo, 4 tabelas com relacionamentos |
| **Contexto** | Genérico | Específico do domínio elétrico |
| **Exemplos** | 5 genéricos | Múltiplos por categoria |
| **Categorização** | Não tinha | 8 categorias com detecção automática |
| **Prompts** | Estático | Dinâmico baseado em contexto |
| **Validação** | Básica | Regras de negócio incluídas |

## Vantagens do Sistema

1. **Precisão Superior**: Prompts contextualizados geram SQL mais preciso
2. **Menor Alucinação**: Schema detalhado reduz erros do LLM
3. **Performance**: Categorização permite otimizações específicas
4. **Manutenibilidade**: Sistema modular facilita ajustes
5. **Escalabilidade**: Fácil adicionar novas categorias ou tabelas

## Próximos Passos

1. **Implementar cache** por categoria de prompt
2. **Adicionar mais exemplos** few-shot por categoria
3. **Criar sistema de feedback** para melhorar prompts
4. **Implementar versionamento** de prompts
5. **Adicionar suporte multilíngue** (português/inglês)

## Conclusão

O sistema de prompts elaborado representa uma evolução significativa na geração de SQL via LLM, fornecendo contexto rico e específico do domínio que resulta em queries mais precisas e confiáveis. 