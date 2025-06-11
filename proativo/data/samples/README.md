# Dados de Exemplo - PROAtivo

Este diretório contém arquivos de exemplo para testes do sistema PROAtivo.

## Arquivos Disponíveis

### 1. equipamentos.csv
Arquivo CSV contendo dados de equipamentos elétricos de diferentes tipos:
- Transformadores (TR)
- Disjuntores (DJ)
- Chaves seccionadoras (CH)
- Para-raios (PR)
- Capacitores (CP)
- Reatores (RT)
- Reguladores (RG)
- Medidores (MD)

**Campos principais:**
- id, tipo, nome, fabricante, modelo
- data_instalacao, tensao_nominal, potencia_nominal
- subestacao, bay, status, coordenadas geográficas

### 2. manutencoes.csv
Arquivo CSV com histórico de manutenções realizadas:
- Manutenções preventivas, corretivas, preditivas e emergenciais
- Status: PLANEJADA, EM_ANDAMENTO, CONCLUIDA, CANCELADA, ADIADA

**Campos principais:**
- id, equipment_id, tipo, datas (programada/início/fim)
- status, prioridade, descrição, responsável
- custo, tempo estimado/real, observações

### 3. equipamentos.xml
Arquivo XML com estrutura hierárquica de dados de equipamentos:
- Informações detalhadas de equipamentos
- Especificações técnicas organizadas
- Dados de localização estruturados

### 4. indicadores_manutencao.xlsx (a ser criado manualmente)
Planilha Excel com duas abas:
1. **Historico_Falhas**: Registro de falhas ocorridas
   - Tipo de falha, severidade, tempo de parada
   - Causa raiz, ação tomada, custos
   
2. **Indicadores_Confiabilidade**: Métricas de confiabilidade
   - MTBF (Mean Time Between Failures)
   - MTTR (Mean Time To Repair)
   - Disponibilidade percentual
   - Custos anuais de manutenção

## Uso dos Dados

Estes arquivos são utilizados para:
- Testes unitários dos processadores ETL
- Testes de integração do pipeline de dados
- Validação das funcionalidades de importação
- Demonstração do sistema

## Observações

- Todos os dados são fictícios e foram criados apenas para fins de teste
- As coordenadas geográficas apontam para a região de São Paulo
- Os IDs seguem o padrão: TIPO-NUMERO (ex: TR-0001)
- Datas estão no formato ISO (YYYY-MM-DD) 