#!/bin/bash

# Script para iniciar o sistema de monitoramento Padtec

echo "=========================================="
echo "  Padtec Monitoring System - Deploy"
echo "=========================================="
echo ""

# Verificar se Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker não está instalado!"
    echo "   Por favor, instale o Docker Desktop: https://www.docker.com/products/docker-desktop"
    exit 1
fi

# Verificar se Docker está rodando
if ! docker info &> /dev/null; then
    echo "⚠️  Docker daemon não está rodando!"
    echo ""
    echo "   Por favor, inicie o Docker Desktop e aguarde alguns segundos."
    echo "   Depois execute este script novamente."
    echo ""
    read -p "Pressione ENTER após iniciar o Docker Desktop..."
    
    # Verificar novamente
    if ! docker info &> /dev/null; then
        echo "❌ Docker ainda não está rodando. Por favor, inicie o Docker Desktop primeiro."
        exit 1
    fi
fi

echo "✅ Docker está rodando"
echo ""

# Verificar se docker-compose está disponível
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose não está instalado!"
    exit 1
fi

# Usar docker compose (v2) se disponível, senão docker-compose (v1)
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

echo "✅ Docker Compose disponível"
echo ""

# Parar containers existentes
echo "🛑 Parando containers existentes..."
$COMPOSE_CMD down 2>/dev/null || true
echo ""

# Construir imagens
echo "🔨 Construindo imagens Docker..."
$COMPOSE_CMD build --no-cache
if [ $? -ne 0 ]; then
    echo "❌ Erro ao construir imagens"
    exit 1
fi
echo ""

# Iniciar serviços
echo "🚀 Iniciando serviços..."
$COMPOSE_CMD up -d
if [ $? -ne 0 ]; then
    echo "❌ Erro ao iniciar serviços"
    exit 1
fi
echo ""

# Aguardar serviços iniciarem
echo "⏳ Aguardando serviços iniciarem (30 segundos)..."
sleep 30
echo ""

# Verificar status
echo "📊 Status dos containers:"
$COMPOSE_CMD ps
echo ""

# Verificar logs de erro
echo "🔍 Verificando erros nos logs..."
ERRORS=$(docker-compose logs 2>&1 | grep -i "error\|failed\|exception" | head -10)
if [ ! -z "$ERRORS" ]; then
    echo "⚠️  Foram encontrados alguns erros:"
    echo "$ERRORS"
    echo ""
    echo "Para ver logs completos, execute: docker-compose logs"
else
    echo "✅ Nenhum erro crítico encontrado"
fi
echo ""

# Mostrar URLs
echo "=========================================="
echo "  ✅ Deploy concluído!"
echo "=========================================="
echo ""
echo "🌐 Acesse os serviços:"
echo "   • Frontend:     http://localhost:3000"
echo "   • Backend API:  http://localhost:8000"
echo "   • API Docs:     http://localhost:8000/docs"
echo "   • RabbitMQ:     http://localhost:15672 (guest/guest)"
echo ""
echo "📝 Comandos úteis:"
echo "   • Ver logs:     docker-compose logs -f"
echo "   • Parar:        docker-compose down"
echo "   • Status:       docker-compose ps"
echo ""




