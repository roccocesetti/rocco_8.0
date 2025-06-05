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
from openerp import api, _


from openerp import tools
from openerp.osv import osv, fields, expression
from lxml import etree
import openerp.pooler as pooler
import openerp.sql_db as sql_db
from datetime import datetime, timedelta, date
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
from openerp import netsvc
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp import models
import time
from openerp.tools.translate import _
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
from contextlib import contextmanager
import logging
_logger = logging.getLogger(__name__)

@contextmanager
def commit(cr):
    """
    Commit the cursor after the ``yield``, or rollback it if an
    exception occurs.

    Warning: using this method, the exceptions are logged then discarded.
    """
    try:
        yield
    except Exception:
        cr.rollback()
        _logger.exception('Error during an automatic workflow action.')
    else:
        cr.commit()

class invoice_picking_webtex(osv.osv_memory):
    _name = 'account.invoice.acq.picking'
    _description = 'aggancia  a fattura'
    _columns = {
        'name':fields.char('Name', size=64, required=False, readonly=False),
        'partner_id':fields.many2one('res.partner', string='Fornitore', 
         domain=[('supplier','=',True)] ),                           
        'invoice_id':fields.many2one('account.invoice', string='Fattura di acquisto', 
         domain=[('type','ilike','in_invoice')]),
    }
    _defaults = {
    'name':'update_picking'  + time.strftime('%Y-%m-%d') ,
    }
    @api.multi
    def close_invoice_picking(self):
            active_ids=self.env.context.get('active_ids', [])#
            invoice_obj = self.env['account.invoice']
            purchase_obj = self.env['purchase.order']
            picking_obj = self.env['stock.picking']
            print 'self.invoice_id.id',self.invoice_id.id
            for picking_id_obj in  picking_obj.browse(active_ids):
                        picking_id_obj.write({'invoice_id':self.invoice_id.id,
                                              'invoice_state':'invoiced',
                                              'invoice_ids':[(3,self.invoice_id.id,_)]
                                              })
                        if self.invoice_id.origin:
                            origin=self.invoice_id.origin
                        else:
                            origin=''
                        self.invoice_id.write({'origin':origin+'-'+picking_id_obj.name})
                        if picking_id_obj.origin:
                            purchase_ids=purchase_obj.search([('name','=',picking_id_obj.origin)])
                            if purchase_ids:
                                purchase_ids[0].write({'invoice_ids':[(3,self.invoice_id.id,_)]})
                           
            return True
        
            
            
            
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
        
            
            
            
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
    @api.multi
    def form_close_pick_invoice(self):
        view_ref = self.env['ir.model.data'].get_object_reference('prof_webtex', 'view_account_invoice_acq_picking_webtex')
        view_id = view_ref and view_ref[1] or False,
        my_id=self.create({})
        context=self.env.context.copy()
        context.update({'search_default_supplier':1,
                        'search_default_partner_id': self.partner_id.id or None,
                        'default_partner_id':self.partner_id.id or None, 
                        'form_view_ref':'account.invoice_supplier_form', 
                        'tree_view_ref':'prof_webtex.invoice_tree_sel_purchase',
                        'search_view_ref':'account.view_account_invoice_filter', 
                        'default_type': 'in_invoice'})
              
        print 'self.env.context',self.env.context
        print 'my_id',my_id.id
        return {'name':_("acquisisci fattura"),
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'account.invoice.acq.picking',
                'res_id': my_id.id,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new',
                'domain': self.env.context,                                 
                'context': self.env.context,                                 
            }


class invoice_webtex(osv.osv_memory):
    _name = 'account.invoice.conversion'
    _description = 'Conversione da corrispettivo a fattura'

    def _default_journal(self, cr, uid,context=None):
        company_id = context.get('company_id', self.pool.get('res.users').browse(cr,uid,uid,context=context).company_id.id)
        domain = [
            ('type', '=', 'sale'),
            ('company_id', '=', company_id),
        ]
        res= self.pool.get('account.journal').search(cr,uid,domain,order='name DESC', limit=1)
        if res:
            return res[0]
        else:
            return None
    _columns = {
        'name':fields.char('Name', size=64, required=False, readonly=False),
        'journal_id':fields.many2one('account.journal', 'Sezionale di fatturazione', required=True,
         domain=[('type','ilike','sale')]                            
            
),
        'fiscal_position_id':fields.many2one('account.fiscal.position', 'Posizione Fiscale', required=False,
                         ),
                 
        'invoice_date': fields.date('Data di rifatturazione'), 
        'yes_invoice_date': fields.boolean('Forza Data di rifatturazione'), 
    }
    _defaults = {
    'name':'update_conversion'  + time.strftime('%Y-%m-%d') ,
    'invoice_date': lambda *a: time.strftime('%Y-%m-%d'),  
    'journal_id':_default_journal,
    'yes_invoice_date':True
    }
    @api.multi
    def chg_invoice(self):
            ir_property_obj=self.env['ir.property']
            active_ids=self.env.context.get('active_ids', [])#
            period_obj=self.env['account.period']
            if self.invoice_date:
                invoice_date=datetime.strptime(self.invoice_date, '%Y-%m-%d')
            else:
                invoice_date=datetime.today()
            invoice_obj = self.env['account.invoice']
            """ rimuovo la riconciliazione e cambio i conti e le aliquote"""
            reconcile_ids=[]
            par_reconcile_ids=[]
            for invoice_id_obj in  invoice_obj.browse(active_ids):
                sv_x_to_company_journal_id=None
                for payment_id_obj in invoice_id_obj.payment_ids:
                    if payment_id_obj.company_id.id != self.journal_id.company_id.id:
                        for x_to_company_journal_id in payment_id_obj.journal_id.x_to_company_journal_id:
                            if x_to_company_journal_id.company_id.id==self.journal_id.company_id.id:
                                    sv_x_to_company_journal_id=x_to_company_journal_id
                                    break
                            else:
                                    sv_x_to_company_journal_id=payment_id_obj.journal_id
                                    break
                                
                    else:
                        sv_x_to_company_journal_id=payment_id_obj.journal_id
                            
                reconcile_ids=[]
                par_reconcile_ids=[]
                for move_line_id_obj in invoice_id_obj.move_id.line_id:
                    reconcile_ids.append(move_line_id_obj.reconcile_id)
                    par_reconcile_ids.append(move_line_id_obj.reconcile_partial_id.id)
                    #move_line_id_obj.write({'reconcile_id':None,'reconcile_partial_id':None})
                """Cancello la fattura dalla contabilità """    
                for reconcile_id in reconcile_ids:
                    reconcile_id.unlink()
                invoice_id_obj.signal_workflow('invoice_cancel')        
                invoice_id_obj.action_cancel_draft()
                period_ids_obj=period_obj.search([('id','=',invoice_id_obj.period_id.id)])
                period_comp_2_ids_obj=period_obj.search([('name','=',period_ids_obj[0].name),('company_id','=',self.journal_id.company_id.id)])
                if self.fiscal_position_id:
                    fpos = self.env['account.fiscal.position'].browse(self.fiscal_position_id.id)
                else:    
                    fpos = self.env['account.fiscal.position'].browse(invoice_id_obj.fiscal_position.id)
                
                account_id = fpos.map_account(invoice_id_obj.account_id)
                """ imposto cambio ditta cliente """
                if invoice_id_obj.partner_id.company_id.id!=self.journal_id.company_id.id:
                    invoice_id_obj.partner_id.write({'company_id':self.journal_id.company_id.id,
                                      'property_account_position': self.fiscal_position_id.id if self.fiscal_position_id else invoice_id_obj.fiscal_position.id       
                                                     })
                    if invoice_id_obj.partner_id.parent_id:
                        invoice_id_obj.partner_id.parent_id.write({'company_id':self.journal_id.company_id.id,
                                      'property_account_position': self.fiscal_position_id.id if self.fiscal_position_id else invoice_id_obj.fiscal_position.id       
                                                                   })
                """ imposto la fattura """
                invoice_vals={'internal_number':None,
                                      'number':None,
                                      'state':'draft',
                                      'journal_id':self.journal_id.id,
                                      'company_id':self.journal_id.company_id.id,
                                      'account_id':account_id.id,
                                      'period_id':period_comp_2_ids_obj[0].id,
                                      'fiscal_position': self.fiscal_position_id.id if self.fiscal_position_id else invoice_id_obj.fiscal_position.id       
                                      }
                if self.yes_invoice_date:
                    invoice_vals.update({'date_invoice':invoice_date})
                invoice_id_obj.write(invoice_vals)
                for invoice_line in invoice_id_obj.invoice_line:
                    account_id = fpos.map_account(invoice_line.account_id)
                    fp_taxes = fpos.map_tax(invoice_line.invoice_line_tax_id)
                    invoice_line.write({'account_id':account_id.id,
                                      'company_id':self.journal_id.company_id.id,
                                      'invoice_line_tax_id': [(6, 0 ,[ x for x in fp_taxes.ids] ) ],
                         #'taxes_id': [(6, 0, [x.id for x in tax_obj.browse(cr,uid,tax_ids,context=context)])],

                                        })
                invoice_id_obj.button_compute(True)
                """valido la fattura """
                invoice_id_obj.signal_workflow('invoice_open')##     #   
                if sv_x_to_company_journal_id:
                        """ pago la fattura """
                        pay_amount=invoice_id_obj.amount_total
                        pay_account_id=sv_x_to_company_journal_id.default_credit_account_id
                        period_id=period_comp_2_ids_obj[0]
                        pay_journal_id=sv_x_to_company_journal_id
                                        
                        writeoff_acc_id=sv_x_to_company_journal_id.default_credit_account_id
                        writeoff_period_id=period_comp_2_ids_obj[0]
                        writeoff_journal_id=sv_x_to_company_journal_id
                        print 'pay_account_id',pay_account_id.name,pay_account_id.company_id.name
                        print 'period_id',period_id.name,period_id.company_id.name
                        print 'writeoff_acc_id',writeoff_acc_id.name,writeoff_acc_id.company_id.name
                        print 'writeoff_period_id',writeoff_period_id.name,writeoff_period_id.company_id.name#
                        ir_property_ids_obj=ir_property_obj.search([('name','=','property_account_receivable'),('res_id','=','res.partenr,' + str(invoice_id_obj.partner_id.id))])
                        if ir_property_ids_obj:
                            for ir_property_id_obj in ir_property_ids_obj:
                                ir_property_id_obj.write({
                                                          'name':'property_account_receivable',
                                                          'value_reference':'account.account,' + str(fpos.map_account(invoice_line.partner_id.property_account_receivable).id),
                                                          'company_id':self.journal_id.company_id.id
                                                          }
                                                         )
                        else:
                            ir_property_ids_obj.create({
                                                          'res_id':'res.partenr,' + str(invoice_id_obj.partner_id.id),
                                                          'name':'property_account_receivable',
                                                          'value_reference':'account.account,' + str(fpos.map_account(invoice_line.partner_id.property_account_receivable).id),                                                        
                                                          'company_id':self.journal_id.company_id.id,
                                                          'fields_id':3081
                                                        })
                        invoice_id_obj.partner_id.write({
                                                        'property_account_receivable':fpos.map_account(invoice_line.partner_id.property_account_receivable).id,
                                                        'company_id':sv_x_to_company_journal_id.company_id.id,
                                                        'property_account_position':self.fiscal_position_id.id if self.fiscal_position_id else invoice_id_obj.fiscal_position.id
                                                        }
                                                        )
                        if invoice_id_obj.partner_id.parent_id:
                            ir_property_ids_obj=ir_property_obj.search([('name','=','property_account_receivable'),('res_id','=','res.partenr,' + str(invoice_id_obj.partner_id.parent_id.id))])
                            if ir_property_ids_obj:
                                for ir_property_id_obj in ir_property_ids_obj:
                                    ir_property_id_obj.write({
                                                              'name':'property_account_receivable',
                                                              'value_reference':'account.account' + str(fpos.map_account(invoice_line.partner_id.parent_id.property_account_receivable).id),
                                                              'company_id':self.journal_id.company_id.id
                                                              }
                                                             )
                            else:
                                ir_property_ids_obj.create({
                                                              'res_id':'res.partenr,' + str(invoice_id_obj.partner_id.parent_id.id),
                                                              'name':'property_account_receivable',
                                                              'value_reference':'account.account' + str(fpos.map_account(invoice_line.partner_id.parent_id.property_account_receivable).id),                                                        
                                                              'company_id':self.journal_id.company_id.id,
                                                              'fields_id':3081
                                                            })
                            invoice_id_obj.partner_id.parent_id.write({
                                                            'property_account_receivable':fpos.map_account(invoice_line.partner_id.property_account_receivable).id,
                                                            'company_id':sv_x_to_company_journal_id.company_id.id,
                                                            'property_account_position':self.fiscal_position_id.id if self.fiscal_position_id else invoice_id_obj.fiscal_position.id
                                                            }
                                                            )
                        context=self.env.context.copy() 
                        if context is None:
                            context={}
                        if invoice_id_obj.company_id.parent_id:
                            if invoice_id_obj.currency_id.id!=invoice_id_obj.company_id.parent_id.currency_id.id:
                                context.update({'currency':invoice_id_obj.currency_id,
                                                'amount_currency':invoice_id_obj.amount_total,})   
                        invoice_id_obj.with_context(context).pay_and_reconcile(pay_amount, pay_account_id.id, period_id.id, pay_journal_id.id,
                                                  writeoff_acc_id.id, writeoff_period_id.id, writeoff_journal_id.id, '')
                invoice_id_obj.confirm_paid
            return True
        
            
            
            
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
        
            
            
            
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
    @api.multi
    def open_chg_invoice(self):
        company_id = self.env.context.get('company_id', self.env['res.users'].browse(self.env.uid).company_id.id)
        domain = [
            ('type', '=', 'sale'),
            ('company_id', '=', company_id),
        ]
        journal_ids= self.env['account.journal'].search(domain)
        
        view_ref = self.env['ir.model.data'].get_object_reference('prof_webtex', 'view_account_invoice_conversion_webtex')
        view_id = view_ref and view_ref[1] or False,
        my_id=self.create({})
        print 'self.env.context',self.env.context
        print 'my_id',my_id.id
        return {'name':_("Converti Corrispettivo"),
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'account.invoice.conversion',
                'res_id': my_id.id,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new',
                'domain': self.env.context,                                 
                'context': self.env.context,                                 
            }
class invoice_close_webtex(osv.osv_memory):
    _name = 'account.invoice.close'
    _description = 'Chiudi la fattura'

    def _default_journal(self, cr, uid,context=None):
        company_id = context.get('company_id', self.pool.get('res.users').browse(cr,uid,uid,context=context).company_id.id)
        domain = [
            ('type', 'in', ('cash','bank',)),
            ('company_id', '=', company_id),
        ]
        res= self.pool.get('account.journal').search(cr,uid,domain,order='name DESC', limit=1)
        if res:
            return res[0]
        else:
            return None
    _columns = {
        'name':fields.char('Name', size=64, required=False, readonly=False),
        'journal_id':fields.many2one('account.journal', 'Sezionale di pagamento', required=True,
         domain=[('type','in',('cash','bank',))]                            
            
),
        'fiscal_position_id':fields.many2one('account.fiscal.position', 'Posizione Fiscale', required=False,
                         ),
                 
        'invoice_pag': fields.date('Data di Chiusura'), 
    }
    _defaults = {
    'name':'update_close'  + time.strftime('%Y-%m-%d') ,
    'invoice_pag': lambda *a: time.strftime('%Y-%m-%d'),  
    'journal_id':_default_journal
    }

    @api.multi
    def open_close_invoice(self):
        company_id = self.env.context.get('company_id', self.env['res.users'].browse(self.env.uid).company_id.id)
        domain = [
            ('type', '=', 'sale'),
            ('company_id', '=', company_id),
        ]
        journal_ids= self.env['account.journal'].search(domain)
        
        view_ref = self.env['ir.model.data'].get_object_reference('prof_webtex', 'view_account_invoice_close_webtex')
        view_id = view_ref and view_ref[1] or False,
        my_id=self.create({})
        print 'self.env.context',self.env.context
        print 'my_id',my_id.id
        return {'name':_("Chiudi Corrispettivo"),
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'account.invoice.close',
                'res_id': my_id.id,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new',
                'domain': self.env.context,                                 
                'context': self.env.context,                                 
            }

    @api.multi
    def close_invoice(self):
           return  self.close_invoice_cron(corr_journal_id=None,pag_journal_id=None,da_date_corr=None,a_date_corr=None,date_pag=None)
    
    def close_invoice_v7(self,cr,uid,ids=None,corr_journal_id=None,pag_journal_id=None,da_date_corr=None,a_date_corr=None,date_pag=None,context=None):
           
           return  self.close_invoice_cron(cr,uid,ids=ids,corr_journal_id=corr_journal_id,pag_journal_id=pag_journal_id,da_date_corr=da_date_corr,a_date_corr=a_date_corr,date_pag=date_pag,context=context)
    @api.multi
    def close_invoice_cron(self,corr_journal_id=None,pag_journal_id=None,da_date_corr=None,a_date_corr=None,date_pag=None):
            active_ids=self.env.context.get('active_ids', [])#
            print 'close_invoice_cron,active_ids',active_ids

            period_obj=self.env['account.period']
            invoice_obj = self.env['account.invoice']
            print 'close_invoice,corr_journal_id',corr_journal_id
            print 'close_invoice,pag_journal_id',pag_journal_id
            print 'close_invoice,da_date_corr',da_date_corr
            print 'close_invoice,a_date_corr',a_date_corr
            print 'close_invoice,date_pag',date_pag
            ''' data pagamento '''
            if date_pag:
                pag_date=date_pag
            else:
                if self.invoice_pag:
                    pag_date=datetime.strptime(self.invoice_pag, '%Y-%m-%d')
                else:
                    pag_date=datetime.strptime(str(datetime.today().date()), '%Y-%m-%d')
            ''' data selezione corrispettivo '''
            if a_date_corr:
                a_date_corr=a_date_corr
            else:
                a_date_corr=datetime.strptime(str(datetime.today().date()), '%Y-%m-%d')
            if da_date_corr:
                da_date_corr=da_date_corr
            else:
                da_date_corr=datetime.strptime(str(datetime.today().date()), '%Y-%m-%d')

            'sezionale corrispoettivo da pagare'
            if corr_journal_id:
                corr_journal_id_obj = self.env['account.journal'].search([('id','=',corr_journal_id)])
            'fattura de chiudere'
            
            if active_ids:
                active_ids=active_ids
                invoice_ids_obj=invoice_obj.browse(active_ids)
            else:
                invoice_ids_obj=invoice_obj.search([('journal_id','=',corr_journal_id),('state','=','open'),('date_invoice','>=',da_date_corr),('date_invoice','<=',a_date_corr)])    
                
            'sezionale per pagamento'
            if pag_journal_id:
                pag_journal_id=pag_journal_id
            else:
                pag_journal_id=self.journal_id.id
            
            pag_journal_id_obj = self.env['account.journal'].browse(pag_journal_id)
            context = self.env.context.copy()
            context['date_p'] = pag_date
            for invoice_id_obj in  invoice_ids_obj:##
                period_ids_obj=period_obj.search([('id','=',invoice_id_obj.period_id.id)])
                if not period_ids_obj:
                    period_ids_obj=period_obj.search([('date_start','<=',pag_date),('date_stop','>=',pag_date),('company_id', '=', invoice_id_obj.company_id.id)])
                    
                if self.fiscal_position_id:
                    fpos = self.env['account.fiscal.position'].browse(self.fiscal_position_id.id)
                else:    
                    fpos = self.env['account.fiscal.position'].browse(invoice_id_obj.fiscal_position.id)
                
                account_id = fpos.map_account(invoice_id_obj.account_id)
                if pag_journal_id_obj:
                        """ pago la fattura """
                        pay_amount=invoice_id_obj.amount_total
                        pay_account_id=pag_journal_id_obj.default_credit_account_id
                        if  period_ids_obj:
                            period_id=period_ids_obj[0]
                        pay_journal_id=pag_journal_id_obj
                        writeoff_acc_id=pag_journal_id_obj.default_credit_account_id
                        writeoff_period_id=period_id
                        writeoff_journal_id=pag_journal_id_obj
                        print 'pay_account_id',pay_account_id.name,pay_account_id.company_id.name
                        print 'period_id',period_id.name,period_id.company_id.name
                        print 'writeoff_acc_id',writeoff_acc_id.name,writeoff_acc_id.company_id.name
                        print 'writeoff_period_id',writeoff_period_id.name,writeoff_period_id.company_id.name#
                        if context is None:
                            context={}
                        if invoice_id_obj.company_id.parent_id:
                            if invoice_id_obj.currency_id.id!=invoice_id_obj.company_id.parent_id.currency_id.id:
                                context.update({'currency':invoice_id_obj.currency_id,
                                                'amount_currency':invoice_id_obj.amount_total,})   
                        invoice_id_obj.with_context(context)     
                        invoice_id_obj.with_context(context).pay_and_reconcile(pay_amount, pay_account_id.id, period_id.id, pay_journal_id.id,
                                                  writeoff_acc_id.id, writeoff_period_id.id, writeoff_journal_id.id, '')
                invoice_id_obj.confirm_paid
            return True

    @api.multi
    def open_close_invoice_voucher(self):
        company_id = self.env.context.get('company_id', self.env['res.users'].browse(self.env.uid).company_id.id)
        domain = [
            ('type', '=', 'sale'),
            ('company_id', '=', company_id),
        ]
        journal_ids= self.env['account.journal'].search(domain)
        
        view_ref = self.env['ir.model.data'].get_object_reference('prof_webtex', 'view_account_invoice_close_voucher_webtex')
        view_id = view_ref and view_ref[1] or False,
        my_id=self.create({})
        print 'self.env.context',self.env.context
        print 'my_id',my_id.id
        return {'name':_("Ripristina  pagamenti"),
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'account.invoice.close',
                'res_id': my_id.id,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new',
                'domain': self.env.context,                                 
                'context': self.env.context,                                 
            }

    @api.multi
    def close_invoice_voucher(self):
           return  self.close_invoice_from_vaucher_cron(corr_journal_id=None,pag_journal_id=None,da_date_corr=None,a_date_corr=None,date_pag=None)

        
    def close_invoice_from_voucher_v7(self,cr,uid,ids=None,corr_journal_id=None,pag_journal_id=None,da_date_corr=None,a_date_corr=None,date_pag=None,context=None):
           
           return  self.close_invoice_from_vaucher_cron(cr,uid,ids=ids,corr_journal_id=corr_journal_id,pag_journal_id=pag_journal_id,da_date_corr=da_date_corr,a_date_corr=a_date_corr,date_pag=date_pag,context=context)

    @api.multi
    def close_invoice_from_vaucher_cron(self,corr_journal_id=None,pag_journal_id=None,da_date_corr=None,a_date_corr=None,date_pag=None):
            active_ids=self.env.context.get('active_ids', [])#
            print 'close_invoice_cron,active_ids',active_ids###

            period_obj=self.env['account.period']
            move_obj = self.env['account.move']
            move_line_obj = self.env['account.move.line']
            invoice_obj = self.env['account.invoice']
            vaucher_obj = self.env['account.voucher']
            reconcilie_obj = self.env['account.move.reconcile']
            print 'close_invoice,corr_journal_id',corr_journal_id
            print 'close_invoice,pag_journal_id',pag_journal_id
            print 'close_invoice,da_date_corr',da_date_corr
            print 'close_invoice,a_date_corr',a_date_corr
            print 'close_invoice,date_pag',date_pag
            ''' data pagamento '''
            if date_pag:
                pag_date=date_pag
            else:
                if self.invoice_pag:
                    pag_date=datetime.strptime(self.invoice_pag, '%Y-%m-%d')
                else:
                    pag_date=datetime.strptime(str(datetime.today().date()), '%Y-%m-%d')
            ''' data selezione corrispettivo '''
            if a_date_corr:
                a_date_corr=a_date_corr
            else:
                a_date_corr=datetime.strptime(str(datetime.today().date()), '%Y-%m-%d')
            if da_date_corr:
                da_date_corr=da_date_corr
            else:
                da_date_corr=datetime.strptime(str(datetime.today().date()), '%Y-%m-%d')

            'sezionale corrispoettivo da pagare'
            if corr_journal_id:
                corr_journal_id_obj = self.env['account.journal'].search([('id','=',corr_journal_id)])
            'fattura de chiudere'
            
            if active_ids:
                active_ids=active_ids
                invoice_ids_obj=invoice_obj.browse(active_ids)
            else:
                invoice_ids_obj=invoice_obj.search([('state','=','open'),('date_invoice','>=',da_date_corr),('date_invoice','<=',a_date_corr)])    
                
            'sezionale per pagamento'
            if pag_journal_id:
                pag_journal_id=pag_journal_id
            else:
                pag_journal_id=self.journal_id.id
            
            pag_journal_id_obj = self.env['account.journal'].browse(pag_journal_id)
            context = self.env.context.copy()
            context['date_p'] = pag_date
            for invoice_id_obj in  invoice_ids_obj:##
                
                period_ids_obj=period_obj.search([('id','=',invoice_id_obj.period_id.id)])
                if self.fiscal_position_id:
                    fpos = self.env['account.fiscal.position'].browse(self.fiscal_position_id.id)
                else:    
                    fpos = self.env['account.fiscal.position'].browse(invoice_id_obj.fiscal_position.id)
                
                account_id = fpos.map_account(invoice_id_obj.account_id)
                if invoice_id_obj.partner_id.parent_id:
                    partner_id=invoice_id_obj.partner_id.parent_id
                else:
                    partner_id=invoice_id_obj.partner_id
                    
                for voucher_id_obj in self.env['account.voucher'].search([('partner_id','=',partner_id.id),('partner_id','=',partner_id.id)]):
                    if voucher_id_obj.amount != invoice_id_obj.amount_total:
                        continue
                    if voucher_id_obj.reference:
                        if voucher_id_obj.reference.find(invoice_id_obj.number)<0:
                            continue
                    if invoice_id_obj.type in ('out_invoice','in_invoice'):###
                            if voucher_id_obj.move_ids and (voucher_id_obj.line_cr_ids or voucher_id_obj.line_dr_ids):
                                continue
                            voucher_id_obj.cancel_voucher()
                            voucher_id_obj.action_cancel_draft()
                            try:
                                voucher_id_obj.proforma_voucher()
                                voucher_id_obj.write({'narration':'##RIPRISTINATO##NONRICONCILIATO'})
                                invoice_id_obj.write({'comment':'##RIPRISTINATO##NONRICONCILIATO'})
                                continue
                            except:
                                pass  
                                voucher_id_obj.write({'narration':'##NONRIPRISTINATO##RICONCILIATO'})
                                invoice_id_obj.write({'comment':'##NONRIPRISTINATO##RICONCILIATO'})
                            continue
                            
                            
                            if voucher_id_obj.journal_id:
                                    pag_journal_id_obj=voucher_id_obj.journal_id
                            
                            if voucher_id_obj.date:
                                context['date_p'] = voucher_id_obj.date
    
                            if pag_journal_id_obj:
                                        """ pago la fattura """
                                        pay_amount=invoice_id_obj.amount_total
                                        pay_account_id=pag_journal_id_obj.default_credit_account_id
                                        period_id=period_ids_obj[0]
                                        pay_journal_id=pag_journal_id_obj
                                        writeoff_acc_id=pag_journal_id_obj.default_credit_account_id
                                        writeoff_period_id=period_id
                                        writeoff_journal_id=pag_journal_id_obj
                                        print 'pay_account_id',pay_account_id.name,pay_account_id.company_id.name
                                        print 'period_id',period_id.name,period_id.company_id.name
                                        print 'writeoff_acc_id',writeoff_acc_id.name,writeoff_acc_id.company_id.name
                                        print 'writeoff_period_id',writeoff_period_id.name,writeoff_period_id.company_id.name#
                                        if context is None:
                                            context={}
                                        if invoice_id_obj.company_id.parent_id:
                                            if invoice_id_obj.currency_id.id!=invoice_id_obj.company_id.parent_id.currency_id.id:
                                                context.update({'currency':invoice_id_obj.currency_id,
                                                                'amount_currency':invoice_id_obj.amount_total,})   
                                        invoice_id_obj.with_context(context)     
                                        invoice_id_obj.with_context(context).pay_and_reconcile(pay_amount, pay_account_id.id, period_id.id, pay_journal_id.id,
                                                                  writeoff_acc_id.id, writeoff_period_id.id, writeoff_journal_id.id, '')
                            voucher_id_obj.cancel_voucher()
                            voucher_id_obj.unlink()
                            """
                            for line_id_obj in voucher_id_obj.line_ids:
                                    line_id_obj.unlink()
                            del_account_moves=[]                                                                                       
                            for del_account_move_line_obj  in  voucher_id_obj.move_ids:
                                del_account_moves.append(del_account_move_line_obj)
                                del_account_move_line_obj.unlink()
                            for del_account_move_obj  in  del_account_moves:
                                if del_account_move_obj.line_id:
                                    continue
                                del_account_move_obj.unlink()
                            """    
 
                            invoice_id_obj.confirm_paid
            return True
            
            
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

class stock_return_picking(osv.osv_memory):
    _inherit = 'stock.return.picking' 
    @api.v8
    def create_returns_80(self):
        new_picking_id, pick_type_id = self._create_returns()
        return new_picking_id, pick_type_id
                                                        #Do not touch _name it must be same as _inherit
    @api.v7
    def create_returns_80(self, cr, uid, ids, context=None):
        recs = self.browse(cr, uid, [], context)
        ret_pick = recs.env['stock.return.picking'].browse(ids)
        return stock_return_picking.create_returns_80(recs, ret_pick)

    def default_get_webtex(self, cr, uid, fields, context=None):
        """
         To get default values for the object.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param fields: List of fields for which we want default values
         @param context: A standard dictionary
         @return: A dictionary with default values for all field in ``fields``
        """
        result1 = []
        if context is None:
            context = {}
        if context and context.get('active_ids', False):
            if len(context.get('active_ids')) > 1:
                return {}
        res = super(stock_return_picking, self).default_get(cr, uid, fields, context=context)
        record_id = context and context.get('active_id', False) or False
        uom_obj = self.pool.get('product.uom')
        pick_obj = self.pool.get('stock.picking')
        pick = pick_obj.browse(cr, uid, record_id, context=context)
        quant_obj = self.pool.get("stock.quant")
        chained_move_exist = False
        if pick:
            if pick.state != 'done':
                return {}

            for move in pick.move_lines:
                if move.move_dest_id:
                    chained_move_exist = True
                #Sum the quants in that location that can be returned (they should have been moved by the moves that were included in the returned picking)
                qty = 0
                quant_search = quant_obj.search(cr, uid, [('history_ids', 'in', move.id), ('qty', '>', 0.0), ('location_id', 'child_of', move.location_dest_id.id)], context=context)
                for quant in quant_obj.browse(cr, uid, quant_search, context=context):
                    if not quant.reservation_id or quant.reservation_id.origin_returned_move_id.id != move.id:
                        qty += quant.qty
                qty = uom_obj._compute_qty(cr, uid, move.product_id.uom_id.id, qty, move.product_uom.id)
                result1.append({'product_id': move.product_id.id, 'quantity': qty, 'move_id': move.id})

            if len(result1) == 0:
                return {}
            if 'product_return_moves' in fields:
                res.update({'product_return_moves': result1})
            if 'move_dest_exists' in fields:
                res.update({'move_dest_exists': chained_move_exist})
        return res
                                                         #_name = 'openerpmodel'    
class invoice_refound_webtex(osv.osv_memory):
    _name = 'account.invoice.refund'
    _description = 'Crea Note credito'

    def _default_journal(self, cr, uid,context=None):
        company_id = context.get('company_id', self.pool.get('res.users').browse(cr,uid,uid,context=context).company_id.id)
        domain = [
            ('type', 'in', ('sale_refund',)),
            ('company_id', '=', company_id),
        ]
        res= self.pool.get('account.journal').search(cr,uid,domain,order='name DESC', limit=1)
        if res:
            return res[0]
        else:
            return None
    _columns = {
        'name':fields.char('Name', size=64, required=False, readonly=False),
        'journal_id':fields.many2one('account.journal', 'Sezionale Note Credito', required=True,
         domain=[('type','in',('sale_refund',))]                            
            
),
                 
        'invoice_refund': fields.date('Data Nota Credito'), 
    }
    _defaults = {
    'name':'update_refund'  + time.strftime('%Y-%m-%d') ,
    'invoice_refund': lambda *a: time.strftime('%Y-%m-%d'),  
    'journal_id':_default_journal
    }

    @api.multi
    def open_refund(self):
        company_id = self.env.context.get('company_id', self.env['res.users'].browse(self.env.uid).company_id.id)
        domain = [
            ('type', '=', 'sale_refund'),
            ('company_id', '=', company_id),
        ]
        journal_ids= self.env['account.journal'].search(domain)
        
        view_ref = self.env['ir.model.data'].get_object_reference('prof_webtex', 'view_account_invoice_refund_webtex')
        view_id = view_ref and view_ref[1] or False,
        my_id=self.create({})
        print 'self.env.context',self.env.context
        print 'my_id',my_id.id
        return {'name':_("crea Notacredito"),
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'account.invoice.refund',
                'res_id': my_id.id,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new',
                'domain': self.env.context,                                 
                'context': self.env.context,                                 
            }

    @api.multi
    def create_refund(self):
           return  self.create_refund_cron(refund_journal_id=None,date_refund=None,tag_refund=None)
    
    def create_refund_v7(self,cr,uid,ids=None,refund_journal_id=None,date_refund=None,tag_refund=None,context=None):
           
           return  self.create_refund_cron(cr,uid,ids=ids,refund_journal_id=refund_journal_id,date_refund=date_refund,tag_refund=tag_refund,context=context)
    @api.multi
    def create_refund_cron(self,refund_journal_id=None,date_refund=None,tag_refund=None):
            active_ids=self.env.context.get('active_ids', [])#
            period_obj=self.env['account.period']
            invoice_obj = self.env['account.invoice']
            close_invoice_obj = self.env['account.invoice.close']
            sale_obj = self.env['sale.order']
            pick_obj = self.env['stock.picking']
            move_obj = self.env['stock.move']
            pick_ret_obj = self.env['stock.return.picking']
            pick_ret_line_obj = self.env['stock.return.picking.line']
            
            print 'refund_invoice,refund_journal_id',refund_journal_id
            print 'refund_invoice,date_pag',date_refund
            ''' data notacredito '''
            
            if date_refund:
                date_refund=date_refund
            else:
                if self.invoice_refund:
                    date_refund=datetime.strptime(self.invoice_refund, '%Y-%m-%d')
                else:
                    date_refund=datetime.strptime(str(datetime.today().date()), '%Y-%m-%d')
            
            date_refund=date_refund.date()
            print 'refund_invoice,date_refund',date_refund###
            
            if tag_refund is None:
                tag_refund='##notacredito'
            
            
            pick_ids=[]
            invoice_ids=[]
            refund_ids=[]
            if active_ids:####
                if self.env.context.get('active_model','account.invoice')=='account.invoice':
                    invoice_ids=active_ids
                    for invoice_id_obj in self.env['account.invoice'].browse(invoice_ids):
                        sale_id_obj=self.env['sale.order'].search([('name','=',invoice_id_obj.origin)])
                        if sale_id_obj.invoice_ids:
                            for pick_id_obj in sale_id_obj.picking_ids:
                                pick_ids.append(pick_id_obj)
                        sale_id_obj.write({'note':'nota__credito_creata','client_order_ref':'nota__credito_creata'})
                elif self.env.context.get('active_model','account.invoice')=='sale.order':
                    sale_ids=active_ids
                    for sale_id_obj in self.env['sale.order'].browse(sale_ids):
                        if sale_id_obj.invoice_ids:
                            invoice_ids_parz=[sale_id_obj.invoice_ids[0].id]
                            for invoice_id_parz in invoice_ids_parz:
                                invoice_ids.append(invoice_id_parz)
                            for pick_id_obj in sale_id_obj.picking_ids:
                                pick_ids.append(pick_id_obj)
                        sale_id_obj.write({'note':'nota__credito_creata','client_order_ref':'nota__credito_creata'})
                    
                else:
                    return False
            else:
                for sale_id_obj in self.env['sale.order'].search([('note','=',tag_refund)]):
                    if sale_id_obj.invoice_ids:
                        invoice_ids_parz=[sale_id_obj.invoice_ids[0].id]
                        for invoice_id_parz in invoice_ids_parz:
                            invoice_ids.append(invoice_id_parz)
                        for pick_id_obj in sale_id_obj.picking_ids:
                            pick_ids.append(pick_id_obj)
                    sale_id_obj.write({'note':'nota__credito_creata','client_order_ref':'nota__credito_creata'})
            'sezionale per nota_credito'
            if refund_journal_id:
                refund_journal_id=refund_journal_id
            else:
                if self.journal_id:
                    refund_journal_id=self.journal_id.id
                else:
                    refund_journal_id=None
            
            if refund_journal_id:
                refund_journal_id_obj = self.env['account.journal'].browse(refund_journal_id)
            else:
                refund_journal_id_obj=None
            context = self.env.context.copy()
            
            for invoice_id_obj in self.env['account.invoice'].browse(invoice_ids):
                    """ periodo """      
                    period_ids_obj=period_obj.search([('date_start','<=',date_refund),('date_stop','>=',date_refund),('company_id', '=', invoice_id_obj.company_id.id)])
                    """ sezionale nota credito """
                    if refund_journal_id_obj==None:
                        refund_journal_ids_obj=self.env['account.journal'].search([('type', 'in', ('sale_refund',)),
                    ('company_id', '=', invoice_id_obj.company_id.id),('corrispettivi','=',True)])
                        if refund_journal_ids_obj:
                            refund_journal_id_obj=refund_journal_ids_obj[0]
                        else:
                            refund_journal_ids_obj=self.env['account.journal'].search([('type', 'in', ('sale_refund',)),
                    ('company_id', '=', invoice_id_obj.company_id.id)])
                            
                        for refund_journal_id_obj_iter in refund_journal_ids_obj:
                            if refund_journal_id_obj_iter.name.find('SCARTO')>0:
                                continue
                            refund_journal_id_obj=refund_journal_id_obj_iter
                            if refund_journal_id_obj.company_id.id != invoice_id_obj.company_id.id:
                                for x_to_company_journal_id in refund_journal_id_obj.x_to_company_journal_id:
                                    if invoice_id_obj.company_id.id==x_to_company_journal_id.company_id.id:
                                        refund_journal_id_obj=x_to_company_journal_id
                                        break
                            break
                    else:
                        if refund_journal_id_obj.company_id.id != invoice_id_obj.company_id.id:
                            for x_to_company_journal_id in refund_journal_id_obj.x_to_company_journal_id:
                                if invoice_id_obj.company_id.id==x_to_company_journal_id.company_id.id:
                                    refund_journal_id_obj=x_to_company_journal_id
                                    break
                    print 'refund_invoice,period_id',period_ids_obj
                    print 'refund_invoice,journal_id',refund_journal_id_obj
                    
                    refund_ids_obj=invoice_id_obj.refund(date=date_refund, period_id=period_ids_obj[0].id, description="Note-credito-aut", journal_id=refund_journal_id_obj.id)
                    refund_ids=[]
                    for refund_id_obj in refund_ids_obj:
                        refund_id_obj.button_compute(True)
                        refund_ids.append(refund_id_obj.id)
                        #rocco 01/12/2018
                        #"""valido la fattura """
                        #with commit(self.env.cr):
                        #    refund_id_obj.signal_workflow('invoice_open')##
                         #pag_journal_id_obj=self.env['account.journal'].search([('type', 'in', ('bank',)),('company_id', '=', refund_id_obj.company_id.id)])
                    #context.update({'active_ids':refund_ids})
                    #print 'refund_invoice,active_ids',refund_ids
                    #if refund_ids_obj:
                    #    close_invoice_obj.with_context(context).close_invoice_cron(corr_journal_id=refund_ids_obj[0].journal_id.id,pag_journal_id=pag_journal_id_obj[0].id,da_date_corr=date_refund,a_date_corr=date_refund,date_pag=date_refund)
            for pick_id in pick_ids:
                        context.update({'active_ids':[pick_id.id],'active_id':pick_id.id})#xxx
                        res=pick_ret_obj.with_context(context).default_get_webtex(['product_return_moves','move_dest_exists'])
                        if res:
                            ret_id_obj=pick_ret_obj.with_context(context).create({'invoice_state':'none','move_dest_exists':res.get('move_dest_exists',False)})
                        else:
                            ret_id_obj=[]
                        print 'refund_invoice,pick_ret_obj',res
                        #for product_return_move in res.get('product_return_moves',[]):
                        #    product_return_move.update({'wizard_id':ret_id_obj.id})
                        #    pick_ret_line_obj.with_context(context).create(product_return_move)
                        pick_type_id = pick_id.picking_type_id.return_picking_type_id and pick_id.picking_type_id.return_picking_type_id.id or pick_id.picking_type_id.id
                        # creo picking
                        new_picking_ids_obj = pick_id.copy({
                            'move_lines': [],
                            'picking_type_id': pick_type_id,
                            'state': 'draft',
                            'origin': pick_id.name,
                        }, context=context)

                        for data_get in ret_id_obj.product_return_moves:
                            new_qty = data_get.quantity
                            move = data_get.move_id
                            if move:
                                if new_qty:
                                        move.copy({
                                            'product_id': data_get.product_id.id,
                                            'product_uom_qty': new_qty,
                                            'product_uos_qty': new_qty * move.product_uos_qty / move.product_uom_qty,
                                            'picking_id': new_picking_ids_obj.id,
                                            'state': 'draft',
                                            'location_id': move.location_dest_id.id,
                                            'location_dest_id': move.location_id.id,
                                            'picking_type_id': pick_type_id,
                                            'warehouse_id': pick_id.picking_type_id.warehouse_id.id,
                                            'origin_returned_move_id': move.id,
                                            'procure_method': 'make_to_stock',
                                            'restrict_lot_id': data_get.lot_id.id,
                                            'move_dest_id': move.move_dest_id or None,
                                        })
                        
                        #context.update({'active_ids':[pick_id],'active_id':pick_id})
                        #new_picking_id, pick_type_id=ret_id_obj.with_context(context).create_returns_80()

                        for new_picking_id_obj in new_picking_ids_obj:
                            new_picking_id_obj.action_confirm()
                            new_picking_id_obj.force_assign()
                            new_picking_id_obj.action_done()
                        """
                        try:
                                self.env.cr.commit()
                        except:
                                self.env.cr.rollback()
                        """
            for refund_id_obj in self.env['account.invoice'].browse(refund_ids):
                        """valido la fattura """
                        with commit(self.env.cr):
                            refund_id_obj.signal_workflow('invoice_open')##
                            pag_journal_id_obj=self.env['account.journal'].search([('type', 'in', ('bank',)),('company_id', '=', refund_id_obj.company_id.id)])
                            context.update({'active_ids':[refund_id_obj.id]})
                            close_invoice_obj.with_context(context).close_invoice_cron(corr_journal_id=refund_id_obj.journal_id.id,pag_journal_id=pag_journal_id_obj[0].id,da_date_corr=date_refund,a_date_corr=date_refund,date_pag=date_refund)
 
            return True
        
            
            
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
  
