# -*- coding: utf-8 -*-
##############################################################################
#    
#    Copyright (C) 2011-2012 Associazione OpenERP Italia
#    (<http://www.openerp-italia.org>).
#    Copyright (C) 2012 Agile Business Group sagl (<http://www.agilebg.com>)
#    Copyright (C) 2012 Domsense srl (<http://www.domsense.com>) 
#    Thanks to Antonio de Vincentiis http://www.devincentiis.it/ ,
#    GAzie http://gazie.sourceforge.net/
#    and Cecchi s.r.l http://www.cecchi.com/
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
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

'''
*****************************************************************************************
 Questa classe genera il file RiBa standard ABI-CBI passando alla funzione "creaFile" i due array di seguito specificati:
$intestazione = array monodimensionale con i seguenti index:
              [0] = credit_sia variabile lunghezza 5 alfanumerico
              [1] = credit_abi assuntrice variabile lunghezza 5 numerico
              [2] = credit_cab assuntrice variabile lunghezza 5 numerico
              [3] = credit_conto conto variabile lunghezza 10 alfanumerico
              [4] = data_creazione variabile lunghezza 6 numerico formato GGMMAA
              [5] = nome_supporto variabile lunghezza 20 alfanumerico
              [6] = codice_divisa variabile lunghezza 1 alfanumerico opzionale default "E"
              [7] = name_company nome ragione sociale creditore variabile lunghezza 24 alfanumerico
              [8] = indirizzo_creditore variabile lunghezza 24 alfanumerico
              [9] = cap_citta_creditore variabile lunghezza 24 alfanumerico
              [10] = ref (definizione attivita) creditore 
              [11] = codice fiscale/partita iva creditore alfanumerico opzionale

$ricevute_bancarie = array bidimensionale con i seguenti index:
                   [0] = numero ricevuta lunghezza 10 numerico
                   [1] = data scadenza lunghezza 6 numerico
                   [2] = importo in centesimi di euro
                   [3] = nome debitore lunghezza 60 alfanumerico
                   [4] = codice fiscale/partita iva debitore lunghezza 16 alfanumerico
                   [5] = indirizzo debitore lunghezza 30 alfanumerico
                   [6] = cap debitore lunghezza 5 numerico
                   [7] = citta debitore alfanumerico
                   [8] = debitor_province debitore alfanumerico
                   [9] = abi banca domiciliataria lunghezza 5 numerico
                   [10] = cab banca domiciliataria lunghezza 5 numerico
                   [11] = descrizione banca domiciliataria lunghezza 50 alfanumerico
                   [12] = codice cliente attribuito dal creditore lunghezza 16 numerico
                   [13] = numero fattura lunghezza 40 alfanumerico
                   [14] = data effettiva della fattura

'''

from openerp import tools
import base64
from openerp.osv import fields,orm
from openerp.tools.translate import _
import datetime

class riba_file_export(orm.TransientModel):
    _inherit = 'riba.file.export'

    def act_getfile(self, cr, uid, ids, context=None):
        active_ids = context and context.get('active_ids', [])
        order_obj = self.pool.get('riba.distinta').browse(cr, uid, active_ids, context=context)[0]
        credit_bank = order_obj.config.bank_id
        name_company = order_obj.config.company_id.partner_id.name
        if not credit_bank.iban:        
           if not credit_bank.bank.x_abi:
               raise orm.except_orm('Error', _('Nessun iban specificato o abi/cab'))
        if credit_bank.bank.x_abi:
                credit_abi = credit_bank.bank.x_abi[0:6]
                credit_cab = credit_bank.bank.x_cab[0:6]
        else:
            credit_abi = credit_bank.iban[5:10]
            credit_cab = credit_bank.iban[10:15]
        credit_conto = credit_bank.iban[-12:]
        if not credit_bank.codice_sia:
           raise orm.except_orm('Error', _('No SIA Code specified for: ') + name_company)
        credit_sia = credit_bank.codice_sia
        credit_account = credit_bank.iban[15:27]
        dataemissione = datetime.datetime.now().strftime("%d%m%y")
        nome_supporto = datetime.datetime.now().strftime("%d%m%y%H%M%S") + credit_sia
        creditor_address = order_obj.config.company_id.partner_id
        creditor_street = creditor_address.street or ''
        creditor_city = creditor_address.city or ''
        creditor_province = creditor_address.province.code or ''
        if not order_obj.config.company_id.partner_id.vat and not order_obj.config.company_id.partner_id.fiscalcode:
           raise orm.except_orm('Error', _('No VAT or Fiscalcode specified for: ') + name_company)
        array_testata = [
               credit_sia,
               credit_abi,
               credit_cab,
               credit_conto,
               dataemissione,
               nome_supporto,
               'E',
               name_company,
               creditor_address.street or '',
               creditor_address.zip or '' + ' ' + creditor_city,
               order_obj.config.company_id.partner_id.ref or '',
               order_obj.config.company_id.partner_id.vat and order_obj.config.company_id.partner_id.vat[2:] or order_obj.config.company_id.partner_id.fiscalcode,
               ]
        arrayRiba = []
        for line in order_obj.line_ids:
            debit_bank = line.bank_id
            debitor_address = line.partner_id
            debitor_street = debitor_address.street or ''
            debitor_zip = debitor_address.zip or ''
            if not debit_bank.iban:        
               if not debit_bank.bank.x_abi:
                   raise orm.except_orm('Error', _('Nessun iban specificato o abi/cab')+ line.partner_id.name)
            if debit_bank.bank.x_abi:
                    debit_abi = debit_bank.bank.x_abi[0:6]
                    debit_cab = debit_bank.bank.x_cab[0:6]
            else:
                    debit_abi = debit_bank.iban[5:10]
                    debit_cab = debit_bank.iban[10:15]
            debitor_city = debitor_address.city or ''
            debitor_province = debitor_address.province.code or ''
            if not line.due_date: # ??? VERIFICARE
                due_date =  '000000'
            else:
                due_date = datetime.datetime.strptime(line.due_date[:10], '%Y-%m-%d').strftime("%d%m%y")

            if not line.partner_id.vat and not line.partner_id.fiscalcode:
                raise orm.except_orm('Error', _('No VAT or Fiscal code specified for ') + line.partner_id.name)
            Riba = [
                        line.sequence,
                        due_date,
                        line.amount,
                        line.partner_id.name,
                        line.partner_id.vat and line.partner_id.vat[2:] or line.partner_id.fiscalcode,
                        debitor_street,
                        debitor_zip,
                        debitor_city,
                        debitor_province,
                        debit_abi,
                        debit_cab,
                        debit_bank.bank and debit_bank.bank.name or debit_bank.bank_name,
                        line.partner_id.ref or '',
                        #line.move_line_id.name,
                        line.invoice_number,
                        #datetime.datetime.strptime(line.distinta_id.date_created, '%Y-%m-%d').strftime("%d/%m/%Y"),
                        line.invoice_date,
                        ]
            arrayRiba.append(Riba)

        out=base64.encodestring(self._creaFile(array_testata, arrayRiba).encode("utf8"))
        self.write(cr, uid, ids, {'state':'get', 'riba_.txt':out}, context=context)

        model_data_obj = self.pool.get('ir.model.data')
        view_rec = model_data_obj.get_object_reference(cr, uid, 'l10n_it_ricevute_bancarie', 'wizard_riba_file_export')
        view_id = view_rec and view_rec[1] or False

        return {
           'view_type': 'form',
           'view_id' : [view_id],
           'view_mode': 'form',
           'res_model': 'riba.file.export',
           'res_id': ids[0],
           'type': 'ir.actions.act_window',
           'target': 'new',
           'context': context,
        }

    _name = "riba.file.export"

    _columns = {
        'state': fields.selection( ( ('choose','choose'),   # choose accounts
                                     ('get','get'),         # get the file
                                   ) ),
        'riba_.txt': fields.binary('File', readonly=True),
    }
    _defaults = { 
        'state': lambda *a: 'choose',
        }


