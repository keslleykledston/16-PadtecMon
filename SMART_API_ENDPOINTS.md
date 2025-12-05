# Padtec Smart API - Endpoints Documentados

Baseado no manual: **OM.SMARTAPI.2025.06.POR.V2**

## Estrutura Base

- Swagger: `http://172.30.0.21:8181/nms-api/` (ou IP público equivalente)
- Endpoints: `<BASE>/api/v1/...` — Exemplo: `http://172.30.0.21:8181/nms-api/api/v1/inventory/state`

## Endpoints Principais

### 1. Alarm (Alarmes)
- **Capability**: `/api/v1/alarm/capability` - Lista alarmes disponíveis
- **Count**: `/api/v1/alarm/count` - Quantidade total de alarmes
- **State**: `/api/v1/alarm/state` - Estado atual dos alarmes

### 2. Inventory (Inventário)
- **Capability**: `/api/v1/inventory/capability` - Lista inventário disponível
- **Count**: `/api/v1/inventory/count` - Quantidade total de equipamentos
- **State**: `/api/v1/inventory/state` - Estado dos equipamentos

**Parâmetros para Inventory State:**
- `cardModel` - Exemplo: TNS400G-NX
- `cardPart` - Exemplo: 3780
- `locationSite` - Exemplo: NE 1
- `page` - Índice da página (padrão: 0)
- `size` - Itens por página (padrão: 10)

### 3. Measures (Medições)
- **Capability**: `/api/v1/measures/capability` - Medidas que uma placa pode gerar
- **Count**: `/api/v1/measures/count` - Quantidade de medidas coletadas
- **State**: `/api/v1/measures/state` - Medidas coletadas dos equipamentos

**Nota Importante:**
- As medidas são coletadas com intervalo de **30 segundos**
- Os dados são normalizados pela API

## Autenticação

- **Tipo**: Bearer Token (JWT)
- **Header**: `Authorization: Bearer <TOKEN>`
- **Content-Type**: `application/json`

## Swagger/OpenAPI

A API possui documentação Swagger disponível para:
- Visualizar endpoints
- Testar requisições
- Gerar tokens de autorização

## Migração de Endpoints

### Endpoints Antigos (Inferidos) → Novos (Documentados)

| Antigo | Novo |
|--------|------|
| `/nms-api/cards` | `/api/v1/inventory/state` |
| `/nms-api/measurements` | `/api/v1/measures/state` |
| `/nms-api/alarms` | `/api/v1/alarm/state` |

## Exemplo de URL Completa

```
http://108.165.140.144:8181/nms-api/api/v1/inventory/state
http://172.30.0.21:8181/nms-api/api/v1/inventory/state
```

