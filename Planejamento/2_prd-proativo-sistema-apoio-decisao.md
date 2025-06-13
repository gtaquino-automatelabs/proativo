# PRD - PROAtivo: Sistema Inteligente de Apoio à Decisão para Manutenção de Ativos

## 1. Introdução/Visão Geral

O PROAtivo é um sistema de apoio à decisão baseado em Inteligência Artificial que permite aos gestores de ativos de energia elétrica realizarem consultas em linguagem natural sobre dados de manutenção armazenados em planilhas. O sistema resolve o problema da análise eficiente de grandes volumes de dados semiestruturados, fornecendo insights ágeis e proativos para otimizar o planejamento de manutenção de ativos de transmissão de energia elétrica.

**Objetivo:** Facilitar a tomada de decisão dos gestores através de um chatbot inteligente que converte consultas em linguagem natural em informações relevantes extraídas de bases de dados técnicos.

## 2. Objetivos

- **Objetivo Principal:** Reduzir o tempo de análise de dados de manutenção de horas para minutos através de consultas intuitivas
- **Objetivo Secundário:** Melhorar a qualidade das decisões de manutenção através de acesso facilitado a informações históricas
- **Objetivo Terciário:** Demonstrar a viabilidade de LLMs em domínios especializados do setor elétrico
- **Métrica de Sucesso:** Alcançar satisfação do usuário superior a 80% nas avaliações de feedback

## 3. Histórias de Usuário

### História Principal
**Como** gestor de ativos de energia elétrica  
**Quero** fazer perguntas em linguagem natural sobre dados de manutenção  
**Para que** eu possa tomar decisões mais rápidas e informadas sobre o planejamento de manutenção

### Histórias Específicas

1. **Como** gestor de manutenção  
   **Quero** perguntar "Quando foi a última manutenção do transformador X?"  
   **Para que** eu possa planejar a próxima intervenção

2. **Como** coordenador de equipes  
   **Quero** perguntar "Quais equipamentos precisam de manutenção preventiva este mês?"  
   **Para que** eu possa alocar recursos adequadamente

3. **Como** analista de custos  
   **Quero** perguntar "Qual foi o custo médio de manutenção dos equipamentos tipo Y no último ano?"  
   **Para que** eu possa fazer projeções orçamentárias

4. **Como** engenheiro de confiabilidade  
   **Quero** perguntar "Quantas falhas do tipo Z ocorreram nos últimos 6 meses?"  
   **Para que** eu possa identificar padrões e melhorar a estratégia de manutenção

## 4. Requisitos Funcionais

### 4.1 Interface de Conversação
1. O sistema deve fornecer uma interface de chat simples onde o usuário digita perguntas em português
2. O sistema deve responder às consultas em linguagem natural de forma clara e objetiva
3. O sistema deve processar uma consulta por vez, sem manter histórico de conversas anteriores
4. O sistema deve permitir que o usuário avalie cada resposta com "👍" (positivo) ou "👎" (negativo)

### 4.2 Processamento de Dados
5. O sistema deve ser capaz de processar planilhas nos formatos CSV, XML e XLSX (Excel)
6. O sistema deve extrair automaticamente dados das planilhas e armazená-los em banco de dados PostgreSQL
7. O sistema deve implementar uma pipeline ETL automatizada para ingestão de dados
8. O sistema deve validar a integridade dos dados durante o processo de ingestão

### 4.3 Capacidades de Consulta
9. O sistema deve interpretar consultas sobre datas de manutenção (ex: "última manutenção", "próxima manutenção")
10. O sistema deve responder sobre custos de manutenção (ex: "custo médio", "total gasto")
11. O sistema deve fornecer informações sobre tipos de equipamentos e suas características
12. O sistema deve identificar padrões temporais (ex: "nos últimos 6 meses", "este ano")
13. O sistema deve realizar consultas agregadas (ex: "quantos", "média", "total")

### 4.4 Integração com IA
14. O sistema deve utilizar o LLM Google Gemini 2.5 Flash via API para processamento de linguagem natural
15. O sistema deve implementar técnica RAG (Retrieval Augmented Generation) para contextualizar respostas
16. O sistema deve converter consultas em linguagem natural para queries SQL apropriadas

### 4.5 Tratamento de Casos Limite
17. O sistema deve responder "Não sei responder essa pergunta com base nos dados disponíveis" quando não conseguir processar uma consulta
18. O sistema deve validar se os dados necessários existem antes de formular uma resposta
19. O sistema deve tratar erros de conexão com banco de dados de forma elegante

## 5. Não Objetivos (Fora de Escopo)

- **Histórico de Conversas:** O sistema não manterá registro de conversas anteriores entre sessões
- **Autenticação Complexa:** Não haverá sistema de login ou controle de acesso por usuário
- **Integração com Sistemas Legacy:** Não se integrará com sistemas existentes das concessionárias
- **Análise Preditiva Avançada:** Não fará previsões de falhas ou otimização automática de cronogramas
- **Interface Móvel:** Não terá versão otimizada para dispositivos móveis
- **Visualizações Gráficas:** Não gerará gráficos ou dashboards, apenas respostas textuais
- **Edição de Dados:** Usuários não poderão modificar dados através da interface
- **Relatórios Complexos:** Não gerará relatórios em PDF ou outros formatos estruturados

## 6. Considerações de Design

### Interface de Usuário
- **Framework:** Streamlit para interface web simples e responsiva
- **Layout:** Interface de chat minimalista com campo de entrada e área de resposta
- **Feedback:** Botões de avaliação (👍/👎) visíveis após cada resposta
- **Loading States:** Indicador visual durante processamento de consultas

### Experiência do Usuário
- **Linguagem:** Interface em português brasileiro
- **Tom de Voz:** Profissional mas acessível, adequado para ambiente corporativo
- **Tempo de Resposta:** Máximo de 10 segundos para consultas simples
- **Clareza:** Respostas diretas e objetivas, evitando jargões técnicos desnecessários

## 7. Considerações Técnicas

### Arquitetura
- **Backend:** FastAPI para API REST
- **Frontend:** Streamlit para interface web
- **Banco de Dados:** PostgreSQL para armazenamento estruturado
- **ORM:** SQLAlchemy para interação com banco de dados
- **Containerização:** Docker para ambiente de desenvolvimento e produção

### Stack de Processamento de Dados
- **Pandas:** Manipulação de dados de planilhas CSV
- **OpenPyXL:** Processamento de arquivos Excel (XLSX)
- **XML Parser:** Biblioteca padrão Python para arquivos XML
- **SQLAlchemy:** Mapeamento objeto-relacional e queries

### Integração de IA
- **LLM:** Google Gemini 2.5 Flash via API oficial
- **RAG Implementation:** Técnica de recuperação e geração aumentada
- **Embedding Storage:** PostgreSQL com extensão vector (se necessário)

### Dependências Críticas
- Conectividade com API do Google Gemini
- Banco PostgreSQL configurado e acessível
- Ambiente Python 3.8+ com dependências instaladas

## 8. Métricas de Sucesso

### Métricas Primárias
- **Satisfação do Usuário:** ≥ 80% de avaliações positivas (👍)
- **Taxa de Respostas Válidas:** ≥ 90% das consultas devem gerar respostas (não "não sei")
- **Tempo de Resposta:** ≤ 10 segundos para 95% das consultas

### Métricas Secundárias
- **Precisão das Respostas:** Validação manual de amostra de respostas
- **Disponibilidade do Sistema:** ≥ 95% de uptime durante testes
- **Cobertura de Tipos de Consulta:** Sistema deve responder aos 4 tipos principais definidos nas histórias de usuário

### Método de Coleta
- Logging automático de todas as avaliações de usuário (👍/👎)
- Medição automática de tempo de resposta
- Registro de consultas que resultaram em "não sei"

## 9. Perguntas em Aberto

1. **Estrutura dos Dados:** Qual será o schema exato das planilhas de entrada? Quais colunas serão obrigatórias?

2. **Volume de Dados:** Qual o volume estimado de dados a serem processados? (número de registros, tamanho dos arquivos)

3. **Frequência de Atualização:** Com que frequência novos dados serão adicionados ao sistema?

4. **Validação de Respostas:** Como validaremos se as respostas do sistema estão corretas durante o desenvolvimento?

5. **Deployment:** Onde o sistema será hospedado para os testes? (ambiente local, cloud, servidor específico)

6. **Usuários de Teste:** Quantos usuários participarão dos testes preliminares de usabilidade?

7. **Critérios de Qualidade:** Existem padrões específicos de qualidade ou conformidade que o sistema deve atender?

8. **Backup e Recuperação:** Quais são os requisitos para backup dos dados e recuperação em caso de falha?

---

**Versão:** 1.0  
**Data:** Janeiro 2025  
**Responsável:** Equipe PROAtivo  
**Status:** Em Desenvolvimento 