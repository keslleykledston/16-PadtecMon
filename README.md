# Sistema de Monitoramento Padtec

Sistema completo de monitoramento da rede óptica Padtec que coleta dados continuamente, armazena histórico, gera alertas automáticos e exibe dashboards em tempo real estilo Grafana.

---

## 📚 Documentação

### Documentos Principais

1. **[Análise Consolidada da Arquitetura](./ANALISE_ARQUITETURA_CONSOLIDADA.md)**
   - Visão completa e detalhada da arquitetura do sistema
   - Todos os componentes, tecnologias e fluxos
   - **Recomendado para: Arquitetos, Desenvolvedores Sênior**

2. **[Resumo Executivo da Arquitetura](./RESUMO_EXECUTIVO_ARQUITETURA.md)**
   - Visão de alto nível e resumida
   - Diagramas simplificados
   - **Recomendado para: Gestores, Stakeholders**

3. **[Guia de Referência Técnica](./GUIA_REFERENCIA_TECNICA.md)**
   - Referência rápida de endpoints, queries, comandos
   - Informações técnicas para consulta diária
   - **Recomendado para: Desenvolvedores, DevOps**

### Documentos de Especificação (API Manual and Test Data Instructions)

4. **[Proposta Técnica de Arquitetura](./API%20Manual%20and%20Test%20Data%20Instructions/Proposta%20Técnica%20de%20Arquitetura%20-%20Sistema%20de%20Monitoramento%20Padtec.md)**
   - Especificação técnica completa original
   - Detalhes de implementação

5. **[Análise Completa da API Padtec NMS](./API%20Manual%20and%20Test%20Data%20Instructions/Análise%20Completa%20da%20API%20Padtec%20NMS.md)**
   - Documentação completa da API externa Padtec
   - Entidades, endpoints, padrões de autenticação

6. **[Especificação do Dashboard Estilo Grafana](./API%20Manual%20and%20Test%20Data%20Instructions/Especificação%20do%20Dashboard%20Estilo%20Grafana.md)**
   - Design e especificação dos dashboards
   - Painéis, cores, organização visual

7. **[Fluxo Operacional de Coleta de Dados e Regras de Alerta](./API%20Manual%20and%20Test%20Data%20Instructions/Fluxo%20Operacional%20de%20Coleta%20de%20Dados%20e%20Regras%20de%20Alerta.md)**
   - Fluxos detalhados de coleta
   - Regras de alerta e configuração

8. **[Análise Preliminar da API Padtec](./API%20Manual%20and%20Test%20Data%20Instructions/padtec_api_preliminary_analysis.md)**
   - Análise inicial da API
   - Estrutura de dados inferida

---

## 🏗️ Arquitetura em Resumo

### Componentes Principais

```
┌──────────────┐         ┌──────────────┐
│  Padtec API  │         │   Frontend   │
│  (Upstream)  │         │   (React)    │
└──────┬───────┘         └──────┬───────┘
       │                        │
       ▼                        │
┌──────────────┐                │
│   Collector  │                │
│   Service    │                │
└──────┬───────┘                │
       │                        │
       ▼                        │
┌──────────────┐                │
│ TimescaleDB  │                │
└──────┬───────┘                │
       │                        │
       ▼                        │
┌──────────────┐                │
│    Alert     │                │
│   Manager    │                │
└──────┬───────┘                │
       │                        │
       ▼                        │
┌──────────────┐                │
│   RabbitMQ   │                │
└──────┬───────┘                │
       │                        │
       ▼                        │
┌──────────────┐                │
│   Notifier   │                │
│   Service    │                │
└──────────────┘                │
                                │
                                ▼
                        ┌──────────────┐
                        │   Backend    │
                        │     API      │
                        └──────────────┘
```

### Stack Tecnológico

| Componente | Tecnologia |
|------------|------------|
| **Frontend** | React 18 + TypeScript + TailwindCSS |
| **Backend** | Python 3.11 + FastAPI |
| **Database** | TimescaleDB (PostgreSQL) |
| **Message Queue** | RabbitMQ |
| **Scheduler** | APScheduler |
| **Gráficos** | Chart.js / Recharts |
| **Containerização** | Docker Compose |

---

## 🚀 Início Rápido

### Pré-requisitos
- Docker e Docker Compose instalados
- Acesso à API Padtec NMS
- Token de autenticação da API Padtec

### Configuração

1. **Clone o repositório** (quando disponível)
2. **Configure variáveis de ambiente**
   ```bash
   cp .env.example .env
   # Edite .env com suas configurações
   ```

3. **Inicie os serviços**
   ```bash
   docker-compose up -d
   ```

4. **Acesse os serviços**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - RabbitMQ Management: http://localhost:15672

---

## 📊 Funcionalidades Principais

### ✅ Coleta Automática de Dados
- Descoberta automática de cartões
- Coleta periódica de medições (30s - 5min)
- Armazenamento em banco time-series

### ✅ Alertas Inteligentes
- Regras configuráveis por threshold
- Detecção de degradação gradual
- Histerese para evitar flapping
- Notificações por múltiplos canais

### ✅ Dashboards em Tempo Real
- Dashboard geral por site
- Dashboard detalhado por card
- Gráficos de tendência
- Timeline de alarmes

### ✅ Gestão de Alarmes
- Listagem de alarmes ativos
- Reconhecimento de alarmes
- Histórico completo
- Filtros por severidade, site, card

---

## 🔑 Informações de Acesso

### API Padtec NMS
```
URL: http://108.165.140.144:8181/nms-api/
Token: eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJubXNwbHVzIiwiaWF0IjoxNzYzMDY3MDMyfQ.IKgvplggs3bhE2Zw7UsnweIbj_h1xSJM5CpsvcUU5uo
```

### Endpoints Principais
- `GET /cards` - Listar cartões
- `GET /measurements` - Listar medições
- `GET /alarms` - Listar alarmes

---

## 🚨 Regras de Alerta

| Regra | Severidade | Threshold |
|-------|------------|-----------|
| Pump Power fora do range | CRITICAL | < 12 dBm ou > 24 dBm |
| Perda de potência óptica | MAJOR | Input Power < -20 dBm |
| Degradação de potência | MAJOR | Perda > 3 dBm em 1h |
| OSNR abaixo do limite | CRITICAL | OSNR < 15 dB |
| Card Down | CRITICAL | status != "UP" |
| Telemetria atrasada | MINOR | lastUpdated > 5min |
| Temperatura elevada | MAJOR | Temperature > 60°C |

---

## 📈 Frequências de Coleta

| Tipo de Dado | Frequência |
|--------------|------------|
| Medições Críticas (Pump Power, OSNR) | 30-60 segundos |
| Medições Normais | 5 minutos |
| Inventário de Cartões | 1 hora |
| Histórico de Alarmes | 1 minuto |

---

## 🗄️ Estrutura do Banco de Dados

### Tabelas Principais
- `measurements` - Medições time-series
- `cards` - Inventário de cartões
- `alarms` - Eventos de alarme
- `alert_rules` - Regras de alerta configuráveis

---

## 🛠️ Desenvolvimento

### Estrutura de Projeto (Proposta)
```
16-PadtecMon/
├── services/
│   ├── collector/          # Serviço de coleta
│   ├── alert_manager/       # Gerenciador de alertas
│   ├── backend/             # API interna
│   ├── frontend/            # Dashboard web
│   └── notifier/            # Serviço de notificações
├── docker-compose.yml       # Orquestração de containers
├── .env.example             # Exemplo de variáveis de ambiente
└── docs/                    # Documentação
```

### Testes
```bash
# Testes unitários
pytest tests/

# Testes de integração
pytest tests/integration/
```

---

## 📝 Checklist de Implementação

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

## 🔐 Segurança

- ✅ Autenticação JWT para API interna
- ✅ Bearer Token para API Padtec
- ✅ HTTPS/TLS em produção
- ✅ Variáveis de ambiente para secrets
- ✅ Rate limiting
- ✅ Validação de entrada
- ✅ Auditoria de acesso

---

## 📚 Referências

- [TimescaleDB Documentation](https://docs.timescale.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [RabbitMQ Documentation](https://www.rabbitmq.com/documentation.html)

---

## 🤝 Contribuindo

1. Crie uma branch para sua feature (`git checkout -b feature/nova-feature`)
2. Commit suas mudanças (`git commit -m 'Adiciona nova feature'`)
3. Push para a branch (`git push origin feature/nova-feature`)
4. Abra um Pull Request

---

## 📄 Licença

[Especificar licença quando aplicável]

---

## 📞 Contato

[Informações de contato quando aplicável]

---

## 🎯 Status do Projeto

**Fase Atual**: Documentação e Arquitetura ✅

**Próximos Passos**:
1. Revisar arquitetura com equipe técnica
2. Configurar ambiente de desenvolvimento
3. Iniciar implementação da Fase 1

---

**Última atualização**: Janeiro 2024




