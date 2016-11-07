# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2011-2012 OpenERP S.A. <http://openerp.com>
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
import requests
from openerp.osv import osv, fields
from openerp.addons.edi import EDIMixin
from openerp.tools.translate import _
from werkzeug import url_encode
import openerp.pooler as pooler
import os
import sys, httplib
import urllib2 
import urllib
import httplib2
import webbrowser
from openerp import http, SUPERUSER_ID
from openerp.http import request
import werkzeug
import webbrowser
from datetime import datetime
import time
from urllib import quote as quote
from openerp.tools import float_repr
from cookielib import CookieJar
import werkzeug
try:
    import simplejson as json
except ImportError:
    import json
import logging
try:
    from mako.template import Template as MakoTemplate
except ImportError:
    _logger.warning("payment_acquirer: mako templates not available, payment acquirer will not work!")

_logger = logging.getLogger(__name__)
ACCOUNT_X_SERVICE_LINE_EDI_STRUCT = {
    'sequence': True,
    'name': True,
    #custom: 'date_planned'
    'product_id': True,
    'service_uom': True,
    'price_unit': True,
    #custom: 'product_qty'
    'discount': True,

    # fields used for web preview only - discarded on import
    'price_subtotal': True,
}

ACCOUNT_X_SERVICE_NOTIFY_LINE_EDI_STRUCT = {
    'sequence': True,
    'name': True,
    #custom: 'date_planned'
    'product_id': True,
    'service_uom': True,
    'price_unit': True,
    #custom: 'product_qty'
    'discount': True,

    # fields used for web preview only - discarded on import
    'price_subtotal': True,
}

ACCOUNT_X_SERVICE_EDI_STRUCT = {
    'name': True,
    'company_id': True, # -> to be changed into partner
    #custom: 'partner_ref'
    'date_service': True,
    'partner_id': True,
    #custom: 'partner_address'
    #custom: 'notes'
    'line_ids': ACCOUNT_X_SERVICE_LINE_EDI_STRUCT,

    # fields used for web preview only - discarded on import
    'amount_total': True,
    'amount_untaxed': True,
    'amount_tax': True,
    'payment_term': True,
    'order_policy': True,
    'user_id': True,
    'state': True,
}
ACCOUNT_X_SERVICE_NOTIFY_EDI_STRUCT = {
    'name': True,
    'company_id': True, # -> to be changed into partner
    #custom: 'partner_ref'
    'data_notify': True,
    'partner_id': True,
    #custom: 'partner_address'
    #custom: 'notes'
    'notify_line_ids': ACCOUNT_X_SERVICE_NOTIFY_LINE_EDI_STRUCT,

    # fields used for web preview only - discarded on import
    'amount_total': True,
    'amount_untaxed': True,
    'amount_tax': True,
    'payment_term': True,
    'order_policy': True,
    'user_id': True,
    'state': True,
}

class account_x_service(osv.osv, EDIMixin):
    _inherit = 'account.x.service'

    def edi_export(self, cr, uid, records, edi_struct=None, context=None):
        """Exports a account.x.service"""
        edi_struct = dict(edi_struct or ACCOUNT_X_SERVICE_EDI_STRUCT)
        res_company = self.pool.get('res.company')
        res_partner_obj = self.pool.get('res.partner')
        edi_doc_list = []
        for x_service in records:
            # generate the main report
            self._edi_generate_report_attachment(cr, uid, x_service, context=context)

            # Get EDI doc based on struct. The result will also contain all metadata fields and attachments.
            edi_doc = super(account_x_service,self).edi_export(cr, uid, [x_service], edi_struct, context)[0]
            edi_doc.update({
                    # force trans-typing to purchase.order upon import
                    '__import_model': 'account.x.service',
                    '__import_module': 'rc_Cloudonthecloud',

                    'company_address': res_company.edi_export_address(cr, uid, x_service.partner_id.company_id, context=context),
                    'partner_address': res_partner_obj.edi_export(cr, uid, [x_service.partner_id], context=context)[0],

                    'currency': self.pool.get('res.currency').edi_export(cr, uid, [x_service.partner_id.property_product_pricelist.currency_id],
                                                                         context=context)[0],
                    'partner_ref': False,
                    'notes': x_service.note or False,
            })
            edi_doc_list.append(edi_doc)
        return edi_doc_list

    def _edi_import_company(self, cr, uid, edi_document, context=None):
        # TODO: for multi-company setups, we currently import the document in the
        #       user's current company, but we should perhaps foresee a way to select
        #       the desired company among the user's allowed companies

        self._edi_requires_attributes(('company_id','company_address'), edi_document)
        res_partner = self.pool.get('res.partner')

        xid, company_name = edi_document.pop('company_id')
        # Retrofit address info into a unified partner info (changed in v7 - used to keep them separate)
        company_address_edi = edi_document.pop('company_address')
        company_address_edi['name'] = company_name
        company_address_edi['is_company'] = True
        company_address_edi['__import_model'] = 'res.partner'
        company_address_edi['__id'] = xid  # override address ID, as of v7 they should be the same anyway
        if company_address_edi.get('logo'):
            company_address_edi['image'] = company_address_edi.pop('logo')
        company_address_edi['customer'] = True
        partner_id = res_partner.edi_import(cr, uid, company_address_edi, context=context)

        # modify edi_document to refer to new partner
        partner = res_partner.browse(cr, uid, partner_id, context=context)
        partner_edi_m2o = self.edi_m2o(cr, uid, partner, context=context)
        edi_document['partner_id'] = partner_edi_m2o
        edi_document['partner_invoice_id'] = partner_edi_m2o
        edi_document['partner_shipping_id'] = partner_edi_m2o

        edi_document.pop('partner_address', None) # ignored, that's supposed to be our own address!
        return partner_id

    def _edi_get_pricelist(self, cr, uid, partner_id, currency, context=None):
        # TODO: refactor into common place for purchase/sale, e.g. into product module
        partner_model = self.pool.get('res.partner')
        partner = partner_model.browse(cr, uid, partner_id, context=context)
        pricelist = partner.property_product_pricelist
        if not pricelist:
            pricelist = self.pool.get('ir.model.data').get_object(cr, uid, 'product', 'list0', context=context)

        if not pricelist.currency_id == currency:
            # look for a pricelist with the right type and currency, or make a new one
            pricelist_type = 'sale'
            product_pricelist = self.pool.get('product.pricelist')
            match_pricelist_ids = product_pricelist.search(cr, uid,[('type','=',pricelist_type),
                                                                    ('currency_id','=',currency.id)])
            if match_pricelist_ids:
                pricelist_id = match_pricelist_ids[0]
            else:
                pricelist_name = _('EDI Pricelist (%s)') % (currency.name,)
                pricelist_id = product_pricelist.create(cr, uid, {'name': pricelist_name,
                                                                  'type': pricelist_type,
                                                                  'currency_id': currency.id,
                                                                 })
                self.pool.get('product.pricelist.version').create(cr, uid, {'name': pricelist_name,
                                                                            'pricelist_id': pricelist_id})
            pricelist = product_pricelist.browse(cr, uid, pricelist_id)

        return self.edi_m2o(cr, uid, pricelist, context=context)

    def edi_import(self, cr, uid, edi_document, context=None):
        self._edi_requires_attributes(('company_id','company_address','line_ids','date_service','currency'), edi_document)

        #import company as a new partner
        partner_id = self._edi_import_company(cr, uid, edi_document, context=context)

        # currency for rounding the discount calculations and for the pricelist
        res_currency = self.pool.get('res.currency')
        currency_info = edi_document.pop('currency')
        currency_id = res_currency.edi_import(cr, uid, currency_info, context=context)
        order_currency = res_currency.browse(cr, uid, currency_id)

        partner_ref = edi_document.pop('partner_ref', False)
        edi_document['client_order_ref'] = edi_document['name']
        edi_document['name'] = partner_ref or edi_document['name']
        edi_document['note'] = edi_document.pop('notes', False)
        edi_document['pricelist_id'] = self._edi_get_pricelist(cr, uid, partner_id, order_currency, context=context)

        # discard web preview fields, if present
        edi_document.pop('amount_total', None)
        edi_document.pop('amount_tax', None)
        edi_document.pop('amount_untaxed', None)

        x_service_lines = edi_document['line_ids']
        for x_service_line in x_service_lines:
            self._edi_requires_attributes(('product_id', 'service_uom', 'service_qty', 'price_unit'), x_service_line)
            x_service_line['service_uom_qty'] = x_service_line['service_qty']
            del x_service_line['service_qty']

            # discard web preview fields, if present
            x_service_line.pop('price_subtotal', None)
        return super(account_x_service,self).edi_import(cr, uid, edi_document, context=context)

    def _edi_paypal_url(self, cr, uid, ids, field, arg, context=None):
        res = dict.fromkeys(ids, False)
        for account_x_service in self.browse(cr, uid, ids, context=context):
            if account_x_service.x_service_policy in ('prepaid', 'manual', 'invoiced') and \
                    account_x_service.partner_id.company_id.paypal_account and account_x_service.state != 'draft':
                params = {
                    "cmd": "_xclick",
                    "business": account_x_service.partner_id.company_id.paypal_account,
                    "item_name": 'SERV-' + str(account_x_service.id),
                    "invoice": 'SERV-' + str(account_x_service.id),
                    "amount": account_x_service.amount_total,
                    "currency_code": account_x_service.partner_id.property_product_pricelist.currency_id.name,
                    "button_subtype": "services",
                    "no_note": "1",
                    "bn": "OpenERP_Order_PayNow_" + account_x_service.partner_id.property_product_pricelist.currency_id.name,
                }
                res[account_x_service.id] = "https://www.paypal.com/cgi-bin/webscr?" + url_encode(params)
        return res

    _columns = {
        'paypal_url': fields.function(_edi_paypal_url, type='char', string='Paypal Url'),
        'paypal_status': fields.char('Paypal Status',size=64),
    }
    def paypal_url_get(self, cr, uid, ids, context=None):
        res = False
        x_service_id=ids
        if x_service_id:
            x_service_id_obj = self.pool.get('account.x.service').browse(cr,uid,x_service_id,context)
            res = False
            url = x_service_id_obj.paypal_url
            headers = {'Content-type': 'application/x-www-form-urlencoded'}
            http = httplib2.Http()
            request ="<TESTS><TEST></TEST></TESTS>" 
            body = {'xml': request}
            #urllib.urlopen(url)
            #resp = urllib.read()
            urequest = urllib2.Request(url)
            uopen = urllib2.urlopen(urequest)
            resp = uopen.read()

            response, content = http.request(url, 'GET', headers=headers, body=urllib.urlencode(body))
            if resp == 'VERIFIED':
                _logger.info('Paypal: validated data')
                cr, uid, context = request.cr, SUPERUSER_ID, request.context
                res = request.registry['payment.transaction'].form_feedback(cr, uid, post, 'paypal', context=context)
            elif resp == 'INVALID':
                _logger.warning('Paypal: answered INVALID on data verification')
            else:
                _logger.warning('Paypal: unrecognized paypal answer, received %s instead of VERIFIED or INVALID' % response)
            return True

class account_x_service_line(osv.osv, EDIMixin):
    _inherit='account.x.service.line'

    def edi_export(self, cr, uid, records, edi_struct=None, context=None):
        """Overridden to provide sale order line fields with the expected names
           (sale and purchase orders have different column names)"""
        edi_struct = dict(edi_struct or ACCOUNT_X_SERVICE_LINE_EDI_STRUCT)
        edi_doc_list = []
        for line in records:
            edi_doc = super(sale_order_line,self).edi_export(cr, uid, [line], edi_struct, context)[0]
            edi_doc['__import_model'] = 'account.x.service.line'
            edi_doc['service_qty'] = line.service_qty
            if line.product_uos:
                edi_doc.update(service_uom=line.service_uos,
                               service_qty=line.service_uos_qty)

            edi_doc_list.append(edi_doc)
        return edi_doc_list

class account_x_service_notify(osv.osv, EDIMixin):
    _inherit = 'account.x.service.notify'

    def edi_export(self, cr, uid, records, edi_struct=None, context=None):
        """Exports a account.x.service.notify"""
        edi_struct = dict(edi_struct or ACCOUNT_X_SERVICE__NOTIFY_EDI_STRUCT)
        res_company = self.pool.get('res.company')
        res_partner_obj = self.pool.get('res.partner')
        edi_doc_list = []
        for x_service_notify in records:
            # generate the main report
            self._edi_generate_report_attachment(cr, uid, x_service_notify, context=context)

            # Get EDI doc based on struct. The result will also contain all metadata fields and attachments.
            edi_doc = super(account_x_service_notify,self).edi_export(cr, uid, [x_service_notify], edi_struct, context)[0]
            edi_doc.update({
                    # force trans-typing to purchase.order upon import
                    '__import_model': 'account.x.service.notify',
                    '__import_module': 'rc_Cloudonthecloud',

                    'company_address': res_company.edi_export_address(cr, uid, account_x_service_notify.partner_id.company_id, context=context),
                    'partner_address': res_partner_obj.edi_export(cr, uid, [account_x_service_notify.partner_id], context=context)[0],

                    'currency': self.pool.get('res.currency').edi_export(cr, uid, [account_x_service_notify.partner_id.property_product_pricelist.currency_id],
                                                                         context=context)[0],
                    'partner_ref': False,
                    'notes':  False,
            })
            edi_doc_list.append(edi_doc)
        return edi_doc_list

    def _edi_import_company(self, cr, uid, edi_document, context=None):
        # TODO: for multi-company setups, we currently import the document in the
        #       user's current company, but we should perhaps foresee a way to select
        #       the desired company among the user's allowed companies

        self._edi_requires_attributes(('company_id','company_address'), edi_document)
        res_partner = self.pool.get('res.partner')

        xid, company_name = edi_document.pop('company_id')
        # Retrofit address info into a unified partner info (changed in v7 - used to keep them separate)
        company_address_edi = edi_document.pop('company_address')
        company_address_edi['name'] = company_name
        company_address_edi['is_company'] = True
        company_address_edi['__import_model'] = 'res.partner'
        company_address_edi['__id'] = xid  # override address ID, as of v7 they should be the same anyway
        if company_address_edi.get('logo'):
            company_address_edi['image'] = company_address_edi.pop('logo')
        company_address_edi['customer'] = True
        partner_id = res_partner.edi_import(cr, uid, company_address_edi, context=context)

        # modify edi_document to refer to new partner
        partner = res_partner.browse(cr, uid, partner_id, context=context)
        partner_edi_m2o = self.edi_m2o(cr, uid, partner, context=context)
        edi_document['partner_id'] = partner_edi_m2o
        edi_document['partner_invoice_id'] = partner_edi_m2o
        edi_document['partner_shipping_id'] = partner_edi_m2o

        edi_document.pop('partner_address', None) # ignored, that's supposed to be our own address!
        return partner_id

    def _edi_get_pricelist(self, cr, uid, partner_id, currency, context=None):
        # TODO: refactor into common place for purchase/sale, e.g. into product module
        partner_model = self.pool.get('res.partner')
        partner = partner_model.browse(cr, uid, partner_id, context=context)
        pricelist = partner.property_product_pricelist
        if not pricelist:
            pricelist = self.pool.get('ir.model.data').get_object(cr, uid, 'product', 'list0', context=context)

        if not pricelist.currency_id == currency:
            # look for a pricelist with the right type and currency, or make a new one
            pricelist_type = 'sale'
            product_pricelist = self.pool.get('product.pricelist')
            match_pricelist_ids = product_pricelist.search(cr, uid,[('type','=',pricelist_type),
                                                                    ('currency_id','=',currency.id)])
            if match_pricelist_ids:
                pricelist_id = match_pricelist_ids[0]
            else:
                pricelist_name = _('EDI Pricelist (%s)') % (currency.name,)
                pricelist_id = product_pricelist.create(cr, uid, {'name': pricelist_name,
                                                                  'type': pricelist_type,
                                                                  'currency_id': currency.id,
                                                                 })
                self.pool.get('product.pricelist.version').create(cr, uid, {'name': pricelist_name,
                                                                            'pricelist_id': pricelist_id})
            pricelist = product_pricelist.browse(cr, uid, pricelist_id)

        return self.edi_m2o(cr, uid, pricelist, context=context)

    def edi_import(self, cr, uid, edi_document, context=None):
        self._edi_requires_attributes(('company_id','company_address','order_line','date_notify','currency'), edi_document)

        #import company as a new partner
        partner_id = self._edi_import_company(cr, uid, edi_document, context=context)

        # currency for rounding the discount calculations and for the pricelist
        res_currency = self.pool.get('res.currency')
        currency_info = edi_document.pop('currency')
        currency_id = res_currency.edi_import(cr, uid, currency_info, context=context)
        order_currency = res_currency.browse(cr, uid, currency_id)

        partner_ref = edi_document.pop('partner_ref', False)
        edi_document['client_order_ref'] = edi_document['name']
        edi_document['name'] = partner_ref or edi_document['name']
        edi_document['note'] = edi_document.pop('notes', False)
        edi_document['pricelist_id'] = self._edi_get_pricelist(cr, uid, partner_id, order_currency, context=context)

        # discard web preview fields, if present
        edi_document.pop('amount_total', None)
        edi_document.pop('amount_tax', None)
        edi_document.pop('amount_untaxed', None)

        x_service_notify_lines = edi_document['notify_line_ids']
        for x_service_notify_line in x_service_notify_lines:
            self._edi_requires_attributes(('amount_total', 'amount_tax', 'amount_untaxed'), x_service_notify_line)

        return super(account_x_service_notify,self).edi_import(cr, uid, edi_document, context=context)

    def _edi_paypal_url(self, cr, uid, ids, field, arg, context=None):
        res = dict.fromkeys(ids, False)
        for account_x_service_notify in self.browse(cr, uid, ids, context=context):
            if account_x_service_notify.x_service_policy in ('prepaid', 'manual', 'invoiced') and \
                    account_x_service_notify.partner_id.company_id.paypal_account:
                params = {
                    "cmd": "_xclick",
                    "business": account_x_service_notify.partner_id.company_id.paypal_account,
                    "item_name": account_x_service_notify.partner_id.company_id.name + " Servizio " + account_x_service_notify.name,
                    "invoice": account_x_service_notify.notify_ref,
                    "item_number": account_x_service_notify.notify_ref,
                    "amount": account_x_service_notify.amount_total,
                    "currency_code": account_x_service_notify.partner_id.property_product_pricelist.currency_id.name,
                    "button_subtype": "services",
                    "no_note": "1",
                    "bn": "OpenERP_Order_PayNow_" + account_x_service_notify.partner_id.property_product_pricelist.currency_id.name,
                }
                res[account_x_service_notify.id] = "https://www.paypal.com/cgi-bin/webscr?" + url_encode(params)
        return res
    def _edi_paypal_status(self, cr, uid, ids, field, arg, context=None):
        res = dict.fromkeys(ids, False)
        for account_x_service_notify in self.browse(cr, uid, ids, context=context):
            if account_x_service_notify.paypal_url:
                if account_x_service_notify.partner_id.company_id.paypal_account:
                    params = {
                        "cmd": "_notify-validate",
                        "business": account_x_service_notify.partner_id.company_id.paypal_account,
                        "item_name": account_x_service_notify.partner_id.company_id.name + " Servizio " + account_x_service_notify.name,
                        "invoice": account_x_service_notify.notify_ref,
                        "amount": account_x_service_notify.amount_total,
                        "currency_code": account_x_service_notify.partner_id.property_product_pricelist.currency_id.name,
                        "button_subtype": "services",
                        "no_note": "1",
                        "bn": "OpenERP_Order_PayNow_" + account_x_service_notify.partner_id.property_product_pricelist.currency_id.name,
                        #"cmd": "_notify-validate",
                    }
                    """
                    urequest = urllib2.Request("https://www.sandbox.paypal.com/cgi-bin/webscr", werkzeug.url_encode(params))
                    urequest = urllib2.Request("https://www.paypal.com/cgi-bin/webscr", werkzeug.url_encode(params))
                    uopen = urllib2.urlopen(urequest)
                    resp = uopen.read()
                    print 'urequest',urequest
                    print 'uopen',uopen
                    print  'resp',resp
                    print 'response',response
                    if resp == 'VERIFIED':
                        #_logger.info('Paypal: validated data')
                        cr, uid, context = request.cr, SUPERUSER_ID, request.context
                        res = request.registry['payment.transaction'].form_feedback(cr, uid, post, 'paypal', context=context)
                    #elif resp == 'INVALID':
                        #_logger.warning('Paypal: answered INVALID on data verification')
                    #else:
                        #_logger.warning('Paypal: unrecognized paypal answer, received %s instead of VERIFIED or INVALID' % resp.text)
                    res[account_x_service_notify.id] = resp
                    return res
                    """
                    #url="https://www.paypal.com/cgi-bin/webscr?" + url_encode(params)
                    url="https://www.paypal.com/cgi-bin/webscr"# + url_encode(params)
                    #url="https://www.sandbox.paypal.com/cgi-bin/webscr"# + url_encode(params)
                    http = httplib2.Http()
                    request ="<tests><test>test</test></tests>" 
                    body = {'xml': request}
                    headers = {'Content-type': 'application/x-www-form-urlencoded'}
                    response, content = http.request(url, 'POST', headers=headers, body=urllib.urlencode(params))
                    res[account_x_service_notify.id] = content
                    #print 'content',content
                    #print 'response',response
                    
                    #res[account_x_service_notify.id] = paypal_obj.paypal_dpn(url)
        return res

    _columns = {
        'paypal_url': fields.function(_edi_paypal_url, type='char', string='Paypal Url',store=True),
        'paypal_status': fields.char('Paypal Status',size=64),

        #'paypal_status': fields.function(_edi_paypal_status, type='char', string='Paypal Status',store=True),
    }
class account_x_service_notify_line(osv.osv, EDIMixin):
    _inherit='account.x.service.line'

    def edi_export(self, cr, uid, records, edi_struct=None, context=None):
        """Overridden to provide sale order line fields with the expected names
           (sale and purchase orders have different column names)"""
        edi_struct = dict(edi_struct or ACCOUNT_X_SERVICE_NOTIFY_LINE_EDI_STRUCT)
        edi_doc_list = []
        for line in records:
            edi_doc = super(account_x_service_notify_line,self).edi_export(cr, uid, [line], edi_struct, context)[0]
            edi_doc['__import_model'] = 'account.x.service.notify.line'
            edi_doc['amount_total'] = line.amount_total
            edi_doc['amount_tax'] = line.amount_tax
            edi_doc['amount_untaxed'] = line.amount_untaxed
            edi_doc_list.append(edi_doc)
        return edi_doc_list
class x_portal_payment_acquirer(osv.osv):
    _name = 'x.portal.payment.acquirer'
    _description = 'Online Payment Acquirer'
    
    _columns = {
        'name': fields.char('Name', required=True),
        'form_template': fields.text('Payment form template (HTML)', translate=True, required=True), 
        'visible': fields.boolean('Visible', help="Make this payment acquirer available in portal forms (Customer invoices, etc.)"),
    }

    _defaults = {
        'visible': True,
    }

    def render(self, cr, uid, id, object, reference, currency, amount, context=None, **kwargs):
        """ Renders the form template of the given acquirer as a mako template  """
        if not isinstance(id, (int,long)):
            id = id[0]
        this = self.browse(cr, uid, id)
        if context is None:
            context = {}
        try:
            i18n_kind = _(object._description) # may fail to translate, but at least we try
            result = MakoTemplate(this.form_template).render_unicode(object=object,
                                                           reference=reference,
                                                           currency=currency,
                                                           amount=amount,
                                                           kind=i18n_kind,
                                                           quote=quote,
                                                           # context kw would clash with mako internals
                                                           ctx=context,
                                                           format_exceptions=True)
            return result.strip()
        except Exception:
            _logger.exception("failed to render mako template value for payment.acquirer %s: %r", this.name, this.form_template)
            return

    def _wrap_payment_block(self, cr, uid, html_block, amount, currency, context=None):
        if not html_block:
            link = '#action=account.action_account_config'
            payment_header = _('You can finish the configuration in the <a href="%s">Bank&Cash settings</a>') % link
            amount = _('No online payment acquirers configured')
            group_ids = self.pool.get('res.users').browse(cr, uid, uid, context=context).groups_id
            if any(group.is_portal for group in group_ids):
                return ''
        else:
            payment_header = _('Pay safely online')
            amount_str = float_repr(amount, self.pool.get('decimal.precision').precision_get(cr, uid, 'Account'))
            currency_str = currency.symbol or currency.name
            amount = u"%s %s" % ((currency_str, amount_str) if currency.position == 'before' else (amount_str, currency_str))
        result =  """<div class="payment_acquirers">
                         <div class="payment_header">
                             <div class="payment_amount">%s</div>
                             %s
                         </div>
                         %%s
                     </div>""" % (amount, payment_header)
        return result % html_block

    def render_payment_block(self, cr, uid, object, reference, currency, amount, context=None, **kwargs):
        """ Renders all visible payment acquirer forms for the given rendering context, and
            return them wrapped in an appropriate HTML block, ready for direct inclusion
            in an OpenERP v7 form view """
        acquirer_ids = self.search(cr, uid, [('visible', '=', True)])
        if not acquirer_ids:
            return
        html_forms = []
        for this in self.browse(cr, uid, acquirer_ids):
            content = this.render(object, reference, currency, amount, context=context, **kwargs)
            if content:
                html_forms.append(content)
        
        html_block = '\n'.join(filter(None,html_forms[0]))
        return self._wrap_payment_block(cr, uid, html_block, amount, currency, context=context)  
class x_portal_domain(osv.osv):
    _x_url_domain_block_proxy = lambda self, *a, **kw: self._x_url_domain_block(*a, **kw)
    def _get_default_company(self, cr, uid, context=None):
        company_id = self.pool.get('res.users')._get_company(cr, uid, context=context)
        if not company_id:
            raise osv.except_osv(_('Error!'), _('There is no default company for the current user!'))
        return company_id

    def _get_default_link(self, cr, uid, context=None):
        company_id = self.pool.get('res.users')._get_company(cr, uid, context=context)
        if company_id:
            company_id_obj=self.pool.get('res.company').browse(cr,uid,company_id,context=context)
            if company_id_obj:
                x_url_domain=company_id_obj.x_url_domain
            
            else:
                x_url_domain=None
        else:
                x_url_domain=None
            
        return x_url_domain
    def get_default_link(self, cr, uid, context=None):
        company_id = self.pool.get('res.users')._get_company(cr, uid, context=context)
        if company_id:
            company_id_obj=self.pool.get('res.company').browse(cr,uid,company_id,context=context)
            if company_id_obj:
                x_url_domain=company_id_obj.x_url_domain
            
            else:
                x_url_domain=None
        else:
                x_url_domain=None
            
        return x_url_domain

    def _get_default_partner(self, cr, uid, context=None):
        user_id_obj = self.pool.get('res.users').browse(cr,uid,uid,context=context)
        if not user_id_obj:
            raise osv.except_osv(_('Error!'), _('There is no default company for the current user!'))
        return user_id_obj.partner_id.id
    def _get_default_form_domain(self, cr, uid, context=None):
        company_id = self.pool.get('res.users')._get_company(cr, uid, context=context)
        user_id_obj = self.pool.get('res.users').browse(cr,uid,uid,context=context)
        if user_id_obj:
            partner_id=user_id_obj.partner_id.id
        else:
            partner_id=1
        
        partner_obj = self.pool.get('res.partner')       
        partner_obj.signup_prepare(cr, SUPERUSER_ID, partner_id)
        partner_id_obj = partner_obj.browse(cr,uid,partner_id,context=context)
        
        pricelist_obj = self.pool.get('product.pricelist')
        pricelist_version_obj = self.pool.get('product.pricelist.version')
        pricelist_item_obj = self.pool.get('product.pricelist.item')
        product_obj = self.pool.get('product.product')
        date_today=datetime.today()
        product_ids = product_obj.search(cr,SUPERUSER_ID,[('name_template','ilike','dominio')],context=context)
        hosting_product=[]
        hash_prod=''
        if partner_id_obj:
            token=partner_id_obj.signup_token
            if not token:
                token=''
        if product_ids:
                for product in product_obj.browse(cr,SUPERUSER_ID,product_ids,context):
                    if partner_id_obj:
                            price_surcharge = pricelist_obj.price_get(cr, SUPERUSER_ID, [partner_id_obj.property_product_pricelist[0].id],product.id, 1.0, partner_id_obj.id, {'uom': product.uom_id.id,'date': date_today}) [partner_id_obj.property_product_pricelist[0].id]
                            if not price_surcharge:
                                                pricelist_version_ids = pricelist_version_obj.search(cr, SUPERUSER_ID, [('pricelist_id','=', partner_id_obj.property_product_pricelist[0].id)])                                        
                                                if pricelist_version_ids:
                                                    pricelist_item_ids = pricelist_item_obj.search(cr, SUPERUSER_ID, [('product_id','=', product.id),('price_version_id','=',pricelist_version_ids[0])])    
                                                    if pricelist_item_ids:
                                                            pricelist_item_ids_rec = pricelist_item_obj.browse(cr, uid,pricelist_item_ids[0],context )      
                                                            price_surcharge=pricelist_item_ids_rec.price_surcharge
                            
                    else:
                                    price_surcharge=0

                    hosting_product.append({'id':product.id,
                                     'name':product.name,
                                     'price_surcharge':price_surcharge})
                    hash_prod=hash_prod+'&'+'product_id='+str(product.id)+'&'+'product_name='+str(product.name)+'&'+'product_price='+str(price_surcharge)
        if company_id:
            company_id_obj=self.pool.get('res.company').browse(cr,SUPERUSER_ID,company_id,context=context)
            if company_id_obj.x_url_domain:
                
                x_url_domain='<a style="margin-left: 120px;" href="%s?partner_id=%s&token=%s%s">COMPRA UN DOMINIO: %s </a>' % (company_id_obj.x_url_domain,str(partner_id_obj.id),token,hash_prod,company_id_obj.x_url_domain)
            
            else:
                x_url_domain=None
        else:
                x_url_domain=None

        return x_url_domain
    def render(self, cr, uid, id, object, context=None, **kwargs):
        """ Renders the form template of the given acquirer as a mako template  """
        if not isinstance(id, (int,long)):
            id = id[0]
        this = self.browse(cr, uid, id)

        if context is None:
            context = {}
        try:
            i18n_kind = _(object._description) # may fail to translate, but at least we try
            result = MakoTemplate(object.form_domain).render_unicode(object=object,                                                            
                                                            ctx=context,
                                                           format_exceptions=True)
            
            return result.strip()
        except Exception:
            _logger.exception("failed to render mako template value for domain %s: %r", this.name, this.form_domain)
            return
    def _wrap_url_domain_block(self, cr, uid, html_block, context=None):
        return html_block
    def render_url_domain_block(self, cr, uid, ids=None,object=None,  context=None, **kwargs):
        """ Renders all visible payment acquirer forms for the given rendering context, and
            return them wrapped in an appropriate HTML block, ready for direct inclusion
            in an OpenERP v7 form view """
        if ids:
            x_portal_domain_ids=ids
        else:
            user_id_obj = self.pool.get('res.users').browse(cr,uid,uid,context=context)
            if user_id_obj:
                partner_id=user_id_obj.partner_id.id
            else:
                partner_id=1
            x_portal_domain_ids = self.search(cr, uid, [('partner_id', '=', partner_id)])
    
        if not x_portal_domain_ids:
            return
        html_forms = []
        for this in self.browse(cr, uid, x_portal_domain_ids):
            content = this.render(object,  context=context, **kwargs)
            if content:
                html_forms.append(content)
        html_block = '\n'.join(filter(None,html_forms[0]))
        return self._wrap_url_domain_block(cr, uid, html_block, context=context)  
    def _x_url_domain_block(self, cr, uid, ids, fieldname, arg, context=None):
        if fieldname:
            result = dict.fromkeys(ids, False)
        else:
            result={}
        #x_portal_domain_obj = self.pool.get('x.portal.domain')
                     
        for this in self.browse(cr, uid, ids, context=context):
                if fieldname:
                    result[this.id] = self.render_url_domain_block(cr, uid,ids, this, context=context)
                else:
                    result = self.render_url_domain_block(cr, uid,ids, this, context=context)
                    
        return result
    def _x_url_domain_block_2(self, cr, uid, context=None):
        #x_portal_domain_obj = self.pool.get('x.portal.domain')
                     
        this=self.browse(cr, uid, [0], context=context)
        result = self.render_url_domain_block(cr, uid,None, this, context=context)
        return result

    _name = 'x.portal.domain'
    _description = 'x portal domain'
    _columns = {
        'name': fields.char('Nome Domino',size=128, required=True),
        #'partner_id': fields.many2one('res.partner', 'Cliente', required=True, select=True),
        'partner_id': fields.many2one('res.partner', 'Cliente', readonly=True, states={'draft': [('readonly', False)]}, required=True, change_default=True, select=True, track_visibility='always'),
 
        'form_domain': fields.text('Link acquisizione dominio', translate=True, required=True), 
        'visible': fields.boolean('Visible', help="visibile"),
        'company_id': fields.many2one('res.company', 'Company'),
        'domain': fields.char('sotto Dominio ', size=128 ),
        'x_url_domain_option': fields.function(_x_url_domain_block_proxy, type="html", string="Clicca sul link "),
        'state': fields.selection([
            ('draft', 'Bozza'),
            ('done', 'Attivato'),
            ('cancel', 'Cancellato'),
            ('sent', 'inviato'),
            ('error', 'errore'),
            ], 'Status', readonly=True, help="Stati dominio", select=True),
        'message': fields.text('Messaggio di ritorno',readonly=True), 

    }

    _defaults = {
        'form_domain': _get_default_form_domain,
        'name': 'Dominio-',
        'state': 'draft',
        'partner_id': _get_default_partner,
        'company_id': _get_default_company,
        'visible': True,
        'x_url_domain_option': _x_url_domain_block_2,
    }
    def confirm_dummy(self, cr, uid, ids, context=None):
                    vals={'state':'sent'}
                    self.write(cr,uid,ids,vals)
 
    def request_url_post(self, cr, uid, ids, context=None):
        pricelist_obj = self.pool.get('product.pricelist')
        pricelist_version_obj = self.pool.get('product.pricelist.version')
        pricelist_item_obj = self.pool.get('product.pricelist.item')
        product_obj = self.pool.get('product.product')
        date_today=datetime.today()
        res = False
        x_portal_domain_ids=ids
        if x_portal_domain_ids:
            x_portal_domain_id_obj = self.pool.get('x.portal.domain').browse(cr,uid,ids,context)
            product_ids = product_obj.search(cr,SUPERUSER_ID,[('name_template','ilike','hosting')],context=context)
            hosting_product=[]
            if product_ids:
                for product in product_obj.browse(cr,SUPERUSER_ID,product_ids,context):
                    if x_portal_domain_id_obj.partner_id:
                            price_surcharge= pricelist_obj.price_get(cr, SUPERUSER_ID, [x_portal_domain_id_obj.partner_id.property_product_pricelist[0].id],product.id, 1.0, x_portal_domain_id_obj.partner_id.id, {'uom': product.uom_id.id,'date': date_today}) [x_portal_domain_id_obj.partner_id.property_product_pricelist[0].id]
                            if not price_surcharge:
                                                pricelist_version_ids = pricelist_version_obj.search(cr, SUPERUSER_ID, [('pricelist_id','=', x_portal_domain_id_obj.partner_id.property_product_pricelist[0].id)])                                        
                                                if pricelist_version_ids:
                                                    pricelist_item_ids = pricelist_item_obj.search(cr, SUPERUSER_ID, [('product_id','=', product.id),('price_version_id','=',pricelist_version_ids[0])])    
                                                    if pricelist_item_ids:
                                                            pricelist_item_ids_rec = pricelist_item_obj.browse(cr, SUPERUSER_ID,pricelist_item_ids[0],context )      
                                                            price_surcharge=pricelist_item_ids_rec.price_surcharge
                            
                    else:
                                    price_surcharge=0

                    hosting_product.append({'id':product.id,
                                     'name':product.name,
                                     'price_surcharge':price_surcharge})
                    
            res = False
            url = x_portal_domain_id_obj.company_id.x_url_domain
            #headers = {'Content-type': 'application/x-www-form-urlencoded'}
            headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
            data = {'partner_id':x_portal_domain_id_obj.partner_id.id ,'name_domain':x_portal_domain_id_obj.name, 'product_ids':hosting_product }
            http = httplib2.Http()
            
            #request ="<TESTS><TEST></TEST></TESTS>" 
            #body = {'xml': request}
            #urllib.urlopen(url)
            #resp = urllib.read()
            data_1 = urllib.urlencode(data)
            data_1 = data_1.encode('utf-8') # data should be bytes
            u_reponse=urllib.urlopen(url, data_1)
            the_page=u_reponse.read
            cj = CookieJar()
            cj_opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
            cj_response = cj_opener.open(url, data_1)
            urequest = urllib2.Request(url,data_1)
            uopen = urllib2.urlopen(urequest)
            resp = uopen.read()
            
            
            #data=json.dumps(data),
            #response, content = http.request(url, 'post', headers=headers, body=urllib.urlencode(body))
            response = requests.post(url,headers=headers,data=json.dumps(data)  )
            session_id=requests.session()
            sess_get=session_id.get(url, allow_redirects=False)
            res=session_id.resolve_redirects(sess_get, sess_get.request)
            print res
            if str(response.status_code) == '200':
                    vals={'state':'sent','message':str(response.status_code)+str(response.content) }
                    self.write(cr,uid,ids,vals)
            else:
                    vals={'state':'error','message':str(response.status_code)+str(response.content)}
                    self.write(cr,uid,ids,vals)
            view_ref = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'rc_Cloudonthecloud', 'x_portal_domain_form_2')
            view_id = view_ref and view_ref[1] or False,
            return {
                'type': 'ir.actions.act_window',
                'name': _('Servizi Cloud'),
                'res_model': 'x.portal.domain',
                'res_id': ids[0],
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': view_id,
                'target': 'current',
                'nodestroy': True,
            }

    def get_form_domain(self, cr, uid,ids,partner_id, context=None):
        partner_obj = self.pool.get('res.partner')
        if not partner_id:
            partner_id=self._get_default_partner(cr, uid, context)
        partner_obj.signup_prepare(cr, SUPERUSER_ID, partner_id,context=context)
        partner_id_obj = partner_obj.browse(cr,uid,partner_id,context=context)
        if partner_id_obj:
            token=partner_id_obj.signup_token
            if not token:
                token=''
            company_id=partner_id_obj.company_id
        
        pricelist_obj = self.pool.get('product.pricelist')
        pricelist_version_obj = self.pool.get('product.pricelist.version')
        pricelist_item_obj = self.pool.get('product.pricelist.item')
        product_obj = self.pool.get('product.product')
        date_today=datetime.today()
        product_ids = product_obj.search(cr,SUPERUSER_ID,[('name_template','ilike','dominio')],context=context)
        hosting_product=[]
        hash_prod=''

        if product_ids:
                for product in product_obj.browse(cr,SUPERUSER_ID,product_ids,context):
                    if partner_id_obj:
                            price_surcharge= pricelist_obj.price_get(cr, SUPERUSER_ID, [partner_id_obj.property_product_pricelist[0].id],product.id, 1.0, partner_id_obj.id, {'uom': product.uom_id.id,'date': date_today}) [partner_id_obj.property_product_pricelist[0].id]
                            if not price_surcharge:
                                                pricelist_version_ids = pricelist_version_obj.search(cr, SUPERUSER_ID, [('pricelist_id','=', partner_id_obj.property_product_pricelist[0].id)])                                        
                                                if pricelist_version_ids:
                                                    pricelist_item_ids = pricelist_item_obj.search(cr, SUPERUSER_ID, [('product_id','=', product.id),('price_version_id','=',pricelist_version_ids[0])])    
                                                    if pricelist_item_ids:
                                                            pricelist_item_ids_rec = pricelist_item_obj.browse(cr, SUPERUSER_ID,pricelist_item_ids[0],context )      
                                                            price_surcharge=pricelist_item_ids_rec.price_surcharge
                            
                    else:
                                    price_surcharge=0


                    hosting_product.append({'id':product.id,
                                     'name':product.name,
                                     'price_surcharge':price_surcharge})
                    hash_prod=hash_prod+'&'+'product_id='+str(product.id)+'&'+'product_name='+str(product.name)+'&'+'product_price='+str(price_surcharge)
        if company_id:
            company_id_obj=self.pool.get('res.company').browse(cr,SUPERUSER_ID,company_id.id,context=context)
            if company_id_obj.x_url_domain:
                
                x_url_domain='<a style="margin-left: 120px;" href="%s?x_portal_domain_id=%s&partner_id=%s&token=%s%s">COMPRA UN DOMINIO: %s </a>' % (company_id_obj.x_url_domain,str(ids[0]),str(partner_id_obj.id),token,hash_prod,company_id_obj.x_url_domain)
            
            else:
                x_url_domain=None
        else:
                x_url_domain=None

        return x_url_domain
    def partner_id_change(self, cr, uid, ids, partner_id=False, context=None):
        context = context or {}
        warning = {}
        domain = {}
        result = {}
        user_obj=self.pool.get('res.users')
        partner_obj = self.pool.get('res.partner')
        if partner_id:
                partner_id_obj=partner_obj.browse(cr, uid, partner_id, context=context)
                if not ids:
                    id=self.create(cr,uid,{})
                    ids=[id]
                result['form_domain']=self.get_form_domain(cr, uid,ids, partner_id, context)              
                self.write(cr,uid,ids,{'form_domain':result['form_domain'],'partner_id':partner_id},context=context)
                fieldname=None
                arg=None
                result['x_url_domain_option']=self._x_url_domain_block(cr, uid, ids, fieldname, arg, context)               
                return {'value': result, 'domain': domain, 'warning': warning}
    def create_sale(self, cr, uid, ids,post,  context=None):
        if ids:
            ids_decode=str(ids).decode()
            ids_num=int(ids_decode)
            ids=ids_num
            db_name = cr.dbname
            pool = pooler.get_pool(db_name)
            x_portal_domain_obj=self.pool.get('x.portal.domain')
            this = x_portal_domain_obj.browse(cr, uid, ids,context=context)
        else:
            this = None            
        sale_shop_obj = pool.get('sale.shop')
        site_sale_obj = pool.get('product.site.sale')
        order_obj = pool.get('sale.order')
        order_line_obj = pool.get('sale.order.line')
        order_tax_obj = pool.get('sale.order.tax')
        partner_obj = pool.get('res.partner')
        province_obj = pool.get('res.province')
        country_obj = pool.get('res.country')
        product_obj = pool.get('product.product')
        product_tax = pool.get('product.taxes.rel')
        supplier_obj = pool.get('product.supplierinfo')
        account_invoice_obj= pool.get('account.invoice')
        categ_obj=pool.get('product.category')
        um_obj=pool.get('product.uom')
        tax_obj=pool.get('account.tax')
        payment_term_obj=pool.get('account.payment.term')
        pricelist_obj = pool.get('product.pricelist')
        pricelist_item_obj = pool.get('product.pricelist.item')
        pricelist_version_obj = pool.get('product.pricelist.version')
        stock_picking_obj = pool.get('stock.picking.out')
        workflow_job = pool.get('product.workflow.job')
        invoice_obj=pool.get('account.invoice')
        invoice_line_obj=pool.get('account.invoice.line')
        can_obj=pool.get('product.export.can')
        ir_mail_obj = pool.get('ir.mail_server')
        order_sale={}
        date_today=datetime.today()
        str_partner_id=str(post.get('partner_id','0'))
        token=str(post.get('token',''))
        partner_id=int(str_partner_id)
        if token!='' and partner_id!=0 :
            partner_ids = partner_obj.search(cr, uid, [('signup_token', '=', token),('id', '=', partner_id)], context=context)
            if partner_ids:
                    partner_ids_rec = partner_obj.browse(cr, uid, partner_ids[0],context=context)
                    if partner_ids_rec.property_payment_term:
                        property_payment_term=partner_ids_rec.property_payment_term[0].id
                    else:
                        property_payment_term=1
            else:
                    partner_ids_rec=None            

        elif token!='' and partner_id==0:
            partner_ids = partner_obj.search(cr, uid, [('signup_token', '=', token)], context=context)
            if partner_ids:
                    partner_ids_rec = partner_obj.browse(cr, uid, partner_ids[0],context=context)
                    if partner_ids_rec.property_payment_term:
                        property_payment_term=partner_ids_rec.property_payment_term[0].id
                    else:
                        property_payment_term=1
            else:
                    partner_ids_rec=None            
        elif token=='' and partner_id!=0:
            partner_ids = partner_obj.search(cr, uid, [('id', '=', partner_id)], context=context)
            if partner_ids:
                    partner_ids_rec = partner_obj.browse(cr, uid, partner_ids[0],context=context)
                    if partner_ids_rec.property_payment_term:
                        property_payment_term=partner_ids_rec.property_payment_term[0].id
                    else:
                        property_payment_term=1
            else:
                    partner_ids_rec=None            
        else:
                    partner_ids_rec=None      
        if partner_ids_rec:
                        crea_sale=True
                        if this:
                            vals={
                                 'name':'PORT-'+str(this.id),
                                 'partner_id':partner_ids_rec.id,                             
                                 'partner_invoice_id':partner_ids_rec.id,
                                 'partner_shipping_id':partner_ids_rec.id,
                                 'date_order':date_today,
                                 'payment_term':property_payment_term,
                                 'pricelist_id':partner_ids_rec.property_product_pricelist[0].id,
                                 'state':'draft'
    
                            }# skip empty rows and rows where the translation field (=last fiefd) is empty
                        else:
                            vals={
                                'partner_id':partner_ids_rec.id,                             
                                 'partner_invoice_id':partner_ids_rec.id,
                                 'partner_shipping_id':partner_ids_rec.id,
                                 'date_order':date_today,
                                 'payment_term':property_payment_term,
                                 'pricelist_id':partner_ids_rec.property_product_pricelist[0].id,
                                 'state':'draft'
    
                            }# skip empty rows and rows where the translation field (=last fiefd) is empty
                        print "TESTATA_ORDINE",vals        
                        order_ids=order_obj.search(cr,uid,[('name','=',vals['name'])],context=context)
                        if not order_ids:
                            order_ids_id=order_obj.create(cr, uid, vals, context=context)
                        else:
                            order_ids_id=order_ids[0]
                        sequence=0
                        line_row=0
                        if crea_sale==True or crea_sale==False:
                            partner_ids_id=partner_ids_rec.id
                            """creo righe ordine"""
                            sequence +=10
                            product_id=int(str(post['product_id']).decode())
                            prod_ids = product_obj.search(cr, uid, [('id','=', product_id)],context=context)
                            if prod_ids:    
                                    prod_ids_rec = product_obj.browse(cr, uid,prod_ids[0],context )      
                                    order_line_ids = order_line_obj.search(cr, uid, [('order_id','=', order_ids_id),('sequence','=', sequence)])    
                                    product_price=float(str(post.get('product_price',0)).decode())
                                    price_surcharge=product_price
                                    if price_surcharge==0:
                                        """metto il prezzo del listino corrispondente"""       
                                        price_surcharge,listino_id = pricelist_obj.price_get(cr, uid, vals['pricelist_id'],prod_ids_rec.id, 1.0, partner_ids_id, {'uom': prod_ids_rec.uom_id.id,'date': date_today}) ,vals['pricelist_id']
                                        print '[[[[price_surcharge]]]]',price_surcharge

                                        if not price_surcharge:
                                            pricelist_version_ids = pricelist_version_obj.search(cr, uid, [('pricelist_id','=', pricelist_id)])                                        
                                            if pricelist_version_ids:
                                                pricelist_item_ids = pricelist_item_obj.search(cr, uid, [('product_id','=', prod_ids_rec.id),('price_version_id','=',pricelist_version_ids[0])])    
                                                if pricelist_item_ids:
                                                    pricelist_item_ids_rec = pricelist_item_obj.browse(cr, uid,pricelist_item_ids[0],context )      
                                                    price_surcharge=pricelist_item_ids_rec.price_surcharge
                                       
                                    if not str(price_surcharge).replace('.', '').isdigit():
                                        price_surcharge=price_surcharge[listino_id]
                                        print '{{price_surcharge}}',price_surcharge

                                    """ aliquota iva"""
                                    if prod_ids_rec.taxes_id:
                                        tax_ids = tax_obj.search(cr, uid, [('id','=', prod_ids_rec.taxes_id[0].id)])    
                                    else:
                                        tax_ids=[]
                                    if not tax_ids:
                                # lets create the language with locale information
                                         tax_ids_id=None
                                    else:   
                                   
                                         tax_ids_id=tax_ids[0]
                                    
                                    """controllo l'unità di misura"""
                                    if not prod_ids_rec.uom_id:
                                         um_ids_id=0
                                    else:
                                         um_ids_id=prod_ids_rec.uom_id.id
                                    #prezzo_ivato=(float(order_sale_line["Price"])*(100+tax_ids[0]amount])))/100
                                    if not prod_ids_rec.default_code:
                                        prod_ids_rec.default_code=''
                                    if  post.get('domain_name',None):
                                        domain_name=str(post['domain_name']).decode()
                                    else:
                                        domain_name=prod_ids_rec.name

                                    vals={
                                         'order_id':order_ids_id,
                                         'price_unit':price_surcharge,
                                         'product_id':prod_ids[0],
                                         'name':str('[' + prod_ids_rec.default_code +']'+domain_name),
                                         'order_partner_id':partner_ids_id,
                                         'product_uos_qty':1,
                                         'product_uos':prod_ids_rec.uom_id.id,
                                         'product_uom_qty':1,
                                         'product_uom':prod_ids_rec.uom_id.id,
                                         'purchase_price':prod_ids_rec.standard_price,
                                         'sequence':sequence,
               
                                         
                                          }# skip empty rows and rows where the translation field (=last fiefd) is empty
                                    print 'RECSALE-RECSALE-->',vals
                                    if not order_line_ids:                     # lets create the language with locale information
                                         line_row +=1
                                         order_line_ids_id=order_line_obj.create(cr, uid, vals, context=context)
                                         
                                    else:
                                         line_row +=1
                                         order_line_ids_id=order_line_ids[0]
                                         #cr.execute('delete from sale_order_line where product_id=%s and (order_id=%s)',(prod_ids[0],order_ids_id))   
                                         order_line_obj.write(cr, uid, order_line_ids_id, vals, context)
                                    if tax_ids_id:
                                        cr.execute('insert into sale_order_tax (order_line_id,tax_id) '
                                               'select %s,%s where not exists '
                                               '(select * from sale_order_tax where order_line_id=%s and tax_id=%s)',
                                               (order_line_ids_id, tax_ids_id,order_line_ids_id, tax_ids_id))

                        ord_ids_id_list=[order_ids_id]
                        order_obj.action_button_confirm(cr, uid, ord_ids_id_list, context)
                        #order_obj.write_margin(cr, uid, ord_ids_id_list, context)
                        order_ids__rec = order_obj.browse(cr, uid,order_ids_id,context )            
                        mtp_obj = self.pool.get('email.template')
                        try:
                                    template_ids = mtp_obj.search(cr, uid, [('name','ilike', '%MM_DOMINIO%')])
                                                #template_id = ir_model_data.get_object_reference(cr, uid, 'rc_Cloudonthecloud', 'email_template_edi_account_x_service_01')[1]
                                    if template_ids:    
                                                    template_id=template_ids[0]
                                    else:
                                                    template_id=False     
                        except ValueError:
                                    template_id = False
                        mtp_obj.send_mail(cr, uid,template_id, order_ids_id, context=context)
                        
        return 'OK'+'&'+str(order_ids_id)
class sale_order(osv.Model):
    _inherit = 'sale.order'
    def _portal_payment_block(self, cr, uid, ids, fieldname, arg, context=None):
        res=super(sale_order, self)._portal_payment_block(cr, SUPERUSER_ID, ids, fieldname,arg,context=context)
        result = dict.fromkeys(ids, False)
        x_payment_acquirer = self.pool['x.portal.payment.acquirer']
        acquirer_obj = self.pool.get('payment.acquirer')
        transaction_obj = self.pool.get('payment.transaction')
        for this in self.browse(cr, SUPERUSER_ID, ids, context=context):
            if this.state not in ('draft', 'cancel') and not this.invoiced:

                result[this.id] = x_payment_acquirer.render_payment_block(
                    cr, uid, this, this.name,
                    this.partner_id.property_product_pricelist.currency_id, this.amount_total, context=context)
                trans_ids=transaction_obj.search(cr,SUPERUSER_ID,[('sale_order_id','=',this.id)])
                aquirer_ids=acquirer_obj.search(cr,SUPERUSER_ID,[('name','=','Paypal')])
                if this.partner_id.country_id:
                        country_id=this.partner_id.country_id.id
                else:
                        country_id=110               
                if not country_id:
                        country_id=110
                if aquirer_ids:
                    acquirer_id=aquirer_ids[0]
                    if  not trans_ids:         
                                   tx_id = transaction_obj.create(cr,SUPERUSER_ID, {
                                    'acquirer_id': acquirer_id,
                                    'type': 'form',
                                    'amount': this.amount_total,
                                    'currency_id': this.partner_id.property_product_pricelist.currency_id.id,
                                    'partner_id': this.partner_id.id,
                                    'partner_country_id': country_id,
                                    'reference': this.name,
                                    'sale_order_id': this.id,
                                }, context=context)
                    else:
                                   transaction_obj.write(cr,SUPERUSER_ID,trans_ids[0], {
                                    'amount': this.amount_total,
                                }, context=context)
        return result


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
