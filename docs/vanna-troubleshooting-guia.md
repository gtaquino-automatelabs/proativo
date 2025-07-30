# Guia de Troubleshooting - Vanna.ai

**Data:** 01/01/2025  
**Status:** 🛠️ RESOLUÇÃO DE PROBLEMAS  
**Versão:** 1.0

## 🚨 Problema Principal: Erro NumPy 2.0 com ChromaDB

### Sintomas
```
AttributeError: `np.float_` was removed in the NumPy 2.0 release. Use `np.float64` instead.
```

### Causa
O ChromaDB usado pelo Vanna.ai não é compatível com NumPy 2.0+, pois usa APIs que foram removidas.

### ✅ Solução

1. **Atualizar requirements.txt** (já implementado):
```bash
# Versões específicas para compatibilidade
vanna>=0.7.9
chromadb>=0.4.0,<0.5.0  
numpy>=1.21.0,<2.0.0    # Crítico: manter < 2.0.0
```

2. **Reinstalar dependências**:
```bash
# Desinstalar versões incompatíveis
pip uninstall numpy chromadb vanna -y

# Instalar versões compatíveis
pip install 'numpy>=1.21.0,<2.0.0' 'chromadb>=0.4.0,<0.5.0' 'vanna>=0.7.9'
```

3. **Verificar instalação**:
```bash
python -c "import numpy; print('NumPy:', numpy.__version__)"
python -c "import chromadb; print('ChromaDB:', chromadb.__version__)"  
python -c "import vanna; print('Vanna:', vanna.__version__)"
```

## 🔍 Outros Problemas Comuns

### Problema: Erro de definição de classes

**Sintoma:** `NameError: name 'Gemini_Chat' is not defined`

**Causa:** Classes sendo definidas fora do bloco de importação segura

**Solução:** ✅ **JÁ IMPLEMENTADA** - As classes agora são definidas dentro do bloco try/except com fallbacks apropriados.

### Problema: Vanna não inicializa

**Sintomas:**
- Sistema funciona apenas em modo fallback
- Log: "Vanna.ai not available"

**Verificação:**
```bash
# Via API admin
curl http://localhost:8000/admin/vanna/status

# Via Python
python -c "
from src.api.services.vanna_service import get_vanna_service
service = get_vanna_service()
print('Inicializado:', service.is_initialized)
"
```

**Soluções:**

1. **Dependências faltando:**
```bash
pip install vanna chromadb numpy
```

2. **API keys não configuradas:**
```bash
# Para Gemini
export GOOGLE_API_KEY="sua-chave-aqui"

# Para OpenAI  
export OPENAI_API_KEY="sua-chave-aqui"
```

3. **Problemas de permissão de diretório:**
```bash
mkdir -p ./data/vanna_vectordb
chmod 755 ./data/vanna_vectordb
```

### Problema: ChromaDB não conecta

**Sintomas:**
- Erro ao inicializar vector store
- "Connection refused" ou similar

**Soluções:**

1. **Limpar cache do ChromaDB:**
```bash
rm -rf ./data/vanna_vectordb/*
```

2. **Verificar permissões:**
```bash
ls -la ./data/vanna_vectordb/
# Deve ter permissões de leitura/escrita
```

3. **Recriar base vectorial:**
```bash
python scripts/vanna/setup_vanna_model.py
```

### Problema: SQL incorreto gerado

**Sintomas:**
- Confiança baixa consistente
- SQL não funciona com schema

**Soluções:**

1. **Re-treinar modelo:**
```bash
python scripts/vanna/setup_vanna_model.py
```

2. **Verificar schema do banco:**
```bash
# Via database
python -c "
from src.database.connection import get_database_session
import asyncio
from sqlalchemy import text

async def check_schema():
    async with get_database_session() as db:
        result = await db.execute(text('SELECT table_name FROM information_schema.tables WHERE table_schema = \\'public\\';'))
        tables = [row[0] for row in result.fetchall()]
        print('Tabelas encontradas:', tables)

asyncio.run(check_schema())
"
```

3. **Adicionar exemplos específicos:**
```python
from src.api.services.vanna_service import get_vanna_service
service = get_vanna_service()

service.vanna.train(
    question="Sua pergunta específica",
    sql="SELECT correta correspondente;"
)
```

## 🛠️ Comandos de Diagnóstico

### Verificação Completa do Sistema
```bash
# 1. Verificar status via API
curl http://localhost:8000/admin/vanna/status | python -m json.tool

# 2. Logs detalhados
tail -f logs/proativo.log | grep -i vanna

# 3. Teste manual de geração SQL
python -c "
import asyncio
from src.api.services.vanna_query_processor import get_vanna_query_processor

async def test_query():
    processor = get_vanna_query_processor()
    result = await processor.process_query('Quantos equipamentos temos?')
    print('SQL:', result.sql_query)
    print('Método:', result.processing_method)
    print('Confiança:', result.confidence_score)

asyncio.run(test_query())
"
```

### Verificação de Dependências
```bash
docker exec proativo-app pip list | Select-String -Pattern "(vanna|chromadb|numpy)"
```

### Reset Completo (último recurso)
```bash
# 1. Parar sistema
docker-compose down

# 2. Limpar dados Vanna
rm -rf ./data/vanna_vectordb

# 3. Reinstalar dependências
pip uninstall vanna chromadb numpy -y
pip install -r requirements.txt

# 4. Recriar setup
python scripts/vanna/setup_vanna_model.py

# 5. Reiniciar sistema
docker-compose up -d
```

## 📊 Monitoramento Contínuo

### Métricas a Observar
- **Taxa de inicialização**: Vanna.is_initialized deve ser `true`
- **Taxa de uso Vanna vs Fallback**: Ideal >70% Vanna
- **Confiança média**: Ideal >0.7
- **Tempo de resposta**: <2 segundos para queries simples

### Alertas Recomendados
- Fallback rate >80% por >1 hora
- Vanna initialization failed
- ChromaDB connection errors
- NumPy compatibility warnings

## 🚀 Prevenção de Problemas

### Dockerfile/Docker-compose
```dockerfile
# Especificar versões exatas
RUN pip install 'numpy>=1.21.0,<2.0.0' 'chromadb>=0.4.0,<0.5.0' 'vanna>=0.7.9'
```

### CI/CD
```yaml
# Teste de compatibilidade em pipeline
- name: Test Vanna Compatibility
  run: |
    python -c "import vanna, chromadb, numpy; print('All imports OK')"
    python scripts/vanna/setup_vanna_model.py --test-only
```

### Monitoramento Automático
```python
# Healthcheck personalizado
async def vanna_health_check():
    from src.api.services.vanna_service import get_vanna_service
    service = get_vanna_service()
    return {
        "vanna_ready": service.is_initialized,
        "last_check": datetime.now().isoformat()
    }
```

## 📞 Escalação de Suporte

### Nível 1: Reinicialização
1. Restart containers
2. Verificar logs
3. Testar endpoint /admin/vanna/status

### Nível 2: Reconfiguração  
1. Verificar dependências
2. Re-executar setup do Vanna
3. Limpar cache vectorial

### Nível 3: Investigação Profunda
1. Análise de compatibilidade de versões
2. Debug de inicialização do ChromaDB
3. Validação manual do schema training

---

**Contato:** Sistema PROAtivo  
**Última atualização:** 01/01/2025  
**Próxima revisão:** Quando nova versão do ChromaDB for lançada 