import subprocess
import sys


def run_spider(spider_name):
    cmd = [sys.executable, '-m', 'scrapy', 'crawl', spider_name]
    subprocess.run(cmd, cwd='backend/app/crawlers/scrapy_grad')


if __name__ == '__main__':
    for spider in ['kaoyan', 'yz']:
        print(f'Running {spider} spider...')
        run_spider(spider)
