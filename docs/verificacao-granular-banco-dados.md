# Verificação Granular do Banco de Dados

## Visão Geral

A nova versão do sistema de inicialização implementa uma **verificação granular** do banco de dados que analisa cada tabela individualmente e executa apenas os scripts necessários para popular as tabelas vazias.

## Como Funcionava Antes

### Verificação Simples
```bash
📊 Registros encontrados:
   Equipamentos: 25
   Manutenções: 40
   Falhas: 15
   Total: 80

# Se total > 0 → "Banco tem dados, não faz nada"
# Se total = 0 → "Banco vazio, executa TUDO"
```

### Problemas da Abordagem Anterior
- ❌ **Tudo ou nada**: Ou executava todos os scripts ou nenhum
- ❌ **Ineficiente**: Repovoava tabelas que já tinham dados
- ❌ **Sem granularidade**: Não identificava tabelas específicas vazias
- ❌ **Recuperação difícil**: Se uma etapa falhasse, tinha que refazer tudo

## Como Funciona Agora

### Verificação Granular
```bash
📊 Status detalhado do banco:
   Equipamentos: 25 ✅
   Manutenções: 40 ✅
   Falhas: 15 ✅
   Localidades SAP: 0 ❌
   Planos PMM_2: 0 ❌
   Total: 80

📋 Tabelas que precisam ser populadas: sap_location, pmm_2

📋 Scripts a executar:
   ✅ import_localidades_sap
   ✅ populate_pmm_2
   ⏭️  create_tables (não necessário)
   ⏭️  populate_database (não necessário)
   ⏭️  correlate_equipment_locations (não necessário)
```

### Vantagens da Nova Abordagem
- ✅ **Eficiência**: Executa apenas os scripts necessários
- ✅ **Granularidade**: Identifica exatamente quais tabelas precisam ser populadas
- ✅ **Recuperação**: Se uma etapa falhar, não refaz o que já está completo
- ✅ **Flexibilidade**: Pode popular tabelas específicas
- ✅ **Inteligência**: Analisa dependências entre tabelas

## Estados do Banco

### 1. `populated` - Banco Completo
```bash
📊 Status detalhado do banco:
   Equipamentos: 25 ✅
   Manutenções: 40 ✅
   Falhas: 15 ✅
   Localidades SAP: 41 ✅
   Planos PMM_2: 214 ✅
   Total: 335

✅ Banco já está completamente populado
```
**Ação**: Nenhuma

### 2. `empty` - Banco Vazio
```bash
📊 Status detalhado do banco:
   Equipamentos: 0 ❌
   Manutenções: 0 ❌
   Falhas: 0 ❌
   Localidades SAP: 0 ❌
   Planos PMM_2: 0 ❌
   Total: 0

💡 Banco vazio - configuração completa necessária
```
**Ação**: Executa todos os scripts

### 3. `partial_population` - População Parcial
```bash
📊 Status detalhado do banco:
   Equipamentos: 25 ✅
   Manutenções: 40 ✅
   Falhas: 15 ✅
   Localidades SAP: 0 ❌
   Planos PMM_2: 0 ❌
   Total: 80

📋 Algumas tabelas precisam ser populadas: sap_location, pmm_2
```
**Ação**: Executa apenas os scripts necessários

### 4. `missing_tables` - Tabelas Faltando
```bash
📊 Status detalhado do banco:
   Equipamentos: 25 ✅
   Manutenções: 40 ✅
   Falhas: 15 ✅
   Localidades SAP: 0 ❌ (tabela não existe)
   Planos PMM_2: 0 ❌ (tabela não existe)

🔧 Algumas tabelas não existem - criação necessária
```
**Ação**: Cria tabelas e executa scripts necessários

## Lógica de Determinação de Scripts

### Scripts Críticos (Sempre executados se necessário)
- `create_tables.py` - Se tabelas não existem
- `populate_database.py` - Se dados básicos estão vazios

### Scripts Condicionais (Executados conforme necessidade)
- `import_localidades_sap.py` - Se tabela `sap_location` está vazia
- `correlate_equipment_locations.py` - Se equipamentos e localidades existem mas não estão correlacionados
- `populate_pmm_2.py` - Se tabela `pmm_2` está vazia

### Dependências Inteligentes
```python
# Correlação só executa se tem equipamentos E localidades
if (not status['equipment']['needs_population'] and 
    not status['sap_location']['needs_population']):
    scripts_to_run['correlate_equipment_locations'] = True
```

## Exemplos de Uso

### Cenário 1: Banco Novo
```bash
🚀 PROATIVO - CONFIGURAÇÃO AUTOMÁTICA INTELIGENTE
📊 Status detalhado do banco:
   Equipamentos: 0 ❌
   Manutenções: 0 ❌
   Falhas: 0 ❌
   Localidades SAP: 0 ❌
   Planos PMM_2: 0 ❌
   Total: 0

💡 Banco vazio - configuração completa necessária

📋 Scripts a executar:
   ✅ create_tables
   ✅ populate_database
   ✅ import_localidades_sap
   ✅ correlate_equipment_locations
   ✅ populate_pmm_2
```

### Cenário 2: Falha na Importação de Localidades
```bash
📊 Status detalhado do banco:
   Equipamentos: 25 ✅
   Manutenções: 40 ✅
   Falhas: 15 ✅
   Localidades SAP: 0 ❌
   Planos PMM_2: 214 ✅
   Total: 254

📋 Algumas tabelas precisam ser populadas: sap_location

📋 Scripts a executar:
   ✅ import_localidades_sap
   ✅ correlate_equipment_locations
   ⏭️  create_tables (não necessário)
   ⏭️  populate_database (não necessário)
   ⏭️  populate_pmm_2 (não necessário)
```

### Cenário 3: Arquivo PMM_2 Adicionado Posteriormente
```bash
📊 Status detalhado do banco:
   Equipamentos: 25 ✅
   Manutenções: 40 ✅
   Falhas: 15 ✅
   Localidades SAP: 41 ✅
   Planos PMM_2: 0 ❌
   Total: 121

📋 Algumas tabelas precisam ser populadas: pmm_2

📋 Scripts a executar:
   ✅ populate_pmm_2
   ⏭️  create_tables (não necessário)
   ⏭️  populate_database (não necessário)
   ⏭️  import_localidades_sap (não necessário)
   ⏭️  correlate_equipment_locations (não necessário)
```

## Função `check_database_status()`

### Estrutura do Retorno
```python
{
    'equipment': {
        'count': 25,
        'needs_population': False,
        'table_exists': True
    },
    'maintenance': {
        'count': 40,
        'needs_population': False,
        'table_exists': True
    },
    'failure': {
        'count': 15,
        'needs_population': False,
        'table_exists': True
    },
    'sap_location': {
        'count': 0,
        'needs_population': True,
        'table_exists': True
    },
    'pmm_2': {
        'count': 0,
        'needs_population': True,
        'table_exists': True
    }
}
```

### Campos Explicados
- `count`: Número de registros na tabela
- `needs_population`: `True` se a tabela está vazia (count = 0)
- `table_exists`: `True` se a tabela existe no banco

## Função `determine_required_scripts()`

### Lógica de Decisão
```python
def determine_required_scripts(status, status_type):
    # Configuração completa
    if status_type in ["empty", "missing_tables", "error"]:
        return "executa_tudo"
    
    # População seletiva
    elif status_type == "partial_population":
        return "executa_apenas_necessarios"
    
    # Nada a fazer
    elif status_type == "populated":
        return "nada_a_fazer"
```

## Benefícios da Implementação

### 1. **Performance**
- ⚡ Executa apenas o necessário
- ⚡ Não reprocessa dados existentes
- ⚡ Reduz tempo de inicialização

### 2. **Robustez**
- 🛡️ Recuperação automática de falhas parciais
- 🛡️ Não perde dados existentes
- 🛡️ Continua funcional mesmo com falhas não-críticas

### 3. **Manutenibilidade**
- 🔧 Fácil adicionar novas tabelas
- 🔧 Lógica clara e extensível
- 🔧 Logs detalhados para debugging

### 4. **Experiência do Usuário**
- 👥 Feedback claro sobre o que será executado
- 👥 Progresso visível de cada etapa
- 👥 Mensagens informativas sobre o status

## Conclusão

A verificação granular torna o sistema de inicialização do banco **mais inteligente, eficiente e robusto**, executando apenas o que é necessário e fornecendo feedback detalhado sobre o estado de cada tabela. 