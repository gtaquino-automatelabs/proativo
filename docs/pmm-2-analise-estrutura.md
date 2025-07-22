# Análise da Estrutura PMM_2 (Plano de Manutenção Mestre)

## Visão Geral
O arquivo **PMM_2.CSV** contém dados de planos de manutenção do sistema SAP, representando programações de manutenção preventiva e operacional de equipamentos elétricos.

## Estrutura do Arquivo CSV

### Configurações de Leitura
- **Encoding**: `latin-1` ou `cp1252` (devido a caracteres especiais)
- **Separador**: `;` (ponto e vírgula)
- **Formato de Data**: `dd/mm/yyyy`
- **Total de Registros**: 214 linhas (213 dados + 1 cabeçalho)

### Campos Identificados

| Campo Original | Tipo | Exemplo | Descrição |
|----------------|------|---------|-----------|
| `Plano manut.` | String(50) | `TBDPDTCH001A` | Código único do plano de manutenção |
| `CenTrab respon.` | String(20) | `TTABDPM` | Centro de trabalho responsável |
| `Texto item man.` | String(200) | `Teste operativo (BDP) CH-301F7T` | Descrição do item de manutenção |
| `Loc.instalação` | String(100) | `MT-S-70113-FE01-CH-301F7T` | Localização/ID do equipamento |
| `Data planejada` | Date | `15/01/2028` | Data planejada da manutenção |
| `Dta.início.progr.` | Date | `11/03/2025` | Data de início programada |
| `Data encermto.` | Date | `11/03/2025` | Data de encerramento (pode estar vazio) |
| `Última ordem` | String(20) | `2200264285` | Número da última ordem |
| `Ordem` | String(20) | `2200264285` | Número da ordem atual (pode estar vazio) |

## Mapeamento para Modelo PMM_2

### Campos Propostos para Modelo SQL

```sql
CREATE TABLE pmm_2_maintenance_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Campos principais
    maintenance_plan_code VARCHAR(50) NOT NULL UNIQUE,  -- Plano manut.
    work_center_responsible VARCHAR(20) NOT NULL,       -- CenTrab respon.
    maintenance_item_description TEXT NOT NULL,         -- Texto item man.
    installation_location VARCHAR(100) NOT NULL,        -- Loc.instalação
    
    -- Datas
    planned_date DATE NOT NULL,                         -- Data planejada
    scheduled_start_date DATE,                          -- Dta.início.progr.
    completion_date DATE,                               -- Data encermto.
    
    -- Ordens
    last_order_number VARCHAR(20),                      -- Última ordem
    current_order_number VARCHAR(20),                   -- Ordem
    
    -- Relacionamentos
    equipment_id UUID,                                  -- FK para equipments (derivado de installation_location)
    
    -- Metadados
    data_source VARCHAR(50) DEFAULT 'PMM_2_CSV',
    source_file VARCHAR(255),
    source_row INTEGER,
    metadata_json JSONB,
    
    -- Auditoria
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT fk_pmm2_equipment FOREIGN KEY (equipment_id) REFERENCES equipments(id)
);
```

### Mapeamento de Campos CSV → SQL

| Campo CSV | Campo SQL | Transformação |
|-----------|-----------|---------------|
| `Plano manut.` | `maintenance_plan_code` | Trim, uppercase |
| `CenTrab respon.` | `work_center_responsible` | Trim, uppercase |
| `Texto item man.` | `maintenance_item_description` | Trim, fix encoding |
| `Loc.instalação` | `installation_location` | Trim, usar para buscar equipment_id |
| `Data planejada` | `planned_date` | Parse DD/MM/YYYY |
| `Dta.início.progr.` | `scheduled_start_date` | Parse DD/MM/YYYY |
| `Data encermto.` | `completion_date` | Parse DD/MM/YYYY (nullable) |
| `Última ordem` | `last_order_number` | Trim |
| `Ordem` | `current_order_number` | Trim (nullable) |

## Relacionamentos Identificados

### 1. Relacionamento com Equipment
- **Campo de Ligação**: `installation_location` → `equipment.code` ou `equipment.location`
- **Estratégia**: Extrair código do equipamento do campo `installation_location`
- **Exemplo**: `MT-S-70113-FE01-CH-301F7T` → equipamento `CH-301F7T`

### 2. Relacionamento com Maintenance (Existente)
- **Campo de Ligação**: `current_order_number` → `maintenance.maintenance_code`
- **Estratégia**: Criar/atualizar registros de manutenção baseados nos PMM_2

## Padrões Identificados

### Códigos de Plano de Manutenção
```
TBDPDTCH001A  - Teste operativo BDP para CH (Chave)
TUEMDTDJ003A  - Teste operativo UEM para DJ (Disjuntor)
TUJGDTCH026A  - Teste operativo UJG para CH (Chave)
TSGTDTCH003A  - Teste operativo SGT para CH (Chave)
```

### Centros de Trabalho
```
TTABDPM  - Centro BDP
TTAEMPM  - Centro UEM
TTAJGPM  - Centro UJG
TTASGPM  - Centro SGT
TTASSPM  - Centro USS
```

### Tipos de Manutenção Identificados
- **Teste operativo**: Testes de funcionamento
- **Ensaios e medições**: Medições técnicas
- **Inspeção visual detalhada**: Inspeções visuais
- **Revisão desmontagem**: Revisões com desmontagem

## Considerações Técnicas

### Encoding
- Arquivo contém caracteres especiais (ç, ã, ê, etc.)
- Necessário detectar encoding `latin-1` ou `cp1252`

### Dados Ausentes
- Campo `Data encermto.` pode estar vazio
- Campo `Ordem` pode estar vazio

### Duplicatas
- Mesmo `maintenance_plan_code` pode aparecer múltiplas vezes
- Estratégia de upsert necessária baseada em `maintenance_plan_code`

### Validações Necessárias
1. **Obrigatórios**: `maintenance_plan_code`, `work_center_responsible`, `planned_date`
2. **Formatos de Data**: Validar formato DD/MM/YYYY
3. **Relacionamentos**: Verificar se equipamento existe antes de associar
4. **Unicidade**: `maintenance_plan_code` deve ser único

## Próximos Passos

1. **Implementar modelo PMM_2** seguindo estrutura proposta
2. **Criar processador específico** para parsing e validação
3. **Implementar lógica de relacionamento** com equipamentos
4. **Desenvolver estratégia de upsert** para atualizações
5. **Criar testes unitários** para validação de dados 