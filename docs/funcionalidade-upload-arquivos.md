# Funcionalidade de Upload de Arquivos - PROAtivo

## Visão Geral

A funcionalidade de upload de arquivos permite aos usuários enviar arquivos CSV, XLSX e XML diretamente pela interface web, que são processados automaticamente pelo pipeline ETL e integrados ao banco de dados do sistema.

## Arquitetura da Solução

### Componentes Principais

1. **Frontend (Streamlit)** - Interface de usuário para upload
2. **API (FastAPI)** - Endpoints REST para recebimento de arquivos
3. **Pipeline ETL** - Processamento automático dos arquivos
4. **Banco de Dados** - Armazenamento e monitoramento de status
5. **Sistema de Diagnóstico** - Testes e validações

### Fluxo de Dados

```
[Frontend] → [API Upload] → [Diretório uploads/] → [Monitor ETL] → [Processamento] → [Banco de Dados]
     ↓              ↓                                    ↓               ↓              ↓
[Interface]    [Validação]                        [Job Manager]    [DataProcessor]  [Feedback]
```

## Guia de Uso

### 1. Upload de Arquivo via Interface Web

#### Passo a Passo:
1. **Acesse a aplicação** Streamlit
2. **Navegue para a aba "Upload"**
3. **Selecione o arquivo** usando o botão "Browse files"
4. **Aguarde a validação** automática (extensão e tamanho)
5. **Visualize o preview** dos dados (opcional)
6. **Clique em "Enviar Arquivo"**
7. **Acompanhe o progresso** na barra de status
8. **Receba confirmação** de sucesso ou erro

#### Tipos de Arquivo Suportados:
- **CSV** (.csv) - Dados tabulares separados por vírgula
- **Excel** (.xlsx, .xls) - Planilhas do Microsoft Excel
- **XML** (.xml) - Dados estruturados em formato XML

#### Limitações:
- **Tamanho máximo**: 50MB por arquivo
- **Tipos aceitos**: Apenas equipamentos e manutenções
- **Formato**: Deve seguir o schema esperado pelo sistema

### 2. Monitoramento do Processamento

#### Status Disponíveis:
- **📤 Uploaded** - Arquivo enviado com sucesso
- **⚙️ Processing** - Sendo processado pelo ETL
- **✅ Completed** - Processamento concluído com sucesso
- **❌ Failed** - Falha no processamento
- **🧹 Cleaned** - Arquivo removido pela limpeza automática

#### Acompanhamento:
1. **Histórico de Uploads** - Lista todos os uploads realizados
2. **Detalhes por Upload** - Status, métricas e logs específicos
3. **Notificações em Tempo Real** - Atualizações automáticas na sidebar
4. **Métricas Agregadas** - Estatísticas gerais de processamento

### 3. Diagnóstico e Testes

#### Aba de Diagnóstico:
- **Testes de Performance** - Arquivos grandes (40-45MB)
- **Testes de Concorrência** - Uploads simultâneos
- **Testes de Limpeza** - Limpeza automática
- **Testes de Integração** - Fluxo completo
- **Todos os Testes** - Execução completa (5-10 min)

## Configuração e Instalação

### Variáveis de Ambiente Necessárias:

```bash
# Configurações de Upload
MAX_FILE_SIZE_MB=50
UPLOAD_DIRECTORY=data/uploads
ALLOWED_EXTENSIONS=csv,xlsx,xls,xml

# Configurações de Limpeza
MAX_FILE_AGE_HOURS=24
CLEANUP_INTERVAL_HOURS=6

# Configurações de Monitoramento
MONITOR_INTERVAL_SECONDS=30
MAX_CONCURRENT_UPLOADS=5
```

### Estrutura de Diretórios:

```
data/
├── uploads/              # Arquivos recém-enviados
├── processed/           # Arquivos processados com sucesso
│   └── 2024-01-01/     # Organizados por data
└── failed/              # Arquivos com falha no processamento
    └── 2024-01-01/     # Organizados por data
```

### Tabelas do Banco de Dados:

```sql
-- Tabela para rastreamento de uploads
CREATE TABLE upload_status (
    id UUID PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_size INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL,
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processing_start_time TIMESTAMP,
    processing_end_time TIMESTAMP,
    records_processed INTEGER DEFAULT 0,
    error_message TEXT,
    metadata JSONB
);
```

## API Endpoints

### POST /api/v1/files/upload
**Descrição**: Upload de arquivo
**Parâmetros**:
- `file`: Arquivo a ser enviado (multipart/form-data)
- `file_type`: Tipo do arquivo (opcional, auto-detectado)

**Resposta**:
```json
{
    "upload_id": "uuid",
    "filename": "arquivo_processado.csv",
    "status": "uploaded",
    "message": "Arquivo enviado com sucesso"
}
```

### GET /api/v1/files/status/{upload_id}
**Descrição**: Consulta status de um upload
**Resposta**:
```json
{
    "upload_id": "uuid",
    "filename": "arquivo.csv",
    "status": "completed",
    "upload_time": "2024-01-01T10:00:00Z",
    "processing_time": 45.2,
    "records_processed": 1500,
    "file_size": 2048576
}
```

### GET /api/v1/files/history
**Descrição**: Histórico de uploads
**Parâmetros**:
- `limit`: Número máximo de registros (padrão: 50)
- `status`: Filtrar por status
- `file_type`: Filtrar por tipo de arquivo

### GET /api/v1/files/metrics
**Descrição**: Métricas agregadas de uploads

## Troubleshooting

### Problemas Comuns e Soluções

#### 1. "Arquivo muito grande"
**Problema**: Arquivo excede 50MB
**Solução**: 
- Dividir arquivo em partes menores
- Verificar configuração `MAX_FILE_SIZE_MB`
- Considerar compressão dos dados

#### 2. "Formato de arquivo não suportado"
**Problema**: Extensão não permitida
**Solução**:
- Verificar extensões suportadas: .csv, .xlsx, .xls, .xml
- Converter arquivo para formato suportado
- Verificar configuração `ALLOWED_EXTENSIONS`

#### 3. "Falha no processamento"
**Problema**: Erro durante o processamento ETL
**Solução**:
- Verificar logs do sistema
- Validar schema dos dados
- Conferir conexão com banco de dados
- Executar testes de diagnóstico

#### 4. "Upload travado em 'Processing'"
**Problema**: Processamento não finaliza
**Solução**:
- Verificar se o serviço de monitoramento está ativo
- Reiniciar o UploadMonitor
- Verificar logs de erro
- Executar limpeza manual se necessário

#### 5. "Arquivo não aparece no histórico"
**Problema**: Upload não é registrado
**Solução**:
- Verificar conectividade com banco de dados
- Conferir se tabela `upload_status` existe
- Executar script de criação de tabelas
- Verificar logs da API

### Comandos de Diagnóstico

#### Verificar Status do Sistema:
```bash
python scripts/testing/validate_system.py
```

#### Testar Funcionalidade de Upload:
```bash
python scripts/testing/test_upload_integration.py
```

#### Executar Testes de Performance:
```bash
python -m pytest tests/unit/test_upload_performance.py -v
```

#### Executar Todos os Testes de Upload:
```bash
python -m pytest tests/unit/test_upload_*.py tests/integration/test_upload_*.py -v
```

#### Verificar Logs:
```bash
# Logs da aplicação
tail -f logs/app.log

# Logs específicos de upload
grep "upload" logs/app.log | tail -20
```

### Monitoramento e Manutenção

#### Limpeza Manual de Arquivos:
```python
from src.etl.upload_monitor import UploadMonitor
monitor = UploadMonitor()
monitor.cleanup_old_files()
```

#### Verificar Diretórios:
```python
from src.etl.upload_monitor import UploadMonitor
monitor = UploadMonitor()
structure = monitor.get_directory_structure()
print(structure)
```

#### Reprocessar Arquivo com Falha:
```python
from src.etl.data_processor import DataProcessor
processor = DataProcessor()
result = processor.process_file("caminho/para/arquivo.csv", "equipments")
```

## Métricas e Performance

### Benchmarks Esperados:
- **Arquivos pequenos** (< 1MB): < 5 segundos
- **Arquivos médios** (1-10MB): 5-30 segundos  
- **Arquivos grandes** (10-50MB): 30-180 segundos
- **Uploads concorrentes**: Até 5 simultâneos
- **Memória adicional**: < 300MB por upload grande

### Monitoramento de Performance:
- Tempo de upload por arquivo
- Uso de memória durante processamento
- Taxa de sucesso/falha
- Tempo médio de processamento
- Throughput de registros por segundo

## Integração com Outros Módulos

### Pipeline ETL Existente:
- Utiliza os mesmos processadores (CSV, XLSX, XML)
- Integra com DataProcessor para validação
- Compartilha configurações de banco de dados
- Usa sistema de logging unificado

### Sistema de Feedback:
- Notificações em tempo real
- Histórico persistente
- Métricas agregadas
- Status detalhados

### Componentes Frontend:
- Integração com tema existente
- Uso de componentes reutilizáveis
- Sistema de erro handlers
- Validações frontend/backend

## Segurança

### Validações Implementadas:
- **Extensão de arquivo**: Whitelist de tipos permitidos
- **Tamanho de arquivo**: Limite configurável
- **Conteúdo**: Validação de schema dos dados
- **Nome de arquivo**: Sanitização e geração de nomes únicos
- **Upload rate limiting**: Controle de uploads simultâneos

### Recomendações de Segurança:
- Manter limite de tamanho adequado
- Monitorar uso de disco
- Implementar autenticação se necessário
- Logs de auditoria de uploads
- Backup regular dos dados processados

## Expansões Futuras

### Funcionalidades Planejadas:
- **Suporte a mais formatos**: JSON, Parquet
- **Upload em lote**: Múltiplos arquivos simultâneos
- **API de webhook**: Notificações externas
- **Interface de administração**: Gestão avançada
- **Integração com cloud storage**: S3, Azure Blob

### Melhorias de Performance:
- **Processamento assíncrono**: Workers dedicados
- **Cache de resultados**: Redis/Memcached
- **Compressão**: Arquivos grandes
- **Streaming**: Processamento em chunks
- **Load balancing**: Múltiplas instâncias 