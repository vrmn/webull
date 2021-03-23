import scrapy


class LoginBullSpider(scrapy.Spider):
    name = 'login_bull'
    allowed_domains = ['webull.com']
    start_urls = ['http://webull.com/']

    def parse(self, response):
        pass
