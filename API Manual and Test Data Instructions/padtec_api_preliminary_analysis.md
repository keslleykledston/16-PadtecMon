# Análise Preliminar da API Padtec NMS

Com base nas informações fornecidas (URL, Token e campos JSON esperados), e na impossibilidade de acesso direto à API no momento, a estrutura e as entidades da API são inferidas para prosseguir com o projeto de arquitetura.

## 1. Informações de Acesso
*   **URL Base**: `http://108.165.140.144:8181/nms-api/`
*   **Autenticação**: Padrão **Bearer Token** (JWT-like).
    *   **Token**: `eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJubXNwbHVzIiwiaWF0IjoxNzYzMDY3MDMyfQ.IKgvplggs3bhE2Zw7UsnweIbj_h1xSJM5CpsvcUU5uo`
    *   O token deve ser enviado no cabeçalho `Authorization: Bearer <TOKEN>`.

## 2. Entidades e Endpoints Chave (Inferidos)

A API deve seguir um padrão RESTful, com endpoints dedicados para as principais entidades de monitoramento.

| Entidade | Endpoint Sugerido | Propósito | Campos Chave (Exemplos Fornecidos) |
| :--- | :--- | :--- | :--- |
| **Inventário/Cards** | `/cards` ou `/devices` | Listar todas as placas instaladas na rede. | `cardPart`, `cardSerial`, `locationSite`, `cardFamily`, `cardModel` |
| **Medições** | `/measurements` | Coletar dados de telemetria (POWER, TEMP, etc.). | `measureName`, `measureValue`, `measureGroup`, `measureKey`, `updatedAt` |
| **Alarmes** | `/alarms` | Listar alarmes ativos ou históricos. | (Não especificado, mas essencial para monitoramento) |

## 3. Estrutura de Dados (JSON)

O objeto de medição principal deve conter os seguintes campos para permitir a correlação de dados e o armazenamento em série temporal:

| Campo | Tipo | Descrição | Propósito no Projeto |
| :--- | :--- | :--- | :--- |
| `cardPart` | String | Identificador único da placa. | Chave de relacionamento e identificação. |
| `cardSerial` | String | Número de série da placa. | Inventário e rastreabilidade. |
| `locationSite` | String | Identificador do site/localização. | Agrupamento de dados por localização. |
| `measureName` | String | Nome amigável da medição (ex: "Pump Power"). | Exibição em dashboards. |
| `measureValue` | Numérico | O valor da medição. | Dado principal para análise e alerta. |
| `measureGroup` | String | Categoria da medição (ex: "POWER", "OPTICAL"). | Agrupamento lógico de telemetria. |
| `measureKey` | String | Chave única para o tipo de medição (ex: "PUMP_POWER_A"). | Chave para normalização e consulta. |
| `updatedAt` | Timestamp | Carimbo de tempo da medição. | Essencial para banco de dados Time-Series. |

Esta análise preliminar serve como base para a elaboração da arquitetura técnica e dos fluxos de coleta de dados. A próxima fase será a elaboração da Análise Detalhada da API.
