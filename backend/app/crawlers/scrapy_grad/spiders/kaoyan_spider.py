import scrapy


class KaoyanSpider(scrapy.Spider):
    name = 'kaoyan'
    allowed_domains = ['kaoyan.com']
    start_urls = [
        'https://www.kaoyan.com/experience/',
        'https://www.kaoyan.com/news/list/1/9370',
        'https://www.kaoyan.com/news/list/1/3946',
        'https://www.kaoyan.com/news/list/1/3949',
    ]
    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS': 10,
        'DEPTH_LIMIT': 2,
    }

    def parse(self, response):
        for link in response.css('a::attr(href)').getall():
            if '/article/' in link or 'uuid=' in link:
                yield response.follow(link, self.parse_article)

    def parse_article(self, response):
        yield {
            'url': response.url,
            'title': response.css('title::text').get('').strip(),
            'content': response.css('body').get('').strip()[:3000],
            'source': 'kaoyan.com',
        }
