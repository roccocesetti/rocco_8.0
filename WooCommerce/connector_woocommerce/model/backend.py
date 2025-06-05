# -*- coding: utf-8 -*-
#
#
#    Tech-Receptives Solutions Pvt. Ltd.
#    Copyright (C) 2009-TODAY Tech-Receptives(<http://www.techreceptives.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#

from openerp import models, api, fields, _
from woocommerce import API
from openerp.exceptions import Warning
from openerp.addons.connector.session import ConnectorSession
from datetime import datetime
from .product_category import category_import_batch
from .product import product_import_batch
from .customer import customer_import_batch
from .sale import sale_order_import_batch


class wc_backend(models.Model):
    _name = 'wc.backend'
    _inherit = 'connector.backend'
    _description = 'WooCommerce Backend Configuration'
    name = fields.Char(string='name')
    _backend_type = 'woo'
    location = fields.Char("Url")
    consumer_key = fields.Char("Consumer key")
    consumer_secret = fields.Char("Consumer Secret")
    version = fields.Selection([('v2', 'V2')], 'Version')
    verify_ssl = fields.Boolean("Verify SSL")
    https_location = fields.Char("Url https")
    https_version = fields.Selection([('wc/v2', 'wc/V2')], 'Version')
    https_query_string_auth = fields.Boolean("query_string_auth")
    https_verify_ssl = fields.Boolean("Verify SSL")
    default_lang_id = fields.Many2one(
        comodel_name='res.lang',
        string='Default Language',
        help="If a default language is selected, the records "
             "will be imported in the translation of this language.\n"
             "Note that a similar configuration exists "
             "for each storeview.",
    )
    carrier_id = fields.Many2one(
        comodel_name='delivery.carrier',
        string='Tipo spedizione',
        help="Tipo spedizione",
    )
    transportation_reason_id = fields.Many2one(
        comodel_name='stock.picking.transportation_reason',
        string='Ragione del trasporto',
        help="Ragione del trasporto",
    )
    transportation_method_id = fields.Many2one(
        comodel_name='stock.picking.transportation_method',
        string='metodo di trasporto',
        help="metodo del trasporto",
    )
    carriage_condition_id = fields.Many2one(
        comodel_name='stock.picking.carriage_condition',
        string='Condizioni di trasporto',
        help="Condizioni del trasporto",
    )
    goods_description_id = fields.Many2one(
        comodel_name='stock.picking.goods_description',
        string='Descrizione trasporto ',
        help="Descrizione trasporto ",
    )
    tax_id = fields.Many2one(
        comodel_name='account.tax',
        string='Default tax',
        help="aliquota prodotto",
    )
    wholesale_tax_id = fields.Many2one(
        comodel_name='account.tax',
        string='Aliquota rivenditore',
        help="aliquota rivenditore prodotto",
    )
    delivery_product_id = fields.Many2one(
        comodel_name='product.product',
        string='Trasporto ',
        help="Trasporto ",
    )
    workflow_process_id = fields.Many2one(
        comodel_name='sale.workflow.process',
        string='workFlow ',
        help="workFlow ",
    )
    payment_method_id = fields.Many2one(
        comodel_name='payment.method',
        string='Metodo di pagamento ',
        help="Metodo di pagamemnto ",
    )
    pricelist_id = fields.Many2one(
        comodel_name='product.pricelist',
        string='Prezzo rivenditore ',
        help="Prezzo rivenditore",
    )

    @api.multi
    def get_product_ids(self, data):
        product_ids = [x['id'] for x in data['products']]
        product_ids = sorted(product_ids)
        return product_ids

    @api.multi
    def get_product_category_ids(self, data):
        product_category_ids = [x['id'] for x in data['product_categories']]
        product_category_ids = sorted(product_category_ids)
        return product_category_ids

    @api.multi
    def get_customer_ids(self, data):
        customer_ids = [x['id'] for x in data['customers']]
        customer_ids = sorted(customer_ids)
        return customer_ids

    @api.multi
    def get_order_ids(self, data):
        order_ids = self.check_existing_order(data)
        return order_ids

    @api.multi
    def update_existing_order(self, woo_sale_order, data):
        """ Enter Your logic for Existing Sale Order """
        return True

    @api.multi
    def check_existing_order(self, data):
        order_ids = []
        for val in data['orders']:
            woo_sale_order = self.env['woo.sale.order'].search(
                [('woo_id', '=', val['id'])])
            if woo_sale_order:
                self.update_existing_order(woo_sale_order[0], val)
                continue
            order_ids.append(val['id'])
        return order_ids

    @api.multi
    def test_connection(self):
        location = self.location
        cons_key = self.consumer_key
        sec_key = self.consumer_secret
        verify_ssl = self.verify_ssl
        query_string_auth=self.https_query_string_auth,
        #query_string_auth = self.query_string_auth
        version = 'v2'

        if location.find('https')>=0:
            wcapi = API(url=location, 
                        consumer_key=cons_key,
                        consumer_secret=sec_key,
                        version=version,                                        
                        verify_ssl=verify_ssl,
                        query_string_auth=True,

                        )
            print 'https'
        else:
            wcapi = API(url=location, 
                        consumer_key=cons_key,
                        consumer_secret=sec_key,
                        version=version,                                        
                        )
        #wcapi.get("products").json()
        r = wcapi.get("products")
        if r.status_code == 404:
            raise Warning(_("Enter Valid url"))
        val = r.json()
        print 'test_connection_val',val
        msg = ''
        if 'errors' in r.json():
            msg = val['errors'][0]['message'] + '\n' + val['errors'][0]['code']
            raise Warning(_(msg))
        else:
            raise Warning(_('Test Success'))
        return True

    @api.multi
    def import_category(self):
        session = ConnectorSession(self.env.cr, self.env.uid,
                                   context=self.env.context)
        import_start_time = datetime.now()
        backend_id = self.id
        from_date = None
        category_import_batch.delay(
            session, 'woo.product.category', backend_id,
            {'from_date': from_date,
             'to_date': import_start_time}, priority=1)
        return True

    @api.multi
    def import_product(self):
        session = ConnectorSession(self.env.cr, self.env.uid,
                                   context=self.env.context)
        import_start_time = datetime.now()
        backend_id = self.id
        from_date = None
        product_import_batch.delay(
            session, 'woo.product.product', backend_id,
            {'from_date': from_date,
             'to_date': import_start_time}, priority=2)
        return True

    @api.multi
    def import_customer(self):
        session = ConnectorSession(self.env.cr, self.env.uid,
                                   context=self.env.context)
        import_start_time = datetime.now()
        backend_id = self.id
        from_date = None
        customer_import_batch.delay(
            session, 'woo.res.partner', backend_id,
            {'from_date': from_date,
             'to_date': import_start_time}, priority=3)
        return True

    @api.multi
    def import_order(self):
        session = ConnectorSession(self.env.cr, self.env.uid,
                                   context=self.env.context)
        import_start_time = datetime.now()
        backend_id = self.id
        from_date = None
        sale_order_import_batch.delay(
            session, 'woo.sale.order', backend_id,
            {'from_date': from_date,
             'to_date': import_start_time}, priority=4)
        return True

    @api.multi
    def import_categories(self):
        """ Import Product categories """
        for backend in self:
            backend.import_category()
        return True

    @api.multi
    def import_products(self):
        """ Import categories from all websites """
        for backend in self:
            backend.import_product()
        return True

    @api.multi
    def import_customers(self):
        """ Import categories from all websites """
        for backend in self:
            backend.import_customer()
        return True

    @api.multi
    def import_orders(self):
        """ Import Orders from all websites """
        print 'import_orders'
        for backend in self:
            backend.import_order()
        return True
    
    @api.model
    def import_orders_cron(self):
            print 'import_orders_cron'
            back_ids_obj=self.search([('id','>',0)])
            for backend in back_ids_obj:
                backend.import_order()
            return True
