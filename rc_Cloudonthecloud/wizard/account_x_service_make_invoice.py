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
from openerp import models, fields as new_fields
from openerp.osv import fields, osv
from openerp.tools.translate import _
import os
import sys, httplib
import urllib2 
import urllib
import httplib2
from openerp import SUPERUSER_ID
import openerp.exceptions
from openerp.osv.orm import browse_record
from datetime import datetime
import time
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
import openerp.addons.decimal_precision as dp
from openerp import netsvc
from openerp.tools import html2text
from openerp.loglevels import ustr
from urllib import urlencode
from urlparse import urljoin
import curses.ascii
class account_invoice(models.Model):
    _inherit = 'account.invoice' 
    internal_number = new_fields.Char(string='Invoice Number', readonly=False,
        default=False, copy=False,
        help="Unique number of the invoice, computed automatically when the invoice is created.")
    
    #Do not touch _name it must be same as _inherit
    #_name = 'account.invoice'
class account_x_service_make_invoice(osv.osv_memory):
    _name = "account.x.service.make.invoice"
    _description = "account_x_service Make Invoice"
    _columns = {
        'grouped': fields.boolean('Group the invoices', help='Check the box to group the invoices for the same customers'),
        'invoice_date': fields.date('Invoice Date'),
    }
    _defaults = {
        'grouped': False,
        'invoice_date': fields.date.context_today,
    }

    def view_init(self, cr, uid, fields_list, context=None):
        if context is None:
            context = {}
        record_id = context and context.get('active_id', False)
        order = self.pool.get('account.x.service').browse(cr, uid, record_id, context=context)
        if order.state == 'draft':
            raise osv.except_osv(_('Warning!'), _('You cannot create invoice when sales order is not confirmed.'))
        return False

    def make_invoices(self, cr, uid, ids, context=None):
        account_x_service_obj = self.pool.get('account.x.service')
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        newinv = []
        if context is None:
            context = {}
        data = self.read(cr, uid, ids)[0]
        for account_x_service in account_x_service_obj.browse(cr, uid, context.get(('active_ids'), []), context=context):
            if account_x_service.state != 'done':
                raise osv.except_osv(_('ATTENZIONE!'), _("Non ci sono Servizi Cloud attivati %s") % (account_x_service.name))

        account_x_service_obj.action_invoice_create(cr, uid, context.get(('active_ids'), []), data['grouped'],states=None, date_invoice=data['invoice_date'],context=context)
        account_x_service_ids_obj = account_x_service_obj.browse(cr, uid, context.get(('active_ids'), []), context=context)
        for o in account_x_service_ids_obj:
            for i in o.invoice_ids:
                newinv.append(i.id)
        # Dummy call to workflow, will not create another invoice but bind the new invoice to the subflow
        account_x_service_obj.signal_workflow(cr, uid, [o.id for o in account_x_service_ids_obj],'manual_invoice')
        result = mod_obj.get_object_reference(cr, uid, 'account', 'action_invoice_tree1')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        result['domain'] = "[('id','in', [" + ','.join(map(str, newinv)) + "])]"

        return result
    def recurring_create_invoice(self, cr, uid, ids=None, context=None):
        x_service_obj=self.pool.get('account.x.service')
        return x_service_obj.recurring_create_invoice(cr, uid, ids=None, context=context)
    def validate_x_service_paid(self, cr, uid, ids=None, context=None):
        x_service_obj=self.pool.get('account.x.service')
        return x_service_obj.validate_x_service_paid(cr, uid, ids=None, context=context)

class account_x_service_notify_make(osv.osv):
    _name = "account.x.service.notify.make"
    _description = "account_x_service_notify_Make"
    _columns = {
        'notify_date': fields.date('Data Notifica'),
    }
    _defaults = {
        'notify_date': fields.date.context_today,
    }

    def view_init(self, cr, uid, fields_list, context=None):
        if context is None:
            context = {}
        record_id = context and context.get('active_id', False)
        x_service = self.pool.get('account.x.service').browse(cr, uid, record_id, context=context)
        if x_service.state == 'done' or x_service.state == 'paid' or x_service.state == 'progress':
            raise osv.except_osv(_('Warning!'), _('Non ci sono Servizi Validi'))
        return False

    def make_notify_expire(self, cr, uid, ids, context=None):
        account_x_service_obj = self.pool.get('account.x.service')
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        newinv = []
        if context is None:
            context = {}
        data = self.read(cr, uid, ids)[0]
        
        account_x_service_obj.notify_service_expire(cr, uid, ids=None,context=context)
        result = mod_obj.get_object_reference(cr, uid, 'rc_Cloudonthecloud', 'action_rc_cloudonthecloud_account_x_notify')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        result['domain'] = "[('id','in', [" + ','.join(map(str, newinv)) + "])]"
    def make_notify_exired(self, cr, uid, ids, context=None):
        account_x_service_obj = self.pool.get('account.x.service')
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        newinv = []
        if context is None:
            context = {}
        data = self.read(cr, uid, ids)[0]
        
        account_x_service_obj.notify_service_expired(cr, uid, ids=None,context=context)
        result = mod_obj.get_object_reference(cr, uid, 'rc_Cloudonthecloud', 'action_rc_cloudonthecloud_account_x_notify')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        result['domain'] = "[('id','in', [" + ','.join(map(str, newinv)) + "])]"

        return result
    def make_notify_trial_expire(self, cr, uid, ids, context=None):
        account_x_service_obj = self.pool.get('account.x.service')
        if context is None:
            context = {}
        notify_ids=account_x_service_obj.notify_service_trial_expire(cr, uid, ids=None,context=context)
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        newinv = []
        result = mod_obj.get_object_reference(cr, uid, 'rc_Cloudonthecloud', 'action_rc_cloudonthecloud_account_x_notify_tree1')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        result['domain'] = "[('id','in', [" + ','.join(map(str, notify_ids)) + "])]"
        return result

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
