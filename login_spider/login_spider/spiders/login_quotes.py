import scrapy


class LoginQuotesSpider(scrapy.Spider):
    name = 'login_quotes'
    allowed_domains = ['quotes.toscrape.com']
    start_urls = ['http://quotes.toscrape.com/login']

    def parse(self, response):
        pass
