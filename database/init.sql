-- Create extensions
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create measurements table
CREATE TABLE IF NOT EXISTS measurements (
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

-- Create hypertable for time-series optimization
SELECT create_hypertable('measurements', 'time', if_not_exists => TRUE);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_measurements_card_serial_time 
    ON measurements (card_serial, time DESC);
CREATE INDEX IF NOT EXISTS idx_measurements_location_site_time 
    ON measurements (location_site, time DESC);
CREATE INDEX IF NOT EXISTS idx_measurements_measure_key_time 
    ON measurements (measure_key, time DESC);
CREATE INDEX IF NOT EXISTS idx_measurements_measure_group 
    ON measurements (measure_group, time DESC);

-- Create cards table
CREATE TABLE IF NOT EXISTS cards (
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

-- Create indexes for cards
CREATE INDEX IF NOT EXISTS idx_cards_location_site 
    ON cards (location_site);
CREATE INDEX IF NOT EXISTS idx_cards_card_family 
    ON cards (card_family);
CREATE INDEX IF NOT EXISTS idx_cards_status 
    ON cards (status);

-- Create alarms table
CREATE TABLE IF NOT EXISTS alarms (
    alarm_id VARCHAR(100) PRIMARY KEY,
    alarm_type VARCHAR(50),
    severity VARCHAR(20),
    card_serial VARCHAR(50),
    location_site VARCHAR(50),
    description TEXT,
    triggered_at TIMESTAMPTZ NOT NULL,
    cleared_at TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for alarms
CREATE INDEX IF NOT EXISTS idx_alarms_card_serial_triggered 
    ON alarms (card_serial, triggered_at DESC);
CREATE INDEX IF NOT EXISTS idx_alarms_location_site_triggered 
    ON alarms (location_site, triggered_at DESC);
CREATE INDEX IF NOT EXISTS idx_alarms_status_triggered 
    ON alarms (status, triggered_at DESC);
CREATE INDEX IF NOT EXISTS idx_alarms_severity 
    ON alarms (severity, triggered_at DESC);

-- Create alert_rules table
CREATE TABLE IF NOT EXISTS alert_rules (
    rule_id SERIAL PRIMARY KEY,
    rule_name VARCHAR(200) NOT NULL,
    measure_key VARCHAR(100) NOT NULL,
    condition VARCHAR(50) NOT NULL, -- 'ABOVE', 'BELOW', 'RANGE', 'DEGRADATION'
    threshold_min FLOAT8,
    threshold_max FLOAT8,
    severity VARCHAR(20) NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    hysteresis FLOAT8 DEFAULT 0.5,
    time_window INTERVAL, -- For degradation detection
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for alert_rules
CREATE INDEX IF NOT EXISTS idx_alert_rules_measure_key 
    ON alert_rules (measure_key);
CREATE INDEX IF NOT EXISTS idx_alert_rules_enabled 
    ON alert_rules (enabled);

-- Insert default alert rules
INSERT INTO alert_rules (rule_name, measure_key, condition, threshold_min, threshold_max, severity, enabled, hysteresis) VALUES
    ('Pump Power Fora do Range', 'PUMP_POWER_A', 'RANGE', 12.0, 24.0, 'CRITICAL', TRUE, 0.5),
    ('Pump Power Fora do Range', 'PUMP_POWER_B', 'RANGE', 12.0, 24.0, 'CRITICAL', TRUE, 0.5),
    ('Perda de Potência Óptica', 'INPUT_POWER', 'BELOW', -20.0, NULL, 'MAJOR', TRUE, 1.0),
    ('OSNR Abaixo do Limite', 'OSNR', 'BELOW', 15.0, NULL, 'CRITICAL', TRUE, 0.2),
    ('Temperatura Elevada', 'TEMPERATURE', 'ABOVE', NULL, 60.0, 'MAJOR', TRUE, 1.0)
ON CONFLICT DO NOTHING;

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for alert_rules
CREATE TRIGGER update_alert_rules_updated_at 
    BEFORE UPDATE ON alert_rules
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create system_config table for storing configuration
CREATE TABLE IF NOT EXISTS system_config (
    config_key VARCHAR(100) PRIMARY KEY,
    config_value TEXT,
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_system_config_key ON system_config (config_key);

-- Insert default configuration
INSERT INTO system_config (config_key, config_value, description) VALUES
    ('PADTEC_API_URL', 'http://108.165.140.144:8181/nms-api/', 'URL da API Padtec NMS'),
    ('PADTEC_API_TOKEN', '', 'Token de autenticação da API Padtec'),
    ('COLLECT_INTERVAL_CRITICAL', '30', 'Intervalo de coleta para medições críticas (segundos)'),
    ('COLLECT_INTERVAL_NORMAL', '300', 'Intervalo de coleta para medições normais (segundos)')
ON CONFLICT (config_key) DO NOTHING;

-- Create view for latest measurements
CREATE OR REPLACE VIEW latest_measurements AS
SELECT DISTINCT ON (card_serial, measure_key)
    time,
    card_serial,
    card_part,
    location_site,
    measure_key,
    measure_name,
    measure_value,
    measure_unit,
    measure_group,
    quality
FROM measurements
ORDER BY card_serial, measure_key, time DESC;

-- Create view for active alarms summary
CREATE OR REPLACE VIEW active_alarms_summary AS
SELECT 
    location_site,
    severity,
    COUNT(*) AS count
FROM alarms
WHERE status = 'ACTIVE'
GROUP BY location_site, severity;

