import scrapy


class LoginBull2Spider(scrapy.Spider):
    name = 'login_bull2'
    allowed_domains = ['invest.webull.com']
    start_urls = ['http://invest.webull.com/']

    def parse(self, response):
        pass
