BOT_NAME = 'gradpath_crawlers'
SPIDER_MODULES = ['app.crawlers.scrapy_grad.spiders']
NEWSPIDER_MODULE = 'app.crawlers.scrapy_grad.spiders'

# Redis for distributed crawling
SCHEDULER = 'scrapy_redis.scheduler.Scheduler'
DUPEFILTER_CLASS = 'scrapy_redis.dupefilter.RFPDupeFilter'
REDIS_URL = 'redis://localhost:6379/0'

# Performance settings
DOWNLOAD_DELAY = 2
CONCURRENT_REQUESTS = 10
CONCURRENT_REQUESTS_PER_DOMAIN = 5
DEPTH_LIMIT = 2
RETRY_TIMES = 3

# Output
FEED_FORMAT = 'json'
FEED_URI = 'output/%(name)s_%(time)s.json'

# Scrapy-Redis pipeline
ITEM_PIPELINES = {
    'scrapy_redis.pipelines.RedisPipeline': 300,
}
