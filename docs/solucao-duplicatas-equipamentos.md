# Solução para Problema de Duplicatas de Equipamentos

## 🔍 Diagnóstico do Problema

### Sintomas Observados
- Erro `duplicate key value violates unique constraint "equipments_code_key"`
- Script de população falhando com códigos TR-001, TR-002, DJ-001, etc.
- Mensagem: "Key (code)=(TR-001) already exists"

### Causa Raiz
O script de população tentava inserir equipamentos que já existiam no banco de dados, sem verificar duplicatas primeiro.

**Problema no Código:**
```python
# ❌ Versão antiga (data_processor.py)
await self.repository_manager.equipment.create(**eq_data)  # Falha se já existe
```

**Localização:**
- Arquivo: `src/etl/data_processor.py`
- Função: `save_to_database()` (linhas 231-290)
- Issue: Falta de lógica "upsert" (insert ou update)

## 🛠️ Solução Implementada

### 1. Modificação do DataProcessor

**✅ Nova implementação com lógica upsert:**
```python
# Verifica se equipamento já existe pelo código
equipment_code = eq_data.get('code')
if equipment_code:
    existing_equipment = await self.repository_manager.equipment.get_by_code(equipment_code)
    
    if existing_equipment:
        # Atualiza equipamento existente
        await self.repository_manager.equipment.update(existing_equipment.id, **eq_data)
        updated_count += 1
    else:
        # Cria novo equipamento
        await self.repository_manager.equipment.create(**eq_data)
        saved_count += 1
```

**Vantagens:**
- ✅ Não falha com duplicatas
- ✅ Atualiza dados existentes
- ✅ Cria novos quando necessário
- ✅ Log detalhado de operações

### 2. Script de Limpeza de Duplicatas

**Arquivo:** `scripts/maintenance/clean_duplicate_equipment.py`

**Funcionalidades:**
- 🔍 Identifica equipamentos duplicados por código
- 🗑️ Remove duplicatas mantendo o registro mais recente
- ✅ Verifica resultado da limpeza
- 📊 Relatório detalhado de operações

**Como usar:**
```bash
cd proativo
python scripts/maintenance/clean_duplicate_equipment.py
```

### 3. Script de População Melhorado (V3)

**Arquivo:** `scripts/setup/populate_database_v3.py`

**Melhorias:**
- 🔄 Usa lógica upsert automaticamente
- 📊 Estatísticas em tempo real
- 🛡️ Tratamento robusto de erros
- 📝 Logs detalhados com emojis
- ⚡ Performance otimizada

**Como usar:**
```bash
cd proativo
python scripts/setup/populate_database_v3.py
```

## 📋 Plano de Execução

### Cenário 1: Banco com Duplicatas Existentes

1. **Limpar duplicatas:**
   ```bash
   python scripts/maintenance/clean_duplicate_equipment.py
   ```

2. **Popular dados:**
   ```bash
   python scripts/setup/populate_database_v3.py
   ```

### Cenário 2: Banco Limpo

1. **Popular diretamente:**
   ```bash
   python scripts/setup/populate_database_v3.py
   ```

## 🔧 Arquivos Modificados

| Arquivo | Tipo | Descrição |
|---------|------|-----------|
| `src/etl/data_processor.py` | Modificado | Implementou lógica upsert |
| `scripts/maintenance/clean_duplicate_equipment.py` | Novo | Script de limpeza |
| `scripts/setup/populate_database_v3.py` | Novo | Script melhorado |
| `docs/solucao-duplicatas-equipamentos.md` | Novo | Esta documentação |

## 📊 Logs Esperados (Após Correção)

### Logs de Sucesso:
```
✅ Equipamento atualizado: TR-001
✅ Equipamento criado: TR-NEW
📊 Equipamentos processados: 5 criados, 20 atualizados
```

### Logs de Limpeza:
```
✅ Removido equipamento ID abc-123 (código: TR-001)
🎉 LIMPEZA CONCLUÍDA COM SUCESSO!
   Equipamentos removidos: 15
```

## 🧪 Testando a Solução

### Teste 1: Verificar se duplicatas foram resolvidas
```bash
# No banco PostgreSQL
SELECT code, COUNT(*) as count 
FROM equipments 
GROUP BY code 
HAVING COUNT(*) > 1;
```
**Resultado esperado:** Nenhum registro (tabela vazia)

### Teste 2: Executar população novamente
```bash
python scripts/setup/populate_database_v3.py
```
**Resultado esperado:** Nenhum erro, apenas updates

### Teste 3: Verificar estatísticas
```python
# No Python
from src.database.repositories import RepositoryManager
# ... código para contar equipamentos
```

## 🚀 Benefícios da Solução

- **🛡️ Robustez:** Não falha mais com duplicatas
- **🔄 Idempotência:** Pode ser executado múltiplas vezes
- **📊 Visibilidade:** Logs claros sobre o que acontece
- **⚡ Eficiência:** Atualiza apenas o necessário
- **🧹 Limpeza:** Scripts dedicados para manutenção

## 🔮 Prevenção Futura

### Boas Práticas Implementadas:

1. **Validação na origem:** Verificar duplicatas antes de inserir
2. **Lógica upsert:** Sempre usar insert ou update
3. **Logging detalhado:** Rastrear todas as operações
4. **Scripts de manutenção:** Ferramentas para limpeza periódica
5. **Testes automatizados:** Verificar integridade regularmente

### Monitoramento:

```sql
-- Query para monitorar duplicatas
SELECT 
    code,
    COUNT(*) as duplicates,
    MIN(created_at) as first_created,
    MAX(created_at) as last_created
FROM equipments 
GROUP BY code 
HAVING COUNT(*) > 1;
```

---

**Status:** ✅ Problema resolvido  
**Data:** Janeiro 2025  
**Versão:** 1.0 