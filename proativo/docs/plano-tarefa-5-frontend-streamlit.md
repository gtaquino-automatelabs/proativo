# Plano de Implementação - Tarefa 5.0: Frontend Streamlit

**Sistema PROAtivo - Sistema Inteligente de Apoio à Decisão**

---

## Detalhamento da Tarefa 5.0

### Visão Geral
A tarefa 5.0 tem como objetivo criar uma interface frontend moderna e intuitiva usando Streamlit para permitir que gestores de manutenção de ativos elétricos interajam com o sistema através de consultas em linguagem natural.

### Subtarefas da Tarefa 5.0

#### **5.1 Configurar aplicação Streamlit principal** 
**Arquivo**: `src/frontend/app.py`

**Objetivos**:
- Configurar estrutura base da aplicação Streamlit
- Implementar sistema de navegação entre páginas
- Configurar tema profissional e branding
- Definir configurações globais (título, favicon, layout)
- Configurar conexão com variáveis de ambiente

**Entregáveis**:
- Aplicação principal Streamlit funcional
- Sistema de navegação implementado
- Configurações básicas definidas

#### **5.2 Criar componente de interface de chat**
**Arquivo**: `src/frontend/components/chat_interface.py`

**Objetivos**:
- Interface de conversação com histórico scrollável
- Campo de entrada de mensagem com validação
- Área de exibição de respostas formatadas
- Gestão de estado de sessão via `st.session_state`
- Integração com API backend
- **NOVO**: Captura e exibição da query SQL gerada

**Entregáveis**:
- Componente de chat funcional e reutilizável
- Histórico de conversa persistente na sessão
- Interface responsiva e user-friendly
- **NOVO**: Sistema de captura de queries SQL da resposta da API

#### **5.3 Implementar sistema de feedback**
**Arquivo**: `src/frontend/components/feedback.py`

**Objetivos**:
- Botões de avaliação 👍/👎 para cada resposta
- Sistema de coleta de comentários detalhados
- Integração com endpoint `/feedback` da API
- Interface modal para feedback expandido

**Entregáveis**:
- Sistema de feedback totalmente funcional
- Integração com backend para armazenamento
- Interface intuitiva para avaliação

#### **5.4 Adicionar indicador visual de loading**

**Objetivos**:
- Spinner animado durante processamento de consultas
- Mensagens de status informativas
- Feedback visual de tempo de resposta
- Estados de carregamento para diferentes operações

**Entregáveis**:
- Indicadores visuais de loading implementados
- UX melhorada durante operações assíncronas
- Feedback claro sobre o status das operações

#### **5.5 Configurar layout responsivo e tema profissional**

**Objetivos**:
- Implementar paleta de cores corporativa
- Layout adaptável para diferentes resoluções
- CSS customizado para identidade visual
- Tema consistente em toda a aplicação

**Entregáveis**:
- Design system implementado
- Interface responsiva e profissional
- Branding consistente

#### **5.6 Implementar validação de entrada do usuário**

**Objetivos**:
- Verificação de mensagem não vazia
- Limite de caracteres (máximo 2000)
- Sanitização básica de entrada
- Mensagens de erro claras

**Entregáveis**:
- Sistema de validação robusto
- UX melhorada com feedback imediato
- Prevenção de inputs inválidos

#### **5.7 Configurar tratamento de erros na interface**

**Objetivos**:
- Mensagens de erro amigáveis para usuários finais
- Degradação graceful em caso de falhas
- Logs de erro para debugging
- Fallback para cenários de indisponibilidade

**Entregáveis**:
- Sistema de tratamento de erros implementado
- Interface robusta e resiliente
- Experiência de usuário mantida mesmo com erros

#### **5.8 Implementar visualizador de queries SQL (TCC)**
**Arquivo**: `src/frontend/components/sql_viewer.py`

**Objetivos** (Específicos para TCC):
- Componente dedicado na sidebar para exibir queries SQL
- Syntax highlighting para melhor legibilidade
- Formatação e identação automática do SQL
- Botão para copiar query gerada
- Histórico das últimas queries executadas

**Entregáveis**:
- Componente SQL viewer totalmente funcional
- Integração com respostas da API que contêm SQL
- Interface visual atrativa para demonstração acadêmica
- Sistema de cache de queries para histórico

#### **5.9 Integrar frontend com API backend**

**Objetivos**:
- Conexão HTTP com FastAPI via `requests`
- Configuração de timeouts e retry logic
- Configuração de base URL via variáveis de ambiente
- Tratamento de respostas da API
- **NOVO**: Captura de dados de debug incluindo SQL gerado

**Entregáveis**:
- Integração completa frontend-backend
- Sistema de comunicação robusto
- Configuração flexível de ambientes
- **NOVO**: Captura e processamento de queries SQL das respostas

---

## Layout Sugerido

### 🎯 Design Principal: Interface de Chat Centralizada

```
┌─────────────────────────────────────────────────────────────┐
│ 🔌 PROAtivo - Sistema Inteligente de Apoio à Decisão        │
│                                                             │
│ ┌─────────────────┐  ┌───────────────────────────────────┐ │
│ │     SIDEBAR     │  │        ÁREA PRINCIPAL             │ │
│ │                 │  │                                   │ │
│ │ 📊 Dashboard    │  │  💬 INTERFACE DE CHAT             │ │
│ │ 🔍 Consultas    │  │  ┌─────────────────────────────┐   │ │
│ │ 📈 Métricas     │  │  │ Histórico de Conversa       │   │ │
│ │ ⚙️ Config       │  │  │                             │   │ │
│ │                 │  │  │ 🤖: Como posso ajudar?      │   │ │
│ │ 📋 Sobre        │  │  │ 👤: Última manutenção do... │   │ │
│ │ ❓ Ajuda        │  │  │ 🤖: A última manutenção...  │   │ │
│ │                 │  │  │                             │   │ │
│ │ ┌─────────────┐ │  │  └─────────────────────────────┘   │ │
│ │ │📜 Query SQL │ │  │                                   │ │
│ │ │             │ │  │  ┌─────────────────────────────┐   │ │
│ │ │SELECT * FROM│ │  │  │ Digite sua pergunta...      │   │ │
│ │ │equipments   │ │  │  │                    [Enviar] │   │ │
│ │ │WHERE...     │ │  │  └─────────────────────────────┘   │ │
│ │ │             │ │  │                                   │ │
│ │ └─────────────┘ │  │  [👍] [👎] Feedback             │ │
│ └─────────────────┘  └───────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 🎨 Design System

#### **Paleta de Cores**
- **Primária**: Azul corporativo (#1E3A8A) - Confiabilidade técnica
- **Secundária**: Verde (#059669) - Sucesso/Disponibilidade
- **Acento**: Laranja (#EA580C) - Alertas/Manutenção
- **Neutro**: Cinza (#64748B) - Texto e backgrounds
- **Background**: Branco/Cinza claro (#F8FAFC)

#### **Tipografia**
- **Fonte principal**: Inter/Roboto (legibilidade técnica)
- **Títulos**: Font-weight 600-700
- **Corpo**: Font-weight 400
- **Códigos**: Fonte monospace para dados técnicos

#### **Espaçamento**
- **Containers**: Padding consistente (16px/24px)
- **Componentes**: Margin bottom padrão (12px)
- **Elementos**: Espaçamento harmonioso

### 📱 Estrutura de Páginas

#### **1. Página Principal: Chat Interface**
- **Layout**: Wide layout para maximizar área de chat
- **Sidebar**: Navegação compacta e sempre visível
- **Chat Area**: Interface conversacional como foco central
- **Footer**: Informações de status e versão

#### **2. Páginas Auxiliares**

**Dashboard** 📊
- Métricas de uso do sistema
- Status dos serviços (API, Database, LLM)
- Estatísticas de satisfação do usuário
- Gráficos de performance

**Consultas Rápidas** 🔍
- Templates de perguntas frequentes
- Categorias de consultas (Manutenção, Custos, Equipamentos)
- Exemplos de uso
- Atalhos para consultas comuns

**Métricas do Sistema** 📈
- Analytics de feedback (👍/👎)
- Tempo médio de resposta
- Tipos de consulta mais frequentes
- Taxa de resolução de consultas

**Configurações** ⚙️
- Parâmetros de exibição
- Configurações de timeout
- Preferências do usuário
- Configurações de debug

**Ajuda** ❓
- Guia de uso do sistema
- Exemplos de consultas
- FAQ
- Documentação técnica

### 🚀 Features Específicas do Layout

#### **1. Interface de Chat Inteligente**

**Componentes principais**:
- **Área de conversa scrollável** com histórico persistente
- **Campo de entrada** com validação em tempo real
- **Indicadores visuais**: typing indicator, tempo de resposta
- **Sugestões contextuais** baseadas no tipo de consulta

**Funcionalidades**:
- Auto-scroll para mensagens novas
- Formatação rica das respostas
- Timestamps das mensagens
- Indicador de status da conexão

#### **2. Sistema de Feedback Integrado**

**Elementos**:
- Botões **👍/👎** após cada resposta
- **Modal de comentários** para feedback detalhado
- **Rating de confiança** da resposta (1-5 estrelas)
- **Tags de categorização** para o feedback

**Funcionalidades**:
- Envio automático para API
- Feedback visual de confirmação
- Histórico de avaliações
- Analytics agregados

#### **3. Elementos de Apoio à Decisão**

**Componentes**:
- **Tags de categorização** para respostas (manutenção, custos, etc.)
- **Metadados da consulta** (tempo de processamento, confiança)
- **Sugestões de follow-up** baseadas na consulta
- **Links para dados relacionados** quando disponível

#### **4. Indicadores de Status**

**Informações exibidas**:
- **Status da API** (online/offline/degraded)
- **Performance metrics** (tempo de resposta médio)
- **Cache status** para otimização
- **Número de consultas na sessão**

#### **5. Exibição de Query SQL (Para TCC)** 📜

**Objetivo Acadêmico**: Demonstrar visualmente a capacidade de conversão de linguagem natural para SQL

**Componentes**:
- **Painel dedicado na sidebar** com query SQL gerada
- **Syntax highlighting** para melhor legibilidade
- **Formatação automática** do SQL gerado
- **Indicador de sucesso/erro** da query

**Funcionalidades**:
- Atualização automática a cada nova consulta
- Botão para copiar query para clipboard
- Opção de expandir/colapsar o painel
- Histórico das últimas queries geradas
- Tempo de execução da query no banco

**Valor para TCC**:
- **Transparência do processo**: Mostra como o sistema interpreta linguagem natural
- **Validação técnica**: Permite verificar se a query está correta
- **Demonstração de capacidades**: Evidencia a inteligência do sistema
- **Debugging acadêmico**: Facilita análise e melhorias

### 💡 Justificativa do Design

Este layout foi projetado considerando:

1. **Público-alvo**: Gestores de manutenção que precisam de informações rápidas e precisas
2. **Contexto de uso**: Ambiente corporativo com foco em produtividade
3. **Tipo de interação**: Consultas pontuais em linguagem natural
4. **Necessidades do negócio**: Tomada de decisão baseada em dados históricos
5. **Escalabilidade**: Estrutura modular para futuras funcionalidades

### 🔧 Considerações Técnicas

#### **Performance**
- **Cache de componentes** para melhor responsividade
- **Lazy loading** de dados históricos
- **Otimização de re-renderização** via Streamlit
- **Compressão de assets** estáticos

#### **Acessibilidade**
- **Contraste adequado** nas cores escolhidas
- **Navegação por teclado** em todos os componentes
- **Screen reader friendly** com labels apropriados
- **Responsive design** para diferentes dispositivos

#### **Segurança**
- **Sanitização de inputs** no frontend
- **Validação dupla** (frontend + backend)
- **Headers de segurança** apropriados
- **Rate limiting** visual para evitar spam

---

## Implementação Técnica

### Estrutura de Arquivos Proposta

```
src/frontend/
├── app.py                          # Aplicação principal
├── config/
│   ├── __init__.py
│   ├── settings.py                 # Configurações do frontend
│   └── theme.py                    # Definições de tema e CSS
├── components/
│   ├── __init__.py
│   ├── chat_interface.py           # Interface de chat
│   ├── feedback.py                 # Sistema de feedback
│   ├── sidebar.py                  # Navegação lateral
│   ├── sql_viewer.py               # Visualizador de queries SQL (TCC)
│   ├── loading.py                  # Indicadores de loading
│   └── status_indicators.py        # Indicadores de status
├── pages/
│   ├── __init__.py
│   ├── dashboard.py                # Dashboard principal
│   ├── quick_queries.py            # Consultas rápidas
│   ├── metrics.py                  # Métricas do sistema
│   ├── settings.py                 # Configurações
│   └── help.py                     # Ajuda e documentação
├── services/
│   ├── __init__.py
│   ├── api_client.py               # Cliente para API backend
│   ├── session_manager.py          # Gerenciamento de sessão
│   └── validators.py               # Validações do frontend
├── utils/
│   ├── __init__.py
│   ├── formatters.py               # Formatação de dados
│   ├── helpers.py                  # Funções auxiliares
│   └── constants.py                # Constantes da aplicação
└── assets/
    ├── styles/
    │   ├── main.css                # Estilos principais
    │   └── components.css          # Estilos dos componentes
    └── images/
        ├── logo.png                # Logo da aplicação
        └── icons/                  # Ícones diversos
```

### Tecnologias e Bibliotecas

#### **Core**
- **Streamlit**: Framework principal para interface web
- **Requests**: Comunicação HTTP com API backend
- **Pandas**: Manipulação de dados para exibição

#### **UI/UX**
- **Plotly**: Gráficos e visualizações (para dashboard)
- **Streamlit-agraph**: Visualizações de rede (futuro)
- **Streamlit-option-menu**: Menu de navegação avançado
- **NOVO**: **Pygments**: Syntax highlighting para SQL
- **NOVO**: **sqlparse**: Formatação e parsing de SQL

#### **Utilitários**
- **Pydantic**: Validação de dados
- **Python-dotenv**: Carregamento de variáveis de ambiente
- **Loguru**: Logging estruturado

---

## Cronograma de Implementação

### Fase 1: Estrutura Base (Subtarefas 5.1-5.2)
**Duração estimada**: 2-3 dias
- Configurar aplicação Streamlit principal
- Implementar estrutura de navegação
- Criar componente básico de chat
- Configurar integração com API

### Fase 2: Funcionalidades Core (Subtarefas 5.3-5.4)
**Duração estimada**: 2-3 dias
- Implementar sistema de feedback
- Adicionar indicadores de loading
- Otimizar UX da interface de chat
- Testes de integração básicos

### Fase 3: Design e Validação (Subtarefas 5.5-5.6)
**Duração estimada**: 2 dias
- Configurar tema profissional
- Implementar validações de entrada
- Ajustes de responsividade
- Testes de usabilidade

### Fase 4: Robustez e Integração Final (Subtarefas 5.7-5.9)
**Duração estimada**: 3-4 dias
- Tratamento de erros avançado
- **NOVO**: Implementação do visualizador de SQL para TCC
- Integração completa com backend (incluindo captura de SQL)
- Testes end-to-end
- Documentação de uso

### **Total estimado**: 9-12 dias de desenvolvimento

---

## Critérios de Aceitação

### Funcionais
- [ ] Interface de chat funcional com histórico
- [ ] Sistema de feedback operacional (👍/👎)
- [ ] **NOVO**: Visualizador de queries SQL na sidebar (para TCC)
- [ ] Integração completa com API backend
- [ ] Validação de entrada implementada
- [ ] Tratamento de erros robusto

### Não-funcionais
- [ ] Tempo de resposta da interface < 2 segundos
- [ ] Layout responsivo para diferentes telas
- [ ] Design profissional e consistente
- [ ] Acessibilidade básica implementada
- [ ] Documentação de uso disponível

### Técnicos
- [ ] Código seguindo padrões do projeto
- [ ] Testes básicos implementados
- [ ] Logging apropriado configurado
- [ ] Configurações externalizadas
- [ ] Deploy funcional via Docker

---

## Próximos Passos

1. **Revisar e aprovar** este plano de implementação
2. **Configurar ambiente** de desenvolvimento frontend
3. **Iniciar subtarefa 5.1**: Configurar aplicação Streamlit principal
4. **Implementar incrementalmente** seguindo as diretrizes do projeto
5. **Testar continuamente** com dados reais da API

---

**Documento criado em**: Janeiro 2025  
**Versão**: 1.0  
**Status**: Plano Aprovado - Pronto para Implementação  
**Próxima ação**: Aguardando aprovação para iniciar subtarefa 5.1 