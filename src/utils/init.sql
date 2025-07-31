-- E-commerce Analytics Database Schema
-- This script creates all necessary tables for the analytics pipeline

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Raw events table (for storing incoming events)
CREATE TABLE IF NOT EXISTS raw_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255),
    session_id VARCHAR(255),
    event_type VARCHAR(50) NOT NULL,
    event_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    product_id VARCHAR(255),
    category VARCHAR(100),
    price DECIMAL(10,2),
    quantity INTEGER,
    page_url VARCHAR(500),
    user_agent TEXT,
    ip_address INET,
    raw_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE
);

-- Processed events table (for storing cleaned and enriched events)
CREATE TABLE IF NOT EXISTS processed_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    raw_event_id UUID REFERENCES raw_events(id),
    event_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255),
    session_id VARCHAR(255),
    event_type VARCHAR(50) NOT NULL,
    event_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    product_id VARCHAR(255),
    category VARCHAR(100),
    price DECIMAL(10,2),
    quantity INTEGER,
    page_url VARCHAR(500),
    user_agent TEXT,
    ip_address INET,
    enriched_data JSONB,
    quality_score DECIMAL(3,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Daily aggregations table
CREATE TABLE IF NOT EXISTS daily_aggregations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL,
    category VARCHAR(100),
    event_type VARCHAR(50),
    total_events BIGINT DEFAULT 0,
    total_revenue DECIMAL(15,2) DEFAULT 0,
    unique_users BIGINT DEFAULT 0,
    unique_sessions BIGINT DEFAULT 0,
    conversion_rate DECIMAL(5,4),
    avg_order_value DECIMAL(10,2),
    top_products JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(date, category, event_type)
);

-- Real-time metrics table
CREATE TABLE IF NOT EXISTS realtime_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(15,2),
    metric_count BIGINT,
    window_start TIMESTAMP WITH TIME ZONE NOT NULL,
    window_end TIMESTAMP WITH TIME ZONE NOT NULL,
    category VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User sessions table
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(255) UNIQUE NOT NULL,
    user_id VARCHAR(255),
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    page_views INTEGER DEFAULT 0,
    cart_additions INTEGER DEFAULT 0,
    purchases INTEGER DEFAULT 0,
    total_revenue DECIMAL(10,2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Product analytics table
CREATE TABLE IF NOT EXISTS product_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    name VARCHAR(255),
    price DECIMAL(10,2),
    total_views BIGINT DEFAULT 0,
    total_cart_additions BIGINT DEFAULT 0,
    total_purchases BIGINT DEFAULT 0,
    conversion_rate DECIMAL(5,4),
    revenue DECIMAL(15,2) DEFAULT 0,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(product_id)
);

-- Data quality logs table
CREATE TABLE IF NOT EXISTS data_quality_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    validation_name VARCHAR(255) NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    validation_result BOOLEAN NOT NULL,
    error_message TEXT,
    records_checked BIGINT,
    records_failed BIGINT,
    validation_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Pipeline execution logs table
CREATE TABLE IF NOT EXISTS pipeline_execution_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pipeline_name VARCHAR(255) NOT NULL,
    execution_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    records_processed BIGINT,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_raw_events_timestamp ON raw_events(event_timestamp);
CREATE INDEX IF NOT EXISTS idx_raw_events_type ON raw_events(event_type);
CREATE INDEX IF NOT EXISTS idx_raw_events_user_id ON raw_events(user_id);
CREATE INDEX IF NOT EXISTS idx_raw_events_product_id ON raw_events(product_id);

CREATE INDEX IF NOT EXISTS idx_processed_events_timestamp ON processed_events(event_timestamp);
CREATE INDEX IF NOT EXISTS idx_processed_events_type ON processed_events(event_type);
CREATE INDEX IF NOT EXISTS idx_processed_events_user_id ON processed_events(user_id);

CREATE INDEX IF NOT EXISTS idx_daily_aggregations_date ON daily_aggregations(date);
CREATE INDEX IF NOT EXISTS idx_daily_aggregations_category ON daily_aggregations(category);

CREATE INDEX IF NOT EXISTS idx_realtime_metrics_window ON realtime_metrics(window_start, window_end);
CREATE INDEX IF NOT EXISTS idx_realtime_metrics_name ON realtime_metrics(metric_name);

CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_start_time ON user_sessions(start_time);

CREATE INDEX IF NOT EXISTS idx_product_analytics_product_id ON product_analytics(product_id);
CREATE INDEX IF NOT EXISTS idx_product_analytics_category ON product_analytics(category);

-- Create views for common analytics queries
CREATE OR REPLACE VIEW daily_summary AS
SELECT 
    date,
    SUM(CASE WHEN event_type = 'page_view' THEN total_events ELSE 0 END) as page_views,
    SUM(CASE WHEN event_type = 'add_to_cart' THEN total_events ELSE 0 END) as cart_additions,
    SUM(CASE WHEN event_type = 'purchase' THEN total_events ELSE 0 END) as purchases,
    SUM(total_revenue) as total_revenue,
    SUM(unique_users) as unique_users,
    SUM(unique_sessions) as unique_sessions,
    CASE 
        WHEN SUM(CASE WHEN event_type = 'page_view' THEN total_events ELSE 0 END) > 0 
        THEN ROUND(
            CAST(SUM(CASE WHEN event_type = 'purchase' THEN total_events ELSE 0 END) AS DECIMAL) / 
            CAST(SUM(CASE WHEN event_type = 'page_view' THEN total_events ELSE 0 END) AS DECIMAL) * 100, 2
        )
        ELSE 0 
    END as conversion_rate
FROM daily_aggregations 
GROUP BY date 
ORDER BY date DESC;

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns
DROP TRIGGER IF EXISTS update_daily_aggregations_updated_at ON daily_aggregations;
CREATE TRIGGER update_daily_aggregations_updated_at 
    BEFORE UPDATE ON daily_aggregations 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_sessions_updated_at ON user_sessions;
CREATE TRIGGER update_user_sessions_updated_at 
    BEFORE UPDATE ON user_sessions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert sample data for testing
INSERT INTO product_analytics (product_id, category, name, price) VALUES
('PROD001', 'Electronics', 'Smartphone X', 799.99),
('PROD002', 'Electronics', 'Laptop Pro', 1299.99),
('PROD003', 'Clothing', 'T-Shirt', 29.99),
('PROD004', 'Books', 'Data Science Guide', 49.99),
('PROD005', 'Home', 'Coffee Maker', 89.99)
ON CONFLICT (product_id) DO NOTHING; 