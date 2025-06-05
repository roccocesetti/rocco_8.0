# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
##############################################################################
from openerp.tools.translate import _
import base64
from tempfile import TemporaryFile

from openerp import tools
from openerp.osv import osv, fields, expression
from lxml import etree
import openerp.pooler as pooler
import openerp.sql_db as sql_db
from datetime import datetime, timedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
from openerp import netsvc
import openerp.addons.decimal_precision as dp
import xxsubtype
import itertools
from lxml import etree
from openerp import api,models
from openerp import SUPERUSER_ID
import tempfile
import csv
from string import strip
from openerp.tools.misc import ustr
import requests
import json

try:
    import xlwt
except ImportError:
    xlwt = None
try:
    import xlrd
except ImportError:
    xlrd = None
try:
    from xlrd import xlsx
except ImportError:
    xlr = None
import os, sys
import time
import urllib2 
import urllib
import httplib2
import sys, httplib
from requests import Request as Session
from requests.auth import HTTPBasicAuth
import requests
class product_template(osv.osv):
    _inherit = "product.template"
    _columns = {
        'x_imb_x': fields.float('Lunghezza', digits_compute=dp.get_precision('Product Price'),required=False),
        'x_imb_y': fields.float('Altezza', digits_compute=dp.get_precision('Product Price'),required=False),
        'x_imb_z': fields.float('Profondità', digits_compute=dp.get_precision('Product Price'),required=False),

    }
    def create_variant_ids(self, cr, uid, ids, context=None):
        res=super(product_template, self).create_variant_ids(cr, uid, ids, context=context)
        if res:
            tmpl_ids = self.browse(cr, uid, ids, context=context)
            product_obj = self.pool.get("product.product")
            for tmpl_id in tmpl_ids:
    
                # list of values combination
                for variant_id in tmpl_id.product_variant_ids:
                    if variant_id.standard_price==0:
                            product_obj.write(cr,uid,variant_id.id,{'standard_price':tmpl_id.standard_price})

        return res
    def onchange_dim(self, cr, uid, ids, x_imb_x=0, x_imb_y=0,x_imb_z=0, context=None):
        """ Changes UoM if product_id changes.
        @param x_imb_x: x_imb_y x_imb_z
        @return:  Dictionary of changed values
        """
        res = {}
        res['value'] = {
                'volume': x_imb_x*x_imb_y*x_imb_z,
            }
        return res
class product_product(osv.osv):
    _inherit = "product.product"
    _columns = {
        'standard_price': fields.property(type = 'float', digits_compute=dp.get_precision('Product Price'), 
                                          help="Cost price of the product template used for standard stock valuation in accounting and used as a base price on purchase orders. "
                                               "Expressed in the default unit of measure of the product.",
                                          groups="base.group_user", string="Cost Price"),
        'x_imb_x': fields.float('Lunghezza', digits_compute=dp.get_precision('Product Price'),required=False),
        'x_imb_y': fields.float('Altezza', digits_compute=dp.get_precision('Product Price'),required=False),
        'x_imb_z': fields.float('Profondità', digits_compute=dp.get_precision('Product Price'),required=False),
        'volume': fields.float('Volume', help="The volume in m3."),

     }
    @api.model
    @api.returns('self', lambda value:value.id)
    def create(self, vals):
        if hasattr(self._ids, '__iter__'):
            if self._ids:
                for myself in self:#0000000
                        if vals.get('standard_price',0)<=0:
                            vals['standard_price']=myself.product_tmpl_id.standard_price
                        if vals.get('x_imb_x',0)<=0:
                            vals['x_imb_x']=myself.product_tmpl_id.x_imb_x
                        if vals.get('x_imb_y',0)<=0:
                            vals['x_imb_y']=myself.product_tmpl_id.x_imb_y
                        if vals.get('x_imb_z',0)<=0:
                            vals['x_imb_z']=myself.product_tmpl_id.x_imb_z
                        if vals.get('volume',0)<=0:
                            vals['volume']=myself.product_tmpl_id.x_imb_z*myself.product_tmpl_id.x_imb_y*myself.product_tmpl_id.x_imb_x
            else:
                        if vals.get('standard_price',0)<=0:
                            vals['standard_price']=self.product_tmpl_id.standard_price
                        if vals.get('x_imb_x',0)<=0:
                            vals['x_imb_x']=self.product_tmpl_id.x_imb_x
                        if vals.get('x_imb_y',0)<=0:
                            vals['x_imb_y']=self.product_tmpl_id.x_imb_y
                        if vals.get('x_imb_z',0)<=0:
                            vals['x_imb_z']=self.product_tmpl_id.x_imb_z
                        if vals.get('volume',0)<=0:
                            vals['volume']=self.product_tmpl_id.x_imb_z*self.product_tmpl_id.x_imb_y*self.product_tmpl_id.x_imb_x
                
        else:
                    if vals.get('standard_price',0)<=0:
                        vals['standard_price']=self.product_tmpl_id.standard_price
                    if vals.get('x_imb_x',0)<=0:
                            vals['x_imb_x']=self.product_tmpl_id.x_imb_x
                    if vals.get('x_imb_y',0)<=0:
                            vals['x_imb_y']=self.product_tmpl_id.x_imb_y
                    if vals.get('x_imb_z',0)<=0:
                            vals['x_imb_z']=self.product_tmpl_id.x_imb_z
                    if vals.get('volume',0)<=0:
                            vals['volume']=self.product_tmpl_id.x_imb_z*self.product_tmpl_id.x_imb_y*self.product_tmpl_id.x_imb_x
        res=super(product_product, self).create(vals=vals)
        return res
    @api.multi
    def write(self, vals):
        if hasattr(self._ids, '__iter__'):
            if self._ids:
                for myself in self:
                   if vals.get('standard_price',None)==None:
                        if myself.standard_price:
                            vals['standard_price']=myself.standard_price
                        else:
                                vals['standard_price']=myself.product_tmpl_id.standard_price
                   if vals.get('x_imb_x',0)<=0:
                            vals['x_imb_x']=myself.product_tmpl_id.x_imb_x
                   if vals.get('x_imb_y',0)<=0:
                            vals['x_imb_y']=myself.product_tmpl_id.x_imb_y
                   if vals.get('x_imb_z',0)<=0:
                            vals['x_imb_z']=myself.product_tmpl_id.x_imb_z
                   if vals.get('volume',0)<=0:
                            vals['volume']=myself.product_tmpl_id.x_imb_z*myself.product_tmpl_id.x_imb_y*myself.product_tmpl_id.x_imb_x
                
            else:
                    if vals.get('standard_price',None)==None:
                        if self.standard_price:
                            vals['standard_price']=self.standard_price
                        else:
                                vals['standard_price']=self.product_tmpl_id.standard_price
                    if vals.get('x_imb_x',0)<=0:
                            vals['x_imb_x']=self.product_tmpl_id.x_imb_x
                    if vals.get('x_imb_y',0)<=0:
                            vals['x_imb_y']=self.product_tmpl_id.x_imb_y
                    if vals.get('x_imb_z',0)<=0:
                            vals['x_imb_z']=self.product_tmpl_id.x_imb_z
                    if vals.get('volume',0)<=0:
                            vals['volume']=self.product_tmpl_id.x_imb_z*self.product_tmpl_id.x_imb_y*self.product_tmpl_id.x_imb_x
                
        else:
            if vals.get('standard_price',None)==None:
                        if self.standard_price:
                            vals['standard_price']=self.standard_price
                        else:
                                vals['standard_price']=self.product_tmpl_id.standard_price
            if vals.get('x_imb_x',0)<=0:
                            vals['x_imb_x']=self.product_tmpl_id.x_imb_x
            if vals.get('x_imb_y',0)<=0:
                            vals['x_imb_y']=self.product_tmpl_id.x_imb_y
            if vals.get('x_imb_z',0)<=0:
                            vals['x_imb_z']=self.product_tmpl_id.x_imb_z
            if vals.get('volume',0)<=0:
                            vals['volume']=self.product_tmpl_id.x_imb_z*self.product_tmpl_id.x_imb_y*self.product_tmpl_id.x_imb_x
        res=super(product_product, self).write(vals)
        return res
    def onchange_dim(self, cr, uid, ids, x_imb_x=0, x_imb_y=0,x_imb_z=0, context=None):
        """ Changes UoM if product_id changes.
        @param x_imb_x: x_imb_y x_imb_z
        @return:  Dictionary of changed values
        """
        res = {}
        res['value'] = {
                'volume': x_imb_x*x_imb_y*x_imb_z,
            }
        return res


class delivery_carrier_tnt(osv.osv):
    _name = 'delivery.carrier.tnt'
    _description = 'Url carrier'

    _columns = {
        'name':fields.char('Name', size=64, required=True, readonly=False),
        'active':fields.boolean('Active', required=False), 
        'seq': fields.integer('Sequenza di ricerca'), 
        'url':fields.char('url', size=256, required=True, readonly=False),
        'customer':fields.char('Customer', size=64, required=True, readonly=False),
        'user':fields.char('Utente', size=64, required=True, readonly=False),
        'password':fields.char('Password', size=64, required=True, readonly=False),
        'langid':fields.char('langid', size=64, required=True, readonly=False),
        'application':fields.char('application', size=128, required=True, readonly=False),
        'consignmentaction':fields.char('consignmentaction', size=128, required=True, readonly=False),
        'senderAccId':fields.char('senderAccId', size=128, required=True, readonly=False),
        'consignmenttype':fields.char('consignmenttype', size=128, required=True, readonly=False),
        'packagetype':fields.char('packagetype', size=128, required=True, readonly=False),
        'division':fields.char('division', size=128, required=True, readonly=False),
        'product':fields.char('product', size=128, required=True, readonly=False),
        'termsofpayment':fields.char('termsofpayment', size=128, required=True, readonly=False),
        'systemcode':fields.char('systemcode', size=128, required=True, readonly=False),
        'systemversion':fields.char('systemversion', size=128, required=True, readonly=False),
        'addressType':fields.char('addressType', size=128, required=True, readonly=False),
        'product':fields.selection([
('AU','Automotive'),
('BB','Biological Substance Cat. B'),
('DI','Dry Ice'),
('ES','Enhanced Security Program'),
('FD','US Food & Drug Administration'),
('HZ','Hazardous Goods'),
('IN','Insurance'),
('LB','Excepted Lithium Batteries'),
('LQ','Hazardous (Limited Quantity)'),
('PR','Priority'),
('SA','Saturday Delivery'),
('TD','Time Definite'),
('ESP','Enhanced Security Program'),
('FDA','US Food & Drug Administration'),
('IN','Insurance'),
('IN','Insurance'),
('PR','Priority'),
('SA','Saturday Delivery'),
('TD','Time Definite'),
('AU','Automotive'),
('BB','Biological Substance Cat. B'),
('CL','Central Clearance'),
('DI','Dry Ice'),
('ESP','Enhanced Security Program'),
('FDA','US Food & Drug Administration'),
('HZ','Hazardous Goods'),
('IN','Insurance'),
('LB','Excepted Lithium Batteries'),
('PP','Prepaid'),
('PR','Priority'),
('SA','Saturday Delivery'),
('TD','Time Definite'),
('IN','Insurance'),
('BB','Biological Substance Cat. B'),
('CL','Central Clearance'),
('ESP','Enhanced Security Program'),
('FDA','US Food & Drug Administration'),
('IN','Insurance'),
('LB','Excepted Lithium Batteries'),
('SA','Saturday Delivery'),
('IN','Insurance'),
             ],    
'Prodotti', select=True, readonly=True),
        'option':fields.selection([
('0','Consegna all’indirizzo'),
('1','Fermo deposito TNT'),
('2','Fermo Deposito TNT Point'),
('3','Consegna Programmata'),
('6','Reso in Locker Box'),
             ],    'Opzioni', select=True, readonly=True),

    }
class delivery_carrier_tnt_tx_rx(osv.osv_memory):
    _name = 'delivery.carrier.tnt.tx.rx'
    _description = 'tx sale'
    def _default_carrier_tnt(self, cr, uid, context=None):
        #self.search(cr, user, args, offset, limit, order, context, count)
        return self.pool.get('delivery.carrier.tnt').search(cr, uid, [('active', '=', True)],order='seq',context=context)[0]
    
    _columns = {
        'name':fields.char('Name', size=64, required=True, readonly=False),
        'carrier_tnt_id':fields.many2one('delivery.carrier.tnt', 'Url di Trasmissione', required=False), 
    }
    _defaults = {  
        'name':  lambda *a: 'tx-' + time.strftime('%Y-%m-%d') ,  
        'carrier_tnt_id': _default_carrier_tnt,
        }
    def json2xml(self,json_obj, line_padding=""):
        result_list = list()
    
        json_obj_type = type(json_obj)
    
        if json_obj_type is list:
            for sub_elem in json_obj:
                result_list.append(json2xml(sub_elem, line_padding))
    
            return "\n".join(result_list)
    
        if json_obj_type is dict:
            for tag_name in json_obj:
                sub_obj = json_obj[tag_name]
                result_list.append("%s<%s>" % (line_padding, tag_name))
                result_list.append(json2xml(sub_obj, "\t" + line_padding))
                result_list.append("%s</%s>" % (line_padding, tag_name))
    
            return "\n".join(result_list)
    
        return "%s%s" % (line_padding, json_obj)
    @api.multi
    def delivery_tx(self):
        def send_request(url,request):
            date_today=datetime.today()
            if url:
               http = httplib2.Http()
                #body = {'USERNAME': 'foo', 'PASSWORD': 'bar'}
               body = {'xml': request}
               headers = {'Content-type': 'application/x-www-form-urlencoded'}
               hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
       'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
       'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
       'Accept-Encoding': 'none',
       'Accept-Language': 'en-US,en,it-IT,it;q=0.8',
       'Connection': 'keep-alive'}
               try: 
                print 'body-->',body
                if str(url).find('https')>=0:
                    http = httplib2.Http("/home/rocco/.cache", disable_ssl_certificate_validation=True)
                response, content = http.request(url, 'POST', headers=headers, body=urllib.urlencode(body))
               except:
                         response={'status':500}
                         content={}
               if response:
                    print 'response-->',response
                    if response.status!=200:
                            print 'response_error-->',response
                            return False
                    else:
                            return  True             
               else:
                            return  False             
        date_today=datetime.today()
        db_name = cr.dbname
        pool = pooler.get_pool(db_name)
        sale_obj = self.env['sale.order']
        tnt_obj = self.env['delivery.carrier.tnt']
        active_ids=self.env.context.get('active_ids', [])
        carrier_tnt_id=_default_carrier_tnt
        carrier_tnt_id_obj=tnt_obj.browse(carrier_tnt_id)
        
        for sale_id_obj in sale_obj.browse(active_ids):
                    tnt_tx=self.init_json()
                    tnt_tx['shipment']['software']['application']=carrier_tnt_id_obj.application
                    tnt_tx['shipment']['software']['version']=carrier_tnt_id_obj.version
                    tnt_tx['shipment']['security']['customer']=carrier_tnt_id_obj.customer
                    tnt_tx['shipment']['security']['user']=carrier_tnt_id_obj.user
                    tnt_tx['shipment']['security']['password']=carrier_tnt_id_obj.password
                    tnt_tx['shipment']['security']['langid']=carrier_tnt_id_obj.langid
                    tnt_tx['shipment']['consignment']['laroseDepot']=carrier_tnt_id_obj.application
                    tnt_tx['shipment']['consignment']['senderAccId']=carrier_tnt_id_obj.application
                    tnt_tx['shipment']['consignment']['consignmentno']=sale_id_obj.name
                    tnt_tx['shipment']['consignment']['consignmenttype']='C'
                    tnt_tx['shipment']['consignment']['CollectionTrg']['priopntime']=carrier_tnt_id_obj.application
                    tnt_tx['shipment']['consignment']['CollectionTrg']['priclotime']=carrier_tnt_id_obj.application
                    tnt_tx['shipment']['consignment']['CollectionTrg']['secopntime']=carrier_tnt_id_obj.application
                    tnt_tx['shipment']['consignment']['CollectionTrg']['availabilitytime']=carrier_tnt_id_obj.application
                    tnt_tx['shipment']['consignment']['CollectionTrg']['pickupdate']=carrier_tnt_id_obj.application
                    tnt_tx['shipment']['consignment']['CollectionTrg']['pickuptime']=carrier_tnt_id_obj.application
                    tnt_tx['shipment']['consignment']['CollectionTrg']['pickupinstr']=carrier_tnt_id_obj.application
                    tnt_tx['shipment']['consignment']['actualweight']=carrier_tnt_id_obj.application
                    tnt_tx['shipment']['consignment']['actualvolume']=carrier_tnt_id_obj.application
                    tnt_tx['shipment']['consignment']['totalpackages']=carrier_tnt_id_obj.application
                    tnt_tx['shipment']['consignment']['packagetype']=carrier_tnt_id_obj.application
                    tnt_tx['shipment']['consignment']['division']=carrier_tnt_id_obj.application
                    tnt_tx['shipment']['consignment']['product']=carrier_tnt_id_obj.application
                    tnt_tx['shipment']['consignment']['vehicle']=carrier_tnt_id_obj.application
                    tnt_tx['shipment']['consignment']['insurancevalue']=carrier_tnt_id_obj.application
                    tnt_tx['shipment']['consignment']['insurancecurrency']=carrier_tnt_id_obj.application
                    tnt_tx['shipment']['consignment']['packingdesc']=carrier_tnt_id_obj.application
                    tnt_tx['shipment']['consignment']['reference']=carrier_tnt_id_obj.application
                    tnt_tx['shipment']['consignment']['collectiondate']=carrier_tnt_id_obj.application
                    tnt_tx['shipment']['consignment']['collectiontime']=carrier_tnt_id_obj.application
                    tnt_tx['shipment']['consignment']['invoicevalue']=carrier_tnt_id_obj.application
                    tnt_tx['shipment']['consignment']['invoicecurrency']=carrier_tnt_id_obj.application
                    tnt_tx['shipment']['consignment']['options']['option']=carrier_tnt_id_obj.application
                    tnt_tx['shipment']['consignment']['termsofpayment']=carrier_tnt_id_obj.application
                    tnt_tx['shipment']['consignment']['specialinstructions']=carrier_tnt_id_obj.application
                    tnt_tx['shipment']['consignment']['systemcode']=carrier_tnt_id_obj.application
                    tnt_tx['shipment']['consignment']['systemversion']=carrier_tnt_id_obj.application
                    tnt_tx['shipment']['consignment']['addresses']['address']['addressType']='S'
                    tnt_tx['shipment']['consignment']['addresses']['address']['vatno']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['addrline1']=sale_id_obj.company_id.partner_id.street
                    tnt_tx['shipment']['consignment']['addresses']['address']['addrline2']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['addrline3']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['phone1']=sale_id_obj.company_id.partner_id.phone
                    tnt_tx['shipment']['consignment']['addresses']['address']['phone2']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['postcode']=sale_id_obj.company_id.partner_id.zip
                    tnt_tx['shipment']['consignment']['addresses']['address']['name']=sale_id_obj.company_id.partner_id.name
                    tnt_tx['shipment']['consignment']['addresses']['address']['country']=sale_id_obj.company_id.partner_id.country_id.code
                    tnt_tx['shipment']['consignment']['addresses']['address']['town']=sale_id_obj.company_id.partner_id.city
                    tnt_tx['shipment']['consignment']['addresses']['address']['province']=sale_id_obj.company_id.partner_id.state_id.code
                    tnt_tx['shipment']['consignment']['addresses']['address']['custcountry']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['address']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['address']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['addressType']='D'
                    tnt_tx['shipment']['consignment']['addresses']['address']['vatno']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['addrline1']=sale_id_obj.partner_id.street
                    tnt_tx['shipment']['consignment']['addresses']['address']['addrline2']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['addrline3']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['phone1']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['phone2']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['postcode']=sale_id_obj.partner_id.zip
                    tnt_tx['shipment']['consignment']['addresses']['address']['name']=sale_id_obj.partner_id.name
                    tnt_tx['shipment']['consignment']['addresses']['address']['country']=sale_id_obj.partner_id.country_id.code
                    tnt_tx['shipment']['consignment']['addresses']['address']['town']=sale_id_obj.partner_id.city
                    tnt_tx['shipment']['consignment']['addresses']['address']['province']=sale_id_obj.partner_id.state_id.code
                    tnt_tx['shipment']['consignment']['addresses']['address']['custcountry']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['address']=sale_id_obj.partner_id.street
                    tnt_tx['shipment']['consignment']['addresses']['address']['address']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['addressType']='R'
                    tnt_tx['shipment']['consignment']['addresses']['address']['vatno']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['addrline1']=carrier_tnt_id_obj.application
                    tnt_tx['shipment']['consignment']['addresses']['address']['addrline2']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['addrline3']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['phone1']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['phone2']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['postcode']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['name']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['country']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['town']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['province']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['custcountry']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['address']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['address']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['addressType']='C'
                    tnt_tx['shipment']['consignment']['addresses']['address']['vatno']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['addrline1']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['addrline2']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['addrline3']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['phone1']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['phone2']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['postcode']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['name']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['country']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['town']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['province']=''
                    tnt_tx['shipment']['consignment']['addresses']['address']['custcountry']=''
                    tnt_tx['shipment']['consignment']['dimensions']['itemsequenceno']=''
                    tnt_tx['shipment']['consignment']['dimensions']['itemtype']=''
                    tnt_tx['shipment']['consignment']['dimensions']['itemreference']=''
                    tnt_tx['shipment']['consignment']['dimensions']['volume']=''
                    tnt_tx['shipment']['consignment']['dimensions']['weight']=''
                    tnt_tx['shipment']['consignment']['dimensions']['length']=''
                    tnt_tx['shipment']['consignment']['dimensions']['height']=''
                    tnt_tx['shipment']['consignment']['dimensions']['width']=''
                    tnt_tx['shipment']['consignment']['dimensions']['quantity']=''
                    tnt_tx['shipment']['consignment']['articles']['tariff']=''
                    tnt_tx['shipment']['consignment']['articles']['origcountry']=''
                    #print 'conta-->',conta,'request-->',request
                    if conta>0:
                        send_request(site_ids.name_site,request,context)
        return True
    def init_json(self):
        return {
  "xsd:schema": {
    "-xmlns:xsd": "http://www.w3.org/2001/XMLSchema",
    "xsd:annotation": { "xsd:documentation": "Schema: routing label Version: 1.0" },
    "xsd:element": {
      "-name": "shipment",
      "xsd:complexType": {
        "xsd:sequence": {
          "xsd:element": [
            {
              "-name": "software",
              "xsd:complexType": {
                "xsd:sequence": {
                  "xsd:element": [
                    {
                      "-name": "application",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:string",
                          "xsd:minLength": { "-value": "1" },
                          "xsd:maxLength": { "-value": "5" }
                        }
                      }
                    },
                    {
                      "-name": "version",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:string",
                          "xsd:minLength": { "-value": "1" },
                          "xsd:maxLength": { "-value": "10" }
                        }
                      }
                    }
                  ]
                }
              }
            },
            {
              "-name": "security",
              "xsd:complexType": {
                "xsd:sequence": {
                  "xsd:element": [
                    {
                      "-name": "customer",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:string",
                          "xsd:minLength": { "-value": "1" },
                          "xsd:maxLength": { "-value": "6" }
                        }
                      }
                    },
                    {
                      "-name": "user",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:string",
                          "xsd:minLength": { "-value": "1" },
                          "xsd:maxLength": { "-value": "20" }
                        }
                      }
                    },
                    {
                      "-name": "password",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:string",
                          "xsd:minLength": { "-value": "1" },
                          "xsd:maxLength": { "-value": "20" }
                        }
                      }
                    },
                    {
                      "-name": "langid",
                      "-minOccurs": "0",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:string",
                          "xsd:minLength": { "-value": "1" },
                          "xsd:maxLength": { "-value": "2" }
                        }
                      }
                    }
                  ]
                }
              }
            },
            {
              "-name": "consignment",
              "-maxOccurs": "unbounded",
              "xsd:complexType": {
                "xsd:sequence": {
                  "xsd:element": [
                    {
                      "-name": "laroseDepot",
                      "-minOccurs": "0",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:string",
                          "xsd:maxLength": { "-value": "4" }
                        }
                      }
                    },
                    {
                      "-name": "senderAccId",
                      "-minOccurs": "0",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:string",
                          "xsd:maxLength": { "-value": "11" }
                        }
                      }
                    },
                    {
                      "-name": "consignmentno",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:string",
                          "xsd:maxLength": { "-value": "15" }
                        }
                      }
                    },
                    {
                      "-name": "consignmenttype",
                      "-minOccurs": "0",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:string",
                          "xsd:maxLength": { "-value": "1" },
                          "xsd:minLength": { "-value": "1" }
                        }
                      }
                    },
                    {
                      "-name": "CollectionTrg",
                      "xsd:complexType": {
                        "xsd:sequence": {
                          "xsd:element": [
                            {
                              "-name": "priopntime",
                              "-type": "xsd:integer"
                            },
                            {
                              "-name": "priclotime",
                              "-type": "xsd:integer"
                            },
                            {
                              "-name": "secopntime",
                              "-type": "xsd:integer"
                            },
                            {
                              "-name": "secclotime",
                              "-type": "xsd:integer"
                            },
                            {
                              "-name": "availabilitytime",
                              "-type": "xsd:integer"
                            },
                            {
                              "-name": "pickupdate",
                              "-type": "xsd:NMTOKEN"
                            },
                            {
                              "-name": "pickuptime",
                              "-type": "xsd:integer"
                            },
                            {
                              "-name": "pickupinstr",
                              "-type": "xsd:string"
                            }
                          ]
                        }
                      }
                    },
                    {
                      "-name": "actualweight",
                      "-minOccurs": "0",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:integer",
                          "xsd:totalDigits": { "-value": "8" },
                          "xsd:minInclusive": { "-value": "0" }
                        }
                      }
                    },
                    {
                      "-name": "actualvolume",
                      "-minOccurs": "0",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:integer",
                          "xsd:totalDigits": { "-value": "7" },
                          "xsd:minInclusive": { "-value": "0" }
                        }
                      }
                    },
                    {
                      "-name": "totalpackages",
                      "-minOccurs": "0",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:integer",
                          "xsd:totalDigits": { "-value": "5" },
                          "xsd:minInclusive": { "-value": "0" }
                        }
                      }
                    },
                    {
                      "-name": "packagetype",
                      "-minOccurs": "0",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:string",
                          "xsd:maxLength": { "-value": "1" }
                        }
                      }
                    },
                    {
                      "-name": "division",
                      "-minOccurs": "0",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:string",
                          "xsd:maxLength": { "-value": "3" }
                        }
                      }
                    },
                    {
                      "-name": "product",
                      "-minOccurs": "0",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:string",
                          "xsd:maxLength": { "-value": "4" }
                        }
                      }
                    },
                    {
                      "-name": "vehicle",
                      "-minOccurs": "0",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:string",
                          "xsd:maxLength": { "-value": "1" }
                        }
                      }
                    },
                    {
                      "-name": "insurancevalue",
                      "-minOccurs": "0",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:integer",
                          "xsd:totalDigits": { "-value": "13" },
                          "xsd:minInclusive": { "-value": "0" }
                        }
                      }
                    },
                    {
                      "-name": "insurancecurrency",
                      "-minOccurs": "0",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:string",
                          "xsd:maxLength": { "-value": "3" }
                        }
                      }
                    },
                    {
                      "-name": "packingdesc",
                      "-minOccurs": "0",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:string",
                          "xsd:maxLength": { "-value": "20" }
                        }
                      }
                    },
                    {
                      "-name": "reference",
                      "-minOccurs": "0",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:string",
                          "xsd:maxLength": { "-value": "24" }
                        }
                      }
                    },
                    {
                      "-name": "collectiondate",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:string",
                          "xsd:maxLength": { "-value": "8" }
                        }
                      }
                    },
                    {
                      "-name": "collectiontime",
                      "-minOccurs": "0",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:string",
                          "xsd:maxLength": { "-value": "4" }
                        }
                      }
                    },
                    {
                      "-name": "invoicevalue",
                      "-minOccurs": "0",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:integer",
                          "xsd:totalDigits": { "-value": "13" },
                          "xsd:minInclusive": { "-value": "0" }
                        }
                      }
                    },
                    {
                      "-name": "invoicecurrency",
                      "-minOccurs": "0",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:string",
                          "xsd:maxLength": { "-value": "3" }
                        }
                      }
                    },
                    {
                      "-name": "options",
                      "-minOccurs": "0",
                      "xsd:complexType": {
                        "xsd:sequence": {
                          "xsd:element": {
                            "-name": "option",
                            "-minOccurs": "0",
                            "-maxOccurs": "4",
                            "xsd:simpleType": {
                              "xsd:restriction": {
                                "-base": "xsd:string",
                                "xsd:maxLength": { "-value": "3" }
                              }
                            }
                          }
                        }
                      }
                    },
                    {
                      "-name": "termsofpayment",
                      "-minOccurs": "0",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:string",
                          "xsd:maxLength": { "-value": "1" }
                        }
                      }
                    },
                    {
                      "-name": "specialinstructions",
                      "-minOccurs": "0",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:string",
                          "xsd:maxLength": { "-value": "80" }
                        }
                      }
                    },
                    {
                      "-name": "systemcode",
                      "-minOccurs": "0",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:string",
                          "xsd:maxLength": { "-value": "2" }
                        }
                      }
                    },
                    {
                      "-name": "systemversion",
                      "-minOccurs": "0",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:string",
                          "xsd:maxLength": { "-value": "5" }
                        }
                      }
                    },
                    {
                      "-name": "codfvalue",
                      "-minOccurs": "0",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:integer",
                          "xsd:totalDigits": { "-value": "13" },
                          "xsd:minInclusive": { "-value": "0" }
                        }
                      }
                    },
                    {
                      "-name": "codfcurrency",
                      "-minOccurs": "0",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:string",
                          "xsd:maxLength": { "-value": "3" }
                        }
                      }
                    },
                    {
                      "-name": "eomofferno",
                      "-minOccurs": "0",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:string",
                          "xsd:maxLength": { "-value": "7" }
                        }
                      }
                    },
                    {
                      "-name": "eomdivision",
                      "-minOccurs": "0",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:string",
                          "xsd:maxLength": { "-value": "5" }
                        }
                      }
                    },
                    {
                      "-name": "eomenclosure",
                      "-minOccurs": "0",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:string",
                          "xsd:maxLength": { "-value": "15" }
                        }
                      }
                    },
                    {
                      "-name": "goodsdesc",
                      "-minOccurs": "0",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:string",
                          "xsd:maxLength": { "-value": "30" }
                        }
                      }
                    },
                    {
                      "-name": "eomunification",
                      "-minOccurs": "0",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:string",
                          "xsd:maxLength": { "-value": "8" }
                        }
                      }
                    },
                    {
                      "-name": "dropoffpoint",
                      "-minOccurs": "0",
                      "xsd:simpleType": {
                        "xsd:restriction": {
                          "-base": "xsd:string",
                          "xsd:maxLength": { "-value": "5" }
                        }
                      }
                    },
                    {
                      "-name": "addresses",
                      "-minOccurs": "0",
                      "xsd:complexType": {
                        "xsd:sequence": {
                          "xsd:element": {
                            "-name": "address",
                            "-minOccurs": "1",
                            "-maxOccurs": "4",
                            "xsd:complexType": {
                              "xsd:sequence": {
                                "xsd:element": [
                                  {
                                    "-name": "addressType",
                                    "xsd:simpleType": {
                                      "xsd:restriction": {
                                        "-base": "xsd:string",
                                        "xsd:maxLength": { "-value": "2" }
                                      }
                                    }
                                  },
                                  {
                                    "-name": "vatno",
                                    "-minOccurs": "0",
                                    "xsd:simpleType": {
                                      "xsd:restriction": {
                                        "-base": "xsd:string",
                                        "xsd:maxLength": { "-value": "20" }
                                      }
                                    }
                                  },
                                  {
                                    "-name": "addrline1",
                                    "xsd:simpleType": {
                                      "xsd:restriction": {
                                        "-base": "xsd:string",
                                        "xsd:maxLength": { "-value": "35" }
                                      }
                                    }
                                  },
                                  {
                                    "-name": "addrline2",
                                    "-minOccurs": "0",
                                    "xsd:simpleType": {
                                      "xsd:restriction": {
                                        "-base": "xsd:string",
                                        "xsd:maxLength": { "-value": "30" }
                                      }
                                    }
                                  },
                                  {
                                    "-name": "addrline3",
                                    "-minOccurs": "0",
                                    "xsd:simpleType": {
                                      "xsd:restriction": {
                                        "-base": "xsd:string",
                                        "xsd:maxLength": { "-value": "30" }
                                      }
                                    }
                                  },
                                  {
                                    "-name": "postcode",
                                    "-minOccurs": "0",
                                    "xsd:simpleType": {
                                      "xsd:restriction": {
                                        "-base": "xsd:string",
                                        "xsd:maxLength": { "-value": "9" }
                                      }
                                    }
                                  },
                                  {
                                    "-name": "phone1",
                                    "-minOccurs": "0",
                                    "xsd:simpleType": {
                                      "xsd:restriction": {
                                        "-base": "xsd:string",
                                        "xsd:maxLength": { "-value": "7" }
                                      }
                                    }
                                  },
                                  {
                                    "-name": "phone2",
                                    "-minOccurs": "0",
                                    "xsd:simpleType": {
                                      "xsd:restriction": {
                                        "-base": "xsd:string",
                                        "xsd:maxLength": { "-value": "9" }
                                      }
                                    }
                                  },
                                  {
                                    "-name": "name",
                                    "xsd:simpleType": {
                                      "xsd:restriction": {
                                        "-base": "xsd:string",
                                        "xsd:maxLength": { "-value": "50" }
                                      }
                                    }
                                  },
                                  {
                                    "-name": "country",
                                    "xsd:simpleType": {
                                      "xsd:restriction": {
                                        "-base": "xsd:string",
                                        "xsd:maxLength": { "-value": "3" }
                                      }
                                    }
                                  },
                                  {
                                    "-name": "town",
                                    "xsd:simpleType": {
                                      "xsd:restriction": {
                                        "-base": "xsd:string",
                                        "xsd:maxLength": { "-value": "30" }
                                      }
                                    }
                                  },
                                  {
                                    "-name": "contactname",
                                    "-minOccurs": "0",
                                    "xsd:simpleType": {
                                      "xsd:restriction": {
                                        "-base": "xsd:string",
                                        "xsd:maxLength": { "-value": "22" }
                                      }
                                    }
                                  },
                                  {
                                    "-name": "fax1",
                                    "-minOccurs": "0",
                                    "xsd:simpleType": {
                                      "xsd:restriction": {
                                        "-base": "xsd:string",
                                        "xsd:maxLength": { "-value": "7" }
                                      }
                                    }
                                  },
                                  {
                                    "-name": "fax2",
                                    "-minOccurs": "0",
                                    "xsd:simpleType": {
                                      "xsd:restriction": {
                                        "-base": "xsd:string",
                                        "xsd:maxLength": { "-value": "9" }
                                      }
                                    }
                                  },
                                  {
                                    "-name": "email",
                                    "-minOccurs": "0",
                                    "xsd:simpleType": {
                                      "xsd:restriction": {
                                        "-base": "xsd:string",
                                        "xsd:maxLength": { "-value": "60" }
                                      }
                                    }
                                  },
                                  {
                                    "-name": "telex",
                                    "-minOccurs": "0",
                                    "xsd:simpleType": {
                                      "xsd:restriction": {
                                        "-base": "xsd:string",
                                        "xsd:maxLength": { "-value": "9" }
                                      }
                                    }
                                  },
                                  {
                                    "-name": "province",
                                    "-minOccurs": "0",
                                    "xsd:simpleType": {
                                      "xsd:restriction": {
                                        "-base": "xsd:string",
                                        "xsd:maxLength": { "-value": "30" }
                                      }
                                    }
                                  },
                                  {
                                    "-name": "custcountry",
                                    "-minOccurs": "0",
                                    "xsd:simpleType": {
                                      "xsd:restriction": {
                                        "-base": "xsd:string",
                                        "xsd:maxLength": { "-value": "3" }
                                      }
                                    }
                                  },
                                  {
                                    "-name": "title",
                                    "-minOccurs": "0",
                                    "xsd:simpleType": {
                                      "xsd:restriction": {
                                        "-base": "xsd:string",
                                        "xsd:maxLength": { "-value": "4" }
                                      }
                                    }
                                  }
                                ]
                              }
                            }
                          }
                        }
                      }
                    },
                    {
                      "-name": "dimensions",
                      "-minOccurs": "0",
                      "-maxOccurs": "99",
                      "xsd:complexType": {
                        "xsd:sequence": {
                          "xsd:element": [
                            {
                              "-name": "itemsequenceno",
                              "-minOccurs": "0",
                              "xsd:simpleType": {
                                "xsd:restriction": {
                                  "-base": "xsd:integer",
                                  "xsd:totalDigits": { "-value": "5" },
                                  "xsd:minInclusive": { "-value": "0" }
                                }
                              }
                            },
                            {
                              "-name": "itemtype",
                              "-minOccurs": "0",
                              "xsd:simpleType": {
                                "xsd:restriction": {
                                  "-base": "xsd:string",
                                  "xsd:maxLength": { "-value": "1" }
                                }
                              }
                            },
                            {
                              "-name": "itemreference",
                              "-minOccurs": "0",
                              "xsd:simpleType": {
                                "xsd:restriction": {
                                  "-base": "xsd:string",
                                  "xsd:maxLength": { "-value": "24" }
                                }
                              }
                            },
                            {
                              "-name": "volume",
                              "-minOccurs": "0",
                              "xsd:simpleType": {
                                "xsd:restriction": {
                                  "-base": "xsd:integer",
                                  "xsd:totalDigits": { "-value": "7" },
                                  "xsd:minInclusive": { "-value": "0" }
                                }
                              }
                            },
                            {
                              "-name": "weight",
                              "-minOccurs": "0",
                              "xsd:simpleType": {
                                "xsd:restriction": {
                                  "-base": "xsd:integer",
                                  "xsd:totalDigits": { "-value": "8" },
                                  "xsd:minInclusive": { "-value": "0" }
                                }
                              }
                            },
                            {
                              "-name": "length",
                              "-minOccurs": "0",
                              "xsd:simpleType": {
                                "xsd:restriction": {
                                  "-base": "xsd:integer",
                                  "xsd:totalDigits": { "-value": "6" },
                                  "xsd:minInclusive": { "-value": "0" }
                                }
                              }
                            },
                            {
                              "-name": "height",
                              "-minOccurs": "0",
                              "xsd:simpleType": {
                                "xsd:restriction": {
                                  "-base": "xsd:integer",
                                  "xsd:totalDigits": { "-value": "6" },
                                  "xsd:minInclusive": { "-value": "0" }
                                }
                              }
                            },
                            {
                              "-name": "width",
                              "-minOccurs": "0",
                              "xsd:simpleType": {
                                "xsd:restriction": {
                                  "-base": "xsd:integer",
                                  "xsd:totalDigits": { "-value": "6" },
                                  "xsd:minInclusive": { "-value": "0" }
                                }
                              }
                            },
                            {
                              "-name": "quantity",
                              "-minOccurs": "0",
                              "xsd:simpleType": {
                                "xsd:restriction": {
                                  "-base": "xsd:integer",
                                  "xsd:totalDigits": { "-value": "5" },
                                  "xsd:minInclusive": { "-value": "0" }
                                }
                              }
                            }
                          ]
                        },
                        "xsd:attribute": [
                          {
                            "-name": "itemaction",
                            "-use": "optional",
                            "xsd:simpleType": {
                              "xsd:restriction": {
                                "-base": "xsd:string",
                                "xsd:minLength": { "-value": "1" },
                                "xsd:maxLength": { "-value": "1" }
                              }
                            }
                          },
                          {
                            "-name": "international",
                            "-use": "optional",
                            "xsd:simpleType": {
                              "xsd:restriction": {
                                "-base": "xsd:string",
                                "xsd:maxLength": { "-value": "1" },
                                "xsd:minLength": { "-value": "1" }
                              }
                            }
                          }
                        ]
                      }
                    },
                    {
                      "-name": "articles",
                      "-minOccurs": "0",
                      "-maxOccurs": "99",
                      "xsd:complexType": {
                        "xsd:sequence": {
                          "xsd:element": [
                            {
                              "-name": "tariff",
                              "-minOccurs": "0",
                              "xsd:simpleType": {
                                "xsd:restriction": {
                                  "-base": "xsd:string",
                                  "xsd:maxLength": { "-value": "30" }
                                }
                              }
                            },
                            {
                              "-name": "origcountry",
                              "-minOccurs": "0",
                              "xsd:simpleType": {
                                "xsd:restriction": {
                                  "-base": "xsd:string",
                                  "xsd:maxLength": { "-value": "3" }
                                }
                              }
                            }
                          ]
                        }
                      }
                    }
                  ]
                },
                "xsd:attribute": [
                  {
                    "-name": "action",
                    "-use": "required",
                    "xsd:simpleType": {
                      "xsd:restriction": {
                        "-base": "xsd:string",
                        "xsd:minLength": { "-value": "1" },
                        "xsd:maxLength": { "-value": "1" }
                      }
                    }
                  },
                  {
                    "-name": "insurance",
                    "-use": "optional",
                    "xsd:simpleType": {
                      "xsd:restriction": {
                        "-base": "xsd:string",
                        "xsd:maxLength": { "-value": "1" },
                        "xsd:minLength": { "-value": "1" }
                      }
                    }
                  },
                  {
                    "-name": "hazardous",
                    "-use": "optional",
                    "xsd:simpleType": {
                      "xsd:restriction": {
                        "-base": "xsd:string",
                        "xsd:minLength": { "-value": "1" },
                        "xsd:maxLength": { "-value": "1" }
                      }
                    }
                  },
                  {
                    "-name": "cashondelivery",
                    "-use": "optional",
                    "xsd:simpleType": {
                      "xsd:restriction": {
                        "-base": "xsd:string",
                        "xsd:minLength": { "-value": "1" },
                        "xsd:maxLength": { "-value": "1" }
                      }
                    }
                  },
                  {
                    "-name": "codcommission",
                    "-use": "optional",
                    "xsd:simpleType": {
                      "xsd:restriction": {
                        "-base": "xsd:string",
                        "xsd:minLength": { "-value": "1" },
                        "xsd:maxLength": { "-value": "1" }
                      }
                    }
                  },
                  {
                    "-name": "insurancecommission",
                    "-use": "optional",
                    "xsd:simpleType": {
                      "xsd:restriction": {
                        "-base": "xsd:string",
                        "xsd:minLength": { "-value": "1" },
                        "xsd:maxLength": { "-value": "1" }
                      }
                    }
                  },
                  {
                    "-name": "operationaloption",
                    "-use": "optional",
                    "xsd:simpleType": {
                      "xsd:restriction": {
                        "-base": "xsd:string",
                        "xsd:minLength": { "-value": "1" },
                        "xsd:maxLength": { "-value": "1" }
                      }
                    }
                  },
                  {
                    "-name": "highvalue",
                    "-use": "optional",
                    "xsd:simpleType": {
                      "xsd:restriction": {
                        "-base": "xsd:string",
                        "xsd:minLength": { "-value": "1" },
                        "xsd:maxLength": { "-value": "1" }
                      }
                    }
                  },
                  {
                    "-name": "specialgoods",
                    "-use": "optional",
                    "xsd:simpleType": {
                      "xsd:restriction": {
                        "-base": "xsd:string",
                        "xsd:minLength": { "-value": "1" },
                        "xsd:maxLength": { "-value": "1" }
                      }
                    }
                  }
                ]
              }
            }
          ]
        }
      }
    }
  }
}
        
class delivery_carrier(osv.osv):
    _inherit = 'delivery.carrier'
    _columns = {
             'carrier_tnt_id':fields.many2one('delivery.carrier.tnt', 'Connessione Tnt ', required=False),    
             'carrier_sda_id':fields.many2one('delivery.carrier.sda', 'Connessione sda ', required=False),    
                        }
class delivery_carrier_sda(osv.osv):
    _name = 'delivery.carrier.sda'
    _description = 'Url carrier sda'

    _columns = {
        'name':fields.char('Name', size=64, required=True, readonly=False),
        'active':fields.boolean('Active', required=False), 
        'seq': fields.integer('Sequenza di ricerca'), 
        'url':fields.char('url', size=256, required=True, readonly=False),
        'customer':fields.char('Customer', size=64, required=True, readonly=False),
        'user':fields.char('Utente', size=64, required=True, readonly=False),
        'password':fields.char('Password', size=64, required=True, readonly=False),
        'langid':fields.char('langid', size=64, required=True, readonly=False),
        'langid2':fields.char('langid2', size=64, required=True, readonly=False),
        'servizio':fields.selection([
                 
('S01','ZERO TRE'),
('S02','ZERO QUINDICI'),
('S03','ZERO TRENTA'),
('S04','REGIONALE'),
('S05','GOLDEN SERVICE'),
('S06','ANDATA E RITORNO'),
('S08','INTERNAZIONALE'),
('S09','EXTRA LARGE'),
('S10','CAPI APPESI SMALL'),
('S11','CAPI APPESI LARGE'),
('S21','PORTO ASSEGNATO'),
('S24','ECONOMY'),
('S28','RACCOMANDATA'),
('S29','RACCOMANDATA UNO'),
('S34','ROAD EUROPE'),
('S36','EXPORT BOX'),
('S37','EXPRESS BOX'),
('S40','CONSEGNA&INSTALLA '),
             ],    
'Servizio',  required=True,),
        
        'Fasce_ass':fields.selection([
('AS01','FINO A EURO 258,23'),
('AS02','FINO A EURO 516,46'),
('AS03','FINO A EURO 1.549,37'),
('AS04','FINO A EURO 2.582,28'),
('AS05','OLTRE EURO 2.582,28'),
('AS12','ASSICURATA ROAD EUROPE'),
('AS13','ASSICURATA EXPORT BOX'),
('AC32','ASSICURAZIONE IN % SUL VALORE'),
('AC33','ASSICURAZIONE IN % SUL VALORE'),
('AC34','ASSICURAZIONE IN % SUL VALORE'),
('AC35','ASSICURAZIONE IN % SUL VALORE'),
             ],    'Fasce Assicurative', required=True,),

        'fasce_orarie':fields.selection([
('A','9:00 – 11:00'),
('B','10:00 – 12:00'),
('C','11:00 – 13:00'),
('D','14:00 – 16:00'),
('E','15:00 – 17:00'),
('F','16:00 – 18:00'),

             ],    'Fasce orarie', required=True,),
        
        'giorno_consegna':fields.selection([

('1','Lunedi'),
('2','Martedì'),
('3','Mercoledì'),
('4','Giovedì'),
('5','Venerdì'),
             ],    'Giorno di consegna', required=True,),
        
        'consegna_stabilita':fields.selection([

('AM','AM'),
('PM','PM'),
             ],    'Consegna_stabilita', required=True,),
        
        'time':fields.selection([

('T09','Ore 09:00'),
('T10','Ore 10:00'),
('T12','Ore 12:00'),
             ],    'Time definite', required=True,),
        'formato_stampa':fields.char('Formato di Stampa', size=64, required=True, readonly=False),
        'certificato':fields.binary('Certificato', filters=None), 
        'usa_cert':fields.boolean('Usa Certificato', required=False), 
        'idv':fields.char('id Seme idv ', size=64, required=True, readonly=False),
        'url_trk':fields.char('url tracking ', size=256, required=False, readonly=False),
        'codTipoPagamento':fields.selection([

('ABM','Ass.Banc.Mittente'),
('CON','Contanti'),
('ABS','Ass.Banc.SDA'),
('ACM','Ass.Circ.Mittente'),
('ACS','Ass.Circ.SDA'),
('VAR','Tutti'),
             ],    'Codice di Contrassegno', required=False,),
    
    }
    _order = 'seq,id' 
class delivery_carrier_sda_tx_rx(osv.osv_memory):
    _name = 'delivery.carrier.sda.tx.rx'
    _description = 'delivery.carrier.sda'
    def _default_carrier_sda(self, cr, uid, context=None):
        return self.pool.get('delivery.carrier.sda').search(cr, uid, [('active', '=', True)],order='seq',context=context)[0]
    
    _columns = {
        'name':fields.char('Name', size=64, required=True, readonly=False),
        'carrier_sda_id':fields.many2one('delivery.carrier.sda', 'Url di Trasmissione', required=False), 
        'dataspedizione': fields.date('Data di spedizione'), 
        'colli_ids':fields.one2many('delivery.carrier.sda.tx.rx.line', 'carrier_sda_tx_id', 'Colli', required=False),
        'lettere_ids':fields.one2many('delivery.carrier.sda.tx.rx.download', 'carrier_sda_tx_id', 'Lettere', required=False),
        'sda_rx_lettere': fields.binary('File', required=False),
        'sda_rx_file_name':fields.char('nome file', readonly=False), 
        'state': fields.selection([('choose', 'choose'),   # choose language
                                       ('get', 'get')]),        # get the file


    }
    _defaults = {  
        'name':  lambda *a: 'tx-' + time.strftime('%Y-%m-%d') ,  
        'dataspedizione':  lambda *a: time.strftime('%Y-%m-%d') ,  
        'carrier_sda_id': _default_carrier_sda,
        'state': 'choose',

        }
    @api.multi
    def view_init(self,fields_list):
        active_ids = self.env.context and self.env.context.get('active_ids', False)
    @api.multi
    def onchange_carrier_sda_id(self):
        active_ids = self.env.context and self.env.context.get('active_ids', False)
        print '1 self.id',self.id#...
        print '1 env',self.env
        print '1 context',self.env.context
        line_obj=self.env['delivery.carrier.sda.tx.rx.line']#..
        conta=0
        colli_ids=line_obj.search([('carrier_sda_tx_id','=',self.id)])
        for colli_id in colli_ids:
            colli_id.unlink()
        lettere_obj=self.env['delivery.carrier.sda.tx.rx.download']#..
        lettere_ids=lettere_obj.search([('carrier_sda_tx_id','=',self.id)])
        for lettere_id in lettere_ids:
            lettere_id.unlink()
        if self.env.context.get('active_model', 'sale.order')=='sale.order':
            for sale_id_obj in self.env['sale.order'].browse(active_ids):
                if sale_id_obj.picking_ids:
                    for stock_id_obj in sale_id_obj.picking_ids[0]:
                        for move_id_obj in stock_id_obj.move_lines:
                            
                            line_obj.create({'x_imb_x':move_id_obj.x_imb_x,
                                            'x_imb_y':move_id_obj.x_imb_y,
                                            'x_imb_z':move_id_obj.x_imb_z,
                                            "x_peso":move_id_obj.weight,
                                            "product_id":move_id_obj.product_id.id,
                                            'sale_id':sale_id_obj.id,
                                            'pick_id':move_id_obj.picking_id.id,
                                            'carrier_sda_tx_id':self.id,
                                            'sale_line_:id':None,
                                            'move_id':move_id_obj.id,
                                            })    
                        conta+=1
                else:
                        for line_id_obj in sale_id_obj.order_line:
                            if line_id_obj.product_id.type=='product':
                                line_obj.create({'x_imb_x':line_id_obj.x_imb_x,
                                                'x_imb_y':line_id_obj.x_imb_y,
                                                'x_imb_z':line_id_obj.x_imb_z,
                                                "x_peso":line_id_obj.th_weight,
                                                "product_id":line_id_obj.product_id.id,
                                                'sale_id':sale_id_obj.id,
                                                'pick_id':None,
                                                'carrier_sda_tx_id':self.id,
                                                'sale_line_:id':line_id_obj.id,
                                                'move_id':None,
                                                })    
                    
                        conta+=1
        if self.env.context.get('active_model', 'sale.order')=='stock.picking':
            for picking_id_obj in self.env['stock.picking'].browse(active_ids):
                        for move_id_obj in picking_id_obj.move_lines:
                            line_obj.create({'x_imb_x':move_id_obj.x_imb_x,
                                            'x_imb_y':move_id_obj.x_imb_y,
                                            'x_imb_z':move_id_obj.x_imb_z,
                                            "x_peso":move_id_obj.weight,
                                            "product_id":move_id_obj.product_id.id,
                                            'sale_id':move_id_obj.picking_id.sale_id.id,
                                            'pick_id':move_id_obj.picking_id.id,
                                            'carrier_sda_tx_id':self.id,
                                            'sale_line_:id':None,
                                            'move_id':move_id_obj.id,
                                            })    
                        conta+=1
        view_ref = self.env['ir.model.data'].get_object_reference('prof_tnt_sda_delivery', 'view_delivery_carrier_sda_tx_rx')
        view_id = view_ref and view_ref[1] or False,
        return {'name':_("Ricezine Lettere di Vettura"),
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'delivery.carrier.sda.tx.rx',
                'res_id': self.id,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'normal',
                'domain': self.env.context,                                 
                'context': self.env.context,                                 
            }

    @api.multi
    def delivery_open_tx(self):
        view_ref = self.env['ir.model.data'].get_object_reference('prof_tnt_sda_delivery', 'view_delivery_carrier_sda_tx_rx')
        view_id = view_ref and view_ref[1] or False,
        my_id=self.create({
                                   'name':   'tx-' + time.strftime('%Y-%m-%d') ,  
                                   'dataspedizione': time.strftime('%Y-%m-%d') ,  
                           })
        print 'self.env.context',self.env.context
        print 'my_id',my_id.id
        return {'name':_("Ricezine Lettere di Vettura"),
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'delivery.carrier.sda.tx.rx',
                'res_id': my_id.id,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'normal',
                'domain': self.env.context,                                 
                'context': self.env.context,                                 
            }

    @api.multi
    def delivery_tx(self):
        def set_sda(sale_id_obj,carrier_sda_id_obj,date_today,colli):
                    numero=sale_id_obj.name
                    if hasattr(sale_id_obj,'shop_id'):
                        if hasattr(sale_id_obj.shop_id,'x_tag'):
                                if sale_id_obj.shop_id.x_tag:
                                    numero=sale_id_obj.name.replace(sale_id_obj.shop_id.x_tag,'') 
                                else:
                                    numero=sale_id_obj.name                                                    
                    if hasattr(sale_id_obj,'x_invoice_state'):                    
                        if sale_id_obj.x_invoice_state.find('Contrassegno')>=0:
                            accessori={'contrassegno':{"codTipoPagamento":carrier_sda_id_obj.codTipoPagamento,
                                                       "contrassegnoValore":sale_id_obj.invoice_ids[0].amount_total
                                                       }
                                       }
                        else:
                            accessori={
                                   }    
                    else:
                        accessori={
                                   }                        
                    #print 'set_sda_accessori',accessori
                    return {
                            "ldv": {
                                "mittente": {
                                    "intestatario": sale_id_obj.company_id.partner_id.name,
                                    "indirizzo": sale_id_obj.company_id.partner_id.street,
                                    "cap": sale_id_obj.company_id.partner_id.zip,
                                    "identificativoFiscale": sale_id_obj.company_id.partner_id.fiscalcode,
                                    "localita": sale_id_obj.company_id.partner_id.city,
                                    "provincia": sale_id_obj.company_id.partner_id.state_id.code,
                                    "tipoAnagrafica": "S",
                                    "codNazione": sale_id_obj.company_id.partner_id.country_id.sda_code or carrier_sda_id_obj.langid,
                                    "referente": sale_id_obj.company_id.partner_id.ref,
                                    "telefono": int(str(sale_id_obj.company_id.partner_id.phone or '0').replace(' ','')),
                                    "email": sale_id_obj.company_id.partner_id.email
                                },
                                "destinatario": {
                                    "intestatario": sale_id_obj.partner_shipping_id.name or sale_id_obj.partner_id.name,
                                    "indirizzo": sale_id_obj.partner_shipping_id.street or sale_id_obj.partner_id.street,
                                    "cap":  sale_id_obj.partner_shipping_id.zip or sale_id_obj.partner_id.zip,
                                    "identificativoFiscale": sale_id_obj.partner_shipping_id.fiscalcode or  sale_id_obj.partner_id.fiscalcode,
                                    "localita": sale_id_obj.partner_shipping_id.city or sale_id_obj.partner_id.city,
                                    "provincia": sale_id_obj.partner_shipping_id.state_id.code or sale_id_obj.partner_id.state_id.code,
                                    "tipoAnagrafica": "S",
                                    "codNazione": sale_id_obj.partner_id.country_id.sda_code or carrier_sda_id_obj.langid2,
                                    "referente": sale_id_obj.partner_id.ref or sale_id_obj.partner_shipping_id.ref or '',
                                    "telefono": int(str(sale_id_obj.partner_id.phone or sale_id_obj.partner_shipping_id.phone or '0').replace(' ','')),
                                    "email": sale_id_obj.partner_id.email or sale_id_obj.partner_shipping_id.email
                                },
                                "datiSpedizione": {
                                    "codiceServizio": carrier_sda_id_obj.servizio,
                         
                                    "datiGenerali": {
                                        "dataSpedizione": date_today.strftime('%d/%m/%Y'),
                                        "numRifInterno": numero,
                                        "note": sale_id_obj.note or '',
                                        "contenuto": sale_id_obj.order_line[0].product_id.categ_id.name
                                    },
                                        "accessori":accessori,
                                        
                                    "sezioneColli": {
                                        "colli":colli
                                        
                                    }
                        
                                }
                            },
                                "formatoStampa":str(carrier_sda_id_obj.formato_stampa)
                        }#print 'conta-->',conta,'request-->',request
        def get_fileobj():
            try:
                handle, filepath = tempfile.mkstemp()
                fileobj = os.fdopen(handle,'w+') # convert raw handle to file object        try:
                
                #fileobj.close()
            except:
                fileobj=None
            return {'fileobj':fileobj,'handle':handle,'filepath':filepath}
        def send_request(sda_obj,sda_json):
            date_today=datetime.today()
            cert_file=date_today.strftime('%d-%m-%Y_%h_%m_%s')+'_.crt'
            if sda_obj.usa_cert:
                        try:
                                handle, filepath = tempfile.mkstemp(cert_file)
                                fileobj = os.fdopen(handle,'w+')  # convert raw handle to file object        try:
                                
                                fileobj.write(base64.decodestring(sda_obj.certificato))
                                fileobj.close()
                                print 'handle',handle
                                print 'filepath',filepath
                                
                        except:
                                print 'errore'
            user_password=base64.b64encode(sda_obj.user+':'+sda_obj.password )
            #user_password=sda_obj.user+':'+sda_obj.password..
            user_password='Basic '+user_password
            filepath='/media/disco2/ship_sda_doc/collaudo-ws.sda.it.crt'
            if sda_obj.url:
               http = httplib2.Http()
                #body = {'USERNAME': 'foo', 'PASSWORD': 'bar'}..
               body = sda_json
               
               headers ={'Content-Type':'application/json','Authorization':user_password}
               #headers ={'Authorization':user_password}
               #try: 
               print 'url',sda_obj.url
               print 'user,password-->',sda_obj.user,sda_obj.password
               print 'body-->',body
               print 'headers-->',headers
               if str(sda_obj.url).find('https')>=0:
                    if sda_obj.usa_cert==False:
                        req = requests.post(sda_obj.url, data=json.dumps(body),headers=headers,verify=False,auth=HTTPBasicAuth(sda_obj.user,sda_obj.password)) 
                        response=req.text
                        #print 'response',response
                    else:
                        req = requests.post(sda_obj.url, data=json.dumps(body),
                                            headers=headers,verify=True,
                                            cert=filepath,
                                            auth=HTTPBasicAuth(sda_obj.user,sda_obj.password)) 
                        """"
                        s = Session()
                        req = Request('POST',  url,
                            data=json.dumps(body),
                            headers=headers,
                            auth=HTTPBasicAuth(sda_obj.user,sda_obj.password)
                        )
                        """
                        response=req.text
               else:
                        req = requests.post(sda_obj.url, data=json.dumps(body),headers=headers,verify=False,auth=HTTPBasicAuth(sda_obj.user,sda_obj.password)) 
                        response=req.text
                        #print 'response',response
               if response:
                    ret=json.loads(response)
                    return   ret             
                
               else:
                            return  False             
        sale_obj = self.env['sale.order']
        pick_obj = self.env['stock.picking']#'''''dd
        sda_obj = self.env['delivery.carrier.sda']
        lettere_obj=self.env['delivery.carrier.sda.tx.rx.download']#..

        active_ids=self.env.context.get('active_ids', [])
        if self.dataspedizione:
            date_today=datetime.strptime(self.dataspedizione, '%Y-%m-%d')
        else:
            date_today=datetime.today()
        if self.carrier_sda_id:
            carrier_sda_id=self.carrier_sda_id.id
        else:
            carrier_sda_id=self._default_carrier_sda()
        file_obj_ids=[]
        if carrier_sda_id==None:
                if self.colli_ids[0].sale_id.carrier_id.carrier_sda_id:
                        carrier_sda_id=self.colli_ids[0].sale_id.carrier_id.carrier_sda_id.id
                else:
                        carrier_sda_id=self._default_carrier_sda()
                
        carrier_sda_id_obj=sda_obj.browse(carrier_sda_id)
        lettere_obj=self.env['delivery.carrier.sda.tx.rx.download']#..
        lettere_ids=lettere_obj.search([('carrier_sda_tx_id','=',self.id)])
        for lettere_id in lettere_ids:
            lettere_id.unlink()
        colli=[]
        l_lett=[]
        my_sale=None
        sale_id_obj=None
        conta=0
        riep_lettere=base64.b64encode('')
        if self.colli_ids:
            for colli_id_obj in self.colli_ids:
                my_sale=self.colli_ids[0].sale_id.id
                sale_id_obj=self.colli_ids[0].sale_id
                pick_id_obj=self.colli_ids[0].pick_id
                break
        for colli_id_obj in self.colli_ids:
            if colli_id_obj.sale_id.id==my_sale:#-----...
                #print 'my_sale',my_sale
                colli.append({
                                      "peso":colli_id_obj.x_peso,
                                      "larghezza": colli_id_obj.x_imb_x,
                                      "profondita": colli_id_obj.x_imb_y,
                                      "altezza": colli_id_obj.x_imb_z
                                      
                                      })
                conta+=1
            else:
                    sda_vals=set_sda(sale_id_obj,carrier_sda_id_obj,date_today,colli)
                    if conta>0:
                                resp=send_request(carrier_sda_id_obj,sda_vals)
                                if resp:
                                    if resp.get('messages',None):
                                        sda_rx_messagge=resp['messages']['messages'][0]['message']
                                    else:
                                        sda_rx_messagge=None
                                    if resp.get('documentoDiStampa',None):
                                            riep_lettere +=resp.get('documentoDiStampa',base64.b64encode(''))
                                            print 'spedizioni',resp.get('spedizioni')
                                            print 'colli',resp.get('spedizioni')[0]['datiSpedizione']['sezioneColli']['colli']
                                            l_lett.append(
                                                          {'sda_rx_stato':resp.get('outcome','ERORRE'),
                                                           'sda_rx_lettera':resp.get('documentoDiStampa',base64.b64encode('')),
                                                           'sda_rx_messagge':sda_rx_messagge, 
                                                            'sda_rx_file_name': 'lettera_%s.pdf' % str(sale_id_obj.id),
                                                            'carrier_sda_tx_id':self.id,
                                                             'sda_rx_numero':[ str(colli.get('numero','')).replace("'",'"') for colli in resp.get('spedizioni',[{'datiSpedizione':{'sezioneColli':{"colli":[{'numero':None}]}}}])[0]['datiSpedizione']['sezioneColli']['colli'] ], 
 
                                                           }
                                                          )
                                            #print '1 riep_lettere',riep_lettere
                                            file_obj_id=get_fileobj()
                                            file_obj_id['fileobj'].write(base64.decodestring(resp.get('documentoDiStampa',base64.b64encode(''))))
                                            file_obj_id['fileobj'].close()
                                            file_obj_ids.append(file_obj_id)
                                    else:
                                            l_lett.append(
                                                          {'sda_rx_stato':resp.get('outcome','ERORRE'),
                                                           'sda_rx_lettera':resp.get('documentoDiStampa',base64.b64encode('')),
                                                           'sda_rx_messagge':sda_rx_messagge, 
                                                            'sda_rx_file_name': 'lettera_%s.pdf' % str(sale_id_obj.id),
                                                            'carrier_sda_tx_id':self.id,
                                                            'sda_rx_numero':None, 
                                                           }
                                                          )
                                        
                                    if sale_id_obj:
                                        file_name='lettera_%s.pdf' % str(sale_id_obj.id)
                                        #print 'spedizioni data',resp.get('spedizioni')[0]['datiSpedizione']['datiGenerali']
                                        sale_id_obj.write({'sda_rx_stato':resp.get('outcome','ERORRE'),
                                                                           'sda_rx_documentoDiStampa': resp.get('documentoDiStampa',None),
                                                                           'sda_rx_dataspedizione':resp.get('spedizioni',[{'datiSpedizione':{'datiGenerali':{'dataSpedizione':None}}}])[0]['datiSpedizione']['datiGenerali']['dataSpedizione'],
                                                                           'sda_rx_messagge':sda_rx_messagge,
                                                                           'sda_rx_file_name': 'lettera_%s.pdf' % str(sale_id_obj.id),
                                                             'sda_rx_numero':[ str(colli.get('numero',' ')).replace("'",'"') for colli in resp.get('spedizioni',[{'datiSpedizione':{'sezioneColli':{"colli":[{'numero':None}]}}}])[0]['datiSpedizione']['sezioneColli']['colli'] ], 
            
                                                                             })
                                    if pick_id_obj:
                                        file_name='lettera_%s.pdf' % str(pick_id_obj.id)
                                        pick_id_obj.write({'sda_rx_stato':resp.get('outcome','ERORRE'),
                                                                           'sda_rx_documentoDiStampa':resp.get('documentoDiStampa',None),
                                                                           'sda_rx_dataspedizione':resp.get('spedizioni',[{'datiSpedizione':{'datiGenerali':{'dataSpedizione':None}}}])[0]['datiSpedizione']['datiGenerali']['dataSpedizione'],
                                                                           'sda_rx_messagge':sda_rx_messagge,     
                                                                           'sda_rx_file_name': 'lettera_%s.pdf' % str(pick_id_obj.id),
                                                             'sda_rx_numero':[ str(colli.get('numero',' ')).replace("'",'"') for colli in resp.get('spedizioni',[{'datiSpedizione':{'sezioneColli':{"colli":[{'numero':None}]}}}])[0]['datiSpedizione']['sezioneColli']['colli'] ], 
                                                                              })
                                    sale_id_obj=colli_id_obj.sale_id
                                    pick_id_obj=colli_id_obj.pick_id
                                    my_sale=colli_id_obj.sale_id.id
                                    conta=1
                                    colli=[]
                                    colli.append({
                                                      "peso":colli_id_obj.x_peso,
                                                      "larghezza": colli_id_obj.x_imb_x,
                                                      "profondita": colli_id_obj.x_imb_y,
                                                      "altezza": colli_id_obj.x_imb_z
                                                      
                                                      })
        if my_sale:
                    sda_vals=set_sda(sale_id_obj,carrier_sda_id_obj,date_today,colli)
                    sale_id_obj=colli_id_obj.sale_id
                    pick_id_obj=colli_id_obj.pick_id
                    mysale=colli_id_obj.sale_id.id
                    if conta>0:
                                resp=send_request(carrier_sda_id_obj,sda_vals)
                                if resp:
                                    if resp.get('messages',None):
                                        sda_rx_messagge=resp['messages']['messages'][0]['message']
                                    else:
                                        sda_rx_messagge=None
                                    if resp.get('documentoDiStampa',None):
                                            riep_lettere += resp.get('documentoDiStampa',base64.b64encode(''))
                                            l_lett.append(
                                                          {'sda_rx_stato':resp.get('outcome','ERORRE'),
                                                           'sda_rx_lettera':resp.get('documentoDiStampa',base64.b64encode('')),
                                                           'sda_rx_messagge':sda_rx_messagge, 
                                                            'sda_rx_file_name': 'lettera_%s.pdf' % str(sale_id_obj.id),
                                                            'carrier_sda_tx_id':self.id,
                                                             'sda_rx_numero':[ str(colli.get('numero',' ')).replace("'",'"') for colli in resp.get('spedizioni',[{'datiSpedizione':{'sezioneColli':{"colli":[{'numero':None}]}}}])[0]['datiSpedizione']['sezioneColli']['colli'] ], 
                                          }
                                                          )
                                            file_obj_id=get_fileobj()
                                            file_obj_id['fileobj'].write(base64.decodestring(resp.get('documentoDiStampa',base64.b64encode(''))))
                                            file_obj_id['fileobj'].close()
                                            file_obj_ids.append(file_obj_id)
                                    else:
                                            l_lett.append(
                                                          {'sda_rx_stato':resp.get('outcome','ERORRE'),
                                                           'sda_rx_lettera':resp.get('documentoDiStampa',base64.b64encode('')),
                                                           'sda_rx_messagge':sda_rx_messagge, 
                                                            'sda_rx_file_name': 'lettera_%s.pdf' % str(sale_id_obj.id),
                                                            'carrier_sda_tx_id':self.id,
                                                            'sda_rx_numero':None, 
                                                           }
                                                          )
                                    if sale_id_obj:
                                        file_name='lettera_%s.pdf' % str(sale_id_obj.id)
                                        sale_id_obj.write({
                                                                       'sda_rx_stato':resp.get('outcome','ERORRE'),
                                                                   'sda_rx_documentoDiStampa':resp.get('documentoDiStampa',None),
                                                                           'sda_rx_dataspedizione':resp.get('spedizioni',[{'datiSpedizione':{'datiGenerali':{'dataSpedizione':None}}}])[0]['datiSpedizione']['datiGenerali']['dataSpedizione'],
                                                                   'sda_rx_messagge':sda_rx_messagge,
                                                                    'sda_rx_file_name': 'lettera_%s.pdf' % str(sale_id_obj.id),
                                                             'sda_rx_numero':[ str(colli.get('numero',' ')).replace("'",'"') for colli in resp.get('spedizioni',[{'datiSpedizione':{'sezioneColli':{"colli":[{'numero':None}]}}}])[0]['datiSpedizione']['sezioneColli']['colli'] ], 
        
                                                                     })
                                    if pick_id_obj:
                                        file_name='lettera_%s.pdf' % str(pick_id_obj.id)
                                        pick_id_obj.write({'sda_rx_stato':resp.get('outcome','ERORRE'),
                                                                       'sda_rx_documentoDiStampa':resp.get('documentoDiStampa',None),
                                                                           'sda_rx_dataspedizione':resp.get('spedizioni',[{'datiSpedizione':{'datiGenerali':{'dataSpedizione':None}}}])[0]['datiSpedizione']['datiGenerali']['dataSpedizione'],
                                                                       'sda_rx_messagge':sda_rx_messagge ,      
                                                                       'sda_rx_file_name': 'lettera_%s.pdf' % str(pick_id_obj.id),
                                                             'sda_rx_numero':[ str(colli.get('numero',' ')).replace("'",'"') for colli in resp.get('spedizioni',[{'datiSpedizione':{'sezioneColli':{"colli":[{'numero':None}]}}}])[0]['datiSpedizione']['sezioneColli']['colli'] ], 
 
                                                                         })
            
        
        file_name='lettera_%s.pdf' % str(self.id)
        #print '5 file_name',file_name
        #print 'riep_lettere',riep_lettere
        lettere_vett=base64.b64encode('')
        lettera_c=0
        for my_lett in l_lett:
                lettera_c+=1
                lettere_vett+=my_lett['sda_rx_lettera']
                letterea_name='lettera_%s.pdf' % str(lettera_c)
                lettere_obj.create(my_lett)    

                #print 'lettere_vett',lettere_vett
        my_file=''
        for file_obj_id in file_obj_ids:
            my_file+= ' ' + file_obj_id['filepath']
            print 'my_file',my_file
        file_cat_id=get_fileobj()
        print 'file_cat_id',file_cat_id['filepath']
        
        file_cat_id['fileobj'].close()
        os.system('pdftk %s cat output %s' % (my_file,file_cat_id['filepath']))
        fileobj = open(file_cat_id['filepath']) # convert raw handle to file object        try:
        dati = fileobj.read()
        fileobj.close()
        self.write({'state':'get','sda_rx_lettere':base64.encodestring(dati),'sda_rx_file_name':'lettere_%s.pdf' % str(self.id)})
        return {'name':_("Message"),
                'view_mode': 'form',
                'view_id': False,
                'view_type': 'form',
                #'res_model': self.env.context['active_model'],
                'res_model': 'delivery.carrier.sda.tx.rx',
                #'res_id': active_ids[0],
                'res_id': self.id,
                'type': 'ir.actions.act_window',
                'nodestroy': False,
                'target': 'normal',
                'domain': self.env.context,                                 
            }
    """
    Tracking
    """
    @api.multi
    def delivery_trk(self,cron=False):
        def set_sda(carrier_sda_id_obj,datispedizine):
                    return {
                            "codCliente":carrier_sda_id_obj.customer, 
                            "datiSpedizione": datispedizine,
                            "descrizioneStatus": "E",
                            "tipologiaCliente": "SDA",
                            "postazione": carrier_sda_id_obj.idv                        
}#print 'conta-->',conta,'request-->',request
        def send_request(sda_obj,sda_json):
            date_today=datetime.today()
            cert_file=date_today.strftime('%d-%m-%Y_%h_%m_%s')+'_.crt'
            if sda_obj.usa_cert:
                        try:
                                handle, filepath = tempfile.mkstemp(cert_file)
                                fileobj = os.fdopen(handle,'w+')  # convert raw handle to file object        try:
                                
                                fileobj.write(base64.decodestring(sda_obj.certificato))
                                fileobj.close()
                                print 'handle',handle
                                print 'filepath',filepath
                                
                        except:
                                print 'errore'
            user_password=base64.b64encode(sda_obj.user+':'+sda_obj.password )
            user_password='Basic '+user_password
            #filepath='/media/disco2/ship_sda_doc/collaudo-ws.sda.it.crt'
            if sda_obj.url_trk:
                #body = {'USERNAME': 'foo', 'PASSWORD': 'bar'}..
               body = sda_json
               
               headers ={'Content-Type':'application/json','Authorization':user_password}
               #headers ={'Authorization':user_password}
               #try: 
               print 'url',sda_obj.url
               print 'user,password-->',sda_obj.user,sda_obj.password
               print 'body-->',body
               print 'headers-->',headers
               if str(sda_obj.url_trk).find('https')>=0:
                    if sda_obj.usa_cert==False:
                        req = requests.post(sda_obj.url_trk, data=json.dumps(body),headers=headers,verify=False,auth=HTTPBasicAuth(sda_obj.user,sda_obj.password)) 
                        response=req.text
                        #print 'response',response
                    else:
                        req = requests.post(sda_obj.url_trk, data=json.dumps(body),
                                            headers=headers,verify=True,
                                            cert=filepath,
                                            auth=HTTPBasicAuth(sda_obj.user,sda_obj.password)) 
                        """"
                        s = Session()
                        req = Request('POST',  url_trk,
                            data=json.dumps(body),
                            headers=headers,
                            auth=HTTPBasicAuth(sda_obj.user,sda_obj.password)
                        )
                        """
                        response=req.text
               else:
                        req = requests.post(sda_obj.url_trk, data=json.dumps(body),headers=headers,verify=False,auth=HTTPBasicAuth(sda_obj.user,sda_obj.password)) 
                        response=req.text
                        #print 'response',response
                #except:
                #         response={'status':500}
                #         content={}
               if response:
                    #print 'response-->',response
                    #print 'content-->',response
                    ret=json.loads(response)
                    #campo=base64.b64decode(ret.get('documentoDiStampa','non trovato'))
                    #print 'campo',campo
                    return   ret             
                
               else:
                            return  False             
        sale_obj = self.env['sale.order']
        pick_obj = self.env['stock.picking']#'''''dd
        sda_obj = self.env['delivery.carrier.sda']
        active_ids=self.env.context.get('active_ids', [])
        if self.carrier_sda_id:
            carrier_sda_id=self.carrier_sda_id.id
        else:
            carrier_sda_id=self._default_carrier_sda()
        if carrier_sda_id==None:
                if self.colli_ids[0].sale_id.carrier_id.carrier_sda_id:
                        carrier_sda_id=self.colli_ids[0].sale_id.carrier_id.carrier_sda_id.id
                else:
                        carrier_sda_id=self._default_carrier_sda()
                
        carrier_sda_id_obj=sda_obj.browse(carrier_sda_id)
        if cron==True:
            obj_ids=sale_obj.search([('sda_rx_numero','<>',None),('sda_trk_stato','=','""')])
        else:
            if self.env.context['active_model']=='sale.order':
                obj_ids=sale_obj.search([('id','in',tuple(active_ids))])
            elif self.env.context['active_model']=='stock.picking':
                obj_ids=pick_obj.search([('id','in',tuple(active_ids))])
            else:
                obj_ids=sale_obj.search([('sda_rx_numero','<>',None),('sda_trk_stato','=','""')])
                
        conta=0
        for obj_id_obj in obj_ids:
            datispedizine=[]
            if self.env.context['active_model']=='sale.order':
                carrier_sda_id=obj_id_obj.carrier_id.carrier_sda_id.id or self._default_carrier_sda()
            elif self.env.context['active_model']=='stock.picking':
                carrier_sda_id=obj_id_obj.sale_id.carrier_id.carrier_sda_id.id or self._default_carrier_sda()
            else:
                carrier_sda_id=self._default_carrier_sda()
            conta+=1
            if self.env.context['active_model']=='sale.order': 
                numero=obj_id_obj.name
                if hasattr(obj_id_obj,'shop_id'):
                            if hasattr(obj_id_obj.shop_id,'x_tag'):
                                    numero=obj_id_obj.name.replace(obj_id_obj.shop_id.x_tag,'')                        
            elif self.env.context['active_model']=='stock.picking':
                numero=obj_id_obj.sale_id.name
                if hasattr(obj_id_obj.sale_id,'shop_id'):
                            if hasattr(obj_id_obj.sale_id.shop_id,'x_tag'):
                                    numero=obj_id_obj.sale_id.name.replace(obj_id_obj.sale_id.shop_id.x_tag,'')                        
            else:
                numero=obj_id_obj.name
                
            datispedizine.append({
                                      "numOrdine": numero ,
                                      "ultimoStato": 'N',
                                 })
            sda_vals=set_sda(carrier_sda_id_obj,datispedizine)
            resp=send_request(carrier_sda_id_obj,sda_vals)
            if resp:
                                    print 'resp',resp
                                    if resp.get('messages',None):
                                        print 'messages_',resp['messages']
                                        if resp['messages'].get('messages',[]):
                                            sda_trx_message=str(resp['messages']['messages'][0]['code']) + ' '+ resp['messages']['messages'][0]['message']
                                        else:
                                            sda_trx_message='-'
                                    else:
                                        sda_trx_message='Errore Generico ti Ricezione'
                                    if resp.get('result',None):
                                            
                                            if resp.get('spedizione',None)==None:
                                                resp['spedizione']=[{'tracking':[{'stato':'Errore TRK','descrizioneStato':'Errore TRK'}]}]
                                            if resp['code']==0:
                                                    state_message='OK'
                                            elif resp['code']>=100 and resp['code']<=199:
                                                    state_message='Errore Formale'
                                            elif resp['code']>=200 and resp['code']<=299:
                                                    state_message='Errore BUSINESS'
                                            elif resp['code']==999:                       
                                                    state_message='Errore Generico'
                                            else:                       
                                                    state_message='Errore Generico'
                                            obj_id_obj.write({
                                                              'sda_trk_stato':resp['spedizione'][0]['tracking'][0]['stato'] if resp.get('spedizione',[]) else str(resp['code'])+'-'+resp['result'] ,
                                                              'sda_trk_desc_stato': resp['spedizione'][0]['tracking'][0]['descrizioneStato'] if resp.get('spedizione',[]) else state_message,
                                                              'sda_trk_message':sda_trx_message,
                                                              #'sda_trk_message':resp['spedizione']
                                                                             })
        if cron==False:
            return {'name':_("Message"),
                'view_mode': 'form'  if len(active_ids)==1 else 'tree,form',
                'view_id': False,
                'view_type': 'form',
                'res_model': self.env.context['active_model'],
                'res_id': active_ids[0] if len(active_ids)==1 else None,
                'type': 'ir.actions.act_window',
                'nodestroy': False,
                'target': 'normal',
                'domain': [('id','in',tuple(active_ids))],                                 
            }
        return {}

    @api.multi
    def delivery_tx_old(self):
        def send_request(sda_obj,sda_json):
            date_today=datetime.today()
            cert_file=date_today.strftime('%d-%m-%Y_%h_%m_%s')+'_.crt'
            if sda_obj.usa_cert:
                        try:
                                handle, filepath = tempfile.mkstemp(cert_file)
                                fileobj = os.fdopen(handle,'w+')  # convert raw handle to file object        try:
                                
                                fileobj.write(base64.decodestring(sda_obj.certificato))
                                fileobj.close()
                                print 'handle',handle
                                print 'filepath',filepath
                                
                        except:
                                print 'errore'
            user_password=base64.b64encode(sda_obj.user+':'+sda_obj.password )
            #user_password=sda_obj.user+':'+sda_obj.password..
            user_password='Basic '+user_password
            filepath='/media/disco2/ship_sda_doc/collaudo-ws.sda.it.crt'
            if sda_obj.url:
               http = httplib2.Http()
                #body = {'USERNAME': 'foo', 'PASSWORD': 'bar'}..
               body = sda_json
               
               headers ={'Content-Type':'application/json','Authorization':user_password}
               #headers ={'Authorization':user_password}
               #try: 
               print 'url',sda_obj.url
               print 'user,password-->',sda_obj.user,sda_obj.password
               print 'body-->',body
               print 'headers-->',headers
               if str(sda_obj.url).find('https')>=0:
                    if sda_obj.usa_cert==False:
                        #http = httplib2.Http("/home/rocco/.cache", disable_ssl_certificate_validation=True)
                        #response, content = http.request(sda_obj.url, 'POST', headers=headers, body=urllib.urlencode(body))
                        req = requests.post(sda_obj.url, data=json.dumps(body),headers=headers,verify=False,auth=HTTPBasicAuth(sda_obj.user,sda_obj.password)) 
                        print 'request',req
                        print 'request.text',req.text
                        print 'raw',req.raw
                        #print 'request.text',req.text
                        #print 'documentoDiStampa',req.text['documentoDiStampa']
                        #response=dict(req.text)
                        response=req.text
                        print 'response',response
                        print type(response)
                        #campo=base64.b64decode(response['documentoDiStampa'])
                        #campo=dict(response)
                        #print campo
                        #json.loads(s, encoding, cls, object_hook, parse_float, parse_int, parse_constant, object_pairs_hook)
                    else:
                        #http = httplib2.Http("/home/rocco/.cache", disable_ssl_certificate_validation=True)
                        #response, content = http.request(sda_obj.url, 'POST', headers=headers, body=urllib.urlencode(body))
                        req = requests.post(sda_obj.url, data=json.dumps(body),
                                            headers=headers,verify=True,
                                            cert=filepath,
                                            auth=HTTPBasicAuth(sda_obj.user,sda_obj.password)) 
                        """"
                        s = Session()
                        req = Request('POST',  url,
                            data=json.dumps(body),
                            headers=headers,
                            auth=HTTPBasicAuth(sda_obj.user,sda_obj.password)
                        )
                        """
                        print 'request',req
                        print 'request.text',req.text
                        #print 'request.text',req.text
                        #print 'documentoDiStampa',req.text['documentoDiStampa']
                        #response=dict(req.text)
                        response=req.text
                        print 'response',response
               else:
                    response, content = http.request(sda_obj.url, 'POST',cert=filepath, headers=headers,body=urllib.urlencode(body))
                #except:
                #         response={'status':500}
                #         content={}
               if response:
                    print 'response-->',response
                    print 'content-->',response
                    ret=json.loads(response)
                    #campo=base64.b64decode(ret.get('documentoDiStampa','non trovato'))
                    #print 'campo',campo
                    return   ret             
                
               else:
                            return  False             
        sale_obj = self.env['sale.order']#'''''dd
        sda_obj = self.env['delivery.carrier.sda']
        active_ids=self.env.context.get('active_ids', [])
        if self.dataspedizione:
            date_today=self.dataspedizione
        else:
            date_today=datetime.today()
        if self.carrier_sda_id:
            carrier_sda_id=self.carrier_sda_id.id
        else:
            carrier_sda_id=self._default_carrier_sda()
        #for sale_id_obj in sale_obj.browse(active_ids):
        
        for colli_id_obj in self.colli_ids:
            colli=[]
            if carrier_sda_id==None:
                if sale_id_obj.carrier_id.carrier_sda_id:
                        carrier_sda_id=sale_id_obj.carrier_id.carrier_sda_id.id
                else:
                        carrier_sda_id=self._default_carrier_sda()
                
            carrier_sda_id_obj=sda_obj.browse(carrier_sda_id)
            conta=0
            numero=sale_id_obj.name
            if hasattr(sale_id_obj,'shop_id'):
                        if hasattr(sale_id_obj.shop_id,'x_tag'):
                                numero=sale_id_obj.name.replace(sale_id_obj.shop_id.x_tag,'')                        
            if sale_id_obj.picking_ids:
                for stock_id_obj in sale_id_obj.picking_ids[0]:
                    for move_id_obj in stock_id_obj.move_lines:
                        colli.append({
                                      "peso":move_id_obj.weight,
                                      "larghezza": move_id_obj.x_imb_x,
                                      "profondita": move_id_obj.x_imb_y,
                                       "altezza": move_id_obj.x_imb_z
                                      
                                      })
                    conta+=1
            else:
                    for line_id_obj in sale_id_obj.order_line:
                        colli.append({
                                      "peso":line_id_obj.th_weight,
                                      "larghezza": line_id_obj.x_imb_x,
                                      "profondita": line_id_obj.x_imb_y,
                                       "altezza": line_id_obj.x_imb_z
                                      
                                      })
                
                    conta+=1
            sda_vals={
                            "ldv": {
                                "mittente": {
                                    "intestatario": sale_id_obj.company_id.partner_id.name,
                                    "indirizzo": sale_id_obj.company_id.partner_id.street,
                                    "cap": sale_id_obj.company_id.partner_id.zip,
                                    "identificativoFiscale": sale_id_obj.company_id.partner_id.fiscalcode,
                                    "localita": sale_id_obj.company_id.partner_id.city,
                                    "provincia": sale_id_obj.company_id.partner_id.state_id.code,
                                    "tipoAnagrafica": "S",
                                    "codNazione": carrier_sda_id_obj.langid,
                                    "referente": sale_id_obj.company_id.partner_id.ref,
                                    "telefono": int(sale_id_obj.company_id.partner_id.phone.strip()),
                                    "email": sale_id_obj.company_id.partner_id.email
                                },
                                "destinatario": {
                                    "intestatario": sale_id_obj.partner_id.name,
                                    "indirizzo": sale_id_obj.partner_id.street,
                                    "cap": sale_id_obj.partner_id.zip,
                                    "identificativoFiscale": sale_id_obj.partner_id.fiscalcode,
                                    "localita": sale_id_obj.partner_id.city,
                                    "provincia": sale_id_obj.partner_id.state_id.code,
                                    "tipoAnagrafica": "S",
                                    "codNazione": carrier_sda_id_obj.langid2,
                                    "referente": sale_id_obj.partner_id.ref,
                                    "telefono": int(str(sale_id_obj.partner_id.phone).strip()),
                                    "email": sale_id_obj.partner_id.email
                                },
                                "datiSpedizione": {
                                    "codiceServizio": carrier_sda_id_obj.servizio,
                         
                                    "datiGenerali": {
                                        "dataSpedizione": date_today.strftime('%d/%m/%Y'),
                                        "numRifInterno": sale_id_obj.name,
                                        "note": sale_id_obj.note,
                                        "contenuto": sale_id_obj.order_line[0].product_id.categ_id.name
                                    },
                                        "accessori": {},
                                        
                                    "sezioneColli": {
                                        "colli":colli
                                        
                                    }
                        
                                }
                            },
                                "formatoStampa":str(carrier_sda_id_obj.formato_stampa)
                        }#print 'conta-->',conta,'request-->',request
            if conta>0:
                        resp=send_request(carrier_sda_id_obj,sda_vals)
                        if resp:
                            sale_obj.write(sale_id_obj.id,{'sda_rx_stato':resp.get('outcome','ERORRE'),
                                                           'sda_rx_documentoDiStampa':resp.get('documentoDiStampa',None),
                                                           'sda_rx_dataspedizione':resp.get('dataspedizione',None)
                                                           })
        return {'name':_("Message"),
                'view_mode': 'form',
                'view_id': False,
                'view_type': 'form',
                'res_model': 'sale.order',
                'res_id': active_ids[0],
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'self',
                'domain': self.env.context,                                 
            }

        return resp

class delivery_carrier_sda_tx_rx_line(osv.osv_memory):
    _name = 'delivery.carrier.sda.tx.rx.line'
    _columns = {
        'carrier_sda_tx_id':fields.many2one('delivery.carrier.sda.tx.rx', 'Testata sda_tx', required=True, ondelete='cascade', select=True, readonly=True),        
        'sale_id':fields.many2one('sale.order', 'Ordine cliente', required=False),        
        'sale_line_id':fields.many2one('sale.order.line', 'Linea ordine cliente', required=False),        
        'pick_id':fields.many2one('stock.picking', 'picking', required=False),        
        'move_id':fields.many2one('stock.move', 'movimento', required=False),        
        'product_id':fields.many2one('product.product', 'prodotto', required=False),        
        'x_peso': fields.float('Peso', digits_compute=dp.get_precision('Product Price'),required=False),
        'x_imb_x': fields.float('Lunghezza', digits_compute=dp.get_precision('Product Price'),required=False),
        'x_imb_y': fields.float('Altezza', digits_compute=dp.get_precision('Product Price'),required=False),
        'x_imb_z': fields.float('Profondità', digits_compute=dp.get_precision('Product Price'),required=False),
                        }
    _order = 'sale_id asc,pick_id asc,id asc' 

    def onchange_product_id(self, cr, uid, ids, prod_id=False,context=None ):
        product_obj = self.pool.get('product.product')
        product_obj = product_obj.browse(cr, uid, prod_id, context=context)
        res={'value':{}}
        res['value']['x_weight'] = product_obj.weight        # Round the quantity up   
        res['value']['x_imb_x'] = product_obj.x_imb_x        # Round the quantity up   
        res['value']['x_imb_y'] = product_obj.x_imb_y        # Round the quantity up   
        res['value']['x_imb_z'] = product_obj.x_imb_z        # Round the quantity up   
        return res 
class delivery_carrier_sda_tx_rx_download(osv.osv_memory):
    _name = 'delivery.carrier.sda.tx.rx.download'
    _columns = {
        'carrier_sda_tx_id':fields.many2one('delivery.carrier.sda.tx.rx', 'Testata sda_tx', required=True, ondelete='cascade', select=True, readonly=True),        
        'sda_rx_lettera': fields.binary('Lettera', required=False),
        'sda_rx_stato':fields.char('Stato ricezione', size=64, required=False, readonly=False), 
        'sda_rx_messagge':fields.char('Messaggio', size=256, required=False, readonly=False), 
        'sda_rx_file_name':fields.char('nome file', readonly=False), 
        'state': fields.selection([('choose', 'choose'),   # choose language
                                       ('get', 'get')]),        # get the file
        'sda_rx_numero':fields.char('Numero', size=64, required=False, readonly=False), 

                        }

class sale_order(osv.osv):
    _inherit = 'sale.order'
    _columns = {
        'sda_rx_stato':fields.char('Stato ricezione', size=64, required=False, readonly=True), 
        'sda_rx_documentoDiStampa': fields.binary('File', required=False),
        'sda_rx_dataspedizione':fields.date('Data Spedizione',readonly=True), 
        'sda_rx_messagge':fields.char('Messaggio', size=256, required=False, readonly=True), 
        'sda_rx_file_name':fields.char('nome file', readonly=True), 
        'sda_rx_numero':fields.char('Numero', size=256, required=False, readonly=True), 
        'sda_trk_stato':fields.char('Stato track', size=64, required=False, readonly=True), 
        'sda_trk_desc_stato':fields.char('Descrizione Tracking', size=256, required=False, readonly=True), 
        'sda_trk_message':fields.char('Descrizione tx Tracking', size=1024, required=False, readonly=True), 
                        

                        }
class stock_picking(osv.osv):
    _inherit = 'stock.picking'
    _columns = {
        'sda_rx_stato':fields.char('Stato ricezione', size=64, required=False, readonly=True), 
        'sda_rx_documentoDiStampa': fields.binary('File', required=False),
        'sda_rx_dataspedizione':fields.date('Data Spedizione',readonly=True), 
        'sda_rx_messagge':fields.char('Messaggio', size=256, required=False, readonly=True), 
        'sda_rx_file_name':fields.char('nome file', readonly=True), 
        'sda_rx_numero':fields.char('Numero', size=256, required=False, readonly=True ), 
        'sda_trk_stato':fields.char('Stato track', size=64, required=False, readonly=True), 
        'sda_trk_desc_stato':fields.char('Descrizione Tracking', size=256, required=False, readonly=True), 
        'sda_trk_message':fields.char('Descrizione tx Tracking', size=1024, required=False, readonly=True), 
                        }

class sale_order_line(osv.osv):
    _inherit = 'sale.order.line'
    _columns = {
        'x_imb_x': fields.float('Lunghezza', digits_compute=dp.get_precision('Product Price'),required=False),
        'x_imb_y': fields.float('Altezza', digits_compute=dp.get_precision('Product Price'),required=False),
        'x_imb_z': fields.float('Profondità', digits_compute=dp.get_precision('Product Price'),required=False),
                        }
    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, context=None):
        res=super(sale_order_line, self).product_id_change(cr, uid, ids, pricelist, product, qty,
            uom, qty_uos, uos, name, partner_id,
            lang, update_tax, date_order, packaging, fiscal_position, flag, context)
        product_obj = self.pool.get('product.product')
        product_obj = product_obj.browse(cr, uid, product, context=context)
        res['value']['x_imb_x'] = product_obj.x_imb_x        # Round the quantity up   
        res['value']['x_imb_y'] = product_obj.x_imb_y        # Round the quantity up   
        res['value']['x_imb_z'] = product_obj.x_imb_z        # Round the quantity up   
        return res
class stock_move(osv.osv):
    _inherit = 'stock.move'
    _columns = {
        'x_imb_x': fields.float('Lunghezza', digits_compute=dp.get_precision('Product Price'),required=False),
        'x_imb_y': fields.float('Altezza', digits_compute=dp.get_precision('Product Price'),required=False),
        'x_imb_z': fields.float('Profondità', digits_compute=dp.get_precision('Product Price'),required=False),
                        }
    def onchange_product_id(self, cr, uid, ids, prod_id=False, loc_id=False, loc_dest_id=False, partner_id=False):
        res=super(stock_move, self).onchange_product_id(cr, uid, ids, prod_id, loc_id, loc_dest_id, partner_id)
        product_obj = self.pool.get('product.product')
        product_obj = product_obj.browse(cr, uid, prod_id)
        if res.get('value',None):
            res['value']['x_imb_x'] = product_obj.x_imb_x        # Round the quantity up   
            res['value']['x_imb_y'] = product_obj.x_imb_y        # Round the quantity up   
            res['value']['x_imb_z'] = product_obj.x_imb_z        # Round the quantity up   
        return res
class res_country(osv.osv):
    _inherit = 'res.country'
    _columns = {
        'sda_code':fields.char('Codice Nazione sda', size=3, required=False, readonly=False), 
        }
class stock_quant(osv.osv):
    """
    Quants are the smallest unit of stock physical instances
    """
    _inherit = "stock.quant"
    @api.multi
    def recalculate_quant(self):
        """
        Use the removal strategies of product to search for the correct quants
        If you inherit, put the super at the end of your method.
        """
        def recalculate(quant_ids):
                move_obj=self.env['stock.move']
                ex_move=[]
                for quant_id_obj in quant_ids:
                        """ ricalcolo dei movimenti confermati """
                        ric_qry=0
                        if quant_id_obj.location_id.usage!='internal':
                            continue
                        #('partner_id','=',quant_id_obj.owner_id or quant_id_obj.owner_id.id or None)
                        move_ids_obj=move_obj.search([('state','=','done'),('restrict_lot_id','=',quant_id_obj.lot_id or quant_id_obj.lot_id.id or None),('product_id','=',quant_id_obj.product_id.id),('location_dest_id','=',quant_id_obj.location_id.id)])
                        for move_id in move_ids_obj:
                            if move_id.id not in ex_move:
                               ric_qry+= move_id.product_uom_qty
                               move_id.write({'quant_id':quant_id_obj.id})
                               ex_move.append(move_id.id)
                        move_ids_obj=move_obj.search([('state','=','done'),('restrict_lot_id','=',quant_id_obj.lot_id or quant_id_obj.lot_id.id or None),('product_id','=',quant_id_obj.product_id.id),('location_id','=',quant_id_obj.location_id.id)])
                        for move_id in move_ids_obj:
                            if move_id.id not in ex_move:
                               ric_qry-= move_id.product_uom_qty
                               move_id.write({'quant_id':quant_id_obj.id})
                               ex_move.append(move_id.id)
                        quant_id_obj.write({'qty':ric_qry})
        active_ids = self.env.context and self.env.context.get('active_ids', False)
        move_obj=self.env['stock.move']
        product_obj=self.env['product.product']
        templ_obj=self.env['product.template']
        if active_ids:
            if  self.env.context.get('active_model', False)=='stock.quant':
                quant_ids=self.search([('id','in',tuple(active_ids))])
                recalculate(quant_ids)
            elif self.env.context.get('active_model', False)=='product.product':
                for product_id_obj in product_obj.browse(active_ids):
                    quant_ids=self.search([('product_id','=',product_id_obj.id)])
                    recalculate(quant_ids)
            elif self.env.context.get('active_model', False)=='product.template':
                for templ_id_obj in templ_obj.browse(active_ids):
                    for product_id_obj in templ_id_obj.product_variant_ids:
                        quant_ids=self.search([('product_id','=',product_id_obj.id)])
                        recalculate(quant_ids)
                
                
        return {'name':_("Message"),
                'view_mode': 'form'  if len(active_ids)==1 else 'tree,form',
                'view_id': False,
                'view_type': 'form',
                'res_model': self.env.context['active_model'],
                'res_id': active_ids[0] if len(active_ids)==1 else None,
                'type': 'ir.actions.act_window',
                'nodestroy': False,
                'target': 'normal',
                'domain': [('id','in',tuple(active_ids))],                                 
            }
