# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 Davide Corio <davide.corio@lsweb.it>
#    Copyright (C) 2015 Lorenzo Battistini <lorenzo.battistini@agilebg.com>
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

import base64
from openerp.osv import orm,fields
import time
from openerp.tools.translate import _
from openerp.addons.l10n_it_fatturapa.bindings.fatturapa_v_1_2 import (
    FatturaElettronica,
    FatturaElettronicaHeaderType,
    DatiTrasmissioneType,
    IdFiscaleType,
    ContattiTrasmittenteType,
    CedentePrestatoreType,
    DatiDDTType,
    DatiTrasportoType,
    DatiAnagraficiVettoreType,
    IdFiscaleType,
    AnagraficaType,
    IndirizzoType,
    IscrizioneREAType,
    CessionarioCommittenteType,
    DatiAnagraficiCedenteType,
    DatiAnagraficiCessionarioType,
    FatturaElettronicaBodyType,
    DatiGeneraliType,
    DettaglioLineeType,
    DatiBeniServiziType,
    DatiRiepilogoType,
    DatiGeneraliDocumentoType,
    DatiDocumentiCorrelatiType,
    ContattiType,
    DatiPagamentoType,
    DettaglioPagamentoType,
    AllegatiType,
    ScontoMaggiorazioneType
)
from openerp.addons.l10n_it_fatturapa.models.account import (
    RELATED_DOCUMENT_TYPES)
import logging
_logger = logging.getLogger(__name__)

try:
    from unidecode import unidecode
    from pyxb.exceptions_ import SimpleFacetValueError, SimpleTypeValueError
except ImportError as err:
    _logger.debug(err)
from openerp.tools.float_utils import float_round as round
from openerp import models, fields as x_fields

class wizard_show_Fatturapa(orm.TransientModel):
    _name = "wizard.show.fatturapa"
    _description = "show FatturaPA"
    _columns = {
        'name':fields.char('name', size=64, required=False, readonly=False),
        'fatturapa_html': fields.html('Fatturapa html', readonly=True, translate=True, sanitize=True, help="Rich-text/HTML version of the message (placeholders may be used here)"),
        'fatturapa':fields.binary('Fatturapa download', filters=None, readonly=True),     
        'fatturapa_name':fields.char(size=64, required=False, readonly=False),     
                    }
    
    _defaults = {  
        'name': str(lambda *a: time.strftime('%Y-%m-%d')),  
        }

class WizardExportFatturapa(orm.TransientModel):
    _inherit = 'wizard.export.fatturapa' 
    #Do not touch _name it must be same as _inherit
    #_name = 'wizard.export.fatturapa' = "wizard.export.fatturapa"
    #_description = "Export FatturaPA"
    _columns = {

    'include_ddt_data' : fields.selection([
        ('normale', 'Normale'),
        ('dati_ddt', 'Includi Dati DDT'),
        ('dati_trasporto', 'Includi Dati Trasporto'),
        ],
        string="Dati DDT",
        help='Includi Dati DDT: Blocco da valorizzare nei casi di fattura '
             '"differita" per '
             'indicare il documento con cui e\' stato consegnato il bene\n'
             'Includi Dati Trasporto: Blocco valorizzabile nei casi di '
             'fattura "accompagnatoria" per '
             'inserire informazioni relative al trasporto'
    )
    }
    _defaults = {  
        'include_ddt_data': 'normale',  
        }
    def __init__(self, cr, uid, **kwargs):
        self.fatturapa = False
        self.number = False
        super(WizardExportFatturapa, self).__init__(cr, uid, **kwargs)

    def saveAttachment(self, cr, uid, context=None):
        if context is None:
            context = {}

        number = self.number

        user_obj = self.pool['res.users']
        company = user_obj.browse(cr, uid, uid).company_id

        if not company.vat:
            raise orm.except_orm(
                _('Error!'), _('Company TIN not set.'))
        attach_obj = self.pool['fatturapa.attachment.out']
        attach_vals = {
            'name': '%s_%s.xml' % (company.vat, str(number)),
            'datas_fname': '%s_%s.xml' % (company.vat, str(number)),
            'datas': base64.encodestring(self.fatturapa.toxml("latin1")),
        }
        attach_id = attach_obj.create(cr, uid, attach_vals, context=context)

        return attach_id

    def setProgressivoInvio(self, cr, uid, context=None):
        if context is None:
            context = {}

        user_obj = self.pool['res.users']
        company = user_obj.browse(cr, uid, uid).company_id
        sequence_obj = self.pool['ir.sequence']
        fatturapa_sequence = company.fatturapa_sequence_id
        if not fatturapa_sequence:
            raise orm.except_orm(
                _('Error!'), _('FatturaPA sequence not configured.'))
        self.number = number = sequence_obj.next_by_id(
            cr, uid, fatturapa_sequence.id, context=context)
        self.fatturapa.FatturaElettronicaHeader.DatiTrasmissione.\
            ProgressivoInvio = number
        return True

    def _setIdTrasmittente(self, cr, uid, company, context=None):
        if context is None:
            context = {}

        if not company.country_id:
            raise orm.except_orm(
                _('Error!'), _('Company Country not set.'))
        IdPaese = company.country_id.code

        IdCodice = company.partner_id.fiscalcode
        if not IdCodice:
            IdCodice = company.vat[2:]
        if not IdCodice:
            raise orm.except_orm(
                _('Error'), _('Company does not have fiscal code or VAT'))

        self.fatturapa.FatturaElettronicaHeader.DatiTrasmissione.\
            IdTrasmittente = IdFiscaleType(
                IdPaese=IdPaese, IdCodice=IdCodice)

        return True

    def _setFormatoTrasmissione(self, cr, uid, company,partner, context=None):
        if context is None:
            context = {}
        code='FPR12'
        if partner.is_pa:
                        code='FPA12'
        else:
                        code='FPR12'
        self.fatturapa.FatturaElettronicaHeader.DatiTrasmissione.\
            FormatoTrasmissione = code

        return True

    def _setCodiceDestinatario(self, cr, uid, partner, context=None):
        if context is None:
            context = {}
        """
        code = partner.ipa_code
        if not code:
                        raise orm.except_orm(
                            _('Error!'), _('IPA Code not set on partner form.'))
        
        """
        pec_destinatario = None
        if partner.is_pa:
            if not partner.ipa_code:
                raise orm.except_orm(_(
                    "Partner %s is PA but does not have IPA code"
                ) % partner.name)
            code = partner.ipa_code
        else:
            if not partner.codice_destinatario:
                raise orm.except_orm(_(
                    "Partner %s is not PA but does not have Codice "
                    "Destinatario"
                ) % partner.name)
            code = partner.codice_destinatario
            if code == '0000000':
                pec_destinatario = partner.pec_destinatario

        self.fatturapa.FatturaElettronicaHeader.DatiTrasmissione.\
            CodiceDestinatario = code.upper()
        self.fatturapa.FatturaElettronicaHeader.DatiTrasmissione. \
            CodiceDestinatario = code.upper()
        if pec_destinatario:
            self.fatturapa.FatturaElettronicaHeader.DatiTrasmissione. \
                PECDestinatario = pec_destinatario

        return True
    def _setPECDestinatario(self, cr, uid, partner, context=None):
        if context is None:
            context = {}
        pec_mail = partner.pec_mail
        #if not pec_mail and ( partner.ipa_code=='0000000'):
        if not pec_mail and not partner.ipa_code:
            raise orm.except_orm(
                _('Error!'), _('PEC mail not set on partner form.'))
        if pec_mail:
            self.fatturapa.FatturaElettronicaHeader.DatiTrasmissione.\
                PECDestinatario = pec_mail

        return True

    def _setContattiTrasmittente(self, cr, uid, company, context=None):
        if context is None:
            context = {}

        if not company.phone:
            raise orm.except_orm(
                _('Error!'), _('Company Telephone number not set.'))
        Telefono = company.phone

        if not company.email:
            raise orm.except_orm(
                _('Error!'), _('Email address not set.'))
        Email = company.email
        self.fatturapa.FatturaElettronicaHeader.DatiTrasmissione.\
            ContattiTrasmittente = ContattiTrasmittenteType(
                Telefono=Telefono, Email=Email)

        return True

    def setDatiTrasmissione(self, cr, uid, company, partner, context=None):
        if context is None:
            context = {}
        self.fatturapa.FatturaElettronicaHeader.DatiTrasmissione = (
            DatiTrasmissioneType())
        self._setIdTrasmittente(cr, uid, company, context=context)
        self._setFormatoTrasmissione(cr, uid, company, partner,context=context)
        self._setCodiceDestinatario(cr, uid, partner, context=context)
        self._setPECDestinatario(cr, uid, partner, context=context)
        self._setContattiTrasmittente(cr, uid, company, context=context)

    def _setDatiAnagraficiCedente(self, cr, uid, CedentePrestatore,
                                  company, context=None):
        if context is None:
            context = {}

        if not company.vat:
            raise orm.except_orm(
                _('Error!'), _('TIN not set.'))
        CedentePrestatore.DatiAnagrafici = DatiAnagraficiCedenteType()
        fatturapa_fp = company.fatturapa_fiscal_position_id
        if not fatturapa_fp:
            raise orm.except_orm(
                _('Error!'), _('FatturaPA fiscal position not set.'))
        CedentePrestatore.DatiAnagrafici.IdFiscaleIVA = IdFiscaleType(
            IdPaese=company.country_id.code, IdCodice=company.vat[2:])
        CedentePrestatore.DatiAnagrafici.Anagrafica = AnagraficaType(
            Denominazione=company.name)

        # not using for now
        #
        # Anagrafica = DatiAnagrafici.find('Anagrafica')
        # Nome = Anagrafica.find('Nome')
        # Cognome = Anagrafica.find('Cognome')
        # Titolo = Anagrafica.find('Titolo')
        # Anagrafica.remove(Nome)
        # Anagrafica.remove(Cognome)
        # Anagrafica.remove(Titolo)

        if company.partner_id.fiscalcode:
            CedentePrestatore.DatiAnagrafici.CodiceFiscale = (
                company.partner_id.fiscalcode)
        CedentePrestatore.DatiAnagrafici.RegimeFiscale = fatturapa_fp.code
        return True

    def _setAlboProfessionaleCedente(self, cr, uid, CedentePrestatore,
                                     company, context=None):
        if context is None:
            context = {}
        # TODO Albo professionale, for now the main company is considered
        # to be a legal entity and not a single person
        # 1.2.1.4   <AlboProfessionale>
        # 1.2.1.5   <ProvinciaAlbo>
        # 1.2.1.6   <NumeroIscrizioneAlbo>
        # 1.2.1.7   <DataIscrizioneAlbo>

    def _setSedeCedente(self, cr, uid, CedentePrestatore,
                        company, context=None):
        if context is None:
            context = {}

        if not company.street:
            raise orm.except_orm(
                _('Error!'), _('Street not set.'))
        if not company.zip:
            raise orm.except_orm(
                _('Error!'), _('ZIP not set.'))
        if not company.city:
            raise orm.except_orm(
                _('Error!'), _('City not set.'))
        if not company.partner_id.state_id:
            raise orm.except_orm(
                _('Error!'), _('Province not set.'))
        if not company.country_id:
            raise orm.except_orm(
                _('Error!'), _('Country not set.'))
        # FIXME: manage address number in <NumeroCivico>
        # see https://github.com/OCA/partner-contact/pull/96
        CedentePrestatore.Sede = IndirizzoType(
            Indirizzo=company.street,
            CAP=company.zip,
            Comune=company.city,
            Provincia=company.partner_id.state_id.code,
            Nazione=company.country_id.code)

        return True

    def _setStabileOrganizzazione(self, cr, uid, CedentePrestatore,
                                  company, context=None):
        if context is None:
            context = {}
        # not handled

    def _setRea(self, cr, uid, CedentePrestatore, company, context=None):
        if context is None:
            context = {}

        if company.fatturapa_rea_office and company.fatturapa_rea_number:
            CedentePrestatore.IscrizioneREA = IscrizioneREAType(
                Ufficio=(
                    company.fatturapa_rea_office and
                    company.fatturapa_rea_office.code or None),
                NumeroREA=company.fatturapa_rea_number or None,
                CapitaleSociale=(
                    company.fatturapa_rea_capital and
                    '%.2f' % company.fatturapa_rea_capital or None),
                SocioUnico=(company.fatturapa_rea_partner or None),
                StatoLiquidazione=company.fatturapa_rea_liquidation or None
                )

    def _setContatti(self, cr, uid, CedentePrestatore,
                     company, context=None):
        if context is None:
            context = {}
        CedentePrestatore.Contatti = ContattiType(
            Telefono=company.partner_id.phone or None,
            Fax=company.partner_id.fax or None,
            Email=company.partner_id.email or None
            )

    def _setPubAdministrationRef(self, cr, uid, CedentePrestatore,
                                 company, context=None):
        if context is None:
            context = {}
        if company.fatturapa_pub_administration_ref:
            CedentePrestatore.RiferimentoAmministrazione = (
                company.fatturapa_pub_administration_ref)

    def setCedentePrestatore(self, cr, uid, company, context=None):
        self.fatturapa.FatturaElettronicaHeader.CedentePrestatore = (
            CedentePrestatoreType())
        self._setDatiAnagraficiCedente(
            cr, uid, self.fatturapa.FatturaElettronicaHeader.CedentePrestatore,
            company, context=context)
        self._setSedeCedente(
            cr, uid, self.fatturapa.FatturaElettronicaHeader.CedentePrestatore,
            company, context=context)
        self._setAlboProfessionaleCedente(
            cr, uid, self.fatturapa.FatturaElettronicaHeader.CedentePrestatore,
            company, context=context)
        self._setStabileOrganizzazione(
            cr, uid, self.fatturapa.FatturaElettronicaHeader.CedentePrestatore,
            company, context=context)
        # FIXME: add Contacts
        self._setRea(
            cr, uid, self.fatturapa.FatturaElettronicaHeader.CedentePrestatore,
            company, context=context)
        self._setContatti(
            cr, uid, self.fatturapa.FatturaElettronicaHeader.CedentePrestatore,
            company, context=context)
        self._setPubAdministrationRef(
            cr, uid, self.fatturapa.FatturaElettronicaHeader.CedentePrestatore,
            company, context=context)

    def _setDatiAnagraficiCessionario(
            self, cr, uid, partner, context=None):
        if context is None:
            context = {}
        self.fatturapa.FatturaElettronicaHeader.CessionarioCommittente.\
            DatiAnagrafici = DatiAnagraficiCessionarioType()
        if not partner.vat and not partner.fiscalcode:
            raise orm.except_orm(
                _('Error!'), _('Partner VAT and Fiscalcode not set.'))
        fiscalcode=partner.fiscalcode
        vat=partner.vat
        if fiscalcode:
            if fiscalcode.find('OO99999999999')>=0:
                vat=fiscalcode
                fiscalcode=None
        if fiscalcode:
            self.fatturapa.FatturaElettronicaHeader.CessionarioCommittente.\
                DatiAnagrafici.CodiceFiscale = fiscalcode
        if vat:
                
                self.fatturapa.FatturaElettronicaHeader.CessionarioCommittente.\
                    DatiAnagrafici.IdFiscaleIVA = IdFiscaleType(
                        IdPaese=vat[0:2], IdCodice=vat[2:])
        self.fatturapa.FatturaElettronicaHeader.CessionarioCommittente.\
            DatiAnagrafici.Anagrafica = AnagraficaType(
                Denominazione=partner.name)

        # not using for now
        #
        # Anagrafica = DatiAnagrafici.find('Anagrafica')
        # Nome = Anagrafica.find('Nome')
        # Cognome = Anagrafica.find('Cognome')
        # Titolo = Anagrafica.find('Titolo')
        # Anagrafica.remove(Nome)
        # Anagrafica.remove(Cognome)
        # Anagrafica.remove(Titolo)

        if partner.eori_code:
            self.fatturapa.FatturaElettronicaHeader.CessionarioCommittente.\
                DatiAnagrafici.Anagrafica.CodEORI = partner.eori_code

        return True

    def _setSedeCessionario(self, cr, uid, partner, context=None):
        if context is None:
            context = {}

        if not partner.street:
            raise orm.except_orm(
                _('Error!'), _('Customer street not set.'))
        if not partner.zip:
            raise orm.except_orm(
                _('Error!'), _('Customer ZIP not set.'))
        if not partner.city:
            raise orm.except_orm(
                _('Error!'), _('Customer city not set.'))
        if not partner.state_id:
            raise orm.except_orm(
                _('Error!'), _('Customer province not set.'))
        if not partner.country_id:
            raise orm.except_orm(
                _('Error!'), _('Customer country not set.'))

        # FIXME: manage address number in <NumeroCivico>
        self.fatturapa.FatturaElettronicaHeader.CessionarioCommittente.Sede = (
            IndirizzoType(
                Indirizzo=partner.street,
                CAP=partner.zip,
                Comune=partner.city,
                Provincia=partner.state_id.code,
                Nazione=partner.country_id.code))

        return True

    def setRappresentanteFiscale(
            self, cr, uid, company, context=None):
        if context is None:
            context = {}

        if company.fatturapa_tax_representative:
            # TODO: RappresentanteFiscale should be usefull for foreign
            # companies sending invoices to italian PA only
            raise orm.except_orm(
                _("Error"), _("RappresentanteFiscale not handled"))
            # partner = company.fatturapa_tax_representative

        # DatiAnagrafici = RappresentanteFiscale.find('DatiAnagrafici')

        # if not partner.fiscalcode:
            # raise orm.except_orm(
            # _('Error!'), _('RappresentanteFiscale Partner '
            # 'fiscalcode not set.'))

        # DatiAnagrafici.find('CodiceFiscale').text = partner.fiscalcode

        # if not partner.vat:
            # raise orm.except_orm(
            # _('Error!'), _('RappresentanteFiscale Partner VAT not set.'))
        # DatiAnagrafici.find(
            # 'IdFiscaleIVA/IdPaese').text = partner.vat[0:2]
        # DatiAnagrafici.find(
            # 'IdFiscaleIVA/IdCodice').text = partner.vat[2:]
        # DatiAnagrafici.find('Anagrafica/Denominazione').text = partner.name
        # if partner.eori_code:
            # DatiAnagrafici.find(
            # 'Anagrafica/CodEORI').text = partner.codiceEORI
        return True

    def setCessionarioCommittente(self, cr, uid, partner, context=None):
        self.fatturapa.FatturaElettronicaHeader.CessionarioCommittente = (
            CessionarioCommittenteType())
        self._setDatiAnagraficiCessionario(cr, uid, partner, context=context)
        self._setSedeCessionario(cr, uid, partner, context=context)

    def setTerzoIntermediarioOSoggettoEmittente(
            self, cr, uid, company, context=None):
        if context is None:
            context = {}
        if company.fatturapa_sender_partner:
            # TODO
            raise orm.except_orm(
                _("Error"),
                _("TerzoIntermediarioOSoggettoEmittente not handled"))
        return True

    def setSoggettoEmittente(self, cr, uid, context=None):

        # FIXME: this record is to be checked invoice by invoice
        # so a control is needed to verify that all invoices are
        # of type CC, TZ or internally created by the company

        # SoggettoEmittente.text = 'CC'
        return True

    def setDatiGeneraliDocumento(self, cr, uid, invoice, body, context=None):
        if context is None:
            context = {}

        # TODO DatiSAL

        # TODO DatiDDT

        body.DatiGenerali = DatiGeneraliType()
        if not invoice.number:
            raise orm.except_orm(
                _('Error!'),
                _('Invoice does not have a number.'))

        TipoDocumento = 'TD01'
        if invoice.type == 'out_refund':
            TipoDocumento = 'TD04'
        if hasattr(invoice, 'fiscal_document_type_id'):
            if invoice.fiscal_document_type_id:
                TipoDocumento=invoice.fiscal_document_type_id.code
        ImportoTotaleDocumento = invoice.amount_total
        if invoice.split_payment:
            ImportoTotaleDocumento += invoice.amount_sp
        ImportoTotaleDocumento='%.2f' % ImportoTotaleDocumento
        body.DatiGenerali.DatiGeneraliDocumento = DatiGeneraliDocumentoType(
            TipoDocumento=TipoDocumento,
            Divisa=invoice.currency_id.name,
            Data=invoice.date_invoice,
            Numero=invoice.number,
            ImportoTotaleDocumento=ImportoTotaleDocumento)

        # TODO: DatiRitenuta, DatiBollo, DatiCassaPrevidenziale,
        # ScontoMaggiorazione, Arrotondamento,
        if invoice.partner_id.comment:
            if invoice.partner_id.comment.find('####')>=0:
                # max length of Causale is 200
                caus_list = invoice.partner_id.comment.replace('####','').split('\n')
                for causale in caus_list:
                    # Remove non latin chars, but go back to unicode string,
                    # as expected by String200LatinType
                    causale = causale.replace('#',' ').encode(
                        'latin', 'ignore').decode('latin')
                    body.DatiGenerali.DatiGeneraliDocumento.Causale.append(causale)

        if invoice.comment:
            # max length of Causale is 200
            caus_list = invoice.comment.split('\n')
            for causale in caus_list:
                # Remove non latin chars, but go back to unicode string,
                # as expected by String200LatinType
                causale = causale.strip().replace('#',' ').encode(
                    'latin', 'ignore').decode('latin')
                if len(causale)>0:
                    body.DatiGenerali.DatiGeneraliDocumento.Causale.append(causale)

        if invoice.company_id.fatturapa_art73:
            body.DatiGenerali.DatiGeneraliDocumento.Art73 = 'SI'

        return True

    def setRelatedDocumentTypes(self, cr, uid, invoice, body,
                                context=None):
        linecount = 1
        for line in invoice.invoice_line:
            for related_document in line.related_documents:
                doc_type = RELATED_DOCUMENT_TYPES[related_document.type]
                documento = DatiDocumentiCorrelatiType()
                if related_document.name:
                    documento.IdDocumento = related_document.name
                if related_document.lineRef:
                    documento.RiferimentoNumeroLinea.append(linecount)
                if related_document.date:
                    documento.Data = related_document.date
                if related_document.numitem:
                    documento.NumItem = related_document.numitem
                if related_document.code:
                    documento.CodiceCommessaConvenzione = related_document.code
                if related_document.cup:
                    documento.CodiceCUP = related_document.cup
                if related_document.cig:
                    documento.CodiceCIG = related_document.cig
                getattr(body.DatiGenerali, doc_type).append(documento)
            linecount += 1
        for related_document in invoice.related_documents:
            doc_type = RELATED_DOCUMENT_TYPES[related_document.type]
            documento = DatiDocumentiCorrelatiType()
            if related_document.name:
                documento.IdDocumento = related_document.name
            if related_document.date:
                documento.Data = related_document.date
            if related_document.numitem:
                documento.NumItem = related_document.numitem
            if related_document.code:
                documento.CodiceCommessaConvenzione = related_document.code
            if related_document.cup:
                documento.CodiceCUP = related_document.cup
            if related_document.cig:
                documento.CodiceCIG = related_document.cig
            getattr(body.DatiGenerali, doc_type).append(documento)
        return True

    def setDatiTrasporto(self, cr, uid, invoice, body, context=None):
        if context is None:
            context = {}

        return True
    def setDatiDDT(self, cr, uid, invoice, body, context=None):
        #res = super(WizardExportFatturapa, self).setDatiDDT(
        #    invoice, body)
        if context.get('fpa_export_id',None):
            if hasattr(context.get('fpa_export_id',None), '__iter__'):
                fpa_export_id=context.get('fpa_export_id',None)[0]
            else:
                fpa_export_id=context.get('fpa_export_id',None)
            This=self.pool.get('wizard.export.fatturapa').browse(cr,uid,fpa_export_id,context=context)
        else:
            return True    
        if This.include_ddt_data == 'dati_ddt':
        #if self.include_ddt_data == 'dati_ddt':
            inv_lines_by_ddt = {}
            for line in invoice.invoice_line:
                for move_line_id in line.move_line_ids:
                    for ddt_id  in move_line_id.picking_id.ddt_ids:
                        if (
                            ddt_id.ddt_number and
                            ddt_id.date
                        ):
                            key = (
                                ddt_id.ddt_number,
                                ddt_id.date[:10]
                            )
                            if key not in inv_lines_by_ddt:
                                inv_lines_by_ddt[key] = []
                            inv_lines_by_ddt[key].append(line.ftpa_line_number)
            for key in sorted(inv_lines_by_ddt.iterkeys()):
                DatiDDT = DatiDDTType(
                    NumeroDDT=key[0],
                    DataDDT=key[1]
                )
                for line_number in inv_lines_by_ddt[key]:
                    DatiDDT.RiferimentoNumeroLinea.append(line_number)
                body.DatiGenerali.DatiDDT.append(DatiDDT)
        #elif self.include_ddt_data == 'dati_trasporto':
        elif This.include_ddt_data == 'dati_trasporto':
                for ddt_id in invoice.x_pack_ids:
                    body.DatiGenerali.DatiTrasporto = DatiTrasportoType(
                        MezzoTrasporto=ddt_id.transportation_method_id.name or None,
                        CausaleTrasporto=ddt_id.transportation_reason_id.name or None,
                        NumeroColli=ddt_id.parcels or None,
                        Descrizione=ddt_id.goods_description_id.name or None,
                        PesoLordo='%.2f' % ddt_id.weight,
                        PesoNetto='%.2f' % ddt_id.net_weight,
                        TipoResa= None
                    )
                    if ddt_id.carrier_id:
                        if not ddt_id.carrier_id.vat:
                            raise orm.except_orm(
                                _('Error!'),  _('TIN not set for %s') % ddt_id.carrier_id.name)
                        body.DatiGenerali.DatiTrasporto.DatiAnagraficiVettore = (
                            DatiAnagraficiVettoreType())
                        if ddt_id.carrier_id.fiscalcode:
                            body.DatiGenerali.DatiTrasporto.DatiAnagraficiVettore.\
                                CodiceFiscale = ddt_id.carrier_id.fiscalcode
                        body.DatiGenerali.DatiTrasporto.DatiAnagraficiVettore.\
                            IdFiscaleIVA = IdFiscaleType(
                                IdPaese=ddt_id.carrier_id.vat[0:2],
                                IdCodice=ddt_id.carrier_id.vat[2:]
                            )
                        body.DatiGenerali.DatiTrasporto.DatiAnagraficiVettore.\
                            Anagrafica = AnagraficaType(
                                Denominazione=ddt_id.carrier_id.name)
        return True
    
    def price_tax_include_to_exclude(self, cr, uid, tax_id, price_unit,price_subtotal, quantity,context=None):
        """
        :param force_excluded: boolean used to say that we don't want to consider the value of field price_include of
            tax. It's used in encoding by line where you don't matter if you encoded a tax with that boolean to True or
            False
        RETURN: {
                'total': 0.0,                # Total without taxes
                'total_included: 0.0,        # Total with taxes
                'taxes': []                  # List of taxes, see compute for the format
            }
        """

        # By default, for each tax, tax amount will first be computed
        # and rounded at the 'Account' decimal precision for each
        # PO/SO/invoice line and then these rounded amounts will be
        # summed, leading to the total amount for that tax. But, if the
        # company has tax_calculation_rounding_method = round_globally,
        # we still follow the same method, but we use a much larger
        # precision when we round the tax amount for each line (we use
        # the 'Account' decimal precision + 5), and that way it's like
        # rounding after the sum of the tax amounts of each line
        precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'Product Price')
        if precision < 2:
            precision = 2
        if tax_id.price_include==False:
            price_float=price_unit*(10**precision)
            price_int=float(int(price_unit*(10**precision)))
            diff=price_float-price_int
            if diff>0:
                tax_compute_precision = precision+1
                if diff*10-float(int(diff*10))>0:
                        tax_compute_precision += 1

            else:
                tax_compute_precision = precision                    
            return {'price_unit':price_unit,'precision':tax_compute_precision}
        precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'Product Price')
        tax_compute_precision = precision+1
        price_unit_tax_exclude10=(price_subtotal/quantity)*(10**tax_compute_precision)
        price_round10=int(price_unit_tax_exclude10)
        diff_round=price_unit_tax_exclude10-price_round10
        if diff_round>=0.51:
            price_round10=price_round10+1
            price_result=float(price_round10)/(10**tax_compute_precision)
        else:
            price_round10=price_round10
            price_result=float(price_round10)/(10**tax_compute_precision)
            if diff_round>0.11:
                tax_compute_precision=precision+1
            else:
                tax_compute_precision=precision
        return {'price_unit':price_result,'precision':tax_compute_precision}
    def setDettaglioLinee(self, cr, uid, invoice, body, context=None):
        if context is None:
            context = {}

        body.DatiBeniServizi = DatiBeniServiziType()
        # TipoCessionePrestazione not handled

        # TODO CodiceArticolo

        line_no = 1
        price_precision = self.pool.get('decimal.precision').precision_get(cr,uid,
            'Product Price')
        if price_precision < 2:
            # XML wants at least 2 decimals always
            price_precision = 2
        uom_precision = self.pool.get('decimal.precision').precision_get(cr,uid,
            'Product Unit of Measure')
        if uom_precision < 2:
            uom_precision = 2
        for line in invoice.invoice_line:
            if not line.invoice_line_tax_id:
                raise orm.except_orm(
                    _('Error'),
                    _("Invoice line %s does not have tax") % line.name)
            if len(line.invoice_line_tax_id) > 1:
                raise orm.except_orm(
                    _('Error'),
                    _("Too many taxes for invoice line %s") % line.name)
            aliquota = line.invoice_line_tax_id[0].amount*100
            price_unit=self.price_tax_include_to_exclude(cr,uid,line.invoice_line_tax_id[0],line.price_unit,line.price_subtotal,line.quantity,context=context)
            Quantita=('%.' + str(
                uom_precision
            ) + 'f') % line.quantity

            AliquotaIVA = '%.2f' % (aliquota)
            PrezzoUnitario=('%.' + str(
                    price_unit['precision']
                ) + 'f') % price_unit['price_unit']
            PrezzoTotale='%.2f' % line.price_subtotal
            DettaglioLinea = DettaglioLineeType(
                NumeroLinea=str(line_no),
                Descrizione=line.name.replace('#',' '),
                #PrezzoUnitario='%.2f' % price_unit['price_unit'] if price_unit['precision']<=2 else  '%.3f' % price_unit['price_unit'],              
                PrezzoUnitario=PrezzoUnitario,
                #Quantita='%.2f' % line.quantity,
                Quantita=Quantita,                
                UnitaMisura=line.uos_id and (
                    unidecode(line.uos_id.name)) or None,
                PrezzoTotale=PrezzoTotale,
                AliquotaIVA=AliquotaIVA)
            if line.discount:
                Percentuale='%.2f' % line.discount
                ScontoMaggiorazione = ScontoMaggiorazioneType(
                    Tipo='SC',
                    Percentuale=Percentuale
                )
                DettaglioLinea.ScontoMaggiorazione.append(ScontoMaggiorazione)
            if aliquota == 0.0:
                if not line.invoice_line_tax_id[0].non_taxable_nature:
                    raise orm.except_orm(
                        _('Error'),
                        _("No 'nature' field for tax %s") %
                        line.invoice_line_tax_id[0].name)
                DettaglioLinea.Natura = line.invoice_line_tax_id[
                    0
                ].kind_id.code
            if line.admin_ref:
                DettaglioLinea.RiferimentoAmministrazione = line.admin_ref
            line.write({'ftpa_line_number':line_no})
            line_no += 1

            # not handled

            # el.remove(el.find('DataInizioPeriodo'))
            # el.remove(el.find('DataFinePeriodo'))
            # el.remove(el.find('Ritenuta'))
            # el.remove(el.find('AltriDatiGestionali'))

            body.DatiBeniServizi.DettaglioLinee.append(DettaglioLinea)

        return True

    def setDatiRiepilogo(self, cr, uid, invoice, body, context=None):
        if context is None:
            context = {}
        tax_pool = self.pool['account.tax']
        for tax_line in invoice.tax_line:
            tax_id = self.pool['account.tax'].get_tax_by_invoice_tax(
                cr, uid, tax_line.name, context=context)
            tax = tax_pool.browse(cr, uid, tax_id, context=context)
            AliquotaIVA='%.2f' % (tax.amount * 100)
            ImponibileImporto='%.2f' % tax_line.base
            Imposta='%.2f' % tax_line.amount
            
            riepilogo = DatiRiepilogoType(
                AliquotaIVA=AliquotaIVA,
                ImponibileImporto=ImponibileImporto,
                Imposta=Imposta
                )
            if tax.amount == 0.0:
                if not tax.kind_id:
                    raise orm.except_orm(
                        _('Error'),
                        _("No 'nature' field for tax %s") % tax.name)
                riepilogo.Natura = tax.kind_id.code
                if not tax.law_reference:
                    raise orm.except_orm(
                        _('Error'),
                        _("No 'law reference' field for tax %s") % tax.name)
                riepilogo.RiferimentoNormativo = tax.law_reference
            if tax.payability:
                riepilogo.EsigibilitaIVA = tax.payability
            # TODO

            # el.remove(el.find('SpeseAccessorie'))
            # el.remove(el.find('Arrotondamento'))

            body.DatiBeniServizi.DatiRiepilogo.append(riepilogo)

        return True

    def setDatiPagamento(self, cr, uid, invoice, body, context=None):
        if context is None:
            context = {}
        if invoice.payment_term:
            DatiPagamento = DatiPagamentoType()
            if not invoice.payment_term.fatturapa_pt_id:
                raise orm.except_orm(
                    _('Error'),
                    _('Payment term %s does not have a linked fatturaPA '
                      'payment term') % invoice.payment_term.name)
            if not invoice.payment_term.fatturapa_pm_id:
                raise orm.except_orm(
                    _('Error'),
                    _('Payment term %s does not have a linked fatturaPA '
                      'payment method') % invoice.payment_term.name)
            DatiPagamento.CondizioniPagamento = (
                invoice.payment_term.fatturapa_pt_id.code)
            move_line_pool = self.pool['account.move.line']
            invoice_pool = self.pool['account.invoice']
            payment_line_ids = invoice_pool.move_line_id_payment_get(
                cr, uid, [invoice.id])
            for move_line_id in payment_line_ids:
                move_line = move_line_pool.browse(
                    cr, uid, move_line_id, context=context)
                ImportoPagamento = '%.2f' % move_line.debit
                DettaglioPagamento = DettaglioPagamentoType(
                    ModalitaPagamento=(
                        invoice.payment_term.fatturapa_pm_id.code),
                    DataScadenzaPagamento=move_line.date_maturity,
                    ImportoPagamento=ImportoPagamento
                    )
                if invoice.partner_bank_id:
                    DettaglioPagamento.IstitutoFinanziario = (
                        invoice.partner_bank_id.bank_name)
                    if invoice.partner_bank_id.acc_number:
                        if len(invoice.partner_bank_id.acc_number)>10:
                            DettaglioPagamento.IBAN = (
                                ''.join(invoice.partner_bank_id.acc_number.split())
                                )
                    if invoice.partner_bank_id.bank_bic:
                        DettaglioPagamento.BIC = (
                            invoice.partner_bank_id.bank_bic)
                    if invoice.partner_bank_id.bank.abi:
                        DettaglioPagamento.ABI = (
                            invoice.partner_bank_id.bank.abi)
                    if invoice.partner_bank_id.bank.cab:
                        DettaglioPagamento.CAB = (
                            invoice.partner_bank_id.bank.cab)
                DatiPagamento.DettaglioPagamento.append(DettaglioPagamento)
            body.DatiPagamento.append(DatiPagamento)
        return True

    def setAttachments(self, cr, uid, invoice, body, context=None):
        if context is None:
            context = {}
        if invoice.fatturapa_doc_attachments:
            for doc_id in invoice.fatturapa_doc_attachments:
                AttachDoc = AllegatiType(
                    NomeAttachment=doc_id.datas_fname,
                    Attachment=doc_id.datas
                )
                body.Allegati.append(AttachDoc)
        return True

    def setFatturaElettronicaHeader(self, cr, uid, company,
                                    partner, context=None):
        if context is None:
            context = {}
        self.fatturapa.FatturaElettronicaHeader = (
            FatturaElettronicaHeaderType())
        self.setDatiTrasmissione(cr, uid, company, partner, context=context)
        self.setCedentePrestatore(cr, uid, company, context=context)
        self.setRappresentanteFiscale(cr, uid, company, context=context)
        self.setCessionarioCommittente(
            cr, uid, partner, context=context)
        self.setTerzoIntermediarioOSoggettoEmittente(
            cr, uid, company, context=context)
        self.setSoggettoEmittente(cr, uid, context=context)

    def setFatturaElettronicaBody(
        self, cr, uid, inv, FatturaElettronicaBody, context=None
    ):
        if context is None:
            context = {}

        self.setDatiGeneraliDocumento(
            cr, uid, inv, FatturaElettronicaBody, context=context)
        self.setRelatedDocumentTypes(cr, uid, inv, FatturaElettronicaBody,
                                     context=context)
        self.setDettaglioLinee(
            cr, uid, inv, FatturaElettronicaBody, context=context)

        self.setDatiDDT(cr, uid,inv, FatturaElettronicaBody, context=context)

        self.setDatiTrasporto(cr, uid,inv, FatturaElettronicaBody, context=context)

        self.setDatiRiepilogo(
            cr, uid, inv, FatturaElettronicaBody, context=context)
        self.setDatiPagamento(
            cr, uid, inv, FatturaElettronicaBody, context=context)
        self.setAttachments(
            cr, uid, inv, FatturaElettronicaBody, context=context)

    def getPartnerId(self, cr, uid, invoice_ids, context=None):
        if context is None:
            context = {}

        invoice_model = self.pool['account.invoice']
        partner = False

        invoices = invoice_model.browse(cr, uid, invoice_ids, context=context)

        for invoice in invoices:
            if not partner:
                partner = invoice.partner_id
            if invoice.partner_id != partner:
                raise orm.except_orm(
                    _('Error!'),
                    _('Invoices must belong to the same partner'))

        return partner

    def exportFatturaPA(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        # self.setNameSpace()

        model_data_obj = self.pool['ir.model.data']
        invoice_obj = self.pool['account.invoice']

        invoice_ids = context.get('active_ids', False)
        ###
        #partner = self.getPartnerId(cr, uid, invoice_ids, context=context)
        """
        tup_invoice_ids=tuple(invoice_ids)
        cr.execute('select id from account_invoice where id in (%s) order by partner_id,id',(tup_invoice_ids,))
        invoice_ids=cr.fetchall()
        """
        inv_pa=[]
        user_obj = self.pool['res.users']
        company = user_obj.browse(cr, uid, uid).company_id
        context.update({'fpa_export_id':ids})
        context_partner = context.copy()
        try:
            for invoice_id in invoice_ids:
                inv = invoice_obj.browse(
                    cr, uid, invoice_id, context=context_partner)
                context_partner.update({'lang': inv.partner_id.lang})
                #if inv.partner_id.ipa_code!='0000000':
                #    self.fatturapa = FatturaElettronica(versione='FPA12')
                #else:
                if inv.partner_id.ipa_code:
                     if len(inv.partner_id.ipa_code)>6:
                        self.fatturapa = FatturaElettronica(versione='FPR12')
                     else:
                        self.fatturapa = FatturaElettronica(versione='FPA12')
                else:
                        self.fatturapa = FatturaElettronica(versione='FPR12')

                if inv.partner_id.is_company:
                    partner_id=inv.partner_id
                else:
                    partner_id=inv.partner_id.parent_id
                self.setFatturaElettronicaHeader(cr, uid, company,partner_id, context=context_partner)
                if inv.fatturapa_attachment_out_id:
                        raise orm.except_orm(
                            _("Error"),
                            _("Invoice %s has FatturaPA Export File yet") % (
                                inv.number))
                invoice_body = FatturaElettronicaBodyType()
                self.setFatturaElettronicaBody(
                        cr, uid, inv, invoice_body, context=context_partner)
                self.fatturapa.FatturaElettronicaBody.append(invoice_body)
                    # TODO DatiVeicoli
    
                self.setProgressivoInvio(cr, uid, context=context)
                attach_id = self.saveAttachment(cr, uid, context=context)
                inv_pa.append(attach_id)
                inv.write({'fatturapa_attachment_out_id': attach_id})
                
        except (SimpleFacetValueError, SimpleTypeValueError) as e:
            raise orm.except_orm(
                _("XML SDI validation error"),
                (unicode(e)))


        if len(inv_pa)<2:
            view_rec = model_data_obj.get_object_reference(
                cr, uid, 'l10n_it_fatturapa_out',
                'view_fatturapa_out_attachment_form')
            if view_rec:
                view_id = view_rec and view_rec[1] or False
        else:
            view_tree = model_data_obj.get_object_reference(
                cr, uid, 'prof_fatturapa_out',
                'view_fatturapa_out_attachment_tree_prof')
            if view_tree:
                view_id = view_tree and view_tree[1] or False

        return {
           'domain': "[('id','in',["+','.join(map(str, inv_pa))+"])]",
            'name': "Export FatturaPA",
            'view_id': None,
            'res_id': None, #inv_pa[0] if len(inv_pa)<2 else None,
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'fatturapa.attachment.out',
            'type': 'ir.actions.act_window',
            'context': context
            }
