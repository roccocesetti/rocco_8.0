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

def _unescape(text):
    ##
    # Replaces all encoded characters by urlib with plain utf8 string.
    #
    # @param text source text.
    # @return The plain text.
    from urllib import unquote_plus
    return unquote_plus(text.encode('utf8'))

class account_invoice_line(osv.osv):
    _inherit="account.invoice.line"
    def create_new_order(self,cr,uid,ids=[],context=None):
        if context is None:
            context = {}
        order_data={}
        lines_data=[]
        shop_id=self.pool.get('sale.shop').search(cr,uid,[('name','ilike','casatessile')],limit=1,context=context)
        for invoice_line_id in self.pool.get('account.invoice.line').search(cr,uid,[('id','in',context.get('active_ids',[]) )],context=context):
            invoice_line_id_obj=self.pool.get('account.invoice.line').browse(cr,uid,invoice_line_id,context=context)
            lines_data.append({
                    'order_id'                :False,
                    'product_id'            :invoice_line_id_obj.product_id.id,
                    'price_unit'            :invoice_line_id_obj.price_unit,
                    'product_uom_qty'        :invoice_line_id_obj.quantity,
                    'name'                    :invoice_line_id_obj.name,
                    'discount'                :invoice_line_id_obj.discount,
                    'tax_id':invoice_line_id_obj.invoice_line_tax_id[0].id if invoice_line_id_obj.invoice_line_tax_id else None
                    })
        order_data={'partner_id'            :invoice_line_id_obj.invoice_id.partner_id.id,
                'partner_invoice_id'    :invoice_line_id_obj.invoice_id.partner_id.id,
                'partner_shipping_id'    :invoice_line_id_obj.invoice_id.partner_id.id,
                'payment_term'          :invoice_line_id_obj.invoice_id.payment_term.id,
                'pricelist_id'            :invoice_line_id_obj.invoice_id.partner_id.property_product_pricelist.id,
                'carrier_id'            :False,
                'order_policy'                :'manual',     
                'origin'                :'manual',
                'shop_id':shop_id[0] if shop_id else None
                }  
        order_id=self.create_n_confirm_order(cr,uid,ids,order_data,lines_data,context=context)
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        if context is None:
            context = {}

        result = mod_obj.get_object_reference(cr, uid, 'sale', 'view_quotation_tree')
        view_id = result and result[1] or False
        act_id=act_obj.search(cr,uid,[('view_id','=',view_id)],context=context,limit=1)
        result = act_obj.read(cr, uid, act_id)[0]
        result['domain'] = str([('id', '=', order_id)])
        return result
    def create_n_confirm_order(self,cr,uid,ids,order_data,line_data,context=None):
        if context is None:
            context = {}
        return_array={}
        if order_data and line_data:
            order_dic=order_data
            # if order_data.has_key('invoice_date'):

                # context['invoice_date']=order_data.get('invoice_date',False)
            order_id=self.pool.get('sale.order').create(cr,uid,order_dic)
            if order_id:
                for line in line_data:
                    """
                    if line.get('type').startswith('S'):
                        erp_product_id=self._get_virtual_product_id(cr,uid,{'name':'Shipping'})
                    if line.get('type').startswith('V'):
                        erp_product_id=self._get_virtual_product_id(cr,uid,{'name':'Discount'})
                    if line.get('type').startswith('P'):
                        erp_product_id=line['product_id']
                    """
                    line_dic=line
                    line_dic.update({'order_id':order_id})
                    if line.get('tax_id',None):
                        line_dic['tax_id']=[(6,0,[line['tax_id']])]
                    else:
                        line_dic['tax_id'] = False
                    line_id=self.pool.get('sale.order.line').create(cr,uid,line_dic)
                
                # invoice_id='0'
                # if int(round(float(erp_total)))==int(round(float(order_data['presta_total']))):
                    # workflow.trg_validate(uid, 'sale.order',order_id, 'order_confirm', cr)
                    # invoice_id=self.create_order_invoice(cr,uid,order_id,context)
            return order_id
class sale_order_line(osv.osv):
    _inherit = "sale.order.line"
    def _product_margin(self, cr, uid, ids, field_name, arg, context=None):
        res=super(sale_order_line, self)._product_margin( cr, uid, ids, field_name, arg, context=context)
        cur_obj = self.pool.get('res.currency')
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            cur = line.order_id.pricelist_id.currency_id
            res[line.id] = 0
            if line.product_id:
                price = line.purchase_price

                if not price:
                    from_cur = self.pool['res.users'].browse(cr, uid, uid, context=context).company_id.currency_id
                    cost = line.product_id.standard_price
                    ctx = context.copy()
                    ctx['date'] = line.order_id.date_order
                    price = self.pool['res.currency'].compute(cr, uid, from_cur.id, cur.id, cost, round=False, context=ctx)

                tmp_margin = line.price_subtotal - (price * line.product_uom_qty)
                res[line.id] = cur_obj.round(cr, uid, cur, tmp_margin)
        return res

    _columns = {
        'margin': fields.function(_product_margin, string='Margin', digits_compute= dp.get_precision('Product Price'),
              store = True),
    }

class account_invoice(osv.osv):
    _inherit = "account.invoice"


    def _state_picking(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if context is None:
            context = {}
        """"---"""
        
        
        for inv_id_obj in self.browse(cr, SUPERUSER_ID, ids, context):
            res[inv_id_obj.id]=''
            order_id=self.pool.get('sale.order').search(cr,uid,[('name','=',inv_id_obj.origin)],limit=1)
            if order_id:
                for picking_id_obj in self.pool.get('sale.order').browse(cr, SUPERUSER_ID, order_id[0], context).picking_ids:
                    if picking_id_obj.state in ['confirmed','waiting']:
                        state='Attesa merce'
                    elif picking_id_obj.state == 'cancel':
                        state='Annullato'
                    elif picking_id_obj.state == 'done':
                        state='spedito'
                    elif picking_id_obj.state == 'assigned':
                        state='pronto da preparare'
                    else:
                        state='Attesa merce'
                        
                    if picking_id_obj.name.find('OUT')>=0 or picking_id_obj.name.find('DS')>=0:
                        res[inv_id_obj.id] += state + '-'+ picking_id_obj.name + ' '
                if res[inv_id_obj.id]=='':
                        res[inv_id_obj.id]='Creare picking'
                if inv_id_obj.state_picking!=res[inv_id_obj.id]:
                    self.write(cr,SUPERUSER_ID,inv_id_obj.id,{'state_picking':res[inv_id_obj.id]})



    _columns = {
        #'x_y_picking_state': fields.function(_state_picking, type='char', string='Stato picking'),          
        #'state_picking': fields.char('Stato picking', size=64, required=False, readonly=True),
        'x_country_id': fields.related('partner_id', 'country_id', type="many2one", relation="res.country", string="Nazione", readonly=True),
        'x_category_id': fields.related('partner_id', 'category_id', type="many2many", relation="res.partner.category", string="Categorie", readonly=True,Store=True),
    }


class StockMove(models.Model):
    _inherit = "stock.move"

    @api.multi
    def write(self, vals):
        #self.ensure_one()
        for record in self:
            if 'note' not in vals and record.picking_id and record.picking_id.note:
                vals['note'] = record.picking_id.note
        return super(StockMove, self).write(vals)



#class res_partner(osv.osv):
class res_partner(models.Model):
    _inherit="res.partner"
    @api.multi
    def action_open_invoice_line(self):
        context = self._context
        lines_invoice=[]
        my_partners=[]
        for myself in self.env['res.partner'].browse(self._ids):
            my_partners.append(myself.id)
            if myself.parent_id:
                my_partners.append(myself.parent_id.id)
            for mycontact in myself.child_ids:
                my_partners.append(mycontact.id)

        invoice_ids=self.env['account.invoice'].search([('partner_id','in',my_partners),('state','not in',['cancel','draft'])])
        for invoice_id in invoice_ids:
                        for line in invoice_id.invoice_line:
                            lines_invoice.append(line.id)
                        
                        
        view_ref = self.env['ir.model.data'].get_object_reference('prof_partner_view', 'view_invoice_line_tree_inherit_id')
        view_id = view_ref and view_ref[1] or False,
        view_ref_search = self.env['ir.model.data'].get_object_reference('prof_partner_view', 'view_account_invoice_filter_inherit_id')
        view_id_search = view_ref_search and view_ref_search[1] or False,
        return {'name':_("Righe fatturate"),
                            'views': [(view_id, 'tree')],
                            'view_mode': 'tree,form',
                            #'view_id': view_id if view_id else False,
                            'view_type': 'form',
                            'res_model': 'account.invoice.line',
                            'type': 'ir.actions.act_window',
                            'nodestroy': True,
                            'target': 'normal',
                            'domain': [('id','in',lines_invoice)],
                            'search_view_id': view_id_search,                                
                            'context': context,                                 
                        }


    def create_n_confirm_order(self,cr,uid,order_data,line_data,context=None):
        if context is None:
            context = {}
        return_array={}
        config=self.pool.get('prestashop.configure').search(cr,uid,[('active','=',True)])
        payment_term_id=self.pool.get('prestashop.configure').browse(cr,uid,config[0]).payment_term_id
        if order_data and line_data:
            order_dic={
                'partner_id'            :order_data['partner_id'],
                'partner_invoice_id'    :order_data['partner_invoice_id'],
                'partner_shipping_id'    :order_data['partner_shipping_id'],
                'payment_term'          :payment_term_id.id,
                'pricelist_id'            :order_data['pricelist_id'],
                'carrier_id'            :order_data['carrier_id'],
                'order_policy'                :'manual',     
                'origin'                :'PrestaShop'+'('+order_data['presta_order_reference']+')',
                'channel'                :'prestashop',
                }
            # if order_data.has_key('invoice_date'):

                # context['invoice_date']=order_data.get('invoice_date',False)
            if order_data.has_key('date_add'):    
                order_dic['date_order']=order_data.get('date_add',False)
                # order_dic['date_confirm']=order_data.get('date_upd',False)
                order_dic['date_confirm']=order_data.get('date_add',False)
                context['invoice_date']=order_data.get('date_add',False)
            if order_data.get('shop_id'):
                order_dic.update({'shop_id':order_data['shop_id']})
            order_id=self.pool.get('sale.order').create(cr,uid,order_dic)
            if order_id:
                for line in line_data:
                    if line.get('type').startswith('S'):
                        erp_product_id=self._get_virtual_product_id(cr,uid,{'name':'Shipping'})
                    if line.get('type').startswith('V'):
                        erp_product_id=self._get_virtual_product_id(cr,uid,{'name':'Discount'})
                    if line.get('type').startswith('P'):
                        erp_product_id=line['product_id']
                    line_dic={
                    'order_id'                :order_id,
                    'product_id'            :erp_product_id,
                    'price_unit'            :line['price_unit'],
                    'product_uom_qty'        :line['product_uom_qty'],
                    'name'                    :_unescape(line['name']),
                    'discount'                :line.get('discount',False),
                    }
                    if line.get('tax_id') and int(line.get('tax_id'))!=-1:
                        line_dic['tax_id']=[(6,0,[line.get('tax_id')])]
                    else:
                        line_dic['tax_id'] = False
                    line_id=self.pool.get('sale.order.line').create(cr,uid,line_dic)
                    erp_product_id=False
                
                order_erp=self.pool.get('sale.order').read(cr,uid,order_id,['name','amount_total'])
                order_name=order_erp['name']
                erp_total=order_erp['amount_total']
                cr.execute("INSERT INTO prestashop_order (erp_id, presta_id, object_name,name) VALUES (%s, %s, %s, %s)", (order_id, order_data['presta_order_id'], 'order',order_name+'('+order_data['presta_order_reference']+')'))
                cr.commit()
                # invoice_id='0'
                # if int(round(float(erp_total)))==int(round(float(order_data['presta_total']))):
                    # workflow.trg_validate(uid, 'sale.order',order_id, 'order_confirm', cr)
                    # invoice_id=self.create_order_invoice(cr,uid,order_id,context)
            return [{'erp_order_id':order_id,'prst_order_id':order_data['presta_order_id'],'erp_order_name':order_name,'erp_total':erp_total,'presta_total':order_data['presta_total']}]

class sale_order(models.Model):
    _inherit="sale.order"
    @api.multi
    def reorder_desc(self):
        lines=None
        for myself in self.env['sale.order'].browse(self._ids):
            lines=self.env['sale.order.line'].search([('order_id','=',myself.id)],order='name,id')
            break
        return lines    

class product_supplierinfo(osv.osv):
    _inherit="product.supplierinfo"
    _columns = {
        #'x_y_picking_state': fields.function(_state_picking, type='char', string='Stato picking'),          
        #'state_picking': fields.char('Stato picking', size=64, required=False, readonly=True),
        'nome_fornitore': fields.related('name', 'name', type="char", relation="res.partner", string="Nome Fornitore", readonly=True),
        'categ_id': fields.related('product_tmpl_id', 'categ_id', type="many2one", relation="product.category", string="Categoria", readonly=True),
        'product_variant_ids': fields.related('product_tmpl_id', 'product_variant_ids', type="one2many", relation="product.product", string="Varianti", readonly=True),
        'qty_available': fields.related('product_tmpl_id', 'qty_available', type="float",  string="Disponibile", readonly=True),
    }
    _order = 'name,product_tmpl_id,sequence'

class report_saleorder_desc(models.AbstractModel):

    _name = 'report.prof_partner_view.report_saleorder_desc'
    
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
        report = report_obj._get_report_from_name('prof_partner_view.report_saleorder_desc')
        docargs = {
    'convert_2float': self.convert_2float,
     'doc_ids': self._ids,
    'doc_model': report.model,
    'docs': self,
        }
        return report_obj.render('prof_partner_view.report_saleorder_desc', docargs)

class StockPickingPackagePreparation(models.Model):
    _inherit = 'stock.picking.package.preparation'
    net_weight_manual = x_fields.Float(
        string="Force net Weight",
        help="Fill this field with the value you want to be used as weight. "
             "Leave empty to let the system to compute it")
    @api.one
    @api.depends('package_id',
                 'package_id.children_ids',
                 'package_id.ul_id',
                 'package_id.quant_ids',
                 'picking_ids',
                 'picking_ids.move_lines',
                 'picking_ids.move_lines.quant_ids',
                 'weight_manual',
                 'net_weight_manual'
                 )
    def _compute_weight(self):
        res = super(StockPickingPackagePreparation, self)._compute_weight()
        if self.net_weight_manual:
            self.net_weight = self.net_weight_manual
        return res
    @api.multi
    def reorder_desc(self):
        lines=None
        for myself in self.env['stock.picking.package.preparation'].browse(self._ids):
            lines=self.env['stock.picking.package.preparation.line'].search([('package_preparation_id','=',myself.id)],order='name,id')
            break
        return lines    

class account_invoice_models(models.Model):
    _inherit = 'account.invoice'
    @api.multi
    def reorder_desc(self):
        lines=None
        for myself in self.env['account.invoice'].browse(self._ids):
            lines=self.env['account.invoice.line'].search([('invoice_id','=',myself.id)],order='name,id')
            break
        return lines


class sale_report_country(osv.osv):
    _inherit = "sale.report"

    _columns = {
        'country_id': fields.many2one('res.country',string='Nazione'),
        'state_id': fields.many2one('res.country.state', string='Provincia')
    }

    def _select(self):
        select_str = """
            WITH currency_rate (currency_id, rate, date_start, date_end) AS (
                    SELECT r.currency_id, r.rate, r.name AS date_start,
                        (SELECT name FROM res_currency_rate r2
                        WHERE r2.name > r.name AND
                            r2.currency_id = r.currency_id
                         ORDER BY r2.name ASC
                         LIMIT 1) AS date_end
                    FROM res_currency_rate r
                )
             SELECT min(l.id) as id,
                    l.product_id as product_id,
                    t.uom_id as product_uom,
                    sum(l.product_uom_qty / u.factor * u2.factor) as product_uom_qty,
                    sum(l.product_uom_qty * l.price_unit / cr.rate * (100.0-l.discount) / 100.0) as price_total,
                    count(*) as nbr,
                    s.date_order as date,
                    s.date_confirm as date_confirm,
                    s.partner_id as partner_id,
                    s.user_id as user_id,
                    s.company_id as company_id,
                    extract(epoch from avg(date_trunc('day',s.date_confirm)-date_trunc('day',s.create_date)))/(24*60*60)::decimal(16,2) as delay,
                    l.state,
                    t.categ_id as categ_id,
                    s.pricelist_id as pricelist_id,
                    s.project_id as analytic_account_id,
                    s.section_id as section_id,
                    rp.country_id as country_id,
                    rp.state_id as state_id
        """
        return select_str

    def _from(self):
        from_str = """
                sale_order_line l
                      join sale_order s on (l.order_id=s.id)
                        left join product_product p on (l.product_id=p.id)
                            left join product_template t on (p.product_tmpl_id=t.id)
                    left join product_uom u on (u.id=l.product_uom)
                    left join product_uom u2 on (u2.id=t.uom_id)
                    left join product_pricelist pp on (s.pricelist_id = pp.id)
                    left join res_partner rp on (s.partner_id=rp.id) 
                    join currency_rate cr on (cr.currency_id = pp.currency_id and
                        cr.date_start <= coalesce(s.date_order, now()) and
                        (cr.date_end is null or cr.date_end > coalesce(s.date_order, now())))

        """
        return from_str

    def _group_by(self):
        group_by_str = """
            GROUP BY l.product_id,
                    l.order_id,
                    t.uom_id,
                    t.categ_id,
                    s.date_order,
                    s.date_confirm,
                    s.partner_id,
                    s.user_id,
                    s.company_id,
                    l.state,
                    s.pricelist_id,
                    s.project_id,
                    s.section_id,
                   rp.country_id,
                   rp.state_id
        """
        return group_by_str

    def init(self, cr):
        # self._table = sale_report
        tools.drop_view_if_exists(cr, self._table)
        cr.execute("""CREATE or REPLACE VIEW %s as (
            %s
            FROM ( %s )
            %s
            )""" % (self._table, self._select(), self._from(), self._group_by()))


