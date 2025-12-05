# Instruções de Instalação e Uso

## Pré-requisitos

- Docker e Docker Compose instalados
- Acesso à API Padtec NMS
- Token de autenticação da API Padtec

## Configuração Inicial

1. **Clone ou navegue até o diretório do projeto**
   ```bash
   cd 16-PadtecMon
   ```

2. **Crie o arquivo `.env` baseado no `.env.example`**
   ```bash
   cp .env.example .env
   ```

3. **Edite o arquivo `.env` com suas configurações**
   - Configure o token da API Padtec: `PADTEC_API_TOKEN`
   - Configure as credenciais do banco de dados: `DB_PASSWORD`
   - Configure as credenciais do RabbitMQ: `RABBITMQ_USER`, `RABBITMQ_PASSWORD`
   - Configure notificações (opcional): `SMTP_*`, `TELEGRAM_*`

## Executando a Aplicação

### Iniciar todos os serviços
```bash
docker-compose up -d
```

### Ver logs
```bash
# Todos os serviços
docker-compose logs -f

# Serviço específico
docker-compose logs -f collector
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Parar os serviços
```bash
docker-compose down
```

### Parar e remover volumes (limpar dados)
```bash
docker-compose down -v
```

## Acessando os Serviços

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation (Swagger)**: http://localhost:8000/docs
- **RabbitMQ Management**: http://localhost:15672
  - Usuário: `guest` (ou o configurado)
  - Senha: `guest` (ou a configurada)

## Estrutura dos Serviços

### Data Collector (Porta 8001)
- Coleta dados da API Padtec
- Endpoints:
  - `GET /health` - Health check
  - `GET /status` - Status da coleta
  - `POST /collector/start` - Iniciar coleta manual

### Alert Manager (Porta 8002)
- Processa regras de alerta
- Endpoints:
  - `GET /health` - Health check
  - `GET /alerts/active` - Listar alertas ativos
  - `POST /alerts/{id}/acknowledge` - Reconhecer alerta
  - `POST /alerts/{id}/clear` - Limpar alerta

### Backend API (Porta 8000)
- API REST para o frontend
- Endpoints principais:
  - `GET /api/sites` - Listar sites
  - `GET /api/cards` - Listar cartões
  - `GET /api/cards/{serial}` - Detalhes do cartão
  - `GET /api/measurements/latest` - Últimas medições
  - `GET /api/measurements/history` - Histórico de medições
  - `GET /api/alarms` - Listar alarmes
  - `POST /api/alarms/{id}/acknowledge` - Reconhecer alarme
  - `POST /api/alarms/{id}/clear` - Limpar alarme

### Notification Service (Porta 8003)
- Envia notificações
- Endpoints:
  - `GET /health` - Health check
  - `POST /test/email` - Testar email
  - `POST /test/telegram` - Testar Telegram

### Frontend (Porta 3000)
- Interface web
- Páginas:
  - `/` - Dashboard geral
  - `/sites` - Lista de sites
  - `/cards` - Lista de cartões
  - `/cards/:serial` - Detalhes do cartão
  - `/alarms` - Lista de alarmes

## Verificando o Status

### Verificar se todos os serviços estão rodando
```bash
docker-compose ps
```

### Verificar logs de erro
```bash
docker-compose logs | grep -i error
```

### Verificar conexão com o banco de dados
```bash
docker-compose exec timescaledb psql -U padtec_user -d padtec -c "SELECT COUNT(*) FROM cards;"
```

## Troubleshooting

### Serviço não inicia
1. Verifique os logs: `docker-compose logs <serviço>`
2. Verifique as variáveis de ambiente no `.env`
3. Verifique se as portas estão disponíveis

### Erro de conexão com a API Padtec
1. Verifique se o token está correto no `.env`
2. Verifique se a URL da API está acessível
3. Verifique os logs do collector: `docker-compose logs collector`

### Erro de conexão com o banco de dados
1. Verifique se o TimescaleDB está rodando: `docker-compose ps timescaledb`
2. Verifique a senha do banco no `.env`
3. Verifique os logs: `docker-compose logs timescaledb`

### Frontend não carrega dados
1. Verifique se o backend está rodando: `docker-compose ps backend`
2. Verifique a URL da API no frontend (variável `REACT_APP_API_URL` ou `VITE_API_URL`)
3. Verifique os logs do backend: `docker-compose logs backend`

## Desenvolvimento

### Rebuild dos containers após mudanças
```bash
docker-compose build
docker-compose up -d
```

### Executar comandos dentro de um container
```bash
docker-compose exec <serviço> <comando>
# Exemplo:
docker-compose exec backend python -m pytest
```

### Acessar shell do container
```bash
docker-compose exec <serviço> /bin/bash
```

## Backup e Restore

### Backup do banco de dados
```bash
docker-compose exec timescaledb pg_dump -U padtec_user padtec > backup.sql
```

### Restore do banco de dados
```bash
docker-compose exec -T timescaledb psql -U padtec_user padtec < backup.sql
```

## Próximos Passos

1. Configure as notificações (Email, Telegram) no `.env`
2. Ajuste as regras de alerta no banco de dados se necessário
3. Configure monitoramento adicional (Prometheus, Grafana) se desejado
4. Configure HTTPS em produção
5. Configure backup automático do banco de dados




