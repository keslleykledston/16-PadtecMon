# Instruções para Iniciar o Docker e Deploy

## Problema: Docker Daemon não está rodando

Se você está vendo a mensagem:
```
Cannot connect to the Docker daemon at unix:///Users/keslleykssantos/.docker/run/docker.sock. 
Is the docker daemon running?
```

## Solução

### 1. Iniciar Docker Desktop

**No macOS:**
1. Abra o **Docker Desktop** (procure no Launchpad ou Applications)
2. Aguarde até ver o ícone da baleia na barra de menu superior (canto direito)
3. Quando o ícone estiver estável (não animado), o Docker está pronto

**Verificar se está rodando:**
```bash
docker info
```
Se retornar informações do Docker, está funcionando! ✅

### 2. Executar o Deploy

**Opção A: Usar o script automatizado (Recomendado)**
```bash
./start.sh
```

**Opção B: Executar manualmente**
```bash
# 1. Construir as imagens
docker-compose build

# 2. Iniciar os serviços
docker-compose up -d

# 3. Verificar status
docker-compose ps

# 4. Ver logs
docker-compose logs -f
```

## Verificação Rápida

Após iniciar o Docker Desktop, execute:

```bash
# Verificar Docker
docker --version
docker info

# Se funcionar, executar deploy
docker-compose build
docker-compose up -d
```

## Troubleshooting

### Docker Desktop não inicia
- Verifique se há atualizações pendentes
- Reinicie o Mac se necessário
- Verifique se há outros processos usando Docker

### Porta já em uso
Se a porta 8000 estiver em uso:
```bash
# Ver o que está usando a porta
lsof -i :8000

# Parar o processo (substitua PID pelo número do processo)
kill -9 <PID>
```

### Limpar e recomeçar
```bash
# Parar e remover tudo
docker-compose down -v

# Reconstruir do zero
docker-compose build --no-cache
docker-compose up -d
```

## Status Esperado

Após o deploy bem-sucedido, você deve ver:

```
NAME                   STATUS
padtec_timescaledb     Up (healthy)
padtec_rabbitmq        Up (healthy)
padtec_backend         Up
padtec_collector       Up
padtec_alert_manager   Up
padtec_notifier        Up
padtec_frontend        Up
```

## Acessar os Serviços

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **RabbitMQ Management**: http://localhost:15672




