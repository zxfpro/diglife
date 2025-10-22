# config.py

# 注意：请确保这些信息是正确的，尤其是密码。
# 为了安全，在生产环境中，这些敏感信息应该通过环境变量或密钥管理服务来提供，而不是硬编码。

# 阿里云 Redis 连接信息
REDIS_HOST = 'r-2zeuujf6lqtgf5hk7xpd.redis.rds.aliyuncs.com'
REDIS_PORT = 6379
REDIS_USERNAME = 'skgn'  # 如果没有用户名，可以留空或删除
REDIS_PASSWORD = 'Ahs2025_skgn'
REDIS_DATABASE_BROKER = 20 # 用于 Celery broker
REDIS_DATABASE_BACKEND = 21 # 用于 Celery result backend (推荐使用不同的数据库)

# Celery Broker URL
# 格式: redis://[:password@]host:port/db_number
# 如果有用户名: redis://username:password@host:port/db_number
CELERY_BROKER_URL = f"redis://{REDIS_USERNAME}:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DATABASE_BROKER}"

# Celery Result Backend URL
CELERY_RESULT_BACKEND = f"redis://{REDIS_USERNAME}:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DATABASE_BACKEND}"
