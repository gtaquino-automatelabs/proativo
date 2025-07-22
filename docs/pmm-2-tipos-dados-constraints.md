# PMM_2 - Tipos de Dados e Constraints

## Especificação Detalhada dos Campos

### 1. Campos de Identificação

#### `id` (Chave Primária)
```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
```
- **Tipo**: `UUID` (36 caracteres)
- **Características**: Chave primária, geração automática, imutável
- **Constraints**: `PRIMARY KEY`, `NOT NULL`
- **Índice**: Automático (chave primária)

#### `maintenance_plan_code` (Chave de Negócio)
```sql
maintenance_plan_code VARCHAR(50) NOT NULL UNIQUE
```
- **Tipo**: `VARCHAR(50)` 
- **Características**: Código único do plano de manutenção do SAP
- **Formato**: Letras + números + letra (ex: `TBDPDTCH001A`)
- **Constraints**: 
  - `NOT NULL`
  - `UNIQUE`
  - `CHECK (LENGTH(maintenance_plan_code) BETWEEN 8 AND 50)`
  - `CHECK (maintenance_plan_code ~ '^[A-Z0-9]+$')`
- **Índice**: `UNIQUE INDEX idx_pmm2_maintenance_plan_code`

### 2. Campos Descritivos

#### `work_center_responsible`
```sql
work_center_responsible VARCHAR(20) NOT NULL
```
- **Tipo**: `VARCHAR(20)`
- **Características**: Centro de trabalho responsável
- **Formato**: Letras maiúsculas (ex: `TTABDPM`)
- **Constraints**:
  - `NOT NULL`
  - `CHECK (LENGTH(work_center_responsible) BETWEEN 6 AND 20)`
  - `CHECK (work_center_responsible ~ '^[A-Z]+$')`
- **Índice**: `INDEX idx_pmm2_work_center`

#### `maintenance_item_description`
```sql
maintenance_item_description TEXT NOT NULL
```
- **Tipo**: `TEXT`
- **Características**: Descrição detalhada do item de manutenção
- **Formato**: Texto livre com possíveis caracteres especiais
- **Constraints**:
  - `NOT NULL`
  - `CHECK (LENGTH(maintenance_item_description) BETWEEN 10 AND 1000)`
- **Tratamento**: Limpeza de encoding e caracteres especiais

#### `installation_location`
```sql
installation_location VARCHAR(100) NOT NULL
```
- **Tipo**: `VARCHAR(100)`
- **Características**: Localização/ID do equipamento
- **Formato**: Código estruturado (ex: `MT-S-70113-FE01-CH-301F7T`)
- **Constraints**:
  - `NOT NULL`
  - `CHECK (LENGTH(installation_location) BETWEEN 5 AND 100)`
- **Uso**: Extração do código do equipamento

### 3. Campos de Data

#### `planned_date`
```sql
planned_date DATE NOT NULL
```
- **Tipo**: `DATE`
- **Características**: Data planejada da manutenção
- **Formato**: `YYYY-MM-DD`
- **Constraints**:
  - `NOT NULL`
  - `CHECK (planned_date >= '2020-01-01')`
  - `CHECK (planned_date <= '2050-12-31')`
- **Índice**: `INDEX idx_pmm2_planned_date`

#### `scheduled_start_date`
```sql
scheduled_start_date DATE
```
- **Tipo**: `DATE`
- **Características**: Data de início programada
- **Formato**: `YYYY-MM-DD`
- **Constraints**:
  - `NULL` permitido
  - `CHECK (scheduled_start_date IS NULL OR scheduled_start_date >= planned_date)`
- **Validação**: Deve ser >= `planned_date`

#### `completion_date`
```sql
completion_date DATE
```
- **Tipo**: `DATE`
- **Características**: Data de encerramento/conclusão
- **Formato**: `YYYY-MM-DD`
- **Constraints**:
  - `NULL` permitido
  - `CHECK (completion_date IS NULL OR completion_date >= COALESCE(scheduled_start_date, planned_date))`
- **Validação**: Deve ser >= `scheduled_start_date` ou `planned_date`

### 4. Campos de Ordem

#### `last_order_number`
```sql
last_order_number VARCHAR(20)
```
- **Tipo**: `VARCHAR(20)`
- **Características**: Número da última ordem
- **Formato**: Números (ex: `2200264285`)
- **Constraints**:
  - `NULL` permitido
  - `CHECK (last_order_number IS NULL OR last_order_number ~ '^[0-9]+$')`
  - `CHECK (last_order_number IS NULL OR LENGTH(last_order_number) = 10)`

#### `current_order_number`
```sql
current_order_number VARCHAR(20)
```
- **Tipo**: `VARCHAR(20)`
- **Características**: Número da ordem atual
- **Formato**: Números (ex: `2200264285`)
- **Constraints**:
  - `NULL` permitido
  - `CHECK (current_order_number IS NULL OR current_order_number ~ '^[0-9]+$')`
  - `CHECK (current_order_number IS NULL OR LENGTH(current_order_number) = 10)`
- **Índice**: `INDEX idx_pmm2_current_order`

### 5. Campos de Relacionamento

#### `equipment_id`
```sql
equipment_id UUID
```
- **Tipo**: `UUID`
- **Características**: Chave estrangeira para equipamentos
- **Constraints**:
  - `NULL` permitido (caso equipamento não seja encontrado)
  - `FOREIGN KEY (equipment_id) REFERENCES equipments(id) ON DELETE SET NULL`
- **Índice**: `INDEX idx_pmm2_equipment_id`

### 6. Campos de Metadados

#### `data_source`
```sql
data_source VARCHAR(50) NOT NULL DEFAULT 'PMM_2_CSV'
```
- **Tipo**: `VARCHAR(50)`
- **Características**: Fonte dos dados
- **Constraints**:
  - `NOT NULL`
  - `DEFAULT 'PMM_2_CSV'`
  - `CHECK (data_source IN ('PMM_2_CSV', 'PMM_2_API', 'PMM_2_MANUAL'))`

#### `source_file`
```sql
source_file VARCHAR(255)
```
- **Tipo**: `VARCHAR(255)`
- **Características**: Nome do arquivo fonte
- **Constraints**:
  - `NULL` permitido
  - `CHECK (source_file IS NULL OR LENGTH(source_file) BETWEEN 1 AND 255)`

#### `source_row`
```sql
source_row INTEGER
```
- **Tipo**: `INTEGER`
- **Características**: Número da linha no arquivo fonte
- **Constraints**:
  - `NULL` permitido
  - `CHECK (source_row IS NULL OR source_row > 0)`

#### `metadata_json`
```sql
metadata_json JSONB
```
- **Tipo**: `JSONB`
- **Características**: Dados estruturados adicionais
- **Constraints**:
  - `NULL` permitido
  - Validação JSON automática pelo PostgreSQL

### 7. Campos de Auditoria

#### `created_at`
```sql
created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
```
- **Tipo**: `TIMESTAMP WITH TIME ZONE`
- **Características**: Data/hora de criação
- **Constraints**:
  - `NOT NULL`
  - `DEFAULT NOW()`
- **Imutável**: Não deve ser alterado após criação

#### `updated_at`
```sql
updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
```
- **Tipo**: `TIMESTAMP WITH TIME ZONE`
- **Características**: Data/hora da última atualização
- **Constraints**:
  - `NOT NULL`
  - `DEFAULT NOW()`
- **Trigger**: Atualização automática via trigger

## Constraints Compostas

### 1. Constraint de Integridade de Datas
```sql
CONSTRAINT ck_pmm2_date_sequence CHECK (
    planned_date IS NOT NULL AND
    (scheduled_start_date IS NULL OR scheduled_start_date >= planned_date) AND
    (completion_date IS NULL OR completion_date >= COALESCE(scheduled_start_date, planned_date))
)
```

### 2. Constraint de Campos Obrigatórios
```sql
CONSTRAINT ck_pmm2_required_fields CHECK (
    maintenance_plan_code IS NOT NULL AND
    work_center_responsible IS NOT NULL AND
    maintenance_item_description IS NOT NULL AND
    installation_location IS NOT NULL AND
    planned_date IS NOT NULL
)
```

### 3. Constraint de Formato de Códigos
```sql
CONSTRAINT ck_pmm2_code_formats CHECK (
    maintenance_plan_code ~ '^[A-Z0-9]+$' AND
    work_center_responsible ~ '^[A-Z]+$' AND
    (last_order_number IS NULL OR last_order_number ~ '^[0-9]+$') AND
    (current_order_number IS NULL OR current_order_number ~ '^[0-9]+$')
)
```

## Índices Estratégicos

### 1. Índices Únicos
```sql
-- Chave de negócio
CREATE UNIQUE INDEX idx_pmm2_maintenance_plan_code 
ON pmm_2_maintenance_plans(maintenance_plan_code);
```

### 2. Índices de Relacionamento
```sql
-- Relacionamento com equipamento
CREATE INDEX idx_pmm2_equipment_id 
ON pmm_2_maintenance_plans(equipment_id);

-- Busca por ordem
CREATE INDEX idx_pmm2_current_order 
ON pmm_2_maintenance_plans(current_order_number);
```

### 3. Índices de Consulta
```sql
-- Busca por data planejada
CREATE INDEX idx_pmm2_planned_date 
ON pmm_2_maintenance_plans(planned_date);

-- Busca por centro de trabalho
CREATE INDEX idx_pmm2_work_center 
ON pmm_2_maintenance_plans(work_center_responsible);

-- Busca por status de conclusão
CREATE INDEX idx_pmm2_completion_status 
ON pmm_2_maintenance_plans(completion_date) 
WHERE completion_date IS NOT NULL;
```

### 4. Índices Compostos
```sql
-- Consultas por equipamento e data
CREATE INDEX idx_pmm2_equipment_planned_date 
ON pmm_2_maintenance_plans(equipment_id, planned_date);

-- Consultas por centro e data
CREATE INDEX idx_pmm2_work_center_planned_date 
ON pmm_2_maintenance_plans(work_center_responsible, planned_date);

-- Consultas por data e status
CREATE INDEX idx_pmm2_planned_completion 
ON pmm_2_maintenance_plans(planned_date, completion_date);
```

## Triggers

### 1. Trigger de Atualização
```sql
CREATE OR REPLACE FUNCTION update_pmm2_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_pmm2_updated_at
    BEFORE UPDATE ON pmm_2_maintenance_plans
    FOR EACH ROW
    EXECUTE FUNCTION update_pmm2_updated_at();
```

### 2. Trigger de Validação
```sql
CREATE OR REPLACE FUNCTION validate_pmm2_data()
RETURNS TRIGGER AS $$
BEGIN
    -- Validação de formato do código do plano
    IF NEW.maintenance_plan_code !~ '^[A-Z0-9]+$' THEN
        RAISE EXCEPTION 'Invalid maintenance_plan_code format: %', NEW.maintenance_plan_code;
    END IF;
    
    -- Validação de sequência de datas
    IF NEW.scheduled_start_date IS NOT NULL AND NEW.scheduled_start_date < NEW.planned_date THEN
        RAISE EXCEPTION 'scheduled_start_date cannot be before planned_date';
    END IF;
    
    IF NEW.completion_date IS NOT NULL AND NEW.completion_date < COALESCE(NEW.scheduled_start_date, NEW.planned_date) THEN
        RAISE EXCEPTION 'completion_date cannot be before scheduled_start_date';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_pmm2_validate_data
    BEFORE INSERT OR UPDATE ON pmm_2_maintenance_plans
    FOR EACH ROW
    EXECUTE FUNCTION validate_pmm2_data();
```

## Considerações de Performance

### 1. Particionamento (Futuro)
```sql
-- Particionamento por ano da data planejada
CREATE TABLE pmm_2_maintenance_plans_2024 PARTITION OF pmm_2_maintenance_plans
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

CREATE TABLE pmm_2_maintenance_plans_2025 PARTITION OF pmm_2_maintenance_plans
FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
```

### 2. Estatísticas
```sql
-- Análise de estatísticas para otimização
ANALYZE pmm_2_maintenance_plans;

-- Configuração de autovacuum
ALTER TABLE pmm_2_maintenance_plans SET (
    autovacuum_vacuum_scale_factor = 0.1,
    autovacuum_analyze_scale_factor = 0.05
);
```

## Validações de Aplicação

### 1. Validações Python
```python
from datetime import date
from typing import Optional
import re

class PMM2DataValidator:
    """Validador para dados PMM_2"""
    
    @staticmethod
    def validate_maintenance_plan_code(code: str) -> bool:
        """Valida código do plano de manutenção"""
        if not code or len(code) < 8 or len(code) > 50:
            return False
        return re.match(r'^[A-Z0-9]+$', code) is not None
    
    @staticmethod
    def validate_work_center(center: str) -> bool:
        """Valida centro de trabalho"""
        if not center or len(center) < 6 or len(center) > 20:
            return False
        return re.match(r'^[A-Z]+$', center) is not None
    
    @staticmethod
    def validate_order_number(order: Optional[str]) -> bool:
        """Valida número da ordem"""
        if order is None:
            return True
        if len(order) != 10:
            return False
        return re.match(r'^[0-9]+$', order) is not None
    
    @staticmethod
    def validate_date_sequence(planned: date, scheduled: Optional[date] = None, 
                             completion: Optional[date] = None) -> bool:
        """Valida sequência de datas"""
        if scheduled and scheduled < planned:
            return False
        if completion and scheduled and completion < scheduled:
            return False
        if completion and not scheduled and completion < planned:
            return False
        return True
    
    @staticmethod
    def validate_description(description: str) -> bool:
        """Valida descrição do item"""
        if not description or len(description) < 10 or len(description) > 1000:
            return False
        return True
    
    @staticmethod
    def validate_installation_location(location: str) -> bool:
        """Valida localização da instalação"""
        if not location or len(location) < 5 or len(location) > 100:
            return False
        return True
```

### 2. Validações SQL
```sql
-- Função de validação completa
CREATE OR REPLACE FUNCTION validate_pmm2_record(
    p_maintenance_plan_code VARCHAR(50),
    p_work_center_responsible VARCHAR(20),
    p_maintenance_item_description TEXT,
    p_installation_location VARCHAR(100),
    p_planned_date DATE,
    p_scheduled_start_date DATE DEFAULT NULL,
    p_completion_date DATE DEFAULT NULL
) RETURNS BOOLEAN AS $$
BEGIN
    -- Validação de campos obrigatórios
    IF p_maintenance_plan_code IS NULL OR p_work_center_responsible IS NULL OR 
       p_maintenance_item_description IS NULL OR p_installation_location IS NULL OR 
       p_planned_date IS NULL THEN
        RETURN FALSE;
    END IF;
    
    -- Validação de formatos
    IF p_maintenance_plan_code !~ '^[A-Z0-9]+$' OR
       p_work_center_responsible !~ '^[A-Z]+$' THEN
        RETURN FALSE;
    END IF;
    
    -- Validação de datas
    IF p_scheduled_start_date IS NOT NULL AND p_scheduled_start_date < p_planned_date THEN
        RETURN FALSE;
    END IF;
    
    IF p_completion_date IS NOT NULL AND p_completion_date < COALESCE(p_scheduled_start_date, p_planned_date) THEN
        RETURN FALSE;
    END IF;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;
``` 