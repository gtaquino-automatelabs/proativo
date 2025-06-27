# Lista de Tarefas - Funcionalidade Upload de Arquivos

## Arquivos Relevantes

- `proativo/src/api/endpoints/upload.py` - ✅ Novo endpoint para upload de arquivos via API (CRIADO)
- `proativo/src/api/endpoints/upload.py` - Testes unitários para endpoint de upload
- `proativo/src/frontend/components/file_upload.py` - ✅ Componente Streamlit para interface de upload (CRIADO)
- `proativo/src/etl/upload_processor.py` - Processador específico para arquivos enviados via upload
- `proativo/src/etl/upload_monitor.py` - ✅ Serviço de monitoramento do diretório uploads (CRIADO)
- `proativo/src/etl/upload_job_manager.py` - ✅ Gerenciador de jobs de upload integrado (CRIADO)
- `proativo/src/etl/data_ingestion.py` - ✅ Método create_upload_ingestion_job adicionado (MODIFICADO)
- `proativo/src/api/endpoints/upload.py` - ✅ Validação prévia com DataProcessor adicionada (MODIFICADO)
- `proativo/scripts/testing/test_upload_integration.py` - ✅ Script de teste de integração completa (CRIADO)
- `proativo/src/api/models/upload.py` - ✅ Modelos Pydantic para requests/responses de upload (CRIADO)
- `proativo/src/database/models.py` - ✅ Modelo UploadStatus para tabela no banco adicionado (MODIFICADO)
- `proativo/scripts/setup/create_upload_status_table.py` - ✅ Script para criar tabela upload_status (CRIADO)
- `proativo/src/database/repositories.py` - ✅ UploadStatusRepository com métodos CRUD adicionado (MODIFICADO)
- `proativo/src/api/endpoints/upload.py` - ✅ Endpoint GET /status/{upload_id} implementado com banco real (MODIFICADO)
- `proativo/src/etl/upload_monitor.py` - ✅ Integração com banco para atualização automática de status (MODIFICADO)
- `proativo/src/frontend/app.py` - ✅ Aplicação principal modificada para incluir página de upload (MODIFICADO)
- `proativo/src/frontend/components/file_upload.py` - ✅ Componente UploadHistoryComponent e função render_file_upload_page adicionados (MODIFICADO)
- `proativo/src/frontend/components/file_upload.py` - ✅ RealTimeNotificationComponent para notificações em tempo real adicionado (MODIFICADO)
- `proativo/src/frontend/app.py` - ✅ Integração de notificações na sidebar adicionada (MODIFICADO)
- `proativo/src/api/endpoints/upload.py` - ✅ Endpoint de histórico implementado e endpoint de métricas agregadas adicionado (MODIFICADO)
- `proativo/tests/integration/test_upload_workflow.py` - Testes de integração do fluxo completo

### Observações

- A infraestrutura base já existe (configurações, pipeline ETL, validações)
- Diretório `data/uploads` já está configurado e protegido
- Processadores de arquivo (CSV, XML, XLSX) já estão implementados
- Falta apenas integrar os componentes existentes com a funcionalidade de upload

## Tarefas

- [x] 1.0 Implementar Endpoint de Upload na API
  - [x] 1.1 Criar modelos Pydantic em `src/api/models/upload.py` para requests e responses
  - [x] 1.2 Implementar endpoint POST `/api/v1/files/upload` com suporte a UploadFile do FastAPI
  - [x] 1.3 Adicionar validações de extensão de arquivo usando configurações existentes
  - [x] 1.4 Implementar validação de tamanho de arquivo usando `validate_request_size`
  - [x] 1.5 Salvar arquivo no diretório `data/uploads` com nome único para evitar conflitos
  - [x] 1.6 Retornar resposta com ID do upload e status inicial
  - [x] 1.7 Integrar endpoint no router principal da API (`src/api/main.py`)
  - [x] 1.8 Implementar tratamento de erros específicos para upload

- [x] 2.0 Criar Interface de Upload no Frontend Streamlit
  - [x] 2.1 Criar componente `file_upload.py` em `src/frontend/components/`
  - [x] 2.2 Implementar interface com `st.file_uploader` para múltiplos tipos de arquivo
  - [x] 2.3 Adicionar validação frontend de extensões permitidas
  - [x] 2.4 Integrar com `api_client.py` para enviar arquivo para API
  - [x] 2.5 Implementar barra de progresso durante upload
  - [x] 2.6 Exibir feedback visual de sucesso/erro após upload
  - [x] 2.7 Integrar componente na aplicação principal (`src/frontend/app.py`)
  - [x] 2.8 Adicionar preview dos dados do arquivo enviado

- [x] 3.0 Integrar Pipeline ETL com Diretório de Uploads
  - [x] 3.1 Criar `upload_monitor.py` em `src/etl/` para monitorar diretório uploads
  - [x] 3.2 Implementar job de ingestão que processa arquivos em `data/uploads`
  - [x] 3.3 Usar `DataProcessor` existente para processar arquivos enviados
  - [x] 3.4 Implementar lógica para mover arquivos processados para subdiretório `processed/`
  - [x] 3.5 Adicionar logging específico para processamento de uploads
  - [x] 3.6 Integrar monitoramento com scheduler ou trigger automático
  - [x] 3.7 Implementar limpeza automática de arquivos antigos processados

- [x] 4.0 Implementar Sistema de Monitoramento e Feedback
  - [x] 4.1 Criar tabela no banco para rastrear status de uploads
  - [x] 4.2 Implementar endpoint GET `/api/v1/files/status/{upload_id}` para consultar status
  - [x] 4.3 Atualizar status durante processamento (uploaded → processing → completed/failed)
  - [x] 4.4 Criar componente frontend para exibir histórico de uploads
  - [x] 4.5 Implementar notificações em tempo real usando polling ou websockets
  - [x] 4.6 Adicionar métricas de processamento (tempo, registros processados, erros)
  - [x] 4.7 Criar página de detalhes do processamento com logs e estatísticas

- [ ] 5.0 Testes de Integração e Validação do Fluxo Completo
  - [ ] 5.1 Criar testes unitários para endpoint de upload
  - [ ] 5.2 Criar testes unitários para componente frontend de upload
  - [ ] 5.3 Implementar teste de integração completo (upload → processamento → banco)
  - [ ] 5.4 Testar cenários de erro (arquivo inválido, tamanho excedido, formato não suportado)
  - [ ] 5.5 Testar performance com arquivos grandes (próximo ao limite de 50MB)
  - [ ] 5.6 Validar limpeza automática de arquivos processados
  - [ ] 5.7 Testar concorrência de múltiplos uploads simultâneos
  - [ ] 5.8 Documentar fluxo de uso e troubleshooting 