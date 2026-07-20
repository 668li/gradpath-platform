import scrapy


class YzSpider(scrapy.Spider):
    name = 'yz'
    allowed_domains = ['yz.chsi.com.cn']
    start_urls = [
        'https://yz.chsi.com.cn/kyzx/kydt/',
        'https://yz.chsi.com.cn/kyzx/jybzc/',
        'https://yz.chsi.com.cn/kyzx/zsjz/',
    ]
    custom_settings = {
        'DOWNLOAD_DELAY': 3,
        'CONCURRENT_REQUESTS': 5,
    }

    def parse(self, response):
        for link in response.css('a[href*="/kyzx/"]::attr(href)').getall():
            if link.endswith('.html'):
                yield response.follow(link, self.parse_article)

    def parse_article(self, response):
        yield {
            'url': response.url,
            'title': response.css('title::text').get('').strip(),
            'content': response.css('body').get('').strip()[:3000],
            'source': 'yz.chsi.com.cn',
        }
