# Tarefas - Integração de Localidades SAP

## Arquivos Relevantes

- `src/database/models.py` - Adicionar modelo para localidades SAP
- `src/database/repositories.py` - Adicionar repository para localidades SAP
- `src/database/__init__.py` - Exportar novos componentes de localidades
- `src/etl/processors/localidades_processor.py` - Processar arquivo CSV de localidades
- `scripts/setup/import_localidades_sap.py` - Script para importar localidades iniciais
- `scripts/setup/correlate_equipment_locations.py` - Script para correlacionar equipamentos com localidades
- `tests/unit/test_localidades_model.py` - Testes para modelo de localidades
- `tests/unit/test_localidades_repository.py` - Testes para repository de localidades
- `tests/unit/test_localidades_processor.py` - Testes para processador de localidades
- `tests/integration/test_localidades_integration.py` - Testes de integração

### Observações

- O arquivo CSV `Localidades_SAP.csv` contém códigos de localização que devem ser correlacionados com equipamentos
- As localidades serão usadas para enriquecer dados de equipamentos e planos PMM_2
- A correlação será feita usando padrões de código de localização

## Tarefas

- [x] 1.0 Criar modelo de dados para localidades SAP
  - [x] 1.1 Adicionar modelo `SAPLocation` em `models.py`
  - [x] 1.2 Definir campos: código, denominação, abreviação
  - [x] 1.3 Adicionar relacionamentos com equipamentos
  - [x] 1.4 Criar índices para performance
- [x] 2.0 Implementar repository para localidades
  - [x] 2.1 Criar `SAPLocationRepository` em `repositories.py`
  - [x] 2.2 Implementar métodos CRUD básicos
  - [x] 2.3 Implementar busca por código e denominação
  - [x] 2.4 Implementar métodos de correlação com equipamentos
- [x] 3.0 Criar processador ETL para arquivo CSV
  - [x] 3.1 Criar `LocalidadesProcessor` em `etl/processors/`
  - [x] 3.2 Implementar leitura e validação do CSV
  - [x] 3.3 Implementar normalização dos dados
  - [x] 3.4 Implementar inserção no banco de dados
- [x] 4.0 Desenvolver scripts de importação e correlação
  - [x] 4.1 Criar script para importar localidades iniciais
  - [x] 4.2 Criar script para correlacionar equipamentos existentes
  - [x] 4.3 Implementar lógica de matching por padrões de código
  - [x] 4.4 Gerar relatórios de correlação
- [x] 6.0 Integrar scripts com inicialização do banco
  - [x] 6.1 Adicionar execução automática em setup_complete_database.py
  - [x] 6.2 Configurar ordem de execução: básico → localidades → correlação
  - [x] 6.3 Implementar tratamento de erros não-críticos
- [x] 5.0 Atualizar modelos existentes para suportar localidades
  - [x] 5.1 Adicionar chave estrangeira para localidade em Equipment
  - [x] 5.2 Adicionar chave estrangeira para localidade em PMM_2
  - [x] 5.3 Criar migration para alterações no banco
  - [x] 5.4 Atualizar repositories existentes

## ✅ Resumo da Implementação

### Status: **CONCLUÍDO** 🎉

A integração completa das localidades SAP foi implementada com sucesso:

#### 📊 Componentes Implementados:

1. **Modelo de Dados** - `SAPLocation`
   - Tabela `sap_locations` com campos para código, denominação e abreviação
   - Extração automática de região e tipo do código
   - Relacionamentos com `Equipment` e `PMM_2`

2. **Repository** - `SAPLocationRepository`
   - Operações CRUD completas
   - Métodos de busca por código, denominação e região
   - Correlação automática com equipamentos
   - Criação em lote para importação

3. **Processador ETL** - `LocalidadesProcessor`
   - Leitura automática de CSV com detecção de encoding
   - Normalização e validação de dados
   - Tratamento de erros e relatórios

4. **Scripts de Integração**:
   - `import_localidades_sap.py` - Importa CSV inicial
   - `correlate_equipment_locations.py` - Correlaciona equipamentos

5. **Atualizações nos Modelos**:
   - `Equipment.sap_location_id` - FK para localidade
   - `PMM_2.sap_location_id` - FK para localidade
   - Índices para performance

#### 🚀 Como Usar:

```bash
# 1. Importar localidades do CSV
python scripts/setup/import_localidades_sap.py

# 2. Correlacionar equipamentos existentes
python scripts/setup/correlate_equipment_locations.py
```

#### 📈 Resultados Esperados:
- Localidades SAP importadas e disponíveis para consulta
- Equipamentos correlacionados com suas localidades
- Enriquecimento dos dados de equipamentos e PMM_2
- Base para análises geográficas e regionais

#### 🔧 Funcionalidades Disponíveis:
- Busca de equipamentos por localidade
- Relatórios por região/tipo de instalação
- Análise de distribuição geográfica dos ativos
- Correlação automática para novos equipamentos 