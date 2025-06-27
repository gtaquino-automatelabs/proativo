# Sistemática "NLP to SQL" no PROAtivo

**Data:** 22/06/2025  
**Autor:** Análise Técnica do Sistema PROAtivo  
**Versão:** 1.0

## 📋 Resumo Executivo

Este documento apresenta uma análise completa da sistemática "NLP to SQL" implementada no sistema PROAtivo, detalhando como as consultas em linguagem natural são processadas e transformadas em queries SQL para recuperação de dados de manutenção de equipamentos elétricos.

## 🔄 Abordagem Atual: HÍBRIDA (Sem LLM na geração de SQL)

A sistemática atual **NÃO utiliza LLM** para transformar perguntas em queries SQL. Em vez disso, usa uma abordagem determinística baseada em **regras e padrões**.

### ⚙️ Componentes Principais

#### 1. **QueryProcessor** - Processamento NLP
- **Framework:** spaCy para processamento de linguagem natural em português
- **Funcionalidade:** Reconhecimento de entidades e extração de intenções
- **Localização:** `src/api/services/query_processor.py`

**Padrões pré-definidos para reconhecimento:**
- **Tipos de equipamentos:** transformador, disjuntor, motor, gerador, seccionadora
- **Tipos de manutenção:** preventiva, corretiva, preditiva, emergencial
- **Contexto temporal:** hoje, semana passada, último mês, próximo ano
- **IDs de equipamentos:** T001, DIS-005, EQ-123, etc.

#### 2. **Extração de Intenções e Entidades**

```python
# Enums de Intenções Suportadas
QueryIntent.LAST_MAINTENANCE    # "última manutenção"
QueryIntent.COUNT_EQUIPMENT     # "quantos equipamentos"
QueryIntent.COUNT_MAINTENANCE   # "quantas manutenções"
QueryIntent.EQUIPMENT_STATUS    # "status do equipamento"
QueryIntent.MAINTENANCE_HISTORY # "histórico de manutenções"
QueryIntent.FAILURE_ANALYSIS    # "análise de falhas"
QueryIntent.GENERAL_QUERY       # consultas gerais

# Tipos de Entidades Reconhecidas
QueryEntity.EQUIPMENT_TYPE      # "transformador"
QueryEntity.EQUIPMENT_ID        # "T001"
QueryEntity.TIME_PERIOD         # "semana passada"
QueryEntity.MAINTENANCE_TYPE    # "preventiva"
QueryEntity.STATUS              # "crítico"
```

#### 3. **Geração de SQL Determinística**

O método `_generate_sql_query()` utiliza **lógica condicional** para gerar SQL:

```python
# Exemplo: Query para última manutenção
if intent == QueryIntent.LAST_MAINTENANCE:
    sql = """
    SELECT e.name, e.equipment_type, 
           COALESCE(m.completion_date, m.start_date, m.scheduled_date) as maintenance_date,
           m.maintenance_type, m.status, m.title
    FROM equipments e
    JOIN maintenances m ON e.id = m.equipment_id
    WHERE m.completion_date IS NOT NULL
    """
    
    # Aplicação de filtros dinâmicos
    if equipment_types:
        sql += " AND e.equipment_type = ANY(%(equipment_types)s)"
        parameters['equipment_types'] = equipment_types
    
    sql += " ORDER BY m.completion_date DESC LIMIT 1"
```

## 🤖 Papel do LLM no Fluxo

O **LLM (Google Gemini) É USADO**, mas **APÓS** a geração e execução do SQL:

### Fluxo de Processamento:

1. **QueryProcessor:** Gera SQL baseado em regras
2. **Banco de Dados:** SQL é executado e retorna resultados
3. **RAGService:** Enriquece contexto com dados adicionais
4. **LLMService:** Processa dados e gera resposta em linguagem natural

```python
# Assinatura do método no LLMService
async def generate_response(
    self,
    user_query: str,
    sql_query: Optional[str] = None,           # ← SQL já gerado
    query_results: Optional[List[Dict]] = None, # ← Resultados já obtidos
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    # LLM transforma dados estruturados em resposta natural
```

## 🎯 Arquitetura do Fluxo Completo

```
Pergunta do Usuário
        ↓
   QueryProcessor (spaCy + Regras)
   ├─ Extração de Entidades
   ├─ Identificação de Intenção
   └─ Geração de SQL
        ↓
    SQL Query + Parâmetros
        ↓
   Execução no PostgreSQL
        ↓
     Resultados Estruturados
        ↓
   RAGService (Contexto Adicional)
        ↓
   LLMService (Google Gemini)
   ├─ Prompt Estruturado
   ├─ Validação de Resposta
   └─ Formatação Natural
        ↓
   Resposta em Linguagem Natural
```

## ⚖️ Análise de Vantagens e Limitações

### ✅ **Vantagens da Abordagem Atual**

1. **Controle Total:**
   - Queries SQL previsíveis e otimizadas
   - Lógica de negócio explícita e auditável

2. **Performance Consistente:**
   - Sem latência adicional para geração de SQL
   - Tempo de resposta determinístico

3. **Segurança:**
   - Zero risco de SQL injection via LLM
   - Parâmetros sempre sanitizados

4. **Custos Otimizados:**
   - Uso mínimo de tokens do LLM
   - LLM usado apenas para formatação de resposta

5. **Manutenibilidade:**
   - Lógica clara e estruturada
   - Debugging facilitado

### ⚠️ **Limitações Identificadas**

1. **Flexibilidade Limitada:**
   - Restrito a padrões pré-definidos
   - Dificuldade com consultas complexas não mapeadas

2. **Manutenção Manual:**
   - Necessidade de atualizar regras manualmente
   - Adição de novos padrões requer desenvolvimento

3. **Cobertura Limitada:**
   - Casos edge podem não ser tratados
   - Consultas muito específicas podem falhar

4. **Escalabilidade de Padrões:**
   - Crescimento linear da complexidade
   - Possíveis conflitos entre padrões

## 🔮 Cenários de Processamento

### Exemplo 1: Consulta Simples
```
Usuário: "Qual foi a última manutenção?"

QueryProcessor:
├─ Intent: LAST_MAINTENANCE
├─ Entities: []
└─ SQL: SELECT ... FROM equipments e JOIN maintenances m ...

Resultado: Dados da última manutenção
LLM: "A última manutenção foi realizada no transformador T001 em 15/12/2024."
```

### Exemplo 2: Consulta com Filtros
```
Usuário: "Quantos transformadores temos?"

QueryProcessor:
├─ Intent: COUNT_EQUIPMENT
├─ Entities: [EQUIPMENT_TYPE: "transformador"]
└─ SQL: SELECT COUNT(*) FROM equipments WHERE equipment_type = 'transformer'

Resultado: {"total": 8}
LLM: "Temos 8 transformadores no parque elétrico."
```

### Exemplo 3: Consulta Temporal
```
Usuário: "Manutenções da última semana"

QueryProcessor:
├─ Intent: MAINTENANCE_HISTORY
├─ Entities: [TIME_PERIOD: "última semana"]
├─ Temporal Context: {"start": "2024-12-25", "end": "2025-01-01"}
└─ SQL: SELECT ... WHERE maintenance_date BETWEEN ...

Resultado: Lista de manutenções
LLM: "Na última semana foram realizadas 3 manutenções: ..."
```

## 🚀 Possível Evolução para LLM-Based SQL

### Implementação Hipotética:

```python
class LLMQueryProcessor:
    async def generate_sql_with_llm(
        self, 
        user_query: str, 
        schema: str
    ) -> Tuple[str, Dict]:
        
        prompt = f"""
        ESQUEMA DO BANCO DE DADOS:
        {schema}
        
        PERGUNTA DO USUÁRIO:
        {user_query}
        
        INSTRUÇÃO:
        Gere uma query SQL PostgreSQL segura e otimizada para responder 
        à pergunta. Use apenas as tabelas e colunas do esquema fornecido.
        
        FORMATO DE RESPOSTA:
        ```sql
        SELECT ...
        ```
        """
        
        response = await self.llm_service.generate(prompt)
        sql = self.extract_sql_from_response(response)
        validated_sql = await self.sql_validator.validate(sql)
        
        return validated_sql, {}
```

### Vantagens da Abordagem LLM:
- 🎯 **Flexibilidade total** para consultas complexas
- 🧠 **Aprendizado contínuo** com novos padrões
- 📈 **Escalabilidade automática** sem manutenção manual
- 🔄 **Adaptação dinâmica** a mudanças no esquema

### Desafios da Abordagem LLM:
- 🛡️ **Segurança:** Validação rigorosa necessária
- 💰 **Custos:** Aumento significativo de tokens
- ⏱️ **Latência:** Tempo adicional para geração
- 🎲 **Inconsistência:** Variabilidade nas respostas

## 📊 Métricas e Monitoramento Atual

O sistema atual inclui métricas detalhadas:

```python
# Métricas do QueryProcessor
- Queries processadas
- Taxa de sucesso na extração de entidades
- Distribuição de intenções identificadas
- Tempo médio de processamento

# Métricas do LLMService
- Requests totais
- Cache hits
- Fallback usage
- Categorias de "não sei"
- Tempo de resposta do Gemini
```

## 🎯 Recomendações

### Curto Prazo:
1. **Expandir padrões** existentes para cobrir mais casos
2. **Otimizar queries** SQL geradas
3. **Melhorar tratamento** de casos edge

### Médio Prazo:
1. **Implementar abordagem híbrida:** regras para casos comuns + LLM para casos complexos
2. **Adicionar validação semântica** das queries geradas
3. **Desenvolver sistema de feedback** para melhoria contínua

### Longo Prazo:
1. **Avaliar migração** para abordagem LLM completa
2. **Implementar fine-tuning** para domínio específico
3. **Desenvolver sistema de auto-correção** baseado em feedback

## 📝 Conclusão

A sistemática atual do PROAtivo representa uma implementação robusta e eficiente para o processamento NLP to SQL, priorizando segurança, performance e previsibilidade. Embora tenha limitações em flexibilidade, atende adequadamente aos requisitos atuais do sistema de manutenção de equipamentos elétricos.

A arquitetura modular permite evolução gradual, seja através da expansão de padrões existentes ou da incorporação de tecnologias LLM para casos mais complexos, mantendo sempre o foco na qualidade e confiabilidade das respostas geradas.

---

**Próximas Discussões Sugeridas:**
- Análise de casos edge não cobertos pelos padrões atuais
- Avaliação de custo-benefício para implementação LLM-based
- Estratégias de validação e segurança para queries geradas por LLM
- Métricas de qualidade para comparação entre abordagens 