# Análise Completa da API Padtec NMS

## Resumo Executivo

A API Padtec NMS (Network Management System) é uma interface RESTful que fornece acesso aos dados de monitoramento de equipamentos ópticos DWDM (Dense Wavelength Division Multiplexing). Esta análise documenta a estrutura geral da API, as entidades principais, os padrões de autenticação, as limitações e as melhores práticas para integração em sistemas de monitoramento contínuo.

---

## 1. Estrutura Geral da API

### 1.1 Informações de Acesso

| Atributo | Valor |
| :--- | :--- |
| **URL Base** | `http://108.165.140.144:8181/nms-api/` |
| **Protocolo** | HTTP/REST |
| **Autenticação** | Bearer Token (JWT-like) |
| **Formato de Dados** | JSON |
| **Versionamento** | Não especificado (verificar documentação técnica) |

### 1.2 Padrão de Autenticação

A API utiliza autenticação baseada em **Bearer Token**, seguindo o padrão OAuth 2.0 simplificado. O token deve ser incluído em todas as requisições no cabeçalho `Authorization`:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJubXNwbHVzIiwiaWF0IjoxNzYzMDY3MDMyfQ.IKgvplggs3bhE2Zw7UsnweIbj_h1xSJM5CpsvcUU5uo
```

**Características do Token:**
*   Tipo: JWT (JSON Web Token)
*   Algoritmo: HS256 (HMAC SHA-256)
*   Subject (`sub`): "nmsplus" (usuário/aplicação)
*   Issued At (`iat`): 1763067032 (timestamp UNIX)
*   Validade: Verificar com a documentação técnica (geralmente 24h ou 7 dias)

---

## 2. Entidades Principais

A API Padtec gerencia as seguintes entidades principais, essenciais para o monitoramento de redes ópticas:

### 2.1 Cartões (Cards) / Placas

Representam os módulos de hardware instalados nos equipamentos de transmissão óptica.

| Campo | Tipo | Descrição | Exemplo |
| :--- | :--- | :--- | :--- |
| `cardPart` | String | Identificador único da placa (SKU/Part Number). | "OADM-40CH-2.5G" |
| `cardSerial` | String | Número de série único do hardware. | "SN-2024-001234" |
| `cardFamily` | String | Família de placas (agrupamento lógico). | "OADM", "ROADM", "Amplifier" |
| `cardModel` | String | Modelo específico da placa. | "OADM-40CH-2.5G-v2" |
| `locationSite` | String | Identificador do site/localização onde a placa está instalada. | "SP-01", "RJ-02" |
| `slotNumber` | Integer | Posição física da placa no chassis. | 1, 2, 3 |
| `status` | String | Estado operacional da placa. | "UP", "DOWN", "DEGRADED" |
| `installedAt` | Timestamp | Data de instalação. | 1700000000 |
| `lastUpdated` | Timestamp | Última vez que os dados foram atualizados. | 1763067032 |

### 2.2 Medições (Measurements)

Dados de telemetria coletados periodicamente dos cartões.

| Campo | Tipo | Descrição | Exemplo |
| :--- | :--- | :--- | :--- |
| `measureName` | String | Nome amigável da medição. | "Pump Power", "Input Power", "OsNR" |
| `measureValue` | Float | Valor numérico da medição. | 15.5, -20.3, 35.2 |
| `measureUnit` | String | Unidade de medida. | "dBm", "°C", "dB" |
| `measureGroup` | String | Categoria de medição. | "POWER", "OPTICAL", "TEMPERATURE" |
| `measureKey` | String | Chave única para a medição (normalizada). | "PUMP_POWER_A", "OSC_POWER_IN" |
| `cardPart` | String | Referência ao cartão que gerou a medição. | "OADM-40CH-2.5G" |
| `cardSerial` | String | Serial do cartão (para correlação). | "SN-2024-001234" |
| `locationSite` | String | Site onde a medição foi coletada. | "SP-01" |
| `timestamp` | Timestamp | Momento da coleta. | 1763067032 |
| `updatedAt` | Timestamp | Última atualização do registro. | 1763067032 |
| `quality` | String | Qualidade/confiabilidade da medição. | "GOOD", "FAIR", "POOR" |

### 2.3 Alarmes (Alarms)

Eventos de alerta gerados quando medições excedem limites ou quando há falhas de hardware.

| Campo | Tipo | Descrição | Exemplo |
| :--- | :--- | :--- | :--- |
| `alarmId` | String | Identificador único do alarme. | "ALARM-2024-001" |
| `alarmType` | String | Tipo de alarme. | "THRESHOLD_EXCEEDED", "CARD_DOWN", "LINK_LOSS" |
| `severity` | String | Nível de severidade. | "MINOR", "MAJOR", "CRITICAL" |
| `cardPart` | String | Cartão afetado. | "OADM-40CH-2.5G" |
| `cardSerial` | String | Serial do cartão. | "SN-2024-001234" |
| `locationSite` | String | Site afetado. | "SP-01" |
| `description` | String | Descrição textual do alarme. | "Pump Power abaixo do limite mínimo" |
| `triggeredAt` | Timestamp | Momento do disparo. | 1763067032 |
| `clearedAt` | Timestamp (nullable) | Momento da limpeza (se resolvido). | null ou timestamp |
| `status` | String | Estado do alarme. | "ACTIVE", "CLEARED", "ACKNOWLEDGED" |

### 2.4 Parâmetros Ópticos (Optical Parameters)

Dados especializados para análise de qualidade de sinal óptico.

| Campo | Tipo | Descrição | Exemplo |
| :--- | :--- | :--- | :--- |
| `osnr` | Float | Optical Signal-to-Noise Ratio (dB). | 18.5 |
| `chromDispersion` | Float | Dispersão cromática (ps/nm). | 45.2 |
| `polarizationMode` | Float | Polarization Mode Dispersion (ps). | 0.8 |
| `inputPower` | Float | Potência de entrada (dBm). | -15.3 |
| `outputPower` | Float | Potência de saída (dBm). | -12.5 |
| `pumpPower` | Float | Potência da bomba (dBm, para amplificadores). | 22.1 |
| `wavelength` | Float | Comprimento de onda (nm). | 1550.0 |

---

## 3. Endpoints Principais (Inferidos)

Com base na estrutura de dados, os seguintes endpoints devem estar disponíveis:

### 3.1 Inventário de Cartões

**GET `/cards`** - Listar todos os cartões instalados

```
GET /nms-api/cards
Authorization: Bearer <TOKEN>

Response:
{
  "status": "success",
  "data": [
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
  ],
  "totalCount": 25
}
```

**GET `/cards/{cardSerial}`** - Obter detalhes de um cartão específico

### 3.2 Medições

**GET `/measurements`** - Listar medições recentes

```
GET /nms-api/measurements?limit=100&offset=0&cardSerial=SN-2024-001234
Authorization: Bearer <TOKEN>

Response:
{
  "status": "success",
  "data": [
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
  ],
  "totalCount": 1500
}
```

**GET `/measurements/{cardSerial}/{measureKey}`** - Obter histórico de uma medição específica

### 3.3 Alarmes

**GET `/alarms`** - Listar alarmes ativos ou históricos

```
GET /nms-api/alarms?status=ACTIVE&severity=CRITICAL
Authorization: Bearer <TOKEN>

Response:
{
  "status": "success",
  "data": [
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
  ],
  "totalCount": 5
}
```

---

## 4. Padrões de Autenticação e Segurança

### 4.1 Autenticação

*   **Tipo**: Bearer Token (JWT)
*   **Cabeçalho**: `Authorization: Bearer <TOKEN>`
*   **Validade**: Presumivelmente 24 horas (verificar com documentação)
*   **Renovação**: Implementar mecanismo de refresh token ou re-autenticação periódica

### 4.2 Recomendações de Segurança

1.  **Armazenamento Seguro**: Nunca armazenar tokens em código-fonte. Usar variáveis de ambiente ou vaults.
2.  **HTTPS**: Sempre usar HTTPS em produção (atualmente a API está em HTTP, considerar upgrade).
3.  **Rate Limiting**: Implementar backoff exponencial para respeitar limites de taxa.
4.  **Validação**: Validar todos os dados recebidos antes de armazenar em banco de dados.
5.  **Auditoria**: Registrar todas as chamadas à API para fins de auditoria.

---

## 5. Limitações e Considerações

### 5.1 Limitações Conhecidas

1.  **Paginação**: Implementar paginação com `limit` e `offset` para grandes volumes de dados.
2.  **Filtros**: Suportar filtros por `cardSerial`, `locationSite`, `measureGroup`, `status`.
3.  **Ordenação**: Permitir ordenação por `timestamp`, `measureValue`, `severity`.
4.  **Histórico**: Manter histórico de medições por período (ex: 30 dias, 1 ano).
5.  **Latência**: Considerar latência de coleta (geralmente 30s a 5min entre atualizações).

### 5.2 Considerações de Performance

*   **Volume de Dados**: Uma rede com 100 sites, 25 cartões por site e 50 medições por cartão gera ~125.000 pontos de dados por coleta.
*   **Frequência de Coleta**: Coletar a cada 30-60 segundos resulta em ~7,5M de pontos/hora ou ~180M de pontos/dia.
*   **Armazenamento**: Um banco de dados time-series é **obrigatório** para este volume.

---

## 6. Frequência Ideal de Coleta

| Tipo de Dado | Frequência | Justificativa |
| :--- | :--- | :--- |
| **Medições Críticas** (Pump Power, OSNR) | 30-60 segundos | Detectar degradação rápida |
| **Medições Normais** (Temperatura, Potência) | 5 minutos | Monitoramento contínuo com overhead reduzido |
| **Inventário de Cartões** | 1 hora | Detectar mudanças de hardware |
| **Histórico de Alarmes** | 1 minuto | Capturar eventos rapidamente |
| **Limpeza de Dados Antigos** | 1 vez/dia | Manter banco de dados otimizado |

---

## 7. Endpoints Essenciais para Monitoramento Completo

Para compor um monitoramento abrangente, os seguintes endpoints devem ser consultados em sequência:

1.  **`GET /cards`** → Descobrir inventário de cartões
2.  **`GET /cards/{cardSerial}`** → Obter detalhes específicos
3.  **`GET /measurements?cardSerial={id}`** → Coletar medições atuais
4.  **`GET /measurements/{cardSerial}/{measureKey}?limit=1000`** → Histórico de medições
5.  **`GET /alarms?status=ACTIVE`** → Alarmes ativos
6.  **`GET /alarms?cardSerial={id}&timeRange=24h`** → Histórico de alarmes

---

## 8. Melhores Práticas

### 8.1 Coleta de Dados

1.  **Implementar Retry Logic**: Usar backoff exponencial (1s, 2s, 4s, 8s) para falhas transitórias.
2.  **Validação de Dados**: Verificar se `measureValue` está dentro de ranges esperados.
3.  **Deduplicação**: Evitar armazenar medições duplicadas (usar `timestamp` + `measureKey` como chave única).
4.  **Timezone**: Sempre usar UTC internamente, converter para timezone local apenas na exibição.

### 8.2 Armazenamento

1.  **Time-Series Database**: Usar InfluxDB, TimescaleDB ou Prometheus.
2.  **Retenção**: Manter dados brutos por 30 dias, agregados por 1 ano.
3.  **Índices**: Criar índices em `cardSerial`, `locationSite`, `timestamp`, `measureKey`.

### 8.3 Alertas

1.  **Histerese**: Implementar histerese para evitar flapping (ex: ligar em 15dBm, desligar em 16dBm).
2.  **Escalação**: Diferentes canais de notificação por severidade (email, SMS, Telegram).
3.  **Supressão**: Suprimir alertas duplicados dentro de 5 minutos.

---

## 9. Conclusão

A API Padtec NMS fornece acesso abrangente aos dados de monitoramento de redes ópticas. A implementação de um sistema de coleta contínua, armazenamento em banco de dados time-series e dashboard em tempo real permitirá visibilidade completa da saúde da rede óptica, detecção proativa de problemas e resposta rápida a incidentes.

A próxima fase envolve o design da arquitetura técnica completa da aplicação, incluindo backend, banco de dados, scheduler, frontend e containerização.
