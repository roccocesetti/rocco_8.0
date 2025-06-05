# -*- coding: utf-8 -*-

from openerp import http
from openerp.http import request
from openerp.addons.website_sale.controllers import main
from openerp.addons.website_sale.controllers.main import website_sale

main.PPR = 3


class WebsiteSale(website_sale):

    def _get_search_domain(self, search, category, attrib_values):
        domain = super(WebsiteSale, self)._get_search_domain(search, category, attrib_values)
        domain += [('is_shop_product', '=', True)]
        return domain

    # @http.route([
    #     '/shop',
    #     '/shop/page/<int:page>',
    #     '/shop/category/<model("product.category"):category>',
    #     '/shop/category/<model("product.category"):category>/page/<int:page>'
    # ], type='http', auth="public", website=True)
    # def shop(self, page=0, category=None, search='', **post):
    #     return super(WebsiteSale,self).shop(page, category, search,**post)
