# LLMService - Documentação Técnica Detalhada

## 📋 Visão Geral

O **LLMService** é o núcleo da inteligência artificial do sistema PROAtivo, responsável pela integração com o Google Gemini 2.5 Flash e orquestração de todo o pipeline de IA.

## 🏗️ Arquitetura do LLMService

### **Componentes Integrados**
```python
class LLMService:
    - Google Gemini 2.5 Flash API
    - CacheService (opcional)
    - FallbackService (opcional)
    - Métricas e monitoramento
    - Sistema de retry automático
```

### **Inicialização Inteligente**
```python
def __init__(self):
    # Inicialização graceful - serviços opcionais
    self.fallback_service = None
    self.cache_service = None
    self._init_optional_services()  # Não quebra se serviços ausentes
```

## 🔧 Configurações Técnicas

### **Parâmetros do Google Gemini**
| Parâmetro | Valor | Justificativa |
|-----------|-------|---------------|
| **Model** | `gemini-2.5-flash` | Última versão, otimizada para speed |
| **Temperature** | `0.2` | Baixa criatividade, alta precisão |
| **Max Tokens** | `1500` | Suficiente para respostas detalhadas |
| **Top P** | `0.95` | Controle de qualidade |
| **Top K** | `40` | Diversidade controlada |
| **Timeout** | `30s` | Balance entre qualidade e UX |
| **Max Retries** | `3` | Resiliência a falhas temporárias |

### **Safety Settings**
```python
safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: BLOCK_MEDIUM_AND_ABOVE,
}
```

## 🚀 Funcionalidades Principais

### **1. Generate Response (Método Principal)**
```python
async def generate_response(
    user_query: str,
    sql_query: Optional[str] = None,
    query_results: Optional[List[Dict[str, Any]]] = None,
    context: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    cache_strategy: str = "normalized_match"
) -> Dict[str, Any]
```

**Pipeline de Processamento:**
1. **Validação de Entrada** - Query não pode estar vazia
2. **Cache Check** - Busca resposta em cache inteligente
3. **Prompt Generation** - Cria prompts especializados
4. **LLM Call** - Chama Google Gemini com retry
5. **Response Validation** - Valida qualidade da resposta
6. **Fallback Check** - Verifica se precisa usar fallback
7. **Cache Storage** - Armazena resposta para futuro uso
8. **Response Return** - Retorna resposta estruturada

### **2. Prompt Engineering Especializado**

#### **System Prompt**
```python
"""Você é um assistente especializado em manutenção de equipamentos elétricos para o sistema PROAtivo.

CONTEXTO DO SISTEMA:
- Empresa: Setor elétrico/energético  
- Dados: Equipamentos, manutenções, falhas, custos
- Objetivo: Apoio à decisão técnica baseada em dados

INSTRUÇÕES FUNDAMENTAIS:
1. Responda SEMPRE em português brasileiro
2. Use linguagem técnica mas acessível
3. Seja preciso com números, datas e dados técnicos
4. Sugira ações quando apropriado
5. Se não souber ou dados insuficientes, diga claramente
6. Mantenha respostas objetivas e focadas
"""
```

#### **User Prompt Dinâmico**
```python
def _create_user_prompt(self, user_query, retrieved_data, context):
    # Organiza dados encontrados
    # Adiciona contexto relevante
    # Formata para máxima clareza
```

### **3. Sistema de Retry Robusto**
```python
async def _call_gemini_with_retry(self, prompt: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            # Timeout configurável
            response = await asyncio.wait_for(
                asyncio.to_thread(self._model.generate_content, prompt),
                timeout=self.settings.gemini_timeout
            )
            return response.text.strip()
        except asyncio.TimeoutError:
            # Backoff exponencial: 2^attempt segundos
            await asyncio.sleep(2 ** attempt)
        except google_exceptions.ResourceExhausted:
            # Quota excedida - não adianta retry
            break
```

### **4. Validação de Resposta Inteligente**
```python
def _validate_and_clean_response(self, response: str) -> str:
    # Valida tamanho mínimo/máximo
    # Remove conteúdo inadequado
    # Detecta respostas repetitivas
    # Trunca se necessário
```

### **5. Cálculo de Confiança**
```python
def _calculate_confidence_score(self, user_query, retrieved_data, response):
    score = 0.0
    
    # Base score se há dados
    if retrieved_data:
        score += 0.4
    
    # Score por quantidade de dados
    data_count = len(retrieved_data)
    score += min(0.3, data_count * 0.05)
    
    # Score por detalhamento da resposta
    if len(response) > 100:
        score += 0.2
    
    # Penalizar incerteza
    uncertainty_phrases = ["não sei", "não tenho", "incerto"]
    if any(phrase in response.lower() for phrase in uncertainty_phrases):
        score -= 0.2
    
    return max(0.0, min(1.0, score))
```

## 🔍 Integração com Cache

### **Cache Inteligente**
```python
# Busca no cache com múltiplas estratégias
cached_response = await self.cache_service.get(
    query=user_query,
    context=context,
    strategy=cache_strategy  # exact, normalized, semantic, fuzzy
)

if cached_response:
    self.cache_hits += 1
    cached_response["processing_time"] = processing_time
    return cached_response
```

### **TTL Dinâmico**
```python
def _calculate_cache_ttl(self, confidence_score: float, data_records: int) -> int:
    base_ttl = 3600  # 1 hora
    
    # Respostas mais confiáveis ficam mais tempo
    confidence_multiplier = 0.5 + (confidence_score * 1.5)
    
    # Mais dados = mais tempo no cache
    data_multiplier = 1.0 + min(0.5, data_records / 20)
    
    ttl = int(base_ttl * confidence_multiplier * data_multiplier)
    return max(1800, min(14400, ttl))  # 30min - 4h
```

## 🛡️ Sistema de Fallback Integrado

### **Detecção Automática**
```python
# Verifica se resposta do LLM é adequada
should_fallback, fallback_trigger = self.fallback_service.should_use_fallback(
    llm_response=llm_response,
    original_query=user_query,
    llm_confidence=confidence_score,
    error=None
)

if should_fallback:
    return await self._generate_fallback_response(
        user_query, fallback_trigger, start_time, session_id, context
    )
```

### **Triggers de Fallback**
- **LLM_ERROR** - Erro na API
- **TIMEOUT** - Timeout na chamada
- **LOW_CONFIDENCE** - Confiança < 0.5
- **EMPTY_RESPONSE** - Resposta vazia
- **API_QUOTA_EXCEEDED** - Quota da API
- **INVALID_RESPONSE** - Resposta inválida

## 📊 Métricas e Monitoramento

### **Métricas Coletadas**
```python
# Contadores básicos
self.request_count = 0
self.cache_hits = 0
self.error_count = 0
self.fallback_used_count = 0

# Métricas calculadas
cache_hit_rate = (self.cache_hits / self.request_count) if self.request_count > 0 else 0
error_rate = (self.error_count / self.request_count) if self.request_count > 0 else 0
fallback_rate = (self.fallback_used_count / self.request_count) if self.request_count > 0 else 0
```

### **Health Check Avançado**
```python
async def health_check(self) -> Dict[str, Any]:
    # Teste de conectividade com Gemini
    test_response = await self._model.generate_content("Test")
    
    # Status baseado em métricas
    if gemini_status == "healthy" and error_rate < 0.1:
        llm_overall_status = "healthy"
    elif gemini_status == "healthy" and error_rate < 0.3:
        llm_overall_status = "warning"
    else:
        llm_overall_status = "critical"
```

## ⚡ Performance e Otimizações

### **Async/Await Throughout**
- Todas as operações I/O são assíncronas
- Non-blocking para alta concorrência
- Timeout em todas as operações externas

### **Lazy Loading**
- Serviços opcionais carregados sob demanda
- Fallback gracioso se dependências ausentes
- Inicialização rápida

### **Memory Management**
- Cache com size limits
- Eviction automática
- Cleanup de objetos temporários

### **Error Handling Robusto**
```python
try:
    # Operação principal
    response = await self._call_gemini_with_retry(prompt)
except Exception as e:
    # Fallback automático
    if self.fallback_service:
        return await self._generate_fallback_response(...)
    else:
        # Emergency response
        return {
            "response": "Desculpe, erro técnico temporário...",
            "confidence_score": 0.1,
            "fallback_used": True
        }
```

## 🔮 Próximas Melhorias

### **Planejadas**
- **Streaming Responses** - Para respostas longas
- **Multi-model Support** - OpenAI GPT-4, Claude
- **Function Calling** - Gemini function calling para consultas complexas
- **Embedding Cache** - Cache baseado em semantic vectors
- **Real-time Learning** - Feedback loop para melhoria contínua

### **Otimizações de Performance**
- **Connection Pooling** - Para chamadas HTTP
- **Response Compression** - Reduzir overhead de rede
- **Parallel Processing** - Para múltiplas queries
- **Edge Caching** - CDN para respostas frequentes

---

**Status:** ✅ **Produção Ready**  
**Cobertura de Testes:** 27 cenários unitários  
**Performance:** < 2000ms (target)  
**Reliability:** 100% (com fallback)  
**Scalability:** Horizontal scaling ready 