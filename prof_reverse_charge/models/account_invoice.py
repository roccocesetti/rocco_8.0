# -*- coding: utf-8 -*-
# Copyright 2017 Davide Corio
# Copyright 2017 Alex Comba - Agile Business Group
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import api, fields, models
from openerp.exceptions import Warning as UserError
from openerp.tools.translate import _
from openerp.osv import osv,expression

class AccountRCType(models.Model):
    _inherit = 'account.rc.type'

    doc_type_id = fields.Many2one(
        'fatturapa.document_type',
        string='Tipo Documento fiscale autofattura tabella fattura pa',
        required=False,
        )
    fiscal_doc_type_id = fields.Many2one(
        'fiscal.document.type',
        string='Tipo Documento fiscale autofattura tabella fiscal',
        required=False,
        )


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    def rc_inv_vals(self, partner, account, rc_type, lines):
        comment = _(
            "Inversione Contabile(reverse charge) Auto Fattura.\n"
            "Fornitore: %s\n"
            "Riferimento fattura fornitore: %s\n"
            "Data: %s\n"
            "Riferimento: %s\n",
            ) % (
            self.partner_id.display_name, self.reference or self.supplier_invoice_number or '', self.date_invoice,
            rc_type.self_invoice_text or self.number
        )
        comment={}
        
        return {
            'doc_type':rc_type.doc_type_id.id,
            'fiscal_document_type_id':rc_type.fiscal_doc_type_id.id,
            'partner_id': partner.id,
            'type': 'out_invoice',
            'account_id': account.id,
            'journal_id': rc_type.journal_id.id,
            'invoice_line': lines,
            'date_invoice': self.registration_date,
            'registration_date': self.registration_date,
            'origin': self.number,
            'rc_purchase_invoice_id': self.id,
            'name': rc_type.self_invoice_text,
            'comment': comment,
            }
    def generate_self_invoice(self):
        rc_type = self.fiscal_position.rc_type_id
        if not rc_type.payment_journal_id.default_credit_account_id:
            raise UserError(
                _('There is no default credit account defined \n'
                  'on journal "%s".') % rc_type.payment_journal_id.name)
        if rc_type.partner_type == 'other':
            rc_partner = rc_type.partner_id
        else:
            rc_partner = self.partner_id
        rc_account = rc_partner.property_account_receivable

        rc_invoice_lines = []
        for line in self.invoice_line:
            if line.rc:
                rc_invoice_line = self.rc_inv_line_vals(line)
                line_tax = line.invoice_line_tax_id
                if not line_tax:
                    raise UserError(_(
                        "Invoice line\n%s\nis RC but has not tax") % line.name)
                tax_code_id = None
                for tax_mapping in rc_type.tax_ids:
                    if tax_mapping.purchase_tax_id == line_tax[0]:
                        tax_code_id = tax_mapping.sale_tax_id.id
                if not tax_code_id:
                    raise UserError(_("Can't find tax mapping"))
                if line_tax:
                    rc_invoice_line['invoice_line_tax_id'] = [
                        (6, False, [tax_code_id])]
                rc_invoice_line[
                    'account_id'] = rc_type.transitory_account_id.id
                rc_invoice_lines.append([0, False, rc_invoice_line])

        if rc_invoice_lines:
            inv_vals = self.rc_inv_vals(
                rc_partner, rc_account, rc_type, rc_invoice_lines)

            # create or write the self invoice
            if self.rc_self_invoice_id:
                # this is needed when user takes back to draft supplier
                # invoice, edit and validate again
                rc_invoice = self.rc_self_invoice_id
                rc_invoice.invoice_line.unlink()
                rc_invoice.related_documents.unlink()

                rc_invoice.period_id = False
                rc_invoice.write(inv_vals)
                rc_invoice.button_reset_taxes()
                rc_invoice
            else:
                rc_invoice = self.create(inv_vals)
                self.rc_self_invoice_id = rc_invoice.id
                rc_invoice.button_reset_taxes()
            rc_invoice.signal_workflow('invoice_open')
            self.env['fatturapa.related_document_type'].create({'invoice_id':rc_invoice.id,'type':'invoice','date':self.registration_date,
                                                                'DocumentID':self.reference or self.supplier_invoice_number or '',
                                                                'name':self.reference or self.supplier_invoice_number or ''})
            if rc_type.with_supplier_self_invoice:
                self.reconcile_supplier_invoice()
            #else:
                    #rocco 13/07/2022
                    #rc_payment = self.partially_reconcile_supplier_invoice()
                    #self.reconcile_rc_invoice(rc_payment)    
class invoice_close_webtex(osv.osv_memory):
    _inherit = 'account.invoice.close'
    @api.multi
    def close_invoice(self):
           invoice_obj = self.env['account.invoice']
           active_ids=self.env.context.get('active_ids', [])#
           invoice_ids_obj=invoice_obj.browse(active_ids)
           self.close_invoice_cron(corr_journal_id=None,pag_journal_id=None,da_date_corr=None,a_date_corr=None,date_pag=None)
           for invoice_id_obj in invoice_ids_obj:
                if  invoice_id_obj.rc_self_invoice_id and invoice_id_obj.rc_self_invoice_id.state!='paid' :
                   self.with_context({'active_ids':[invoice_id_obj.rc_self_invoice_id.id]}).close_invoice_cron(corr_journal_id=None,pag_journal_id=None,da_date_corr=None,a_date_corr=None,date_pag=None)
           return  True

class Account_move_line(models.Model):
    _inherit = 'account.move.line'
                
    _sql_constraints = [
        ('credit_debit1', 'CHECK (credit*debit=0)',  'Wrong credit or debit value in accounting entry !'),
        ('credit_debit2', 'CHECK (1=1)', 'Wrong credit or debit value in accounting entry !'),
    ]
