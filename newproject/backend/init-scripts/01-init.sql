-- AICloudOps MySQL 初始化脚本
-- 此脚本在 MySQL 容器首次启动时自动执行

-- 设置字符集
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS aicops 
    DEFAULT CHARACTER SET utf8mb4 
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE aicops;

-- 创建会话表
CREATE TABLE IF NOT EXISTS sessions (
    id VARCHAR(36) PRIMARY KEY,
    title VARCHAR(255),
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    INDEX idx_updated_at (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 创建消息表
CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    trace_id VARCHAR(36),
    safety_report JSON,
    tool_result JSON,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    INDEX idx_session_created (session_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 创建审计日志表
CREATE TABLE IF NOT EXISTS audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trace_id VARCHAR(36) NOT NULL,
    step VARCHAR(100) NOT NULL,
    step_order INT NOT NULL,
    data JSON NOT NULL,
    created_at DATETIME NOT NULL,
    INDEX idx_trace (trace_id, step_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 创建工具执行记录表
CREATE TABLE IF NOT EXISTS tool_executions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trace_id VARCHAR(36),
    tool_name VARCHAR(100) NOT NULL,
    params JSON,
    result JSON,
    status VARCHAR(50) NOT NULL,
    executed_at DATETIME NOT NULL,
    INDEX idx_trace (trace_id),
    INDEX idx_tool_status (tool_name, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 授权（确保 aicops 用户有足够权限）
GRANT ALL PRIVILEGES ON aicops.* TO 'aicops'@'%';
FLUSH PRIVILEGES;
