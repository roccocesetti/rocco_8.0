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
import random
from openerp import SUPERUSER_ID
from openerp.osv import osv, orm, fields
from openerp.addons.web.http import request

import time
import openerp.addons.decimal_precision as dp
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from dateutil import parser

from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.decimal_precision as dp
from openerp import netsvc
from openerp import workflow
from contextlib import contextmanager
import logging
from urllib import urlencode
_logger = logging.getLogger(__name__)
class Payment_Transaction(osv.osv):
    _inherit = 'payment.transaction'

    _columns = {
        # link with the sale order
        'notify_id': fields.many2one('account.x.service.notify', 'Notifica servizi cloud'),
        'x_service_id': fields.many2one('account.x.service', 'Servizi cloud'),
    }


class account_x_nods(osv.osv):
    def _service_partner_name(self, cr, uid,ids,prop, unknow_none, unknow_dict):              
               x_service_obj = self.pool.get('account.x.service') 
               """ leggo servizi cloud"""
               if ids:
                   result = dict.fromkeys(ids, False)
                   desc=""
                   for ids_1 in ids:
                            x_service_ids= x_service_obj.search(cr,SUPERUSER_ID, [('x_nod_id', '=', ids_1),('state', '<>', 'cancel')])
                            if x_service_ids:
                                x_service_ids_rec=x_service_obj.browse(cr, SUPERUSER_ID, x_service_ids[0])
                                desc = x_service_ids_rec.partner_id.name #+ chr(curses.ascii.LF)+desc
                                result[ids_1] =  desc
                   return result

    _name = 'account.x.nods'
    _description = 'Nodi virtuali/hardare/domini'
    _columns={
              'name': fields.char('Nome Nodo/', size=64, required=True,
             select=True),
        'active': fields.boolean('Attivo') ,
        'ip_pubblico': fields.char('Ip Pubblico', size=128, select=True),
        'ip_locale': fields.char('Ip Locale', size=128, select=True),
        'applicazione': fields.char('Applicazione', size=128, select=True),
        'x_service_partner': fields.function(_service_partner_name, string='# nodi', type='char'),
        'parent_id': fields.many2one('account.x.nods', 'Nodo padre'),
        'usr_nods': fields.char('Usr Nodo', size=128, select=True),
        'passwd_nods': fields.char('Password  Nodo', size=128, select=True),
        'url_nods': fields.char('URL  usr nodo', size=128, select=True),
        'id_vm': fields.char('ID VM ', size=128, select=True),

    }
    _defaults = {
        'active': True,
        'name': lambda obj, cr, uid, context: '/',
    }
    def name_get(self, cr, user, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not len(ids):
            return []
        def _name_get(d):
            name = d.get('name','')
            parent = d.get('parent_id',False)
            if parent:
                name = '[%s] %s' % (name,parent)
            return (d['id'], name)

 
        result = []
        for x_nods in self.browse(cr, user, ids, context=context):
                if x_nods.parent_id:
                    parent=x_nods.parent_id.name
                else:
                    parent=False
                mydict = {
                          'id': x_nods.id,
                          'name': x_nods.name,
                          'parent_id': parent,
                          }
                result.append(_name_get(mydict))
        return result

class account_x_credenz(osv.osv):
    def _service_partner_name(self, cr, uid,ids,prop, unknow_none, unknow_dict):              
               x_service_obj = self.pool.get('account.x.service') 
               """ leggo servizi cloud"""
               if ids:
                   result = dict.fromkeys(ids, False)
                   desc=""
                   for ids_1 in ids:
                            x_service_ids= x_service_obj.search(cr,SUPERUSER_ID, [('x_credenz_id', '=', ids_1),('state', '<>', 'cancel')])
                            if x_service_ids:
                                x_service_ids_rec=x_service_obj.browse(cr, SUPERUSER_ID, x_service_ids[0])
                                desc = x_service_ids_rec.partner_id.name #+ chr(curses.ascii.LF)+desc
                                result[ids_1] =  desc

                   return result

    _name = 'account.x.credenz'
    _description = 'Credenziali '
    _columns={
              'name': fields.char('login nodo', size=64, required=True,
             select=True),
            'active': fields.boolean('Attivo') ,
            'passwd': fields.char('Password  nodo', size=128, select=True),
            'url': fields.char('Url ', size=128, select=True),
            'nodo_rif': fields.char('Nodo di riferimento ', size=128, select=True),
            'x_service_partner': fields.function(_service_partner_name, string='# nodi', type='char'),

    }
    _defaults = {
        'active': True,
        'name': lambda obj, cr, uid, context: '/',
    }

class account_x_contract_service(osv.osv):
    _name = 'account.x.contract.service'
    _description = 'Servizi collegati al cliente'
    _columns={
              'name': fields.char('Nome Contratto', size=64, required=True,
             select=True),
             'active': fields.boolean('Attivo') ,
              'note': fields.text('Sezione Contratto'),

    }
    _defaults = {
        'active': True,
        'name': lambda obj, cr, uid, context: '/',
    }

class account_x_service(osv.osv):

    # make the real method inheritable
    _payment_block_proxy = lambda self, *a, **kw: self._portal_payment_block(*a, **kw)
    _x_payment_block_proxy = lambda self, *a, **kw: self._x_portal_payment_block(*a, **kw)

    def _portal_payment_block(self, cr, uid, ids, fieldname, arg, context=None):
        result = dict.fromkeys(ids, False)
        payment_acquirer = self.pool.get('payment.acquirer')
        for this in self.browse(cr, uid, ids, context=context):
            if this.state in ('send', 'done','expired'):
                    result[this.id] = payment_acquirer.render_payment_block(
                    cr, uid, 'SERV-'+str(this.id), this.amount_total, this.partner_id.property_product_pricelist.currency_id.id,
                    partner_id=this.partner_id.id, company_id=this.partner_id.company_id.id, context=context)
                    
                    transaction_obj = self.pool.get('payment.transaction')
                    
                    acquirer_obj = self.pool.get('payment.acquirer')
                    aquirer_ids=acquirer_obj.search(cr,uid,[('name','=','Paypal')])
                    trans_ids=transaction_obj.search(cr,uid,[('x_service_id','=',this.id)])
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
                                    'reference': 'SERV'+str(this.id),
                                    'x_service_id': this.id,
                                }, context=context)
                        else:
                                   transaction_obj.write(cr,SUPERUSER_ID,trans_ids[0], {
                                    'amount': this.amount_total,
                                }, context=context)
                                       
        return result
    def _x_portal_payment_block(self, cr, uid, ids, fieldname, arg, context=None):
        result = dict.fromkeys(ids, False)
        x_payment_acquirer = self.pool.get('x.portal.payment.acquirer')
        transaction_obj = self.pool.get('payment.transaction')
        acquirer_obj = self.pool.get('payment.acquirer')
                    
        for this in self.browse(cr, uid, ids, context=context):
            if  this.state in ('send', 'done','expired'):
                result[this.id] = x_payment_acquirer.render_payment_block(cr, uid, this, 'SERV-'+str(this.id),
                    this.partner_id.property_product_pricelist.currency_id, this.amount_total, context=context)
                trans_ids=transaction_obj.search(cr,uid,[('x_service_id','=',this.id)])
                aquirer_ids=acquirer_obj.search(cr,uid,[('name','=','Paypal')])
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
                                    'reference': 'SERV-'+str(this.id),
                                    'x_service_id': this.id,
                                }, context=context)
                    else:
                                   transaction_obj.write(cr,SUPERUSER_ID,trans_ids[0], {
                                    'amount': this.amount_total,
                                }, context=context)
        
        return result

    def _get_parent_nods(self, cr, uid,ids,prop, unknow_none, unknow_dict):              
               x_service_obj = self.pool.get('account.x.service') 
               """ leggo servizi cloud"""
               if ids:
                   result = dict.fromkeys(ids, False)
                   desc=''
                   for ids_1 in ids:
                                x_service_ids_rec=x_service_obj.browse(cr, SUPERUSER_ID, ids_1)
                                if x_service_ids_rec.x_nod_id.parent_id:
                                    desc = x_service_ids_rec.x_nod_id.parent_id.name #+ chr(curses.ascii.LF)+desc
                                else:
                                    desc=''
                                result[ids_1] =  desc
                                
                   return result


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

    def _amount_line_tax(self, cr, uid, line, context=None):
        val = 0.0
        for c in self.pool.get('account.tax').compute_all(cr, uid, line.tax_id, line.price_unit * (1-(line.discount or 0.0)/100.0), line.service_qty, line.product_id, line.x_service_id.partner_id)['taxes']:
            val += c.get('amount', 0.0)
        return val

    def _amount_all_wrapper(self, cr, uid, ids, field_name, arg, context=None):
        """ Wrapper because of direct method passing as parameter for function fields """
        return self._amount_all(cr, uid, ids, field_name, arg, context=context)

    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        cur_obj = self.pool.get('res.currency')
        res = {}
        for x_service in self.browse(cr, SUPERUSER_ID, ids, context=context):
            res[x_service.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
            }
            val = val1 = 0.0
            valco = valco1 = 0.0
            valcoT = valcoT1 = 0.0
            cur = x_service.partner_id.property_product_pricelist.currency_id
            for line in x_service.line_ids:
                
                if x_service.type_service=='normal':
                        val1 += line.price_subtotal
                        val += self._amount_line_tax(cr, SUPERUSER_ID, line, context=context)
                elif x_service.type_service=='consumo':
                         valco1 += line.price_subtotal
                         valco += self._amount_line_tax(cr, SUPERUSER_ID, line, context=context)
                         if valco1>x_service.Imp_a_consumo:
                                valcoT1+=line.price_subtotal
                                valcoT+=self._amount_line_tax(cr, uid, line, context=context)
            if x_service.type_service=='normal':
                res[x_service.id]['amount_tax'] = cur_obj.round(cr, SUPERUSER_ID, cur, val)
                res[x_service.id]['amount_untaxed'] = cur_obj.round(cr, SUPERUSER_ID, cur, val1)
                res[x_service.id]['amount_total'] = res[x_service.id]['amount_untaxed'] + res[x_service.id]['amount_tax']
            else:
                res[x_service.id]['amount_tax'] = cur_obj.round(cr, SUPERUSER_ID, cur, valcoT)
                res[x_service.id]['amount_untaxed'] = cur_obj.round(cr, SUPERUSER_ID, cur, valcoT1)
                res[x_service.id]['amount_total'] = res[x_service.id]['amount_untaxed'] + res[x_service.id]['amount_tax']                    
                
        return res
    
    def _invoiced_rate(self, cursor, user, ids, name, arg, context=None):
        res = {}
        for x_service in self.browse(cursor, user, ids, context=context):
            if x_service.invoiced:
                res[x_service.id] = 100.0
                continue
            tot = 0.0
            for invoice in x_service.invoice_ids:
                if invoice.state not in ('draft', 'cancel'):
                    tot += invoice.amount_untaxed
            if tot:
                res[x_service.id] = min(100.0, tot * 100.0 / (sale.amount_untaxed or 1.00))
            else:
                res[x_service.id] = 0.0
        return res

    def _invoice_exists(self, cursor, user, ids, name, arg, context=None):
        res = {}
        for x_service in self.browse(cursor, SUPERUSER_ID, ids, context=context):
            res[x_service.id] = False
            if x_service.invoice_ids:
                res[x_service.id] = True
        return res
    def _alert_invoice(self, cursor, user, ids, name, arg, context=None):
        res = {}
        current_date =  time.strftime('%Y-%m-%d')
        for x_service in self.browse(cursor, user, ids, context=context):
            res[x_service.id] = current_date
            if x_service.date_next_invoice:
                date_expire = datetime.strptime(x_service.date_next_invoice or current_date, "%Y-%m-%d")
                interval = x_service.gg_alert
                res[x_service.id]  = date_expire+relativedelta(days=-interval)

        return res
    def _alert_trial(self, cursor, user, ids, name, arg, context=None):
        res = {}
        current_date =  time.strftime('%Y-%m-%d')
        for x_service in self.browse(cursor, user, ids, context=context):
            res[x_service.id] = current_date
            if x_service.trial_end:
                #trial_end=datetime.strptime(str(x_service.trial_end),"%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
                date_expire = datetime.strptime(x_service.trial_end or current_date, "%Y-%m-%d")
                interval = x_service.trail_gg_alert
                res[x_service.id]  = date_expire+relativedelta(days=-interval)

        return res

    def _invoiced(self, cursor, user, ids, name, arg, context=None):
        res = {}
        for x_service in self.browse(cursor, user, ids, context=context):
            res[x_service.id] = True
            invoice_existence = False
            for invoice in x_service.invoice_ids:
                if invoice.state!='cancel':
                    invoice_existence = True
                    if invoice.state != 'paid':
                        res[x_service.id] = False
                        break
            if not invoice_existence or x_service.state == 'manual':
                res[x_service.id] = False
        return res

    def _invoiced_search(self, cursor, user, obj, name, args, context=None):
        if not len(args):
            return []
        clause = ''
        x_service_clause = ''
        no_invoiced = False
        for arg in args:
            if arg[1] == '=':
                if arg[2]:
                    clause += 'AND inv.state = \'paid\''
                else:
                    clause += 'AND inv.state != \'cancel\' AND x_service.state != \'cancel\'  AND inv.state <> \'paid\'  AND rel.x_service_id = x_service.id '
                    x_service_clause = ',  account_x_service AS x_service '
                    no_invoiced = True

        cursor.execute('SELECT rel.order_id ' \
                'FROM account_x_service_invoice_rel AS rel, account_invoice AS inv '+ sale_clause + \
                'WHERE rel.invoice_id = inv.id ' + clause)
        res = cursor.fetchall()
        if no_invoiced:
            cursor.execute('SELECT x_service.id ' \
                    'FROM account_x_service AS x_service ' \
                    'WHERE x_service.id NOT IN ' \
                        '(SELECT rel.x_service_id ' \
                        'FROM account_x_service_invoice_rel AS rel) and x_service.state != \'cancel\'')
            res.extend(cursor.fetchall())
        if not res:
            return [('id', '=', 0)]
        return [('id', 'in', [x[0] for x in res])]

    def _get_x_service(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('account.x.service.line').browse(cr, uid, ids, context=context):
            result[line.x_service_id.id] = True
        return result.keys()
    def _get_default_company(self, cr, uid, context=None):
        company_id = self.pool.get('res.users')._get_company(cr, uid, context=context)
        if not company_id:
            raise osv.except_osv(_('Error!'), _('There is no default company for the current user!'))
        return company_id
    def _get_default_x_contract(self, cr, uid, context=None):
        x_contract_ids = self.pool.get('account.x.contract.service').search(cr, uid,[('id','>',0)], context=context)
        if not x_contract_ids:
            raise osv.except_osv(_('Error!'), _('There is no default company for the current user!'))
        x_contract_id=x_contract_ids[0]
        return x_contract_id

    _name = 'account.x.service'
    _description = 'Servizi collegati al cliente'
    _columns={
              'name': fields.char('Nome Servizio', size=64, required=True,
            readonly=True, states={'draft': [('readonly', False)], 'send': [('readonly', False)], 'trial': [('readonly', False)]}, select=True),
        'state': fields.selection([
            ('draft', 'Bozza'),
            ('trial', 'Periodo Test'),
            ('send', 'Inviato'),
            ('done', 'Attivato'),
            ('paid', 'pagato'),
            ('progress', 'Fatturato'),
            ('expired', 'Scaduto'),
            ('cancel', 'Cancellato'),
            ], 'Status', readonly=False, help="Stati del servizio draft in bozza,sent ", select=True),
        'trial_start': fields.date('Inizio prova', required=True, readonly=True, select=True, states={'draft': [('readonly', False)], 'send': [('readonly', False)], 'trial': [('readonly', False)]}),
        'trial_end': fields.date('Fine prova', required=True, readonly=True, select=True, states={'draft': [('readonly', False)], 'send': [('readonly', False)], 'trial': [('readonly', False)]}),
        'trail_gg_alert': fields.integer('Giorni di alert fine prova', required=True, digits_compute=0, ),
        'date_alert_trial': fields.function(_alert_trial, string='Data avviso scadenza prova',
        type='date', help="avviso  scadenza Prova",store=True),
        'date_service': fields.datetime('Date inizio servizio', required=True, readonly=True, select=True, states={'draft': [('readonly', False)], 'send': [('readonly', False)], 'trial': [('readonly', False)]}),
        'F_invoice_repeat': fields.boolean('Ripeti la fatturazione') ,
        'num_decorrenza': fields.integer('Ripeti la fatturazione ogni', required=True, digits_compute=0, ),
        'decorrenza': fields.selection([
            (1,'Giorni' ),
            (7, 'Settimane'),
            (30, 'Mesi'),
            (365, 'Anni'),
            ], 'Decorrenza', readonly=False, help="Decorrenza Fatturazione ", select=True),
        'date_next_invoice': fields.date('Date prossima Fattura', select=True, help="Date prossima Fatturazione"),
        'gg_alert': fields.integer('Giorni di alert', required=True, digits_compute=0, ),
        'date_alert_expire': fields.function(_alert_invoice, string='Data avviso scadenza',
             type='date', help="avviso  scadenza servizio",store=True),

        'partner_id': fields.many2one('res.partner', 'Customer', readonly=True,required=True, change_default=True,states={'draft': [('readonly', False)], 'send': [('readonly', False)], 'trial': [('readonly', False)]}, select=True, track_visibility='always'),
        'x_contract_service_id': fields.many2one('account.x.contract.service', 'Tipo Contratto Servizi Cloud', readonly=True, required=True, states={'draft': [('readonly', False)], 'send': [('readonly', False)], 'trial': [('readonly', False)]}, help="Il contratto può essere cambiato solo in draft"),
        'firma_contratto': fields.boolean('Contratto firmato') ,
        'x_nod_id': fields.many2one('account.x.nods', 'Nodi', required=True, help="Il nodo può essere  solo in draft"),
        'note': fields.text('Note'),
        'line_ids': fields.one2many('account.x.service.line', 'x_service_id', 'linee Servizi', readonly=True, states={'draft': [('readonly', False)], 'send': [('readonly', False)], 'trial': [('readonly', False)]}),
        'user_id': fields.many2one('res.users', 'Assegnato a', select=True, track_visibility='onchange'),
        'type_service': fields.selection([
            ('normal','Normale' ),
            ('consumo', 'A consumo'),
            ], 'Tipo Servizio', readonly=False, help="Tipo Servizio se a consumo il sistema addebiterà l'eccedenza cdell'importo Max a consumo", select=True),
        'Imp_a_consumo': fields.float('Importo Max da consumare per i servizi a consumo', required=True, digits_compute= dp.get_precision('Product Price'), readonly=True, states={'draft': [('readonly', False)], 'trial': [('readonly', False)], 'send': [('readonly', False)]}),
        'amount_untaxed': fields.function(_amount_all_wrapper, digits_compute=dp.get_precision('Account'), string='Untaxed Amount',
            store={
                'account.x.service': (lambda self, cr, uid, ids, c={}: ids, ['line_ids'], 10),
                'account.x.service.line': (_get_x_service, ['price_unit', 'tax_id', 'discount', 'service_qty'], 10),
            },
            multi='sums', help="The amount without tax.", track_visibility='always'),
        'amount_tax': fields.function(_amount_all_wrapper, digits_compute=dp.get_precision('Account'), string='Taxes',
            store={
                'account.x.service': (lambda self, cr, uid, ids, c={}: ids, ['line_ids'], 10),
                'account.x.service.line': (_get_x_service, ['price_unit', 'tax_id', 'discount', 'service_qty'], 10),
            },
            multi='sums', help="The tax amount."),
        'amount_total': fields.function(_amount_all_wrapper, digits_compute=dp.get_precision('Account'), string='Total',
            store={
                'account.x.service': (lambda self, cr, uid, ids, c={}: ids, ['line_ids'], 10),
                'account.x.service.line': (_get_x_service, ['price_unit', 'tax_id', 'discount', 'service_qty'], 10),
            },
            multi='sums', help="The total amount."),
        'invoice_ids': fields.many2many('account.invoice', 'account_x_service_invoice_rel', 'x_service_id', 'invoice_id', 'Invoices', readonly=True, help="This is the list of invoices that have been generated for this sales order. The same sales order may have been invoiced in several times (by line for example)."),
        'invoiced_rate': fields.function(_invoiced_rate, string='Invoiced Ratio', type='float'),
        'invoiced': fields.function(_invoiced, string='Paid',
            fnct_search=_invoiced_search, type='boolean', help="It indicates that an invoice has been paid."),
        'invoice_exists': fields.function(_invoice_exists, string='Invoiced',
            fnct_search=_invoiced_search, type='boolean', help="It indicates that sales order has at least one invoice."),
        'note': fields.text('Terms and conditions'),
        'user_customer_id': fields.many2one('res.users', 'Utente collegato ai servizi', select=True, track_visibility='onchange'),
        'x_service_policy': fields.selection([
                ('prepaid', 'prepagato'),
                ('manual', 'pagato a su richiesta'),
                ('invoiced', 'pagato a emissione fattura'),
            ], 'Pagamento del servizio', required=True, readonly=True, states={'draft': [('readonly', False)], 'send': [('readonly', False)], 'trial': [('readonly', False)]},
            help="""This field controls how invoice and delivery operations are synchronized."""),
        'website_published': fields.boolean('website published'),
        'x_nods_parent_id': fields.function(_get_parent_nods, string='Nodo Padre', type='char',store=True),
        'company_id': fields.many2one('res.company', 'Company'),
        'portal_payment_options': fields.function(_x_payment_block_proxy, type="html", string="Pagamento"),
        'paypal_id': fields.many2one('payment.transaction', 'Paypal id'),

    }
    _defaults = {
        'type_service': 'normal',
         'Imp_a_consumo': 0.00,
        'num_decorrenza': 1,
        'decorrenza': 1,
        'trail_gg_alert': 1,
        'gg_alert': 15,
        'date_service': fields.datetime.now,
        'trial_start': fields.datetime.now,
        'trial_end': fields.datetime.now,
        'date_next_invoice': fields.datetime.now,
        'state': 'draft',
        'name': lambda obj, cr, uid, context: '/',
        'note': lambda self, cr, uid, context: self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.sale_note,
        'x_service_policy': 'prepaid',
        'website_published': True,
        'company_id': _get_default_company,
        'x_contract_service_id': _get_default_x_contract,

    }
    def get_default_x_nods(self, cr, uid, context=None):
        x_nods_ids = self.pool.get('account.x.nods').search(cr, uid,[('id','>',0)], context=context)
        if not x_nods_ids:
            raise osv.except_osv(_('Error!'), _('There is no default nod for the current user!'))
        x_nods_id=x_nods_ids[0]
        return x_nods_id

    def _inv_get(self, cr, uid, x_service, context=None):
        return {}

    def button_dummy(self, cr, uid, ids, context=None):
        return True
    def x_nod_id_change(self, cr, uid, ids, partner_id=False,x_nod_id=False, context=None):
        context = context or {}
        if x_nod_id and partner_id:
            partner_obj = self.pool.get('res.partner')
            x_service_obj=self.pool.get('account.x.service')
            if ids:
                x_service_ids=x_service_obj.search(cr,uid, [('x_nod_id', '=', x_nod_id),('id', '<>', ids[0]),('state', '<>', 'cancel')], context=context)
            else:
                x_service_ids=x_service_obj.search(cr,uid, [('x_nod_id', '=', x_nod_id),('state', '<>', 'cancel')], context=context)
                
            if x_service_ids:
                raise osv.except_osv(_('Error!'), _('Questo nodo è già in uso presso un altro cliente!'))
            return True
        else:
            return False
    def partner_id_change(self, cr, uid, ids, partner_id=False, context=None):
        context = context or {}
        warning = {}
        domain = {}
        result = {}
        user_obj=self.pool.get('res.users')
        partner_obj = self.pool.get('res.partner')
        if partner_id:
                partner_id_obj=partner_obj.browse(cr, uid, partner_id, context=context)
                if partner_id_obj.user_id:
                    result['user_id']=partner_id_obj.user_id.id
                user_ids=user_obj.search(cr, uid, [('partner_id','=',partner_id)], context=context)
                if not user_ids:
                    if partner_id_obj.email:
                        user_ids=user_obj.search(cr, uid, [('login','=',partner_id_obj.email)], context=context)
                if user_ids:
                            result['user_customer_id']=user_ids[0]                
                return {'value': result, 'domain': domain, 'warning': warning}


    def _prepare_invoice(self, cr, uid, x_service, lines, context=None):
        """Prepare the dict of values to create the new invoice for a
           sales order. This method may be overridden to implement custom
           invoice generation (making sure to call super() to establish
           a clean extension chain).

           :param browse_record order: sale.order record to invoice
           :param list(int) line: list of invoice line IDs that must be
                                  attached to the invoice
           :return: dict of value to create() the invoice
        """
        if context is None:
            context = {}
        journal_ids = self.pool.get('account.journal').search(cr, uid,
            [('type', '=', 'sale'), ('company_id', '=', x_service.partner_id.company_id.id)],
            limit=1)
        if not journal_ids:
            raise osv.except_osv(_('Error!'),
                _('Please define sales journal for this company: "%s" (id:%d).') % (x_service.partner_id.company_id.name, x_service.partner_id.company_id.id))
        invoice_vals = {
            'name': x_service.name or '',
            'origin': x_service.name,
            'type': 'out_invoice',
            'reference': x_service.name,
            'account_id': x_service.partner_id.property_account_receivable.id,
            'partner_id': x_service.partner_id.id,
            'journal_id': journal_ids[0],
            'invoice_line': [(6, 0, lines)],
            'currency_id': x_service.partner_id.property_product_pricelist.currency_id.id,
            'comment': x_service.note,
            'payment_term': x_service.partner_id.property_payment_term and x_service.partner_id.property_payment_term.id or False,
            'fiscal_position': x_service.partner_id.property_account_position.id or x_service.partner_id.property_account_position.id,
            'date_invoice': context.get('date_invoice', False),
            'company_id': x_service.partner_id.company_id.id,
            'user_id': x_service.user_id and x_service.user_id.id or False,
            'section_id' : x_service.partner_id.section_id.id
        }

        # Care for deprecated _inv_get() hook - FIXME: to be removed after 6.1
        invoice_vals.update(self._inv_get(cr, uid, x_service, context=context))
        return invoice_vals

    def _make_invoice(self, cr, uid, x_service, lines, context=None):
        inv_obj = self.pool.get('account.invoice')
        obj_invoice_line = self.pool.get('account.invoice.line')
        if context is None:
            context = {}
        invoiced_x_service_line_ids = self.pool.get('account.x.service.line').search(cr, uid, [('x_service_id', '=', x_service.id), ('invoiced', '=', True)], context=context)
        from_line_invoice_ids = []
        for invoiced_x_service_line_id in self.pool.get('account.x.service.line').browse(cr, uid, invoiced_x_service_line_ids, context=context):
            for invoice_line_id in invoiced_x_service_line_id.invoice_lines:
                if invoice_line_id.invoice_id.id not in from_line_invoice_ids:
                    from_line_invoice_ids.append(invoice_line_id.invoice_id.id)
        for preinv in x_service.invoice_ids:
            if preinv.state not in ('cancel',) and preinv.id not in from_line_invoice_ids:
                for preline in preinv.invoice_line:
                    inv_line_id = obj_invoice_line.copy(cr, uid, preline.id, {'invoice_id': False, 'price_unit': -preline.price_unit})
                    lines.append(inv_line_id)
        inv = self._prepare_invoice(cr, uid, x_service, lines, context=context)
        inv_id = inv_obj.create(cr, uid, inv, context=context)
        data = inv_obj.onchange_payment_term_date_invoice(cr, uid, [inv_id], inv['payment_term'], time.strftime(DEFAULT_SERVER_DATE_FORMAT))
        if data.get('value', False):
            inv_obj.write(cr, uid, [inv_id], data['value'], context=context)
        inv_obj.button_compute(cr, uid, [inv_id])
        return inv_id

 
    def manual_invoice(self, cr, uid, ids, context=None):
        """ create invoices for the given sales orders (ids), and open the form
            view of one of the newly created invoices
        """
        mod_obj = self.pool.get('ir.model.data')
        
        # create invoices through the sales orders' workflow
        inv_ids0 = set(inv.id for x_service in self.browse(cr, uid, ids, context) for inv in x_service.invoice_ids)
        self.signal_workflow(cr, uid, ids,'manual_invoice')
        inv_ids1 = set(inv.id for x_service in self.browse(cr, uid, ids, context) for inv in x_service.invoice_ids)
        # determine newly created invoices
        new_inv_ids = list(inv_ids1 - inv_ids0)

        res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')
        res_id = res and res[1] or False,

        return {
            'name': _('Customer Invoices'),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': [res_id],
            'res_model': 'account.invoice',
            'context': "{'type':'out_invoice'}",
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': new_inv_ids and new_inv_ids[0] or False,
        }


    def action_view_invoice(self, cr, uid, ids, context=None):
        '''
        This function returns an action that display existing invoices of given sales order ids. It can either be a in a list or in a form view, if there is only one invoice to show.
        '''
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')

        result = mod_obj.get_object_reference(cr, uid, 'account', 'action_invoice_tree1')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        #compute the number of invoices to display
        inv_ids = []
        for so in self.browse(cr, uid, ids, context=context):
            inv_ids += [invoice.id for invoice in so.invoice_ids]
        #choose the view_mode accordingly
        if len(inv_ids)>1:
            result['domain'] = "[('id','in',["+','.join(map(str, inv_ids))+"])]"
        else:
            res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')
            result['views'] = [(res and res[1] or False, 'form')]
            result['res_id'] = inv_ids and inv_ids[0] or False
        return result

    def action_invoice_create(self, cr, uid, ids, grouped=False, states=None, date_invoice = False, context=None):
        if states is None:
            states = ['draft','send', 'trial','done', 'expired','paid']
        res = False
        invoices = {}
        invoice_ids = []
        invoice = self.pool.get('account.invoice')
        obj_account_x_service_line = self.pool.get('account.x.service.line')
        partner_currency = {}
        if context is None:
            context = {}
        # If date was specified, use it as date invoiced, usefull when invoices are generated this month and put the
        # last day of the last month as invoice date
        if date_invoice:
            context['date_invoice'] = date_invoice
        for o in self.browse(cr, uid, ids, context=context):
            currency_id = o.partner_id.property_product_pricelist.currency_id.id
            if (o.partner_id.id in partner_currency) and (partner_currency[o.partner_id.id] <> currency_id):
                raise osv.except_osv(
                    _('Error!'),
                    _('You cannot group sales having different currencies for the same partner.'))

            partner_currency[o.partner_id.id] = currency_id
            lines = []
            tot_untax=0
            for line in o.line_ids:
                if line.invoiced:
                    continue
                elif (line.state in states):
                    tot_untax+=line.price_subtotal
                    if o.type_service=='normal':
                            lines.append(line.id)
                    elif o.type_service=='consumo':
                            if o.Imp_a_consumo<tot_untax:
                                    lines.append(line.id)
            created_lines = obj_account_x_service_line.invoice_line_create(cr, uid, lines)
            if created_lines:
                invoices.setdefault(o.partner_id.id or o.partner_id.id, []).append((o, created_lines))
        if not invoices:
            for o in self.browse(cr, uid, ids, context=context):
                """
                for i in o.invoice_ids:
                    if i.state == 'draft':
                        return i.id
                """
        for val in invoices.values():
            if grouped:
                res = self._make_invoice(cr, uid, val[0][0], reduce(lambda x, y: x + y, [l for o, l in val], []), context=context)
                invoice_ref = ''
                origin_ref = ''
                for o, l in val:
                    invoice_ref += 'SERV'+str(o.id) + '|'
                    origin_ref += 'SER'+str(o.id) + '|'
                    self.write(cr, uid, [o.id], {'state': 'progress'})
                    cr.execute('insert into account_x_service_invoice_rel (x_service_id,invoice_id) values (%s,%s)', (o.id, res))
                #remove last '|' in invoice_ref
                if len(invoice_ref) >= 1:
                    invoice_ref = invoice_ref[:-1]
                if len(origin_ref) >= 1:
                    origin_ref = origin_ref[:-1]
                invoice.write(cr, uid, [res], {'origin': origin_ref, 'name': invoice_ref})
            else:
                for x_service, il in val:
                    res = self._make_invoice(cr, uid, x_service, il, context=context)
                    invoice_ids.append(res)
                    self.write(cr, uid, [x_service.id], {'state': 'progress'})
                    cr.execute('insert into account_x_service_invoice_rel (x_service_id,invoice_id) values (%s,%s)', (x_service.id, res))
        return res

    def action_invoice_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'invoice_except'}, context=context)
        return True

    def action_invoice_end(self, cr, uid, ids, context=None):
        for this in self.browse(cr, uid, ids, context=context):
            for line in this.line_ids:
                if line.state == 'exception':
                    line.write({'state': 'confirmed'})
            if this.state == 'invoice_except':
                this.write({'state': 'progress'})
        return True
    def action_firma_contratto(self, cr, uid, ids, context=None):
        for this in self.browse(cr, SUPERUSER_ID, ids, context=context):
                 this.write({'firma_contratto': 'True'})
        view_ref = self.pool.get('ir.model.data').get_object_reference(cr, SUPERUSER_ID, 'rc_Cloudonthecloud', 'rc_cloudonthecloud_account_x_service_view_form_contratto')
        view_id = view_ref and view_ref[1] or False,
        return {
            'type': 'ir.actions.act_window',
            'name': _('Servizi Cloud'),
            'res_model': 'account.x.service',
            'res_id': ids[0],
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'nodestroy': True,
        }

    def action_cancel(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        x_service_line_obj = self.pool.get('account.x.service.line')
        account_invoice_obj = self.pool.get('account.invoice')
        for x_service in self.browse(cr, uid, ids, context=context):
            for inv in x_service.invoice_ids:
                if inv.state not in ('draft', 'cancel'):
                    raise osv.except_osv(
                        _('Cannot cancel this serice cloud!'),
                        _('First cancel all invoices attached to this sales order.'))
            for r in self.read(cr, uid, ids, ['invoice_ids']):
                account_invoice_obj.signal_invoice_cancel(cr, uid, r['invoice_ids'])
            sale_order_line_obj.write(cr, uid, [l.id for l in  sale.order_line],
                    {'state': 'cancel'})
        self.write(cr, uid, ids, {'state': 'cancel'})
        return True
    
    def action_done(self, cr, uid, ids, context=None):
        for x_service_line in self.browse(cr, uid, ids, context=context):
            self.pool.get('account.x.service.line').write(cr, uid, [line.id for line in x_service_line.line_ids], {'state': 'done'}, context=context)
        return self.write(cr, uid, ids, {'state': 'done'}, context=context)
    def account_x_service_confirm(self, cr, uid, ids, context=None):
         self.action_done(cr, uid, ids, context=context)

    def action_button_confirm(self, cr, uid, ids, context=None):
        assert len(ids) == 1, 'This option should only be used for a single id at a time.'
        self.account_x_service_confirm(cr, uid, ids)

        # redisplay the record as a sales order
        view_ref = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'rc_Cloudonthecloud', 'rc_cloudonthecloud_account_x_service_view_form')
        view_id = view_ref and view_ref[1] or False,
        return {
            'type': 'ir.actions.act_window',
            'name': _('Servizi Cloud'),
            'res_model': 'account.x.service',
            'res_id': ids[0],
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'nodestroy': True,
        }
    def action_quotation_send(self, cr, uid, ids, context=None):
        '''
        This function opens a window to compose an email, with the edi sale template message loaded by default
        '''
        x_service=self.browse(cr, uid, ids, context)
        x_service_notify_obj=self.pool.get('account.x.service.notify')
        x_service_notify_line_obj=self.pool.get('account.x.service.notify.line')
        mtp_obj = self.pool.get('email.template')
        data_odierna =  time.strftime('%Y-%m-%d')
        assert len(ids) == 1, 'This option should only be used for a single id at a time.'
        ir_model_data = self.pool.get('ir.model.data')
        notify=[]
        F_notify=False
        if F_notify==False:
                                notify_id=x_service_notify_obj.create(cr, uid, {'name':'Attivazione Servizi Cloud','state':'draft','partner_id':x_service.partner_id.id,'user_id':x_service.user_id.id,'data_notify':data_odierna,'x_service_policy':x_service.x_service_policy}, context)
                                notify.append(notify_id)
        F_notify=True
        """ Creo Dettaglio Notifica """
        x_service_notify_line_obj.create(cr, uid, {'name':'Attivazione Servizi Cloud',
                                                   'state':'draft',
                                                    'notify_id':notify_id,
                                                    'x_service_id':x_service.id,
                                                    'data_notify':data_odierna,
                                                    'amount_untaxed':x_service.amount_untaxed,
                                                    'amount_tax':x_service.amount_tax,
                                                    'amount_total':x_service.amount_total,                                                                                  
                                                    }, context)                                          
        x_service_notify_obj.write(cr, uid,notify_id, {'notify_ref':'noti-'+str(notify_id)}, context)
        try:
                    template_ids = mtp_obj.search(cr, uid, [('name','ilike', '%A_pagamento_per_attivazione_cloud%')])
                                #template_id = ir_model_data.get_object_reference(cr, uid, 'rc_Cloudonthecloud', 'email_template_edi_account_x_service_01')[1]
                    if template_ids:    
                                    template_id=template_ids[0]
                    else:
                                    template_id=False     
        except ValueError:
                    template_id = False
                                                        
        if notify:
                   if template_id:
                       for notify_id in notify:
                           mtp_obj.send_mail(cr, uid, template_id, notify_id, context=context)
                           x_service_notify_obj.write(cr, uid,notify_id, {'state':'notifyed'}, context)
                           notify_rec=x_service_notify_obj.browse(cr,uid,notify_id,context=context)

                           transaction_obj = request.registry.get('payment.transaction')
                           acquirer_obj = self.pool.get('payment.acquirer')
                           aquirer_ids=acquirer_obj.search(cr,uid,[('name','=','Paypal')])
                           if notify_rec.partner_id.country_id:
                                        country_id=notify_rec.partner_id.country_id.id
                           else:
                                        country_id=110               
                           if not country_id:
                                        country_id=110
                           if aquirer_ids:
                                   acquirer_id=aquirer_ids[0]
                                   tx_id = transaction_obj.create(cr,SUPERUSER_ID, {
                                    'acquirer_id': acquirer_id,
                                    'type': 'form',
                                    'amount': notify_rec.amount_total,
                                    'currency_id': notify_rec.partner_id.property_product_pricelist.currency_id.id,
                                    'partner_id': notify_rec.partner_id.id,
                                    'partner_country_id': country_id,
                                    'reference': notify_rec.notify_ref,
                                    'notify_id': notify_rec.id,
                                }, context=context)

                       self.write(cr, uid,ids[0],{'state':'send'})


        """    

        try:
            template_ids = mtp_obj.search(cr, uid, [('name','ilike', '%Notifica Servizi Cloud%')])

            #template_id = ir_model_data.get_object_reference(cr, uid, 'rc_Cloudonthecloud', 'email_template_edi_account_x_service_01')[1]
            template_id=template_ids[0]
        except ValueError:
            template_id = False
        if template_id:
                   mtp_obj.send_mail(cr, uid, template_id, ids[0], context=context)
                   self.write(cr, uid,ids[0],{'state':'send'})

        try:
            compose_form_id = ir_model_data.get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False 
        ctx = dict(context)
        ctx.update({
            'default_model': 'account.x.service',
            'default_res_id': ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }
        """
        view_ref = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'rc_Cloudonthecloud', 'rc_cloudonthecloud_account_x_service_view_form')
        view_id = view_ref and view_ref[1] or False,
        return {
            'type': 'ir.actions.act_window',
            'name': _('Servizi Cloud'),
            'res_model': 'account.x.service',
            'res_id': ids[0],
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'nodestroy': True,
        }
          
    def action_trial_send(self, cr, uid, ids, context=None):
        '''
        This function opens a window to compose an email, with the edi sale template message loaded by default
        '''
        x_service=self.browse(cr, uid, ids, context)
        x_service_notify_obj=self.pool.get('account.x.service.notify')
        x_service_notify_line_obj=self.pool.get('account.x.service.notify.line')
        mtp_obj = self.pool.get('email.template')
        assert len(ids) == 1, 'This option should only be used for a single id at a time.'
        ir_model_data = self.pool.get('ir.model.data')
        data_odierna =  time.strftime('%Y-%m-%d')
        notify=[]
        F_notify=False
        if F_notify==False:
                        notify_id=x_service_notify_obj.create(cr, uid, {'name':'Notifica servizio in prova','state':'draft','partner_id':x_service.partner_id.id,'user_id':x_service.user_id.id,'data_notify':data_odierna,'x_service_policy':x_service.x_service_policy}, context)
                        notify.append(notify_id)
        F_notify=True
        """ Creo Dettaglio Notifica """
        x_service_notify_line_obj.create(cr, uid, {'name':'Servizio Cloud in Prova',
                                                                   'state':'draft',
                                                                 'notify_id':notify_id,
                                                                'x_service_id':x_service.id,
                                                            'data_notify':data_odierna,
                                                                'amount_untaxed':x_service.amount_untaxed,
                                                                'amount_tax':x_service.amount_tax,
                                                            'amount_total':x_service.amount_total,                                                                                  
                                    }, context)                                          
        x_service_notify_obj.write(cr, uid,notify_id, {'notify_ref':'noti-'+str(notify_id)}, context)
        try:
                    template_ids = mtp_obj.search(cr, uid, [('name','ilike', '%Servizi Cloud Prova in Scadenza%')])
                                #template_id = ir_model_data.get_object_reference(cr, uid, 'rc_Cloudonthecloud', 'email_template_edi_account_x_service_01')[1]
                    if template_ids:    
                                    template_id=template_ids[0]
                    else:
                                    template_id=False     
        except ValueError:
                    template_id = False
                                                        
        if notify:
                   if template_id:
                       for notify_id in notify:
                           mtp_obj.send_mail(cr, uid, template_id, notify_id, context=context)
                           x_service_notify_obj.write(cr, uid,notify_id, {'state':'notifyed'}, context)
                           notify_rec=x_service_notify_obj.browse(cr,uid,notify_id,context=context)
                           transaction_obj = request.registry.get('payment.transaction')
                           acquirer_obj = self.pool.get('payment.acquirer')
                           aquirer_ids=acquirer_obj.search(cr,uid,[('name','=','Paypal')])
                           if notify_rec.partner_id.country_id:
                                        country_id=notify_rec.partner_id.country_id.id
                           else:
                                        country_id=110               
                           if not country_id:
                                        country_id=110
                           if aquirer_ids:
                                   acquirer_id=aquirer_ids[0]
                                   tx_id = transaction_obj.create(cr,SUPERUSER_ID, {
                                    'acquirer_id': acquirer_id,
                                    'type': 'form',
                                    'amount': notify_rec.amount_total,
                                    'currency_id': notify_rec.partner_id.property_product_pricelist.currency_id.id,
                                    'partner_id': notify_rec.partner_id.id,
                                    'partner_country_id': country_id,
                                    'reference': notify_rec.notify_ref,
                                    'notify_id': notify_rec.id,
                                }, context=context)

                       self.write(cr, uid,ids[0],{'state':'trial'})

        """
        try:
            template_ids = mtp_obj.search(cr, uid, [('name','ilike', '%Prova Periodo Servizi Cloud%')])
            #template_id = ir_model_data.get_object_reference(cr, uid, 'rc_Cloudonthecloud', 'email_template_edi_account_x_service_01')[1]
            if template_ids:    
                template_id=template_ids[0]
            else:
                template_id=False     
        except ValueError:
            template_id = False
        if template_id:
                   
                   mtp_obj.send_mail(cr, uid, template_id, ids[0], context=context)
                   self.write(cr, uid,ids[0],{'state':'trial'})
        """ 
        view_ref = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'rc_Cloudonthecloud', 'rc_cloudonthecloud_account_x_service_view_form')
        view_id = view_ref and view_ref[1] or False,
        return {
            'type': 'ir.actions.act_window',
            'name': _('Servizi Cloud'),
            'res_model': 'account.x.service',
            'res_id': ids[0],
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'nodestroy': True,
        }

    def recurring_create_invoice(self, cr, uid, ids=None, context=None):
        return self._recurring_create_invoice(cr, uid, ids=None, context=context)
    def _cron_recurring_create_invoice(self, cr, uid, context=None):
        return self._recurring_create_invoice(cr, uid, [], automatic=True, context=context)
    def _recurring_create_invoice(self, cr, uid, ids=None, automatic=False, context=None):
        context = context or {}
        invoice_ids = []
        current_date =  time.strftime('%Y-%m-%d')
        mtp_obj = self.pool.get('email.template')
        if ids:
            x_service_ids = ids
        else:
            x_service_ids = self.search(cr, uid, [('date_next_invoice','=', current_date), ('state','<>', 'draft'), ('state','<>', 'trial'), ('state','<>', 'send'), ('state','<>', 'cancel'), ('state','<>', 'progress'), ('state','<>', 'expired'), ('F_invoice_repeat','=', True)])
        if x_service_ids:
            invoice_ids.append(self.action_invoice_create(cr, uid, x_service_ids, grouped=True, states=None, date_invoice = current_date, context=None))
    
        for x_service in self.browse(cr, uid, x_service_ids, context=context):
            try:
                #invoice_values = self._prepare_invoice(cr, uid, x_service, context=context)
                #invoice_ids.append(self.pool['account.invoice'].create(cr, uid, invoice_values, context=context))

                next_date = datetime.strptime(x_service.date_next_invoice or current_date, "%Y-%m-%d")
                interval = x_service.num_decorrenza
                if x_service.decorrenza == 1:
                    new_date = next_date+relativedelta(days=+interval)
                elif x_service.decorrenza == 7:
                    new_date = next_date+relativedelta(weeks=+interval)
                elif x_service.decorrenza == 30:
                    new_date = next_date+relativedelta(months=+interval)
                else:
                    new_date = next_date+relativedelta(years=+interval)
                new_date_expire=new_date+relativedelta(days=-x_service.gg_alert)
                self.write(cr, uid, [x_service.id], {'date_next_invoice': new_date.strftime('%Y-%m-%d'),'date_alert_expire':new_date_expire.strftime('%Y-%m-%d'),'date_service':current_date}, context=context)
                if automatic:
                    cr.commit()
            except Exception:
                if automatic:
                    cr.rollback()
                    _logger.error(traceback.format_exc())
                else:
                    raise
        for invoice_id in invoice_ids:
                self._validate_invoices(cr, uid, invoice_id,context=context)
                self._reconcile_invoices_2(cr, uid, invoice_id,context=context)
                try:
                            template_ids = mtp_obj.search(cr, uid, [('name','ilike', '%Invoice - Send by Email%')])
                                        #template_id = ir_model_data.get_object_reference(cr, uid, 'rc_Cloudonthecloud', 'email_template_edi_account_x_service_01')[1]
                            if template_ids:    
                                            template_id=template_ids[0]
                            else:
                                            template_id=False     
                except ValueError:
                            template_id = False
                mtp_obj.send_mail(cr, uid, template_id, invoice_id, context=context)
                
        return invoice_ids
    def _validate_invoices(self, cr, uid,invoice_id, context=None):
        wf_service = netsvc.LocalService("workflow")
        invoice_obj = self.pool.get('account.invoice')
        invoice_ids = invoice_obj.search(
            cr, uid,
            [('state', 'in', ['draft']),
             ('id', '=', invoice_id)],
            context=context)
        _logger.debug('Invoices to validate: %s', invoice_ids)
        for invoice_id in invoice_ids:
                """with commit(cr):"""
                wf_service.trg_validate(uid, 'account.invoice',
                                        invoice_id, 'invoice_open', cr)
    def _reconcile_invoices_2(self, cr, uid, reconcilie_id=None, context=None):
        invoice_obj = self.pool.get('account.invoice')
        """with commit(cr):"""
        invoice_obj.reconcile_invoice_2(cr, uid,
                                              reconcilie_id,
                                              context=context)
    def validate_x_service_paid(self, cr, uid, ids=None, context=None):
        x_service_notify_line_obj=self.pool.get('account.x.service.notify.line')
        x_service_notify_obj=self.pool.get('account.x.service.notify')
        x_service_obj=self.pool.get('account.x.service')
        context = context or {}
        x_service_ver_ids = []
        current_date =  time.strftime('%Y-%m-%d')
        if ids:
            x_service_ids = ids
        else:
            x_service_ids = x_service_obj.search(cr, uid, [('date_next_invoice','>=', current_date), ('state','<>', 'draft'), ('state','<>', 'cancel'),   ('F_invoice_repeat','=', True)])
        for x_service in x_service_obj.browse(cr, uid,x_service_ids,context=context):
            x_service_id=x_service.id
            date_service=datetime.strptime(str(x_service.date_service),"%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
            x_service_notify_line_ids = x_service_notify_line_obj.search(cr, uid, [('x_service_id','=', x_service_id),('data_notify','>=', date_service)])    
            
            for x_service_notify_line in x_service_notify_line_obj.browse(cr, uid, x_service_notify_line_ids, context=context):
            
                x_service_notify_ids= x_service_notify_obj.search(cr, uid, [('id','=', x_service_notify_line.notify_id.id),('state','=','notifyed')])       
                for x_service_notify in x_service_notify_obj.browse(cr, uid,x_service_notify_ids, context=context):
                    #if x_service_notify.paypal_url:
                                #if x_service_notify.paypal_status=='VERIFIED':
                                if x_service_notify.paypal_status=='VERIFIED':
                                    x_service_obj.write(cr,uid,x_service_id,{'state':'paid'})
                                    x_service_ver_ids.append(x_service_id)
                                    x_service_notify_obj.write(cr, uid,x_service_notify.id, {'state':'verified'}, context)
 
        return x_service_ver_ids
    def notify_service_expired(self, cr, uid, ids=None, context=None):
        '''
            avviso utente con servizi scaduti
        '''
        partner_obj=self.pool.get('res.partner')
        x_service_obj=self.pool.get('account.x.service')
        x_service_notify_obj=self.pool.get('account.x.service.notify')
        x_service_notify_line_obj=self.pool.get('account.x.service.notify.line')
        data_odierna =  time.strftime('%Y-%m-%d')
        notify=[]
        if ids:
            x_service_ids = ids
        partner_ids=partner_obj.search(cr, uid, [('active','=', True),('customer','=', True)])
        for partner_id in partner_ids:
               F_notify=False
               if not ids:
                   x_service_ids=x_service_obj.search(cr, uid, [('state','in', ['done','send','progress']),('date_next_invoice','<', data_odierna), ('partner_id','=', partner_id)])
                   
               user_id=0
               x_service_policy=''
               for x_service in self.browse(cr, uid, x_service_ids, context=context):
                                  date_expired = datetime.strptime(x_service.date_next_invoice or current_date, "%Y-%m-%d")
                                  date_magg_2 =  parser.parse(data_odierna)+relativedelta(days=+1)
                                  date_magg =  str(date_magg_2.strftime('%Y-%m-%d'))
                                  if date_expired>=date_magg_2:
                                      amount_untaxed=(x_service.amount_untaxed*120)/100
                                      if amount_untaxed<10:
                                          amount_untaxed=10
                                      if x_service.amount_tax:
                                              amount_tax=(amount_untaxed*20)/100
                                      else:
                                              amount_tax=0
                                      amount_total=amount_untaxed+amount_tax
                                  else:
                                      amount_untaxed=x_service.amount_untaxed
                                      amount_tax=x_service.amount_tax
                                      amount_total=amount_untaxed+amount_tax
                                  date_expired_dt=datetime.strptime(str(date_expired),"%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
                                  if user_id!=x_service.user_id:
                                                user_id=x_service.user_id
                                                F_notify=False
                                  if x_service_policy!=x_service.x_service_policy:
                                                x_service_policy=x_service.x_service_policy
                                                F_notify=False
                                  if F_notify==False:
                                        notify_id=x_service_notify_obj.create(cr, uid, {'name':'Notifica servizi scaduti','state':'draft','partner_id':partner_id,'user_id':user_id.id,'data_notify':data_odierna,'x_service_policy':x_service_policy}, context)
                                        notify.append(notify_id)

                                  F_notify=True
                                  """ Creo Dettaglio Notifica """
                                  x_service_notify_line_obj.create(cr, uid, {'name':'Servizio scaduti',
                                                                                     'state':'draft',
                                                                                     'notify_id':notify_id,
                                                                                     'x_service_id':x_service.id,
                                                                                     'data_notify':data_odierna,
                                                                                     'amount_untaxed':x_service.amount_untaxed,
                                                                                     'amount_tax':x_service.amount_tax,
                                                                                     'amount_total':x_service.amount_total,
                                                                                     }, context)                                          
                                  x_service_notify_obj.write(cr, uid,notify_id, {'notify_ref':'noti-'+str(notify_id)}, context)
                                  x_service_obj.write(cr,uid,x_service.id,{'state':'expired'})
        mtp_obj = self.pool.get('email.template')
        try:
                    template_ids = mtp_obj.search(cr, uid, [('name','ilike', '%Servizi Cloud Scaduti%')])
                                #template_id = ir_model_data.get_object_reference(cr, uid, 'rc_Cloudonthecloud', 'email_template_edi_account_x_service_01')[1]
                    if template_ids:    
                                    template_id=template_ids[0]
                    else:
                                    template_id=False     
        except ValueError:
                    template_id = False
                                                        
        if notify:
                   transaction_obj = request.registry.get('payment.transaction')
                   acquirer_obj = self.pool.get('payment.acquirer')
                   if template_id:
                       for notify_id in notify:
                           mtp_obj.send_mail(cr, uid, template_id, notify_id, context=context)
                           x_service_notify_obj.write(cr, uid,notify_id, {'state':'notifyed'}, context)
                           notify_rec=x_service_notify_obj.browse(cr,uid,notify_id,context=context)
                           aquirer_ids=acquirer_obj.search(cr,uid,[('name','=','Paypal')])
                           if aquirer_ids:
                                   acquirer_id=aquirer_ids[0]
                                   tx_id = transaction_obj.create(cr,SUPERUSER_ID, {
                                    'acquirer_id': acquirer_id,
                                    'type': 'form',
                                    'amount': notify_rec.amount_total,
                                    'currency_id': notify_rec.partner_id.property_product_pricelist.currency_id.id,
                                    'partner_id': notify_rec.partner_id.id,
                                    'partner_country_id': notify_rec.partner_id.country_id.id,
                                    'reference': notify_rec.notify_ref,
                                    'notify_id': notify_rec.id,
                                }, context=context)

        return notify
       
        
    def notify_service_expire(self, cr, uid, ids=None, context=None):
        '''
            avviso utente con servizi in scadenza
        '''
        partner_obj=self.pool.get('res.partner')
        x_service_obj=self.pool.get('account.x.service')
        x_service_notify_obj=self.pool.get('account.x.service.notify')
        x_service_notify_line_obj=self.pool.get('account.x.service.notify.line')
        data_odierna =  time.strftime('%Y-%m-%d')
        notify=[]
        if ids:
            x_service_ids = ids
        partner_ids=partner_obj.search(cr, uid, [('active','=', True),('customer','=', True)])
        for partner_id in partner_ids:
               F_notify=False
               if not ids:
                   x_service_ids=x_service_obj.search(cr, uid, [('state','in', ['done','progress','paid']),('date_next_invoice','>=', data_odierna), ('partner_id','=', partner_id)])
                   
               user_id=0
               x_service_policy=''
               for x_service in self.browse(cr, uid, x_service_ids, context=context):
                        if x_service.F_invoice_repeat==False and x_service.state=='paid':
                            continue
                        date_expire = datetime.strptime(x_service.date_next_invoice or current_date, "%Y-%m-%d")
                        interval = x_service.gg_alert

                        if date_expire:
                            date_notify = date_expire+relativedelta(days=-interval)
                        else: 
                            date_notify=   data_odierna+relativedelta(days=-interval)
                        date_notify=datetime.strptime(str(date_notify),"%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
                        date_expire_dt=datetime.strptime(str(date_expire),"%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
                        if date_notify<=data_odierna and date_expire_dt>=data_odierna:
                                  if user_id!=x_service.user_id:
                                                user_id=x_service.user_id
                                                F_notify=False
                                  if x_service_policy!=x_service.x_service_policy:
                                                x_service_policy=x_service.x_service_policy
                                                F_notify=False
                                  if F_notify==False:
                                        notify_id=x_service_notify_obj.create(cr, uid, {'name':'Notifica scadenza servizio','state':'draft','partner_id':partner_id,'user_id':user_id.id,'data_notify':data_odierna,'x_service_policy':x_service_policy}, context)
                                        notify.append(notify_id)

                                  F_notify=True
                                  """ Creo Dettaglio Notifica """
                                  x_service_notify_line_obj.create(cr, uid, {'name':'Servizio in scadenza',
                                                                                     'state':'draft',
                                                                                     'notify_id':notify_id,
                                                                                     'x_service_id':x_service.id,
                                                                                     'data_notify':data_odierna,
                                                                                     'amount_untaxed':x_service.amount_untaxed,
                                                                                     'amount_tax':x_service.amount_tax,
                                                                                     'amount_total':x_service.amount_total,
                                                                                     }, context)                                          
                                  x_service_notify_obj.write(cr, uid,notify_id, {'notify_ref':'noti-'+str(notify_id)}, context)
        mtp_obj = self.pool.get('email.template')
        try:
                    template_ids = mtp_obj.search(cr, uid, [('name','ilike', '%Servizi Cloud in Scadenza%')])
                                #template_id = ir_model_data.get_object_reference(cr, uid, 'rc_Cloudonthecloud', 'email_template_edi_account_x_service_01')[1]
                    if template_ids:    
                                    template_id=template_ids[0]
                    else:
                                    template_id=False     
        except ValueError:
                    template_id = False
                                                        
        if notify:
                   transaction_obj = request.registry.get('payment.transaction')
                   acquirer_obj = self.pool.get('payment.acquirer')
                   if template_id:
                       for notify_id in notify:
                           mtp_obj.send_mail(cr, uid, template_id, notify_id, context=context)
                           x_service_notify_obj.write(cr, uid,notify_id, {'state':'notifyed'}, context)
                           notify_rec=x_service_notify_obj.browse(cr,uid,notify_id,context=context)
                           aquirer_ids=acquirer_obj.search(cr,uid,[('name','=','Paypal')])
                           if aquirer_ids:
                                   acquirer_id=aquirer_ids[0]
                                   tx_id = transaction_obj.create(cr,SUPERUSER_ID, {
                                    'acquirer_id': acquirer_id,
                                    'type': 'form',
                                    'amount': notify_rec.amount_total,
                                    'currency_id': notify_rec.partner_id.property_product_pricelist.currency_id.id,
                                    'partner_id': notify_rec.partner_id.id,
                                    'partner_country_id': notify_rec.partner_id.country_id.id,
                                    'reference': notify_rec.notify_ref,
                                    'notify_id': notify_rec.id,
                                }, context=context)

        return notify

    def notify_service_trial_expire(self, cr, uid, ids=None, context=None):
        '''
            avviso utente con servizi in scadenza
        '''
        partner_obj=self.pool.get('res.partner')
        x_service_obj=self.pool.get('account.x.service')
        x_service_notify_obj=self.pool.get('account.x.service.notify')
        x_service_notify_line_obj=self.pool.get('account.x.service.notify.line')
        data_odierna =  time.strftime('%Y-%m-%d')
        notify=[]
        if ids:
            x_service_ids = ids
        partner_ids=partner_obj.search(cr, uid, [('active','=', True),('customer','=', True)])
        for partner_id in partner_ids:
               F_notify=False
               if not ids:
                   x_service_ids=x_service_obj.search(cr, uid, [('trial_start','<=', data_odierna),('trial_end','>=', data_odierna), ('state','=', 'trial'), ('partner_id','=', partner_id)])
               user_id=0
               x_service_policy=''
               for x_service in self.browse(cr, uid, x_service_ids, context=context):
                        date_expire = datetime.strptime(x_service.trial_end or current_date, "%Y-%m-%d")
                        interval = x_service.trail_gg_alert
                        if date_expire:
                            date_notify = date_expire+relativedelta(days=-interval)
                        else: 
                            date_notify=   data_odierna+relativedelta(days=-interval)
                        date_notify=datetime.strptime(str(date_notify),"%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
                        date_expire_dt=datetime.strptime(str(date_expire),"%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
                        if date_notify<=data_odierna and date_expire_dt>=data_odierna:
                                  if user_id!=x_service.user_id:
                                                user_id=x_service.user_id
                                                F_notify=False
                                  if x_service_policy!=x_service.x_service_policy:
                                                x_service_policy=x_service.x_service_policy
                                                F_notify=False

                                  if F_notify==False:
                                        notify_id=x_service_notify_obj.create(cr, uid, {'name':'Notifica scadenza servizio in prova','state':'draft','partner_id':partner_id,'user_id':user_id.id,'data_notify':data_odierna,'x_service_policy':x_service_policy}, context)
                                        notify.append(notify_id)
                                  F_notify=True
                                  """ Creo Dettaglio Notifica """
                                  x_service_notify_line_obj.create(cr, uid, {'name':'Servizio prova in scadenza',
                                                                                     'state':'draft',
                                                                                     'notify_id':notify_id,
                                                                                     'x_service_id':x_service.id,
                                                                                     'data_notify':data_odierna,
                                                                                     'amount_untaxed':x_service.amount_untaxed,
                                                                                     'amount_tax':x_service.amount_tax,
                                                                                     'amount_total':x_service.amount_total,                                                                                  
                                                                                     }, context)                                          
                                  x_service_notify_obj.write(cr, uid,notify_id, {'notify_ref':'noti-'+str(notify_id)}, context)
            
        mtp_obj = self.pool.get('email.template')
        try:
                    template_ids = mtp_obj.search(cr, uid, [('name','ilike', '%Servizi Cloud Prova in Scadenza%')])
                                #template_id = ir_model_data.get_object_reference(cr, uid, 'rc_Cloudonthecloud', 'email_template_edi_account_x_service_01')[1]
                    if template_ids:    
                                    template_id=template_ids[0]
                    else:
                                    template_id=False     
        except ValueError:
                    template_id = False
                                                        
        if notify:
                   transaction_obj = request.registry.get('payment.transaction')
                   acquirer_obj = self.pool.get('payment.acquirer')
                   if template_id:
                       for notify_id in notify:
                           mtp_obj.send_mail(cr, uid, template_id, notify_id, context=context)
                           x_service_notify_obj.write(cr, uid,notify_id, {'state':'notifyed'}, context)
                           notify_rec=x_service_notify_obj.browse(cr,uid,notify_id,context=context)
                           aquirer_ids=acquirer_obj.search(cr,uid,[('name','=','Paypal')])
                           if aquirer_ids:
                                   acquirer_id=aquirer_ids[0]
                                   tx_id = transaction_obj.create(cr, SUPERUSER_ID, {
                                    'acquirer_id': acquirer_id,
                                    'type': 'form',
                                    'amount': notify_rec.amount_total,
                                    'currency_id': notify_rec.partner_id.property_product_pricelist.currency_id.id,
                                    'partner_id': notify_rec.partner_id.id,
                                    'partner_country_id': notify_rec.partner_id.country_id.id,
                                    'reference': notify_rec.notify_ref,
                                    'notify_id': notify_rec.id,
                                },context=context)

 
        return notify
    def create(self, cr, uid, values, context=None):

        return super(account_x_service, self).create(cr, uid, values, context=context)

class account_x_service_line(osv.osv):
    def _check_x_service_id(self, cr, uid, ids, context=None):
        x_service_obj = self.pool.get('account.x.service')
        if context:
            x_service_obj_rec = x_service_obj.browse(cr, uid, context['active_ids'], context=context)
            if x_service_obj_rec:
                return x_service_obj_rec.id
            else:
                return 1
        else:
                return 1
    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        res = {}
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, line.service_qty, line.product_id, line.x_service_id.partner_id)
            cur = line.x_service_id.partner_id.property_product_pricelist.currency_id
            res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])
        return res
    def _fnct_line_invoiced(self, cr, uid, ids, field_name, args, context=None):
        res = dict.fromkeys(ids, False)
        for this in self.browse(cr, uid, ids, context=context):
            res[this.id] = this.invoice_lines and \
                all(iline.invoice_id.state != 'cancel' for iline in this.invoice_lines) 
        return res
    def _x_service_lines_from_invoice(self, cr, uid, ids, context=None):
        # direct access to the m2m table is the less convoluted way to achieve this (and is ok ACL-wise)
        cr.execute("""SELECT DISTINCT sol.id FROM account_x_service_invoice_rel rel JOIN
                                                  account_x_service_line sol ON (sol.x_service_id = rel.x_service_id)
                                    WHERE rel.invoice_id = ANY(%s)""", (list(ids),))
        return [i[0] for i in cr.fetchall()]



    _name = 'account.x.service.line'
    _description = 'Righe Servizi collegati al cliente  '
    _columns={
        'x_service_id': fields.many2one('account.x.service', 'Servizio', required=True, ondelete='cascade', select=True, readonly=True ),
        'name': fields.char('Nome Servizio', size=64, required=True,
            readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, select=True),
        'product_id': fields.many2one('product.product', 'Articolo', readonly=True, required=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, help="Il prodotto può essere cambiato solo in draft"),

        'service_qty': fields.float('Quantità', digits_compute= dp.get_precision('Product UoS'), required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'service_uom': fields.many2one('product.uom', 'Unit of Measure ', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'service_uos_qty': fields.float('Quantity (UoS)' ,digits_compute= dp.get_precision('Product UoS'), readonly=True, states={'draft': [('readonly', False)]}),
        'service_uos': fields.many2one('product.uom', 'Product UoS'),
 
        'price_unit': fields.float('Prezzo', required=True, digits_compute= dp.get_precision('Product Price'), readonly=True, states={'draft': [('readonly', False)]}),
        'user_id': fields.many2one('res.users', 'sistemista',required=False, select=True),

        'state': fields.selection([('cancel', 'Cancelled'),('draft', 'Draft'),('confirmed', 'Confirmed'),('exception', 'Exception'),('done', 'Done')], 'Status', required=True, readonly=True,
                help='* The \'Draft\' status is set when the related sales order in draft status. \
                    \n* The \'Confirmed\' status is set when the related sales order is confirmed. \
                    \n* The \'Exception\' status is set when the related sales order is set as exception. \
                    \n* The \'Done\' status is set when the sales order line has been picked. \
                    \n* The \'Cancelled\' status is set when a user cancel the sales order related.'),
        'note': fields.text('Note'),
        'tax_id': fields.many2many('account.tax', 'account_x_service_tax', 'x_service_line_id', 'tax_id', 'Taxes', readonly=True, states={'draft': [('readonly', False)]}),
        'discount': fields.float('Discount (%)', digits_compute= dp.get_precision('Discount'), readonly=True, states={'draft': [('readonly', False)]}),
        'price_subtotal': fields.function(_amount_line, string='Subtotal', digits_compute= dp.get_precision('Account')),
        'invoice_lines': fields.many2many('account.invoice.line', 'account_x_service_line_invoice_rel', 'x_service_line_id', 'invoice_id', 'Invoice Lines', readonly=True),
        'invoiced': fields.function(_fnct_line_invoiced, string='Invoiced', type='boolean',
            store={
                'account.invoice': (_x_service_lines_from_invoice, ['state'], 10),
                'account.x.service.line': (lambda self,cr,uid,ids,ctx=None: ids, ['invoice_lines'], 10)
            }),

    }
    _defaults = {
        'discount': 0.00,
        'x_service_id':_check_x_service_id,
        'service_qty': 1.00,
        'state': 'draft',
        'name': lambda obj, cr, uid, context: '/',
        'note': lambda self, cr, uid, context: self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.sale_note,
    }
    def _check_no_view(self, cr, uid, ids, context=None):
        service_lines = self.browse(cr, uid, ids, context=context)
        for line in service_lines:
            if not line.x_service_id:
                return False
        return True

    _constraints = [
        (_check_no_view, 'You cannot create service line manca il la teastata .', ['x_service_id']),
    ]

    
    def create(self, cr, uid, values, context=None):
        if values.get('order_id') and values.get('product_id') and  any(f not in values for f in ['name', 'price_unit', 'service_qty' ]):
            x_service = self.pool['account.x.service'].read(cr, uid, values['order_id'], [], context=context)

        return super(account_x_service_line, self).create(cr, uid, values, context=context)
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(account_x_service_line, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar, submenu=submenu)
        x_service = self.pool.get('account.x.service')
        if context:
            x_service_obj = x_service.browse(cr, uid, [1], context=context)
            
            x_service_id = x_service_obj and x_service_obj[0].id 
        res['x_service_id']=x_service_id
        return res
    def _resolve_x_service_id_from_context(self, cr, uid, context=None):
        return None
    def product_id_change(self, cr, uid, ids, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, user_id=False,context=None):
        context = context or {}
        lang = lang or context.get('lang', False)
        if not partner_id:
            raise osv.except_osv(_('No Customer Defined!'), _('Before choosing a product,\n select a customer in the cloud form.'))
        warning = False
        product_uom_obj = self.pool.get('product.uom')
        partner_obj = self.pool.get('res.partner')
        product_obj = self.pool.get('product.product')
        context = {'lang': lang, 'partner_id': partner_id}
        partner = partner_obj.browse(cr, uid, partner_id)
        lang = partner.lang
        context_partner = {'lang': lang, 'partner_id': partner_id}

        if not product:
            return {'value': {'th_weight': 0,
                'service_qty': qty}, 'domain': {'service_uom': [],
                   'service_uos': []}}
        if not date_order:
            date_order = time.strftime(DEFAULT_SERVER_DATE_FORMAT)

        result = {}
        warning_msgs = ''
        product_obj = product_obj.browse(cr, uid, product, context=context_partner)

        uom2 = False
        if uom:
            uom2 = product_uom_obj.browse(cr, uid, uom)
            if product_obj.uom_id.category_id.id != uom2.category_id.id:
                uom = False
        if uos:
            if product_obj.uos_id:
                uos2 = product_uom_obj.browse(cr, uid, uos)
                if product_obj.uos_id.category_id.id != uos2.category_id.id:
                    uos = False
            else:
                uos = False

        fpos = False
        if not fiscal_position:
            fpos = partner.property_account_position or False
        else:
            fpos = self.pool.get('account.fiscal.position').browse(cr, uid, fiscal_position)
        if update_tax: #The quantity only have changed
            result['tax_id'] = self.pool.get('account.fiscal.position').map_tax(cr, uid, fpos, product_obj.taxes_id)

        if not flag:
            result['name'] = self.pool.get('product.product').name_get(cr, uid, [product_obj.id], context=context_partner)[0][1]
            if product_obj.description_sale:
                result['name'] += '\n'+product_obj.description_sale
        domain = {}
        if (not uom) and (not uos):
            result['service_uom'] = product_obj.uom_id.id
            if product_obj.uos_id:
                result['service_uos'] = product_obj.uos_id.id
                result['service_uos_qty'] = qty * product_obj.uos_coeff
                uos_category_id = product_obj.uos_id.category_id.id
            else:
                result['service_uos'] = False
                result['service_uos_qty'] = qty
                uos_category_id = False
            domain = {'service_uom':
                        [('category_id', '=', product_obj.uom_id.category_id.id)],
                        'service_uos':
                        [('category_id', '=', uos_category_id)]}
        elif uos and not uom: # only happens if uom is False
            result['service_uom'] = product_obj.uom_id and product_obj.uom_id.id
            result['service_qty'] = qty_uos / product_obj.uos_coeff
        elif uom: # whether uos is set or not
            default_uom = product_obj.uom_id and product_obj.uom_id.id
            q = product_uom_obj._compute_qty(cr, uid, uom, qty, default_uom)
            if product_obj.uos_id:
                result['service_uos'] = product_obj.uos_id.id
                result['service_uos_qty'] = qty * product_obj.uos_coeff
            else:
                result['service_uos'] = False
                result['service_uos_qty'] = qty

        if not uom2:
            uom2 = product_obj.uom_id
        # get unit price
        if not user_id:
            if partner.user_id:
                user_id=partner.user_id.id
            else:
                user_id=uid
        result['user_id'] = user_id

        if partner_id:
            pricelist=partner.property_product_pricelist.id
        if not pricelist:
            warn_msg = _('You have to select a pricelist or a customer in the cloud form !\n'
                    'Please set one before choosing a product.')
            warning_msgs += _("No Pricelist ! : ") + warn_msg +"\n\n"
        else:
            price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist],
                    product, qty or 1.0, partner_id, {
                        'uom': uom or result.get('service_uom'),
                        'date': date_order,
                        })[pricelist]
            if price is False:
                warn_msg = _("Cannot find a pricelist line matching this product and quantity.\n"
                        "You have to change either the product, the quantity or the pricelist.")

                warning_msgs += _("No valid pricelist line found ! :") + warn_msg +"\n\n"
            else:
                result.update({'price_unit': price})
        if warning_msgs:
            warning = {
                       'title': _('Configuration Error!'),
                       'message' : warning_msgs
                    }
        return {'value': result, 'domain': domain, 'warning': warning}

    def product_uom_change(self, cr, uid, ids, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, user_id=False,context=None):
        context = context or {}
        partner_obj = self.pool.get('res.partner')
        partner = partner_obj.browse(cr, uid, partner_id)

        lang = lang or ('lang' in context and context['lang'])
        if not uom:
            return {'value': {'price_unit': 0.0, 'product_uom' : uom or False}}
        if partner:
            pricelist=partner.property_product_pricelist.id
        else:
            pricelist=1
        return self.product_id_change(cr, uid, ids, product,
                qty=qty, uom=uom, qty_uos=qty_uos, uos=uos, name=name,
                partner_id=partner_id, lang=lang, update_tax=update_tax,
                date_order=date_order,user_id=user_id, context=context)
    def _get_line_qty(self, cr, uid, line, context=None):
        if line.service_uos:
            return line.service_uos_qty or 0.0
        return line.service_qty

    def _get_line_uom(self, cr, uid, line, context=None):
        if line.service_uos:
            return line.service_uos.id
        return line.service_uom.id

    def _prepare_account_x_service_line_invoice_line(self, cr, uid, line, account_id=False, context=None):
        """Prepare the dict of values to create the new invoice line for a
           sales order line. This method may be overridden to implement custom
           invoice generation (making sure to call super() to establish
           a clean extension chain).

           :param browse_record line: sale.order.line record to invoice
           :param int account_id: optional ID of a G/L account to force
               (this is used for returning products including service)
           :return: dict of values to create() the invoice line
        """
        res = {}
        if not line.invoiced:
            if not account_id:
                if line.product_id:
                    account_id = line.product_id.property_account_income.id
                    if not account_id:
                        account_id = line.product_id.categ_id.property_account_income_categ.id
                    if not account_id:
                        raise osv.except_osv(_('Error!'),
                                _('Please define income account for this product: "%s" (id:%d).') % \
                                    (line.product_id.name, line.product_id.id,))
                else:
                    prop = self.pool.get('ir.property').get(cr, uid,
                            'property_account_income_categ', 'product.category',
                            context=context)
                    account_id = prop and prop.id or False
            uosqty = self._get_line_qty(cr, uid, line, context=context)
            uos_id = self._get_line_uom(cr, uid, line, context=context)
            pu = 0.0
            if uosqty:
                pu = round(line.price_unit * line.service_qty / uosqty,
                        self.pool.get('decimal.precision').precision_get(cr, uid, 'Product Price'))
            fpos = line.x_service_id.partner_id.property_account_position or False
            account_id = self.pool.get('account.fiscal.position').map_account(cr, uid, fpos, account_id)
            if not account_id:
                raise osv.except_osv(_('Error!'),
                            _('There is no Fiscal Position defined or Income category account defined for default properties of Product categories.'))
            #print "account_id",account_id
            res = {
                'name': line.name,
                'sequence': 10,
                'origin': line.x_service_id.name,
                'account_id': account_id,
                'price_unit': pu,
                'quantity': uosqty,
                'discount': line.discount,
                'uos_id': uos_id,
                'product_id': line.product_id.id or False,
                'invoice_line_tax_id': [(6, 0, [x.id for x in line.tax_id])],
                'account_analytic_id': False,
            }

        return res

    def invoice_line_create(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        create_ids = []
        x_services = set()
        for line in self.browse(cr, uid, ids, context=context):
            vals = self._prepare_account_x_service_line_invoice_line(cr, uid, line, False, context)
            if vals:
                inv_id = self.pool.get('account.invoice.line').create(cr, uid, vals, context=context)
                self.write(cr, uid, [line.id], {'invoice_lines': [(4, inv_id)]}, context=context)
                x_services.add(line.x_service_id.id)
                create_ids.append(inv_id)
        # Trigger workflow events
        for x_service_id in x_services:
            workflow.trg_write(uid, 'account.x.service', x_service_id, cr)
        return create_ids    
class res_partner(osv.osv):
    def _service_count(self, cr, uid, ids, field_name, arg, context=None):
        x_service = self.pool['account.x.service']
        return {
            partner_id: x_service.search_count(cr,uid, [('partner_id', '=', partner_id)], context=context)
            for partner_id in ids
        }
    
    """ Inherits partner and adds Service information in the partner form """
    _inherit = 'res.partner'
    _columns = {
        'country_id': fields.many2one('res.country', 'Country', ondelete='restrict'),
        'x_service_ids': fields.one2many('account.x.service', 'partner_id', 'Servizi'),
        'x_service_count': fields.function(_service_count, string='# Servizi', type='integer'),
        'website_published': fields.boolean('website published'),
    }
    _defaults = {
        'country_id': 110,
    }

    def create_user_portal(self, cr, uid, ids,  context=None):
            user_obj = self.pool.get('res.users')
            partner_obj = self.pool.get('res.partner')
            partner_ids_obj=partner_obj.browse(cr, uid,ids,context=context)
            if partner_ids_obj.email:
                user_ids = user_obj.search(cr, uid, [('login','=', partner_ids_obj.email)])    
                vals={
                     'login':partner_ids_obj.email,
                     'password':partner_ids_obj.email,
                     #'new_password':row[4],
                     'active':True,
                     'partner_id':partner_ids_obj.id,
                     'group_id':1,
                }# skip empty rows and rows where the translation field (=last fiefd) is empty
                if not user_ids:
             # lets create the language with locale information
                                user_ids_id=user_obj.create(cr, uid, vals, context=context)
                else:
                                user_ids_id=user_ids[0]
                                user_obj.write(cr, uid, user_ids[0], vals, context)  
            view_ref = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'view_users_form')
            view_id = view_ref and view_ref[1] or False,
            return {
                'type': 'ir.actions.act_window',
                'name': _('Utenti'),
                'res_model': 'res.users',
                'res_id': user_ids_id,
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': view_id,
                'target': 'current',
                'nodestroy': True,
            }


class account_invoice(osv.Model):
    _inherit = 'account.invoice'
    def confirm_paid(self, cr, uid, ids, context=None):
        sale_order_obj = self.pool.get('sale.order')
        res = super(account_invoice, self).confirm_paid(cr, uid, ids, context=context)
        so_ids = sale_order_obj.search(cr, uid, [('invoice_ids', 'in', ids)], context=context)
        for so_id in so_ids:
            sale_order_obj.message_post(cr, uid, so_id, body=_("Invoice paid"), context=context)
        return res

    def unlink(self, cr, uid, ids, context=None):
        """ Overwrite unlink method of account invoice to send a trigger to the sale workflow upon invoice deletion """
        invoice_ids = self.search(cr, uid, [('id', 'in', ids), ('state', 'in', ['draft', 'cancel'])], context=context)
        #if we can't cancel all invoices, do nothing
        if len(invoice_ids) == len(ids):
            #Cancel invoice(s) first before deleting them so that if any sale order is associated with them
            #it will trigger the workflow to put the sale order in an 'invoice exception' state
            for id in ids:
                workflow.trg_validate(uid, 'account.invoice', id, 'invoice_cancel', cr)
        return super(account_invoice, self).unlink(cr, uid, ids, context=context)

    

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
   
    def reconcile_invoice_2(self, cr, uid, ids,context=None):
        """ Simple method to reconcile the invoice with the payment
        generated on the sale order """
        if not isinstance(ids, (list, tuple)):
            ids = [ids]
    
        for invoice in self.browse(cr, uid, ids, context=context):
            pay_account_id=235
            pay_journal_id=2
            writeoff_acc_id=235
            writeoff_journal_id=2
            name=invoice.number
            writeoff_period_id=invoice.period_id.id
            self.pay_and_reconcile(cr, uid, ids, invoice['amount_total'] , pay_account_id, invoice.period_id.id, pay_journal_id, writeoff_acc_id, writeoff_period_id, writeoff_journal_id, context, name)
class crm_claim(osv.Model):
    _inherit = 'crm.claim'
    def create(self, cr, uid, vals, context=None):
        return super(crm_claim, self).create(cr, SUPERUSER_ID, vals, context=context)
class mail_compose_message(osv.TransientModel):
    """ Generic message composition wizard. You may inherit from this wizard
        at model and view levels to provide specific features.

        The behavior of the wizard depends on the composition_mode field:
        - 'comment': post on a record. The wizard is pre-populated via ``get_record_data``
        - 'mass_mail': wizard in mass mailing mode where the mail details can
            contain template placeholders that will be merged with actual data
            before being sent to each recipient.
    """
    _inherit = 'mail.compose.message'
    _columns = {
        'no_auto_thread': fields.boolean('No threading for answers',
            help='Answers do not go in the original document\' discussion thread. This has an impact on the generated message-id.'),

    }

    def get_mail_values(self, cr, uid, wizard, res_ids, context=None):
        "17-10-2014 rocco inserita la  mail_server"
        """Generate the values that will be used by send_mail to create mail_messages
        or mail_mails. """
        """inizio 17-10-2014 Rocco Cesetti"""
        ir_mail_server_obj = self.pool.get('ir.mail_server')
        ir_mail_server_ids = ir_mail_server_obj.search(cr, uid, [('name','=','NL-1')], context=context)
        if ir_mail_server_ids:
            ir_mail_server_id=ir_mail_server_ids[0]
        else:
            ir_mail_server_id=4
        """fine 17-10-2014 rocco cesetti"""    
        results = dict.fromkeys(res_ids, False)
        rendered_values, default_recipients = {}, {}
        mass_mail_mode = wizard.composition_mode == 'mass_mail'

        # render all template-based value at once
        if mass_mail_mode and wizard.model:
            rendered_values = self.render_message_batch(cr, uid, wizard, res_ids, context=context)
        # compute alias-based reply-to in batch
        reply_to_value = dict.fromkeys(res_ids, None)
        if mass_mail_mode and not wizard.no_auto_thread:
            reply_to_value = self.pool['mail.thread'].message_get_reply_to(cr, uid, res_ids, default=wizard.email_from, context=dict(context, thread_model=wizard.model))

        for res_id in res_ids:
            # static wizard (mail.message) values
            mail_values = {
                'subject': wizard.subject,
                'body': wizard.body,
                'parent_id': wizard.parent_id and wizard.parent_id.id,
                'partner_ids': [partner.id for partner in wizard.partner_ids],
                'attachment_ids': [attach.id for attach in wizard.attachment_ids],
                'author_id': wizard.author_id.id,
                'email_from': wizard.email_from,
                'record_name': wizard.record_name,
                'no_auto_thread': wizard.no_auto_thread,
                'mail_server_id':ir_mail_server_id,#17-10-2014 Rocco Cesetti   

            }
            # mass mailing: rendering override wizard static values
            if mass_mail_mode and wizard.model:
                # always keep a copy, reset record name (avoid browsing records)
                mail_values.update(notification=True, model=wizard.model, res_id=res_id, record_name=False)
                # auto deletion of mail_mail
                if 'mail_auto_delete' in context:
                    mail_values['auto_delete'] = context.get('mail_auto_delete')
                # rendered values using template
                email_dict = rendered_values[res_id]
                mail_values['partner_ids'] += email_dict.pop('partner_ids', [])
                mail_values.update(email_dict)
                if not wizard.no_auto_thread:
                    mail_values.pop('reply_to')
                    if reply_to_value.get(res_id):
                        mail_values['reply_to'] = reply_to_value[res_id]
                if wizard.no_auto_thread and not mail_values.get('reply_to'):
                    mail_values['reply_to'] = mail_values['email_from']
                # mail_mail values: body -> body_html, partner_ids -> recipient_ids
                mail_values['body_html'] = mail_values.get('body', '')
                mail_values['recipient_ids'] = [(4, id) for id in mail_values.pop('partner_ids', [])]

                # process attachments: should not be encoded before being processed by message_post / mail_mail create
                mail_values['attachments'] = [(name, base64.b64decode(enc_cont)) for name, enc_cont in email_dict.pop('attachments', list())]
                attachment_ids = []
                for attach_id in mail_values.pop('attachment_ids'):
                    new_attach_id = self.pool.get('ir.attachment').copy(cr, uid, attach_id, {'res_model': self._name, 'res_id': wizard.id}, context=context)
                    attachment_ids.append(new_attach_id)
                mail_values['attachment_ids'] = self.pool['mail.thread']._message_preprocess_attachments(
                    cr, uid, mail_values.pop('attachments', []),
                    attachment_ids, 'mail.message', 0, context=context)
            results[res_id] = mail_values
        return results

