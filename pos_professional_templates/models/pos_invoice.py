# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://opensource.org/licenses/LGPL-3.0).
#
#This software and associated files (the "Software") may only be used (executed,
#modified, executed after modifications) if you have purchased a valid license
#from the authors, typically via Odoo Apps, or if you have received a written
#agreement from the authors of the Software (see the COPYRIGHT section below).
#
#You may develop Odoo modules that use the Software as a library (typically
#by depending on it, importing it and using its resources), but without copying
#any source code or material from the Software. You may distribute those
#modules under the license of your choice, provided that this license is
#compatible with the terms of the Odoo Proprietary License (For example:
#LGPL, MIT, or proprietary licenses similar to this one).
#
#It is forbidden to publish, distribute, sublicense, or sell copies of the Software
#or modified copies of the Software.
#
#The above copyright notice and this permission notice must be included in all
#copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
#DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
#ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#DEALINGS IN THE SOFTWARE.
#
#########COPYRIGHT#####
# © 2017 Bernard K Too<bernard.too@optima.co.ke>
from openerp.osv import osv
from openerp.tools.translate import _


class PosInvoiceReportCustom(osv.AbstractModel):
    _inherit = ['report.point_of_sale.report_invoice']

    def render_html(self, cr, uid, ids, data=None, context=None):
        report_obj = self.pool['report']
        posorder_obj = self.pool['pos.order']
        report = report_obj._get_report_from_name(cr, uid, 'professional_templates.report_invoice')
        selected_orders = posorder_obj.browse(cr, uid, ids, context=context)

        ids_to_print = []
        invoiced_posorders_ids = []
        for order in selected_orders:
            if order.invoice_id:
                ids_to_print.append(order.invoice_id.id)
                invoiced_posorders_ids.append(order.id)

        not_invoiced_orders_ids = list(set(ids) - set(invoiced_posorders_ids))
        if not_invoiced_orders_ids:
            not_invoiced_posorders = posorder_obj.browse(cr, uid, not_invoiced_orders_ids, context=context)
            not_invoiced_orders_names = list(map(lambda a: a.name, not_invoiced_posorders))
            raise osv.except_osv(_('Error!'), _('No link to an invoice for %s.' % ', '.join(not_invoiced_orders_names)))

        docargs = {
            'doc_ids': ids_to_print,
            'doc_model': report.model,
            #'docs': selected_orders,
            'docs': self.pool['account.invoice'].browse(cr, uid, ids_to_print, context=context),
        }
        return report_obj.render(cr, uid, ids, 'professional_templates.report_invoice', docargs, context=context)
