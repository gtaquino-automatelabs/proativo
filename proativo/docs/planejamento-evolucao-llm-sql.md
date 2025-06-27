# Planejamento: Evolução para LLM na Geração de SQL - PROAtivo

**Data:** 02/01/2025  
**Versão:** 1.0  
**Status:** Planejamento Estratégico  
**Objetivo:** Implementar LLM para geração de SQL de forma pragmática e eficiente

## 📋 Sumário Executivo

Este documento apresenta um plano simplificado para adicionar capacidade de geração de SQL via LLM ao sistema PROAtivo, mantendo o sistema atual como fallback automático quando o serviço LLM estiver indisponível.

## 🎯 Objetivos

### Objetivos Primários
- **Flexibilidade:** Permitir consultas em linguagem natural livre
- **Robustez:** Manter sistema atual como fallback automático
- **Simplicidade:** Implementação direta sem complexidade desnecessária
- **Rapidez:** MVP funcional em 4-6 semanas

### Benefícios Esperados
- Melhor experiência do usuário com consultas naturais
- Redução gradual da manutenção de padrões
- Sistema resiliente com fallback automático

## 🏗️ Arquitetura Simplificada

```
┌─────────────────────────────────────────────────────────────┐
│                    User Query                                │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              Availability Check                              │
│         Is LLM Service Available?                            │
└──────┬──────────────────────────────┬───────────────────────┘
       │ YES                          │ NO
       ▼                              ▼
┌─────────────────────────┐  ┌─────────────────────────┐
│    LLM SQL Generator    │  │  Rule-Based Generator   │
│   (Google Gemini)       │  │    (Sistema Atual)      │
└──────────┬──────────────┘  └──────────┬───────────────┘
           │                             │
           ▼                             ▼
┌─────────────────────────────────────────────────────────────┐
│                  SQL Validator                               │
│         • Only SELECT allowed                                │
│         • Block dangerous keywords                           │
│         • Basic syntax check                                 │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                Database Execution                            │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 Componentes Principais

### 1. **Availability Router (Simples)**

```python
class AvailabilityRouter:
    """Roteador simples baseado em disponibilidade do serviço."""
    
    async def route_query(self, query: str) -> str:
        if await self._is_llm_available():
            return "llm"
        return "rules"
    
    async def _is_llm_available(self) -> bool:
        try:
            # Verificação rápida de saúde do serviço
            response = await self.llm_service.health_check(timeout=1.0)
            return response.status == "healthy"
        except:
            return False
```

### 2. **LLM SQL Generator**

```python
class LLMSQLGenerator:
    """Gerador de SQL usando Google Gemini."""
    
    async def generate_sql(self, user_query: str) -> str:
        prompt = self._build_prompt(user_query)
        
        try:
            response = await self.gemini_client.generate(
                prompt,
                temperature=0.1,
                max_tokens=500
            )
            
            sql = self._extract_sql(response)
            
            if self._is_valid_sql(sql):
                return sql
            else:
                raise ValueError("Invalid SQL generated")
                
        except Exception as e:
            # Log error and let router handle fallback
            logger.error(f"LLM generation failed: {e}")
            raise
```

### 3. **SQL Validator (Essencial)**

```python
class SQLValidator:
    """Validador focado em segurança essencial."""
    
    def validate(self, sql: str) -> bool:
        sql_upper = sql.upper().strip()
        
        # 1. Apenas SELECT permitido
        if not sql_upper.startswith('SELECT'):
            return False
        
        # 2. Bloquear comandos perigosos
        dangerous = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'TRUNCATE']
        if any(cmd in sql_upper for cmd in dangerous):
            return False
        
        # 3. Verificação básica de sintaxe
        try:
            sqlparse.parse(sql)
            return True
        except:
            return False
```

## 📈 Cronograma de Implementação

### **Fase 1: MVP (4-6 semanas)**

**Semanas 1-2: Setup e Desenvolvimento Base**
```
✅ Configurar API Key do Gemini
✅ Implementar LLM SQL Generator básico
✅ Criar Availability Router
✅ Desenvolver SQL Validator essencial
```

**Semanas 3-4: Integração e Testes**
```
🔧 Integrar com chat endpoint existente
🔧 Implementar fallback automático
🔧 Testes de segurança (SQL injection)
🔧 Validação com 20-30 queries de teste
```

**Semanas 5-6: Deploy e Monitoramento**
```
🚀 Deploy com feature flag
🚀 Configurar logging e métricas básicas
🚀 Documentação essencial
🚀 Monitoramento inicial
```

### **Fase 2: Estabilização (3-4 semanas)**

```
📊 Análise de uso real
📊 Ajustes de prompts baseados em feedback
📊 Otimizações de performance
📊 Expansão gradual de cobertura
```

## 💰 Análise de Custos Simplificada

### **Desenvolvimento**
```
👨‍💻 Desenvolvimento (160-240 horas): R$ 32.000 - R$ 48.000
🧪 Testes e Deploy (40-60 horas): R$ 8.000 - R$ 12.000

Total: R$ 40.000 - R$ 60.000
```

### **Operação Mensal**
```
🤖 Google Gemini API: R$ 500 - R$ 1.500/mês (estimado)
📊 Monitoramento: Infraestrutura existente

Total: R$ 500 - R$ 1.500/mês
```

### **ROI Esperado**
```
Redução de manutenção: R$ 2.000/mês
Payback: 20-30 meses
```

## ⚠️ Riscos e Mitigações

| Risco | Mitigação |
|-------|-----------|
| **SQL Injection** | Validador bloqueia tudo exceto SELECT |
| **LLM Indisponível** | Fallback automático para sistema atual |
| **Custos elevados** | Monitoramento e limites de uso |
| **Queries incorretas** | Sistema atual sempre disponível como backup |

## 🧪 Estratégia de Testes

### **Conjunto de Testes Essenciais**
```python
test_queries = [
    # Queries simples
    "Quantos equipamentos temos?",
    "Liste os transformadores ativos",
    
    # Queries médias
    "Equipamentos com manutenção atrasada",
    "Falhas do último mês",
    
    # Testes de segurança
    "Delete todos os equipamentos",  # Deve ser bloqueado
    "'; DROP TABLE equipments; --",   # SQL injection
]
```

## 📊 Métricas de Sucesso

### **MVP (Fase 1)**
- ✅ Sistema funcional com fallback automático
- ✅ Zero incidentes de segurança
- ✅ Tempo de resposta < 2 segundos

### **Produção (Fase 2)**
- 📈 Disponibilidade > 95%
- 📈 Taxa de sucesso > 90%
- 📈 Satisfação do usuário > 4/5

## 🎯 Próximos Passos

### **Semana 1**
1. Obter API Key do Google Gemini
2. Criar branch `feature/llm-sql-integration`
3. Implementar prova de conceito

### **Semana 2**
1. Desenvolver componentes core
2. Iniciar testes de segurança
3. Preparar integração

## 📝 Considerações Finais

Este plano prioriza simplicidade e entrega rápida de valor. O sistema de fallback automático garante que nunca teremos degradação de serviço, enquanto gradualmente expandimos as capacidades com LLM.

**Princípio fundamental:** Se o LLM está disponível, use-o. Se não, use o sistema atual. Simples assim.

---

**Documentos Relacionados:**
- [Macrotarefas Evolução LLM SQL](../../Planejamento/6_macrotarefas-evolucao-llm-sql.md)
- [Sistemática NLP to SQL Atual](./sistematica-nlp-to-sql-proativo.md)
- [Arquitetura Camada IA](./arquitetura-camada-ia-proativo.md) 