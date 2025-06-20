# 📋 **Relatório Completo: Camada LLM do PROAtivo**

## 🎯 **1. Visão Geral do Sistema**

O **PROAtivo** utilizará **Inteligência Artificial** para permitir que usuários façam perguntas em **linguagem natural** sobre dados de manutenção de equipamentos elétricos, como:

- *"Quais transformadores precisam de manutenção urgente?"*
- *"Qual foi o custo total de reparos em janeiro?"*  
- *"Me mostre falhas recorrentes do equipamento T001"*

## 🤖 **2. API Escolhida: Google Gemini 2.5 Flash**

### **Por que Google Gemini?**
- **✅ Mais moderno:** Lançado em 2024, tecnologia de ponta
- **✅ Multimodal:** Processa texto, imagens e dados estruturados
- **✅ Rápido:** "Flash" = otimizado para velocidade
- **✅ Custo-benefício:** Preço competitivo por token
- **✅ Integração Python:** SDK oficial bem documentado

### **Configuração Técnica:**
```python
# Modelo específico
MODEL = "gemini-2.5-flash"
TEMPERATURE = 0.1  # Respostas mais precisas, menos criativas
MAX_TOKENS = 1000  # Limite de resposta
```

## 🧠 **3. Arquitetura RAG (Retrieval Augmented Generation)**

### **O que é RAG?**
**RAG** combina duas coisas:
1. **Retrieval (Busca):** Encontrar dados relevantes no banco
2. **Generation (Geração):** IA criar resposta baseada nos dados

### **Fluxo RAG no PROAtivo:**

```
👤 Usuário: "Transformadores com problema"
     ⬇️
🔍 Sistema busca no banco: equipamentos + manutenções
     ⬇️  
📊 Dados encontrados: [T001: falha elétrica, T002: ok, T003: vencido]
     ⬇️
🤖 Gemini recebe: pergunta + dados + instruções
     ⬇️
💬 Resposta: "Encontrei 2 transformadores com problemas: T001 com falha elétrica e T003 com manutenção vencida"
```

## 📝 **4. Sistema de Prompts Estruturados**

### **Template Principal:**
```python
SYSTEM_PROMPT = """
Você é um assistente especializado em manutenção de equipamentos elétricos.

CONTEXTO DO SISTEMA:
- Empresa: Setor elétrico/energético
- Dados: Equipamentos, manutenções, falhas, custos
- Objetivo: Apoio à decisão técnica

INSTRUÇÕES:
1. Responda sempre em português brasileiro
2. Use linguagem técnica mas acessível
3. Seja preciso com números e datas  
4. Sugira ações quando apropriado
5. Se não souber, diga claramente

FORMATO DE RESPOSTA:
- Resposta direta à pergunta
- Dados específicos encontrados
- Recomendações (se aplicável)
"""

USER_PROMPT = """
PERGUNTA DO USUÁRIO: {user_question}

DADOS RELEVANTES ENCONTRADOS:
{retrieved_data}

CONTEXTO ADICIONAL:
- Equipamentos total: {total_equipment}
- Última atualização: {last_update}
- Filtros aplicados: {filters}

Responda à pergunta baseando-se nos dados fornecidos.
"""
```

### **Prompts Especializados por Tipo:**

**🔧 Equipamentos:**
```python
EQUIPMENT_PROMPT = """
Analise os dados de equipamentos e forneça:
1. Status atual de cada equipamento
2. Alertas de manutenção vencida
3. Equipamentos críticos
4. Recomendações prioritárias
"""
```

**⚙️ Manutenções:**
```python
MAINTENANCE_PROMPT = """
Analise o histórico de manutenções e inclua:
1. Frequência de manutenções
2. Custos acumulados
3. Padrões de falhas
4. Próximas manutenções devidas
"""
```

## 🛠️ **5. Tools/Funções do Sistema**

### **Function Calling com Gemini:**
O Gemini poderá "chamar funções" para buscar dados específicos:

```python
AVAILABLE_TOOLS = [
    {
        "name": "get_equipment_status",
        "description": "Busca status atual de equipamentos específicos",
        "parameters": {
            "equipment_ids": ["T001", "T002"],
            "include_maintenance": True
        }
    },
    {
        "name": "get_maintenance_history", 
        "description": "Histórico de manutenções por período",
        "parameters": {
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "equipment_type": "transformador"
        }
    },
    {
        "name": "calculate_costs",
        "description": "Calcula custos de manutenção",
        "parameters": {
            "period": "monthly",
            "group_by": "equipment_type"
        }
    }
]
```

### **Como as Tools Funcionam:**

1. **Usuário pergunta:** *"Qual o custo de manutenção dos transformadores?"*
2. **Gemini decide:** "Preciso usar a tool `calculate_costs`"
3. **Sistema executa:** Busca no banco de dados
4. **Dados retornam:** `{"transformadores": 45000, "periodo": "2024"}`
5. **Gemini responde:** *"O custo total foi R$ 45.000 em 2024"*

## 🏗️ **6. Componentes Técnicos**

### **Estrutura de Arquivos:**
```
src/api/services/
├── llm_service.py          # Integração principal com Gemini
├── rag_service.py          # Sistema RAG de busca + geração
├── query_processor.py      # Converte linguagem natural → SQL
├── prompt_templates.py     # Templates de prompts organizados
└── context_manager.py      # Gerencia contexto da conversa
```

### **LLMService - Classe Principal:**
```python
class LLMService:
    async def generate_response(
        self,
        user_query: str,
        context: Dict,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Processo completo:
        1. Preparar prompt com contexto
        2. Chamar Gemini API
        3. Processar resposta
        4. Validar e sanitizar
        5. Retornar estruturado
        """
```

### **RAGService - Busca Inteligente:**
```python
class RAGService:
    async def get_relevant_context(
        self, 
        query: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        1. Analisa intenção da pergunta
        2. Identifica entidades (equipamentos, datas)
        3. Busca dados relevantes no banco
        4. Organiza contexto para o LLM
        """
```

## 🔄 **7. Fluxo Detalhado de Processamento**

### **Passo a Passo Completo:**

```
1️⃣ ENTRADA DO USUÁRIO
   Input: "Transformadores com manutenção atrasada"
   
2️⃣ ANÁLISE INICIAL (QueryProcessor)
   - Detecta entidades: ["transformadores", "manutenção", "atrasada"]
   - Identifica intenção: MAINTENANCE_STATUS
   - Define filtros: equipment_type="transformador", status="overdue"

3️⃣ BUSCA NO BANCO (RAGService)  
   SQL: SELECT * FROM equipments WHERE type='transformador' 
        AND next_maintenance < CURRENT_DATE
   Resultado: [T001, T003, T007] com dados detalhados

4️⃣ PREPARAÇÃO DO CONTEXTO
   - Organiza dados encontrados
   - Adiciona estatísticas relevantes
   - Inclui histórico da conversa

5️⃣ CHAMADA PARA GEMINI (LLMService)
   - Monta prompt estruturado
   - Envia para Gemini 2.5 Flash
   - Recebe resposta em JSON

6️⃣ PROCESSAMENTO DA RESPOSTA
   - Valida formato da resposta
   - Sanitiza conteúdo
   - Adiciona metadados (confiança, fontes)

7️⃣ RETORNO ESTRUTURADO
   {
     "response": "Encontrei 3 transformadores...",
     "data_found": 3,
     "equipment_ids": ["T001", "T003", "T007"],
     "confidence": 0.95,
     "sources": ["equipment_table", "maintenance_table"]
   }
```

## 🔒 **8. Segurança e Validação**

### **Proteções Implementadas:**

**🛡️ Validação de Entrada:**
- Limite de caracteres (1000 max)
- Filtragem de caracteres perigosos
- Detecção de tentativas de injection

**🔐 Sanitização de SQL:**
- Queries parametrizadas sempre
- Whitelist de tabelas permitidas
- Validação de estrutura SQL

**⚡ Rate Limiting:**
- Máximo 60 consultas/hora por usuário
- Timeout de 30 segundos por consulta
- Cache de respostas similares

## 💰 **9. Gestão de Custos**

### **Estratégias de Economia:**

**📊 Cache Inteligente:**
- Respostas similares reutilizadas por 1 hora
- Hash da pergunta + contexto para identificação
- 80% de economia estimada em perguntas repetidas

**🎯 Otimização de Tokens:**
- Prompts compactos mas efetivos
- Dados resumidos antes de enviar
- Respostas limitadas a 1000 tokens

**📈 Monitoramento:**
- Custo por consulta registrado
- Alertas se orçamento mensal excedido
- Relatórios de uso por usuário

## 🚀 **10. Implementação Prática**

### **Configuração de Ambiente:**
```python
# .env
GOOGLE_API_KEY=seu_key_aqui
GEMINI_MODEL=gemini-2.5-flash
GEMINI_TEMPERATURE=0.1
GEMINI_MAX_TOKENS=1000
RAG_CACHE_TTL=3600  # 1 hora
```

### **Exemplo de Uso Real:**
```python
# Usuário pergunta
user_input = "Quanto gastamos com manutenção em dezembro?"

# Sistema processa
result = await llm_service.generate_response(
    user_query=user_input,
    session_id="abc123",
    context=current_session_context
)

# Resposta estruturada
print(result["response"])
# "Em dezembro de 2024, foram gastos R$ 127.450,00 
#  em manutenções, distribuídos entre..."
```

## 📊 **11. Métricas e Monitoramento**

### **KPIs do Sistema LLM:**
- **Precisão:** % de respostas corretas vs esperadas
- **Velocidade:** Tempo médio de resposta (< 3 segundos)
- **Satisfação:** Taxa de 👍 vs 👎 dos usuários
- **Cobertura:** % de perguntas que consegue responder
- **Custo:** $ por consulta processada

### **Dashboard de Monitoramento:**
- Número de consultas por hora/dia
- Tipos de consulta mais frequentes  
- Erros e timeouts
- Uso de tokens e custos
- Feedback dos usuários

## 🎯 **12. Roadmap de Evolução**

### **Fase 1 (Atual):** Mock LLM
- ✅ Simulador básico para desenvolvimento

### **Fase 2 (Próxima):** Gemini Básico  
- 🔄 Integração real com prompts simples

### **Fase 3 (Futuro):** RAG Avançado
- 📈 Busca semântica com embeddings
- 🧠 Context windows maiores
- 🔧 Function calling otimizado

### **Fase 4 (Visão):** IA Especializada
- 🤖 Fine-tuning para domínio elétrico
- 📱 Interface multimodal (voz, imagens)
- 🔮 Análise preditiva automática

---

## 🎉 **Resumo Executivo**

O **PROAtivo** terá uma camada LLM robusta e profissional usando:
- **Google Gemini 2.5 Flash** como IA principal
- **Sistema RAG** para busca + geração contextual  
- **Prompts estruturados** por tipo de consulta
- **Function calling** para execução de tools
- **Segurança** e **economia** como prioridades
- **Monitoramento** completo de performance

Resultado: **Sistema conversacional inteligente** que transforma perguntas naturais em insights acionáveis sobre manutenção de equipamentos! 🚀

---

**Documento criado em:** {{ current_date }}  
**Autor:** Sistema PROAtivo  
**Versão:** 1.0  
**Status:** Planejamento/Documentação 