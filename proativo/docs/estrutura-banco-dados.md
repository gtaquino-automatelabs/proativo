# Estrutura do Banco de Dados - Sistema PROAtivo

## 📋 Resumo Executivo

Este documento apresenta a proposta inicial de estrutura do banco de dados para o **Sistema PROAtivo** - Sistema de Apoio à Decisão (SAD) para manutenção de ativos elétricos. O sistema utilizará consultas em linguagem natural sobre dados semiestruturados provenientes de planilhas externas.

---

## 📊 Informações Necessárias sobre as Planilhas

### 1. Tipos de Dados de Manutenção
- **Dados de Equipamentos:** Transformadores, linhas de transmissão, disjuntores, etc.
- **Histórico de Manutenções:** Preventivas, corretivas, preditivas
- **Ordens de Serviço:** Status, prioridades, recursos alocados
- **Falhas e Incidentes:** Tipos, causas, impactos
- **Cronogramas:** Planejamento de paradas programadas

### 2. Formatos das Planilhas
- **Extensões:** CSV, XLSX, XML
- **Estrutura:** Colunas padronizadas vs. layouts variados
- **Frequência de atualização:** Diária, semanal, mensal
- **Volume de dados:** Quantidade de registros típica

### 3. Qualidade dos Dados
- **Padronização:** Códigos de equipamentos, nomenclaturas
- **Completude:** Campos obrigatórios vs. opcionais
- **Consistência:** Formatos de datas, valores numéricos

---

## 🗄️ Estrutura de Banco de Dados Proposta

### Tabela 1: `equipment` (Equipamentos)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | UUID/String | Código único do equipamento |
| `name` | String | Nome/descrição do equipamento |
| `type` | String | Tipo (transformador, disjuntor, etc.) |
| `location` | String | Localização/subestação |
| `manufacturer` | String | Fabricante |
| `model` | String | Modelo |
| `installation_date` | Date | Data de instalação |
| `rated_power` | Float | Potência nominal |
| `voltage_level` | String | Nível de tensão |
| `status` | String | Status atual (ativo, inativo, manutenção) |
| `criticality` | String | Criticidade (alta, média, baixa) |
| `created_at` | Timestamp | Data de criação do registro |
| `updated_at` | Timestamp | Data de última atualização |

### Tabela 2: `maintenance_orders` (Ordens de Manutenção)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | UUID | ID único da ordem |
| `equipment_id` | FK | Referência ao equipamento |
| `order_number` | String | Número da ordem |
| `type` | String | Tipo (preventiva, corretiva, preditiva) |
| `priority` | String | Prioridade (alta, média, baixa) |
| `status` | String | Status (aberta, em andamento, concluída) |
| `scheduled_date` | Date | Data programada |
| `start_date` | DateTime | Data/hora de início |
| `completion_date` | DateTime | Data/hora de conclusão |
| `description` | Text | Descrição dos serviços |
| `cost` | Decimal | Custo da manutenção |
| `technician_team` | String | Equipe responsável |
| `created_at` | Timestamp | Data de criação do registro |
| `updated_at` | Timestamp | Data de última atualização |

### Tabela 3: `maintenance_activities` (Atividades de Manutenção)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | UUID | ID único da atividade |
| `maintenance_order_id` | FK | Referência à ordem de manutenção |
| `activity_type` | String | Tipo de atividade |
| `description` | Text | Descrição detalhada |
| `duration_hours` | Float | Duração em horas |
| `materials_used` | JSON | Materiais utilizados |
| `observations` | Text | Observações técnicas |
| `performed_by` | String | Técnico que executou |
| `performed_at` | DateTime | Data/hora da execução |

### Tabela 4: `failures_incidents` (Falhas e Incidentes)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | UUID | ID único do incidente |
| `equipment_id` | FK | Referência ao equipamento |
| `incident_number` | String | Número do incidente |
| `occurrence_date` | DateTime | Data/hora da ocorrência |
| `failure_type` | String | Tipo de falha |
| `root_cause` | String | Causa raiz |
| `impact_level` | String | Nível de impacto |
| `downtime_hours` | Float | Tempo de indisponibilidade |
| `affected_customers` | Integer | Clientes afetados |
| `resolution_description` | Text | Descrição da resolução |
| `lessons_learned` | Text | Lições aprendidas |

### Tabela 5: `spare_parts` (Peças de Reposição)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | UUID | ID único da peça |
| `part_number` | String | Número da peça |
| `description` | String | Descrição |
| `manufacturer` | String | Fabricante |
| `unit_cost` | Decimal | Custo unitário |
| `stock_quantity` | Integer | Quantidade em estoque |
| `minimum_stock` | Integer | Estoque mínimo |
| `lead_time_days` | Integer | Prazo de entrega |

### Tabela 6: `equipment_spare_parts` (Relacionamento Equipamento-Peças)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `equipment_id` | FK | Referência ao equipamento |
| `spare_part_id` | FK | Referência à peça |
| `quantity_required` | Integer | Quantidade necessária |
| `maintenance_interval` | String | Intervalo de manutenção |

### Tabela 7: `maintenance_schedules` (Cronogramas de Manutenção)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | UUID | ID único do cronograma |
| `equipment_id` | FK | Referência ao equipamento |
| `maintenance_type` | String | Tipo de manutenção |
| `frequency_months` | Integer | Frequência em meses |
| `last_maintenance_date` | Date | Última manutenção |
| `next_maintenance_date` | Date | Próxima manutenção |
| `season_preference` | String | Preferência sazonal |
| `estimated_duration_hours` | Float | Duração estimada |

---

## ❓ Perguntas para o Departamento Técnico

### 1. Tipos de Equipamentos
**Que tipos de equipamentos** vocês gerenciam especificamente?
- [ ] Transformadores
- [ ] Disjuntores  
- [ ] Linhas de transmissão
- [ ] Seccionadoras
- [ ] Para-raios
- [ ] Outros: ________________________

### 2. Formatos de Dados
**Quais formatos de planilhas** vocês utilizam atualmente?
- [ ] CSV
- [ ] XLSX (Excel)
- [ ] XML
- [ ] Outros: ________________________

**Podem compartilhar exemplos anonimizados** dessas planilhas?

### 3. Informações Críticas
**Quais informações são mais importantes** para as consultas dos gestores?
- [ ] Custos de manutenção
- [ ] Prazos e cronogramas
- [ ] Criticidade dos equipamentos
- [ ] Histórico de falhas
- [ ] Disponibilidade de peças
- [ ] Outros: ________________________

### 4. Padronização
**Há códigos padronizados** em uso para:
- [ ] Equipamentos (ex: TAG, código patrimonial)
- [ ] Tipos de manutenção
- [ ] Localizações/subestações
- [ ] Equipes técnicas
- [ ] Outros: ________________________

### 5. Frequência de Análise
**Com que frequência** os dados são analisados?
- [ ] Diariamente
- [ ] Semanalmente  
- [ ] Mensalmente
- [ ] Sob demanda
- [ ] Outros: ________________________

### 6. Insights Desejados
**Que tipos de insights** os gestores mais procuram?
- [ ] Equipamentos críticos próximos da manutenção
- [ ] Custos elevados ou fora do orçamento
- [ ] Prazos vencidos ou em atraso
- [ ] Padrões de falhas recorrentes
- [ ] Eficiência das equipes
- [ ] Previsão de demanda por peças
- [ ] Outros: ________________________

### 7. Volume de Dados
**Qual o volume típico** de dados por período?
- Número de equipamentos: ____________
- Ordens de manutenção por mês: ____________
- Registros de falhas por mês: ____________
- Histórico disponível: ____________ anos

### 8. Integrações Existentes
**Há sistemas existentes** que precisam ser considerados?
- [ ] Sistema de gestão de ativos (EAM)
- [ ] Sistema de gestão empresarial (ERP)
- [ ] Sistema de supervisão (SCADA)
- [ ] Outros: ________________________

---

## 📋 Próximos Passos

1. **Revisão técnica** desta proposta pelo departamento
2. **Resposta às perguntas** específicas sobre os dados
3. **Fornecimento de exemplos** de planilhas anonimizadas
4. **Refinamento da estrutura** baseado no feedback
5. **Definição dos processadores ETL** específicos
6. **Prototipagem e testes** com dados reais

---

## 📞 Contato

Para dúvidas ou esclarecimentos sobre esta proposta, entrar em contato com a equipe de desenvolvimento do Sistema PROAtivo.

**Data:** Junho 2025  
**Versão:** 1.0  
**Status:** Proposta Inicial 