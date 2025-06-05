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
from openerp import SUPERUSER_ID
from openerp import netsvc
import openerp.addons.decimal_precision as dp
import xxsubtype
import itertools
from lxml import etree
from openerp import api
from openerp import SUPERUSER_ID
import tempfile
import csv
from string import strip
from openerp.tools.misc import ustr
import re
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
import logging
_logger = logging.getLogger(__name__)
try:
    import vatnumber
except ImportError:
    _logger.warning("VAT validation partially unavailable because the `vatnumber` Python library cannot be found. "
                                          "Install it to support more countries, for example with `easy_install vatnumber`.")
    vatnumber = None
from openerp import models, fields as x_fields, _
from openerp import api, _
import math

from openerp.tools.float_utils import float_round
from openerp.exceptions import ValidationError



class sale_order(osv.osv):
    _inherit = 'sale.order'
    @api.multi
    def action_invoice_create(self,grouped=False, states=None, date_invoice = False):
        if date_invoice==False:
            date_invoice=datetime.today()
        print 'date_invoice',date_invoice
        res=super(sale_order, self).action_invoice_create(grouped=grouped, states=states, date_invoice = date_invoice)
        return res
    @api.multi
    def convert_2float(self, value, precision=dp.get_precision('account_2_cifre'), currency_obj=None, context=None):
    
        fmt = '%f' if precision is None else '%.{precision}f'
    
        lang_code = self.env.context.get('lang') or 'en_US'
    
        lang = self.pool['res.lang']
    
        formatted = lang.format(self.env.cr, self.env.uid, [lang_code], fmt.format(precision=precision), value, grouping=True,     monetary=True)
    
        if currency_obj:
    
            if currency_obj.position == 'before':
        
                formatted = currency_obj.symbol + ' ' + formatted
        
            else:
        
                formatted = formatted + ' ' + currency_obj.symbol
        
            return formatted
class StockPickingPackagePreparation(osv.osv):
    _inherit = 'stock.picking.package.preparation'
    date_done = x_fields.Datetime(
        string='Shipping Date',
        readonly=False,
    )
    @api.constrains('picking_ids')
    def _check_multiple_picking_ids(self):
        for package in self:
            if not package.ddt_type_id:
                continue
            if not package.ddt_type_id.restrict_pickings:
                continue
            for picking in package.picking_ids:
                other_ddts = picking.ddt_ids - package
                if other_ddts:
                    raise ValidationError(
                        _("The picking %s is already in DDT %s")
                        % (picking.name_get()[0][1],
                           other_ddts.name_get()[0][1]))


class DdTCreateInvoice(models.TransientModel):
    _inherit = "ddt.create.invoice"
    @api.multi
    def create_invoice(self):
        res=super(DdTCreateInvoice, self).create_invoice()
        #ddt_str=''
        ddt_ids_obj=self.env['stock.picking.package.preparation'].browse(self.env.context.get('active_ids',[]))
        doc_type_id_obj=self.env['fiscal.document.type'].search([('code','ilike','TD24')])
        
        ddt_str={}
        for ddt_id_obj in ddt_ids_obj:
                if ddt_id_obj:
                    if ddt_id_obj.ddt_number==False:
                       ddt_id_obj.write({'ddt_number':'NO_DDT_NUM'})

                if self.group:
                    if ddt_str.get(str(ddt_id_obj.partner_id.id),None)==None:
                        ddt_str[str(ddt_id_obj.partner_id.id)]=''
                    ddt_str[str(ddt_id_obj.partner_id.id)]= ddt_str[str(ddt_id_obj.partner_id.id)]+'-' + ddt_id_obj.ddt_number+ ' '+datetime.strptime(str(ddt_id_obj.date)[0:10],'%Y-%m-%d').strftime('%d-%m-%Y')
                else:
                    if ddt_str.get(str(ddt_id_obj.id),None)==None:
                        ddt_str[str(ddt_id_obj.id)]=''
                    ddt_str[str(ddt_id_obj.id)]= ddt_str[str(ddt_id_obj.id)]+'-' + ddt_id_obj.ddt_number+ ' '+datetime.strptime(str(ddt_id_obj.date)[0:10],'%Y-%m-%d').strftime('%d-%m-%Y')
                    
        
        for ddt_id_obj in ddt_ids_obj:
            val_ddt=None
            val_ddt={ 'origin': ddt_str[str(ddt_id_obj.partner_id.id)] if self.group else ddt_str[str(ddt_id_obj.id)] ,       
                                            'x_pack_ids':[(6, 0, [ddt_id_obj.id])],
                                            }
            if doc_type_id_obj and ddt_id_obj.ddt_number!='NO_DDT_NUM':
                val_ddt.update({'fiscal_document_type_id':doc_type_id_obj.id})
                
            if val_ddt:
                invoice_id_obj = ddt_id_obj.invoice_id.write(val_ddt
                                                      
                                                      )
        return res
class account_invoice(models.Model):
    _inherit = 'account.invoice'
    x_pack_ids = x_fields.Many2many('stock.picking.package.preparation',
        'stock_picking_package_preparation_invoice',  'invoice_id','pack_id',
        string='DDT')
    @api.multi
    def invoice_print(self):
        """ Print the invoice and mark it as sent, so that we can see more
            easily the next step of the workflow
        """
        assert len(self) == 1, 'This option should only be used for a single id at a time.'
        self.sent = True
        return self.env['report'].get_action(self, 'prof_fattacc.report_invoice')
    
    def convert_2float(self, value, precision=dp.get_precision('account_2_cifre'), currency_obj=None, context=None):
    
        fmt = '%f' if precision is None else '%.{precision}f'
    
        lang_code = self.env.context.get('lang') or 'en_US'
    
        lang = self.pool['res.lang']
    
        formatted = lang.format(self.env.cr, self.env.uid, [lang_code], fmt.format(precision=precision), value, grouping=True,     monetary=True)
    
        if currency_obj:
    
            if currency_obj.position == 'before':
        
                formatted = currency_obj.symbol + ' ' + formatted
        
            else:
        
                formatted = formatted + ' ' + currency_obj.symbol
        
            return formatted
account_invoice()
class stock_picking(osv.osv):
    _inherit="stock.picking"
    def action_assign_cron(self,cr,uid,ids=None,cron=False,context=None):
        print 'context',context
        if cron==True:
            ids = self.search(cr,uid,[('state','in',('confirmed', 'waiting'))])
        else:
            if context:
                ids=context.get('active_ids',None)
            else:
                ids=None
        if ids:
            if context.get('active_model',None)=='sale.order':
                ids_pick=[]
                for sale in self.pool.get('sale.order').browse(cr,uid,ids,context):
                    for pick in sale.picking_ids:
                        ids_pick.append(pick.id)
            else:
                ids_pick=ids   
            for pick in self.browse(cr, uid, ids_pick, context):
                if pick.state in ('cancel', 'assigned','done'):
                    ids_pick.remove(pick.id)
                    continue
                if pick.state == 'draft':
                    self.action_confirm(cr, uid, [pick.id], context=context)

                self.do_unreserve(cr, uid, [pick.id], context=context)
                self.action_assign(cr, uid, [pick.id], context=context)
            if cron==False:
                    if len(ids_pick)>0:
                        view_ref = self.pool.get('ir.model.data').get_object_reference(cr,uid,'stock', 'view_picking_form')
                        view_id = view_ref and view_ref[1] or False,
                        return {'name':_("Picking elaborati"),
                            'view_mode': 'form' if len(ids_pick)==1 else 'tree,form',
                            'view_id': view_id if len(ids_pick)==1 else False,
                            'view_type': 'form',
                            'res_model': 'stock.picking',
                            'res_id': ids_pick[0] if len(ids_pick)==1 else None,
                            'type': 'ir.actions.act_window',
                            'nodestroy': True,
                            'target': 'normal',
                            'domain': [('id','in',tuple(ids_pick))],                                 
                            'context': context,                                 
                        }
                    else:
                            return {'name':_("Gli ordini  erano già disponibili"),
                        'view_mode': 'tree,form',
                        'view_id': None ,
                        'view_type': 'form',
                        'res_model': context.get('active_model',None),
                        'res_id': None,
                        'type': 'ir.actions.act_window',
                        'nodestroy': True,
                        'target': 'normal',
                        'domain': [('id','in',tuple(context.get('active_ids',None)))],                                 
                        'context': context,                                 
                    }

            else:
                    return True
        else:
            return False
    def _invoice_create_line(self, cr, uid, moves, journal_id, inv_type='out_invoice', context=None):
        invoice_obj = self.pool.get('account.invoice')
        move_obj = self.pool.get('stock.move')
        invoices = {}
        is_extra_move, extra_move_tax = move_obj._get_moves_taxes(cr, uid, moves, inv_type, context=context)
        product_price_unit = {}
        for move in moves:
            company = move.company_id
            origin = move.picking_id.name
            partner, user_id, currency_id = move_obj._get_master_data(cr, uid, move, company, context=context)
            """ rocco li 13-07-2017 rottura fattura solo partner e non per utente"""
            #key = (partner, currency_id, company.id, user_id)
            key = (partner, currency_id, company.id, uid)
            """ rocco li 13-07-2017 """
            
            invoice_vals = self._get_invoice_vals(cr, uid, key, inv_type, journal_id, move, context=context)

            if key not in invoices:
                # Get account and payment terms
                invoice_id = self._create_invoice_from_picking(cr, uid, move.picking_id, invoice_vals, context=context)
                invoices[key] = invoice_id
            else:
                invoice = invoice_obj.browse(cr, uid, invoices[key], context=context)
                merge_vals = {}
                if not invoice.origin or invoice_vals['origin'] not in invoice.origin.split(', '):
                    invoice_origin = filter(None, [invoice.origin, invoice_vals['origin']])
                    merge_vals['origin'] = ', '.join(invoice_origin)
                if invoice_vals.get('name', False) and (not invoice.name or invoice_vals['name'] not in invoice.name.split(', ')):
                    invoice_name = filter(None, [invoice.name, invoice_vals['name']])
                    merge_vals['name'] = ', '.join(invoice_name)
                if merge_vals:
                    invoice.write(merge_vals)
            invoice_line_vals = move_obj._get_invoice_line_vals(cr, uid, move, partner, inv_type, context=dict(context, fp_id=invoice_vals.get('fiscal_position', False)))
            invoice_line_vals['invoice_id'] = invoices[key]
            invoice_line_vals['origin'] = origin
            if not is_extra_move[move.id]:
                product_price_unit[invoice_line_vals['product_id'], invoice_line_vals['uos_id']] = invoice_line_vals['price_unit']
            if is_extra_move[move.id] and (invoice_line_vals['product_id'], invoice_line_vals['uos_id']) in product_price_unit:
                invoice_line_vals['price_unit'] = product_price_unit[invoice_line_vals['product_id'], invoice_line_vals['uos_id']]
            if is_extra_move[move.id]:
                desc = (inv_type in ('out_invoice', 'out_refund') and move.product_id.product_tmpl_id.description_sale) or \
                    (inv_type in ('in_invoice','in_refund') and move.product_id.product_tmpl_id.description_purchase)
                invoice_line_vals['name'] += ' ' + desc if desc else ''
                if extra_move_tax[move.picking_id, move.product_id]:
                    invoice_line_vals['invoice_line_tax_id'] = extra_move_tax[move.picking_id, move.product_id]
                #the default product taxes
                elif (0, move.product_id) in extra_move_tax:
                    invoice_line_vals['invoice_line_tax_id'] = extra_move_tax[0, move.product_id]

            move_obj._create_invoice_line_from_vals(cr, uid, move, invoice_line_vals, context=context)
            move_obj.write(cr, uid, move.id, {'invoice_state': 'invoiced'}, context=context)

        invoice_obj.button_compute(cr, uid, invoices.values(), context=context, set_total=(inv_type in ('in_invoice', 'in_refund')))
        return invoices.values()

class report_invoice_acc(models.AbstractModel):
    #Do not touch _name it must be same as _inherit
    #_name = 'report.report_invoice'
    _name = 'report.prof_fattacc.report_invoice_acc'
    
    def convert_2float(self, value, precision=dp.get_precision('account_2_cifre'), currency_obj=None, context=None):
    
        fmt = '%f' if precision is None else '%.{precision}f'
    
        lang_code = self.env.context.get('lang') or 'en_US'
    
        lang = self.pool['res.lang']
    
        formatted = lang.format(self.env.cr, self.env.uid, [lang_code], fmt.format(precision=precision), value, grouping=True,     monetary=True)
    
        if currency_obj:
    
            if currency_obj.position == 'before':
        
                formatted = currency_obj.symbol + ' ' + formatted
        
            else:
        
                formatted = formatted + ' ' + currency_obj.symbol
        
            return formatted

    @api.multi
    def render_html(self, data=None):
        report_obj = self.env['report']#xx
        report = report_obj._get_report_from_name('prof_fattacc.report_invoice_acc')
        docargs = {
    'convert_2float': self.convert_2float,
     'doc_ids': self._ids,
    'doc_model': report.model,
    'docs': self,
        }
        return report_obj.render('prof_fattacc.report_invoice_acc', docargs)

class report_invoiceproforma(models.AbstractModel):

    _name = 'report.prof_fattacc.report_invoiceproforma'
    
    def convert_2float(self, value, precision=dp.get_precision('account_2_cifre'), currency_obj=None, context=None):
    
        fmt = '%f' if precision is None else '%.{precision}f'
    
        lang_code = self.env.context.get('lang') or 'en_US'
    
        lang = self.pool['res.lang']
    
        formatted = lang.format(self.env.cr, self.env.uid, [lang_code], fmt.format(precision=precision), value, grouping=True,     monetary=True)
    
        if currency_obj:
    
            if currency_obj.position == 'before':
        
                formatted = currency_obj.symbol + ' ' + formatted
        
            else:
        
                formatted = formatted + ' ' + currency_obj.symbol
        
            return formatted

    @api.multi
    def render_html(self, data=None):
        report_obj = self.env['report']#xx
        report = report_obj._get_report_from_name('prof_fattacc.report_invoiceproforma')
        docargs = {
    'convert_2float': self.convert_2float,
     'doc_ids': self._ids,
    'doc_model': report.model,
    'docs': self,
        }
        return report_obj.render('prof_fattacc.report_invoiceproforma', docargs)

class report_invoice_document(models.AbstractModel):
    #Do not touch _name it must be same as _inherit
    #_name = 'report.report_invoice'
    _name = 'report.account.report_invoice_document'
    
    def convert_2float(self, value, precision=dp.get_precision('account_2_cifre'), currency_obj=None, context=None):
    
        fmt = '%f' if precision is None else '%.{precision}f'
    
        lang_code = self.env.context.get('lang') or 'en_US'
    
        lang = self.pool['res.lang']
    
        formatted = lang.format(self.env.cr, self.env.uid, [lang_code], fmt.format(precision=precision), value, grouping=True,     monetary=True)
    
        if currency_obj:
    
            if currency_obj.position == 'before':
        
                formatted = currency_obj.symbol + ' ' + formatted
        
            else:
        
                formatted = formatted + ' ' + currency_obj.symbol
        
            return formatted
    @api.multi
    def render_html(self, data=None):
        report_obj = self.env['report']#xx
        report = report_obj._get_report_from_name('account.report_invoice_document')
        docargs = {
    'convert_2float': self.convert_2float,
     'doc_ids': self._ids,
    'doc_model': report.model,
    'docs': self,
        }
        return report_obj.render('account.report_invoice_document', docargs)

class report_saleorderproforma(models.AbstractModel):

    _name = 'report.prof_fattacc.report_saleorderproforma'
    
    def convert_2float(self, value, precision=dp.get_precision('account_2_cifre'), currency_obj=None, context=None):
    
        fmt = '%f' if precision is None else '%.{precision}f'
    
        lang_code = self.env.context.get('lang') or 'en_US'
    
        lang = self.pool['res.lang']
    
        formatted = lang.format(self.env.cr, self.env.uid, [lang_code], fmt.format(precision=precision), value, grouping=True,     monetary=True)
    
        if currency_obj:
    
            if currency_obj.position == 'before':
        
                formatted = currency_obj.symbol + ' ' + formatted
        
            else:
        
                formatted = formatted + ' ' + currency_obj.symbol
        
            return formatted

    @api.multi
    def render_html(self, data=None):
        report_obj = self.env['report']#xx
        report = report_obj._get_report_from_name('prof_fattacc.report_saleorderproforma')
        docargs = {
    'convert_2float': self.convert_2float,
     'doc_ids': self._ids,
    'doc_model': report.model,
    'docs': self,
        }
        return report_obj.render('prof_fattacc.report_saleorderproforma', docargs)

        