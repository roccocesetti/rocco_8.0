# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 Davide Corio <davide.corio@lsweb.it>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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

#import openerp
#from openerp import SUPERUSER_ID, api
#from openerp import tools
#from openerp.osv import fields, osv, expression
#from openerp.tools.translate import _
#from openerp.tools.float_utils import float_round as round
#from openerp.tools.safe_eval import safe_eval as eval
from openerp.osv import fields, orm

class AccountTax(orm.Model):
    _inherit = 'account.tax'
    _columns = {
        'non_taxable_nature': fields.selection([
            ('N1', 'escluse ex art. 15'),
            ('N2', 'non soggette'),
            ('N3', 'non imponibili'),
            ('N4', 'esenti'),
            ('N5', 'regime del margine'),
            ('N6', 'inversione contabile (reverse charge)'),
            ], string="Non taxable nature"),
        'payability': fields.selection([
            ('I', 'Immediate payability'),
            ('D', 'Deferred payability'),
            ('S', 'Split payment'),
            ], string="VAT payability"),
        'law_reference': fields.char(
            'Law reference', size=128),
    }

    def get_tax_by_invoice_tax(self, cr, uid, invoice_tax, context=None):
        if ' - ' in invoice_tax:
            tax_descr = invoice_tax.split(' - ')[0]
            tax_ids = self.search(cr, uid, [
                ('description', '=', tax_descr),
                ], context=context)
            if not tax_ids:
                raise orm.except_orm(
                    _('Error'), _('No tax %s found') %
                    tax_descr)
            if len(tax_ids) > 1:
                raise orm.except_orm(
                    _('Error'), _('Too many tax %s found') %
                    tax_descr)
        else:
            tax_name = invoice_tax
            tax_ids = self.search(cr, uid, [
                ('name', '=', tax_name),
                ], context=context)
            if not tax_ids:
                raise orm.except_orm(
                    _('Error'), _('No tax %s found') %
                    tax_name)
            if len(tax_ids) > 1:
                raise orm.except_orm(
                    _('Error'), _('Too many tax %s found') %
                    tax_name)
        return tax_ids[0]

class faturapa_summary_data(orm.Model):
    # _position = ['2.2.2']
    _name = "faturapa.summary.data"
    _columns = {
        'tax_rate': fields.float('Tax Rate'),
        'non_taxable_nature': fields.selection([
            ('N1', 'escluse ex art. 15'),
            ('N2', 'non soggette'),
            ('N3', 'non imponibili'),
            ('N4', 'esenti'),
            ('N5', 'regime del margine'),
            ('N6', 'inversione contabile (reverse charge)'),
        ], string="Non taxable nature"),
        'incidental charges': fields.float('Incidental Charges'),
        'rounding': fields.float('Rounding'),
        'amount_untaxed': fields.float('Amount untaxed'),
        'amount_tax': fields.float('Amount tax'),
        'payability': fields.selection([
            ('I', 'Immediate payability'),
            ('D', 'Deferred payability'),
            ('S', 'Split payment'),
        ], string="VAT payability"),
        'law_reference': fields.char(
            'Law reference', size=128),
        'invoice_id': fields.many2one(
            'account.invoice', 'Related Invoice',
            ondelete='cascade', select=True)
    }


class account_invoice(orm.Model):
    _inherit = "account.invoice"

    _columns = {
        'fatturapa_attachment_in_id': fields.many2one(
            'fatturapa.attachment.in', 'FatturaPA Import File',
            ondelete='restrict'),
        'inconsistencies': fields.text('Import Inconsistencies'),
        'fatturapa_summary_ids': fields.one2many(
            'faturapa.summary.data', 'invoice_id',
            'FatturaPA Summary   Datas'
        ),
        'transport_vehicle': fields.char('Vehicle', size=80),

    }


class fatturapa_article_code(orm.Model):
    # _position = ['2.2.1.3']
    _name = "fatturapa.article.code"
    _description = 'FatturaPA Article Code'

    _columns = {
        'name': fields.char('Cod Type', size=35),
        'code_val': fields.char('Code Value', size=35),
        'invoice_line_id': fields.many2one(
            'account.invoice.line', 'Related Invoice line',
            ondelete='cascade', select=True
        )
    }


class account_invoice_line(orm.Model):
    # _position = [
    #     '2.2.1.3', '2.2.1.6', '2.2.1.7',
    #     '2.2.1.8', '2.1.1.10'
    # ]
    _inherit = "account.invoice.line"

    _columns = {
        'cod_article_ids': fields.one2many(
            'fatturapa.article.code', 'invoice_line_id',
            'Cod. Articles'
        ),
        'service_type': fields.selection([
            ('SC', 'sconto'),
            ('PR', 'premio'),
            ('AB', 'abbuono'),
            ('AC', 'spesa accessoria'),
            ], string="Service Type"),
        'ftpa_uom': fields.char('Fattura Pa Unit of Measure', size=10),
        'service_start': fields.date('Service start at'),
        'service_end': fields.date('Service end at'),
        'discount_rise_price_ids': fields.one2many(
            'discount.rise.price', 'invoice_line_id',
            'Discount and Rise Price Details'
        ),
    }
class discount_rise_price_pav12(orm.Model):
    # _position = ['2.1.1.8', '2.2.1.10']
    _name = "discount.rise.price.pav12"
    _description = 'FatturaPA Discount Rise Price Data'

    _columns = {
        'name': fields.selection(
            [('SC', 'Discount'), ('MG', 'Rise Price')], 'Type'),
        'percentage': fields.float('Percentage'),
        'amount': fields.float('Amount'),
        'invoice_id': fields.many2one(
            'account.invoice.line', 'Related Invoice',
            ondelete='cascade', select=True
        ),
    }
#discount_rise_price_pav12()
class discount_rise_price(orm.Model):
    # _position = ['2.1.1.8', '2.2.1.10']
    _name = "discount.rise.price"
    _description = 'FatturaPA Discount Rise Price Data'

    _columns = {
        'name': fields.selection(
            [('SC', 'Discount'), ('MG', 'Rise Price')], 'Type'),
        'percentage': fields.float('Percentage'),
        'amount': fields.float('Amount'),
        'invoice_id': fields.many2one(
            'account.invoice', 'Related Invoice',
            ondelete='cascade', select=True
        ),
        'invoice_line_id': fields.many2one(
            'account.invoice.line', 'Related Invoice line',
            ondelete='cascade', select=True
        ),
    }
#discount_rise_price()