# AICloudOps 一键启动脚本

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AICloudOps 数据存储服务启动脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Docker 是否安装
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "[错误] Docker 未安装，请先安装 Docker Desktop" -ForegroundColor Red
    exit 1
}

# 检查 Docker Compose 是否可用
if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
    Write-Host "[错误] Docker Compose 未安装" -ForegroundColor Red
    exit 1
}

# 检查 .env 文件是否存在
if (-not (Test-Path ".env")) {
    Write-Host "[提示] .env 文件不存在，从模板创建..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "[完成] .env 文件已创建，请配置 LLM_API_KEY" -ForegroundColor Green
}

# 显示菜单
Write-Host "请选择启动模式：" -ForegroundColor Yellow
Write-Host "  1. 仅启动 Redis（推荐开发环境）"
Write-Host "  2. 启动 Redis + MySQL（生产环境）"
Write-Host "  3. 启动所有服务（含 Adminer 管理工具）"
Write-Host "  4. 停止所有服务"
Write-Host "  5. 查看服务状态"
Write-Host "  6. 查看日志"
Write-Host ""

$choice = Read-Host "请输入选项 (1-6)"

switch ($choice) {
    "1" {
        Write-Host "[启动] 正在启动 Redis..." -ForegroundColor Green
        docker-compose up -d redis
        Write-Host "[完成] Redis 已启动" -ForegroundColor Green
        Write-Host ""
        Write-Host "Redis 连接信息：" -ForegroundColor Cyan
        Write-Host "  URL: redis://localhost:6379/0"
        Write-Host ""
    }
    "2" {
        Write-Host "[启动] 正在启动 Redis 和 MySQL..." -ForegroundColor Green
        docker-compose up -d redis mysql
        Write-Host "[等待] MySQL 初始化中，请稍候 10 秒..." -ForegroundColor Yellow
        Start-Sleep -Seconds 10
        Write-Host "[完成] Redis 和 MySQL 已启动" -ForegroundColor Green
        Write-Host ""
        Write-Host "连接信息：" -ForegroundColor Cyan
        Write-Host "  Redis: redis://localhost:6379/0"
        Write-Host "  MySQL: mysql://aicops:aicops_pass_2024@localhost:3306/aicops"
        Write-Host ""
    }
    "3" {
        Write-Host "[启动] 正在启动所有服务..." -ForegroundColor Green
        docker-compose --profile dev up -d
        Write-Host "[等待] MySQL 初始化中，请稍候 10 秒..." -ForegroundColor Yellow
        Start-Sleep -Seconds 10
        Write-Host "[完成] 所有服务已启动" -ForegroundColor Green
        Write-Host ""
        Write-Host "连接信息：" -ForegroundColor Cyan
        Write-Host "  Redis: redis://localhost:6379/0"
        Write-Host "  MySQL: mysql://aicops:aicops_pass_2024@localhost:3306/aicops"
        Write-Host "  Adminer: http://localhost:8080"
        Write-Host ""
        Write-Host "Adminer 登录信息：" -ForegroundColor Cyan
        Write-Host "  服务器: mysql"
        Write-Host "  用户名: aicops"
        Write-Host "  密码: aicops_pass_2024"
        Write-Host "  数据库: aicops"
        Write-Host ""
    }
    "4" {
        Write-Host "[停止] 正在停止所有服务..." -ForegroundColor Yellow
        docker-compose down
        Write-Host "[完成] 所有服务已停止" -ForegroundColor Green
    }
    "5" {
        Write-Host "[状态] 服务运行状态：" -ForegroundColor Cyan
        docker-compose ps
    }
    "6" {
        Write-Host "[日志] 选择要查看的服务：" -ForegroundColor Yellow
        Write-Host "  1. Redis"
        Write-Host "  2. MySQL"
        Write-Host "  3. Adminer"
        $logChoice = Read-Host "请输入选项 (1-3)"
        
        switch ($logChoice) {
            "1" { docker-compose logs -f redis }
            "2" { docker-compose logs -f mysql }
            "3" { docker-compose logs -f adminer }
            default { Write-Host "[错误] 无效选项" -ForegroundColor Red }
        }
    }
    default {
        Write-Host "[错误] 无效选项" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  操作完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
