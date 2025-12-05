# Análise Consolidada da Arquitetura - Sistema de Monitoramento Padtec

## 📋 Resumo Executivo

Este documento consolida a análise completa da arquitetura proposta para o sistema de monitoramento da rede óptica Padtec. O sistema é projetado como uma aplicação distribuída em microsserviços, capaz de coletar dados contínuos da API Padtec NMS, armazená-los em banco de dados time-series, gerar alertas automáticos e exibir dashboards em tempo real estilo Grafana.

---

## 🏗️ 1. Arquitetura Geral do Sistema

### 1.1 Visão de Alto Nível

O sistema segue uma arquitetura de **microsserviços** com os seguintes componentes principais:

```
┌─────────────────────────────────────────────────────────────────┐
│                    PADTEC MONITORING SYSTEM                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐         ┌──────────────┐                      │
│  │  Padtec API  │         │  Web         │                      │
│  │  (Upstream)  │         │  Dashboard   │                      │
│  └──────┬───────┘         └──────┬───────┘                      │
│         │                        │                                │
│  ┌──────▼────────────────────────▼──────┐                        │
│  │   API Gateway / Load Balancer        │                        │
│  │   (Nginx / Kong)                     │                        │
│  └──────┬───────────────────────────────┘                        │
│         │                                                         │
│  ┌──────┴───────────────────────────────┐                        │
│  │                                       │                        │
│  ▼                                       ▼                        │
│  ┌──────────────────┐      ┌────────────────────┐               │
│  │  Data Collector  │      │  Alert Manager     │               │
│  │  (FastAPI)       │      │  (FastAPI)         │               │
│  └────────┬─────────┘      └──────────┬─────────┘               │
│           │                             │                         │
│  ┌────────┴─────────────────────────────┴─────────┐             │
│  │                                                 │             │
│  │    Time-Series Database (TimescaleDB)          │             │
│  │                                                 │             │
│  └─────────────────────────────────────────────────┘             │
│                                                                   │
│  ┌─────────────────────────────────────────────────┐            │
│  │  Message Queue (RabbitMQ)                       │            │
│  └─────────────────────────────────────────────────┘            │
│                                                                   │
│  ┌─────────────────────────────────────────────────┐            │
│  │  Notification Service                           │            │
│  │  (Email, SMS, Telegram, Webhook)               │            │
│  └─────────────────────────────────────────────────┘            │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Fluxo de Dados Principal

1. **Coleta**: Data Collector consulta a API Padtec periodicamente
2. **Armazenamento**: Dados são persistidos no TimescaleDB
3. **Processamento**: Alert Manager avalia regras em tempo real
4. **Notificação**: Notifier envia alertas por múltiplos canais
5. **Visualização**: Frontend exibe dashboards em tempo real

---

## 🔌 2. Integração com API Padtec NMS

### 2.1 Informações de Acesso

| Atributo | Valor |
|----------|-------|
| **URL Base** | `http://108.165.140.144:8181/nms-api/` |
| **Protocolo** | HTTP/REST |
| **Autenticação** | Bearer Token (JWT) |
| **Formato** | JSON |

### 2.2 Entidades Principais

#### 2.2.1 Cartões (Cards)
- `cardPart`: Identificador único da placa (SKU)
- `cardSerial`: Número de série único
- `cardFamily`: Família (OADM, ROADM, Amplifier)
- `cardModel`: Modelo específico
- `locationSite`: Site/localização
- `slotNumber`: Posição física no chassis
- `status`: Estado operacional (UP, DOWN, DEGRADED)

#### 2.2.2 Medições (Measurements)
- `measureName`: Nome amigável (ex: "Pump Power")
- `measureValue`: Valor numérico
- `measureUnit`: Unidade (dBm, °C, dB)
- `measureGroup`: Categoria (POWER, OPTICAL, TEMPERATURE)
- `measureKey`: Chave única normalizada
- `timestamp`: Momento da coleta
- `quality`: Qualidade da medição (GOOD, FAIR, POOR)

#### 2.2.3 Alarmes (Alarms)
- `alarmId`: Identificador único
- `alarmType`: Tipo de alarme
- `severity`: Severidade (MINOR, MAJOR, CRITICAL)
- `triggeredAt`: Momento do disparo
- `clearedAt`: Momento da limpeza
- `status`: Estado (ACTIVE, CLEARED, ACKNOWLEDGED)

### 2.3 Frequência de Coleta Recomendada

| Tipo de Dado | Frequência | Justificativa |
|--------------|------------|---------------|
| **Medições Críticas** (Pump Power, OSNR) | 30-60 segundos | Detectar degradação rápida |
| **Medições Normais** | 5 minutos | Monitoramento contínuo |
| **Inventário de Cartões** | 1 hora | Detectar mudanças de hardware |
| **Histórico de Alarmes** | 1 minuto | Capturar eventos rapidamente |

---

## 🧩 3. Componentes do Sistema

### 3.1 Data Collector (Coletor de Dados)

**Responsabilidades:**
- Autenticar na API Padtec periodicamente
- Descobrir automaticamente todos os cartões instalados
- Coletar medições para cada cartão
- Validar e normalizar dados
- Armazenar em banco de dados time-series
- Implementar retry logic com backoff exponencial

**Tecnologia:** Python 3.11 + FastAPI + APScheduler

**Endpoints Internos:**
- `POST /collector/start` - Iniciar coleta
- `GET /collector/status` - Status da coleta
- `GET /collector/logs` - Logs da coleta

### 3.2 Alert Manager (Gerenciador de Alertas)

**Responsabilidades:**
- Monitorar medições em tempo real
- Comparar contra limites configuráveis
- Implementar histerese para evitar flapping
- Detectar degradação gradual (análise histórica)
- Gerar eventos de alerta
- Enviar notificações por múltiplos canais

**Tecnologia:** Python 3.11 + FastAPI + APScheduler

**Endpoints Internos:**
- `POST /alerts/rules` - Criar/atualizar regras
- `GET /alerts/active` - Listar alertas ativos
- `POST /alerts/{id}/acknowledge` - Reconhecer alerta
- `POST /alerts/{id}/clear` - Limpar alerta

### 3.3 Backend API

**Responsabilidades:**
- Expor dados coletados para o frontend
- Gerenciar configurações de alertas
- Fornecer endpoints para histórico e análise
- Autenticação e autorização

**Tecnologia:** Python 3.11 + FastAPI

**Endpoints Principais:**
- `GET /api/sites` - Listar sites
- `GET /api/sites/{siteId}/cards` - Listar cartões de um site
- `GET /api/cards/{cardSerial}/measurements` - Histórico de medições
- `GET /api/measurements/latest` - Últimas medições
- `GET /api/alarms` - Listar alarmes
- `POST /api/alarms/{id}/acknowledge` - Reconhecer alerta
- `GET /api/dashboards/{dashboardId}` - Dados do dashboard

### 3.4 Frontend (Dashboard)

**Responsabilidades:**
- Exibir dados em tempo real
- Mostrar gráficos e tendências
- Listar sites, cartões e medições
- Exibir alarmes ativos
- Permitir configuração de alertas

**Tecnologia:** React 18 + TypeScript + TailwindCSS + Chart.js / Recharts

**Páginas Principais:**
1. **Dashboard Geral** - Visão geral de todos os sites
2. **Sites** - Lista de sites com status
3. **Cartões** - Detalhes de cada cartão
4. **Medições** - Histórico e gráficos
5. **Alarmes** - Timeline de alarmes
6. **Configurações** - Limites e regras de alerta

### 3.5 Notification Service

**Canais Suportados:**
- Email (SMTP)
- Telegram (Bot API)
- WhatsApp (Twilio)
- Webhook (HTTP POST)
- SMS (Twilio)

**Configuração por Severidade:**

| Severidade | Email | Telegram | SMS | Webhook |
|------------|-------|----------|-----|---------|
| MINOR | ✓ | ✓ | ✗ | ✓ |
| MAJOR | ✓ | ✓ | ✓ | ✓ |
| CRITICAL | ✓ | ✓ | ✓ | ✓ |

---

## 🗄️ 4. Banco de Dados

### 4.1 Time-Series Database

**Recomendação:** TimescaleDB (PostgreSQL com extensão)

**Vantagens:**
- Compatibilidade com PostgreSQL
- Excelente performance para time-series
- Suporte a queries SQL complexas
- Compressão automática de dados antigos
- Backup e replicação nativos

### 4.2 Estrutura de Tabelas

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

### 4.3 Política de Retenção

- **Dados Brutos**: 30 dias
- **Agregação Horária**: 1 ano
- **Agregação Diária**: 3 anos
- **Alarmes**: 1 ano (com arquivo)

---

## ⚙️ 5. Scheduler e Tarefas Agendadas

**Tecnologia:** APScheduler (Python)

| Tarefa | Frequência | Descrição |
|--------|------------|-----------|
| `collect_cards` | 1 hora | Descobrir novos cartões |
| `collect_measurements` | 30-60 segundos | Coletar medições críticas |
| `collect_measurements_normal` | 5 minutos | Coletar medições normais |
| `check_alarms` | 1 minuto | Verificar e gerar alarmes |
| `aggregate_hourly` | 1 hora | Agregar dados por hora |
| `aggregate_daily` | 1 dia | Agregar dados por dia |
| `cleanup_old_data` | 1 dia | Remover dados antigos |
| `send_notifications` | Contínuo | Enviar notificações de alerta |

---

## 📨 6. Message Queue

**Tecnologia:** RabbitMQ

**Tópicos/Filas:**
- `measurements.collected` - Novas medições coletadas
- `alarms.triggered` - Alarmes disparados
- `alarms.cleared` - Alarmes limpos
- `notifications.pending` - Notificações a enviar

**Benefícios:**
- Desacoplamento entre serviços
- Processamento assíncrono confiável
- Retry automático em caso de falha
- Escalabilidade horizontal

---

## 🚨 7. Regras de Alerta

### 7.1 Regras Propostas

| Regra | Descrição | Severidade | Threshold/Condição | Histerese |
|-------|-----------|------------|-------------------|-----------|
| **Pump Power Fora do Range** | Potência da bomba fora dos limites | CRITICAL | < 12 dBm ou > 24 dBm | 0.5 dBm |
| **Perda de Potência Óptica** | Queda na potência de entrada/saída | MAJOR | `Input Power` < -20 dBm | 1.0 dBm |
| **Degradação de Potência** | Perda de potência em período | MAJOR | Perda > 3 dBm em 1 hora | N/A |
| **OSNR Abaixo do Limite** | OSNR abaixo do mínimo | CRITICAL | `OSNR` < 15 dB | 0.2 dB |
| **Card Down** | Cartão não operacional | CRITICAL | `status` != "UP" | N/A |
| **Telemetria Atrasada** | Falha na atualização | MINOR | `lastUpdated` > 5 minutos | N/A |
| **Temperatura Elevada** | Temperatura acima do limite | MAJOR | `Temperature` > 60 °C | 1.0 °C |

### 7.2 Histerese

A histerese evita "flapping" (alternância rápida entre alerta e normal). Exemplo:
- **Disparo**: Quando `Pump Power` cai para **11.5 dBm** (limite - histerese)
- **Limpeza**: Quando `Pump Power` retorna para **12.5 dBm** (limite + histerese)

### 7.3 Detecção de Degradação

O Alert Manager realiza consultas históricas no TimescaleDB para detectar tendências:
```sql
SELECT avg(measure_value) 
FROM measurements 
WHERE card_serial='{id}' 
  AND measure_key='InputPower' 
  AND time > now() - interval '1 hour'
```

---

## 📊 8. Dashboard Estilo Grafana

### 8.1 Dashboard Geral por Site

| Painel | Tipo | Métrica Principal |
|--------|------|-------------------|
| **Status da Rede** | Stat/Gauge | Porcentagem de Cards UP |
| **Alarmes Ativos** | Tabela | Contagem por Severidade |
| **Mapa de Sites** | Geomap | Localização dos Sites |
| **Últimas Medições Críticas** | Tabela | Pump Power, OSNR, Input Power |
| **Timeline de Alarmes** | Gráfico Temporal | Eventos nas últimas 24h |
| **Inventário Rápido** | Stat/Tabela | Distribuição de tipos de placas |

### 8.2 Dashboard Detalhado por Card

| Painel | Tipo | Métrica Principal |
|--------|------|-------------------|
| **Status do Card** | Stat/Gauge | Status UP/DOWN |
| **Pump Power (Tendência)** | Gráfico Temporal | Pump Power (dBm) |
| **OSNR (Tendência)** | Gráfico Temporal | OSNR (dB) |
| **In/Out Power** | Gráfico Temporal | Input/Output Power (dBm) |
| **Temperatura** | Gráfico Temporal | Temperature (°C) |
| **Timeline de Alarmes** | Tabela/Gráfico | Histórico de Alarmes |
| **Últimas Medições** | Tabela | Todas as measureKey |

### 8.3 Esquema de Cores

| Cor | Significado | Uso |
|-----|-------------|-----|
| **Verde** (#4CAF50) | Normal / UP | Status de Cards, Medições dentro do limite |
| **Amarelo** (#FFC107) | Aviso / MINOR | Alertas de baixa severidade |
| **Laranja** (#FF9800) | Atenção / MAJOR | Alertas de média severidade |
| **Vermelho** (#F44336) | Crítico / DOWN | Alertas de alta severidade, falha |
| **Azul** (#2196F3) | Informativo | Dados históricos, tendências |

---

## 🐳 9. Containerização

### 9.1 Docker Compose

A aplicação será containerizada usando Docker Compose com os seguintes serviços:

- **timescaledb**: Banco de dados time-series
- **rabbitmq**: Message queue
- **collector**: Serviço de coleta de dados
- **alert_manager**: Gerenciador de alertas
- **backend**: API interna
- **frontend**: Dashboard web
- **notifier**: Serviço de notificações

### 9.2 Estrutura de Microsserviços

Cada serviço é independente e pode ser escalado horizontalmente:
- **Collector**: Múltiplas instâncias para alta disponibilidade
- **Alert Manager**: Processamento paralelo de regras
- **Backend**: Load balancing para múltiplas requisições
- **Notifier**: Processamento assíncrono de notificações

---

## 🔄 10. Fluxo Operacional Completo

```
1. Scheduler inicia ciclo de coleta
   ↓
2. Data Collector autentica na API Padtec
   ↓
3. Busca inventário: GET /cards
   ↓
4. Para cada card detectado:
   ↓
5. Consulta medições: GET /measurements?cardSerial={id}
   ↓
6. Normaliza e valida dados
   ↓
7. Armazena em TimescaleDB
   ↓
8. Publica evento: measurements.collected (RabbitMQ)
   ↓
9. Alert Manager consome evento
   ↓
10. Aplica regras de alerta (threshold, histórico)
    ↓
11. Se alerta disparado → Publica: alarms.triggered
    ↓
12. Notifier consome evento
    ↓
13. Envia notificação (Telegram, Email, Webhook)
    ↓
14. Backend API expõe dados
    ↓
15. Frontend exibe no dashboard
```

---

## 🛠️ 11. Stack Tecnológico

| Componente | Tecnologia | Justificativa |
|------------|------------|---------------|
| **Backend** | Python 3.11 + FastAPI | Performance, async, documentação automática |
| **Database** | TimescaleDB | Time-series otimizado, SQL compatível |
| **Message Queue** | RabbitMQ | Confiabilidade, routing avançado |
| **Scheduler** | APScheduler | Flexibilidade, Python nativo |
| **Frontend** | React 18 + TypeScript | Reatividade, type safety, comunidade |
| **Gráficos** | Chart.js / Recharts | Interatividade, performance |
| **Containerização** | Docker Compose | Simplicidade, desenvolvimento local |
| **Orquestração** | Kubernetes (futuro) | Escalabilidade em produção |

---

## ✅ 12. Melhores Práticas

### 12.1 Desenvolvimento
- Versionamento semântico para APIs
- Logging estruturado (JSON)
- Testes unitários e integração (pytest, Jest)
- CI/CD com GitHub Actions ou GitLab CI

### 12.2 Produção
- HTTPS/TLS para todas as comunicações
- Autenticação e autorização (JWT)
- Monitoramento com Prometheus/Grafana
- Backup automático do banco de dados
- Plano de disaster recovery

### 12.3 Segurança
- Validar todas as entradas
- Variáveis de ambiente para secrets
- Rate limiting
- Auditoria de acesso
- Dependências atualizadas

---

## 🚀 13. Expansões Futuras

1. **Machine Learning**: Detecção de anomalias com modelos preditivos
2. **Integração com Grafana**: Exportar dados para Grafana nativo
3. **Kubernetes**: Orquestração em produção
4. **Multi-tenancy**: Suportar múltiplas redes Padtec
5. **API GraphQL**: Alternativa ao REST para queries flexíveis
6. **Mobile App**: Aplicativo mobile para alertas
7. **Integração com ServiceNow**: Criação automática de tickets
8. **Análise Preditiva**: Previsão de falhas baseada em histórico

---

## 📝 14. Conclusão

Esta arquitetura fornece uma base sólida e escalável para monitoramento contínuo de redes ópticas Padtec. A separação em microsserviços, o uso de banco de dados time-series e a implementação de alertas em tempo real garantem:

- ✅ **Visibilidade Completa**: Monitoramento em tempo real de toda a rede
- ✅ **Detecção Proativa**: Alertas automáticos antes de falhas críticas
- ✅ **Escalabilidade**: Arquitetura preparada para crescimento
- ✅ **Manutenibilidade**: Código modular e bem estruturado
- ✅ **Confiabilidade**: Retry logic, circuit breakers e redundância

O sistema está pronto para implementação seguindo os padrões e melhores práticas documentados.

---

## 📚 Documentos Relacionados

1. **Proposta Técnica de Arquitetura** - Detalhes completos da arquitetura
2. **Análise Completa da API Padtec NMS** - Documentação da API externa
3. **Especificação do Dashboard Estilo Grafana** - Design dos dashboards
4. **Fluxo Operacional de Coleta de Dados e Regras de Alerta** - Fluxos detalhados
5. **Análise Preliminar da API Padtec** - Análise inicial da API




