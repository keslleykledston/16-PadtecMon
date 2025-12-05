# Fluxo Operacional de Coleta de Dados e Regras de Alerta

## 1. Fluxo Completo de Coleta de Dados (Diagrama Textual)

O fluxo de coleta de dados é um processo contínuo e cíclico, executado pelo microsserviço **Data Collector** (Coletor de Dados).

```mermaid
graph TD
    A[Início do Ciclo (Scheduler)] --> B{Autenticação na API Padtec};
    B -- Sucesso --> C[Busca de Inventário: GET /cards];
    B -- Falha --> B;
    C --> D{Processar Lista de Cards};
    D --> E(Para Cada Card Detectado);
    E --> F[Consultar Medições: GET /measurements?cardSerial={id}];
    F --> G{Normalizar e Validar Dados};
    G --> H[Armazenar em Banco Time-Series (TimescaleDB)];
    H --> I[Publicar Evento: measurements.collected (RabbitMQ)];
    I --> J{Alert Manager Consome Evento};
    J --> K[Aplicar Regras de Alerta (Threshold, Histórico)];
    K -- Alerta Disparado --> L[Publicar Evento: alarms.triggered (RabbitMQ)];
    L --> M[Notifier Consome Evento];
    M --> N[Disparar Notificação (Telegram, Email, Webhook)];
    N --> O[Exposição em API Interna (Backend)];
    O --> P[Exibição no Dashboard (Frontend)];
    P --> Q[Fim do Ciclo];
    E --> Q;
```

### 1.1 Detalhamento das Etapas

| Etapa | Descrição | Frequência |
| :--- | :--- | :--- |
| **Autenticação** | Enviar o Bearer Token no cabeçalho `Authorization`. O token deve ser renovado periodicamente. | A cada ciclo ou conforme validade do token. |
| **Busca de Inventário** | `GET /nms-api/cards`. Essencial para descobrir novos cartões ou cartões removidos. | A cada 1 hora. |
| **Consultar Medições** | `GET /nms-api/measurements?cardSerial={id}`. Coleta os dados de telemetria (POWER, OPTICAL, TEMP). | 30 segundos a 5 minutos (depende da criticidade). |
| **Normalização** | Garantir que `measureKey`, `measureUnit` e `timestamp` estejam padronizados antes de armazenar. | Em cada coleta. |
| **Armazenamento** | Inserir dados na tabela `measurements` do TimescaleDB. | Em cada coleta. |
| **Publicação de Evento** | Enviar a medição para a fila `measurements.collected` para processamento assíncrono de alertas. | Em cada coleta. |
| **Regra de Alerta** | O Alert Manager verifica se a nova medição viola qualquer regra (limite estático ou tendência). | Em tempo real (após cada coleta). |
| **Disparo de Notificação** | O Notifier envia a notificação pelo canal configurado (Telegram, Email, etc.). | Imediatamente após o disparo do alerta. |
| **Exposição/Exibição** | O Backend API consulta o TimescaleDB para fornecer dados ao Frontend para exibição em dashboards. | Sob demanda do usuário. |

---

## 2. Regras de Alerta

As regras de alerta são o coração do sistema de monitoramento, garantindo que desvios e falhas sejam detectados e comunicados rapidamente.

### 2.1 Estrutura da Regra

| Campo | Descrição | Exemplo |
| :--- | :--- | :--- |
| **Severidade** | Nível de impacto do alerta. | MINOR / MAJOR / CRITICAL |
| **Frequência de Verificação** | Com que frequência a regra é avaliada. | 1 minuto |
| **Histerese** | Margem para evitar "flapping" (alternância rápida entre alerta e normal). | 0.5 dBm |
| **Threshold** | Limite numérico para disparo. | < 15 dBm |
| **Comparação Histórica** | Análise de tendência ou desvio. | Perda > 3 dBm em 1 hora |

### 2.2 Regras de Alerta Propostas

| Regra | Descrição | Severidade | Threshold/Condição | Histerese |
| :--- | :--- | :--- | :--- | :--- |
| **Pump Power Fora do Range** | Potência da bomba do amplificador fora dos limites operacionais. | CRITICAL | `Pump Power` < 12 dBm ou > 24 dBm | 0.5 dBm |
| **Perda de Potência Óptica** | Queda abrupta ou gradual na potência de entrada/saída. | MAJOR | `Input Power` < -20 dBm (limite estático) | 1.0 dBm |
| **Degradação de Potência** | Perda de potência maior que um valor em um período de tempo. | MAJOR | `Input Power` (atual) < `Input Power` (1h atrás) - 3 dBm | N/A |
| **OSNR Abaixo do Limite** | Optical Signal-to-Noise Ratio abaixo do mínimo aceitável. | CRITICAL | `OSNR` < 15 dB | 0.2 dB |
| **Card Down** | O cartão não está em estado operacional (status != UP). | CRITICAL | `card.status` != "UP" | N/A |
| **Telemetria Atrasada** | Falha na atualização de dados de um cartão. | MINOR | `lastUpdated` > 5 minutos | N/A |
| **Temperatura Elevada** | Temperatura interna do cartão acima do limite de segurança. | MAJOR | `Temperature` > 60 °C | 1.0 °C |

### 2.3 Histerese para Evitar Flapping

A histerese é crucial para sistemas de monitoramento. Por exemplo, se o limite crítico para `Pump Power` for 12 dBm:

*   **Disparo do Alerta**: Ocorre quando `Pump Power` cai para **11.5 dBm** (limite - histerese).
*   **Limpeza do Alerta**: Ocorre quando `Pump Power` retorna para **12.5 dBm** (limite + histerese).

Isso evita que pequenas flutuações em torno do limite (ex: 11.9, 12.1, 11.9, 12.1) causem múltiplos alertas desnecessários.

### 2.4 Comparação Histórica (Detecção de Degradação)

O Alert Manager deve ser capaz de realizar consultas no TimescaleDB para detectar tendências:

1.  **Consulta**: `SELECT avg(measure_value) FROM measurements WHERE card_serial='{id}' AND measure_key='InputPower' AND time > now() - interval '1 hour'`
2.  **Regra**: Se `(média_atual - média_anterior)` for menor que um limite (ex: -3 dBm), dispara um alerta de **Degradação Gradual**.

---

## 3. Especificação da API Interna (Backend)

A API interna (FastAPI) serve como a camada de dados para o Frontend, abstraindo a complexidade do TimescaleDB.

| Endpoint | Método | Descrição | Parâmetros Chave |
| :--- | :--- | :--- | :--- |
| `/api/sites` | GET | Lista todos os sites. | `status` (opcional) |
| `/api/cards` | GET | Lista todos os cartões. | `site_id`, `family`, `model` |
| `/api/cards/{serial}` | GET | Detalhes de um cartão. | N/A |
| `/api/measurements/latest` | GET | Últimas medições de todos os cartões. | `limit`, `offset` |
| `/api/measurements/history` | GET | Histórico de medições. | `serial`, `key`, `start_time`, `end_time`, `interval` |
| `/api/alarms` | GET | Lista alarmes ativos ou históricos. | `status`, `severity`, `serial`, `start_time` |
| `/api/alarms/{id}/ack` | POST | Reconhece um alarme. | `user_id` |
| `/api/rules` | GET/POST | Gerencia regras de alerta. | N/A |

---

## 4. Conclusão

O fluxo de coleta de dados é robusto, utilizando um agendador para garantir a periodicidade e uma fila de mensagens para desacoplar o processamento de alertas. As regras de alerta propostas cobrem os principais cenários de falha em redes ópticas, com a inclusão de histerese e análise histórica para maior precisão e redução de falsos positivos.
