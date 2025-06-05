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
import socket
from woocommerce import API
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
from openerp.addons.connector.session import ConnectorSession
from datetime import datetime
from openerp.addons.connector.exception import (NetworkRetryableError,
                                                RetryableJobError)
_logger = logging.getLogger(__name__)


class woo_sale_order_status(models.Model):
    _name = 'woo.sale.order.status'
    _description = 'WooCommerce Sale Order Status'

    name = fields.Char('Name')
    desc = fields.Text('Description')
    @api.multi
    def name_get(self):
        result = []
        for id_obj in self:
            result.append((id_obj.id, "%s " % (id_obj.name,)))
        return result


class SaleOrder(models.Model):

    _inherit = 'sale.order'

    status_id = fields.Many2one('woo.sale.order.status',
                                'WooCommerce Order Status')
    woo_sale_order_id = fields.One2many('woo.sale.order','openerp_id',string='woo ordine')
    @api.one
    @api.depends()
    def _default_x_woo_status(self):
        x_woo_status="-"
        for woo_id_obj in self.env['woo.sale.order'].search([('openerp_id','=',self.id)]):
            x_woo_status+=woo_id_obj.status_id.name
        print 'x_woo_status',x_woo_status
        
        return x_woo_status
    x_woo_status = fields.Char(default=_default_x_woo_status, string='woo Status',
         store=True,
         readonly=True,
         compute='_default_x_woo_status',
         
         )
    @api.model
    @api.returns('self', lambda value:value.id)
    def create(self, vals):
        res=models.Model.create(self, vals)
        for woo_id_obj in self.env['woo.sale.order'].search([('openerp_id','=',res.id)]):
            res.write({'status_id':woo_id_obj.status_id.id})
        return res
class WooSaleOrder(models.Model):
    _name = 'woo.sale.order'
    _inherit = 'woo.binding'
    _inherits = {'sale.order': 'openerp_id'}
    _description = 'Woo Sale Order'

    _rec_name = 'name'

    status_id = fields.Many2one('woo.sale.order.status',
                                'WooCommerce Order Status')

    openerp_id = fields.Many2one(comodel_name='sale.order',
                                 string='Sale Order',
                                 required=True,
                                 ondelete='cascade')
    woo_order_line_ids = fields.One2many(
        comodel_name='woo.sale.order.line',
        inverse_name='woo_order_id',
        string='Woo Order Lines'
    )
    backend_id = fields.Many2one(
        comodel_name='wc.backend',
        string='Woo Backend',
        store=True,
        readonly=False,
        required=True,
    )
    @api.multi
    def name_get(self):
        result = []
        for woo_id_obj in self:
            result.append((woo_id_obj.id, "%s %s" % (woo_id_obj.woo_id, woo_id_obj.status_id.name)))
        return result

    @api.model
    @api.returns('self', lambda value:value.id)
    def create(self, vals):
        res=models.Model.create(self, vals)
        for sale_id_obj in self.env['sale.order'].search([('id','=',res.openerp_id.id)]):
            sale_id_obj.write({'status_id':res.status_id.id})
        return res

class WooSaleOrderLine(models.Model):
    _name = 'woo.sale.order.line'
    _inherits = {'sale.order.line': 'openerp_id'}

    woo_order_id = fields.Many2one(comodel_name='woo.sale.order',
                                   string='Woo Sale Order',
                                   required=True,
                                   ondelete='cascade',
                                   select=True)

    openerp_id = fields.Many2one(comodel_name='sale.order.line',
                                 string='Sale Order Line',
                                 required=True,
                                 ondelete='cascade')

    backend_id = fields.Many2one(
        related='woo_order_id.backend_id',
        string='Woo Backend',
        readonly=True,
        store=True,
        required=False,
    )

    @api.model
    def create(self, vals):
        woo_order_id = vals['woo_order_id']
        binding = self.env['woo.sale.order'].browse(woo_order_id)
        vals['order_id'] = binding.openerp_id.id
        binding = super(WooSaleOrderLine, self).create(vals)
        return binding


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    woo_bind_ids = fields.One2many(
        comodel_name='woo.sale.order.line',
        inverse_name='openerp_id',
        string="WooCommerce Bindings",
    )

class WooSaleOrder_update(models.TransientModel):
    _name = 'woo.sale.order.update'
    _description = 'Woo Sale Order'
    name=fields.Char('Name')
    status_id = fields.Many2one('woo.sale.order.status',
                                'WooCommerce Order Status', required=True,)
    @api.multi
    def update_order_batch(self):
        session = ConnectorSession(self.env.cr, self.env.uid,
                                   context=self.env.context)
        woo_sale_obj=self.env['woo.sale.order']
        backend_obj=self.env['wc.backend']
        print 'update_order', self.status_id.name
        print 'update_order_session', session
        for backend_id_obj in backend_obj.search([('id','>',0)]):
            woo_sale_ids_obj=woo_sale_obj.search([('openerp_id','in',tuple(active_ids))])
            print 'woo_sale_ids_obj',woo_sale_ids_obj
            for woo_sale_id_obj in woo_sale_ids_obj:
                print 'update_order_woo_sale_id_objwoo_id', woo_sale_id_obj.woo_id
                print 'update_order_woo_sale_id_objstatus_id', self.status_id.name.encode('utf8')
    
                sale_order_update_batch.delay(
                    session, 
                    'woo.sale.order',   
                    backend_id_obj.id,
                    woo_sale_id_obj.woo_id,
                    {'status': self.status_id.name.encode('utf8')}, 
                    priority=4
                    )
                woo_sale_id_obj.write({'status_id':self.status_id.id})
                woo_sale_id_obj.openerp_id.write({'status_id':self.status_id.id})

        return True
    @api.multi
    def update_order(self):

        woo_sale_obj=self.env['woo.sale.order']#
        backend_obj=self.env['wc.backend']
        print 'update_order'
        for backend_id_obj in backend_obj.search([('id','>',0)]):
            wcapi = API(
                url=backend_id_obj.https_location,
                consumer_key=backend_id_obj.consumer_key,
                consumer_secret=backend_id_obj.consumer_secret,
                wp_api=True,
                version=backend_id_obj.https_version,
                query_string_auth=backend_id_obj.https_query_string_auth,
                verify_ssl=backend_id_obj.https_verify_ssl
            )
            print 'update_orderbackend_id_obj',backend_id_obj.id,self.env.context.get('active_ids')
            active_ids=self.env.context.get('active_ids',[])
            print 'active_ids',active_ids,tuple(active_ids)
            woo_sale_ids_obj=woo_sale_obj.search([('openerp_id','in',tuple(active_ids))])
            print 'woo_sale_ids_obj',woo_sale_ids_obj
            for woo_sale_id_obj in woo_sale_ids_obj:
                print 'woo_id', woo_sale_id_obj.woo_id
                data={'status': str(self.status_id.name)}
                print 'data', data
                my_put="orders/%s" % (woo_sale_id_obj.woo_id,)
                print 'my_put',my_put
                result=wcapi.put(my_put, data).json()
                print result
                woo_sale_id_obj.write({'status_id':self.status_id.id})
                woo_sale_id_obj.openerp_id.write({'status_id':self.status_id.id})
                #data = {"status": "completed"}
                #print(wcapi.put("orders/8884", data).json())
        return True
    

@woo
class SaleOrderLineImportMapper(ImportMapper):
    _model_name = 'woo.sale.order.line'

    direct = [('quantity', 'product_uom_qty'),
              ('quantity', 'product_uos_qty'),
              ('name', 'name'),
              ('price', 'price_unit')
              ]

    """ rocco 04_09_2017
    #@mapping
    def product_id(self, record):
        binder = self.binder_for('woo.product.product')
        product_id = binder.to_openerp(record['product_id'], unwrap=True)
        assert product_id is not None, (
            "product_id %s should have been imported in "
            "SaleOrderImporter._import_dependencies" % record['product_id'])
        return {'product_id': product_id}
    """ 
    @mapping
    def product_id(self, record):
        print 'product_id'
        binder = self.binder_for('woo.product.product')
        product_id = binder.to_openerp(record['product_id'], unwrap=True)
        if record.get('sku',None)!='TRASPORTO':
            assert product_id is not None, (
                "product_id %s should have been imported in "
                "SaleOrderImporter._import_dependencies" % record['product_id'])
        product_ids_obj=self.env['product.product'].search([('id','=',product_id)])
        if product_ids_obj:
            if product_ids_obj[0].taxes_id:
                tax_id=product_ids_obj[0].taxes_id[0].id
            else:
                tax_id=None            
        if record.get('sku',None)=='TRASPORTO':
            product_id=self.backend_record.delivery_product_id.id
            tax_id=self.backend_record.wholesale_tax_id.id
        return {'product_id': product_id,'tax_id':[(6, 0, [self.backend_record.tax_id.id or tax_id  ])],
}    

@woo
class SaleOrderAdapter(GenericAdapter):
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

    def _call_put(self, woo_model,woo_id,data):
        try:
            _logger.debug("Start put Woocommerce api %s", woo_model)
            api = API(url=self.woo.https_location,
                      consumer_key=self.woo.consumer_key,
                      consumer_secret=self.woo.consumer_secret,
                      wp_api=True,
                      version=self.woo.https_version,
                      verify_ssl=self.woo.https_verify_ssl,
                      query_string_auth=self.woo.https_query_string_auth,
                      )
            if api:
                start = datetime.now()
                try:
                    print '_call_put',woo_model,id
                    result=api.put("%s/%s" % ('orders',woo_id), data).json()
                    print '_call_put_result',result
                except:
                    _logger.error("api.put(%s/%s) failed", 'orders', woo_id)
                    raise
                else:
                    _logger.debug("api.call(%s, %s) returned %s in %s seconds",
                                  woo_model, woo_id, result,
                                  (datetime.now() - start).seconds)
                return result
        except (socket.gaierror, socket.error, socket.timeout) as err:
            raise NetworkRetryableError(
                'A network error caused the failure of the job: '
                '%s' % err)
        except xmlrpclib.ProtocolError as err:
            if err.errcode in [502,   # Bad gateway
                               503,   # Service unavailable
                               504]:  # Gateway timeout
                raise RetryableJobError(
                    'A protocol error caused the failure of the job:\n'
                    'URL: %s\n'
                    'HTTP/HTTPS headers: %s\n'
                    'Error code: %d\n'
                    'Error message: %s\n' %
                    (err.url, err.headers, err.errcode, err.errmsg))
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

    def put(self, woo_id, data):
        """ Update records on the external system """
        #wcapi.put("orders/8883", data).json())
        return self._call_put(self._woo_model,woo_id, data)
@woo
class SaleOrderBatchImporter(DelayedBatchImporter):

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
class SaleOrderImporter(WooImporter):
    _model_name = ['woo.sale.order']

    def _import_addresses(self):
        record = self.woo_record
        record = record['order']
        self._import_dependency(record['customer_id'],
                                'woo.res.partner')

    def _import_dependencies(self):
        """ Import the dependencies for the record"""
        record = self.woo_record

        self._import_addresses()
        record = record['items']
        for line in record:
            _logger.debug('line: %s', line)
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
        print '_clean_woo_items',resource
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
class SaleOrderImportMapper(ImportMapper):
    _model_name = 'woo.sale.order'

    children = [('items', 'woo_order_line_ids', 'woo.sale.order.line'),
                ]


        
    @property
    def source(self):
        """ Source record to be converted """
        print 'self._source_00',self._source
        if self.__source.get('order',None):
            if self.__source.get('order_number',None)==None:
                self.__source.update({'order_number':None})
            
            if self.__source.get('id',None)==None:
                self.__source.update({'id':None})
            
            if self.__source.get('payment_details',None)==None:
                self.__source.update({'payment_details':None})
            
            if self.__source.get('shipping_methods',None)==None:
                self.__source.update({'shipping_methods':None})
            
            if self.__source.get('view_order_url',None)==None:
                self.__source.update({'view_order_url':'view_order_url'})
            
            if self.__source.get('customer_ip',None)==None:
                self.__source.update({'customer_ip':'customer_ip'})
        
        print 'self._source_001',self._source
        return self._source

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
        #import pdb; pdb.set_trace()
        if record['order']:
            rec = record['order']
            if rec['order_number']:
                result= {'name':'wo-'+rec['order_number']}
                return result
    @mapping
    def id(self, record):
        #import pdb; pdb.set_trace()
        if record['order']:
            rec = record['order']
            if rec['id']:
                result= {'origin':'wo-'+rec['order_number']}
                return result
 
    @mapping
    def payment_details(self, record):
        pay_obj=self.env['account.payment.term']
        #import pdb; pdb.set_trace()
        if record['order']:
            rec = record['order']
            if rec['payment_details']:
                result= {'payment_term':1}
                print 'payment_detail.spayment_details',rec['payment_details']
                #_logger.debug('payment_details: %s', rec['payment_details'],)
                payment_detail=rec['payment_details']['method_title']
                pay_ids_obj=pay_obj.search([('name','=',payment_detail)])
                if pay_ids_obj:
                        pay_id=pay_ids_obj[0].id
                        print 'esitente.pay_id',pay_id

                else:
                    pay_id_obj=pay_ids_obj.create({'name':payment_detail})
                    pay_id=pay_id_obj.id
                    print 'non_esitente.pay_id',pay_id
                print 'payment_term',pay_id
                result= {'payment_term':pay_id}
                return result
    @mapping
    def shipping_methods(self, record):
        ship_obj=self.env['delivery.carrier']
        print 'mapping_shipping_methods'
        if record['order']:
            rec = record['order']
            print 'shipping_methods',rec.get('shipping_methods','errore')
            if rec['shipping_methods']:
                result= {'carrier_id':1}
                ship_ids_obj=ship_obj.search([('name','=',rec['shipping_methods'])])
                if ship_ids_obj:
                        ship_id=ship_ids_obj[0].id
                else:
                        ship_id=self.backend_record.carrier_id.id                
                result= {'carrier_id':ship_id,
                         #'goods_description_id':self.backend_record.goods_description_id.id or None,
                         #'carriage_condition_id':self.backend_record.carriage_condition_id.id or None,
                         #'transportation_method_id':self.backend_record.transportation_method_id.id or None,
                         #'transportation_reason_id':self.backend_record.transportation_reason_id.id or None,
                         #'workflow_process_id':self.backend_record.workflow_process_id.id or None,
                         #'payment_method_id':self.backend_record.payment_method_id.id or None
                         }
                result.update({
                             'goods_description_id':self.backend_record.goods_description_id.id ,#or None,
                             'carriage_condition_id':self.backend_record.carriage_condition_id.id ,#or None,
                             'transportation_method_id':self.backend_record.transportation_method_id.id ,#or None,
                             'transportation_reason_id':self.backend_record.transportation_reason_id.id ,#or None,
                               })

                if record['order']['customer'].get('role',None):
                                 if record['order']['customer'].get('role',None)=='wholesale_customer':
                                     result.update({'pricelist_id':self.backend_record.pricelist_id.id })
                print 'mapping_shipping_methods_result',result

                return result
    @mapping
    def view_order_url(self, record):
        #import pdb; pdb.set_trace()
        paymethod_obj=self.env['payment.method']
        print 'mapping_view_order_url'
        if record['order']:
            rec = record['order']
            if rec['view_order_url']:
                result= {'payment_method_id':1}
                payment_detail=rec['payment_details']['method_title']
                print 'view_order_url.spayment_details',rec['payment_details']
                paymethod_ids_obj=paymethod_obj.search([('name','=',payment_detail)])
                if paymethod_ids_obj:
                        paymethod_id=paymethod_ids_obj[0].id
                else:
                        paymethod_id=self.backend_record.payment_method_id.id or None
                result= {'payment_method_id':paymethod_id}
                return result
    @mapping
    def customer_ip(self, record):
        #import pdb; pdb.set_trace()
        workflow_process_obj=self.env['sale.workflow.process']
        paymethod_obj=self.env['payment.method']
        print 'mapping_billing_address'
        if record['order']:
            rec = record['order']
            if rec['payment_details']:
                result= {'workflow_process_id':self.backend_record.workflow_process_id.id}
                payment_detail=rec['payment_details']['method_title']
                paymethod_ids_obj=paymethod_obj.search([('name','=',payment_detail)])
                if paymethod_ids_obj:
                        workflow_process_id=paymethod_ids_obj[0].workflow_process_id.id or None
                else:
                        workflow_process_id=self.backend_record.workflow_process_id.id or None
                result= {'workflow_process_id':workflow_process_id}
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
                        [('code', '=', customer['state']),('country_id', '=', country_id)])
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
                result.update({
                               
                               })
                """
                if rec['order_number']:
                    result['name']='wo-'+rec['order_number']
                    result['origin']='wo-'+rec['order_number']
                ship_obj=self.env['delivery.carrier']
                if rec['shipping_methods']:
                    result['carrier_id']=1
                    ship_ids=ship_obj.search([('name','=',rec['shipping_methods'])])
                    if ship_ids:
                            ship_id=ship_ids[0]
                    else:
                            ship_id=self.backend_record.carrier_id.id                
                    result['carrier_id']=ship_id,
                    result['goods_description_id']=self.backend_record.goods_description_id.id or None
                    result['carriage_condition_id']=self.backend_record.carriage_condition_id.id or None
                    result['transportation_method_id']=self.backend_record.transportation_method_id.id or None
                    result['transportation_reason_id']=self.backend_record.transportation_reason_id.id or None
                    result['workflow_process_id']=self.backend_record.workflow_process_id.id or None
                pay_obj=self.env['account.payment.term']
                paymethod_obj=self.env['payment.method']
                if rec['payment_details']:
                    result['payment_term']=1
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
                        result['payment_term']=pay_id
                        result['payment_method_id']=paymethod_id
                             #'payment_method_id':self.backend_record.payment_method_id.id or None
                """            

            return result

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}


@job(default_channel='root.woo')
def sale_order_import_batch(session, model_name, backend_id, filters=None):
    """ Prepare the import of Sale Order modified on Woo """
    print 'sale_order_import_batch'
    env = get_environment(session, model_name, backend_id)
    print 'sale_order_import_batch_01'
    importer = env.get_connector_unit(SaleOrderBatchImporter)
    print 'sale_order_import_batch_02'
    importer.run(filters=filters)

@job(default_channel='root.woo')
def sale_order_update_batch(session, model_name, backend_id, id,data):
    """ Prepare the update  of Sale Order modified on odoo """
    print 'sale_order_update_batch'
    env = get_environment(session, model_name, backend_id)
    print 'sale_order_update_batch_01'
    woo_order_upd = env.get_connector_unit(SaleOrderAdapter)
    print 'sale_order_update_batch_02'
    woo_order_upd.put(id,data)
