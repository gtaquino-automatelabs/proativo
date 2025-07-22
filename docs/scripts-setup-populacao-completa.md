# Scripts de Setup - População Completa do Banco de Dados

## Resumo das Melhorias Implementadas

Este documento descreve as melhorias implementadas no sistema de inicialização do banco de dados para garantir que **todas as tabelas sejam populadas automaticamente** durante a inicialização do sistema.

## Problemas Identificados e Soluções

### 1. **Problema**: Tabela PMM_2 não estava sendo populada
**Solução**: Criado script específico `populate_pmm_2.py` para popular dados PMM_2

### 2. **Problema**: Verificação incompleta das tabelas
**Solução**: Atualizado `check_database.py` para incluir verificação de **todas as tabelas**

### 3. **Problema**: Ordem de execução não incluía PMM_2
**Solução**: Integrado PMM_2 na sequência de execução do `setup_complete_database.py`

## Scripts Implementados

### 1. **populate_pmm_2.py** - Novo Script
```python
# Localização: proativo-clone/scripts/setup/populate_pmm_2.py
```

**Funcionalidades**:
- Procura arquivos PMM_2.CSV em diferentes locais
- Utiliza o processador PMM_2 existente
- Verifica se tabela existe antes de processar
- Evita duplicação de dados
- Gera estatísticas detalhadas

### 2. **check_database.py** - Melhorado
**Melhorias**:
- Agora verifica **5 tabelas** ao invés de 3:
  - ✅ Equipamentos
  - ✅ Manutenções
  - ✅ Falhas
  - ✅ Localidades SAP
  - ✅ Planos PMM_2

### 3. **setup_complete_database.py** - Expandido
**Nova sequência de execução**:
1. ✅ Verificação inicial
2. ✅ Criação de tabelas
3. ✅ População básica (equipamentos, manutenções, falhas)
4. ✅ Importação de localidades SAP
5. ✅ Correlação equipamentos-localidades
6. ✅ **População PMM_2** (NOVO)
7. ✅ Verificação final

## Verificação Completa das Tabelas

### Antes (Verificação Incompleta)
```bash
📊 Registros encontrados:
   Equipamentos: 25
   Manutenções: 40
   Falhas: 15
   Total: 80
```

### Depois (Verificação Completa)
```bash
📊 Registros encontrados:
   Equipamentos: 25
   Manutenções: 40
   Falhas: 15
   Localidades SAP: 41
   Planos PMM_2: 214
   Total: 335
```

## Tratamento de Erros

### Scripts Críticos (Abortam se falharem)
- `create_tables.py`
- `populate_database.py`

### Scripts Não-Críticos (Continuam se falharem)
- `import_localidades_sap.py`
- `correlate_equipment_locations.py`
- `populate_pmm_2.py`

## Execução Automática

### Via Docker
```bash
docker-compose up
# A população completa acontece automaticamente
```

### Manual
```bash
python scripts/setup/setup_complete_database.py
# Executa todas as etapas em sequência
```

## Localização dos Arquivos de Dados

### PMM_2.CSV
O script `populate_pmm_2.py` procura o arquivo em:
1. `data/samples/PMM_2.csv`
2. `data/samples/PMM_2.CSV`
3. `../../Planilhas SAP_Proativo/PMM_2.CSV`
4. `../../Planilhas SAP_Proativo/PMM_2.csv`

### Localidades SAP
O script `import_localidades_sap.py` procura em:
1. `data/samples/Localidades_SAP.csv`
2. `../../Planilhas SAP_Proativo/Localidades_SAP.csv`

## Logs de Execução

### Exemplo de Log Completo
```
🚀 PROATIVO - CONFIGURAÇÃO AUTOMÁTICA COMPLETA
====================================
   1️⃣  Verificar status atual
   2️⃣  Criar tabelas (se necessário)
   3️⃣  Popular dados básicos (se necessário)
   4️⃣  Importar localidades SAP (se necessário)
   5️⃣  Correlacionar equipamentos com localidades (se necessário)
   6️⃣  Popular dados PMM_2 (se necessário)
   7️⃣  Verificar resultado final

🔍 VERIFICAÇÃO INICIAL
==================
📊 Status atual do banco:
   Equipamentos: 0
   Manutenções: 0
   Falhas: 0
   Localidades SAP: 0
   Planos PMM_2: 0
   Total: 0

🔄 CRIANDO TABELAS
==================
✅ CRIANDO TABELAS - CONCLUÍDO

🔄 POPULANDO DADOS BÁSICOS
=========================
✅ POPULANDO DADOS BÁSICOS - CONCLUÍDO

🔄 IMPORTANDO LOCALIDADES SAP
============================
✅ IMPORTANDO LOCALIDADES SAP - CONCLUÍDO

🔄 CORRELACIONANDO EQUIPAMENTOS COM LOCALIDADES
===============================================
✅ CORRELACIONANDO EQUIPAMENTOS COM LOCALIDADES - CONCLUÍDO

🔄 POPULANDO DADOS PMM_2
=======================
✅ POPULANDO DADOS PMM_2 - CONCLUÍDO

🔄 VERIFICAÇÃO FINAL
===================
📊 Registros encontrados:
   Equipamentos: 25
   Manutenções: 40
   Falhas: 15
   Localidades SAP: 41
   Planos PMM_2: 214
   Total: 335
✅ VERIFICAÇÃO FINAL - CONCLUÍDO

============================================================
🎉 CONFIGURAÇÃO COMPLETA FINALIZADA COM SUCESSO!
============================================================
✅ Tabelas criadas
✅ Dados básicos populados
✅ Localidades SAP importadas
✅ Equipamentos correlacionados com localidades
✅ Dados PMM_2 populados
✅ Sistema pronto para uso
============================================================
```

## Benefícios da Implementação

1. **Automação Completa**: Todas as tabelas são populadas automaticamente
2. **Verificação Robusta**: Sistema verifica se **todas** as tabelas têm dados
3. **Ordem Correta**: Execução respeitada ordem de dependências
4. **Tratamento de Erros**: Diferenciação entre erros críticos e não-críticos
5. **Flexibilidade**: Pula etapas desnecessárias se dados já existem
6. **Visibilidade**: Logs detalhados de cada etapa

## Conclusão

O sistema agora garante que **todas as tabelas principais** (equipamentos, manutenções, falhas, localidades SAP e PMM_2) sejam populadas automaticamente durante a inicialização, proporcionando um banco de dados completo e pronto para uso sem intervenção manual. 