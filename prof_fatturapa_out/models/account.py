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

from openerp.osv import fields, orm
import time
from lxml import etree
import logging
from openerp.api import multi
_logger = logging.getLogger(__name__)
from openerp import models, fields as x_fields, api, _

class res_partner(orm.Model):
    _inherit = 'res.partner'

    _sql_constraints = [
        ('rea_code_uniq', 'Check(1=1)',
         'The rea code code must be unique per company !'),
    ]

    def simple_vat_check(self, cr, uid, country_code, vat_number, context=None):
       return True


class account_invoice_line(orm.Model):
    _inherit = "account.invoice.line"
    _columns = {

        'ftpa_line_number': fields.integer("Line number", readonly=True, copy=False)

    }
class account_invoice(orm.Model):
    _inherit = "account.invoice"

    def _get_ir_attachment(self, cr, uid, ids, name, args, context=None):
        
        res = {}
        for inv_pa in self.browse(cr, uid, ids, context=context):
            id = inv_pa.id
            res[id] = []
            ir_attach_obj=self.pool.get('ir.attachment')
            if inv_pa.fatturapa_attachment_out_id:
                if inv_pa.fatturapa_attachment_out_id.url_id.type=="json":
                        if inv_pa.fatturapa_attachment_out_id.json_fatCliSDIStato in ('HDO01','HDO05'):
                                res[id] = True
                                self.write(cr, uid, id, {'firmata':True}, context)
                        else: 
                                res[id] = False
                                self.write(cr, uid, id, {'firmata':False}, context)
                else:
                            
                    if inv_pa.fatturapa_attachment_out_id:
                        if inv_pa.fatturapa_attachment_out_id.ir_attachment_signed_id:
                                res[id] = True
                                if inv_pa.firmata==False:
                                    self.write(cr, uid, id, {'firmata':True}, context)
                        else:
                                res[id] = False
                                if inv_pa.firmata==True:
                                    self.write(cr, uid, id, {'firmata':False}, context)
                    else:
                                res[id] = False
                                if inv_pa.firmata==True:
                                    self.write(cr, uid, id, {'firmata':False}, context)
            else:
                                res[id] = False
                    
        return res
    def _get_trasmix(self, cr, uid, ids, name, args, context=None):
        
        res = {}
        for inv_pa in self.browse(cr, uid, ids, context=context):
            id = inv_pa.id
            res[id] = []
            if inv_pa.fatturapa_attachment_out_id:
                if inv_pa.fatturapa_attachment_out_id.trasmessa:
                    res[id] = True
                    if inv_pa.trasmessa==False:
                        self.write(cr, uid, id, {'trasmessa':True}, context)
                else:
                    res[id] = False
                    if inv_pa.trasmessa==True:
                        self.write(cr, uid, id, {'trasmessa':False}, context)
            else:
                        res[id] = False
                        if inv_pa.trasmessa==True:
                            self.write(cr, uid, id, {'trasmessa':False}, context)
        return res

    _columns = {
        'fatturapa_attachment_out_id': fields.many2one(
            'fatturapa.attachment.out', 'FatturaPA Export File',
            readonly=True),
        'fun_firmata': fields.function(_get_ir_attachment, string='Funz.fatt.firmata',type='boolean'),
        'fun_tramessa': fields.function(_get_trasmix, string='Funz.fatt.trasmessa',type='boolean'),
        'firmata':fields.boolean('Firmata', required=False),
        'trasmessa':fields.boolean('Trasmessa', required=False),
        'x_pack_ids' : fields.many2many('stock.picking.package.preparation',
        'stock_picking_package_preparation_invoice',  'invoice_id','pack_id',
        string='DDT'),

    }
    def copy(self, cr, uid, id, default=None, context=None):
        default = default or {}
        default.update({
            'pick_ids':None,
            'picking_ids':None,
            'fatturapa_attachment_in_id':None,
                        'fatturapa_attachment_out_id':None,
            })
        res=super(account_invoice, self).copy( cr, uid, id, default=default, context=context)
        return res    
class FatturapaDocumentType(models.Model):
    # _position = ['2.1.1.1']
    _name = "fatturapa.document_type"
    _description = 'E-invoice Document Type'

    name = x_fields.Char('Description', size=128)
    code = x_fields.Char('Code', size=4)

class res_company(orm.Model):
    _inherit = 'res.company'
    _columns = {

    'dati_bollo_product_id' : fields.many2one(
        'product.product', 'Product for Dati Bollo',
        help='Prodotto da utilizzare nelle fatture passive quando nell\'XML '
             'viene valorizzato l\'elemento DatiBollo'
        ),
    'cassa_previdenziale_product_id': fields.many2one(
        'product.product', 'Product for Dati Cassa Previdenziale',
        help='Prodotto da utilizzare nelle fatture passive quando nell\'XML '
             'viene valorizzato l\'elemento DatiCassaPrevidenziale'
        ),
    'sconto_maggiorazione_product_id': fields.many2one(
        'product.product', 'Product for Sconto Maggiorazione',
        help='Prodotto da utilizzare nelle fatture passive quando nell\'XML '
             'viene valorizzato l\'elemento ScontoMaggiorazione'
        ),

    }

class AccountTaxKind(orm.Model):

    _inherit = 'account.tax.kind'
    _columns = {

    'code': fields.char(string='Code', size=4, required=True)
}
"""
class AccountTax(orm.Model):
    _inherit = 'account.tax'
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
"""
