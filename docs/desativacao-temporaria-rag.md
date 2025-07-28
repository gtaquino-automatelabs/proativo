# Desativação Temporária do Sistema RAG - PROAtivo

**Data da Modificação**: 28 de Julho de 2025  
**Motivo**: Ausência de documentos de texto para indexação  
**Status**: RAG desabilitado temporariamente  
**Impacto**: Sistema continua funcional usando apenas dados SQL estruturados  

---

## 📋 **Resumo da Alteração**

O sistema RAG (Retrieval-Augmented Generation) foi **temporariamente desabilitado** devido à ausência de documentos de texto para indexação. A implementação foi **preservada completamente** através de comentários, permitindo reativação rápida no futuro.

### **Antes vs Depois**
- **ANTES**: LLM + RAG + SQL → Respostas enriquecidas com documentos
- **DEPOIS**: LLM + SQL → Respostas baseadas apenas em dados estruturados

---

## 🔍 **Justificativa Técnica**

### **Problema Identificado**
```python
# Problema: query_results = [] confundia o LLM
# LLM interpretava como "não há informação suficiente"
# Mesmo tendo dados SQL válidos disponíveis
```

### **Solução Implementada**
```python
# Solução: query_results = None vs [] vs [dados]
# None    = RAG não executado (não mencionar no prompt)
# []      = RAG executado mas vazio (mencionar busca sem resultado)  
# [dados] = RAG executado com sucesso (incluir no contexto)
```

---

## 📂 **Arquivos Modificados**

### **1. `/src/api/endpoints/chat.py`**
**Linhas afetadas**: 12, 214-250, 274-285, 300

**Modificações:**
- Import RAGService comentado
- Flag `RAG_ENABLED = False` adicionada
- Seção RAG completa comentada (linhas 214-234)
- Lógica condicional para `query_results`

### **2. `/src/api/services/llm_service.py`**
**Linhas afetadas**: 448, 520-530, 166, 240-280, 580-610, 850-920

**Modificações:**
- `query_results` alterado para `Optional[List[Dict]]`
- `_create_user_prompt` trata `None` vs `[]`
- `_generate_suggestions` adaptado
- Logs incluem flag `rag_enabled`

---

## 🔄 **Como Reativar o Sistema RAG**

### **Pré-requisitos para Reativação**
- [ ] **Documentos disponíveis**: Manuais técnicos, procedimentos, especificações
- [ ] **Formato dos documentos**: PDF, TXT, MD, DOCX suportados
- [ ] **Estrutura de diretórios**: `/data/documents/` criada
- [ ] **Testes de indexação**: Verificar que documentos são indexáveis

### **Passo 1: Habilitar Flag RAG**
```python
# Arquivo: src/api/endpoints/chat.py
# Linha ~217

# DE:
RAG_ENABLED = False

# PARA:
RAG_ENABLED = True
```

### **Passo 2: Descomentar Import**
```python
# Arquivo: src/api/endpoints/chat.py
# Linha ~12

# DE:
# from ..services.rag_service import RAGService  # Comentado temporariamente - RAG desabilitado

# PARA:
from ..services.rag_service import RAGService
```

### **Passo 3: Descomentar Seção RAG**
```python
# Arquivo: src/api/endpoints/chat.py
# Linhas 214-234

# Descomentar TODO o bloco:
if RAG_ENABLED:
    # # 2. BUSCAR DADOS RELEVANTES VIA RAG
    # try:
    #     rag_service = RAGService()
    #     await rag_service.index_data_sources()
    #     rag_context = await rag_service.retrieve_context(query=request.message, max_chunks=5)
    #     
    #     # Preparar dados para o LLM
    #     for chunk in rag_context.chunks:
    #         query_results.append({
    #             "source": chunk.source,
    #             "content": chunk.content,
    #             "metadata": chunk.metadata,
    #             "score": chunk.score
    #         })
    #     
    #     logger.info(f"RAG retrieved {len(rag_context.chunks)} chunks")
    #     
    # except Exception as e:
    #     logger.error(f"RAG processing failed: {str(e)}")
    #     # Continuar sem RAG em caso de erro
    
# Remover os comentários (#) de todas as linhas acima
```

### **Passo 4: Adicionar Documentos**
```bash
# Criar estrutura de diretórios
mkdir -p data/documents/manuals
mkdir -p data/documents/procedures  
mkdir -p data/documents/specifications

# Adicionar documentos nos formatos:
# - PDF: Manuais de equipamentos
# - TXT: Procedimentos de manutenção
# - MD: Documentação técnica
# - DOCX: Especificações
```

### **Passo 5: Configurar RAGService**
```python
# Verificar se RAGService está configurado para ler documentos
# Arquivo: src/api/services/rag_service.py

# Adicionar novos tipos de documento se necessário:
SUPPORTED_EXTENSIONS = {'.pdf', '.txt', '.md', '.docx', '.doc'}
DOCUMENTS_PATH = "data/documents"
```

### **Passo 6: Teste de Reativação**
```python
# Script de teste (criar se necessário)
# test_rag_reactivation.py

async def test_rag_system():
    """Teste completo do RAG reativado"""
    
    # 1. Testar indexação
    rag_service = RAGService()
    await rag_service.index_data_sources()
    
    # 2. Testar busca
    results = await rag_service.retrieve_context(
        query="manual do transformador T001",
        max_chunks=5
    )
    
    # 3. Verificar resultados
    assert len(results.chunks) > 0
    print(f"✅ RAG encontrou {len(results.chunks)} documentos")
    
    # 4. Testar chat endpoint
    response = await chat_endpoint(ChatRequest(message="Como fazer manutenção preventiva?"))
    assert "query_results" in response
    print("✅ Chat endpoint funcionando com RAG")

if __name__ == "__main__":
    asyncio.run(test_rag_system())
```

---

## ✅ **Checklist de Verificação Pós-Reativação**

### **Funcionalidade**
- [ ] Sistema indexa documentos sem erro
- [ ] Busca por documentos retorna resultados relevantes
- [ ] Chat endpoint inclui `query_results` populado
- [ ] Respostas do LLM são mais ricas e detalhadas
- [ ] Cache de RAG funciona corretamente

### **Performance**
- [ ] Tempo de resposta aceitável (< 5 segundos)
- [ ] Uso de memória dentro dos limites
- [ ] Indexação não trava o sistema
- [ ] Cache evita reindexação desnecessária

### **Logs e Monitoramento**
- [ ] Logs mostram `rag_enabled: true`
- [ ] Contadores de documentos indexados
- [ ] Métricas de similaridade funcionando
- [ ] Erros de RAG são capturados adequadamente

### **Qualidade das Respostas**
- [ ] Respostas citam documentos específicos
- [ ] Informações são mais precisas e detalhadas
- [ ] LLM não confunde dados RAG com dados SQL
- [ ] Sugestões incluem opções baseadas em documentos

---

## 🚨 **Pontos de Atenção**

### **Segurança**
- **Documentos sensíveis**: Verificar que não há informações confidenciais sendo indexadas
- **Controle de acesso**: RAG deve respeitar permissões de usuário
- **Sanitização**: Documentos podem conter dados pessoais

### **Performance**
- **Volume de documentos**: Mais de 1000 docs pode degradar performance
- **Reindexação**: Estabelecer cronograma de atualização (diário/semanal)
- **Cache de embedding**: Verificar se cache funciona adequadamente

### **Manutenção**
- **Documentos desatualizados**: Processo para remover/atualizar docs
- **Versionamento**: Controlar versões de documentos indexados
- **Backup**: Fazer backup dos índices do RAG

---

## 📈 **Roadmap Futuro**

### **Fase 1: Reativação Básica**
- Documentos em formato simples (TXT, MD)
- Indexação manual
- Busca básica por similaridade

### **Fase 2: Integração Avançada**
- Upload automático de documentos via interface
- OCR para documentos escaneados
- Extração de metadados avançada

### **Fase 3: IA Avançada**
- Sumarização automática de documentos
- Classificação inteligente por tipo/equipamento
- Recomendações proativas baseadas em contexto

---

## 🔧 **Comandos Úteis**

### **Verificar Status do RAG**
```bash
# Via logs
docker logs proativo-api-1 | grep "rag_enabled"

# Via endpoint de diagnóstico
curl http://localhost:8000/api/health/detailed
```

### **Resetar Cache do RAG**
```bash
# Limpar cache se necessário
docker exec proativo-api-1 rm -rf /tmp/rag_cache/*
```

### **Reindexar Documentos**
```bash
# Forçar reindexação
curl -X POST http://localhost:8000/api/rag/reindex
```

---

## 📞 **Contato e Suporte**

**Implementação**: Sistema PROAtivo - Análise Técnica Automatizada  
**Data**: 28 de Julho de 2025  
**Revisão**: Verificar este documento a cada 3 meses  

**Em caso de dúvidas**:
1. Consultar logs do sistema
2. Verificar este documento
3. Testar em ambiente de desenvolvimento primeiro
4. Documentar mudanças adicionais neste arquivo 