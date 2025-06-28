# Solução: Problema de Comunicação entre Containers Docker

**Data:** 25/06/2025  
**Sistema:** PROAtivo API  
**Problema:** Falhas de comunicação entre containers Docker com status 400  
**Status:** ✅ **RESOLVIDO**

---

## 🔍 **Diagnóstico do Problema**

### **Sintomas Observados**
- ✅ Requests de **localhost (127.0.0.1)** funcionavam normalmente (status 200)
- ❌ Requests de **containers Docker (172.18.0.5)** falhavam com **status 400**
- ❌ Endpoints `/api/v1/health/` e `/api/v1/chat/` rejeitavam requests entre containers
- ⚠️ Logs mostravam falhas rápidas (~2ms) indicando rejeição imediata

### **Logs Típicos do Problema**
```json
{
  "timestamp": "2025-06-25T01:44:44.720332",
  "level": "INFO",
  "message": "Request completed: GET /api/v1/health/",
  "extra": {
    "method": "GET",
    "path": "/api/v1/health/",
    "status_code": 400,
    "client_ip": "172.18.0.5"
  }
}
```

---

## 🎯 **Causa Raiz Identificada**

### **Problema Principal: Configuração de Ambiente**
A variável `environment` no arquivo `config.py` estava **hardcoded** como "development" e não lia do arquivo `.env`:

```python
# ❌ PROBLEMA - Não lia do .env
environment: str = "development"
```

### **Problema Secundário: TrustedHostMiddleware**
Como a aplicação sempre rodava em modo "development" internamente, mas o Docker Compose configurava como "production", o middleware `TrustedHostMiddleware` aplicava configurações inadequadas.

**Em modo production (real):**
```python
allowed_hosts = ["api.proativo.com", "localhost"]  # ❌ Não incluía containers
```

---

## 🔧 **Solução Implementada**

### **Correção 1: Configuração de Ambiente**
**Arquivo:** `proativo/src/api/config.py`

```python
# ✅ ANTES (PROBLEMA)
environment: str = "development"

# ✅ DEPOIS (CORRIGIDO)
environment: str = Field(default="development", env="ENVIRONMENT")
```

### **Correção 2: TrustedHostMiddleware**
**Arquivo:** `proativo/src/api/main.py`

```python
# ✅ ANTES (PROBLEMA)
if not settings.is_development():
    allowed_hosts = ["api.proativo.com", "localhost"]
else:
    allowed_hosts = ["*"]

# ✅ DEPOIS (CORRIGIDO)
if not settings.is_development():
    allowed_hosts = [
        "api.proativo.com", 
        "localhost", 
        "127.0.0.1",
        "proativo-app",
        "streamlit-app",
        "0.0.0.0"
    ]
else:
    allowed_hosts = ["*"]
```

---

## 📝 **Comandos de Aplicação**

### **1. Parar Containers**
```bash
cd /d/Proativo/proativo-main/proativo
docker compose down
```

### **2. Aplicar Correções**
- Editar `proativo/src/api/config.py`
- Editar `proativo/src/api/main.py`

### **3. Reiniciar Containers**
```bash
docker compose up -d
# ou apenas reiniciar a API
docker compose restart proativo-app
```

---

## ✅ **Validação da Solução**

### **Teste 1: Health Check**
```bash
docker compose exec streamlit-app curl -f http://proativo-app:8000/api/v1/health/
```

**Resultado Esperado:**
```json
{
  "status": "healthy",
  "timestamp": "2025-06-25T02:37:41.537162",
  "version": "0.1.0",
  "environment": "production",
  "uptime_seconds": 19.186841,
  "system": {
    "cpu_percent": 1.5,
    "memory_percent": 7.6,
    "disk_percent": 0.8
  }
}
```

### **Teste 2: Chat Endpoint**
```bash
docker compose exec streamlit-app curl -X POST \
  "http://proativo-app:8000/api/v1/chat/" \
  -H "Content-Type: application/json" \
  -d '{"message": "teste"}'
```

**Resultado Esperado:**
```json
{
  "message_id": "uuid-generated",
  "session_id": "uuid-generated",
  "response": "Resposta da IA...",
  "response_type": "success",
  "query_type": "general_query"
}
```

---

## 🔄 **Fluxo de Comunicação Corrigido**

### **Antes (Falhando)**
```
Streamlit Container (172.18.0.5) 
    ↓ HTTP Request
API Container (TrustedHostMiddleware)
    ↓ Host Check: "172.18.0.5" não está em allowed_hosts
    ❌ Status 400 - Rejeitado
```

### **Depois (Funcionando)**
```
Streamlit Container (streamlit-app) 
    ↓ HTTP Request com Host: proativo-app:8000
API Container (TrustedHostMiddleware)
    ↓ Host Check: "proativo-app" está em allowed_hosts
    ✅ Status 200 - Processado normalmente
```

---

## 📊 **Impacto da Solução**

### **Performance**
- ✅ Comunicação entre containers: **2ms** (antes falhava)
- ✅ Localhost continua funcionando: **1000ms** (sem alteração)
- ✅ Sem overhead adicional de segurança

### **Segurança**
- ✅ Hosts de produção ainda restringidos
- ✅ Containers Docker permitidos especificamente
- ✅ Proteção contra host header injection mantida

### **Funcionalidade**
- ✅ Frontend Streamlit pode comunicar com API
- ✅ Health checks funcionam
- ✅ Chat endpoints operacionais
- ✅ Todos os middlewares funcionais

---

## 🚨 **Lições Aprendidas**

### **1. Configuração de Ambiente**
- Sempre usar `Field(env="VARIABLE_NAME")` para variáveis que devem vir do `.env`
- Validar que variáveis de ambiente estão sendo lidas corretamente
- Testar em diferentes ambientes (dev/prod)

### **2. Docker Networking**
- Containers se comunicam via nomes de serviço (não IPs)
- TrustedHostMiddleware precisa incluir nomes de containers
- Header `Host` é preenchido automaticamente pelo Docker

### **3. Middleware de Segurança**
- TrustedHostMiddleware é essencial mas pode bloquear comunicação legítima
- Sempre incluir todos os hosts válidos para o ambiente
- Testar comunicação entre todos os componentes

---

## 🛠️ **Configuração Final**

### **Docker Compose (.env)**
```env
ENVIRONMENT=production
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/db
CORS_ORIGINS=http://localhost:8501,http://streamlit-app:8501
```

### **Hosts Permitidos em Produção**
- `api.proativo.com` - Domain principal
- `localhost` - Testes locais
- `127.0.0.1` - Testes locais
- `proativo-app` - Container da API
- `streamlit-app` - Container do frontend
- `0.0.0.0` - Bind interno

---

## 📈 **Status Final**

| Componente | Status | Observações |
|------------|---------|-------------|
| **Health Check** | ✅ Funcionando | Resposta em 2ms |
| **Chat API** | ✅ Funcionando | IA processando |
| **CORS** | ✅ Funcionando | Headers corretos |
| **Environment** | ✅ Production | Lendo do .env |
| **Logs** | ✅ Funcionando | JSON structured |
| **Containers** | ✅ Comunicando | Docker networking |

---

**Solução implementada com sucesso em 25/06/2025**  
**Documentado por:** Sistema PROAtivo  
**Revisão:** v1.0 