# Dados Sintéticos - Sistema PROAtivo

## 📋 Visão Geral

Este diretório contém **dados sintéticos realistas** do setor elétrico brasileiro para desenvolvimento e testes do Sistema PROAtivo. Os dados foram criados baseados na estrutura proposta do banco de dados e representam cenários típicos de manutenção de ativos elétricos.

## 📊 Arquivos de Dados

### 1. `equipment.csv` (25 registros)
**Equipamentos de subestações elétrica**
- **Tipos:** Transformadores, Disjuntores, Seccionadoras, Para-raios
- **Localizações:** SE Norte, SE Centro, SE Sul, SE Leste, SE Oeste
- **Fabricantes:** WEG, ABB, Schneider Electric, Siemens, Balestro
- **Níveis de Tensão:** 138kV, 69kV, 13.8kV
- **Status:** Ativo, Inativo, Manutenção
- **Criticidade:** Alta, Média, Baixa

### 2. `maintenance_orders.csv` (25 registros)
**Ordens de manutenção do ano de 2024**
- **Tipos:** Preventiva, Corretiva, Preditiva
- **Status:** Concluída, Em Andamento, Aberta
- **Custos:** R$ 1.500 a R$ 67.800 (valores realistas)
- **Equipes:** Equipe A, B, C (especializações diferentes)
- **Período:** Janeiro 2024 a Fevereiro 2025

### 3. `failures_incidents.csv` (15 registros)
**Histórico de falhas e incidentes**
- **Tipos de Falha:** Isolação, Operação, Vazamento, Dano Físico, Térmica
- **Causas:** Sobretensão, Desgaste, Deterioração, Vandalismo, Falha de sistema
- **Impacto:** Alto, Médio, Baixo
- **Tempo de Reparo:** 1 a 72 horas
- **Clientes Afetados:** 0 a 22.000 clientes

### 4. `spare_parts.csv` (20 registros)
**Catálogo de peças de reposição**
- **Tipos:** Buchas, Válvulas, Contatos, Óleo, Vedações, Varistores
- **Fabricantes:** ABB, Schneider, Siemens, Shell, SKF, Parker
- **Custos:** R$ 25 a R$ 12.500
- **Estoque:** Quantidades atuais e mínimas
- **Lead Time:** 7 a 75 dias

### 5. `maintenance_schedules.csv` (40 registros)
**Cronogramas de manutenção programada**
- **Tipos:** Preventiva, Preditiva, Inspeção, Análise, Calibração
- **Frequências:** 3 a 24 meses
- **Sazonalidade:** Seco, Qualquer (considerando período chuvoso)
- **Duração:** 0.5 a 24 horas

### 6. `equipment_spare_parts.csv` (68 registros)
**Relacionamento equipamentos ↔ peças**
- **Mapeamento:** Cada equipamento com suas peças específicas
- **Quantidades:** Necessárias por tipo de manutenção
- **Intervalos:** Quando cada peça é tipicamente utilizada

## 🎯 Características dos Dados

### **Realismo Técnico:**
- **Códigos de equipamentos** seguem padrão brasileiro (TR-, DJ-, SC-, PR-)
- **Modelos e especificações** baseados em equipamentos reais
- **Custos de manutenção** compatíveis com mercado brasileiro
- **Tipos de falhas** comuns no setor elétrico
- **Cronogramas** considerando sazonalidade (período seco/chuvoso)

### **Consistência Relacional:**
- **Foreign Keys** válidas entre todas as tabelas
- **Datas** em sequência lógica temporal
- **Relacionamentos** equipamentos ↔ ordens ↔ falhas ↔ peças
- **Status e tipos** padronizados e consistentes

### **Volume Representativo:**
- **25 equipamentos** distribuídos em 5 subestações
- **25 ordens** cobrindo ano completo
- **15 incidentes** com severidades variadas
- **40 cronogramas** para diferentes tipos de manutenção

## 🔄 Flexibilidade para Mudanças

### **Estrutura Preparada:**
- **Colunas mapeáveis** facilmente para novos formatos
- **Tipos de dados** compatíveis com variações
- **Relacionamentos** mantidos mesmo com mudanças de schema
- **Formato CSV** facilita conversão para XLSX quando necessário

### **Extensibilidade:**
- **Novos equipamentos** podem ser adicionados facilmente
- **Novos tipos** de manutenção, falhas e peças
- **Períodos adicionais** seguindo mesmo padrão
- **Novos relacionamentos** mantendo consistência

## 🧪 Casos de Teste Cobertos

### **Consultas Típicas de Gestores:**
1. **"Quais equipamentos precisam de manutenção este mês?"**
2. **"Qual o custo total de manutenção da SE Norte?"**
3. **"Quais equipamentos tiveram mais falhas?"**
4. **"Temos peças em estoque para manutenção do TR-001?"**
5. **"Qual a próxima manutenção programada de transformadores?"**

### **Cenários de Negócio:**
- ✅ Equipamentos com diferentes criticidades
- ✅ Ordens em diferentes status (concluída, andamento, aberta)
- ✅ Falhas com diferentes impactos e custos
- ✅ Peças com diferentes disponibilidades
- ✅ Cronogramas com diferentes frequências

## 📈 Métricas dos Dados

| Categoria | Quantidade | Faixa de Valores |
|-----------|------------|------------------|
| **Equipamentos** | 25 | 5 tipos, 5 localizações |
| **Ordens de Manutenção** | 25 | R$ 1.500 - R$ 67.800 |
| **Falhas/Incidentes** | 15 | 0 - 22.000 clientes afetados |
| **Peças de Reposição** | 20 | R$ 25 - R$ 12.500 |
| **Cronogramas** | 40 | 3 - 24 meses frequência |
| **Relacionamentos** | 68 | Equipamento ↔ Peças |

## 🎯 Próximos Passos

1. **Teste de Ingestão:** Verificar pipeline ETL com estes dados
2. **Validação de Queries:** Testar consultas SQL complexas
3. **Teste de RAG:** Usar dados para treinar contexto do LLM
4. **Interface de Demo:** Demonstrações realistas para stakeholders
5. **Migração Futura:** Base para adaptação com dados reais

---

**📅 Criado:** Dezembro 2024  
**🔄 Versão:** 1.0  
**👥 Uso:** Desenvolvimento e testes do Sistema PROAtivo 