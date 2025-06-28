# Solução para Problema de Mapeamento de Campos de Manutenção

## 🔍 Diagnóstico do Problema

### Sintomas Observados
- Erro: `Equipamento 'None' não encontrado`
- Logs mostram: `⚠️ Equipamento 'None' não encontrado` repetidamente
- Conversões falhando: `🔄 Conversões: 0 sucesso, 25 falhas`

### Causa Raiz
O processador CSV de manutenções estava perdendo o campo `equipment_id` durante a conversão para dicionário. Especificamente:

1. **Problema no Mapeamento de Colunas**: Mapeamento incompleto para os campos reais dos CSVs
2. **Perda de Dados na Conversão**: Lógica `if pd.notna(value)` removia campos com valores válidos
3. **Falta de Logs Detalhados**: Impossível debugar onde o campo estava sendo perdido

## 🛠️ Solução Implementada

### 1. Correção do Processador CSV

**Arquivo**: `src/etl/processors/csv_processor.py`

#### Melhorias na Função `process_maintenance_csv()`:

```python
# ✅ NOVO: Logs detalhados
logger.info(f"CSV lido com {len(df)} linhas e colunas: {list(df.columns)}")

# ✅ NOVO: Mapeamento completo baseado nos arquivos reais
column_mapping = {
    'equipment_id': 'equipment_id',
    'id': 'maintenance_code',              # Campo real: id
    'order_number': 'maintenance_code',    # Campo real: order_number  
    'type': 'maintenance_type',            # Campo real: type
    'priority': 'priority',                # Campo real: priority
    'status': 'status',                    # Campo real: status
    'description': 'title',                # Campo real: description
    'cost': 'estimated_cost',              # Campo real: cost
    'technician_team': 'technician',       # Campo real: technician_team
    # ... mais mapeamentos
}

# ✅ NOVO: Preservação do equipment_id
for col, value in row.items():
    if pd.notna(value) and value != '':
        # Processar valor válido
        record[col] = value
    else:
        # IMPORTANTE: preservar equipment_id mesmo se for None/vazio
        if col == 'equipment_id':
            record[col] = value if pd.notna(value) else None
```

### 2. Scripts de Diagnóstico

#### **Script de Debug**: `scripts/debugging/debug_maintenance_processing.py`
- Analisa passo a passo o processamento dos CSVs
- Identifica onde os campos são perdidos
- Mostra valores antes e depois de cada transformação

#### **Script de Correção**: `scripts/maintenance/fix_maintenance_mapping.py`
- Analisa a estrutura real dos arquivos CSV
- Testa o mapeamento corrigido
- Valida o fluxo completo de conversão

### 3. Mapeamento Baseado em Dados Reais

Com base na análise dos arquivos CSV reais, criamos mapeamento específico:

**maintenance_orders.csv**:
```csv
id,equipment_id,order_number,type,priority,status,scheduled_date,start_date,completion_date,description,cost,technician_team,created_at,updated_at
```

**maintenance_schedules.csv**:
```csv
id,equipment_id,maintenance_type,frequency_months,last_maintenance_date,next_maintenance_date,season_preference,estimated_duration_hours
```

## 🔧 Comandos para Executar no Docker

### 1. Diagnóstico Completo
```bash
# Executar script de diagnóstico
docker compose exec proativo-app python scripts/debugging/debug_maintenance_processing.py

# Executar script de correção e teste
docker compose exec proativo-app python scripts/maintenance/fix_maintenance_mapping.py
```

### 2. População Corrigida
```bash
# Limpar dados duplicados (se necessário)
docker compose exec proativo-app python scripts/maintenance/clean_duplicate_equipment.py

# Executar população com processamento corrigido
docker compose exec proativo-app python scripts/setup/populate_database_v3.py
```

### 3. Validação
```bash
# Verificar se os dados foram importados corretamente
docker compose exec proativo-app python scripts/testing/validate_system.py
```

## 📊 Resultados Esperados

### Antes da Correção
```
⚠️  Equipamento 'None' não encontrado
⚠️  Equipamento 'None' não encontrado
🔄 Conversões: 0 sucesso, 25 falhas
```

### Após a Correção
```
✅ Campo equipment_id encontrado. Amostras: ['TR-001', 'DJ-001', 'TR-002']
✅ Conversão: TR-001 -> f47ac10b-58cc-4372-a567-0e02b2c3d479
🔄 Conversões: 25 sucesso, 0 falhas
```

## 🎯 Validação da Solução

### Checklist de Verificação
- [ ] Campo `equipment_id` preservado durante processamento
- [ ] Mapeamento de colunas funcionando corretamente
- [ ] Conversão de códigos para UUIDs funcionando
- [ ] Logs detalhados disponíveis para debug
- [ ] Todos os arquivos CSV processados sem erros

### Comandos de Teste
```bash
# 1. Testar processamento isolado
docker compose exec proativo-app python scripts/debugging/debug_maintenance_processing.py

# 2. Testar conversão de UUIDs
docker compose exec proativo-app python scripts/maintenance/fix_maintenance_mapping.py

# 3. Testar população completa
docker compose exec proativo-app python scripts/setup/populate_database_v3.py
```

## 📋 Próximos Passos

1. **Executar Diagnóstico**: Rodar script de debug para confirmar o problema
2. **Aplicar Correção**: Executar script de população corrigido
3. **Validar Dados**: Verificar se manutenções foram importadas corretamente
4. **Monitorar**: Acompanhar logs para garantir funcionamento contínuo

## 🔍 Troubleshooting

### Se ainda houver problemas:

1. **Verificar Logs Detalhados**:
   ```bash
   docker compose logs proativo-app -f
   ```

2. **Executar Diagnóstico Isolado**:
   ```bash
   docker compose exec proativo-app python scripts/debugging/debug_maintenance_processing.py
   ```

3. **Verificar Estrutura dos CSVs**:
   ```bash
   docker compose exec proativo-app head -n 3 data/samples/maintenance_orders.csv
   ```

### Problemas Comuns:
- **Equipment_id ainda None**: Verificar se o mapeamento está correto
- **Conversão falhando**: Equipamentos podem não estar no banco ainda
- **Arquivo não encontrado**: Verificar se CSVs estão no diretório correto

## 💡 Lições Aprendidas

1. **Importância de Logs Detalhados**: Logs ajudam a identificar rapidamente onde dados são perdidos
2. **Mapeamento Baseado em Dados Reais**: Sempre analisar arquivos reais antes de criar mapeamentos
3. **Preservação de Campos Críticos**: Campos como `equipment_id` precisam ser preservados mesmo quando None
4. **Testes Isolados**: Scripts de debug são essenciais para troubleshooting 