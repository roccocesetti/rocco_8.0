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
import time
import openerp.addons.decimal_precision as dp
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.decimal_precision as dp
from openerp import workflow
from urllib import urlencode
class account_x_service_notifiy(osv.osv):
    def _get_access_link(self, cr, uid, mail, partner, context=None):
        # the parameters to encode for the query and fragment part of url
        query = {'db': cr.dbname}
        fragment = {
            'login': partner.user_ids[0].login,
            'action': 'mail.action_mail_redirect',
        }
        if mail.notification:
            fragment['message_id'] = mail.mail_message_id.id
        elif mail.model and mail.res_id:
            fragment.update(model=mail.model, res_id=mail.res_id)

        return "/web?%s#%s" % (urlencode(query), urlencode(fragment))

    def _amount_all_wrapper(self, cr, uid, ids, field_name, arg, context=None):
        """ Wrapper because of direct method passing as parameter for function fields """
        return self._amount_all(cr, uid, ids, field_name, arg, context=context)

    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        cur_obj = self.pool.get('res.currency')
        res = {}
        for x_service_notify in self.browse(cr, uid, ids, context=context):
            res[x_service_notify.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
            }
            val = val1 = 0.0
            cur = x_service_notify.partner_id.property_product_pricelist.currency_id
            for x_service in x_service_notify.notify_ids:
                        val1 += x_service.amount_untaxed
                        val += x_service.amount_tax
            res[x_service_notify.id]['amount_tax'] = cur_obj.round(cr, uid, cur, val)
            res[x_service_notify.id]['amount_untaxed'] = cur_obj.round(cr, uid, cur, val1)
            res[x_service_notify.id]['amount_total'] = res[x_service_notify.id]['amount_untaxed'] + res[x_service_notify.id]['amount_tax']
                
        return res
    def _get_x_service(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('account.x.service.notify.line').browse(cr, uid, ids, context=context):
            result[line.notify_id.id] = True
        return result.keys()
    """ servizi cloud notify """
    _name = "account.x.service.notify"
    _description = "service notifiy"
    _columns = {
        'name': fields.char('Notifica', size=128 , required=False),
        'notify_ref': fields.char('rif_notifica', size=128 , required=False),
        'data_notify': fields.datetime('Date'),
        'notify_ids': fields.one2many('account.x.service.notify.line', 'notify_id', 'Servizi Cloud in scadenza', states={'notifyed': [('readonly', True)], 'cancel': [('readonly', True)]}),
        'state': fields.selection([('draft', 'New'),
                                   ('cancel', 'Cancelled'),
                                   ('notifyed', 'notificata'),
                                   ('verified', 'verificata'),
                                   ], 'Status', readonly=True, select=True,
                 help= "* New: When the notify is created and not yet confirmed.\n"\
                       "* notifyed: When the notify is processed, the state is \'notifyed\'."),
        'partner_id': fields.many2one('res.partner', 'Partner' ),
        'user_id': fields.many2one('res.users', 'Assegnato a'),

        'amount_untaxed': fields.function(_amount_all_wrapper, digits_compute=dp.get_precision('Account'), string='Untaxed Amount',
            store={
                'account.x.service.notify': (lambda self, cr, uid, ids, c={}: ids, ['notify_ids'], 10),
                'account.x.service.notify.line': (_get_x_service, ['amount_untaxed', 'amount_tax', 'amount_total'], 10),
            },
            multi='sums', help="The amount without tax.", track_visibility='always'),
        'amount_tax': fields.function(_amount_all_wrapper, digits_compute=dp.get_precision('Account'), string='Taxes',
            store={
                'account.x.service.notify': (lambda self, cr, uid, ids, c={}: ids, ['notify_ids'], 10),
                'account.x.servicenotify.line': (_get_x_service,  ['amount_untaxed', 'amount_tax', 'amount_total'], 10),
            },
            multi='sums', help="The tax amount."),
        'amount_total': fields.function(_amount_all_wrapper, digits_compute=dp.get_precision('Account'), string='Total',
            store={
                'account.x.service.notify': (lambda self, cr, uid, ids, c={}: ids, ['notify_ids'], 10),
                'account.x.service.notify.line': (_get_x_service,  ['amount_untaxed', 'amount_tax', 'amount_total'], 10),
            },
            multi='sums', help="The total amount."),
        'x_service_policy': fields.selection([
                ('prepaid', 'pregato'),
                ('manual', 'pagato a su richiesta'),
                ('invoiced', 'pagato a emissione fattura'),
            ], 'Pagamento del servizio', required=True, readonly=True, states={'draft': [('readonly', False)], 'send': [('readonly', False)], 'trial': [('readonly', False)]},
            help="""This field controls how invoice and delivery operations are synchronized."""),
        'payment_acquirer_id': fields.many2one('payment.acquirer', 'Payment Acquirer', on_delete='set null'),
        'payment_tx_id': fields.many2one('payment.transaction', 'Transaction', on_delete='set null'),

     }
    _defaults = {
        'name': 'notifica',
        'state': 'draft',
        'data_notify': fields.datetime.now,
        'x_service_policy': 'prepaid',
    }
    def create(self, cr, user, vals, context=None):
                 return super(account_x_service_notifiy, self).create(cr, user, vals, context=context)
    def notify_service_expired(self, cr, uid, ids=None, context=None):
        x_service_obj=self.pool.get('account.x.service')
        x_service_obj.notify_service_expired(cr, uid, ids=None, context=context)

    def notify_service_expire(self, cr, uid, ids=None, context=None):
        x_service_obj=self.pool.get('account.x.service')
        x_service_obj.notify_service_expire(cr, uid, ids=None, context=context)
    def notify_service_trial_expire(self, cr, uid, ids=None, context=None):
        x_service_obj=self.pool.get('account.x.service')
        x_service_obj.notify_service_trial_expire(cr, uid, ids=None, context=context)
    def recurring_create_invoice(self, cr, uid, ids=None, context=None):
        x_service_obj=self.pool.get('account.x.service')
        return x_service_obj.recurring_create_invoice(cr, uid, ids=None, context=context)
    def validate_x_service_paid(self, cr, uid, ids=None, context=None):
        x_service_obj=self.pool.get('account.x.service')
        return x_service_obj.validate_x_service_paid(cr, uid, ids=None, context=context)
    def notify_get_transaction(self, cr, uid, ids, context=None):
        transaction_obj = self.pool.get('payment.transaction')
        tx_id = request.session.get('notify_transaction_id')
        if tx_id:
            tx_ids = transaction_obj.search(cr, uid, [('id', '=', tx_id), ('state', 'not in', ['cancel'])], context=context)
            if tx_ids:
                return transaction_obj.browse(cr, uid, tx_ids[0], context=context)
            else:
                request.session['notify_transaction_id'] = False
        return False
    def _get_errors(self, cr, uid, order, context=None):
        return []

class account_x_service_notifiy_line(osv.osv):

    """ orderpoint notify """

    _name = "account.x.service.notify.line"
    _description = "servizi cliente in scadenza notifiy"
    _columns = {
        'name': fields.char('Notifica servizio Cloud', size=128 , required=True),
        'notify_id': fields.many2one('account.x.service.notify', 'Notifica', ondelete='cascade', required=True, select=True),
        'x_service_id': fields.many2one('account.x.service', 'Servizio Cloud', required=True, select=True, domain=[],states={'done': [('readonly', True)]}),
        'state': fields.selection([('draft', 'New'),
                                   ('cancel', 'Cancelled'),
                                   ('notifyed', 'notifyed'),
                                   ('verified', 'verificata'),
                                   ], 'Status', readonly=True, select=True,
                 help= "* New: When the notify is created and not yet confirmed.\n"\
                       "* notifyed: When the notify is processed, the state is \'notifyed\'."),
        'data_notify': fields.datetime('Date'),
        'amount_untaxed': fields.float('Imponibile', required=True, digits_compute= dp.get_precision('Product Price')),
        'amount_tax': fields.float('Imposta', required=True, digits_compute= dp.get_precision('Product Price')),
        'amount_total': fields.float('Totale', required=True, digits_compute= dp.get_precision('Product Price')),

     }
    _defaults = {
        
        'name': 'notifica',
        'state': 'draft',
        'data_notify': fields.datetime.now,
        'amount_untaxed': 0.00,
        'amount_tax': 0.00,
        'amount_total': 0.00,

    }