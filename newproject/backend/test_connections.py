"""
数据存储连接测试脚本

用途：验证 Redis 和 MySQL 连接是否正常
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_redis_connection():
    """测试 Redis 连接"""
    print("\n" + "=" * 60)
    print("  Redis 连接测试")
    print("=" * 60)
    
    try:
        from backend.redis_client import redis_client
        from backend.config import get_settings
        
        settings = get_settings()
        
        if not settings.REDIS_ENABLED:
            print("[跳过] Redis 未启用")
            return False
        
        print(f"[连接] {settings.REDIS_URL}")
        await redis_client.initialize()
        
        # 测试基本操作
        print("[测试] 写入测试数据...")
        await redis_client.set("test:key", {"message": "Hello Redis!"}, expire=10)
        
        print("[测试] 读取测试数据...")
        data = await redis_client.get("test:key")
        
        if data and data.get("message") == "Hello Redis!":
            print("[成功] Redis 连接正常")
            print(f"[数据] {data}")
            
            # 清理测试数据
            await redis_client.delete("test:key")
            await redis_client.close()
            return True
        else:
            print("[失败] 数据读写异常")
            return False
            
    except Exception as e:
        print(f"[失败] Redis 连接失败: {e}")
        print("[提示] 请确保 Redis 容器已启动: docker-compose up -d redis")
        return False


async def test_mysql_connection():
    """测试 MySQL 连接"""
    print("\n" + "=" * 60)
    print("  MySQL 连接测试")
    print("=" * 60)
    
    try:
        from backend.database_mysql import mysql_db
        from backend.config import get_settings
        
        settings = get_settings()
        
        if settings.DATABASE_TYPE != "mysql":
            print("[跳过] 当前使用 SQLite，未启用 MySQL")
            return False
        
        print(f"[连接] {settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}")
        await mysql_db.initialize()
        
        # 测试基本操作
        print("[测试] 创建测试会话...")
        session_id = await mysql_db.create_session("测试会话")
        
        print("[测试] 查询会话列表...")
        sessions = await mysql_db.get_sessions(limit=1)
        
        if sessions:
            print("[成功] MySQL 连接正常")
            print(f"[数据] 最新会话: {sessions[0]['title']}")
            
            # 清理测试数据
            await mysql_db.delete_session(session_id)
            await mysql_db.close()
            return True
        else:
            print("[失败] 数据读写异常")
            return False
            
    except Exception as e:
        print(f"[失败] MySQL 连接失败: {e}")
        print("[提示] 请确保 MySQL 容器已启动: docker-compose up -d mysql")
        return False


async def test_sqlite_connection():
    """测试 SQLite 连接"""
    print("\n" + "=" * 60)
    print("  SQLite 连接测试")
    print("=" * 60)
    
    try:
        from backend.database import db
        from backend.config import get_settings
        
        settings = get_settings()
        
        if settings.DATABASE_TYPE != "sqlite":
            print("[跳过] 当前使用 MySQL，未启用 SQLite")
            return False
        
        print(f"[连接] {settings.DATABASE_URL}")
        
        # 测试基本操作
        print("[测试] 创建测试会话...")
        session_id = db.create_session("测试会话")
        
        print("[测试] 查询会话列表...")
        sessions = db.get_sessions(limit=1)
        
        if sessions:
            print("[成功] SQLite 连接正常")
            print(f"[数据] 最新会话: {sessions[0]['title']}")
            
            # 清理测试数据
            db.delete_session(session_id)
            return True
        else:
            print("[失败] 数据读写异常")
            return False
            
    except Exception as e:
        print(f"[失败] SQLite 连接失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("  AICloudOps 数据存储连接测试")
    print("=" * 60)
    
    results = {
        "Redis": await test_redis_connection(),
        "SQLite": await test_sqlite_connection(),
        "MySQL": await test_mysql_connection()
    }
    
    print("\n" + "=" * 60)
    print("  测试结果汇总")
    print("=" * 60)
    
    for name, success in results.items():
        status = "✅ 成功" if success else "❌ 失败"
        print(f"  {name:10s} {status}")
    
    print("=" * 60)
    
    # 给出建议
    if not results["Redis"]:
        print("\n[建议] 启动 Redis 容器以获得更好的性能：")
        print("  docker-compose up -d redis")
    
    if results["SQLite"] and not results["MySQL"]:
        print("\n[建议] 当前使用 SQLite，适合开发环境。")
        print("  生产环境建议切换到 MySQL：")
        print("  1. docker-compose up -d mysql")
        print("  2. 修改 .env: DATABASE_TYPE=mysql")
        print("  3. python backend/migrate_to_mysql.py")


if __name__ == "__main__":
    asyncio.run(main())
