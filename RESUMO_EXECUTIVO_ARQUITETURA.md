# Resumo Executivo - Arquitetura do Sistema de Monitoramento Padtec

## 🎯 Objetivo

Construir um sistema completo de monitoramento da rede óptica Padtec que colete dados continuamente, armazene histórico, gere alertas automáticos e exiba dashboards em tempo real estilo Grafana.

---

## 📐 Arquitetura em Camadas

```
┌─────────────────────────────────────────────────────────────┐
│                    CAMADA DE APRESENTAÇÃO                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Frontend (React + TypeScript)                       │  │
│  │  - Dashboard Geral                                   │  │
│  │  - Dashboard por Card                                │  │
│  │  - Gráficos em Tempo Real                            │  │
│  │  - Gestão de Alarmes                                 │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↕ HTTP/REST + WebSocket
┌─────────────────────────────────────────────────────────────┐
│                    CAMADA DE APLICAÇÃO                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Backend    │  │   Collector  │  │    Alert     │     │
│  │     API      │  │   Service    │  │   Manager    │     │
│  │  (FastAPI)   │  │  (FastAPI)   │  │  (FastAPI)   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Notification Service                         │  │
│  │  (Email, Telegram, SMS, Webhook)                    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↕ AMQP
┌─────────────────────────────────────────────────────────────┐
│                    CAMADA DE MENSAGENS                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              RabbitMQ                                │  │
│  │  - measurements.collected                            │  │
│  │  - alarms.triggered                                 │  │
│  │  - alarms.cleared                                   │  │
│  │  - notifications.pending                            │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↕ SQL
┌─────────────────────────────────────────────────────────────┐
│                    CAMADA DE DADOS                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              TimescaleDB                             │  │
│  │  - measurements (time-series)                         │  │
│  │  - cards (inventário)                                │  │
│  │  - alarms (eventos)                                  │  │
│  │  - alert_rules (configuração)                        │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↕ HTTP/REST
┌─────────────────────────────────────────────────────────────┐
│                    CAMADA EXTERNA                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Padtec NMS API                                │  │
│  │  http://108.165.140.144:8181/nms-api/                │  │
│  │  - GET /cards                                         │  │
│  │  - GET /measurements                                  │  │
│  │  - GET /alarms                                        │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Fluxo de Dados Simplificado

```
API Padtec → Collector → TimescaleDB → Alert Manager → RabbitMQ → Notifier
                                                              ↓
                                                         Frontend ← Backend API
```

### Detalhamento do Fluxo:

1. **Coleta (Collector)**
   - Autentica na API Padtec
   - Descobre cartões automaticamente
   - Coleta medições periodicamente
   - Armazena no TimescaleDB

2. **Processamento (Alert Manager)**
   - Monitora medições em tempo real
   - Aplica regras de alerta
   - Detecta degradação gradual
   - Publica eventos no RabbitMQ

3. **Notificação (Notifier)**
   - Consome eventos de alarme
   - Envia por múltiplos canais
   - Implementa rate limiting

4. **Visualização (Frontend)**
   - Consulta Backend API
   - Exibe dashboards em tempo real
   - Mostra gráficos e tendências

---

## 🏗️ Estrutura de Microsserviços

### 1. Data Collector Service
- **Responsabilidade**: Coletar dados da API Padtec
- **Tecnologia**: Python + FastAPI + APScheduler
- **Frequência**: 30s-5min (depende da criticidade)
- **Saída**: TimescaleDB + RabbitMQ

### 2. Alert Manager Service
- **Responsabilidade**: Processar regras de alerta
- **Tecnologia**: Python + FastAPI + APScheduler
- **Frequência**: Tempo real (após cada coleta)
- **Saída**: RabbitMQ (eventos de alarme)

### 3. Backend API Service
- **Responsabilidade**: Expor dados para frontend
- **Tecnologia**: Python + FastAPI
- **Frequência**: Sob demanda (requisições HTTP)
- **Saída**: JSON para frontend

### 4. Notification Service
- **Responsabilidade**: Enviar notificações
- **Tecnologia**: Python + FastAPI
- **Frequência**: Assíncrono (via RabbitMQ)
- **Canais**: Email, Telegram, SMS, Webhook

### 5. Frontend Service
- **Responsabilidade**: Interface web
- **Tecnologia**: React + TypeScript
- **Frequência**: Tempo real (WebSocket)
- **Visualização**: Dashboards estilo Grafana

---

## 📊 Modelo de Dados

### Entidades Principais

```
┌─────────────┐
│    Card     │
│─────────────│
│ cardSerial  │──┐
│ cardPart    │  │
│ locationSite│  │
│ status      │  │
└─────────────┘  │
                 │
                 │ 1:N
                 │
┌─────────────┐  │
│ Measurement │  │
│─────────────│  │
│ time        │  │
│ cardSerial  │◄─┘
│ measureKey  │
│ measureValue│
│ measureUnit │
└─────────────┘
     │
     │ 1:N
     │
┌─────────────┐
│   Alarm     │
│─────────────│
│ alarmId     │
│ cardSerial  │
│ severity    │
│ triggeredAt │
│ status      │
└─────────────┘
```

---

## 🚨 Regras de Alerta - Resumo

| Regra | Severidade | Frequência | Histerese |
|-------|------------|------------|-----------|
| Pump Power fora do range | CRITICAL | 30s | 0.5 dBm |
| Perda de potência óptica | MAJOR | 30s | 1.0 dBm |
| Degradação de potência | MAJOR | 1h | N/A |
| OSNR abaixo do limite | CRITICAL | 30s | 0.2 dB |
| Card Down | CRITICAL | 1min | N/A |
| Telemetria atrasada | MINOR | 5min | N/A |
| Temperatura elevada | MAJOR | 5min | 1.0 °C |

---

## 🎨 Dashboard - Visão Geral

### Dashboard Geral
- Status da rede (% de cards UP)
- Alarmes ativos por severidade
- Mapa de sites
- Últimas medições críticas
- Timeline de alarmes (24h)
- Inventário de placas

### Dashboard por Card
- Status do card
- Pump Power (tendência)
- OSNR (tendência)
- In/Out Power (comparação)
- Temperatura
- Timeline de alarmes
- Tabela de medições

---

## 🛠️ Stack Tecnológico Resumido

| Camada | Tecnologia |
|--------|------------|
| **Frontend** | React 18 + TypeScript + TailwindCSS |
| **Backend** | Python 3.11 + FastAPI |
| **Database** | TimescaleDB (PostgreSQL) |
| **Message Queue** | RabbitMQ |
| **Scheduler** | APScheduler |
| **Gráficos** | Chart.js / Recharts |
| **Containerização** | Docker Compose |
| **CI/CD** | GitHub Actions / GitLab CI |

---

## 📈 Métricas de Performance Esperadas

- **Latência de Coleta**: < 5 segundos por ciclo
- **Latência de Alerta**: < 10 segundos (coleta → notificação)
- **Throughput**: Suportar 100+ sites, 2500+ cards
- **Volume de Dados**: ~180M pontos/dia (com agregação)
- **Disponibilidade**: 99.9% (com redundância)

---

## 🔐 Segurança

- ✅ Autenticação JWT para API interna
- ✅ Bearer Token para API Padtec
- ✅ HTTPS/TLS em produção
- ✅ Variáveis de ambiente para secrets
- ✅ Rate limiting
- ✅ Validação de entrada
- ✅ Auditoria de acesso

---

## 📦 Deploy

### Desenvolvimento
```bash
docker-compose up
```

### Produção
- Kubernetes (futuro)
- Load balancer (Nginx/Kong)
- Backup automático
- Monitoramento (Prometheus/Grafana)

---

## ✅ Checklist de Implementação

### Fase 1: Infraestrutura Base
- [ ] Configurar TimescaleDB
- [ ] Configurar RabbitMQ
- [ ] Criar estrutura de microsserviços
- [ ] Docker Compose básico

### Fase 2: Coleta de Dados
- [ ] Implementar Data Collector
- [ ] Integração com API Padtec
- [ ] Armazenamento no TimescaleDB
- [ ] Scheduler de tarefas

### Fase 3: Alertas
- [ ] Implementar Alert Manager
- [ ] Regras de alerta configuráveis
- [ ] Histerese e detecção de degradação
- [ ] Notification Service

### Fase 4: Backend API
- [ ] Endpoints REST
- [ ] Autenticação e autorização
- [ ] Queries otimizadas
- [ ] Documentação (Swagger)

### Fase 5: Frontend
- [ ] Dashboard geral
- [ ] Dashboard por card
- [ ] Gráficos em tempo real
- [ ] Gestão de alarmes

### Fase 6: Testes e Deploy
- [ ] Testes unitários
- [ ] Testes de integração
- [ ] Deploy em ambiente de staging
- [ ] Deploy em produção

---

## 🎯 Próximos Passos

1. **Revisar arquitetura** com equipe técnica
2. **Definir ambiente de desenvolvimento**
3. **Configurar repositório Git**
4. **Iniciar implementação da Fase 1**
5. **Estabelecer CI/CD pipeline**

---

## 📚 Documentação Completa

Consulte `ANALISE_ARQUITETURA_CONSOLIDADA.md` para detalhes completos de cada componente.




