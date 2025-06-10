# PROJETO DE PESQUISA

## PROAtivo: Sistema Inteligente de suporte ao planejamento de manutenção

**RANIERI BORGES DE OLIVEIRA**
**GUSTAVO TEIXEIRA DE AQUINO**

*Projeto de Pesquisa apresentado ao Programa de Capacitação e Formação do Centro de Competências Embrapii em Tecnologias Imersivas (AKCIT) como parte dos requisitos para elaboração do Trabalho de Conclusão de Curso.*

**GOIÂNIA**
**2025**

---

## 1. INTRODUÇÃO

No cenário atual, os Grandes Modelos de Linguagem (LLMs) emergem como ferramentas fundamentais de Inteligência Artificial (IA), destacando-se pela capacidade de gerar, interpretar e manipular a linguagem humana em larga escala. A aplicação desses modelos em ambientes corporativos complexos tem transformado a maneira como as decisões são tomadas, permitindo uma análise aprofundada de grandes volumes de dados e a geração de insights valiosos.

A crescente responsabilidade dos gestores em tomar decisões rápidas e assertivas, com foco no melhor custo-benefício, impulsiona a busca por soluções inovadoras. Nesse contexto, a IA, e mais especificamente os LLMs, representam um potencial transformador para a automação e qualificação de processos decisórios. A digitalização da economia global e do setor elétrico intensifica a interconexão entre as empresas de energia e a indústria de tecnologia.

As tendências atuais em LLMs incluem a fusão multimodal, que integra diferentes formatos de dados como texto, imagens, áudio e vídeo em um modelo unificado, e o raciocínio em tempo real, conectando LLMs a fluxos de dados contínuos (APIs, sensores IoT, bancos de dados externos) para gerar insights sob demanda, utilizando técnicas como a Geração Aumentada por Recuperação (RAG). Além disso, a emergência de LLMs específicos para domínios, treinados com vocabulários especializados e bases de conhecimento curadas, promete resultados mais precisos para necessidades setoriais, como saúde, direito e gestão de emergências.

No setor de energia, a aplicação de LLMs já demonstra aprimoramentos significativos na eficiência operacional, na manutenção de ativos e na detecção de perdas. Exemplos incluem a otimização da exploração, produção e manutenção, a previsão de falhas de equipamentos para manutenção preditiva e a otimização da alocação de recursos e cronogramas de manutenção [7]. Ferramentas de IA generativa são usadas para gerar resumos concisos de documentos de manutenção e manuais de instruções, agilizando o acesso à informação para engenheiros de concessionárias.

Um desafio constante para as organizações é a análise eficiente de grandes volumes de dados, frequentemente armazenados em formatos semi ou não estruturados, para a extração de informações valiosas de forma ágil. Dados semiestruturados, como JSON e XML, são flexíveis, auto-descritivos e hierárquicos, facilitando a adaptação a mudanças nos requisitos de dados. No entanto, a gestão desses dados apresenta desafios, como a complexidade no gerenciamento, potenciais problemas de desempenho e a falta de padronização, que exigem ferramentas e abordagens especializadas para uma análise eficaz. Nesse cenário, o desenvolvimento de um sistema de apoio à decisão (SAD) baseado em LLM para consultas em linguagem natural sobre dados semi estruturados, como planilhas externas, emerge como uma proposta promissora. Contudo, a implantação de tais sistemas em ambientes complexos como o planejamento de manutenção deativos elétricos apresenta uma série de desafios práticos que precisam ser explorados e compreendidos para guiar futuras implementações.

A literatura recente tem explorado intensamente o potencial dos Grandes Modelos de Linguagem (LLMs) como ferramentas de apoio à decisão em diversos contextos. Trabalhos como o de EIGNER e HÄNDLER (2024) investigam os determinantes tecnológicos, psicológicos e específicos da decisão que influenciam a eficácia da tomada de decisão assistida por LLMs, destacando tanto os benefícios quanto os riscos associados, como a super confiança. A capacidade dos LLMs de analisar documentos e gerar insights para chatbots e sistemas de apoio à decisão (SAD) é demonstrada por IBRAHIM et al. (2025) e PIRES (2025), que propõem arquiteturas e exploram a aplicação prática dessas tecnologias no mercado, incluindo o uso de Engenharia de Prompt e Geração Aumentada por Recuperação (RAG).

Especificamente no âmbito do planejamento e da tomada de decisão estratégica, PALLAGANI et al. (2024) revisam a incorporação de LLMs em Planejamento e Agendamento Automatizado (APS), enquanto CHANGEUX e MONTAGNIER (2024) ilustram, por meio de um estudo de caso, como LLMs podem melhorar a previsibilidade de negócios e o planejamento de cenários. Técnicas avançadas de RAG, como o PlanRAG proposto por LEE et al. (2024), buscam otimizar a forma como LLMs recuperam e utilizam dados para a tomada de decisão complexa. No contexto de negócios, os gestores são cada vez mais responsáveis por decisões tomadas de forma rápida e assertiva, visando sempre o melhor custo benefício associado.

Este conjunto de estudos indica que, embora os LLMs ofereçam um potencial transformador para a automatização e qualificação de processos decisórios, a sua implementação eficaz depende da compreensão dos fatores que moldam a interação humano-IA e do desenvolvimento de metodologias robustas para integrar esses modelos a fontes de conhecimento específicas e atendendo regras de negócio estabelecidas de acordo com a especificidade da aplicação pretendida.

A pesquisa atual, embora abranja a capacidade dos LLMs de analisar documentos e auxiliar na tomada de decisão, concentra-se em investigações aprofundadas sobre a construção de arquiteturas e metodologias que sejam capazes de lidar com dados de natureza heterogênea e, frequentemente isolada, que podem não estar em bases de dados relacionais tradicionais. No entanto, a literatura ainda apresenta uma lacuna quanto à exploração sistemática dos desafios práticos intrínsecos ao processo de desenvolvimento e implementação de SADs baseados em LLMs, especialmente quando se trata da integração com fontes de dados semi estruturadas em um domínio tão especializado e crítico como o planejamento de manutenção de ativos de transmissão/distribuição de energia elétrica. O presente TCC se insere nesse contexto, buscando preencher essa lacuna ao focar na identificação e documentação desses desafios, o que servirá de base para futuras implementações e aprimoramentos no setor.

## 2. PERGUNTA DE PESQUISA

A implementação de um sistema de apoio à decisão baseado em (LLM), capaz de realizar consultas em linguagem natural sobre dados semi estruturados, pode fornecer informações relevantes e insights que auxiliem no processo de tomada de decisão dos gestores de ativos de energia?

## 3. HIPÓTESE

Não se aplica.

## 4. JUSTIFICATIVA

O presente trabalho se insere no contexto da crescente aplicação da Inteligência Artificial (IA) como ferramenta de suporte à tomada de decisão em ambientes corporativos complexos. A gestão e o planejamento da manutenção de ativos em concessionárias de distribuição de energia elétrica, setor crucial para o desenvolvimento socioeconômico, representam um desafio constante, com impacto direto na confiabilidade do fornecimento, nos custos operacionais e na segurança dos sistemas. Em um cenário de intensa e contínua transformação digital, a capacidade de analisar grandes volumes de dados – frequentemente armazenados em formatos semi ou não estruturados – e deles extrair informações valiosas de forma ágil, apresenta-se como um desafio e, para aqueles que lograram êxito em endereçar corretamente essa demanda, converte-se em um diferencial estratégico importante.

O PROAtivo visa endereçar essa lacuna ao introduzir uma solução que emprega técnicas como a Geração Aumentada por Recuperação (RAG) para permitir consultas em linguagem natural sobre estes dados semiestruturados. Desta forma, gestores poderão obter insights e informações relevantes de maneira mais intuitiva, ágil e proativa, fomentando decisões mais embasadas. A pesquisa contribuirá também para o campo do Processamento de Linguagem Natural (PLN) ao investigar a aplicação de LLMs na análise de dados técnicos específicos do setor elétrico, gerando conhecimento sobre a construção e os desafios de SADs eficazes para domínios especializados.

Os impactos esperados com a eventual implementação e os resultados advindos do estudo do protótipo PROAtivo são multifacetados. No âmbito acadêmico e científico, o trabalho proposto trará contribuições ao apresentar um estudo de caso prático da aplicação de LLMs e da técnica de RAG em um domínio altamente especializado. Ele oferecerá insights sobre os desafios e as limitações para o desenvolvimento e implementação de sistemas inteligentes customizados para atender a necessidades setoriais específicas e, para futuras pesquisas, os benefícios da interação humano-IA em processos de tomada de decisão complexas. Para as concessionárias de energia, abre-se um caminho para a busca de impactos positivos diretos na eficiência operacional. Isso inclui a potencial redução de custos associados a manutenções corretivas emergenciais (que são tipicamente mais caras), a otimização na alocação de equipes e recursos de manutenção, e o prolongamento da vida útil dos ativos através de um planejamento mais assertivo e potencialmente preditivo. Como consequência, espera-se uma melhoria na confiabilidade e na qualidade do fornecimento de energia elétrica para a sociedade, um benefício extensível a todos os consumidores.

Esta pesquisa está intrinsecamente alinhada com as macrotendências de digitalização do setor elétrico e com os preceitos da Indústria 4.0, onde a inteligência artificial e a análise avançada de dados são reconhecidas como pilares para a transformação de processos industriais e de gestão.

## 5. OBJETIVO GERAL

Desenvolver um sistema de apoio à decisão baseado em um grande modelo de linguagem (LLM), capaz de receber consultas em linguagem natural e realizar pesquisas em dados semi estruturados contidos em planilhas externas, visando fornecer informações relevantes e insights que auxiliem no processo de tomada de decisão do planejamento de manutenção de ativos de transmissão de energia elétrica.

### 5.1. Objetivos específicos

*   Projetar e implementar a arquitetura de um sistema de apoio à decisão que integre um grande modelo de linguagem (LLM) com a capacidade de acessar e processar dados de planilhas externas contendo informações sobre manutenção de ativos de transmissão de energia elétrica.
*   Desenvolver uma interface de consulta em linguagem natural que permita aos usuários formular perguntas complexas sobre o planejamento de manutenção de ativos, de forma intuitiva e eficiente.
*   Elaborar e executar testes unitários, integrados e de funcionalidade, para garantir o bom desempenho do sistema como um todo, aliando usabilidade e praticidade a uma performance de qualidade.

## 6. MÉTODO PRELIMINAR

O TCC adotará uma metodologia de pesquisa de desenvolvimento experimental para criar um protótipo de Sistema de Apoio à Decisão (SAD) na forma de um chatbot inteligente.

### 6.1. Descrição da Tecnologia e Desenvolvimento - Premissas

O protótipo será desenvolvido para permitir interação em linguagem natural, viabilizando consultas a uma base de conhecimento composta por documentos técnicos, através da técnica de Retrieval Augmented Generation (RAG).

A aplicação será construída predominantemente em Python, utilizando `FastAPI` para o desenvolvimento de uma API backend. O núcleo de inteligência artificial será o LLM `Google Gemini 2.5 Flash`, acessado via API. Os dados relevantes, extraídos de planilhas (csv, xmls) com o auxílio da biblioteca `Pandas` e `OpenPyXL`, serão persistidos em um banco de dados `PostgreSQL`. A interação com este banco será otimizada pelo uso do `SQLAlchemy` como ORM. A interface do chatbot será desenvolvida com `Streamlit`, e todo o ambiente da aplicação será gerenciado com `Docker`.

### 6.2. Procedimentos Metodológicos

#### 6.2.1. Detalhamento do Planejamento:

*   Levantamento e análise das planilhas de dados.
*   Projetar a arquitetura geral do sistema.
*   Definir a estrutura do banco de dados SQL (`PostgreSQL`).
*   Desenhar o fluxo da pipeline de ETL.
*   Desenho conceitual da interface do usuário (UI).
*   Identificar e documentar as regras de negócio.
*   Elaborar um plano de testes inicial.

#### 6.2.2. Construção do Protótipo:

*   **Configuração do Ambiente de Desenvolvimento:** Criar ambiente virtual, instalar dependências, configurar `Docker` e `PostgreSQL`.
*   **Ingestão e Tratamento de Dados:** Desenvolver scripts para leitura e processamento de dados (`Pandas`, `OpenPyXL`), implementar pipeline de ingestão automatizada (`SQLAlchemy`).
*   **Desenvolvimento do Backend:** Desenvolver endpoints da API com `FastAPI`, implementar lógica de consultas SQL, integrar LLM Gemini e mecanismo RAG, codificar regras de negócio.
*   **Desenvolvimento da Interface do Usuário:** Construir a interface do chatbot utilizando `Streamlit`.

#### 6.2.3. Testes Iterativos:

*   **Testes Unitários:** Testar as menores unidades de código do backend e componentes da UI.
*   **Testes de Integração:** Verificar a interação entre UI e backend, comunicação com banco de dados, integração com API do LLM e fluxo de ingestão.
*   **Testes de Funcionalidade:** Validar se o sistema executa as funcionalidades especificadas corretamente.
*   **Testes Preliminares de Usabilidade:** Realizar testes informais para coletar feedback.

## 7. RESULTADOS ESPERADOS

*   Um sistema funcional e modular com arquitetura definida.
*   Um banco de dados SQL robusto para armazenar e gerenciar os dados.
*   Uma pipeline de ingestão de dados automatizada.
*   Um backend da aplicação que controla a lógica do sistema.
*   Uma interface de usuário intuitiva e de fácil uso.
*   Inspirar pesquisas futuras para o desenvolvimento de sistemas mais robustos.