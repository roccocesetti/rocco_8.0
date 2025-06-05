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

from openerp import tools
import openerp.addons.decimal_precision as dp
from openerp.osv import fields,osv

class account_invoice_report(osv.osv):
    _name = "account.invoice.corr.report"
    _description = "Invoices Statistics"
    _auto = False
    _rec_name = 'date'

    def _compute_amounts_in_user_currency(self, cr, uid, ids, field_names, args, context=None):
        """Compute the amounts in the currency of the user
        """
        if context is None:
            context={}
        currency_obj = self.pool.get('res.currency')
        currency_rate_obj = self.pool.get('res.currency.rate')
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        user_currency_id = user.company_id.currency_id.id
        currency_rate_id = currency_rate_obj.search(
            cr, uid, [
                ('rate', '=', 1),
                '|',
                    ('currency_id.company_id', '=', user.company_id.id),
                    ('currency_id.company_id', '=', False)
                ], limit=1, context=context)[0]
        base_currency_id = currency_rate_obj.browse(cr, uid, currency_rate_id, context=context).currency_id.id
        res = {}
        ctx = context.copy()
        for item in self.browse(cr, uid, ids, context=context):
            ctx['date'] = item.date
            price_total = currency_obj.compute(cr, uid, base_currency_id, user_currency_id, item.amount_total, context=ctx)
            price_tax = currency_obj.compute(cr, uid, base_currency_id, user_currency_id, item.amount_tax, context=ctx)
            price_notax = currency_obj.compute(cr, uid, base_currency_id, user_currency_id, item.amount_notax, context=ctx)
            residual = currency_obj.compute(cr, uid, base_currency_id, user_currency_id, item.residual, context=ctx)
            res[item.id] = {
                'user_currency_amount_total': price_total,
                'user_currency_amount_tax': price_tax,
                'user_currency_amount_notax': price_notax,
                'user_currency_residual': residual,
            }
        return res

    _columns = {
        'date': fields.date('Data', readonly=True),
        'period_id': fields.many2one('account.period', 'Force Period', domain=[('state','<>','done')], readonly=True),
        'fiscal_position': fields.many2one('account.fiscal.position', 'Fiscal Position', readonly=True),
        'currency_id': fields.many2one('res.currency', 'Currency', readonly=True),
        'journal_id': fields.many2one('account.journal', 'Journal', readonly=True),
        'partner_id': fields.many2one('res.partner', 'Partner', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'user_id': fields.many2one('res.users', 'Salesperson', readonly=True),
        'amount_total': fields.float('Totale', readonly=True),
        'amount_notax': fields.float('Imponibile', readonly=True),
        'amount_tax': fields.float('Iva', readonly=True),
        'tax_id': fields.many2one('account.tax.code', 'Iva',readonly=True),
        'user_currency_amount_total': fields.function(_compute_amounts_in_user_currency, string="Totale", type='float', digits_compute=dp.get_precision('Account'), multi="_compute_amounts"),
        'user_currency_amonunt_notax': fields.function(_compute_amounts_in_user_currency, string="Totale Imponibile", type='float', digits_compute=dp.get_precision('Account'), multi="_compute_amounts"),
        'user_currency_amonunt_tax': fields.function(_compute_amounts_in_user_currency, string="Totale Iva", type='float', digits_compute=dp.get_precision('Account'), multi="_compute_amounts"),
        'currency_rate': fields.float('Currency Rate', readonly=True),
        'nbr': fields.integer('# of Invoices', readonly=True),  # TDE FIXME master: rename into nbr_lines
        'type': fields.selection([
            ('out_invoice','Customer Invoice'),
            ('in_invoice','Supplier Invoice'),
            ('out_refund','Customer Refund'),
            ('in_refund','Supplier Refund'),
            ],'Type', readonly=True),
        'state': fields.selection([
            ('draft','Draft'),
            ('proforma','Pro-forma'),
            ('proforma2','Pro-forma'),
            ('open','Open'),
            ('paid','Done'),
            ('cancel','Cancelled')
            ], 'Invoice Status', readonly=True),
        'account_id': fields.many2one('account.account', 'Account',readonly=True),
        'account_tax_id': fields.many2one('account.account', 'Account tax',readonly=True),
        'partner_bank_id': fields.many2one('res.partner.bank', 'Bank Account',readonly=True),
        'residual': fields.float('Total Residual', readonly=True),
        'user_currency_residual': fields.function(_compute_amounts_in_user_currency, string="Total Residual", type='float', digits_compute=dp.get_precision('Account'), multi="_compute_amounts"),
        'date_due': fields.date('Due Date', readonly=True),
        'country_id': fields.many2one('res.country', 'Country of the Partner Company'),
    }
    _order = 'date desc'

    _depends = {
        'account.invoice': [
            'account_id', 'amount_total', 'amount_untaxed','amount_tax','commercial_partner_id', 'company_id',
            'currency_id', 'date_due', 'date_invoice', 'fiscal_position',
            'journal_id', 'partner_bank_id', 'partner_id', 'payment_term',
            'period_id', 'residual', 'state', 'type', 'user_id',
        ],
        'account.invoice.tax': [
            'account_id', 'invoice_id', 'amount', 'base',
            'base_amount', 'base_code_id','tax_code_id','tax_amount'
        ],
        'account.tax.code': ['code'],
        'res.currency.rate': ['currency_id', 'name'],
        'res.partner': ['country_id'],
    }

    def _select(self):
        select_str = """
            SELECT sub.id, sub.date, sub.tax_id,sub.partner_id, sub.country_id,
                sub.payment_term, sub.period_id, sub.currency_id, sub.journal_id,
                sub.fiscal_position, sub.user_id, sub.company_id, sub.nbr, sub.type, sub.state,
                sub.amount_total, sub.amount_notax,  sub.amount_tax, 
                sub.date_due, sub.account_id, sub.account_tax_id,sub.partner_bank_id,
                sub.amount_total / cr.rate as price_total, sub.amount_notax /cr.rate as price_notax,sub.amount_tax /cr.rate as price_tax,
                cr.rate as currency_rate,sub.residual / cr.rate as residual, sub.commercial_partner_id as commercial_partner_id
        """
        return select_str

    def _sub_select(self):
        select_str = """
                SELECT min(ait.id) AS id,
                    ai.date_invoice AS date,
                     ai.partner_id, ai.payment_term, ai.period_id,
                    ai.currency_id, ai.journal_id, ai.fiscal_position, ai.user_id, ai.company_id,
                    count(ait.*) AS nbr,
                    ai.type, ai.state,  ai.date_due,ai.account_id,ait.account_id as account_tax_id, ait.tax_code_id as tax_id,
                    ai.partner_bank_id,
                    SUM(CASE
                         WHEN ai.type::text = ANY (ARRAY['out_refund'::character varying::text, 'in_invoice'::character varying::text])
                            THEN - (ait.amount + ait.base)
                            ELSE (ait.amount + ait.base)
                        END) AS amount_total,
                    SUM(CASE
                         WHEN ai.type::text = ANY (ARRAY['out_refund'::character varying::text, 'in_invoice'::character varying::text])
                            THEN - ait.base
                            ELSE ait.base 
                        END) AS amount_notax,
                    SUM(CASE
                         WHEN ai.type::text = ANY (ARRAY['out_refund'::character varying::text, 'in_invoice'::character varying::text])
                            THEN - ait.amount
                            ELSE ait.amount 
                        END) AS amount_tax,
                    CASE
                     WHEN ai.type::text = ANY (ARRAY['out_refund'::character varying::text, 'in_invoice'::character varying::text])
                        THEN - ai.residual
                        ELSE ai.residual
                    END / (SELECT count(*) FROM account_invoice_line l where invoice_id = ai.id) *
                    count(*) AS residual,
                    ai.commercial_partner_id as commercial_partner_id,
                    partner.country_id
        """
        return select_str

    def _from(self):
        from_str = """
                FROM account_invoice_tax ait
                JOIN account_invoice ai ON ai.id = ait.invoice_id
                JOIN res_partner partner ON ai.commercial_partner_id = partner.id
                LEFT JOIN account_tax_code atc ON atc.id = ait.tax_code_id
        """
        return from_str

    def _group_by(self):
        group_by_str = """
                GROUP BY ait.tax_code_id,ai.period_id, ai.date_invoice, ai.id,
                    ai.partner_id, ai.payment_term,  ai.currency_id, ai.journal_id,
                    ai.fiscal_position, ai.user_id, ai.company_id, ai.type, ai.state, 
                    ai.date_due, ai.account_id, ait.account_id, ai.partner_bank_id, ai.residual,
                    ai.amount_total, ai.commercial_partner_id, partner.country_id
        """
        return group_by_str

    def init(self, cr):
        # self._table = account_invoice_report
        tools.drop_view_if_exists(cr, self._table)
        cr.execute("""CREATE or REPLACE VIEW %s as (
            WITH currency_rate (currency_id, rate, date_start, date_end) AS (
                SELECT r.currency_id, r.rate, r.name AS date_start,
                    (SELECT name FROM res_currency_rate r2
                     WHERE r2.name > r.name AND
                           r2.currency_id = r.currency_id
                     ORDER BY r2.name ASC
                     LIMIT 1) AS date_end
                FROM res_currency_rate r
            )
            %s
            FROM (
                %s %s %s
            ) AS sub
            JOIN currency_rate cr ON
                (cr.currency_id = sub.currency_id AND
                 cr.date_start <= COALESCE(sub.date, NOW()) AND
                 (cr.date_end IS NULL OR cr.date_end > COALESCE(sub.date, NOW())))
        )""" % (
                    self._table,
                    self._select(), self._sub_select(), self._from(), self._group_by()))


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
