# Proposta Técnica de Arquitetura - Sistema de Monitoramento Padtec

## 1. Visão Geral da Arquitetura

O sistema de monitoramento Padtec é uma aplicação distribuída em microsserviços, projetada para coletar dados contínuos de uma rede óptica, armazená-los em um banco de dados time-series, gerar alertas automáticos e exibir dashboards em tempo real.

```
┌─────────────────────────────────────────────────────────────────────┐
│                     PADTEC MONITORING SYSTEM                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────┐         ┌──────────────────┐                  │
│  │  Padtec API      │         │  Web Dashboard   │                  │
│  │  (Upstream)      │         │  (Frontend)      │                  │
│  └────────┬─────────┘         └────────┬─────────┘                  │
│           │                            │                             │
│           │                            │                             │
│  ┌────────▼──────────────────────────────────────┐                  │
│  │         API Gateway / Load Balancer            │                  │
│  │         (Nginx / Kong)                         │                  │
│  └────────┬──────────────────────────────────────┘                  │
│           │                                                           │
│  ┌────────┴──────────────────────────────────────┐                  │
│  │                                                │                  │
│  ▼                                                ▼                  │
│  ┌─────────────────────┐      ┌──────────────────────────┐          │
│  │  Data Collector     │      │  Alert Manager           │          │
│  │  (Python/FastAPI)   │      │  (Python/FastAPI)        │          │
│  │                     │      │                          │          │
│  │ - Fetch cards       │      │ - Process thresholds     │          │
│  │ - Fetch measurements│      │ - Generate alerts        │          │
│  │ - Validate data     │      │ - Send notifications     │          │
│  └────────┬────────────┘      └──────────┬───────────────┘          │
│           │                              │                           │
│           │                              │                           │
│  ┌────────┴──────────────────────────────┴───────────────┐          │
│  │                                                        │          │
│  │         Time-Series Database (InfluxDB/TimescaleDB)   │          │
│  │                                                        │          │
│  │  - Measurements (POWER, OPTICAL, TEMPERATURE)         │          │
│  │  - Alarms (ACTIVE, CLEARED, ACKNOWLEDGED)             │          │
│  │  - Inventory (Cards, Sites, Models)                   │          │
│  │  - Aggregations (Hourly, Daily, Monthly)              │          │
│  │                                                        │          │
│  └────────────────────────────────────────────────────────┘          │
│                                                                       │
│  ┌────────────────────────────────────────────────────────┐          │
│  │  Message Queue (RabbitMQ / Kafka)                      │          │
│  │  - Decoupling between services                         │          │
│  │  - Reliable event processing                           │          │
│  └────────────────────────────────────────────────────────┘          │
│                                                                       │
│  ┌────────────────────────────────────────────────────────┐          │
│  │  Notification Service                                  │          │
│  │  - Email, SMS, Telegram, Webhook                       │          │
│  └────────────────────────────────────────────────────────┘          │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Componentes Principais

### 2.1 Data Collector (Coletor de Dados)

**Responsabilidades:**
*   Autenticar na API Padtec periodicamente
*   Descobrir automaticamente todos os cartões (cards) instalados
*   Coletar medições para cada cartão
*   Validar e normalizar dados
*   Armazenar em banco de dados time-series
*   Implementar retry logic com backoff exponencial

**Tecnologia:** Python 3.11 + FastAPI + APScheduler

**Endpoints Internos:**
*   `POST /collector/start` - Iniciar coleta
*   `GET /collector/status` - Status da coleta
*   `GET /collector/logs` - Logs da coleta

**Frequência de Coleta:**
*   Medições críticas (Pump Power, OSNR): 30-60 segundos
*   Medições normais: 5 minutos
*   Inventário de cartões: 1 hora
*   Histórico de alarmes: 1 minuto

### 2.2 Alert Manager (Gerenciador de Alertas)

**Responsabilidades:**
*   Monitorar medições em tempo real
*   Comparar contra limites configuráveis
*   Implementar histerese para evitar flapping
*   Detectar degradação gradual (análise histórica)
*   Gerar eventos de alerta
*   Enviar notificações por múltiplos canais

**Tecnologia:** Python 3.11 + FastAPI + APScheduler

**Endpoints Internos:**
*   `POST /alerts/rules` - Criar/atualizar regras
*   `GET /alerts/active` - Listar alertas ativos
*   `POST /alerts/{id}/acknowledge` - Reconhecer alerta
*   `POST /alerts/{id}/clear` - Limpar alerta

**Regras de Alerta (Exemplos):**
*   Pump Power fora do range [12dBm, 24dBm]
*   Perda de potência > 3dBm em 1 hora
*   OSNR < 15dB
*   Card Down (status != UP)
*   Falta de atualização > 5 minutos

### 2.3 API Interna (Backend)

**Responsabilidades:**
*   Expor dados coletados para o frontend
*   Gerenciar configurações de alertas
*   Fornecer endpoints para histórico e análise
*   Autenticação e autorização

**Tecnologia:** Python 3.11 + FastAPI

**Endpoints Principais:**
*   `GET /api/sites` - Listar sites
*   `GET /api/sites/{siteId}/cards` - Listar cartões de um site
*   `GET /api/cards/{cardSerial}/measurements` - Histórico de medições
*   `GET /api/measurements/latest` - Últimas medições
*   `GET /api/alarms` - Listar alarmes
*   `POST /api/alarms/{id}/acknowledge` - Reconhecer alerta
*   `GET /api/dashboards/{dashboardId}` - Dados do dashboard

### 2.4 Frontend (Dashboard)

**Responsabilidades:**
*   Exibir dados em tempo real
*   Mostrar gráficos e tendências
*   Listar sites, cartões e medições
*   Exibir alarmes ativos
*   Permitir configuração de alertas

**Tecnologia:** React 18 + TypeScript + TailwindCSS + Chart.js / Recharts

**Páginas Principais:**
1.  **Dashboard Geral** - Visão geral de todos os sites
2.  **Sites** - Lista de sites com status
3.  **Cartões** - Detalhes de cada cartão
4.  **Medições** - Histórico e gráficos
5.  **Alarmes** - Timeline de alarmes
6.  **Configurações** - Limites e regras de alerta

---

## 3. Banco de Dados

### 3.1 Time-Series Database

**Recomendação:** TimescaleDB (PostgreSQL com extensão) ou InfluxDB

**Vantagens do TimescaleDB:**
*   Compatibilidade com PostgreSQL
*   Excelente performance para time-series
*   Suporte a queries SQL complexas
*   Compressão automática de dados antigos
*   Backup e replicação nativos

**Tabelas Principais:**

#### Tabela: `measurements`
```sql
CREATE TABLE measurements (
    time TIMESTAMPTZ NOT NULL,
    card_serial VARCHAR(50) NOT NULL,
    card_part VARCHAR(100),
    location_site VARCHAR(50),
    measure_key VARCHAR(100) NOT NULL,
    measure_name VARCHAR(200),
    measure_value FLOAT8,
    measure_unit VARCHAR(20),
    measure_group VARCHAR(50),
    quality VARCHAR(20),
    PRIMARY KEY (time, card_serial, measure_key)
);

SELECT create_hypertable('measurements', 'time', if_not_exists => TRUE);
CREATE INDEX ON measurements (card_serial, time DESC);
CREATE INDEX ON measurements (location_site, time DESC);
CREATE INDEX ON measurements (measure_key, time DESC);
```

#### Tabela: `cards`
```sql
CREATE TABLE cards (
    card_serial VARCHAR(50) PRIMARY KEY,
    card_part VARCHAR(100),
    card_family VARCHAR(50),
    card_model VARCHAR(100),
    location_site VARCHAR(50),
    slot_number INTEGER,
    status VARCHAR(20),
    installed_at TIMESTAMPTZ,
    last_updated TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ON cards (location_site);
CREATE INDEX ON cards (card_family);
```

#### Tabela: `alarms`
```sql
CREATE TABLE alarms (
    alarm_id VARCHAR(100) PRIMARY KEY,
    alarm_type VARCHAR(50),
    severity VARCHAR(20),
    card_serial VARCHAR(50),
    location_site VARCHAR(50),
    description TEXT,
    triggered_at TIMESTAMPTZ NOT NULL,
    cleared_at TIMESTAMPTZ,
    status VARCHAR(20),
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ON alarms (card_serial, triggered_at DESC);
CREATE INDEX ON alarms (location_site, triggered_at DESC);
CREATE INDEX ON alarms (status, triggered_at DESC);
```

#### Tabela: `alert_rules`
```sql
CREATE TABLE alert_rules (
    rule_id SERIAL PRIMARY KEY,
    rule_name VARCHAR(200),
    measure_key VARCHAR(100),
    condition VARCHAR(50), -- 'ABOVE', 'BELOW', 'RANGE'
    threshold_min FLOAT8,
    threshold_max FLOAT8,
    severity VARCHAR(20),
    enabled BOOLEAN DEFAULT TRUE,
    hysteresis FLOAT8 DEFAULT 0.5,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.2 Política de Retenção

*   **Dados Brutos**: 30 dias
*   **Agregação Horária**: 1 ano
*   **Agregação Diária**: 3 anos
*   **Alarmes**: 1 ano (com arquivo)

---

## 4. Scheduler (Agendador de Tarefas)

**Tecnologia:** APScheduler (Python)

**Tarefas Agendadas:**

| Tarefa | Frequência | Descrição |
| :--- | :--- | :--- |
| `collect_cards` | 1 hora | Descobrir novos cartões |
| `collect_measurements` | 30-60 segundos | Coletar medições críticas |
| `collect_measurements_normal` | 5 minutos | Coletar medições normais |
| `check_alarms` | 1 minuto | Verificar e gerar alarmes |
| `aggregate_hourly` | 1 hora | Agregar dados por hora |
| `aggregate_daily` | 1 dia | Agregar dados por dia |
| `cleanup_old_data` | 1 dia | Remover dados antigos |
| `send_notifications` | Contínuo | Enviar notificações de alerta |

---

## 5. Message Queue (Fila de Mensagens)

**Tecnologia:** RabbitMQ ou Kafka

**Tópicos/Filas:**

*   `measurements.collected` - Novas medições coletadas
*   `alarms.triggered` - Alarmes disparados
*   `alarms.cleared` - Alarmes limpos
*   `notifications.pending` - Notificações a enviar

**Benefícios:**
*   Desacoplamento entre serviços
*   Processamento assíncrono confiável
*   Retry automático em caso de falha
*   Escalabilidade horizontal

---

## 6. Notification Service (Serviço de Notificações)

**Canais Suportados:**
*   Email (SMTP)
*   Telegram (Bot API)
*   WhatsApp (Twilio)
*   Webhook (HTTP POST)
*   SMS (Twilio)

**Configuração por Severidade:**

| Severidade | Email | Telegram | SMS | Webhook |
| :--- | :--- | :--- | :--- | :--- |
| MINOR | ✓ | ✓ | ✗ | ✓ |
| MAJOR | ✓ | ✓ | ✓ | ✓ |
| CRITICAL | ✓ | ✓ | ✓ | ✓ |

---

## 7. Containerização (Docker Compose)

**Estrutura de Containers:**

```yaml
version: '3.9'

services:
  # Database
  timescaledb:
    image: timescale/timescaledb:latest-pg15
    environment:
      POSTGRES_PASSWORD: secure_password
    volumes:
      - timescaledb_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  # Message Queue
  rabbitmq:
    image: rabbitmq:3.12-management
    environment:
      RABBITMQ_DEFAULT_USER: guest
      RABBITMQ_DEFAULT_PASS: guest
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
    ports:
      - "5672:5672"
      - "15672:15672"

  # Data Collector
  collector:
    build: ./services/collector
    environment:
      PADTEC_API_URL: http://108.165.140.144:8181/nms-api/
      PADTEC_API_TOKEN: ${PADTEC_API_TOKEN}
      DATABASE_URL: postgresql://user:password@timescaledb:5432/padtec
      RABBITMQ_URL: amqp://guest:guest@rabbitmq:5672/
    depends_on:
      - timescaledb
      - rabbitmq
    restart: always

  # Alert Manager
  alert_manager:
    build: ./services/alert_manager
    environment:
      DATABASE_URL: postgresql://user:password@timescaledb:5432/padtec
      RABBITMQ_URL: amqp://guest:guest@rabbitmq:5672/
    depends_on:
      - timescaledb
      - rabbitmq
    restart: always

  # Backend API
  backend:
    build: ./services/backend
    environment:
      DATABASE_URL: postgresql://user:password@timescaledb:5432/padtec
      RABBITMQ_URL: amqp://guest:guest@rabbitmq:5672/
    ports:
      - "8000:8000"
    depends_on:
      - timescaledb
      - rabbitmq
    restart: always

  # Frontend
  frontend:
    build: ./services/frontend
    ports:
      - "3000:3000"
    environment:
      REACT_APP_API_URL: http://localhost:8000/api
    depends_on:
      - backend
    restart: always

  # Notification Service
  notifier:
    build: ./services/notifier
    environment:
      DATABASE_URL: postgresql://user:password@timescaledb:5432/padtec
      RABBITMQ_URL: amqp://guest:guest@rabbitmq:5672/
      SMTP_SERVER: ${SMTP_SERVER}
      SMTP_USER: ${SMTP_USER}
      SMTP_PASSWORD: ${SMTP_PASSWORD}
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
    depends_on:
      - rabbitmq
    restart: always

volumes:
  timescaledb_data:
  rabbitmq_data:
```

---

## 8. Estrutura de Microsserviços

A arquitetura utiliza microsserviços para garantir escalabilidade e manutenibilidade:

### 8.1 Serviço de Coleta (Collector)
*   Responsável por comunicar com a API Padtec
*   Implementa retry logic e circuit breaker
*   Publica eventos de medições coletadas

### 8.2 Serviço de Alertas (Alert Manager)
*   Monitora medições em tempo real
*   Aplica regras de alerta configuráveis
*   Publica eventos de alarme

### 8.3 Serviço de Backend (API)
*   Expõe dados para o frontend
*   Gerencia configurações
*   Fornece endpoints para análise

### 8.4 Serviço de Notificações (Notifier)
*   Consome eventos de alarme
*   Envia notificações por múltiplos canais
*   Implementa rate limiting e deduplicação

### 8.5 Serviço de Frontend (Dashboard)
*   Interface web em React
*   Conexão WebSocket para atualizações em tempo real
*   Gráficos interativos com Chart.js

---

## 9. Fluxo de Dados

```
┌─────────────────────┐
│   Padtec API        │
│  (Upstream)         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Data Collector     │
│  - Fetch cards      │
│  - Fetch measures   │
│  - Validate         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  TimescaleDB        │
│  - Store raw data   │
│  - Index by time    │
└──────────┬──────────┘
           │
      ┌────┴────┐
      │          │
      ▼          ▼
   ┌──────────┐ ┌──────────────┐
   │ Backend  │ │ Alert        │
   │ API      │ │ Manager      │
   └────┬─────┘ └──────┬───────┘
        │               │
        │          ┌────▼─────┐
        │          │ RabbitMQ  │
        │          │ (Events)  │
        │          └────┬─────┘
        │               │
        │          ┌────▼─────────┐
        │          │ Notifier      │
        │          │ (Email, SMS)  │
        │          └───────────────┘
        │
        ▼
   ┌──────────┐
   │ Frontend │
   │ (React)  │
   └──────────┘
```

---

## 10. Tecnologias Recomendadas

| Componente | Tecnologia | Justificativa |
| :--- | :--- | :--- |
| **Backend** | Python 3.11 + FastAPI | Performance, async, documentação automática |
| **Database** | TimescaleDB | Time-series otimizado, SQL compatível |
| **Message Queue** | RabbitMQ | Confiabilidade, routing avançado |
| **Scheduler** | APScheduler | Flexibilidade, Python nativo |
| **Frontend** | React 18 + TypeScript | Reatividade, type safety, comunidade |
| **Gráficos** | Chart.js / Recharts | Interatividade, performance |
| **Containerização** | Docker Compose | Simplicidade, desenvolvimento local |
| **Orquestração** | Kubernetes (futuro) | Escalabilidade em produção |

---

## 11. Melhores Práticas

### 11.1 Desenvolvimento
*   Usar versionamento semântico para APIs
*   Implementar logging estruturado (JSON)
*   Testes unitários e integração (pytest, Jest)
*   CI/CD com GitHub Actions ou GitLab CI

### 11.2 Produção
*   Usar HTTPS/TLS para todas as comunicações
*   Implementar autenticação e autorização (JWT)
*   Monitorar performance com Prometheus/Grafana
*   Backup automático do banco de dados
*   Plano de disaster recovery

### 11.3 Segurança
*   Validar todas as entradas
*   Usar variáveis de ambiente para secrets
*   Implementar rate limiting
*   Auditar acesso a dados sensíveis
*   Manter dependências atualizadas

---

## 12. Possíveis Expansões Futuras

1.  **Machine Learning**: Detecção de anomalias com modelos preditivos
2.  **Integração com Grafana**: Exportar dados para Grafana nativo
3.  **Kubernetes**: Orquestração em produção
4.  **Multi-tenancy**: Suportar múltiplas redes Padtec
5.  **API GraphQL**: Alternativa ao REST para queries flexíveis
6.  **Mobile App**: Aplicativo mobile para alertas e monitoramento
7.  **Integração com ServiceNow**: Criação automática de tickets
8.  **Análise Preditiva**: Previsão de falhas baseada em histórico

---

## Conclusão

Esta arquitetura fornece uma base sólida e escalável para monitoramento contínuo de redes ópticas Padtec. A separação em microsserviços, o uso de banco de dados time-series e a implementação de alertas em tempo real garantem visibilidade completa e resposta rápida a incidentes.
