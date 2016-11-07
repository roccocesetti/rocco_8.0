# -*- coding: utf-8 -*-
##############################################################################
#    
#    Copyright (C) 2010 Associazione OpenERP Italia
#    (<http://www.openerp-italia.org>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
from openerp.osv import orm, fields
from openerp.osv import fields, osv
from openerp import models, api
from openerp.tools.sql import drop_view_if_exists
from openerp.addons.decimal_precision import decimal_precision as dp
from atom import Date
from datetime import datetime, timedelta
import xml.etree.ElementTree as ETree
#from psycopg2.tests.testconfig import dbname
from openerp.http import request
from openerp import http, SUPERUSER_ID
class res_x_spese(osv.osv):
    """ spese"""

    _name = "res.x.spese"
    _description = "spese incasso"
    _columns = {
        'code':fields.char(string='Codice',size=16),
        'name':fields.char(string='Descrizione', size=64) ,
        'product_id': fields.many2one('product.product', 'Spese incasso', required=False, ),
        'product_bolli_id': fields.many2one('product.product', 'Spese bolli', required=False, )
     
     }

class Bank(osv.osv):
    _inherit = "res.bank"
    _columns = {
        'x_abi': fields.char('ABI', size=6, required=False),
        'x_cab': fields.char('CAB', size=6),
     }
    def name_get(self, cr, uid, ids, context=None):
        result = []
        for bank in self.browse(cr, uid, ids, context):
            if bank.x_abi==False:
                    bank.x_abi=''
            if bank.x_cab==False:
                    bank.x_cab=''
            
            result.append((bank.id, (bank.bic and (bank.bic + ' - ') or '') + bank.name+' '+bank.x_abi+ ' '+ bank.x_cab))
        return result
class res_partner_bank(osv.osv):
    _inherit = "res.partner.bank"
    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        if isinstance(ids, (int, long)):
                    ids = [ids]
        reads = self.read(cr, uid, ids, ['id','bank_name', 'x_abi', 'x_cab'], context=context)
        res = []
        for record in reads:
            bank_obj=self.pool.get('res.partner.bank')
            bank_ids_obj=bank_obj.browse(cr,uid,record['id'],context=context)
            if bank_ids_obj:
                x_abi=bank_ids_obj.bank.x_abi
                x_cab=bank_ids_obj.bank.x_cab
                nome=bank_ids_obj.bank.name
            name = nome
            if x_abi:
                name = x_abi + ' ' + name
            if x_cab :
                    name = '[' + x_abi+'/' +x_cab + '] ' + name
            res.append((record['id'], name))
        return res 


class res_partner(osv.osv):
    _inherit = "res.partner"
    _columns = {
       'x_spese_id': fields.many2one('res.x.spese', 'Spese', required=False),
       'x_data_dec': fields.datetime('Data decorrenza fatture', required=False),
        'x_payment_term_dec': fields.property(
            type='many2one',
            relation='account.payment.term',
            string="Termine di pagamento  su decorecorrenza",

            help="Termine di pagamento  su decorecorrenza",
            required=False),

        }
class sale_order(osv.osv):
    _inherit = "sale.order"
    _columns = {
       'x_spese_id': fields.many2one('res.x.spese', 'Spese', required=False),
       'x_partner_bank_id': fields.many2one('res.partner.bank', 'Bank Account',
            help='Bank Account Number to which the invoice will be paid. A Company bank account if this is a Customer Invoice or Supplier Refund, otherwise a Partner bank account number.' ),
        }
    def _make_invoice(self, cr, uid, order, lines, context={}):
        """ Redefines _make_invoice to create invoices with payment_type and acc_number from the sale order"""
        inv_id = super(sale_order, self)._make_invoice(cr, uid, order, lines, context)
        inv_obj = self.pool.get('account.invoice')
        if order.x_spese_id:
            inv_obj.write(cr, uid, [inv_id], {'x_spese_id':order.x_spese_id.id}, context=context)
        return inv_id
    def onchange_partner_id(self, cr, uid, ids, partner_id, context=None):
        val = super(sale_order, self).onchange_partner_id(cr, uid, ids,partner_id, context)
        if partner_id:
            part = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
            if not part:
                return {'value': {'x_spese_id': False}}
            if part:
                if part.x_spese_id:
                    x_spese_id = part.x_spese_id and part.x_spese_id.id or False
                else:
                    x_spese_id=False
            if not val:
                val = {}
            val['value']['x_spese_id'] = x_spese_id
            date_today=datetime.today().date()
            if part.bank_ids:
                     partner_bank_id=part.bank_ids[0]
                     val['value']['x_partner_bank_id'] = partner_bank_id.id
     
            if part.x_data_dec:
                x_data_dec=datetime.strptime(str(part.x_data_dec),"%Y-%m-%d %H:%M:%S").strftime("%m-%d")
                data_today_1=datetime.strptime(str(date_today),"%Y-%m-%d").strftime("%m-%d")
    
                if  data_today_1>x_data_dec:
                    val['value']['payment_term'] = part.x_payment_term_dec.id           
                else:    
                    val['value']['payment_term'] = part.property_payment_term.id
        return val
class account_invoice(osv.osv):
    _inherit = "account.invoice"
    _columns = {
       'name': fields.char('Description', size=256, select=True, readonly=True, states={'draft':[('readonly',False)]}),
       'origin': fields.char('Source Document', size=256, help="Reference of the document that produced this invoice.", readonly=True, states={'draft':[('readonly',False)]}),
       'x_spese_id': fields.many2one('res.x.spese', 'Spese', required=False),
       'x_colli':fields.integer(string='Colli', required=False),
       'x_carrier_id': fields.many2one('delivery.carrier', 'Trasportatore', required=False),
       'x_shipping_id': fields.many2one('res.partner', 'Destinazione per Fatt.acc.', required=False),
       'pick_ids': fields.many2many('stock.picking', 'stock_picking_invoice_rel',
                                     'invoice_id', 'pick_id',
                                     string='stock pickings'),
        'x_date_cons': fields.datetime('Date Consegna', help="Date of Completion"),
        'x_weight':fields.integer(string='Peso', required=False),
       
       }
    _defaults = {  
       'x_colli': 0,
       'x_weight': 0,
         }
    @api.multi
    def onchange_partner_id(self,type, partner_id,
            date_invoice=False, payment_term=False, partner_bank_id=False, company_id=False,context={}):
        print 'partner_id--res_bank',partner_id
        val = super(account_invoice, self).onchange_partner_id(type, partner_id,
            date_invoice, payment_term, partner_bank_id, company_id)
        cr, uid, context = request.cr, SUPERUSER_ID, request.context

        if partner_id:
            part = self.pool.get('res.partner').browse(cr, uid, partner_id,context=None)
            if not part:
                return {'value': {'x_spese_id': False}}
            x_spese_id = part.x_spese_id and part.x_spese_id.id or False
            carrier_id = part.property_delivery_carrier and part.property_delivery_carrier.id or False
            print "property_delivery_carrier",part.property_delivery_carrier.id
            transportation_reason_id = part.transportation_reason_id and part.transportation_reason_id.id or False
            carriage_condition_id = part.carriage_condition_id and part.carriage_condition_id.id or False
            goods_description_id = part.goods_description_id and part.goods_description_id.id or False
            x_shipping_id = part and part.id or False
            if not val:
                val = {}
            val['value']['x_spese_id'] = x_spese_id
            val['value']['x_carrier_id'] = carrier_id
            val['value']['transportation_reason_id'] = transportation_reason_id
            val['value']['carriage_condition_id'] = carriage_condition_id
            val['value']['goods_description_id'] = goods_description_id
            val['value']['x_shipping_id'] = x_shipping_id
            date_today=datetime.today().date()
            if part.bank_ids:
                 partner_bank_id=part.bank_ids[0].id
                 val['value']['partner_bank_id'] = partner_bank_id
            if part.x_data_dec:
                x_data_dec=datetime.strptime(str(part.x_data_dec),"%Y-%m-%d %H:%M:%S").strftime("%m-%d")
            else:
                x_data_dec=datetime.strptime(str(date_today),"%Y-%m-%d").strftime("%m-%d")

            data_today_1=datetime.strptime(str(date_today),"%Y-%m-%d").strftime("%m-%d")

            if  data_today_1>x_data_dec:
                val['value']['payment_term'] = part.x_payment_term_dec.id           
            else:    
                val['value']['payment_term'] = part.property_payment_term.id

        return val
class stock_picking(osv.osv):
    _inherit = 'stock.picking'

    def action_invoice_create(self, cr, uid, ids, journal_id=False, group=False, type='out_invoice', context=None):
        """ Redefines action_invoice_create to create invoices with payment_type and acc_number from the partner of the picking list"""
        res = super(stock_picking, self).action_invoice_create(cr, uid, ids, journal_id, group, type, context)
        invoice_obj = self.pool.get('account.invoice')
        sale_obj = self.pool.get('sale.order')
        for picking_id, invoice_id in res.items():
            picking = self.browse(cr, uid, picking_id, context=context)
            cr.execute('insert into stock_picking_invoice_rel (invoice_id,pick_id) '
                                                   'select %s,%s where not exists '
                                                   '(select * from stock_picking_invoice_rel where invoice_id=%s and pick_id=%s)',
                                                   (invoice_id, picking_id,invoice_id, picking_id))

            # Check if the picking comes from a sale
            if picking.sale_id:
                # Use the payment options from the order
                order = picking.sale_id
                vals = {}
     
                if order.x_spese_id:
                    vals['x_spese_id'] = order.x_spese_id.id
                if order.carrier_id:
                    vals['x_carrier_id'] = order.carrier_id.id
                if  order.partner_shipping_id:   
                    vals['x_shipping_id'] = order.partner_shipping_id.id
                if  order.x_partner_bank_id:   
                    vals['partner_bank_id'] = order.x_partner_bank_id.id
                if  order.payment_term:   
                    vals['payment_term'] = order.payment_term.id

            if  picking.transportation_reason_id:   
                    vals['transportation_reason_id'] = picking.transportation_reason_id.id
            if  picking.carriage_condition_id:                       
                    vals['carriage_condition_id'] = picking.carriage_condition_id.id
            if  picking.goods_description_id:   
                    vals['goods_description_id'] = picking.goods_description_id.id
            if  picking.goods_description_id:   
                    vals['goods_description_id'] = picking.goods_description_id.id
                    # Write the payment info into the invoice.
            vals['x_colli'] = picking.number_of_packages
            vals['x_weight'] = picking.weight
            if picking.date_done:
                vals['x_date_cons'] = picking.date_done
                    
            invoice_obj.write(cr, uid, [invoice_id], vals, context=context)
            cr.execute('insert into sale_order_tax (order_line_id,tax_id) '
                                                   'select %s,%s where not exists '
                                                   '(select * from sale_order_tax where order_line_id=%s and tax_id=%s)',
                                                   (order_line_ids_id, tax_ids_id,order_line_ids_id, tax_ids_id))

        return res
    
    def _prepare_invoice_line_x_spese(self, cr, uid, group, picking, invoice_id,x_spese_product_id,
        invoice_vals, context=None):
        """ Builds the dict containing the values for the invoice line
            @param group: True or False
            @param picking: picking object
            @param: move_line: move_line object
            @param: invoice_id: ID of the related invoice
            @param: invoice_vals: dict used to created the invoice
            @return: dict that will be used to create the invoice line
        """
        partner_obj = self.pool.get('res.partner')
        position_tax_obj = self.pool.get('account.fiscal.position.tax')
        account_tax_obj = self.pool.get('account.tax')
        invoice_obj = self.pool.get('account.invoice')
        if x_spese_product_id:    
                if group:
                    name = x_spese_product_id.name
                else:
                    name = x_spese_product_id.name
        else:
                name="-"
        if x_spese_product_id.taxes_id:
                x_spese_product_id_taxes_id=x_spese_product_id.taxes_id[0].id
        else:
                x_spese_product_id_taxes_id=None
        if x_spese_product_id_taxes_id:        
            invoice_ids_obj=invoice_obj.browse(cr, uid, invoice_id, context=context)
            if invoice_ids_obj:
                partner_ids_obj=partner_obj.browse(cr, uid, invoice_ids_obj.partner_id.id, context=context)
                if partner_ids_obj.property_account_position:
                    position_tax_ids=position_tax_obj.search(cr, uid, [('position_id','=',partner_ids_obj.property_account_position.id),('tax_src_id','=',x_spese_product_id_taxes_id)], context=context)
                    if position_tax_ids:
                       position_tax_ids_obj=position_tax_obj.browse(cr, uid, position_tax_ids[0], context=context)
                       if position_tax_ids_obj.tax_dest_id:
                           x_spese_product_id_taxes_id=position_tax_ids_obj.tax_dest_id.id
        origin = picking.name or ''
        if picking:
            if picking.origin:
                origin += ':' + picking.origin

        if invoice_vals.get('type','out_invoice') in ('out_invoice', 'out_refund'):
            if x_spese_product_id:
                account_id = x_spese_product_id.property_account_income.id
            else:
                return {}
            if not account_id:
                account_id = x_spese_product_id.categ_id.\
                        property_account_income_categ.id
        else:
            account_id = x_spese_product_id.property_account_expense.id
            if not account_id:
                account_id = x_spese_product_id.categ_id.\
                        property_account_expense_categ.id
        if invoice_vals.get('fiscal_position',None):
            fp_obj = self.pool.get('account.fiscal.position')
            fiscal_position = fp_obj.browse(cr, uid, invoice_vals['fiscal_position'], context=context)
            account_id = fp_obj.map_account(cr, uid, fiscal_position, account_id)
        # set UoS if it's a sale and the picking doesn't have one
        uos_id = x_spese_product_id.uos_id and x_spese_product_id.uos_id.id or False
        if not uos_id and invoice_vals.get('type','out_invoice') in ('out_invoice', 'out_refund'):
            uos_id = x_spese_product_id.uom_id.id
        """ calcolo scadenze"""
        pterm_list = self.pool.get('account.payment.term').compute(cr, uid, invoice_ids_obj.payment_term.id, value=1, date_ref=invoice_ids_obj.date_invoice)
        qscad=0
        if pterm_list:
            for line in pterm_list:
                qscad +=1
        return {
            'name': name,
            'origin': origin,
            'invoice_id': invoice_id,
            'uos_id': uos_id,
            'product_id': x_spese_product_id.id,
            'account_id': account_id,
            'price_unit': x_spese_product_id.list_price,
            'discount': 0,
            'quantity': qscad,
            'invoice_line_tax_id': [(6, 0, [x_spese_product_id_taxes_id])],
        }


  
