# PMM_2 - Chaves Primárias e Relacionamentos

## Estrutura de Chaves

### Chave Primária
- **Campo**: `id` (UUID)
- **Tipo**: `UUID` com geração automática
- **Objetivo**: Identificador único interno do sistema

### Chave Única (Business Key)
- **Campo**: `maintenance_plan_code` (VARCHAR(50))
- **Exemplo**: `TBDPDTCH001A`
- **Objetivo**: Identificador único do plano de manutenção no SAP
- **Constraint**: `UNIQUE` para evitar duplicatas

### Índices Propostos

```sql
-- Índice único para business key
CREATE UNIQUE INDEX idx_pmm2_maintenance_plan_code 
ON pmm_2_maintenance_plans(maintenance_plan_code);

-- Índice para relacionamento com equipment
CREATE INDEX idx_pmm2_equipment_id 
ON pmm_2_maintenance_plans(equipment_id);

-- Índice para busca por data planejada
CREATE INDEX idx_pmm2_planned_date 
ON pmm_2_maintenance_plans(planned_date);

-- Índice para busca por centro de trabalho
CREATE INDEX idx_pmm2_work_center 
ON pmm_2_maintenance_plans(work_center_responsible);

-- Índice para busca por ordem
CREATE INDEX idx_pmm2_current_order 
ON pmm_2_maintenance_plans(current_order_number);

-- Índice composto para queries comuns
CREATE INDEX idx_pmm2_equipment_planned_date 
ON pmm_2_maintenance_plans(equipment_id, planned_date);
```

## Relacionamentos

### 1. Relacionamento com Equipment (1:N)

**Tipo**: Um equipamento pode ter múltiplos planos de manutenção

```sql
-- Chave estrangeira
equipment_id UUID REFERENCES equipments(id)
```

**Estratégia de Associação**:
1. **Extração do código**: Extrair código do equipamento do campo `installation_location`
2. **Busca por código**: Buscar equipamento existente pela coluna `code`
3. **Fallback para localização**: Se não encontrar por código, buscar por `location`

**Exemplo de Extração**:
```
installation_location: "MT-S-70113-FE01-CH-301F7T"
↓
equipment_code: "CH-301F7T"
↓
SELECT id FROM equipments WHERE code = 'CH-301F7T'
```

**Lógica de Relacionamento**:
```python
def extract_equipment_code(installation_location: str) -> str:
    """
    Extrai código do equipamento do campo installation_location
    
    Padrões identificados:
    - CH-301F7T (Chave)
    - DJ-3U4 (Disjuntor)  
    - GM-1 (Gerador)
    - BB-3 (Banco de Baterias)
    - BC-C1_F (Banco de Capacitores)
    """
    # Busca por padrão no final: letras-números
    match = re.search(r'([A-Z]+)-([A-Z0-9_]+)$', installation_location)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    
    # Fallback: retorna últimos componentes
    parts = installation_location.split('-')
    if len(parts) >= 2:
        return f"{parts[-2]}-{parts[-1]}"
    
    return installation_location
```

### 2. Relacionamento com Maintenance (1:0..1)

**Tipo**: Um plano PMM_2 pode gerar zero ou uma manutenção

```sql
-- Relacionamento via ordem
current_order_number VARCHAR(20) -- Liga com maintenance.maintenance_code
```

**Estratégia de Associação**:
1. **Busca por código**: `current_order_number` → `maintenance.maintenance_code`
2. **Criação automática**: Se não existir, criar nova manutenção baseada no PMM_2
3. **Sincronização**: Manter dados sincronizados entre PMM_2 e Maintenance

**Mapeamento PMM_2 → Maintenance**:
```python
def create_maintenance_from_pmm2(pmm2_record) -> dict:
    """Cria registro de manutenção baseado no PMM_2"""
    
    # Determina tipo de manutenção baseado na descrição
    maintenance_type = "Preventive"  # Default
    description = pmm2_record.maintenance_item_description.lower()
    
    if "teste operativo" in description:
        maintenance_type = "Preventive"
    elif "ensaio" in description or "medição" in description:
        maintenance_type = "Predictive"
    elif "inspeção" in description:
        maintenance_type = "Preventive"
    elif "revisão" in description:
        maintenance_type = "Preventive"
    
    return {
        "equipment_id": pmm2_record.equipment_id,
        "maintenance_code": pmm2_record.current_order_number,
        "maintenance_type": maintenance_type,
        "title": pmm2_record.maintenance_item_description,
        "description": f"Manutenção programada - {pmm2_record.maintenance_item_description}",
        "scheduled_date": pmm2_record.planned_date,
        "start_date": pmm2_record.scheduled_start_date,
        "completion_date": pmm2_record.completion_date,
        "status": "Planned" if not pmm2_record.completion_date else "Completed",
        "priority": "Medium",
        "metadata_json": {
            "source": "PMM_2",
            "maintenance_plan_code": pmm2_record.maintenance_plan_code,
            "work_center": pmm2_record.work_center_responsible
        }
    }
```

## Constraints e Validações

### Constraints de Integridade

```sql
-- Constraint de chave única
CONSTRAINT uk_pmm2_maintenance_plan_code 
    UNIQUE (maintenance_plan_code);

-- Constraint de chave estrangeira
CONSTRAINT fk_pmm2_equipment 
    FOREIGN KEY (equipment_id) REFERENCES equipments(id) ON DELETE SET NULL;

-- Constraint de datas
CONSTRAINT ck_pmm2_dates 
    CHECK (planned_date IS NOT NULL AND 
           (scheduled_start_date IS NULL OR scheduled_start_date >= planned_date) AND
           (completion_date IS NULL OR completion_date >= scheduled_start_date));

-- Constraint de campos obrigatórios
CONSTRAINT ck_pmm2_required_fields 
    CHECK (maintenance_plan_code IS NOT NULL AND 
           work_center_responsible IS NOT NULL AND 
           maintenance_item_description IS NOT NULL AND
           installation_location IS NOT NULL);
```

### Validações de Negócio

```python
class PMM2Validator:
    """Validador para registros PMM_2"""
    
    def validate_maintenance_plan_code(self, code: str) -> bool:
        """Valida formato do código do plano"""
        # Formato esperado: LETRAS + NÚMEROS + LETRA (ex: TBDPDTCH001A)
        return re.match(r'^[A-Z]{8,12}[0-9]{3}[A-Z]$', code) is not None
    
    def validate_work_center(self, center: str) -> bool:
        """Valida centro de trabalho"""
        # Formato esperado: LETRAS (ex: TTABDPM)
        return re.match(r'^[A-Z]{6,8}$', center) is not None
    
    def validate_order_number(self, order: str) -> bool:
        """Valida número da ordem"""
        # Formato esperado: números (ex: 2200264285)
        return re.match(r'^[0-9]{10}$', order) is not None if order else True
    
    def validate_dates(self, planned: date, scheduled: date = None, 
                      completion: date = None) -> bool:
        """Valida sequência de datas"""
        if scheduled and scheduled < planned:
            return False
        if completion and scheduled and completion < scheduled:
            return False
        return True
```

## Estratégia de Upsert

### Chave de Upsert
- **Campo**: `maintenance_plan_code`
- **Estratégia**: Insert ou Update baseado na existência do código

### Lógica de Upsert

```python
async def upsert_pmm2_record(self, pmm2_data: dict) -> PMM2MaintenancePlan:
    """Executa upsert de registro PMM_2"""
    
    # Busca registro existente
    existing = await self.get_by_maintenance_plan_code(
        pmm2_data['maintenance_plan_code']
    )
    
    if existing:
        # Atualiza registro existente
        for key, value in pmm2_data.items():
            if key != 'id' and key != 'created_at':
                setattr(existing, key, value)
        
        existing.updated_at = datetime.now()
        await self.session.flush()
        return existing
    else:
        # Cria novo registro
        new_record = PMM2MaintenancePlan(**pmm2_data)
        self.session.add(new_record)
        await self.session.flush()
        return new_record
```

## Integridade Referencial

### Políticas de Relacionamento

1. **Equipment → PMM_2**: `ON DELETE SET NULL`
   - Se equipamento for deletado, PMM_2 fica com `equipment_id = NULL`

2. **PMM_2 → Maintenance**: Relacionamento via código (não FK)
   - Permite flexibilidade na sincronização

### Sincronização de Dados

```python
async def sync_pmm2_with_maintenance(self, pmm2_record: PMM2MaintenancePlan):
    """Sincroniza dados PMM_2 com tabela Maintenance"""
    
    if not pmm2_record.current_order_number:
        return
    
    # Busca manutenção existente
    maintenance = await self.maintenance_repo.get_by_code(
        pmm2_record.current_order_number
    )
    
    if not maintenance:
        # Cria nova manutenção
        maintenance_data = create_maintenance_from_pmm2(pmm2_record)
        await self.maintenance_repo.create(**maintenance_data)
    else:
        # Atualiza dados existentes
        maintenance.scheduled_date = pmm2_record.planned_date
        maintenance.start_date = pmm2_record.scheduled_start_date
        maintenance.completion_date = pmm2_record.completion_date
        maintenance.status = "Completed" if pmm2_record.completion_date else "Planned"
        await self.maintenance_repo.update(maintenance.id, **maintenance.__dict__)
```

## Considerações de Performance

### Índices Estratégicos
- **maintenance_plan_code**: Único, para upsert rápido
- **equipment_id**: Para queries de relacionamento
- **planned_date**: Para queries temporais
- **work_center_responsible**: Para filtragem por centro

### Otimizações
- **Batch Processing**: Processar múltiplos registros em lote
- **Connection Pooling**: Usar pool de conexões para performance
- **Async Operations**: Operações assíncronas para não bloquear 