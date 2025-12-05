# Especificação do Dashboard Estilo Grafana

O dashboard deve fornecer uma visão clara e imediata da saúde da rede óptica, seguindo a filosofia de visualização de dados do Grafana: painéis modulares, métricas em tempo real e histórico de séries temporais.

## 1. Dashboard Geral por Site (Site Overview)

**Objetivo:** Fornecer uma visão de alto nível do status operacional de todos os sites e equipamentos.

| Painel | Tipo de Visualização | Métrica Principal | Sugestão Visual |
| :--- | :--- | :--- | :--- |
| **Status da Rede** | Stat/Gauge | Porcentagem de Cards UP | Gauge grande. Cor: Verde (UP), Amarelo (DEGRADED), Vermelho (DOWN). |
| **Alarmes Ativos** | Tabela | Contagem de alarmes por Severidade | Tabela com filtro por CRITICAL/MAJOR/MINOR. Fundo vermelho para CRITICAL. |
| **Mapa de Sites** | Geomap | Localização dos Sites | Mapa com marcadores coloridos (Verde/Amarelo/Vermelho) indicando o pior status do site. |
| **Últimas Medições Críticas** | Tabela | `Pump Power`, `OSNR`, `Input Power` | Tabela com as últimas medições de todos os cards, ordenadas por `updatedAt`. Células coloridas se fora do limite. |
| **Timeline de Alarmes** | Gráfico de Série Temporal | Eventos de Alarme | Gráfico de barras ou pontos no tempo, mostrando a frequência de alertas nas últimas 24h. |
| **Inventário Rápido** | Stat/Tabela | Contagem de `cardFamily` e `cardModel` | Mostrar a distribuição de tipos de placas na rede. |

## 2. Dashboard Detalhado por Card/Modelo (Card Detail)

**Objetivo:** Fornecer uma análise aprofundada e histórica de um cartão específico.

| Painel | Tipo de Visualização | Métrica Principal | Sugestão Visual |
| :--- | :--- | :--- | :--- |
| **Status do Card** | Stat/Gauge | Status UP/DOWN | Indicador grande e claro. Exibir `cardSerial`, `cardModel`, `locationSite`. |
| **Pump Power (Tendência)** | Gráfico de Série Temporal | `Pump Power` (dBm) | Gráfico de linha com limites de alerta (Thresholds) como linhas horizontais (Vermelho/Amarelo). Tendência horária/diária. |
| **OSNR (Tendência)** | Gráfico de Série Temporal | `OSNR` (dB) | Gráfico de linha com limite mínimo de alerta. Mostrar a média móvel para detectar degradação gradual. |
| **In/Out Power** | Gráfico de Série Temporal | `Input Power` e `Output Power` (dBm) | Gráficos de linha sobrepostos para comparação. Destacar a diferença (perda). |
| **Temperatura** | Gráfico de Série Temporal | `Temperature` (°C) | Gráfico de linha com limite máximo de alerta. |
| **Timeline de Alarmes do Card** | Tabela/Gráfico | Histórico de Alarmes | Tabela de eventos de alarme específicos para este card, com `triggeredAt`, `clearedAt` e `severity`. |
| **Tabela com Últimas Medições** | Tabela | Todas as `measureKey` | Tabela detalhada com a última leitura de cada parâmetro do card. |

## 3. Sugestões Visuais e Organização

### 3.1 Cores

As cores devem ser usadas para transmitir o status de forma imediata:

| Cor | Significado | Uso |
| :--- | :--- | :--- |
| **Verde** (`#4CAF50`) | Normal / UP | Status de Cards, Medições dentro do limite. |
| **Amarelo** (`#FFC107`) | Aviso / MINOR | Alertas de baixa severidade, medições próximas ao limite. |
| **Laranja** (`#FF9800`) | Atenção / MAJOR | Alertas de média severidade, degradação. |
| **Vermelho** (`#F44336`) | Crítico / DOWN | Alertas de alta severidade, falha de card, medições fora do limite. |
| **Azul** (`#2196F3`) | Informativo | Dados históricos, tendências, contagens. |

### 3.2 Organização

1.  **Layout Responsivo**: O dashboard deve se adaptar a diferentes tamanhos de tela (desktop, tablet).
2.  **Filtros**: No topo, filtros globais para `locationSite`, `cardFamily`, `cardModel` e `Time Range`.
3.  **Navegação**: Links claros entre o Dashboard Geral (Site Overview) e o Dashboard Detalhado (Card Detail).
4.  **Painéis de Tendência**: Usar o recurso de "Annotation" do Grafana para marcar eventos de alarme diretamente nos gráficos de tendência, correlacionando a falha com a mudança na métrica.
5.  **Unidades**: Sempre exibir as unidades de medida (`dBm`, `°C`, `dB`, etc.) de forma clara nos eixos e legendas.

---

## 4. Consolidação do Projeto

Este documento, juntamente com a **Análise Detalhada da API Padtec**, a **Proposta Técnica de Arquitetura** e o **Fluxo Operacional de Coleta de Dados e Regras de Alerta**, compõe o projeto completo de monitoramento.
