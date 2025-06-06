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

import logging
import xmlrpclib
from openerp import models, fields, api
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.unit.mapper import (mapping,
                                                  ImportMapper
                                                  )
from openerp.addons.connector.exception import IDMissingInBackend
from ..unit.backend_adapter import (GenericAdapter)
from ..unit.import_synchronizer import (DelayedBatchImporter, WooImporter)
from ..connector import get_environment
from ..backend import woo
from openerp.addons.connector_woocommerce.model.sale import SaleOrderAdapter,WooImporter,SaleOrderLineImportMapper
from openerp.addons.connector_woocommerce.model.sale import SaleOrderBatchImporter,SaleOrderImporter,SaleOrderImportMapper
_logger = logging.getLogger(__name__)


class woo_sale_order_status(models.Model):
    _inherit = 'woo.sale.order.status'


class SaleOrder(models.Model):

    _inherit = 'sale.order'


class WooSaleOrder(models.Model):
    _inherit = 'woo.sale.order'


class WooSaleOrderLine(models.Model):
    _inherit = 'woo.sale.order.line'

    @api.model
    def create(self, vals):
        woo_order_id = vals['woo_order_id']
        binding = self.env['woo.sale.order'].browse(woo_order_id)
        vals['order_id'] = binding.openerp_id.id
        binding = super(WooSaleOrderLine, self).create(vals)
        return binding


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
@woo
class SaleOrderLineImportMapper(SaleOrderLineImportMapper):
    _model_name = 'woo.sale.order.line'

    direct = [('quantity', 'product_uom_qty'),
              ('quantity', 'product_uos_qty'),
              ('name', 'name'),
              ('price', 'price_unit')
              ]

    @mapping
    def product_id(self, record):
        binder = self.binder_for('woo.product.product')
        product_id = binder.to_openerp(record['product_id'], unwrap=True)
        assert product_id is not None, (
            "product_id %s should have been imported in "
            "SaleOrderImporter._import_dependencies" % record['product_id'])
        product_ids_obj=self.env['product.product'].search([('id','=',product_id)])
        if product_ids_obj:
            if product_ids_obj[0].taxes_id:
                tax_id=product_ids_obj[0].taxes_id[0]
            else:
                tax_id=None
        return {'product_id': product_id,'tax_id':[(6, 0, [tax_id or self.backend_record.tax_id.id  ])],
}


@woo
class SaleOrderAdapter(SaleOrderAdapter):
    _model_name = 'woo.sale.order'
    _woo_model = 'orders'

    def _call(self, method, arguments):
        try:
            return super(SaleOrderAdapter, self)._call(method, arguments)
        except xmlrpclib.Fault as err:
            # this is the error in the Woo API
            # when the customer does not exist
            if err.faultCode == 102:
                raise IDMissingInBackend
            else:
                raise

    def search(self, filters=None, from_date=None, to_date=None):
        """ Search records according to some criteria and return a
        list of ids

        :rtype: list
        """
        if filters is None:
            filters = {}
        WOO_DATETIME_FORMAT = '%Y/%m/%d %H:%M:%S'
        dt_fmt = WOO_DATETIME_FORMAT
        if from_date is not None:
            # updated_at include the created records
            filters.setdefault('updated_at', {})
            filters['updated_at']['from'] = from_date.strftime(dt_fmt)
        if to_date is not None:
            filters.setdefault('updated_at', {})
            filters['updated_at']['to'] = to_date.strftime(dt_fmt)

        return self._call('orders/list',
                          [filters] if filters else [{}])


@woo
class SaleOrderBatchImporter(SaleOrderBatchImporter):

    """ Import the WooCommerce Partners.

    For every partner in the list, a delayed job is created.
    """
    _model_name = ['woo.sale.order']

    def _import_record(self, woo_id, priority=None):
        """ Delay a job for the import """
        super(SaleOrderBatchImporter, self)._import_record(
            woo_id, priority=priority)

    def update_existing_order(self, woo_sale_order, record_id):
        """ Enter Your logic for Existing Sale Order """
        return True

    def run(self, filters=None):
        """ Run the synchronization """
#
        from_date = filters.pop('from_date', None)
        to_date = filters.pop('to_date', None)
        record_ids = self.backend_adapter.search(
            filters,
            from_date=from_date,
            to_date=to_date,
        )
        order_ids = []
        for record_id in record_ids:
            woo_sale_order = self.env['woo.sale.order'].search(
                [('woo_id', '=', record_id)])
            if woo_sale_order:
                self.update_existing_order(woo_sale_order[0], record_id)
            else:
                order_ids.append(record_id)
        _logger.info('search for woo partners %s returned %s',
                     filters, record_ids)
        for record_id in order_ids:
            self._import_record(record_id, 50)


SaleOrderBatchImporter = SaleOrderBatchImporter
#


@woo
class SaleOrderImporter(SaleOrderImporter):
    _model_name = ['woo.sale.order']

    def _import_addresses(self):
        record = self.woo_record
        record = record['order']
        print 'record',record['order']
        self._import_dependency(record['customer_id'],
                                'woo.res.partner')

    def _import_dependencies(self):
        """ Import the dependencies for the record"""
        record = self.woo_record

        self._import_addresses()
        record = record['items']
        print 'record',record['items']

        for line in record:
            _logger.debug('line: %s', line)
            print 'line',line
            if 'product_id' in line:
                self._import_dependency(line['product_id'],
                                        'woo.product.product')

    def _clean_woo_items(self, resource):
        """
        Method that clean the sale order line given by WooCommerce before
        importing it

        This method has to stay here because it allow to customize the
        behavior of the sale order.

        """
        child_items = {}  # key is the parent item id
        top_items = []

        # Group the childs with their parent
        for item in resource['order']['line_items']:
            if item.get('parent_item_id'):
                child_items.setdefault(item['parent_item_id'], []).append(item)
            else:
                top_items.append(item)

        all_items = []
        for top_item in top_items:
            all_items.append(top_item)
        resource['items'] = all_items
        return resource

    def _create(self, data):
        openerp_binding = super(SaleOrderImporter, self)._create(data)
        return openerp_binding

    def _after_import(self, binding):
        """ Hook called at the end of the import """
        return

    def _get_woo_data(self):
        """ Return the raw WooCommerce data for ``self.woo_id`` """
        record = super(SaleOrderImporter, self)._get_woo_data()
        # sometimes we need to clean woo items (ex : configurable
        # product in a sale)
        record = self._clean_woo_items(record)
        return record
SaleOrderImport = SaleOrderImporter


@woo
class SaleOrderImportMapper(SaleOrderImportMapper):
    _model_name = 'woo.sale.order'

    children = [('items', 'woo_order_line_ids', 'woo.sale.order.line'),
                ]

    @mapping
    def status(self, record):
        if record['order']:
            rec = record['order']
            if rec['status']:
                status_id = self.env['woo.sale.order.status'].search(
                    [('name', '=', rec['status'])])
                if status_id:
                    return {'status_id': status_id[0].id}
                else:
                    status_id = self.env['woo.sale.order.status'].create({
                        'name': rec['status']
                    })
                    return {'status_id': status_id.id}
            else:
                return {'status_id': False}

    @mapping
    def order_number(self, record):
        if record['order']:
            rec = record['order']
            if rec['order_number']:
                result= {'name':'wo-'+rec['order_number'],'origin':'wo-'+rec['order_number']}
            return result

    @mapping
    def shipping_methods(self, record):
        ship_obj=self.env['delivery.carrier']
        if record['order']:
            rec = record['order']
            if rec['shipping_methods']:
                result= {'carrier_id':1}
                ship_ids=ship_obj.search([('name','=',rec['shipping_methods'])])
                if ship_ids:
                        ship_id=ship_ids[0]
                else:
                        ship_id=self.backend_record.carrier_id.id                
                result= {'carrier_id':ship_id,
                         'goods_description_id':self.backend_record.goods_description_id.id or None,
                         'carriage_condition_id':self.backend_record.carriage_condition_id.id or None,
                         'transportation_method_id':self.backend_record.transportation_method_id.id or None,
                         'transportation_reason_id':self.backend_record.transportation_reason_id.id or None,
                         'workflow_process_id':self.backend_record.workflow_process_id.id or None,
                         #'payment_method_id':self.backend_record.payment_method_id.id or None
                         }
                return result

    @mapping
    def payment_details(self, record):
        pay_obj=self.env['account.payment.term']
        paymethod_obj=self.env['payment.method']
        if record['order']:
            rec = record['order']
            if rec['payment_details']:
                result= {'payment_term':1}
                for payment_detail in rec['payment_details']: 
                    pay_ids=pay_obj.search([('name','=',payment_detail['method_title'])])
                    if pay_ids:
                        pay_id=pay_ids[0]
                    else:
                        pay_id=pay_obj.create({'name':payment_detail['method_title']})
                    paymethod_ids=paymethod_obj.search([('name','=',payment_detail['method_title'])])
                    if paymethod_ids:
                        paymethod_id=paymethod_ids[0]
                    else:
                        paymethod_id=self.backend_record.payment_method_id.id or None
                    result= {'payment_term':pay_id,'payment_method_id':paymethod_id}
                return result
    @mapping
    def customer_id(self, record):
        if record['order']:
            rec = record['order']
            binder = self.binder_for('woo.res.partner')
            if rec['customer_id']:
                partner_id = binder.to_openerp(rec['customer_id'],
                                               unwrap=True) or False
#               customer_id = str(rec['customer_id'])
                assert partner_id, ("Please Check Customer Role \
                                    in WooCommerce")
                result = {'partner_id': partner_id}
                onchange_val = self.env['sale.order'].onchange_partner_id(
                    partner_id)
                result.update(onchange_val['value'])
            else:
                customer = rec['customer']['billing_address']
                country_id = False
                state_id = False
                if customer['country']:
                    country_id = self.env['res.country'].search(
                        [('code', '=', customer['country'])])
                    if country_id:
                        country_id = country_id.id
                if customer['state']:
                    state_id = self.env['res.country.state'].search(
                        [('code', '=', customer['state'])])
                    if state_id:
                        state_id = state_id.id
                name = customer['first_name'] + ' ' + customer['last_name']
                partner_dict = {
                    'name': name,
                    'city': customer['city'],
                    'phone': customer['phone'],
                    'zip': customer['postcode'],
                    'state_id': state_id,
                    'country_id': country_id
                }
                partner_id = self.env['res.partner'].create(partner_dict)
                partner_dict.update({
                    'backend_id': self.backend_record.id,
                    'openerp_id': partner_id.id,
                })
#                 woo_partner_id = self.env['woo.res.partner'].create(
#                     partner_dict)
                result = {'partner_id': partner_id.id}
                onchange_val = self.env['sale.order'].onchange_partner_id(
                    partner_id.id)
                result.update(onchange_val['value'])
            return result

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}
    

@job(default_channel='root.woo')
def sale_order_import_batch(session, model_name, backend_id, filters=None):
    """ Prepare the import of Sale Order modified on Woo """
    env = get_environment(session, model_name, backend_id)
    importer = env.get_connector_unit(SaleOrderBatchImporter)
    importer.run(filters=filters)
