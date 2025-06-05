# -*- coding: utf-8 -*-
# Copyright 2014 Davide Corio
# Copyright 2015-2016 Lorenzo Battistini - Agile Business Group
# Copyright 2018 Gianmarco Conte, Marco Calcagni - Dinamiche Aziendali srl
# Copyright 2018 Sergio Corato
# Copyright 2019 Alex Comba - Agile Business Group

import base64
import logging
import os


import openerp
from openerp import fields, models, api, _
from openerp.exceptions import Warning as UserError
from openerp.addons.l10n_it_account.tools.account_tools import encode_for_export
from openerp.tools.safe_eval import safe_eval
import time

from openerp.addons.l10n_it_fatturapa.bindings.fatturapa_v_1_2 import (
    FatturaElettronica,
    FatturaElettronicaHeaderType,
    DatiTrasmissioneType,
    IdFiscaleType,
    ContattiTrasmittenteType,
    CedentePrestatoreType,
    AnagraficaType,
    IndirizzoType,
    IscrizioneREAType,
    CessionarioCommittenteType,
    RappresentanteFiscaleType,
    DatiAnagraficiCedenteType,
    DatiAnagraficiCessionarioType,
    DatiAnagraficiRappresentanteType,
    TerzoIntermediarioSoggettoEmittenteType,
    DatiAnagraficiTerzoIntermediarioType,
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
    ScontoMaggiorazioneType,
    CodiceArticoloType,
    DatiDDTType,
    DatiTrasportoType,
    DatiAnagraficiVettoreType,

)
from openerp.addons.l10n_it_fatturapa.models.account import (
    RELATED_DOCUMENT_TYPES)

_logger = logging.getLogger(__name__)

try:
    from unidecode import unidecode
    from pyxb.exceptions_ import SimpleFacetValueError, SimpleTypeValueError
except ImportError as err:
    _logger.debug(err)


from openerp.osv import orm,fields as orm_fields
class wizard_show_Fatturapa(orm.TransientModel):
    _name = "wizard.show.fatturapa"
    _description = "show FatturaPA"
    _columns = {
        'name':orm_fields.char('name', size=64, required=False, readonly=False),
        'fatturapa_html': orm_fields.html('Fatturapa html', readonly=True, translate=True, sanitize=True, help="Rich-text/HTML version of the message (placeholders may be used here)"),
        'fatturapa':orm_fields.binary('Fatturapa download', filters=None, readonly=True),     
        'fatturapa_name':orm_fields.char(size=64, required=False, readonly=False),     
                    }
    
    _defaults = {  
        'name': str(lambda *a: time.strftime('%Y-%m-%d')),  
        }


class WizardExportFatturapa(models.TransientModel):
    _inherit = 'wizard.export.fatturapa' 
    #_name = "wizard.export.fatturapa"
    #_description = "Export E-invoice"

    
    include_ddt_data= fields.Selection([
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
             'inserire informazioni relative al trasporto',default='normale'
    )
    fiscal_document_type_id = fields.Many2one(
            'fiscal.document.type', 'Forza tipo Documento Fiscale',
            )

    def saveAttachment(self, fatturapa, number):

        company = self.env.user.company_id

        if not company.vat:
            raise UserError(
                _('Company %s TIN not set.') % company.name)
        if (company.fatturapa_sender_partner and
                not company.fatturapa_sender_partner.vat):
            raise UserError(
                _('Partner %s TIN not set.')
                % company.fatturapa_sender_partner.name
            )
        vat = company.vat
        if company.fatturapa_sender_partner:
            vat = company.fatturapa_sender_partner.vat
        vat = vat.replace(' ', '').replace('.', '').replace('-', '')
        attach_obj = self.env['fatturapa.attachment.out']
        #print 'fatturapa.toxml("UTF-8")',fatturapa.toxml("UTF-8")
        attach_vals = {
            'name': '%s_%s.xml' % (vat, str(number)),
            'datas_fname': '%s_%s.xml' % (vat, str(number)),
            'datas': base64.encodestring(fatturapa.toxml("UTF-8")),
        }
        return attach_obj.create(attach_vals)

    def setProgressivoInvio(self, fatturapa):

        company = self.env.user.company_id
        fatturapa_sequence = company.fatturapa_sequence_id
        if not fatturapa_sequence:
            raise UserError(
                _('E-invoice sequence not configured.'))
        number = fatturapa_sequence.next_by_id(fatturapa_sequence.id)
        try:
            fatturapa.FatturaElettronicaHeader.DatiTrasmissione. \
                ProgressivoInvio = number
        except (SimpleFacetValueError, SimpleTypeValueError) as e:
            msg = _(
                'FatturaElettronicaHeader.DatiTrasmissione.'
                'ProgressivoInvio:\n%s'
            ) % unicode(e)
            raise UserError(msg)
        return number

    def _setIdTrasmittente(self, company, fatturapa):

        if not company.country_id:
            raise UserError(
                _('Company Country not set.'))
        if  hasattr(company, 'partner_id'):
                
            IdPaese = company.country_id.code
            IdCodice = company.partner_id.fiscalcode
        else:
            IdPaese = company.country_id.code
            IdCodice = company.fiscalcode
        if not IdCodice:
            if company.vat:
                IdCodice = company.vat[2:]
        if not IdCodice:
            raise UserError(
                _('Company does not have fiscal code or VAT'))
        fatturapa.FatturaElettronicaHeader.DatiTrasmissione. \
            IdTrasmittente = IdFiscaleType(
                IdPaese=IdPaese, IdCodice=IdCodice)
        return True

    def _setFormatoTrasmissione(self, partner, fatturapa):
        if partner.is_pa:
            fatturapa.FatturaElettronicaHeader.DatiTrasmissione. \
                FormatoTrasmissione = 'FPA12'
        else:
            fatturapa.FatturaElettronicaHeader.DatiTrasmissione. \
                FormatoTrasmissione = 'FPR12'

        return True

    def _setCodiceDestinatario(self, partner, fatturapa):
        pec_destinatario = None
        if partner.is_pa:
            if not partner.ipa_code:
                raise UserError(_(
                    "Partner %s is PA but does not have IPA code"
                ) % partner.name)
            code = partner.ipa_code
        else:
            if not partner.codice_destinatario:
                raise UserError(_(
                    "Partner %s is not PA but does not have Codice "
                    "Destinatario"
                ) % partner.name)
            code = partner.codice_destinatario
            if code == '0000000':
                pec_destinatario = partner.pec_destinatario
        fatturapa.FatturaElettronicaHeader.DatiTrasmissione. \
            CodiceDestinatario = code.upper()
        if pec_destinatario:
            fatturapa.FatturaElettronicaHeader.DatiTrasmissione. \
                PECDestinatario = pec_destinatario

        return True

    def _setContattiTrasmittente(self, company, fatturapa):

        if not company.phone:
            raise UserError(
                _('Company Telephone number not set.'))
        Telefono = company.phone

        if not company.email:
            raise UserError(
                _('Email address not set.'))
        Email = company.email
        fatturapa.FatturaElettronicaHeader.DatiTrasmissione. \
            ContattiTrasmittente = ContattiTrasmittenteType(
                Telefono=Telefono, Email=Email)

        return True

    def setDatiTrasmissione(self, company, partner, fatturapa):
        fatturapa.FatturaElettronicaHeader.DatiTrasmissione = (
            DatiTrasmissioneType())
        self._setIdTrasmittente(company, fatturapa)
        self._setFormatoTrasmissione(partner.commercial_partner_id, fatturapa)
        self._setCodiceDestinatario(partner.commercial_partner_id, fatturapa)
        self._setContattiTrasmittente(company, fatturapa)

    def _setDatiAnagraficiCedente(self, CedentePrestatore, company):

        if not company.vat:
            raise UserError(
                _('TIN not set.'))
        CedentePrestatore.DatiAnagrafici = DatiAnagraficiCedenteType()
        if hasattr(company, 'partner_id'):
            fatturapa_fp = company.fatturapa_fiscal_position_id
        else:
            fatturapa_fp = company.company_id.fatturapa_fiscal_position_id
        if not fatturapa_fp:
            raise UserError(_(
                'Fiscal position for Electronic Invoice not set '
                'for company %s. '
                '(Go to Accounting --> Configuration --> Settings --> '
                'Electronic Invoice)' % company.name
            ))
        CedentePrestatore.DatiAnagrafici.IdFiscaleIVA = IdFiscaleType(
            IdPaese=company.country_id.code, IdCodice=company.vat[2:])
        CedentePrestatore.DatiAnagrafici.Anagrafica = AnagraficaType(
            Denominazione=company.name)

        if hasattr(company, 'partner_id'):
    
            if company.partner_id.fiscalcode:
                CedentePrestatore.DatiAnagrafici.CodiceFiscale = (
                    company.partner_id.fiscalcode)
        else:
            if company.fiscalcode:
                CedentePrestatore.DatiAnagrafici.CodiceFiscale = (
                    company.fiscalcode)
            
        CedentePrestatore.DatiAnagrafici.RegimeFiscale = fatturapa_fp.code
        return True

    def _setAlboProfessionaleCedente(self, CedentePrestatore, company):
        # TODO Albo professionale, for now the main company is considered
        # to be a legal entity and not a single person
        # 1.2.1.4   <AlboProfessionale>
        # 1.2.1.5   <ProvinciaAlbo>
        # 1.2.1.6   <NumeroIscrizioneAlbo>
        # 1.2.1.7   <DataIscrizioneAlbo>
        return True

    def _setSedeCedente(self, CedentePrestatore, company):

        if not company.street:
            raise UserError(
                _('Your company Street not set.'))
        if not company.zip:
            raise UserError(
                _('Your company ZIP not set.'))
        if not company.city:
            raise UserError(
                _('Your company City not set.'))
        if not company.country_id:
            raise UserError(
                _('Your company Country not set.'))
        # TODO: manage address number in <NumeroCivico>
        # see https://github.com/OCA/partner-contact/pull/96
        CedentePrestatore.Sede = IndirizzoType(
            Indirizzo=encode_for_export(company.street, 60),
            CAP=company.zip,
            Comune=encode_for_export(company.city, 60),
            Nazione=company.country_id.code)
        if hasattr(company, 'partner_id'):
            if company.partner_id.state_id:
                CedentePrestatore.Sede.Provincia = company.partner_id.state_id.code
            else:
                CedentePrestatore.Sede.Provincia = company.state_id.code
                

        return True

    def _setStabileOrganizzazione(self, CedentePrestatore, company):
        if hasattr(company, 'partner_id'):
            company=company
        else:
            company=company.company_id
            

        if company.fatturapa_stabile_organizzazione:
            stabile_organizzazione = company.fatturapa_stabile_organizzazione
            if not stabile_organizzazione.street:
                raise UserError(
                    _('Street not set for %s') % stabile_organizzazione.name)
            if not stabile_organizzazione.zip:
                raise UserError(
                    _('ZIP not set for %s') % stabile_organizzazione.name)
            if not stabile_organizzazione.city:
                raise UserError(
                    _('City not set for %s') % stabile_organizzazione.name)
            if not stabile_organizzazione.country_id:
                raise UserError(
                    _('Country not set for %s') % stabile_organizzazione.name)
            CedentePrestatore.StabileOrganizzazione = IndirizzoType(
                Indirizzo=stabile_organizzazione.street,
                CAP=stabile_organizzazione.zip,
                Comune=stabile_organizzazione.city,
                Nazione=stabile_organizzazione.country_id.code)
            if stabile_organizzazione.state_id:
                CedentePrestatore.StabileOrganizzazione.Provincia = (
                    stabile_organizzazione.state_id.code)
        return True

    def _setRea(self, CedentePrestatore, company):
        if hasattr(company, 'partner_id'):
            company=company
        else:
            company=company.company_id

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

    def _setContatti(self, CedentePrestatore, company):
        if hasattr(company, 'partner_id'):
            company=company.partner_id
            
        CedentePrestatore.Contatti = ContattiType(
            Telefono=company.phone or None,
            Fax=company.fax or None,
            Email=company.email or None
        )

    def _setPubAdministrationRef(self, CedentePrestatore, company):
        if hasattr(company, 'partner_id'):
            company=company
        else:
            company=company.company_id

        if company.fatturapa_pub_administration_ref:
            CedentePrestatore.RiferimentoAmministrazione = (
                company.fatturapa_pub_administration_ref)

    def setCedentePrestatore(self, company, fatturapa):
        fatturapa.FatturaElettronicaHeader.CedentePrestatore = (
            CedentePrestatoreType())
        self._setDatiAnagraficiCedente(
            fatturapa.FatturaElettronicaHeader.CedentePrestatore,
            company)
        self._setSedeCedente(
            fatturapa.FatturaElettronicaHeader.CedentePrestatore,
            company)
        self._setAlboProfessionaleCedente(
            fatturapa.FatturaElettronicaHeader.CedentePrestatore,
            company)
        self._setStabileOrganizzazione(
            fatturapa.FatturaElettronicaHeader.CedentePrestatore,
            company)
        # TODO: add Contacts
        self._setRea(
            fatturapa.FatturaElettronicaHeader.CedentePrestatore,
            company)
        self._setContatti(
            fatturapa.FatturaElettronicaHeader.CedentePrestatore,
            company)
        self._setPubAdministrationRef(
            fatturapa.FatturaElettronicaHeader.CedentePrestatore,
            company)

    def _setDatiAnagraficiCessionario(self, partner, fatturapa):
        fatturapa.FatturaElettronicaHeader.CessionarioCommittente.\
            DatiAnagrafici = DatiAnagraficiCessionarioType()
        if not partner.vat and not partner.fiscalcode:
            if (
                    partner.codice_destinatario == 'XXXXXXX'
                    and partner.country_id.code
                    and partner.country_id.code != 'IT'
            ):
                # SDI accepts missing VAT for foreign customers by setting a
                # fake IdCodice and a valid IdPaese
                # Otherwise raise error if we have no VAT# and no Fiscal code
                fatturapa.FatturaElettronicaHeader.CessionarioCommittente.\
                    DatiAnagrafici.IdFiscaleIVA = IdFiscaleType(
                        IdPaese=partner.country_id.code,
                        IdCodice='99999999999')
            else:
                raise UserError(
                    _('VAT number and fiscal code are not set for %s.') %
                    partner.name)
        if partner.fiscalcode:
            fatturapa.FatturaElettronicaHeader.CessionarioCommittente. \
                DatiAnagrafici.CodiceFiscale = partner.fiscalcode
        if partner.vat:
            fatturapa.FatturaElettronicaHeader.CessionarioCommittente. \
                DatiAnagrafici.IdFiscaleIVA = IdFiscaleType(
                    IdPaese=partner.vat[0:2], IdCodice=partner.vat[2:])
        if partner.is_company:
            fatturapa.FatturaElettronicaHeader.CessionarioCommittente. \
                DatiAnagrafici.Anagrafica = AnagraficaType(
                    Denominazione=encode_for_export(partner.name, 80))
        else:
            if not partner.lastname or not partner.firstname:
                raise UserError(
                    _("Partner %s deve avere nome e cognome") % partner.name)
            fatturapa.FatturaElettronicaHeader.CessionarioCommittente. \
                DatiAnagrafici.Anagrafica = AnagraficaType(
                    Cognome=encode_for_export(partner.lastname, 60),
                    Nome=encode_for_export(partner.firstname, 60))

        if partner.eori_code:
            fatturapa.FatturaElettronicaHeader.CessionarioCommittente. \
                DatiAnagrafici.Anagrafica.CodEORI = partner.eori_code

        return True

    def _setDatiAnagraficiRappresentanteFiscale(self, partner, fatturapa):
        fatturapa.FatturaElettronicaHeader.RappresentanteFiscale = (
            RappresentanteFiscaleType())
        fatturapa.FatturaElettronicaHeader.RappresentanteFiscale. \
            DatiAnagrafici = DatiAnagraficiRappresentanteType()
        if not partner.vat and not partner.fiscalcode:
            raise UserError(
                _('VAT and Fiscalcode not set for %s') % partner.name)
        if partner.fiscalcode:
            fatturapa.FatturaElettronicaHeader.RappresentanteFiscale. \
                DatiAnagrafici.CodiceFiscale = partner.fiscalcode
        if partner.vat:
            fatturapa.FatturaElettronicaHeader.RappresentanteFiscale. \
                DatiAnagrafici.IdFiscaleIVA = IdFiscaleType(
                    IdPaese=partner.vat[0:2], IdCodice=partner.vat[2:])
        fatturapa.FatturaElettronicaHeader.RappresentanteFiscale. \
            DatiAnagrafici.Anagrafica = AnagraficaType(
                Denominazione=encode_for_export(partner.name, 80))
        if partner.eori_code:
            fatturapa.FatturaElettronicaHeader.RappresentanteFiscale. \
                DatiAnagrafici.Anagrafica.CodEORI = partner.eori_code

        return True

    def _setTerzoIntermediarioOSoggettoEmittente(self, partner, fatturapa):
        fatturapa.FatturaElettronicaHeader. \
            TerzoIntermediarioOSoggettoEmittente = \
            (TerzoIntermediarioSoggettoEmittenteType())
        fatturapa.FatturaElettronicaHeader. \
            TerzoIntermediarioOSoggettoEmittente. \
            DatiAnagrafici = DatiAnagraficiTerzoIntermediarioType()
        if not partner.vat and not partner.fiscalcode:
            raise UserError(
                _('Partner VAT and Fiscalcode not set for %s.' % partner.name))
        if partner.fiscalcode:
            fatturapa.FatturaElettronicaHeader. \
                TerzoIntermediarioOSoggettoEmittente. \
                DatiAnagrafici.CodiceFiscale = partner.fiscalcode
        if partner.vat:
            fatturapa.FatturaElettronicaHeader. \
                TerzoIntermediarioOSoggettoEmittente. \
                DatiAnagrafici.IdFiscaleIVA = IdFiscaleType(
                    IdPaese=partner.vat[0:2],
                    IdCodice=partner.vat[2:])
        fatturapa.FatturaElettronicaHeader. \
            TerzoIntermediarioOSoggettoEmittente. \
            DatiAnagrafici.Anagrafica = \
            AnagraficaType(Denominazione=partner.name)
        if partner.eori_code:
            fatturapa.FatturaElettronicaHeader. \
                TerzoIntermediarioOSoggettoEmittente. \
                DatiAnagrafici.Anagrafica.CodEORI = partner.eori_code
        fatturapa.FatturaElettronicaHeader.SoggettoEmittente = 'TZ'
        return True

    def _setSedeCessionario(self, partner, fatturapa):

        if not partner.street:
            raise UserError(
                _('Customer street not set for %s.' % partner.name))
        if not partner.city:
            raise UserError(
                _('Customer city not set for %s.' % partner.name))
        if not partner.country_id:
            raise UserError(
                _('Customer country not set for %s.' % partner.name))

        # TODO: manage address number in <NumeroCivico>
        if partner.codice_destinatario == 'XXXXXXX':
            fatturapa.FatturaElettronicaHeader.CessionarioCommittente.Sede = (
                IndirizzoType(
                    Indirizzo=encode_for_export(partner.street, 60),
                    CAP='00000',
                    Comune=encode_for_export(partner.city, 60),
                    Provincia='EE',
                    Nazione=partner.country_id.code))
        else:
            if not partner.zip:
                raise UserError(
                    _('Customer ZIP not set for %s.' % partner.name))
            fatturapa.FatturaElettronicaHeader.CessionarioCommittente.Sede = (
                IndirizzoType(
                    Indirizzo=encode_for_export(partner.street, 60),
                    CAP=partner.zip,
                    Comune=encode_for_export(partner.city, 60),
                    Nazione=partner.country_id.code))
            if partner.state_id:
                fatturapa.FatturaElettronicaHeader.CessionarioCommittente.\
                    Sede.Provincia = partner.state_id.code

        return True

    def setRappresentanteFiscale(self, company, fatturapa):
        if hasattr(company, 'partner_id'):
            company=company
        else:
            company=company.company_id

        if company.fatturapa_tax_representative:
            self._setDatiAnagraficiRappresentanteFiscale(
                company.fatturapa_tax_representative, fatturapa)
        return True

    def setCessionarioCommittente(self, partner, fatturapa):
        fatturapa.FatturaElettronicaHeader.CessionarioCommittente = (
            CessionarioCommittenteType())
        self._setDatiAnagraficiCessionario(
            partner.commercial_partner_id, fatturapa)
        self._setSedeCessionario(partner, fatturapa)

    def setTerzoIntermediarioOSoggettoEmittente(self, company, fatturapa):
        if hasattr(company, 'partner_id'):
            company=company
        else:
            company=company.company_id

        if company.fatturapa_sender_partner:
            self._setTerzoIntermediarioOSoggettoEmittente(
                company.fatturapa_sender_partner, fatturapa)
        return True

    def setDatiGeneraliDocumento(self, invoice, body):
        ftpa_doctype_poll = self.pool['fatturapa.document_type']
        This=self
        context=self.env.context
        context = dict(context)
        if context.get('fpa_export_id',None):
            if hasattr(context.get('fpa_export_id',None), '__iter__'):
                fpa_export_id=context.get('fpa_export_id',None)[0]
            else:
                fpa_export_id=context.get('fpa_export_id',None)
            This=self.env['wizard.export.fatturapa'].browse(fpa_export_id)
        else:
            This=self

        # TODO DatiSAL

        body.DatiGenerali = DatiGeneraliType()
        if not invoice.number:
            raise UserError(
                _('Invoice %s does not have a number.' % invoice.display_name))
        TipoDocumento=None
        if invoice.fiscal_document_type_id:
            TipoDocumento = invoice.fiscal_document_type_id.code
        if This.fiscal_document_type_id:
            TipoDocumento = This.fiscal_document_type_id.code
        if not TipoDocumento:
            TipoDocumento = 'TD01'
        if invoice.type == 'out_refund':
            TipoDocumento = 'TD04'
        ImportoTotaleDocumento = invoice.amount_total
        if invoice.split_payment:
            ImportoTotaleDocumento += invoice.amount_sp
            ##ImportoTotaleDocumento_str='%.2f' % ImportoTotaleDocumento
        ImportoTotaleDocumento_str=('%.' + str(
                    2
                ) + 'f') % ImportoTotaleDocumento

        body.DatiGenerali.DatiGeneraliDocumento = DatiGeneraliDocumentoType(
            TipoDocumento=TipoDocumento,
            Divisa=invoice.currency_id.name,
            Data=invoice.date_invoice,
            Numero=invoice.number,
            ImportoTotaleDocumento=ImportoTotaleDocumento_str)

        # TODO: DatiRitenuta, DatiBollo, DatiCassaPrevidenziale,
        # ScontoMaggiorazione, Arrotondamento,

        if invoice.comment:
            # max length of Causale is 200
            caus_list = invoice.comment.split('\n')
            for causale in caus_list:
                if not causale:
                    continue
                causale_list_200 = \
                    [causale[i:i+200] for i in range(0, len(causale), 200)]
                for causale200 in causale_list_200:
                    # Remove non latin chars, but go back to unicode string,
                    # as expected by String200LatinType
                    if len(causale200)<=0:
                        continue
                    causale = encode_for_export(causale200.replace('#',''), 200)
                    body.DatiGenerali.DatiGeneraliDocumento.Causale\
                        .append(causale)

        if invoice.company_id.fatturapa_art73:
            body.DatiGenerali.DatiGeneraliDocumento.Art73 = 'SI'

        return True

    def setRelatedDocumentTypes(self, invoice, body):
        for line in invoice.invoice_line:
            for related_document in line.related_documents:
                doc_type = RELATED_DOCUMENT_TYPES[related_document.type]
                documento = DatiDocumentiCorrelatiType()
                if related_document.name:
                    documento.IdDocumento = related_document.name
                if related_document.lineRef:
                    documento.RiferimentoNumeroLinea.append(
                        line.ftpa_line_number)
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

    def setDatiTrasporto(self, invoice, body):
        return True

    def setDatiDDT(self, invoice, body):
        context=self.env.context
        context = dict(context)
        if context.get('fpa_export_id',None):
            if hasattr(context.get('fpa_export_id',None), '__iter__'):
                fpa_export_id=context.get('fpa_export_id',None)[0]
            else:
                fpa_export_id=context.get('fpa_export_id',None)
            This=self.env['wizard.export.fatturapa'].browse(fpa_export_id)
        else:
            This=self    
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
                                raise UserError(
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

    def _get_prezzo_unitario(self, line):
        res = line.price_unit
        if (line.invoice_line_tax_id and
                line.invoice_line_tax_id[0].price_include):
            res = line.price_unit / (
                1 + line.invoice_line_tax_id[0].amount)
        return res

    def setDettaglioLinee(self, invoice, body):

        body.DatiBeniServizi = DatiBeniServiziType()
        # TipoCessionePrestazione not handled

        line_no = 1
        price_precision = self.env['decimal.precision'].precision_get(
            'Product Price for XML e-invoices')
        if price_precision < 2:
            # XML wants at least 2 decimals always
            price_precision = 2
        uom_precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        if uom_precision < 2:
            uom_precision = 2
        for line in invoice.invoice_line:
            self.setDettaglioLinea(
                line_no, line, body, price_precision, uom_precision)
            line_no += 1

        return True

    def setDettaglioLinea(
            self, line_no, line, body, price_precision, uom_precision):
        if not line.invoice_line_tax_id:
            raise UserError(
                _("Invoice line %s does not have tax") % line.name)
        if len(line.invoice_line_tax_id) > 1:
            raise UserError(
                _("Too many taxes for invoice line %s") % line.name)
        aliquota = line.invoice_line_tax_id[0].amount
        AliquotaIVA = '%.2f' % (aliquota * 100)
        line.ftpa_line_number = line_no
        prezzo_unitario = self._get_prezzo_unitario(line)
        PrezzoUnitario=('%.' + str(
                price_precision
            ) + 'f') % prezzo_unitario
        
        Quantita=('%.' + str(
                uom_precision
            ) + 'f') % line.quantity
        PrezzoTotale='%.2f' % line.price_subtotal
        AliquotaIVA=AliquotaIVA
        DettaglioLinea = DettaglioLineeType(
            NumeroLinea=str(line_no),
            # can't insert newline with pyxb
            # see https://tinyurl.com/ycem923t
            # and '&#10;' would not be correctly visualized anyway
            # (for example firefox replaces '&#10;' with space
            Descrizione=encode_for_export(line.name.replace('\n', ' '), 1000),
            PrezzoUnitario=PrezzoUnitario,
            Quantita=Quantita,
            UnitaMisura=line.uos_id and (
                unidecode(line.uos_id.name)) or None,
            PrezzoTotale=PrezzoTotale,
            AliquotaIVA=AliquotaIVA)
        if line.discount:
            ScontoMaggiorazione = ScontoMaggiorazioneType(
                Tipo='SC',
                Percentuale='%.2f' % line.discount
            )
            DettaglioLinea.ScontoMaggiorazione.append(ScontoMaggiorazione)
        if aliquota == 0.0:
            if not line.invoice_line_tax_id[0].kind_id:
                raise UserError(
                    _("No 'nature' field for tax %s") %
                    line.invoice_line_tax_id[0].name)
            DettaglioLinea.Natura = line.invoice_line_tax_id[
                0
            ].kind_id.code
        if line.admin_ref:
            DettaglioLinea.RiferimentoAmministrazione = line.admin_ref
        if line.product_id:
            if line.product_id.default_code:
                CodiceArticolo = CodiceArticoloType(
                    CodiceTipo=self.env['ir.config_parameter'].sudo(
                    ).get_param('fatturapa.codicetipo.odoo', 'ODOO'),
                    CodiceValore=encode_for_export(
                        line.product_id.default_code, 35, 'ascii')
                )
                DettaglioLinea.CodiceArticolo.append(CodiceArticolo)
            if line.product_id.ean13:
                CodiceArticolo = CodiceArticoloType(
                    CodiceTipo='EAN',
                    CodiceValore=encode_for_export(
                        line.product_id.ean13, 35, 'ascii')
                )
                DettaglioLinea.CodiceArticolo.append(CodiceArticolo)

        print ('dettaglio_linea',DettaglioLinea)
        body.DatiBeniServizi.DettaglioLinee.append(DettaglioLinea)
        return True

    def setDatiRiepilogo(self, invoice, body):
        model_tax = self.env['account.tax']
        if not invoice.tax_line:
            raise UserError(
                _("Invoice {invoice} has no tax lines")
                .format(invoice=invoice.display_name))
        for tax_line in invoice.tax_line:
            tax = model_tax.get_tax_by_invoice_tax(tax_line.name)
            riepilogo = DatiRiepilogoType(
                AliquotaIVA='%.2f' % (tax.amount * 100),
                ImponibileImporto='%.2f' % tax_line.base,
                Imposta='%.2f' % tax_line.amount
            )
            if tax.amount == 0.0:
                if not tax.kind_id:
                    raise UserError(
                        _("No 'nature' field for tax %s") % tax.name)
                riepilogo.Natura = tax.kind_id.code
                if not tax.law_reference:
                    raise UserError(
                        _("No 'law reference' field for tax %s") % tax.name)
                riepilogo.RiferimentoNormativo = encode_for_export(
                    tax.law_reference, 100)
            if tax.payability:
                riepilogo.EsigibilitaIVA = tax.payability
            # TODO

            # el.remove(el.find('SpeseAccessorie'))
            # el.remove(el.find('Arrotondamento'))

            body.DatiBeniServizi.DatiRiepilogo.append(riepilogo)

        return True

    def setDatiPagamento(self, invoice, body):
        if invoice.payment_term:
            payment_line_ids = invoice.move_line_id_payment_get()
            if not payment_line_ids:
                return True

            DatiPagamento = DatiPagamentoType()
            if not invoice.payment_term.fatturapa_pt_id:
                raise UserError(
                    _('Payment term %s does not have a linked e-invoice '
                      'payment term') % invoice.payment_term.name)
            if not invoice.payment_term.fatturapa_pm_id:
                raise UserError(
                    _('Payment term %s does not have a linked e-invoice '
                      'payment method') % invoice.payment_term.name)
            DatiPagamento.CondizioniPagamento = (
                invoice.payment_term.fatturapa_pt_id.code)
            move_line_pool = self.env['account.move.line']
            for move_line_id in payment_line_ids:
                move_line = move_line_pool.browse(move_line_id)
                ImportoPagamento = '%.2f' % (
                    move_line.amount_currency or move_line.debit)
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
                        DettaglioPagamento.IBAN = (
                            ''.join(invoice.partner_bank_id.acc_number.split())
                        )
                    if invoice.partner_bank_id.bank_bic:
                        DettaglioPagamento.BIC = (
                            invoice.partner_bank_id.bank_bic)
                DatiPagamento.DettaglioPagamento.append(DettaglioPagamento)
            body.DatiPagamento.append(DatiPagamento)
        return True

    def setAttachments(self, invoice, body):
        if invoice.fatturapa_doc_attachments:
            for doc_id in invoice.fatturapa_doc_attachments:
                file_name, file_extension = os.path.splitext(doc_id.name)
                attachment_name = doc_id.datas_fname if len(
                    doc_id.datas_fname) <= 60 else ''.join([
                        file_name[:(60-len(file_extension))], file_extension])
                AttachDoc = AllegatiType(
                    NomeAttachment=encode_for_export(attachment_name, 60),
                    Attachment=base64.decodestring(doc_id.datas)
                )
                body.Allegati.append(AttachDoc)
        return True

    def setFatturaElettronicaHeader(self, company, partner, fatturapa):
        fatturapa.FatturaElettronicaHeader = (
            FatturaElettronicaHeaderType())
        self.setDatiTrasmissione(company, partner, fatturapa)
        self.setCedentePrestatore(company, fatturapa)
        self.setRappresentanteFiscale(company, fatturapa)
        self.setCessionarioCommittente(partner, fatturapa)
        self.setTerzoIntermediarioOSoggettoEmittente(company, fatturapa)

    def setFatturaElettronicaBody(self, inv, FatturaElettronicaBody):

        self.setDatiGeneraliDocumento(inv, FatturaElettronicaBody)
        self.setDettaglioLinee(inv, FatturaElettronicaBody)
        self.setDatiDDT(inv, FatturaElettronicaBody)
        self.setDatiTrasporto(inv, FatturaElettronicaBody)
        self.setRelatedDocumentTypes(inv, FatturaElettronicaBody)
        self.setDatiRiepilogo(inv, FatturaElettronicaBody)
        self.setDatiPagamento(inv, FatturaElettronicaBody)
        self.setAttachments(inv, FatturaElettronicaBody)

    def getPartnerId(self, invoice_ids):

        invoice_model = self.env['account.invoice']
        partner = False

        invoices = invoice_model.browse(invoice_ids)

        for invoice in invoices:
            if not partner:
                partner = invoice.partner_id
            if invoice.partner_id != partner:
                raise UserError(
                    _('Invoices %s must belong to the same partner') %
                    invoices.mapped('number'))

        return partner

    def group_invoices_by_partner(self):
        invoice_ids = self.env.context.get('active_ids', False)
        res = {}
        for invoice in self.env['account.invoice'].browse(invoice_ids):
            if invoice.partner_id.is_company:
                    partner_id=invoice.partner_id
            else:
                    partner_id=invoice.partner_id.parent_id
            if partner_id.id not in res:

                #res[invoice.partner_id.id] = []
                res[partner_id.id] = []
            res[partner_id.id].append(invoice.id)
        return res

    @api.multi
    def exportFatturaPA(self):
        invoice_obj = self.env['account.invoice']
        invoices_by_partner = self.group_invoices_by_partner()
        attachments = self.env['fatturapa.attachment.out']
        for partner_id in invoices_by_partner:
            invoice_ids = invoices_by_partner[partner_id]
            #partner = self.getPartnerId(invoice_ids)
            partner = self.env['res.partner'].browse(partner_id)
            if partner.is_pa:
                fatturapa = FatturaElettronica(versione='FPA12')
            else:
                fatturapa = FatturaElettronica(versione='FPR12')
            company = self.env.user.company_id
            svcompany=company
            context_partner = self.env.context.copy()
            context_partner.update({'lang': partner.lang})
            context_partner.update({'fpa_export_id':self.id})
            try:
                self.with_context(context_partner).setFatturaElettronicaHeader(
                    company, partner, fatturapa)
                for invoice_id in invoice_ids:
                    inv = invoice_obj.with_context(context_partner).browse(
                        invoice_id)

                    if inv.fiscal_document_type_id.code in ('TD17','TD18'):
                        if inv.rc_purchase_invoice_id:
                            company=inv.rc_purchase_invoice_id.partner_id
                        else:
                            company=svcompany
                            
                    else:
                        
                        company=svcompany
                        
                    self.with_context(context_partner).setFatturaElettronicaHeader(
                        company, partner, fatturapa)

                    if inv.fatturapa_attachment_out_id:
                        raise UserError(
                            _("Invoice %s has E-invoice Export File yet") % (
                                inv.number))
                    if self.report_print_menu:
                        self.generate_attach_report(inv)
                    invoice_body = FatturaElettronicaBodyType()
                    inv.preventive_checks()
                    self.with_context(
                        context_partner
                    ).setFatturaElettronicaBody(
                        inv, invoice_body)
                    fatturapa.FatturaElettronicaBody.append(invoice_body)
                    # TODO DatiVeicoli

                number = self.setProgressivoInvio(fatturapa)
            except (SimpleFacetValueError, SimpleTypeValueError) as e:
                raise UserError(unicode(e))

            attach = self.saveAttachment(fatturapa, number)
            attachments |= attach

            for invoice_id in invoice_ids:
                inv = invoice_obj.browse(invoice_id)
                inv.write({'fatturapa_attachment_out_id': attach.id})

        action = {
            'view_type': 'form',
            'name': "Export Electronic Invoice",
            'res_model': 'fatturapa.attachment.out',
            'type': 'ir.actions.act_window',
        }
        if len(attachments) == 1:
            action['view_mode'] = 'form'
            action['res_id'] = attachments[0].id
        else:
            action['view_mode'] = 'tree,form'
            action['domain'] = [('id', 'in', attachments.ids)]
        return action





    @api.v8
    def generate_attach_report(self, inv):
        action_report_model, action_report_id = (
            self.report_print_menu.value.split(',')[0],
            int(self.report_print_menu.value.split(',')[1]))
        action_report = self.env[action_report_model] \
            .browse(action_report_id)
        report_model = self.env['report']
        attachment_model = self.env['ir.attachment']
        # Generate the PDF: if report_action.attachment is set
        # they will be automatically attached to the invoice,
        # otherwise use res to build a new attachment
        (res, report_format) = openerp.report.render_report(
            self._cr, self._uid, [inv.id],
            action_report.report_name, {'model': inv._name},
            self._context)
        if action_report.attachment:
            # If the report is configured to be attached
            # to the current invoice, just get that from the attachments.
            # Note that in this case the attachment in
            # fatturapa_doc_attachments is exactly the same
            # that is attached to the invoice.
            attachment = report_model._attachment_stored(
                inv, action_report)[inv.id]
        else:
            # Otherwise, create a new attachment to be stored in
            # fatturapa_doc_attachments.
            filename = inv.number
            data_attach = {
                'name': filename,
                'datas': base64.b64encode(res),
                'datas_fname': filename,
                'type': 'binary'
            }
            attachment = attachment_model.create(data_attach)
        inv.write({
            'fatturapa_doc_attachments': [(0, 0, {
                'is_pdf_invoice_print': True,
                'ir_attachment_id': attachment.id,
                'description': _("Attachment generated by "
                                 "Electronic invoice export")})]
        })


class Report(models.Model):
    _inherit = "report"

    @api.model
    def _attachment_filename(self, records, report):
        return dict((record.id, safe_eval(report.attachment,
                                          {'object': record,
                                           'time': time})) for
                    record in records)

    @api.model
    def _attachment_stored(self, records, report, filenames=None):
        if not filenames:
            filenames = self._attachment_filename(records, report)
        return dict((record.id, self.env['ir.attachment'].search([
            ('datas_fname', '=', filenames[record.id]),
            ('res_model', '=', report.model),
            ('res_id', '=', record.id)
        ], limit=1)) for record in records)