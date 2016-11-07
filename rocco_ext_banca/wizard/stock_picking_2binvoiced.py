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
import openerp.pooler as pooler
import openerp.sql_db as sql_db
from openerp.osv import fields,osv,orm

from openerp.tools.translate import _

from datetime import datetime, timedelta
import time
import base64
import cStringIO
from xml.etree.ElementTree import parse
import xml.etree.ElementTree as ETree
from xml.etree.ElementTree import Element, SubElement, Comment, ElementTree
from xml.dom import minidom
class stock_picking_invoiced(osv.osv_memory):

    _name = "stock.picking.2binvoiced"
    _description = "stock  picking 2binvoiced"

    _columns = {
        'group': fields.boolean("Group by partner"),
        'invoice_date': fields.date('Data Fattura'),
    }

    def view_init(self, cr, uid, fields_list, context=None):
        if context is None:
            context = {}
        res = super(stock_picking_invoiced, self).view_init(cr, uid, fields_list, context=context)
        stock_picking_obj = self.pool.get('stock.picking')
        count = 0
        active_ids = context.get('active_ids',[])
        """
        for sale in sale_order_obj.browse(cr, uid, active_ids, context=context):
            if sale.order_line[0].move_ids[0].picking_id.invoice_state != 'draft':
            #if sale.order_line[0].move_ids[0].picking_id.invoice_state != '2binvoiced':
                count += 1
        if len(active_ids) == 1 and count:
            raise osv.except_osv(_('Warning!'), _('This picking list does not require invoicing.'))
        if len(active_ids) == count:
            raise osv.except_osv(_('Warning!'), _("Attenzione l'ordine non può essere chiuso prima comnfermare"))
        """
        return res

    def stock_picking_2binvoiced_put(self, cr, uid, ids, context=None):
        db_name = cr.dbname
        pool = pooler.get_pool(db_name)
        stock_picking_obj = pool.get('stock.picking')
        invoice_obj=pool.get('account.invoice')
        invoice_ids = []
        active_ids=context.get("active_ids",[])
        date_today=datetime.today()
        for invoice_id in active_ids:
            this = self.browse(cr, uid, ids[0])
            invoice_ids_obj = invoice_obj.browse(cr, uid,invoice_id,context )            
            for pick in invoice_ids_obj.pick_ids:
                    vals={'invoice_state':'2binvoiced'}
                    stock_picking_obj.write(cr,uid,pick.id,vals,context=context)
                    vals={'state':'cancel'}
            invoice_obj.write(cr,uid,invoice_ids_obj.id,vals,context=context)
            invoice_ids += [invoice_id]

        if context is None:
            context = {}
        data_pool = self.pool.get('ir.model.data')
        inv_type = context.get('inv_type', False)
        action_model = False
        action = {}
        if not invoice_ids:
            raise osv.except_osv(_('Error!'), _('Nessuna Fattura selezionata'))
        if inv_type == "out_invoice":
            action_model,action_id = data_pool.get_object_reference(cr, uid, 'account', "action_invoice_tree1")
        elif inv_type == "in_invoice":
            action_model,action_id = data_pool.get_object_reference(cr, uid, 'account', "action_invoice_tree2")
        elif inv_type == "out_refund":
            action_model,action_id = data_pool.get_object_reference(cr, uid, 'account', "action_invoice_tree3")
        elif inv_type == "in_refund":
            action_model,action_id = data_pool.get_object_reference(cr, uid, 'account', "action_invoice_tree4")
        if action_model:
            action_pool = self.pool.get(action_model)
            action = action_pool.read(cr, uid, action_id, context=context)
            action['domain'] = "[('id','in', ["+','.join(map(str,invoice_ids))+"])]"
        return action


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
