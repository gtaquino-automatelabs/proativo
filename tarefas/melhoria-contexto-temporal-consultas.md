# Melhoria no Contexto Temporal de Consultas

## **Problema Identificado**

O sistema respondia incorretamente a perguntas sobre execução no passado, tratando-as como consultas sobre planejamento futuro. 

**Exemplo do problema:**
- **Pergunta:** "Quando foi executado o teste operativo do disjuntor 4k4 de UEM?"
- **Data mencionada:** 11/04/2025 (passado)
- **Resposta incorreta:** "O teste operativo está planejado para 11/04/2025"
- **Resposta esperada:** "Não há registro de execução do teste operativo em 11/04/2025"

## **Causa Raiz**

1. **Lógica de intent inadequada:** Sistema não distinguia entre verbos no passado vs. indicadores de futuro
2. **Prompt LLM insuficiente:** Faltavam regras claras sobre como interpretar consultas temporais
3. **Contexto limitado:** Sistema não informava ao LLM se estava buscando dados de execução ou planejamento

## **Melhorias Implementadas**

### **1. Análise Temporal Aprimorada no Query Processor**

**Arquivo:** `proativo-clone/src/api/services/query_processor.py`

#### **A. Detecção de Verbos e Indicadores Temporais**
```python
# Detectar verbos no passado
past_verbs = ["foi", "foram", "executado", "executada", "realizado", "realizada", 
              "feito", "feita", "aconteceu", "ocorreu", "completado", "completada"]

# Detectar indicadores de futuro
future_indicators = ["será", "vai ser", "planejado", "agendado", "programado", 
                   "próximo", "próxima", "futuro", "futura"]
```

#### **B. Comparação de Datas Específicas**
```python
# Detectar datas específicas e compará-las com hoje
today = datetime.now()
specific_date_entities = [e for e in entities if e.type == QueryEntity.DATE_RANGE]

for date_entity in specific_date_entities:
    if isinstance(date_entity.normalized_value, datetime):
        if date_entity.normalized_value < today:
            has_past_date = True
        else:
            has_future_date = True
```

#### **C. Priorização de Intents com Contexto Temporal**
```python
# 1. CONSULTAS SOBRE EXECUÇÃO PASSADA (prioridade alta)
if (has_past_verbs or has_past_date) and not has_future_indicators:
    if any(word in text for word in ["manutenção", "teste", "inspeção", "reparo", "plano"]):
        return QueryIntent.LAST_MAINTENANCE

# 2. CONSULTAS SOBRE PLANEJAMENTO FUTURO
if (has_future_indicators or has_future_date):
    return QueryIntent.UPCOMING_MAINTENANCE

# 3. CONSULTAS AMBÍGUAS - usar contexto adicional
if "quando" in text:
    if has_past_date:
        return QueryIntent.LAST_MAINTENANCE
    elif has_future_date or any(word in text for word in ["planejado", "programado"]):
        return QueryIntent.UPCOMING_MAINTENANCE
```

#### **D. Novos Padrões de Detecção**
```python
# NOVOS PADRÕES PARA EXECUÇÃO PASSADA
[{"LOWER": {"IN": ["quando", "que"]}}, {"LOWER": "foi"}, {"LOWER": {"IN": ["executado", "executada", "realizado", "realizada"]}}],
[{"LOWER": {"IN": ["foi", "foram"]}}, {"LOWER": {"IN": ["executado", "executada", "realizado", "realizada", "feito", "feita"]}}],
[{"LOWER": {"IN": ["aconteceu", "ocorreu"]}}, {"LOWER": {"IN": ["o", "a"]}}, {"LOWER": {"IN": ["teste", "manutenção", "inspeção"]}}],
```

### **2. Regras Temporais no Prompt do LLM**

**Arquivo:** `proativo-clone/src/api/services/llm_service.py`

#### **A. Regras Específicas para Consultas Temporais**
```
REGRAS TEMPORAIS ESPECÍFICAS:
6. Para perguntas sobre EXECUÇÃO passada (ex: "Quando foi executado...?"):
   - Se NÃO há dados de execução: "Não há registro de execução deste teste/manutenção"
   - Se há dados planejados mas não executados: "Este teste estava planejado para [data], mas não há registro de execução"
   - NUNCA diga que algo passado "está planejado"

7. Para perguntas sobre PLANEJAMENTO futuro (ex: "Quando está planejado...?"):
   - Responda com as datas planejadas encontradas
   - Se não há planejamento: "Não há planejamento registrado para este teste/manutenção"

8. Para datas específicas mencionadas na pergunta:
   - Se a data está no passado e não há execução registrada: "Não há registro de execução em [data]"
   - Se a data está no futuro e há planejamento: "Está planejado para [data]"
```

#### **B. Exemplos Específicos**
```
EXEMPLOS CORRETOS:
✅ "Não há registro de execução do teste operativo em 11/04/2025."
✅ "O teste estava planejado para 11/04/2025, mas não foi executado."

EXEMPLOS DO QUE NÃO FAZER:
❌ "O teste operativo está planejado para..." (quando perguntado sobre execução passada)
```

### **3. Contexto Aprimorado no Prompt do Usuário**

#### **A. Identificação do Tipo de Consulta**
```python
# Determinar tipo de consulta temporal
if 'foi executado' in user_query.lower():
    temporal_context = "\n**TIPO DE CONSULTA:** Busca por execução passada (dados de completion_date)\n"
elif 'está planejado' in user_query.lower():
    temporal_context = "\n**TIPO DE CONSULTA:** Busca por planejamento futuro (dados de planned_date)\n"
elif query_intent == 'last_maintenance':
    temporal_context = "\n**TIPO DE CONSULTA:** Busca por execução passada (somente manutenções completadas)\n"
```

#### **B. Formatação Clara dos Dados**
```python
# Dados de execução (completion_date)
if record.get('completion_date'):
    maintenance_info += f"**EXECUTADO em: {completion_date_str}**"

# Dados de planejamento (planned_date)  
elif record.get('planned_date'):
    maintenance_info += f"**PLANEJADO para: {planned_date_str}**"
```

#### **C. Orientação Específica para Casos sem Dados**
```python
if not structured_data and 'foi executado' in user_query.lower():
    guidance = "\n**ORIENTAÇÃO:** Como não há dados de execução, responda que não há registro de execução."
elif not structured_data and 'está planejado' in user_query.lower():
    guidance = "\n**ORIENTAÇÃO:** Como não há dados de planejamento, responda que não há planejamento registrado."
```

### **4. Detecção Aprimorada de Datas**

#### **A. Novos Formatos de Data**
```python
date_patterns_regex = [
    r'\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})\b',  # DD/MM/YYYY or DD-MM-YYYY
    r'\b(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})\b',    # YYYY-MM-DD or YYYY/MM/DD
    r'\b(\d{1,2})\.(\d{1,2})\.(\d{2,4})\b',        # DD.MM.YYYY
    r'\b(\d{4})\.(\d{1,2})\.(\d{1,2})\b'           # YYYY.MM.DD
]
```

#### **B. Padrões Temporais Relativos**
```python
relative_time_patterns = [
    (r'\b(ontem|hoje|amanhã)\b', "day_relative"),
    (r'\b(esta semana|semana passada|próxima semana)\b', "week_relative"),
    (r'\b(há \d+ dias?|em \d+ dias?)\b', "days_offset"),
]
```

## **Como as Melhorias Resolvem o Problema**

### **Para a pergunta:** "Quando foi executado o teste operativo do disjuntor 4k4 de UEM?"

1. **Query Processor:**
   - Detecta verbo "foi executado" → `has_past_verbs = True`
   - Detecta data "11/04/2025" e compara com hoje → `has_past_date = True` (se data já passou)
   - Classifica como `QueryIntent.LAST_MAINTENANCE` (busca por execução)

2. **SQL Query:**
   - Executa query com filtro `WHERE pmm.completion_date IS NOT NULL`
   - Busca apenas manutenções efetivamente executadas

3. **LLM Prompt:**
   - Recebe contexto: "**TIPO DE CONSULTA:** Busca por execução passada"
   - Se não há dados: "**ORIENTAÇÃO:** Como não há dados de execução, responda que não há registro de execução"
   - Aplica regra: "NUNCA diga que algo passado 'está planejado'"

4. **Resposta Final:**
   - ✅ "Não há registro de execução do teste operativo do disjuntor 4k4 em 11/04/2025"
   - ❌ ~~"O teste operativo está planejado para 11/04/2025"~~

## **Benefícios das Melhorias**

1. **Precisão Temporal:** Distingue corretamente entre consultas sobre passado vs. futuro
2. **Contexto Rico:** LLM recebe informação clara sobre o tipo de consulta
3. **Respostas Adequadas:** Evita confusão entre dados planejados e executados
4. **Flexibilidade:** Funciona com vários formatos de data e expressões temporais
5. **Robustez:** Inclui fallbacks para consultas ambíguas

## **Casos de Teste**

### **Execução Passada (sem dados)**
- **Pergunta:** "Quando foi executado o teste de UEM?"
- **Resposta:** "Não há registro de execução deste teste."

### **Execução Passada (com dados planejados)**
- **Pergunta:** "Foi realizada a manutenção do transformador T001?"
- **Resposta:** "A manutenção estava planejada para 15/03/2025, mas não há registro de execução."

### **Planejamento Futuro**
- **Pergunta:** "Quando está agendado o próximo teste?"
- **Resposta:** "O teste está planejado para 20/08/2025."

### **Data Específica no Passado**
- **Pergunta:** "Houve manutenção em 10/04/2025?"
- **Resposta:** "Não há registro de manutenção executada em 10/04/2025." 