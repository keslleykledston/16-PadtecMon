# Guia de Referência Técnica - Sistema de Monitoramento Padtec

## 🔑 Informações de Acesso

### API Padtec NMS
```
URL Base: http://108.165.140.144:8181/nms-api/
Token: eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJubXNwbHVzIiwiaWF0IjoxNzYzMDY3MDMyfQ.IKgvplggs3bhE2Zw7UsnweIbj_h1xSJM5CpsvcUU5uo
Autenticação: Bearer Token
```

### Headers de Requisição
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJubXNwbHVzIiwiaWF0IjoxNzYzMDY3MDMyfQ.IKgvplggs3bhE2Zw7UsnweIbj_h1xSJM5CpsvcUU5uo
Content-Type: application/json
```

---

## 📡 Endpoints da API Padtec (Inferidos)

### Inventário de Cartões
```http
GET /nms-api/cards
GET /nms-api/cards/{cardSerial}
```

### Medições
```http
GET /nms-api/measurements
GET /nms-api/measurements?cardSerial={id}
GET /nms-api/measurements?cardSerial={id}&limit=100&offset=0
GET /nms-api/measurements/{cardSerial}/{measureKey}
```

### Alarmes
```http
GET /nms-api/alarms
GET /nms-api/alarms?status=ACTIVE
GET /nms-api/alarms?severity=CRITICAL
GET /nms-api/alarms?cardSerial={id}
```

---

## 🗄️ Estrutura de Dados

### Card (Cartão)
```json
{
  "cardPart": "OADM-40CH-2.5G",
  "cardSerial": "SN-2024-001234",
  "cardFamily": "OADM",
  "cardModel": "OADM-40CH-2.5G-v2",
  "locationSite": "SP-01",
  "slotNumber": 1,
  "status": "UP",
  "installedAt": 1700000000,
  "lastUpdated": 1763067032
}
```

### Measurement (Medição)
```json
{
  "measureName": "Pump Power",
  "measureValue": 15.5,
  "measureUnit": "dBm",
  "measureGroup": "POWER",
  "measureKey": "PUMP_POWER_A",
  "cardPart": "OADM-40CH-2.5G",
  "cardSerial": "SN-2024-001234",
  "locationSite": "SP-01",
  "timestamp": 1763067032,
  "updatedAt": 1763067032,
  "quality": "GOOD"
}
```

### Alarm (Alarme)
```json
{
  "alarmId": "ALARM-2024-001",
  "alarmType": "THRESHOLD_EXCEEDED",
  "severity": "CRITICAL",
  "cardPart": "OADM-40CH-2.5G",
  "cardSerial": "SN-2024-001234",
  "locationSite": "SP-01",
  "description": "Pump Power abaixo do limite mínimo",
  "triggeredAt": 1763067032,
  "clearedAt": null,
  "status": "ACTIVE"
}
```

---

## 🗃️ Schema do Banco de Dados

### Tabela: measurements
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

### Tabela: cards
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

### Tabela: alarms
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

### Tabela: alert_rules
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

---

## 🔌 Endpoints da API Interna (Backend)

### Sites
```http
GET /api/sites
GET /api/sites?status=UP
```

### Cartões
```http
GET /api/cards
GET /api/cards?site_id=SP-01
GET /api/cards?family=OADM
GET /api/cards/{cardSerial}
```

### Medições
```http
GET /api/measurements/latest
GET /api/measurements/latest?limit=100&offset=0
GET /api/measurements/history?serial={id}&key={key}
GET /api/measurements/history?serial={id}&start_time={ts}&end_time={ts}&interval=1h
GET /api/cards/{cardSerial}/measurements
```

### Alarmes
```http
GET /api/alarms
GET /api/alarms?status=ACTIVE
GET /api/alarms?severity=CRITICAL
GET /api/alarms?cardSerial={id}
POST /api/alarms/{id}/acknowledge
POST /api/alarms/{id}/clear
```

### Regras de Alerta
```http
GET /api/rules
POST /api/rules
PUT /api/rules/{id}
DELETE /api/rules/{id}
```

### Collector
```http
POST /collector/start
GET /collector/status
GET /collector/logs
```

### Alert Manager
```http
GET /alerts/active
POST /alerts/rules
POST /alerts/{id}/acknowledge
POST /alerts/{id}/clear
```

---

## 📨 RabbitMQ - Filas e Tópicos

### Filas
- `measurements.collected` - Novas medições coletadas
- `alarms.triggered` - Alarmes disparados
- `alarms.cleared` - Alarmes limpos
- `notifications.pending` - Notificações a enviar

### Exemplo de Mensagem
```json
{
  "event_type": "measurement_collected",
  "timestamp": 1763067032,
  "data": {
    "card_serial": "SN-2024-001234",
    "measure_key": "PUMP_POWER_A",
    "measure_value": 15.5,
    "measure_unit": "dBm",
    "location_site": "SP-01"
  }
}
```

---

## ⏰ Frequências de Coleta

| Tipo de Dado | Frequência | Justificativa |
|--------------|------------|---------------|
| Medições Críticas (Pump Power, OSNR) | 30-60 segundos | Detectar degradação rápida |
| Medições Normais | 5 minutos | Monitoramento contínuo |
| Inventário de Cartões | 1 hora | Detectar mudanças de hardware |
| Histórico de Alarmes | 1 minuto | Capturar eventos rapidamente |
| Agregação Horária | 1 hora | Otimizar armazenamento |
| Agregação Diária | 1 dia | Análise de tendências |
| Limpeza de Dados | 1 dia | Manter banco otimizado |

---

## 🚨 Regras de Alerta - Configuração

### Exemplo de Regra (JSON)
```json
{
  "rule_name": "Pump Power Fora do Range",
  "measure_key": "PUMP_POWER_A",
  "condition": "RANGE",
  "threshold_min": 12.0,
  "threshold_max": 24.0,
  "severity": "CRITICAL",
  "enabled": true,
  "hysteresis": 0.5
}
```

### Condições Disponíveis
- `ABOVE` - Valor acima do threshold
- `BELOW` - Valor abaixo do threshold
- `RANGE` - Valor fora do range (min, max)
- `DEGRADATION` - Degradação ao longo do tempo

### Severidades
- `MINOR` - Baixa severidade
- `MAJOR` - Média severidade
- `CRITICAL` - Alta severidade

---

## 🐳 Docker Compose - Estrutura

### Serviços Principais
```yaml
services:
  timescaledb:
    image: timescale/timescaledb:latest-pg15
    ports:
      - "5432:5432"
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
  
  rabbitmq:
    image: rabbitmq:3.12-management
    ports:
      - "5672:5672"
      - "15672:15672"
  
  collector:
    build: ./services/collector
    environment:
      PADTEC_API_URL: http://108.165.140.144:8181/nms-api/
      PADTEC_API_TOKEN: ${PADTEC_API_TOKEN}
      DATABASE_URL: postgresql://user:password@timescaledb:5432/padtec
      RABBITMQ_URL: amqp://guest:guest@rabbitmq:5672/
  
  alert_manager:
    build: ./services/alert_manager
    environment:
      DATABASE_URL: postgresql://user:password@timescaledb:5432/padtec
      RABBITMQ_URL: amqp://guest:guest@rabbitmq:5672/
  
  backend:
    build: ./services/backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://user:password@timescaledb:5432/padtec
  
  frontend:
    build: ./services/frontend
    ports:
      - "3000:3000"
    environment:
      REACT_APP_API_URL: http://localhost:8000/api
  
  notifier:
    build: ./services/notifier
    environment:
      RABBITMQ_URL: amqp://guest:guest@rabbitmq:5672/
      SMTP_SERVER: ${SMTP_SERVER}
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
```

---

## 🔍 Queries SQL Úteis

### Últimas Medições de um Card
```sql
SELECT * FROM measurements
WHERE card_serial = 'SN-2024-001234'
ORDER BY time DESC
LIMIT 100;
```

### Média de Pump Power nas Últimas 24h
```sql
SELECT 
    time_bucket('1 hour', time) AS hour,
    AVG(measure_value) AS avg_pump_power
FROM measurements
WHERE card_serial = 'SN-2024-001234'
  AND measure_key = 'PUMP_POWER_A'
  AND time > NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour DESC;
```

### Alarmes Ativos por Site
```sql
SELECT 
    location_site,
    severity,
    COUNT(*) AS count
FROM alarms
WHERE status = 'ACTIVE'
GROUP BY location_site, severity
ORDER BY location_site, severity;
```

### Detecção de Degradação
```sql
WITH current_avg AS (
    SELECT AVG(measure_value) AS avg_value
    FROM measurements
    WHERE card_serial = 'SN-2024-001234'
      AND measure_key = 'INPUT_POWER'
      AND time > NOW() - INTERVAL '1 hour'
),
previous_avg AS (
    SELECT AVG(measure_value) AS avg_value
    FROM measurements
    WHERE card_serial = 'SN-2024-001234'
      AND measure_key = 'INPUT_POWER'
      AND time BETWEEN NOW() - INTERVAL '2 hours' AND NOW() - INTERVAL '1 hour'
)
SELECT 
    (current_avg.avg_value - previous_avg.avg_value) AS degradation_dbm
FROM current_avg, previous_avg
WHERE (current_avg.avg_value - previous_avg.avg_value) < -3.0;
```

---

## 🎨 Cores do Dashboard

| Cor | Hex | Uso |
|-----|-----|-----|
| Verde | `#4CAF50` | Normal / UP |
| Amarelo | `#FFC107` | Aviso / MINOR |
| Laranja | `#FF9800` | Atenção / MAJOR |
| Vermelho | `#F44336` | Crítico / DOWN |
| Azul | `#2196F3` | Informativo |

---

## 📊 Medições Críticas

### Pump Power
- **Limite Mínimo**: 12 dBm
- **Limite Máximo**: 24 dBm
- **Histerese**: 0.5 dBm
- **Frequência**: 30-60 segundos

### OSNR (Optical Signal-to-Noise Ratio)
- **Limite Mínimo**: 15 dB
- **Histerese**: 0.2 dB
- **Frequência**: 30-60 segundos

### Input Power
- **Limite Mínimo**: -20 dBm
- **Histerese**: 1.0 dBm
- **Frequência**: 5 minutos

### Temperature
- **Limite Máximo**: 60 °C
- **Histerese**: 1.0 °C
- **Frequência**: 5 minutos

---

## 🔧 Variáveis de Ambiente

### Data Collector
```bash
PADTEC_API_URL=http://108.165.140.144:8181/nms-api/
PADTEC_API_TOKEN=eyJhbGciOiJIUzI1NiJ9...
DATABASE_URL=postgresql://user:password@timescaledb:5432/padtec
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
COLLECT_INTERVAL_CRITICAL=30
COLLECT_INTERVAL_NORMAL=300
```

### Alert Manager
```bash
DATABASE_URL=postgresql://user:password@timescaledb:5432/padtec
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
CHECK_INTERVAL=60
```

### Notification Service
```bash
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
SMTP_SERVER=smtp.example.com
SMTP_USER=user@example.com
SMTP_PASSWORD=password
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=123456789
```

### Backend API
```bash
DATABASE_URL=postgresql://user:password@timescaledb:5432/padtec
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
CORS_ORIGINS=http://localhost:3000
```

### Frontend
```bash
REACT_APP_API_URL=http://localhost:8000/api
REACT_APP_WS_URL=ws://localhost:8000/ws
```

---

## 📝 Logs e Monitoramento

### Níveis de Log
- `DEBUG` - Informações detalhadas para debug
- `INFO` - Informações gerais de operação
- `WARNING` - Avisos não críticos
- `ERROR` - Erros que não interrompem o serviço
- `CRITICAL` - Erros críticos que interrompem o serviço

### Formato de Log (JSON)
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "service": "collector",
  "message": "Coleta de medições iniciada",
  "card_serial": "SN-2024-001234",
  "measurements_count": 50
}
```

---

## 🚀 Comandos Úteis

### Iniciar Sistema
```bash
docker-compose up -d
```

### Ver Logs
```bash
docker-compose logs -f collector
docker-compose logs -f alert_manager
docker-compose logs -f backend
```

### Parar Sistema
```bash
docker-compose down
```

### Backup do Banco de Dados
```bash
docker-compose exec timescaledb pg_dump -U postgres padtec > backup.sql
```

### Restaurar Banco de Dados
```bash
docker-compose exec -T timescaledb psql -U postgres padtec < backup.sql
```

### Acessar RabbitMQ Management
```
http://localhost:15672
Usuário: guest
Senha: guest
```

### Acessar API Backend
```
http://localhost:8000
Documentação: http://localhost:8000/docs
```

### Acessar Frontend
```
http://localhost:3000
```

---

## 📚 Referências Rápidas

- **Análise Completa**: `ANALISE_ARQUITETURA_CONSOLIDADA.md`
- **Resumo Executivo**: `RESUMO_EXECUTIVO_ARQUITETURA.md`
- **Proposta Técnica**: `API Manual and Test Data Instructions/Proposta Técnica de Arquitetura - Sistema de Monitoramento Padtec.md`
- **Análise da API**: `API Manual and Test Data Instructions/Análise Completa da API Padtec NMS.md`
- **Dashboard**: `API Manual and Test Data Instructions/Especificação do Dashboard Estilo Grafana.md`
- **Fluxo Operacional**: `API Manual and Test Data Instructions/Fluxo Operacional de Coleta de Dados e Regras de Alerta.md`




