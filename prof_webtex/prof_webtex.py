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
from openerp.tools.translate import _
import base64
from tempfile import TemporaryFile

from openerp import tools
from openerp.osv import osv, fields, expression

from lxml import etree
import openerp.pooler as pooler
import openerp.sql_db as sql_db
from datetime import datetime, timedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
from openerp import SUPERUSER_ID
from openerp import netsvc
import openerp.addons.decimal_precision as dp
import xxsubtype
import itertools
from lxml import etree
from openerp import api
from openerp import SUPERUSER_ID
import tempfile
import csv
from string import strip
from openerp.tools.misc import ustr
import re
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
import time
import logging
_logger = logging.getLogger(__name__)
try:
    import vatnumber
except ImportError:
    _logger.warning("VAT validation partially unavailable because the `vatnumber` Python library cannot be found. "
                                          "Install it to support more countries, for example with `easy_install vatnumber`.")
    vatnumber = None
from openerp import models, fields as x_fields, _
from openerp import api, _
import prestapi
from prestapi import PrestaShopWebService,PrestaShopWebServiceDict,PrestaShopWebServiceError,PrestaShopAuthenticationError
import math

from openerp.tools.float_utils import float_round
from openerp.exceptions import ValidationError
from openerp.osv.expression import get_unaccent_wrapper
class mail_mail(osv.Model):
    _inherit = 'mail.mail'

    def send_get_mail_body(self, cr, uid, mail, partner=None, context=None):
        """Return a specific ir_email body. The main purpose of this method
        is to be inherited to add custom content depending on some module."""
        body = mail.body_html

        # generate access links for notifications or emails linked to a specific document with auto threading
        link = None
        #if mail.notification or (mail.model and mail.res_id and not mail.no_auto_thread):
        #    link = self._get_partner_access_link(cr, uid, mail, partner, context=context)
        if link:
            body = tools.append_content_to_html(body, link, plaintext=False, container_tag='div')
        return body

class mail_notification(osv.Model):
    _inherit = "mail.notification"

    def get_signature_footer(self, cr, uid, user_id, res_model=None, res_id=None, context=None, user_signature=True):
        """ Format a standard footer for notification emails (such as pushed messages
            notification or invite emails).
            Format:
                <p>--<br />
                    Administrator
                </p>
                <div>
                    <small>Sent from <a ...>Your Company</a> using <a ...>OpenERP</a>.</small>
                </div>
        """
        footer = ""
        if not user_id:
            return footer

        # add user signature
        user = self.pool.get("res.users").browse(cr, SUPERUSER_ID, [user_id], context=context)[0]
        if user_signature:
            if user.signature:
                signature = user.signature
            else:
                signature = "--<br />%s" % user.name
            footer = tools.append_content_to_html(footer, signature, plaintext=False)

        # add company signature
        if user.company_id.website:
            website_url = ('http://%s' % user.company_id.website) if not user.company_id.website.lower().startswith(('http:', 'https:')) \
                else user.company_id.website
            company = "<a style='color:inherit' href='%s'>%s</a>" % (website_url, user.company_id.name)
        else:
            company = user.company_id.name
        sent_by = _('Inviato da %(company)s ')

        signature_company = '<br /><small>%s</small>' % (sent_by % {
            'company': company,
            'odoo': "<a style='color:inherit' href='https://www.casatessile.it/'>Casatessile.it</a>"
        })
        footer = tools.append_content_to_html(footer, signature_company, plaintext=False, container_tag='div')

        return footer
      
class res_partner(osv.osv):
    _inherit = "res.partner"
    _defaults = {
        
        'carriage_condition_id': lambda s, cr, uid, c:      
        s.pool.get('stock.picking.carriage_condition').search(cr, uid,[('name','=','Porto Franco')] , context=c)[0]  
        if s.pool.get('stock.picking.carriage_condition').search(cr, uid,[('name','=','Porto Franco')] , context=c)  else None,
        
        'goods_description_id': lambda s, cr, uid, c: 
         s.pool.get('stock.picking.goods_description').search(cr, uid,[('name','=','Pacchi')] , context=c)[0]
         if s.pool.get('stock.picking.goods_description').search(cr, uid,[('name','=','Pacchi')] , context=c) else None,
        
        'property_delivery_carrier': lambda s, cr, uid, c: 
        s.pool.get('delivery.carrier').search(cr, uid,[('name','=','SDA Express')] , context=c)[0]
        if  s.pool.get('delivery.carrier').search(cr, uid,[('name','=','SDA Express')] , context=c)
        else  None,
        
        'transportation_method_id': lambda s, cr, uid, c: 
        s.pool.get('stock.picking.transportation_method').search(cr, uid,[('name','=','Corriere SDA')] , context=c)[0]
        if s.pool.get('stock.picking.transportation_method').search(cr, uid,[('name','=','Corriere SDA')] , context=c)
        else None,
        
        'transportation_reason_id': lambda s, cr, uid, c: 
        s.pool.get('stock.picking.transportation_reason').search(cr, uid,[('name','=','Vendita')] , context=c)[0]
        if s.pool.get('stock.picking.transportation_reason').search(cr, uid,[('name','=','Vendita')] , context=c)
        else None
        ,
    }
    @api.model
    @api.returns('self', lambda value:value.id)
    def create(self, vals):
        if vals.get('country_id',None):
            pos_fiscal_obj=self.env['account.fiscal.position']#
            pos_fiscal_ids_obj=pos_fiscal_obj.search([('active','=',True),('country_id','=',vals.get('country_id',None))])
            if vals.get('property_product_pricelist',None):
                for pos_fiscal_id_obj in pos_fiscal_ids_obj:
                    pricelist_id_obj=self.env['product.pricelist'].browse(vals.get('property_product_pricelist',None))
                    if pos_fiscal_id_obj.name.find(pricelist_id_obj.currency_id.name)>=0:
                        pos_fiscal_ids_obj=[pos_fiscal_id_obj]
                        break
            if pos_fiscal_ids_obj:
                pos_fiscal_id_obj=pos_fiscal_ids_obj[0]
                if vals.get('property_account_payable',None):
                    property_account_payable=self.env['account.account'].browse(vals.get('property_account_payable',None))
                else:
                    property_account_payable=pos_fiscal_id_obj.company_id.partner_id.property_account_payable
                
                if vals.get('property_account_receivable',None):
                    property_account_receivable=self.env['account.account'].browse(vals.get('property_account_receivable',None))
                else:
                    property_account_receivable=pos_fiscal_id_obj.company_id.partner_id.property_account_receivable
                
                property_account_payable = pos_fiscal_id_obj.map_account(property_account_payable)
                property_account_receivable = pos_fiscal_id_obj.map_account(property_account_receivable)
                vals['property_account_payable']=property_account_payable.id
                vals['property_account_receivable']=property_account_receivable.id
                vals['property_account_position']=pos_fiscal_id_obj.id
                vals['company_id']=pos_fiscal_id_obj.company_id.id or self.env['res.users'].browse(self.env.uid).company_id.id
        if  self.env['delivery.carrier'].search([('name','=','SDA Express')]):
                        vals['property_delivery_carrier']=  self.env['delivery.carrier'].search([('name','=','SDA Express')])[0].id
        else:
                        vals['property_delivery_carrier']=None
                
        state_obj=self.env['res.country.state']#
        if vals.get('state_id',None):
            state_ids_obj=state_obj.search([('country_id','=',vals.get('country_id',None)),('id','=',vals.get('state_id',None))])
            if state_ids_obj:
                vals['state_id']=state_ids_obj[0].id
            else:
                 state_ids_obj=state_obj.search([('id','=',vals.get('state_id',None))])
                 if state_ids_obj:
                     state_ids_obj=state_obj.search([('country_id','=',vals.get('country_id',None)),('code','=',state_ids_obj[0].code)])
                     if state_ids_obj:
                         vals['state_id']=state_ids_obj[0].id

                
        res=super(res_partner, self).create(vals)
        """
        if res:
            if res.country_id:
                if self.property_account_position:
                    print "è impostato"
                else:
                    pos_fiscal_obj=self.env['account.fiscal.position']#
                    pos_fiscal_ids_obj=pos_fiscal_obj.search([('active','=',True),('country_id','=',res.country_id.id)])
                    if pos_fiscal_ids_obj:
                            pos_fiscal_id_obj=pos_fiscal_ids_obj[0]
                            if vals.get('property_account_payable',None):
                                property_account_payable=self.env['account.account'].browse(vals.get('property_account_payable',None))
                            else:
                                property_account_payable=pos_fiscal_id_obj.company_id.partner_id.property_account_payable
                            
                            if vals.get('property_account_receivable',None):
                                property_account_receivable=self.env['account.account'].browse(vals.get('property_account_receivable',None))
                            else:
                                property_account_receivable=pos_fiscal_id_obj.company_id.partner_id.property_account_receivable
                            
                            property_account_payable = pos_fiscal_id_obj.map_account(property_account_payable)
                            property_account_receivable = pos_fiscal_id_obj.map_account(property_account_receivable)
                            
                            vals_pos={'property_account_payable':property_account_payable.id,
                            'property_account_receivable':property_account_receivable.id,
                            'property_account_position':pos_fiscal_id_obj.id,
                            'company_id':pos_fiscal_id_obj.company_id.id}
                            res.write(vals_pos)
        """        
        #print res#
        return res
        
    @api.multi
    def write(self, vals):
        if hasattr(self, '__iter__'):
            self_ids=self
        else:
            self_ids=[self]

        for self in self_ids:
            if vals.get('company_id',None):
                company_id= vals.get('company_id',None)
                company_id=self.env['res.company'].browse(company_id)
            else:
                company_id=self.env['res.users'].browse(self.env.uid).company_id
            if vals.get('country_id',None):
                country_id= vals.get('country_id',None)
                country_id=self.env['res.country'].browse(country_id)
            else:
                country_id=self.country_id
            if vals.get('property_account_position',None):
                property_account_position= vals.get('property_account_position',None)
                property_account_position=self.env['account.fiscal.position'].browse(property_account_position)
            else:
                property_account_position=self.property_account_position
            if vals.get('property_account_payable',None):
                            property_account_payable=self.env['account.account'].browse(vals.get('property_account_payable',None))
            else:
                            property_account_payable=self.property_account_payable
            if vals.get('property_account_receivable',None):
                            property_account_receivable=self.env['account.account'].browse(vals.get('property_account_receivable',None))
            else:
                            property_account_receivable=self.property_account_receivable
                
            if country_id:
                if property_account_position:                        
                    pos_fiscal_id_obj=property_account_position
                    print "è impostato"
                    if property_account_payable:
                            property_account_payable=property_account_payable
                    else:
                            property_account_payable=pos_fiscal_id_obj.company_id.partner_id.property_account_payable
                        
                    if property_account_receivable:
                            property_account_receivable=property_account_receivable
                    else:
                            property_account_receivable=pos_fiscal_id_obj.company_id.partner_id.property_account_receivable
                        
                    property_account_payable = pos_fiscal_id_obj.map_account(property_account_payable)
                    property_account_receivable = pos_fiscal_id_obj.map_account(property_account_receivable)
                    vals_pos={
                                  'property_account_payable':property_account_payable.id,
                                  'property_account_receivable':property_account_receivable.id,
                                  'property_account_position':pos_fiscal_id_obj.id,
                                  'company_id':pos_fiscal_id_obj.company_id.id or company_id.id
                        }
                    vals.update(vals_pos)
                else:
                    pos_fiscal_obj=self.env['account.fiscal.position']#
                    pos_fiscal_ids_obj=pos_fiscal_obj.search([('active','=',True),('country_id','=',country_id.id)])
                    if vals.get('property_product_pricelist',None):
                        for pos_fiscal_id_obj in pos_fiscal_ids_obj:
                            pricelist_id_obj=self.env['product.pricelist'].browse(vals.get('property_product_pricelist',None))
                            if pos_fiscal_id_obj.name.find(pricelist_id_obj.currency_id.name)>=0:
                                pos_fiscal_ids_obj=[pos_fiscal_id_obj]
                                break
                     
                    if pos_fiscal_ids_obj:
                        pos_fiscal_id_obj=pos_fiscal_ids_obj[0]
                        if self.property_account_payable:
                            property_account_payable=self.property_account_payable
                        else:
                            property_account_payable=pos_fiscal_id_obj.company_id.partner_id.property_account_payable
                        
                        if self.property_account_receivable:
                            property_account_receivable=self.property_account_receivable
                        else:
                            property_account_receivable=pos_fiscal_id_obj.company_id.partner_id.property_account_receivable
                        
                        property_account_payable = pos_fiscal_id_obj.map_account(property_account_payable)
                        property_account_receivable = pos_fiscal_id_obj.map_account(property_account_receivable)
                        vals_pos={
                                  'property_account_payable':property_account_payable.id,
                                  'property_account_receivable':property_account_receivable.id,
                                  'property_account_position':pos_fiscal_id_obj.id,
                                  'company_id':pos_fiscal_id_obj.company_id.id or company_id.id
                        }
                        vals.update(vals_pos)
        if self.env.uid==6:
                    if 'vat' in  vals:
                        del vals['vat']        
        #print 'write_res',vals
        res=super(res_partner, self).write(vals)
            
        return res



    def name_get(self, cr, uid, ids, context=None):
        res=super(res_partner, self).name_get(cr, SUPERUSER_ID, ids, context=context)
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = []
        for record in self.browse(cr, SUPERUSER_ID, ids, context=context):
            if record.country_id:
                country_name="%s,%s" % (record.country_id.code,record.country_id.name)
            elif record.parent_id.country_id:
                country_name="%s,%s" % (record.parent_id.country_id.code,record.parent_id.country_id.name)
            else:
                country_name=''
 
            name = record.name
            wk_company=''
            if record.wk_company:
                wk_company=record.wk_company
            
            if record.parent_id and not record.is_company:
                if record.parent_id.wk_company:
                    wk_company=record.parent_id.wk_company
                if record.parent_name==name:
                    name= "%s, %s, %s" % (record.parent_name,wk_company, '.')
                else:
                    name = "%s, %s, %s" % (record.parent_name,wk_company, name)
            
            if context.get('show_address_only'):
                name = self._display_address(cr, SUPERUSER_ID, record, without_company=True, context=context)
            if context.get('show_address'):
                name = name + "\n" + self._display_address(cr, SUPERUSER_ID, record, without_company=True, context=context)
            name = name.replace('\n\n','\n')
            name = name.replace('\n\n','\n')
            if context.get('show_email') and record.email:
                name = "%s <%s>" % (name, record.email)
            res.append((record.id, name))
        return res

           
"""
    def check_vat(self, cr, uid, ids, context=None):
        #res=super(res_partner, self).check_vat( cr, uid, ids, context=context)
        return True

    def simple_vat_check(self, cr, uid, country_code, vat_number, context=None):
        '''
        Check the VAT number depending of the country.
        http://sima-pc.com/nif.php
        '''
        if not ustr(country_code).encode('utf-8').isalpha():
            return False
        country_code=country_code.upper()
        check_func_name = 'check_vat_' + country_code
        check_func = getattr(self, check_func_name, None) or \
                        getattr(vatnumber, check_func_name, None)
        if not check_func:
            # No VAT validation available, default to check that the country code exists
            check_func_name = 'check_vat_' + 'xx'
            return check_func(vat_number)
            res_country = self.pool.get('res.country')
            return bool(res_country.search(cr, uid, [('code', '=ilike', country_code)], context=context))
        return check_func(vat_number)
    def check_vat_nl(self, vat):
        return len(vat)
        return 12
    def check_vat_se(self, vat):
        return len(vat)
        return 12
    def check_vat_xx(self, vat):
        return len(vat)
        return 11
    def check_vat_it(self, vat):
        return len(vat)
        return True
    def check_vat_ch(self, vat):
        return len(vat)
        return 9
    def check_vat_es(self, vat):
        return len(vat)
        return 9
    def check_vat_be(self, vat):
        return len(vat)
        return 10
    def check_vat_gr(self, vat):
        return len(vat)
        return 8
    def check_vat_pt(self, vat):
        return len(vat)
        return 9
    def check_vat_ru(self, vat):
        return len(vat)
        return 10
    def check_vat_fr(self, vat):
        return len(vat)
        return 11
"""



class res_bank(osv.osv):
    _inherit = "res.bank"
    _columns = {
        'x_code': fields.char('Codice Banca', size=64 , required=False),
     }

class res_partner_import_webtex(osv.osv):
    """ partner Import """

    _name = "res.partner.import.webtex"
    _description = "partner Import "
    _columns = {
        'name': fields.char('identificativo di ricezione  clienti', size=128 , required=True),
        'data': fields.binary('File', required=False),
        'f_clienti': fields.boolean('Clienti', required=False),
        'f_fornitori': fields.boolean('Fornitori', required=False),
        'f_dimensioni': fields.boolean('solo Dimensioni', required=False),
        'overwrite': fields.boolean('Sovrascrivi record esistenti',
                                    help=" i record esistenti  "
                                         ""),

     }
    def del_res_partner(self, cr, uid, ids, context=None):
                self.del_data_cli_danea( cr, uid, ids ,context=context)
    def update_categ_res_partner(self, cr, uid, ids, context=None):
        fileobj = TemporaryFile('w+')
        this = self.browse(cr, uid, ids[0])
        try:
            fileobj.write(base64.decodestring(this.data))
    
            # now we determine the file format
            fileobj.seek(0)
            first_line = fileobj.readline().strip().replace('"', '').replace(' ', '')
            fileformat = first_line.endswith("codice,ragsoc,email,"#2 
                "tag," #3
                ) and 'csv' or 'csv'

            fileobj.seek(0)               
            self.load_data_cat_cli_danea( cr, uid, ids ,fileobj, fileformat, context=context)
        finally:
            fileobj.close()

    def import_res_partner(self, cr, uid, ids, context=None):
        fileobj = TemporaryFile('w+')
        this = self.browse(cr, uid, ids[0])
        try:
            fileobj.write(base64.decodestring(this.data))
    
            # now we determine the file format
            fileobj.seek(0)
            first_line = fileobj.readline().strip().replace('"', '').replace(' ', '')
            if this.f_clienti:
                """
                fileformat = first_line.endswith("codice,ragsoc,indirizzo,indirizzo,"#3 
                "cap4,citta5,prov6,reg7,nazione8,ref9,tele10,cell11,fax_12,email_13,pec_14," #14
                "cfisc_15,part_iva_12,tess_14,punti_15,sconti_16,listino_17,fido_18,age_19,"#19
                "pagamento_20,banca_21,,ns_ba_22.dm_sdd_23,emissione_24,fatt_iva_25,cont_reg,26,'#26
                "rep_asp_27,porto_28,rit_acc_29,doc_email_30,uff_pa_31,rif_amm_pa_32,"#32
                "nuovi_doc_33,note_doc_34,hmoepa_35,log_web_36,ex1_37,ex2_38,extra3_39,"#39
                "extra4_40,extra5_41,extra6_42,note_43"#43
                ) and 'csv' or 'csv'
                """
                fileformat = first_line.endswith("codice,ragsoc,indirizzo,"#2 
                "cap3,citta4,prov5,reg6,nazione7,ref8,tele9,cell10,fax_11,email_12,pec_13," #13
                "cfisc_14,part_iva_15,tess_16,punti_17,sconti_18,listino_19,fido_20,age_21,"#21
                "pagamento_22,banca_23,ns_ba_24,dm_sdd_25,emissione_26,fatt_iva_27,cont_reg,28,"#28
                "rep_asp_29,porto_30,rit_acc_31,doc_email_32,uff_pa_33,rif_amm_pa_34,"#34
                "nuovi_doc_35,note_doc_36,hmoepa_37,log_web_38,ex1_39,ex2_40,extra3_41,"#41
                "extra4_42,extra5_43,extra6_44,note_45"#45
                ) and 'csv' or 'csv'

                fileobj.seek(0)               
                self.load_data_cli_danea( cr, uid, ids ,fileobj, fileformat, context=context)
            elif  this.f_fornitori:
                        """
                        fileformat = first_line.endswith("codice,desc2,ragsoc,indirizzo,"#4
                        "località,localita_1,cap,prov,tel,fax,ipclpf,codifsc,part_iva,"#13
                        ",cod_iso,"#14
                        "mastro,perfis,sesso,"#15
                        "d_nascita,l_nascita,T,codpag,des_mer,cell,email,nota,ditta,ivaditta,"#25
                        "cod_spe,cod_tra,porto,codage,cod_zon,cod_lin,cod_iva,codsel,codric,mese,"#35
                        "al,am,an,ao,ap,aq,ar,as,at,au,av,aw,ax,ban_app,cc_ban,ba,bb,bc,bd,be,bf,bg,"#58
                        "bh,bi,bj,bk,bl,bm,bn,bo,bp,bq,br"#69
                        ) and 'csv' or 'csv'#46
                        """
                        fileformat = first_line.endswith("codice,ragsoc,indirizzo,cap,citta,"#4 
                        "prov,regione,nazione,referente,tele,cell,fax,email,pec,c_fisca,part_iva,"#15
                        "cod_tessera,punti_fed,sconti,listino,fido,agente,"#21
                        "pagamento,banca,ns banca,data_mandato,emis_ssd,fatt_con_iva,conto_reg,"#28
                        "resp.traporto,porto,rit.acconto,doc_viaemail,cod_uff_pa,rif_amm_pa,"#34
                        "avviso_n_doc,note_doc,home_page,loginweb,extra1,extra2,extra3,"#41
                        "extra4,extra5,extra6,note"#45
                        ) and 'csv' or 'csv'#46
                        fileobj.seek(0)
                        
                        self.load_data_for( cr, uid, ids ,fileobj, fileformat, context=context)
                  
        finally:
            fileobj.close()
        return True
    """ codice banca """
    def import_account_account(self, cr, uid, ids, context=None):
        fileobj = TemporaryFile('w+')
        this = self.browse(cr, uid, ids[0])
        try:
            fileobj.write(base64.decodestring(this.data))
    
            # now we determine the file format
            fileobj.seek(0)
            first_line = fileobj.readline().strip().replace('"', '').replace(' ', '')
            fileformat = first_line.endswith("codice,ragsoc,indirizzo,"#3 
                "ccorrente,abi,cab,"#9 
                ) and 'csv' or 'csv'#46
            fileobj.seek(0)               
            self.load_data_bank( cr, uid, ids ,fileobj, fileformat, context=context)
        finally:
            fileobj.close()
        return True
    """ abi e cab """
    def import_account_account_2(self, cr, uid, ids, context=None):
        fileobj = TemporaryFile('w+')
        this = self.browse(cr, uid, ids[0])
        try:
            fileobj.write(base64.decodestring(this.data))
    
            # now we determine the file format
            fileobj.seek(0)
            first_line = fileobj.readline().strip().replace('"', '').replace(' ', '')
            fileformat = first_line.endswith("abi,cab,ragsoc,indirizzo,"#3 
                ) and 'csv' or 'csv'#46
            fileobj.seek(0)               
            self.load_data_bank_abicab( cr, uid, ids ,fileobj, fileformat, context=context)
        finally:
            fileobj.close()
        return True
    """ pagamenti """
    def import_account_pag(self, cr, uid, ids, context=None):
        fileobj = TemporaryFile('w+')
        this = self.browse(cr, uid, ids[0])
        try:
            fileobj.write(base64.decodestring(this.data))
    
            # now we determine the file format
            fileobj.seek(0)
            first_line = fileobj.readline().strip().replace('"', '').replace(' ', '')
            fileformat = first_line.endswith("tipo,rate,passo,scadenze,descrzione"#3 
                ) and 'csv' or 'csv'#46
            fileobj.seek(0)               
            self.load_data_pagamenti( cr, uid, ids ,fileobj, fileformat, context=context)
        finally:
            fileobj.close()
        return True
    def import_articoli(self, cr, uid, ids, context=None):
        fileobj = TemporaryFile('w+')
        this = self.browse(cr, uid, ids[0])
        try:
            fileobj.write(base64.decodestring(this.data))
    
            # now we determine the file format
            fileobj.seek(0)
            first_line = fileobj.readline().strip().replace('"', '').replace(' ', '')
            fileformat = first_line.endswith("cod_pro,descr,2,3,4,5,6,7,8,9,10,11,12"#12
            "gruppo"#13
                ) and 'csv' or 'csv'#46
            fileobj.seek(0)               
            self.load_data_articoli( cr, uid, ids ,fileobj, fileformat, context=context)
        finally:
            fileobj.close()
        return True
    def import_listini(self, cr, uid, ids, context=None):
        fileobj = TemporaryFile('w+')
        this = self.browse(cr, uid, ids[0])
        try:
            fileobj.write(base64.decodestring(this.data))
    
            # now we determine the file format
            fileobj.seek(0)
            first_line = fileobj.readline().strip().replace('"', '').replace(' ', '')
            fileformat = first_line.endswith("cod_lis,cod_prod,valuta,finitura,pric"#5
            "lipven,liddec,lipvec,liccls,lidsfi"#10
                ) and 'csv' or 'csv'#46
            fileobj.seek(0)               
            self.load_data_listini( cr, uid, ids ,fileobj, fileformat, context=context)
        finally:
            fileobj.close()
        return True
    def import_costi(self, cr, uid, ids, context=None):
        fileobj = TemporaryFile('w+')
        this = self.browse(cr, uid, ids[0])
        try:
            fileobj.write(base64.decodestring(this.data))
    
            # now we determine the file format
            fileobj.seek(0)
            first_line = fileobj.readline().strip().replace('"', '').replace(' ', '')
            fileformat = first_line.endswith("anno,codice,magazzino,"#3
            "3,4,5,6,7,8,9,0,"#10
            "1,2,3,4,5,6,7,8,9,0,"#20
            "1,2,3,4,5,6,7,8,9,0,1,2,3,4,costo,"#35
                ) and 'csv' or 'csv'#46
            fileobj.seek(0)               
            self.load_data_costi( cr, uid, ids ,fileobj, fileformat, context=context)
        finally:
            fileobj.close()
        return True
    def load_data_for(self, cr, uid, ids, fileobj, fileformat,  context=None):
        date_today=datetime.today()
        if not ids:
                vals={
                'name':str(date_today),
                'overwrite':False
                }
                ids_id=self.create(cr, uid, vals, context)
        else:      
            ids_id= ids[0]
        this = self.browse(cr, uid, ids_id)
        db_name = cr.dbname
        pool = pooler.get_pool(db_name)
        partner_obj = pool.get('res.partner')
        province_obj = pool.get('res.country.state')
        zip_obj = pool.get('res.better.zip')
        country_obj = pool.get('res.country')
        tax_obj=pool.get('account.tax')
        payment_term_obj=pool.get('account.payment.term')
        porto_obj=pool.get('stock.picking.carriage_condition')
        payment_term_obj=pool.get('account.payment.term')
        try:
           # now, the serious things: we read the language file
            """leggo l'intestazione"""
            fileobj.seek(0)
            if fileformat == 'csv':
                reader = csv.reader(fileobj, quotechar='"', delimiter=',')
                # read the first line of the file (it contains columns titles)
                for row in reader:
                    f = row
                    break

            else:
                raise osv.except_osv(('Bad file format: %s'), (fileformat))
                raise Exception(_('Bad file format'))
    
            # read the rest of the file
            line = 1   
            for row in reader:
                        line +=1        
                        F_fiscode=False
                        if row[11]=='':
                                    row[11]=None

                        """ creo il fornitore"""
                        if row[11]:
                            partner_ids = partner_obj.search(cr, uid, [('fiscalcode','=',row[14])])    
                            if  not partner_ids:   
                                partner_ids = partner_obj.search(cr, uid, [('name','=',row[1])])    
                                F_fiscode=False
                            else:
                                F_fiscode=True
                        else:
                                partner_ids = partner_obj.search(cr, uid, [('name','=',row[1])])    
                        province_ids= province_obj.search(cr, uid, [('code','=',row[5])])
                        country_ids= country_obj.search(cr, uid, [('name','=',row[7])])     
                        if not country_ids:
                            #row[12]='IT'
                            country_ids= country_obj.search(cr, uid, [('code','=',"IT")])     
                            
                        if not province_ids:
                                province_ids_id=None
                        else:
                                province_ids_id=province_ids[0]
                        country_code=None                         
                        if not country_ids:
                                country_ids_id=None
                        else:
                                country_ids_id=country_ids[0]
                                country_ids_obj=country_obj.browse(cr, uid, country_ids_id, context=context)
                                country_code=country_ids_obj.code
                        zip_ids= zip_obj.search(cr, uid, [('name','=',row[3]),('country_id','=',country_ids_id)])
                        if zip_ids:
                            zip_id_obj=zip_obj.browse(cr,uid,zip_ids[0])
                        else:
                            zip_id_obj=None
                        porto_ids= porto_obj.search(cr, uid, [('note','=',row[30])])     
                        if not porto_ids:
                                porto_ids_id=None
                        else:
                                porto_ids_id=porto_ids[0]
 
                        
                        pay_id=None
                        pay_ids=payment_term_obj.search(cr,uid,[('id','>',0)])
                        if pay_ids:
                            for pay_id_obj in payment_term_obj.browse(cr,uid,pay_ids,context=context):
                                if pay_id_obj.name.find(row[22])>=0:
                                    pay_id=pay_id_obj.id
                                    exit
                    # lets create the language with locale information
                        if pay_id==None:
                            pay_id=payment_term_obj.create(cr,uid,{'name':row[22]},context=context)
                        if row[8]==None:
                                    row[8]='0'
                        #if len(row[12])<=11:
                        #         row[12]=str(row[12]).zfill(11)
                                  
                        if row[15] != '':
                            if country_code != None:
                                 
                                 if row[15].find(country_code)>=0:
                                     vat=country_code+row[15][row[15].find(country_code)+2:len(row[15])]
                                 else:
                                     if len(row[15].strip())<9:
                                         row[15]="000"+row[15].strip()
                                     if len(row[15].strip())<10:
                                         row[15]="00"+row[15].strip()
                                     if len(row[15].strip())<11:
                                         row[15]="0"+row[15].strip()
                                     vat=country_code+row[15].strip()
                                     
                        else:
                                 vat=row[15]
                        if row[15]=='':
                                    row[15]=None
                                    vat=None
                        
                        
                        if row[12]=='IT':
                            row[12]=''
                        #if not isnumeric(str(row[12])):        
                        #            vat=None

                        vals={
                              'is_company':True,
                              'ref':row[0],
                              'name':row[1],
                              'street':row[2],
                              'zip':row[3],
                              'city':row[4],
                              'province':province_ids_id,
                              'country':country_ids_id,
                              'email':row[12],
                              'customer':this.f_clienti,
                              'supplier':this.f_fornitori,
                              'phone':row[9],
                              'fax':row[11],
                              'vat_subjected':True,
                              'vat':vat,
                              'fiscalcode':row[14],
                              'carriage_condition_id':porto_ids_id,
                              'transportation_reason_id':1,
                              'goods_description_id':1,
                              'comment':row[45]
                               }# skip empty rows and rows where the translation field (=last fiefd) is empty
                        #print 'fornitore-->'+str(line)+'cod_fis->'+str(row[14])+'par_iva->'+str(vat)        
                        if not partner_ids:
                                partner_ids_id=partner_obj.create(cr, uid, vals, context=context)
                        else:
                             if F_fiscode:
                                vals={'supplier':this.f_fornitori,}
                             vals['comment']=row[45]
                             vals['email']=row[12]

                             if this.overwrite:
                                partner_ids_id=partner_ids[0]
                                partner_obj.write(cr, uid, partner_ids_id,vals, context=context)
                        #_logger.info("importazione effettuata con successo-->"+str(line))
            return True  
        except IOError:
                        _logger.info("importazione non effettuata ")
 
                        return False 
                        """
                        raise osv.except_osv(_("Errore %s"), _('ricezione disponibilita'))
                        """
    def load_data_for_ideasoft(self, cr, uid, ids, fileobj, fileformat,  context=None):
        date_today=datetime.today()
        if not ids:
                vals={
                'name':str(date_today),
                'overwrite':False
                }
                ids_id=self.create(cr, uid, vals, context)
        else:      
            ids_id= ids[0]
        this = self.browse(cr, uid, ids_id)
        db_name = cr.dbname
        pool = pooler.get_pool(db_name)
        partner_obj = pool.get('res.partner')
        province_obj = pool.get('res.country.state')
        country_obj = pool.get('res.country')
        tax_obj=pool.get('account.tax')
        payment_term_obj=pool.get('account.payment.term')
        porto_obj=pool.get('stock.picking.carriage_condition')
        try:
           # now, the serious things: we read the language file
            """leggo l'intestazione"""
            fileobj.seek(0)
            if fileformat == 'csv':
                reader = csv.reader(fileobj, quotechar='"', delimiter=',')
                # read the first line of the file (it contains columns titles)
                for row in reader:
                    f = row
                    break

            else:
                raise osv.except_osv(('Bad file format: %s'), (fileformat))
                raise Exception(_('Bad file format'))
    
            # read the rest of the file
            line = 1   
            for row in reader:
                        line +=1        
                        F_fiscode=False
                        if row[11]=='':
                                    row[11]=None

                        """ creo il fornitore"""
                        if row[11]:
                            partner_ids = partner_obj.search(cr, uid, [('fiscalcode','=',row[11])])    
                            if  not partner_ids:   
                                partner_ids = partner_obj.search(cr, uid, [('name','=',row[2])])    
                                F_fiscode=False
                            else:
                                F_fiscode=True
                        else:
                                partner_ids = partner_obj.search(cr, uid, [('name','=',row[2])])    
                        province_ids= province_obj.search(cr, uid, [('code','=',row[7])])
                        country_ids= country_obj.search(cr, uid, [('code','=',row[13])])     
                        if not country_ids:
                            row[12]='IT'
                            country_ids= country_obj.search(cr, uid, [('code','=',"IT")])     
                        porto_ids= porto_obj.search(cr, uid, [('note','=',row[29])])     
                        if not province_ids:
                                province_ids_id=0
                        else:
                                province_ids_id=province_ids[0]
                        country_code=None                         
                        if not country_ids:
                                country_ids_id=0
                        else:
                                country_ids_id=country_ids[0]
                                country_ids_obj=country_obj.browse(cr, uid, country_ids_id, context=context)
                                country_code=country_ids_obj.code
                        if not porto_ids:
                                porto_ids_id=0
                        else:
                                porto_ids_id=porto_ids[0]
 
                        
                    # lets create the language with locale information
                        if row[8]==None:
                                    row[8]='0'
                        #if len(row[12])<=11:
                        #         row[12]=str(row[12]).zfill(11)
                                  
                        if country_code != None:
                                 vat=country_code+row[12]
                        else:
                                 vat=row[12]
                        if row[12]=='':
                                    row[12]=None
                                    vat=None
                        
                        
                        #if not isnumeric(str(row[12])):        
                        #            vat=None

                        vals={
                              'is_company':True,
                              'ref':row[0],
                              'name':row[2],
                              'street':row[3],
                              'zip':row[6],
                              'city':row[4],
                              'province':province_ids_id,
                              'country':country_ids_id,
                              'email':row[23],
                              'customer':this.f_clienti,
                              'supplier':this.f_fornitori,
                              'phone':row[8],
                              'fax':row[9],
                              'vat_subjected':True,
                              'vat':vat,
                              'fiscalcode':row[11],
                              'carriage_condition_id':porto_ids_id,
                              'transportation_reason_id':1,
                              'goods_description_id':1,
       
                               }# skip empty rows and rows where the translation field (=last fiefd) is empty
                        print 'fornitore-->'+str(line)+'cod_fis->'+str(vals['fiscalcode'])+'par_iva->'+str(vals['vat'])        
                        if not partner_ids:
                                partner_ids_id=partner_obj.create(cr, uid, vals, context=context)
                        else:
                             if F_fiscode:
                                vals={'supplier':this.f_fornitori,}
                             if this.overwrite:
                                partner_ids_id=partner_ids[0]
                                partner_obj.write(cr, uid, partner_ids_id,vals, context=context)
                        #_logger.info("importazione effettuata con successo-->"+str(line))
            return True  
        except IOError:
                        _logger.info("importazione non effettuata ")
 
                        return False 
                        """
                        raise osv.except_osv(_("Errore %s"), _('ricezione disponibilita'))
                        """
    def load_data_cli_danea(self, cr, uid, ids, fileobj, fileformat,  context=None):
        date_today=datetime.today()
        if not ids:
                vals={
                'name':str(date_today),
                'overwrite':False
                }
                ids_id=self.create(cr, uid, vals, context)
        else:      
            ids_id= ids[0]
        this = self.browse(cr, uid, ids_id)
        db_name = cr.dbname
        pool = pooler.get_pool(db_name)
        partner_obj = pool.get('res.partner')
        province_obj = pool.get('res.country.state')
        country_obj = pool.get('res.country')
        tax_obj=pool.get('account.tax')
        payment_term_obj=pool.get('account.payment.term')
        porto_obj=pool.get('stock.picking.carriage_condition')
        bank_partner_obj = pool.get('res.partner.bank') 
        bank_obj = pool.get('res.bank')
        zip_obj = pool.get('res.better.zip')
        try:
           # now, the serious things: we read the language file
            """leggo l'intestazione"""
            fileobj.seek(0)
            if fileformat == 'csv':
                reader = csv.reader(fileobj, quotechar='"', delimiter=',')
                # read the first line of the file (it contains columns titles)
                for row in reader:
                    f = row
                    break

            else:
                raise osv.except_osv(('Bad file format: %s'), (fileformat))
                raise Exception(_('Bad file format'))
    
            # read the rest of the file
            line = 1   
            print 'ancpag-->',row[14]
            pay_ids=payment_term_obj.search(cr,uid,[('id','>',0)])
                        
            print 'pay_ids-->',pay_ids
            for row in reader:
                        line +=1        
                        if line>100:
                            try:
                              cr.commit()
                            except:
                              cr.rollback()
                            line=1
                                
                        F_fiscode=False
                        if row[8]=='':
                                    row[8]=None

                        """ creo il cliente"""
                        parent_id=None
                        if len(str(row[14]).strip())==16:
                            partner_ids = partner_obj.search(cr, uid, [('fiscalcode','=',row[14])])    
                            if  not partner_ids:   
                                partner_ids = partner_obj.search(cr, uid, [('name','=',row[1])])    
                                F_fiscode=False
                            else:
                                F_fiscode=True
                        else:
                                partner_ids = partner_obj.search(cr, uid, [('name','=',row[1])])    
                        partner_ind_ids = partner_obj.search(cr, uid, [('name','=',row[1]),('street','=',row[2])])    
                        if partner_ind_ids==None and partner_ids:
                            parent_id=partner_ids
                            partner_ids=None
                        province_ids= province_obj.search(cr, uid, [('code','=',row[5])])
                        if str(row[7]).upper()=='ITA':
                            row[7]='IT'
                        country_ids= country_obj.search(cr, uid, [('code','=',row[7])])     
                        if not country_ids:
                            country_ids= country_obj.search(cr, uid, [('code','=',"IT")])     
                        if row[30]=='0':
                            row[30]='porto franco'.upper()
                        porto_ids= porto_obj.search(cr, uid, [('note','=',row[30])])     
                        if not province_ids:
                                province_ids_id=None
                        else:
                                province_ids_id=province_ids[0]
                        country_code=None                         
                        if not country_ids:
                                country_ids_id=None
                        else:
                                country_ids_id=country_ids[0]
                                country_ids_obj=country_obj.browse(cr, uid, country_ids_id, context=context)
                                country_code=country_ids_obj.code
                        zip_ids= zip_obj.search(cr, uid, [('name','like',row[3]),('country_id','=',country_ids_id)])
                        if zip_ids==None:
                            zip_ids= zip_obj.search(cr, uid, [('city','like',row[4]),('country_id','=',country_ids_id)])
                            
                        if zip_ids:
                            zip_id_obj=zip_obj.browse(cr,uid,zip_ids[0])
                            zip_id=zip_ids[0]
                        else:
                            zip_id_obj=None
                            zip_id=None
                        if not porto_ids:
                                porto_ids_id=1
                        else:
                                porto_ids_id=porto_ids[0]
 
                        
                    # lets create the language with locale information
                        #if len(row[9])<=11:
                        #         row[9]=str(row[9]).zfill(11)
                                  
                        if len(row[15])>9 and len(row[15])<16:
                            if country_code != None:
                                    if country_code=='IT':
                                        if len(row[15])<9:
                                            row[15]='000'+ row[15]
                                        elif len(row[15])<10:
                                             row[15]='00'+ row[15]
                                        elif len(row[15])<11:
                                             row[15]='0'+ row[15]
                                            
                                    vat=country_code+row[15]
                            
                            else:
                                     vat=row[15]
                            if row[15]=='':
                                        row[15]=None
                                        vat=None
                        else:
                            vat=None
                                               
                        #if not isnumeric(str(row[9])):        
                        #            vat=None 
                        pay_id=None
                        if pay_ids:
                            for pay_id_obj in payment_term_obj.browse(cr,uid,pay_ids,context=context):
                                if pay_id_obj.name.find(row[22]):
                                    pay_id=pay_id_obj.id
                                    exit
                        vals={
                              'is_company':True if vat else False ,
                              'ref':row[0],
                              'name':row[1],
                              #'x_rsoc_est':row[52],
                              'parent_id':parent_id,
                              'street':row[2],
                              'zip':row[3],
                              'city':row[4],
                              'state_id':province_ids_id,
                              'country_id':country_ids_id,
                              'email':row[12],
                              'customer':True,
                              #'supplier':True if row[39]=='F' else False,
                              'phone':row[9],
                              'mobile':row[10],
                              'fax':row[11],
                              'vat_subjected':True if (vat) else False,
                              'vat':None if parent_id==None else vat,
                              'fiscalcode':row[14] if len(row[14])==16 else None,
                              'carriage_condition_id':porto_ids_id,
                              'transportation_reason_id':1,
                              'goods_description_id':1,
                              'property_payment_term':pay_id ,
                              'property_supplier_payment_term':False,
                              'zip_id':zip_id,
                              'comment':row[45]
                              #'x_spese_id':1 if pay_id_obj.riba==True else False
                               }# skip empty rows and rows where the translation field (=last fiefd) is empty
                        print 'cliente-->'+str(line)+'cod_fis->'+str(row[14])+'par_iva->'+str(vat)+'zip_id->',zip_id        
                        if not partner_ids:
                                partner_ids_id=partner_obj.create(cr, uid, vals, context=context)
                                
                        else:
                              partner_ids_id=partner_ids[0]
                              if this.overwrite:
                               partner_obj.write(cr, uid, partner_ids_id,vals, context=context)
                                 
            return True  
        except IOError:
                        _logger.info("importazione non effettuata ")
 
                        return False 
                        """
                        raise osv.except_osv(_("Errore %s"), _('ricezione disponibilita'))
                        """
    def load_data_cat_cli_danea(self, cr, uid, ids, fileobj, fileformat,  context=None):
        date_today=datetime.today()
        if not ids:
                vals={
                'name':str(date_today),
                'overwrite':False
                }
                ids_id=self.create(cr, uid, vals, context)
        else:      
            ids_id= ids[0]
        this = self.browse(cr, uid, ids_id)
        db_name = cr.dbname
        pool = pooler.get_pool(db_name)
        partner_obj = pool.get('res.partner')
        category_obj = pool.get('res.partner.category')
        if this:
        #try:
           # now, the serious things: we read the language file
            """leggo l'intestazione"""
            fileobj.seek(0)
            if fileformat == 'csv':
                reader = csv.reader(fileobj, quotechar='"', delimiter=',')
                # read the first line of the file (it contains columns titles)
                for row in reader:
                    f = row
                    break

            else:
                raise osv.except_osv(('Bad file format: %s'), (fileformat))
                raise Exception(_('Bad file format'))
    
            # read the rest of the filexxx
            line = 1#zzz   
            print 'categoria-->',row[3]
                        
            for row in reader:
                        line +=1        
                        if line>100:
                            try:
                              cr.commit()
                            except:
                              cr.rollback()
                            line=1
                        """ creo il categoria"""
                        category_ids=category_obj.search(cr,uid,[('name','=',row[3])])
                        if category_ids==None or category_ids==[]:
                            category_id=category_obj.create(cr,uid,{'name':row[3]},context=context)
                            category_ids.append(category_id)
                        partner_ids = partner_obj.search(cr, uid, [('name','=',row[1]),('email','=',row[2])])    
                        if  partner_ids:   
                                partner_obj.write(cr,uid,partner_ids[0],{'category_id':[(6,0,category_ids)]})    
                        else:
                            print 'non trovato ->',row[1]
            return True  
        else:
        #except IOError:
        #                _logger.info("importazione non effettuata ")
 
                        return False 
                        """
                        raise osv.except_osv(_("Errore %s"), _('ricezione disponibilita'))
                        """

    def del_data_cli_danea(self, cr, uid, ids,context=None):
        date_today=datetime.today()
        if not ids:
                vals={
                'name':str(date_today),
                'overwrite':False
                }
                ids_id=self.create(cr, uid, vals, context)
        else:      
            ids_id= ids[0]
        this = self.browse(cr, uid, ids_id)
        partner_obj = self.pool.get('res.partner')
        partner_2_obj = self.pool.get('res.partner')
        zip_obj = self.pool.get('res.better.zip')
        partner_ids = partner_obj.search(cr, uid, [('id','>',0),('customer','=',True)])
        for partner_id_obj in partner_obj.browse(cr,uid,partner_ids,context=context): 
                                print 'partner_id_obj.state_id',partner_id_obj.state_id
                                if partner_id_obj.state_id.id==False:
                                    print 'partner_id_obj.state_id_none',partner_id_obj.zip_id,partner_id_obj.state_id
                                    if partner_id_obj.zip_id.state_id.id:
                                            partner_2_obj.write(cr,uid,partner_id_obj.id,{'state_id':partner_id_obj.zip_id.state_id.id},context=context) 
                                    else:    
                                        if partner_id_obj.zip:
                                            if partner_id_obj.country_id.id:
                                                country_id=partner_id_obj.country_id.id
                                            else:
                                                country_id=110
                                            zip_ids= zip_obj.search(cr, uid, [('name','like',partner_id_obj.zip),('country_id','=',country_id)])
                                            if zip_ids:
                                                zip_id_obj=zip_obj.browse(cr, uid, zip_ids[0], context=context)
                                                partner_2_obj.write(cr,uid,partner_id_obj.id,{'zip_id':zip_ids[0],'state_id':zip_id_obj.state_id.id,'country_id':country_id},context=context) 
    
                                partner_2_ids = partner_2_obj.search(cr, uid, [('name','=',partner_id_obj.name),('street','=',partner_id_obj.street),('parent_id','=',None)])    
                                if len(partner_2_ids)>1:
                                    for partner_2_id in partner_2_ids:
                                        if partner_2_id== partner_2_ids[0]:
                                            continue
                                        #partner_obj.unlink(cr, uid, partner_2_id, context=context)
                                        cr.execute('delete from res_partner where id=%s',(partner_2_id,))

        return True  
    def load_data_bank(self, cr, uid, ids, fileobj, fileformat,  context=None):
        date_today=datetime.today()
        if not ids:
                vals={
                'name':str(date_today),
                'overwrite':False
                }
                ids_id=self.create(cr, uid, vals, context)
        else:      
            ids_id= ids[0]
        this = self.browse(cr, uid, ids_id)
        db_name = cr.dbname
        pool = pooler.get_pool(db_name)
        bank_obj = pool.get('res.bank')
        partner_obj = pool.get('res.partner')
        province_obj = pool.get('res.province')
        country_obj = pool.get('res.country')
        tax_obj=pool.get('account.tax')
        payment_term_obj=pool.get('account.payment.term')
        porto_obj=pool.get('stock.picking.carriage_condition')
        try:
           # now, the serious things: we read the language file
            """leggo l'intestazione"""
            fileobj.seek(0)
            if fileformat == 'csv':
                reader = csv.reader(fileobj, quotechar='"', delimiter=',')
                # read the first line of the file (it contains columns titles)
                for row in reader:
                    f = row
                    break

            else:
                raise osv.except_osv(('Bad file format: %s'), (fileformat))
                raise Exception(_('Bad file format'))
    
            # read the rest of the file
            line = 1   
            for row in reader:
                        line +=1        
                        """ creo il banca"""
                        bank_ids = bank_obj.search(cr, uid, [('x_code','=',row[0]),('name','=',row[1])])    
                        vals={
                              'x_code':row[0],
                              'name':row[1],
                              'street':row[2],
                              'x_abi':row[4],
                              'x_cab':row[5],
                              'bic':None,
       
                               }# skip empty rows and rows where the translation field (=last fiefd) is empty
                        print 'banca-->'+str(line)+'name->'+str(vals['name'])+'city->'+str(vals['street'])        
                        if not bank_ids:
                                bank_ids_id=bank_obj.create(cr, uid, vals, context=context)
                        else:
                             if this.overwrite:
                                bank_ids_id=bank_ids[0]
                                bank_obj.write(cr, uid, bank_ids_id,vals, context=context)
                        #_logger.info("importazione effettuata con successo-->"+str(line))
            return True  
        except IOError:
                        _logger.info("importazione non effettuata ")
 
                        return False 
                        """
                        raise osv.except_osv(_("Errore %s"), _('ricezione disponibilita'))
                        """
    def load_data_bank_abicab(self, cr, uid, ids, fileobj, fileformat,  context=None):
        date_today=datetime.today()
        if not ids:
                vals={
                'name':str(date_today),
                'overwrite':False
                }
                ids_id=self.create(cr, uid, vals, context)
        else:      
            ids_id= ids[0]
        this = self.browse(cr, uid, ids_id)
        db_name = cr.dbname
        pool = pooler.get_pool(db_name)
        bank_obj = pool.get('res.bank')
        partner_obj = pool.get('res.partner')
        province_obj = pool.get('res.province')
        country_obj = pool.get('res.country')
        tax_obj=pool.get('account.tax')
        payment_term_obj=pool.get('account.payment.term')
        porto_obj=pool.get('stock.picking.carriage_condition')
        try:
           # now, the serious things: we read the language file
            """leggo l'intestazione"""
            fileobj.seek(0)
            if fileformat == 'csv':
                reader = csv.reader(fileobj, quotechar='"', delimiter=',')
                # read the first line of the file (it contains columns titles)
                for row in reader:
                    f = row
                    break

            else:
                raise osv.except_osv(('Bad file format: %s'), (fileformat))
                raise Exception(_('Bad file format'))
    
            # read the rest of the file
            line = 1   
            for row in reader:
                        line +=1        
                        """ creo il banca"""
                        bank_ids = bank_obj.search(cr, uid, [('x_abi','=',row[0]),('x_cab','=',row[1])])    

                        
                    # lets create the language with locale information
                        
                        
                        #if not isnumeric(str(row[9])):        
                        #            vat=None

                        vals={
                              'name':row[2],
                              'street':row[3],
                              'x_abi':row[0],
                              'x_cab':row[1],
                              'bic':None,
       
                               }# skip empty rows and rows where the translation field (=last fiefd) is empty
                        print 'banca-->'+str(line)+'name->'+str(vals['name'])+'city->'+str(vals['street'])        
                        if not bank_ids:
                                bank_ids_id=bank_obj.create(cr, uid, vals, context=context)
                        else:
                             if this.overwrite:
                                bank_ids_id=bank_ids[0]
                                bank_obj.write(cr, uid, bank_ids_id,vals, context=context)
                        #_logger.info("importazione effettuata con successo-->"+str(line))
            return True  
        except IOError:
                        _logger.info("importazione non effettuata ")
 
                        return False 
                        """
                        raise osv.except_osv(_("Errore %s"), _('ricezione disponibilita'))
                        """
    def load_data_pagamenti(self, cr, uid, ids, fileobj, fileformat,  context=None):
        date_today=datetime.today()
        if not ids:
                vals={
                'name':str(date_today),
                'overwrite':False
                }
                ids_id=self.create(cr, uid, vals, context)
        else:      
            ids_id= ids[0]
        this = self.browse(cr, uid, ids_id)
        db_name = cr.dbname
        pool = pooler.get_pool(db_name)
        bank_obj = pool.get('res.bank')
        partner_obj = pool.get('res.partner')
        province_obj = pool.get('res.province')
        country_obj = pool.get('res.country')
        tax_obj=pool.get('account.tax')
        payment_term_obj=pool.get('account.payment.term')
        porto_obj=pool.get('stock.picking.carriage_condition')
        try:
           # now, the serious things: we read the language file
            """leggo l'intestazione"""
            fileobj.seek(0)
            if fileformat == 'csv':
                reader = csv.reader(fileobj, quotechar='"', delimiter=',')
                # read the first line of the file (it contains columns titles)
                for row in reader:
                    f = row
                    break

            else:
                raise osv.except_osv(('Bad file format: %s'), (fileformat))
                raise Exception(_('Bad file format'))
    
            # read the rest of the file
            line = 1   
            for row in reader:
                        line +=1        
                        """ creo pagamento"""
                        term_ids = payment_term_obj.search(cr, uid, [('name','=',str(row[4])[0:63])])    
                        
                        vals={
                              'name':str(row[4])[0:63],
                              'note':row[0]+row[1]+row[2]+row[3]+"-"+row[4],
                              'riba':True if str(row[4]).find('bancaria') else False,
                               }# skip empty rows and rows where the translation field (=last fiefd) is empty
                        #print 'banca-->'+str(line)+'name->'+str(vals['name'])+'city->'+str(vals['street'])        
                        if not term_ids:
                                term_ids_id=payment_term_obj.create(cr, uid, vals, context=context)
                        else:
                             if this.overwrite:
                                term_ids_id=term_ids[0]
                                payment_term_obj.write(cr, uid, term_ids_id,vals, context=context)
                        #_logger.info("importazione effettuata con successo-->"+str(line))
            return True  
        except IOError:
                        _logger.info("importazione non effettuata ")
 
                        return False 
                        """
                        raise osv.except_osv(_("Errore %s"), _('ricezione disponibilita'))
                        """
    def load_data_articoli(self, cr, uid, ids, fileobj, fileformat,  context=None):
        date_today=datetime.today()
        if not ids:
                vals={
                'name':str(date_today),
                'overwrite':False
                }
                ids_id=self.create(cr, uid, vals, context)
        else:      
            ids_id= ids[0]
        this = self.browse(cr, uid, ids_id)
        db_name = cr.dbname
        pool = pooler.get_pool(db_name)
        product_obj=pool.get('product.product')
        categ_obj=pool.get('product.category')
        try:
           # now, the serious things: we read the language file
            """leggo l'intestazione"""
            fileobj.seek(0)
            if fileformat == 'csv':
                reader = csv.reader(fileobj, quotechar='"', delimiter=',')
                # read the first line of the file (it contains columns titles)
                for row in reader:
                    f = row
                    break

            else:
                raise osv.except_osv(('Bad file format: %s'), (fileformat))
                raise Exception(_('Bad file format'))
    
            # read the rest of the file
            line = 1   
            for row in reader:
                        line +=1        
                        """creo la categoria"""
                        categ_ids = categ_obj.search(cr, uid, [('name','=', row[13])])    
                        if not categ_ids:
                         # lets create the language with locale information
                                 vals={
                                 'name':row[13],
                                 'complete_name':row[13]
                                   }# skip empty rows and rows where the translation field (=last fiefd) is empty
                                 categ_ids_id=categ_obj.create(cr, uid, vals, context=context)
                        else:
                                 categ_ids_id=categ_ids[0]
                        """ creo prodotto"""
                        product_ids = product_obj.search(cr, uid, [('default_code','=',str(row[1]))])    
                        
                        vals={
                              'default_code':str(row[0]),
                              'name':str(row[1])[0:63],
                             'list_price':2,
                             'standard_price':1,
                              'type':'product',
                              'categ_id': categ_ids_id,
                                 'rental':True,
                                 'state':'sellable',
                               }# skip empty rows and rows where the translation field (=last fiefd) is empty
                        #print 'banca-->'+str(line)+'name->'+str(vals['name'])+'city->'+str(vals['street'])        
                        if not product_ids:
                                product_id=product_obj.create(cr, uid, vals, context=context)
                        else:
                             if this.overwrite:
                                product_id=product_ids[0]
                                product_obj.write(cr, uid, product_id,vals, context=context)
                        #_logger.info("importazione effettuata con successo-->"+str(line))
            return True  
        except IOError:
                        _logger.info("importazione non effettuata ")
 
                        return False 
                        """
                        raise osv.except_osv(_("Errore %s"), _('ricezione disponibilita'))
                        """
    def load_data_listini(self, cr, uid, ids, fileobj, fileformat,  context=None):
        date_today=datetime.today()
        if not ids:
                vals={
                'name':str(date_today),
                'overwrite':False
                }
                ids_id=self.create(cr, uid, vals, context)
        else:      
            ids_id= ids[0]
        this = self.browse(cr, uid, ids_id)
        db_name = cr.dbname
        pool = pooler.get_pool(db_name)
        product_obj=pool.get('product.product')
        categ_obj=pool.get('product.category')
        try:
           # now, the serious things: we read the language file
            """leggo l'intestazione"""
            fileobj.seek(0)
            if fileformat == 'csv':
                reader = csv.reader(fileobj, quotechar='"', delimiter=',')
                # read the first line of the file (it contains columns titles)
                for row in reader:
                    f = row
                    break

            else:
                raise osv.except_osv(('Bad file format: %s'), (fileformat))
                raise Exception(_('Bad file format'))
    
            # read the rest of the file
            line = 1   
            for row in reader:
                        line +=1        
                        """ trovo prodotto"""
                        product_ids = product_obj.search(cr, uid, [('default_code','=',str(row[1]))])    
                        
                        vals={
                                'list_price':row[5],
                               }# skip empty rows and rows where the translation field (=last fiefd) is empty
                        #print 'banca-->'+str(line)+'name->'+str(vals['name'])+'city->'+str(vals['street'])        
                        if not product_ids:
                                product_id=None #product_obj.create(cr, uid, vals, context=context)
                        else:
                             #if this.overwrite:
                                product_id=product_ids[0]
                                product_obj.write(cr, uid, product_id,vals, context=context)
                        #_logger.info("importazione effettuata con successo-->"+str(line))
            return True  
        except IOError:
                        _logger.info("importazione non effettuata ")
 
                        return False 
                        """
                        raise osv.except_osv(_("Errore %s"), _('ricezione disponibilita'))
                        """
    def load_data_costi(self, cr, uid, ids, fileobj, fileformat,  context=None):
        date_today=datetime.today()
        if not ids:
                vals={
                'name':str(date_today),
                'overwrite':False
                }
                ids_id=self.create(cr, uid, vals, context)
        else:      
            ids_id= ids[0]
        this = self.browse(cr, uid, ids_id)
        db_name = cr.dbname
        pool = pooler.get_pool(db_name)
        product_obj=pool.get('product.product')
        categ_obj=pool.get('product.category')
        try:
           # now, the serious things: we read the language file
            """leggo l'intestazione"""
            fileobj.seek(0)
            if fileformat == 'csv':
                reader = csv.reader(fileobj, quotechar='"', delimiter=',')
                # read the first line of the file (it contains columns titles)
                for row in reader:
                    f = row
                    break

            else:
                raise osv.except_osv(('Bad file format: %s'), (fileformat))
                raise Exception(_('Bad file format'))
    
            # read the rest of the file
            line = 1   
            for row in reader:
                        line +=1        
                        """ trovo prodotto"""
                        product_ids = product_obj.search(cr, uid, [('default_code','=',str(row[1]))])    
                        
                        vals={
                                'standard_price':row[35],
                               }# skip empty rows and rows where the translation field (=last fiefd) is empty
                        #print 'banca-->'+str(line)+'name->'+str(vals['name'])+'city->'+str(vals['street'])        
                        if not product_ids:
                                product_id=None #product_obj.create(cr, uid, vals, context=context)
                        else:
                             if this.overwrite:
                                product_id=product_ids[0]
                                product_obj.write(cr, uid, product_id,vals, context=context)
                        #_logger.info("importazione effettuata con successo-->"+str(line))
            return True  
        except IOError:
                        _logger.info("importazione non effettuata ")
 
                        return False 
                        """
                        raise osv.except_osv(_("Errore %s"), _('ricezione disponibilita'))
                        """
    def import_product(self, cr, uid, ids, context=None):
        fileobj = TemporaryFile('w+')
        this = self.browse(cr, uid, ids[0])
        try:
            fileobj.write(base64.decodestring(this.data))
    
            # now we determine the file format
            fileobj.seek(0)
            first_line = fileobj.readline().strip().replace('"', '').replace(' ', '')
            fileformat = first_line.endswith("Cod_pro,Descrizione,Tipologia,Categoria,"#3 
            "Sottocategoria,Cod_Udm,Cod_Iva,Listino_1_ivato,Listino_2_ivato,Listino_3_ivato,"#9 
            "note,Cod_barre,"#11
            "Produttore,Cod_fornitore,Fornitore,codprod_for,"#15
            "Prezzo_forn,note_for,scor_min,Ubicazione,costomedio,"#20
            "ultimo_costo,vol_netto,imbx,imby,imbz,vimb,"#26
            "umpeso,pnetto,plordo,immagine"#30
            ) and 'csv' or 'csv'#46
            
            fileobj.seek(0)
            
            self.load_data_prod_danea( cr, uid, ids ,fileobj, fileformat, context=context)
        finally:
            fileobj.close()
        return True
    
    def load_data_prod_danea(self, cr, uid, ids, fileobj, fileformat,  context=None):
        db_name = cr.dbname
        pool = pooler.get_pool(db_name)
        partner_obj = pool.get('res.partner')
        product_tmp_obj = pool.get('product.template')
        product_obj = pool.get('product.product')
        product_tax = pool.get('product.taxes.rel')
        supplier_obj = pool.get('product.supplierinfo')
        categ_obj=pool.get('product.category')
        um_obj=pool.get('product.uom')
        tax_obj=pool.get('account.tax')
        stock_obj = pool.get('stock.move')
        pricelist_obj = pool.get('product.pricelist')
        pricelist_item_obj = pool.get('product.pricelist.item')
        pricelist_version_obj = pool.get('product.pricelist.version')
 
        
        this = self.browse(cr, uid, ids[0])
        try:
           # now, the serious things: we read the language file
            """leggo l'intestazione"""
            fileobj.seek(0)
            if fileformat == 'csv':
                reader = csv.reader(fileobj, quotechar='"', delimiter=',')
                # read the first line of the file (it contains columns titles)
                for row in reader:
                    f = row
                    break

            else:
                raise osv.except_osv(('Bad file format: %s'), (fileformat))
                raise Exception(_('Bad file format'))
    
            # read the rest of the file
            prod_temp=[]
            line = 1   
            for row in reader:
                line +=1
                if line>100:
                            try:
                              cr.commit()
                            except:
                              cr.rollback()
                            line=1

                F_listino=False
                if this.f_dimensioni==False:    
                    """controllo aliquota iva"""
                    tax_ids = tax_obj.search(cr, uid, [('description','=', row[6])])    
                    if not tax_ids:
                         
                         tax_ids = tax_obj.search(cr, uid, [('description','=', '22')])    
                               
                         #raise osv.except_osv(_("imposta  --> " +  row[6] + " <-- non trovata caricare imposta e riprovare"),_(""))
                  # lets create the language with locale information
                         continue
                    
                    tax_ids_id=tax_ids[0]
                    
                    """controllo l'unità di misura"""
                    if row[5]=='':
                        row[5]='pz'
                    um_ids = um_obj.search(cr, uid, [('name','=', row[5])])    
                    if not um_ids:
                         
                         raise osv.except_osv(_("Unià di misura --> " +  row[5] + " <-- non trovata caricare l'unita di misura e riprovare"),_(""))
                  # lets create the language with locale information
                         break
                    um_ids_id=um_ids[0]
                    """creo il fornitore"""
                    partner_ids = partner_obj.search(cr, uid, [('name','=', row[14])])    
                    if not partner_ids:
                 # lets create the language with locale information
                         vals={
                         'name':row[14],
                         'customer':False,
                         'supplier':True
    
                           }# skip empty rows and rows where the translation field (=last fiefd) is empty
                         partner_ids_id=partner_obj.create(cr, uid, vals, context=context)
                    else:
                         partner_ids_id=partner_ids[0]
                     
                    """creo il produttore"""
                    produttore_ids = partner_obj.search(cr, uid, [('name','=', row[12])])    
                    if not produttore_ids:
                 # lets create the language with locale information
                         vals={
                         'name':row[12],
                         'customer':False,
                         'supplier':True
    
    
                           }# skip empty rows and rows where the translation field (=last fiefd) is empty
                         produttore_ids_id=partner_obj.create(cr, uid, vals, context=context)
                    else:
                         produttore_ids_id=produttore_ids[0]
    
                    """creo la categoria"""
                    categ_ids = categ_obj.search(cr, uid, [('name','=', row[3])])    
                    if not categ_ids:
                 # lets create the language with locale information
                         vals={
                         'name':row[3],
                         'complete_name':row[3]
                           }# skip empty rows and rows where the translation field (=last fiefd) is empty
                         categ_ids_id=categ_obj.create(cr, uid, vals, context=context)
                    else:
                         categ_ids_id=categ_ids[0]
                    """creo sotto categoria"""
                    sotto_categ_ids = categ_obj.search(cr, uid, [('name','=', row[4])])    
                    if not sotto_categ_ids:
                 # lets create the language with locale information
                         vals={
                         'name':row[4],
                         'complete_name':row[4],
                         'parent_id':categ_ids_id
                           }# skip empty rows and rows where the translation field (=last fiefd) is empty
                         sotto_categ_ids_id=categ_obj.create(cr, uid, vals, context=context)
                    else:
                         sotto_categ_ids_id=sotto_categ_ids[0]   
                    if row[2]=='1':
                        track_yes=True
                    else:
                        track_yes=False
                    F_listino=False
                    
                    if F_listino==True:
                        """creo listino 1"""
                        pricelist_ids_1 = pricelist_obj.search(cr, uid, [('name','=', 'Listino_1_ivato')])    
                        if not pricelist_ids_1:
                     # lets create the language with locale information
                             vals={
                             'name':'Listino_1_ivato',
                             'type':'sale',
                               }# skip empty rows and rows where the translation field (=last fiefd) is empty
                             pricelist_ids_1_id=pricelist_obj.create(cr, uid, vals, context=context)
                        else:
                             pricelist_ids_1_id=pricelist_ids_1[0]
                        
                        """creo versione listino 1"""
                        pricelist_version_ids_1 = pricelist_version_obj.search(cr, uid, [('name','=', 'Listino_1_ivato'+'_versione')])    
                        if not pricelist_version_ids_1:
                     # lets create the language with locale information
                             vals={
                             'name':'Listino_1_ivato'+'_versione',
                             'pricelist_id':pricelist_ids_1_id,
         
                               }# skip empty rows and rows where the translation field (=last fiefd) is empty
                             pricelist_version_ids_1_id=pricelist_version_obj.create(cr, uid, vals, context=context)
                        else:
                             pricelist_version_ids_1_id=pricelist_version_ids_1[0]
                            
                        """creo listino 2"""
                        pricelist_ids_2 = pricelist_obj.search(cr, uid, [('name','=', 'Listino_2_ivato')])    
                        if not pricelist_ids_2:
                     # lets create the language with locale information
                             vals={
                             'name':'Listino_2_ivato',
                             'type':'sale',
         
                               }# skip empty rows and rows where the translation field (=last fiefd) is empty
                             pricelist_ids_2_id=pricelist_obj.create(cr, uid, vals, context=context)
                        else:
                             pricelist_ids_2_id=pricelist_ids_2[0]
                        """creo versione listino 2"""
                        pricelist_version_ids_2 = pricelist_version_obj.search(cr, uid, [('name','=', 'Listino_2_ivato'+'_versione')])    
                        if not pricelist_version_ids_2:
                     # lets create the language with locale information
                             vals={
                             'name':'Listino_2_ivato'+'_versione',
                             'pricelist_id':pricelist_ids_2_id,
                               }# skip empty rows and rows where the translation field (=last fiefd) is empty
                             pricelist_version_ids_2_id=pricelist_version_obj.create(cr, uid, vals, context=context)
                        else:
                             pricelist_version_ids_2_id=pricelist_version_ids_2[0]
                             
                        """creo listino 3"""
                        pricelist_ids_3 = pricelist_obj.search(cr, uid, [('name','=', 'Listino_3_ivato')])    
                        if not pricelist_ids_3:
                     # lets create the language with locale information
                             vals={
                             'name':'Listino_3_ivato',
                             'type':'sale',
                               }# skip empty rows and rows where the translation field (=last fiefd) is empty
                             pricelist_ids_3_id=pricelist_obj.create(cr, uid, vals, context=context)
                        else:
                             pricelist_ids_3_id=pricelist_ids_3[0]
                        
                        """creo versione listino 3"""
                        pricelist_version_ids_3 = pricelist_version_obj.search(cr, uid, [('name','=', 'Listino_3_ivato'+'_versione')])    
                        if not pricelist_version_ids_3:
                     # lets create the language with locale information
                             vals={
                             'name':'Listino_3_ivato'+'_versione',
                             'pricelist_id':pricelist_ids_3_id,
         
                             
                               }# skip empty rows and rows where the translation field (=last fiefd) is empty
                             pricelist_version_ids_3_id=pricelist_version_obj.create(cr, uid, vals, context=context)
                        else:
                             pricelist_version_ids_3_id=pricelist_version_ids_3[0]
                           
                    if row[2]=='1':
                        track_yes=True
                    else:
                        track_yes=False
                         
                    if row[7]=='':
                        prezzo=0                
                    else:
                        prezzo_A=str(row[7]).replace('€','').replace('.', '').replace(' ', '')
                        prezzo_B=prezzo_A.replace(',', '')
                        prezzo=float(str(prezzo_B))/100
                    if row[8]=='':
                        prezzo_1= 0        
                    else:
                        prezzo_A=str(row[8]).replace('€','').replace('.', '').replace(' ', '')
                        prezzo_B=prezzo_A.replace(',', '.')
                        prezzo_1=float(str(prezzo_B))/100
                    if row[9]=='':
                        prezzo_2=0          
                    else:
                        prezzo_A=str(row[9]).replace('€','').replace('.', '').replace(' ', '')
                        prezzo_B=prezzo_A.replace(',', '.')
                        prezzo__2=float(str(prezzo_B))/100
                    if row[16]=='':
                        costo=0                
                    else:
                        prezzo_A=str(row[16]).replace('€','').replace('.', '').replace(' ', '')
                        prezzo_B=prezzo_A.replace(',', '.')
                        costo=float(str(prezzo_B))
                    """
                    prod_tmp_ids = product_tmp_obj.search(cr, uid, [('default_code','=', row[0])])
                    vals={
                         #'default_code':sheet.row_values(row)[1]+sheet.row_values(row)[3],#marca
                         'name':row[1],#codice
                         'type':'product',
                         'rental':True,
                         'state':'sellable',
                         'list_price':prezzo,
                         'standard_price':costo,
                         'categ_id': sotto_categ_ids_id,
                         'uom_id':um_ids[0],
                         'uom_po_id':um_ids[0],
                         #'manufacturer':produttore_ids_id,
                         #'manufacturer_pname':str(sheet.row_values(row)[1]),
                         'manufacturer_pref':None,
                        'loc_rack':None,
                        'track_outgoing':None,
                        'track_incoming':None,
                        'track_production':None,
                        'loc_case':None,
                         'ean13':None,
                         #'taxes_id': [(6, 0, [x.id for x in tax_obj.browse(cr,uid,tax_ids,context=context)])],
                         #'supplier_taxes_id':[(6, 0, [x.id for x in tax_obj.browse(cr,uid,tax_ids_acq,context=context)])],
                         #'attribute_line_ids':[(6, 0, [x.id for x in attrib_value_obj.browse(cr,uid,attrib_value_id,context=context)])]
                         }# skip empty rows and rows where the translation field (=last fiefd) is empty
                    if not prod_tmp_ids:
                    # lets create the language with locale information
                        
                       #prod_tmp_ids_id=product_tmp_obj.create(cr, uid, vals, context=context)
                       prod_tmp_ids_id=None
                       prod_temp.append({prod_tmp_ids_id})
                       prod_ids = product_obj.search(cr, uid, [('default_code','=',row[0])])
                       if prod_ids:
                           #product_obj.write(cr,uid,prod_ids[0],{'product_tmpl_id':None})
                           mod_prod.append(prod_ids[0])
                    else:
                        prod_tmp_ids_id=prod_tmp_ids[0]
                    
                    """
                    """creo il prodotto"""
                    if str(row[22]).strip()=='':
                        row[22]=0.0
                    else:
                        row[22]=row[22].replace(',','.')
                        row[22]=float(row[22])
                    if str(row[28]).strip()=='':
                        row[28]=0.0
                    else:
                        row[28]=row[28].replace(',', '.')
                        row[28]=float(row[28])
    
                    if str(row[29]).strip()=='':
                        row[29]=0.0
                    else:
                        row[29]=row[29].replace(',', '.')
                        row[29]=float(row[29])
                    
                    
                
                prod_ids = product_obj.search(cr, uid, [('name','=', row[1])])    
                if prod_ids:
                    prod_id_obj=product_obj.browse(cr, uid,prod_ids[0],context)
                else:
                    prod_id_obj=None
                if this.f_dimensioni==False:
                    vals={
                             'default_code':row[0],#marca
                             'name':row[1],#codice
                             'type':'product',
                             'rental':True,
                             'state':'sellable',
                             'list_price':prezzo,
                             'standard_price':costo,
                             'categ_id': sotto_categ_ids_id,
                             'uom_id':um_ids[0],
                             'uom_po_id':um_ids[0],
                             #'product_tmpl_id':prod_tmp_ids_id,
                             'taxes_id': [(6, 0, [x.id for x in tax_obj.browse(cr,uid,tax_ids,context=context)])],
                             'volume':row[22] or row[23]*row[24]*row[25] or 0.0,
                             'weight_net':row[28] or 0.0,
                             'weight':row[29] or 0.0,
                             'x_imb_x':row[23] or 0.0,
                             'x_imb_y':row[24] or 0.0,
                             'x_imb_z':row[25] or 0.0,
                             #'supplier_taxes_id':[(6, 0, [x.id for x in tax_obj.browse(cr,uid,tax_ids_acq,context=context)])],
                             #'manufacturer':produttore_ids_id,
                             #'manufacturer_pname':row[1],
                             #'manufacturer_pref':row[16],
                            #'loc_rack':row[15],
                            #'track_outgoing':track_yes,
                            #'track_incoming':track_yes,
                            #'track_production':track_yes,
                            #'loc_case':row[10],
                             #'ean13':row[11]
                             }# skip empty rows and rows where the translation field (=last fiefd) is empty
                if not prod_ids:
                    if this.f_dimensioni==False:
                    # lets create the language with locale information
                        prod_ids_id=None
                        prod_ids_id=product_obj.create(cr, uid, vals, context=context)
               
                        """
                        cr.execute('delete from product_taxes_rel where prod_id=%s and (tax_id>=%s and tax_id<=%s)',(prod_ids_id,0,9999))
                    
                        cr.execute('insert into product_taxes_rel (prod_id,tax_id) '
                               'select %s,%s where not exists '
                               '(select * from product_taxes_rel where prod_id=%s and tax_id=%s)',
                               (prod_ids_id, tax_ids_id,prod_ids_id, tax_ids_id))
                    
                        cr.execute('delete from product_supplier_taxes_rel where prod_id=%s and (tax_id>=%s and tax_id<=%s)',(prod_ids_id,0,9999))
                    
                        cr.execute('insert into product_supplier_taxes_rel (prod_id,tax_id) '
                               'select %s,%s where not exists '
                               '(select * from product_supplier_taxes_rel where prod_id=%s and tax_id=%s)', 
                               (prod_ids_id, tax_ids_id,prod_ids_id, tax_ids_id))
                        """
                else:
                    prod_ids_id=prod_ids[0]
                    if this.overwrite==True: 
                       if this.f_dimensioni==False:    
        
                               vals={
                             'standard_price':costo,
        
                              #'uom_id':um_ids[0],
                             #'uom_po_id':um_ids[0],
                             #'product_tmpl_id':prod_tmp_ids_id,
                             #'taxes_id': [(6, 0, [x.id for x in tax_obj.browse(cr,uid,tax_ids,context=context)])],
                             #'supplier_taxes_id':[(6, 0, [x.id for x in tax_obj.browse(cr,uid,tax_ids_acq,context=context)])],
                             #'manufacturer':produttore_ids_id,
                             #'manufacturer_pname':row[1],
                             #'manufacturer_pref':row[16],
                            #'loc_rack':row[15],
                            #'track_outgoing':track_yes,
                            #'track_incoming':track_yes,
                            #'track_production':track_yes,
                            #'loc_case':row[10],
                             #'ean13':row[11]
                             'weight_net':row[28] or 0.0,
                             'weight':row[29] or 0.0,
                                 'x_imb_x':row[23].replace(',','.') or 0.0,
                                 'x_imb_y':row[24].replace(',','.') or 0.0,
                                 'x_imb_z':row[25].replace(',','.') or 0.0,
                                 'volume':row[26].replace(',','.') or float(row[23].replace(',','.') or 0.0)*float(row[24].replace(',','.') or 0.0)*float(row[25].replace(',','.') or 0.0) or 0.0,
                             }# skip empty rows and rows where the translation field (=last fiefd) is empty
                       else:    
    
                            vals={
                                 'x_imb_x':row[23].replace(',','.') or 0.0,
                                 'x_imb_y':row[24].replace(',','.') or 0.0,
                                 'x_imb_z':row[25].replace(',','.') or 0.0,
                                 'volume':row[26].replace(',','.') or float(row[23].replace(',','.') or 0.0)*float(row[24].replace(',','.') or 0.0)*float(row[25].replace(',','.') or 0.0) or 0.0,
                            }

                       if prod_id_obj.default_code==None or str(prod_id_obj.default_code).strip()=='':
                           vals['default_code']=row[0]
                       print 'val_prodotto_2',row[1],vals
                       product_obj.write(cr, uid, prod_ids_id, vals, context)
                       if this.f_dimensioni==True:    
                           product_tmp_obj.write(cr,uid,prod_id_obj.product_tmpl_id.id,vals,context=context)
                prod_ids_rec=product_obj.browse(cr, uid,prod_ids_id,context)
                if this.f_dimensioni==True:
                    templ_ids=product_obj.search(cr,uid,[('product_tmpl_id','=',prod_ids_rec.product_tmpl_id.id)])
                    for product_id_obj in product_obj.browse(cr, uid,templ_ids,context):
                        vals={
                                 'x_imb_x':row[23].replace(',','.') or 0.0,
                                 'x_imb_y':row[24].replace(',','.') or 0.0,
                                 'x_imb_z':row[25].replace(',','.') or 0.0,
                                 'volume':row[26].replace(',','.') or float(row[23].replace(',','.') or 0.0)*float(row[24].replace(',','.') or 0.0)*float(row[25].replace(',','.') or 0.0) or 0.0,
                            }
                        if product_id_obj.default_code==None or str(product_id_obj.default_code).strip()=='':
                           vals['default_code']=row[0]

                        product_obj.write(cr, uid, prod_ids_id, vals, context)
                if prod_ids_id and this.f_dimensioni==False:
                    """creo catena di approvvigionamento"""
                    supplier_ids = supplier_obj.search(cr, uid, [('product_tmpl_id','=', prod_ids_rec.product_tmpl_id.id),('name','=', partner_ids_id)])    
                    vals={
                         'name':partner_ids_id,#codice
                         'product_name':row[1],#qta_gicanza
                         'product_code':row[0],#marca
                         'product_uom':um_ids[0],#codice prodotto fornitore
                         'min_qty':1,
                         'product_tmpl_id':prod_ids_rec.product_tmpl_id.id,
                         
                         }# skip empty rows and rows where the translation field (=last fiefd) is empty
                    if not supplier_ids:
                    # lets create the language with locale information
     
                       if prod_ids_id:
                           supplier_obj.create(cr, uid, vals, context=context)
                    else:
                        if this.overwrite==True: 
                           vals={
                         'name':partner_ids_id,#codice
                         'product_name':row[1],#qta_gicanza
                         'product_code':row[0],#marca
                         #'product_uom':um_ids[0],#codice prodotto fornitore
                         'min_qty':1,
                         'product_tmpl_id':prod_ids_rec.product_tmpl_id.id,
                         
                         }# skip empty rows and rows where the translation field (=last fiefd) is empty
                           supplier_obj.write(cr, uid, supplier_ids[0], vals, context)                        
                if F_listino==True:
    
                    """creo voci di listino personalizzato 1"""       
                    pricelist_item_ids = pricelist_item_obj.search(cr, uid, [('name','=', row[0]),('price_version_id','=',pricelist_version_ids_1_id)])    
                    vals={
                         'name':row[0],#marca
                         'product_id':prod_ids_id,#codice
                         'price_surcharge':prezzo,
                         'price_discount':0,
                         'price_version_id':pricelist_version_ids_1_id
                          }# skip empty rows and rows where the translation field (=last fiefd) is empty
                    if prezzo!=0:
                        if not pricelist_item_ids:
                        # lets create the language with locale information     
                           pricelist_item_ids_id=pricelist_item_obj.create(cr, uid, vals, context=context)
                   
                        else:
                            pricelist_item_ids_id=pricelist_item_ids[0]
                            if this.overwrite==True: 
                               pricelist_item_obj.write(cr, uid, pricelist_item_ids_id, vals, context) 
                        
                    """creo voci di listino personalizzato 2"""       
                    pricelist_item_ids = pricelist_item_obj.search(cr, uid, [('name','=', row[0]),('price_version_id','=',pricelist_version_ids_2_id)])    
                    vals={
                         'name':row[0],#marca
                         'product_id':prod_ids_id,#codice
                         'price_surcharge':prezzo_1,                     
                         'price_discount':0,
                         'price_version_id':pricelist_version_ids_2_id
                          }# skip empty rows and rows where the translation field (=last fiefd) is empty
                    if prezzo_1!=0:
                        if not pricelist_item_ids:
                        # lets create the language with locale information     
                           pricelist_item_ids_id=pricelist_item_obj.create(cr, uid, vals, context=context)
                   
                        else:
                            pricelist_item_ids_id=pricelist_item_ids[0]
                            if this.overwrite==True: 
                               pricelist_item_obj.write(cr, uid, pricelist_item_ids_id, vals, context)  
    
                    """creo voci di listino personalizzato 3"""       
                    pricelist_item_ids = pricelist_item_obj.search(cr, uid, [('name','=', row[0]),('price_version_id','=',pricelist_version_ids_3_id)])    
                    vals={
                         'name':row[0],#marca
                         'product_id':prod_ids_id,#codice
                         'price_surcharge':prezzo_2,                   
                         'price_discount':0,
                         'price_version_id':pricelist_version_ids_3_id
                          }# skip empty rows and rows where the translation field (=last fiefd) is empty
                    if prezzo_2!=0:
                        if not pricelist_item_ids:
                        # lets create the language with locale information     
                           pricelist_item_ids_id=pricelist_item_obj.create(cr, uid, vals, context=context)
                   
                        else:
                            pricelist_item_ids_id=pricelist_item_ids[0]
                            if this.overwrite==True: 
                               pricelist_item_obj.write(cr, uid, pricelist_item_ids_id, vals, context)  
                
                #_logger.info("importazione effettuata con successo")
        except IOError:
            lang = tools.config.get('lang')
            iso_lang = tools.get_iso_codes(lang)
            
            filename = '[lang: %s][format: %s]' % (iso_lang or 'new', fileformat)
            raise osv.except_osv(_("Impossibile leggere ilfile %s"), _(filename))
    @api.one
    def riorg_prodotti(self):
        product_obj = self.env['product.product']
        templ_obj=self.env['product.template']
        presta_product_obj=self.env['prestashop.product']
        product_ids=product_obj.search([('active','=',True)])
        for product_id in product_ids:
            presta_product_ids=presta_product_obj.search([('erp_product_id','=',product_id.id)])
            for presta_id in presta_product_ids:
                print 'presta_id',presta_id#+++
                print 'presta_product_id',presta_id.presta_product_id
                dup_presta_product_ids=presta_product_obj.search([('presta_product_id','=',presta_id.presta_product_id),('presta_product_attr_id','=',presta_id.presta_product_attr_id)])
                dup_line=0
                for dup_presta_product_id in dup_presta_product_ids:
                            dup_line+=1
                            #presta_id_obj=presta_product_obj.browse(dup_presta_product_id)
                            if dup_line>1:
                                print 'dup_presta_product_id.id',dup_presta_product_id.id
                                print 'dup_presta_product_id.product_name',dup_presta_product_id.product_name.id,dup_presta_product_id.product_name.name
                                product_id_obj=product_obj.browse(dup_presta_product_id.product_name.id)
                                dup_presta_product_id.write({'name':'RIORGANIZZATO','need_sync':'no'})
                                if product_id_obj:
                                    product_id_obj.write({'active':False,'loc_rack':'RIORGANIZZATO'})
                                
                        
                                          
class stock_import_inve_webtex(osv.osv):
    """ partner Import """

    _name = "stock.import.inve.webtex"
    _description = "inventario  webtex "
    def _default_location_destination(self, cr, uid, context=None):
        context = context or {}
        if context.get('default_picking_type_id', False):
            pick_type = self.pool.get('stock.picking.type').browse(cr, uid, context['default_picking_type_id'], context=context)
            return pick_type.default_location_dest_id and pick_type.default_location_dest_id.id or False
        return False

    _columns = {
        'name': fields.char('identificativo di ricezione  clienti', size=128 , required=True),
        'data': fields.binary('File', required=False),
        'location_id':fields.many2one('stock.location', 'Punto di stoccaggio da inventariare', required=False,domain=[('usage','=','internal')]), 
        'del_inve': fields.boolean('Elimina inventario  esistente',
                                    help=" Elimina inventario  "
                                         ""),

     }
    _defaults = {  
                            'location_id': _default_location_destination,
                            'name': 'inve-/'+str(time.strftime('%Y-%m-%d %H:%M')),  
                            }
    @api.multi
    def inv_open_tx(self):
        view_ref = self.env['ir.model.data'].get_object_reference('prof_webtex', 'view_import_inventario_webtex')
        view_id = view_ref and view_ref[1] or False,
        my_id=self.create({
                                   'name':   'inve-' + time.strftime('%Y-%m-%d') ,  
                           })
        print 'self.env.context',self.env.context
        print 'my_id',my_id.id
        return {'name':_("Importazione inventario"),
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'stock.import.inve.webtex',
                'res_id': my_id.id,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new',
                'domain': self.env.context,                                 
                'context': self.env.context,                                 
            }


    @api.multi
    def import_inventario(self):
        fileobj = TemporaryFile('w+')
        this = self
        try:
            fileobj.write(base64.decodestring(this.data))
    
            # now we determine the file format
            fileobj.seek(0)
            first_line = fileobj.readline().strip().replace('"', '').replace(' ', '')
            fileformat = first_line.endswith("id,codice,categoria,descrizione,attributi,quantita,prezzo,prc,costo,annulla"#3
                ) and 'csv' or 'csv'#46
            fileobj.seek(0)               
            self.load_data_inv(fileobj, fileformat)
        finally:
            fileobj.close()
        return True
    @api.multi
    def load_data_inv(self,fileobj, fileformat):
        date_today=datetime.today()
        if not self.id:
                vals={
                'name':str(date_today),
                'del_inve':False
                }
                ids_id=self.create(vals)
        else:      
            ids_id= self.id
        active_ids = self.env.context and self.env.context.get('active_ids', False)
        this = self
        product_obj=self.env['product.product']
        templ_obj=self.env['product.template']
        inve_obj = self.env['stock.inventory']
        inve_line_obj = self.env['stock.inventory.line']
        try:
           # now, the serious things: we read the language file
            """leggo l'intestazione"""
            fileobj.seek(0)
            if fileformat == 'csv':
                reader = csv.reader(fileobj, quotechar='"', delimiter=',')
                # read the first line of the file (it contains columns titles)
                for row in reader:
                    f = row
                    break

            else:
                raise osv.except_osv(('Bad file format: %s'), (fileformat))
                raise Exception(_('Bad file format'))
    
            # read the rest of the file
                
            line = 1  ### 
            for inve_id_obj in inve_obj.browse(active_ids):
                if inve_id_obj.state!='confirm':
                    continue
                if self.location_id:
                    inve_id_obj.write({'location_id':self.location_id.id})
                    location_id=self.location_id.id
                else:
                    location_id=inve_id_obj.location_id.id
                
                if self.del_inve==True:
                    for line_obj in inve_id_obj.line_ids:
                        line_obj.unlink()
                
                for row in reader:
                            line +=1        
                            """ trovo prodotto"""
                            
                            print 'row[0]',row[0]
                            if len(str(row[0]).strip())>0:
                                mio_id=str(row[0]).strip()
                                int_id=mio_id
                                product_ids = product_obj.search([('id','=',int_id),('active','in',(True,False,))])    
                            else:
                                product_ids=[]
                            if product_ids==[]:
                                if len(str(row[1]).strip())>0:
                                    product_ids = product_obj.search([('default_code','=',str(row[1]))])    
                            if product_ids==[]:
                                if len(str(row[3]).strip())>0:
                                    product_ids = product_obj.search([('name','=',str(row[3]))])    
                            line=0
                            if len(str(row[6]).strip())>0:
                                prezzo_A=str(row[6]).replace('€','').replace(',', '.').replace(' ', '')
                                prezzo_B=prezzo_A.replace(',', '.')
                                prezzo=float(str(prezzo_B))
                            else:
                                prezzo=None
                            if len(str(row[8]).strip())>0:
                                costo_A=str(row[8]).replace('€','').replace(',', '.').replace(' ', '')
                                costo_B=costo_A.replace(',', '.')
                                costo=float(str(costo_B))
                            else:
                                costo=None
                                prezzo=None
                            active=True#xxxhhh
                            if len(str(row[9]).strip())>0:
                                if str(row[9]).strip().upper()=='S':
                                    active=False
                            if len(str(row[5]).strip())>0:
                                qta_a=str(row[5]).replace('€','').replace(',', '.').replace(' ', '')
                                qta_b=qta_a.replace(',', '.')
                                qta_f=float(str(qta_b))
                            else:
                                qta_f=None
                            for product_id_obj in product_ids:
                                vals={}
                                if active==False:
                                    vals['active']=False
                                if prezzo:
                                    if prezzo>0:
                                        vals['list_price']=prezzo
                                        
                                if costo:
                                    if costo>0:
                                        vals['standard_price']=costo
                                if vals:
                                     product_id_obj.write(vals)
                                     if active==False:
                                        product_ids_2 = product_obj.search([('product_tmpl_id','=',product_id_obj.product_tmpl_id.id),('active','=',True)])    
                                        if product_ids_2:
                                            print 'product_ids_2',product_ids_2
                                        else:
                                            print 'product_ids_2_active',active
            
                                            product_id_obj.product_tmpl_id.write({'active':False})
                                        
                                line+1
                                if len(str(row[4]).strip())>0:
                                    F_attrib=True
                                    for attr_value in product_id_obj.attribute_value_ids:
                                        if str(row[4]).lower().find(str(attr_value.name).lower())<0:
                                            F_attrib=False
                                            continue
                                    if F_attrib==False:
                                        continue
                                vals={
                                        'inventory_id':inve_id_obj.id,
                                        'location_id':location_id,
                                        'product_id':product_id_obj.id,
                                        'product_qty':qta_f,
                                       'theoretical_qty': product_id_obj.qty_available,
                                       'product_uom_id': product_id_obj.uom_id.id,
                                       }# skip empty rows and rows where the translation field (=last fiefd) is empty
                                #print 'banca-->'+str(line)+'name->'+str(vals['name'])+'city->'+str(vals['street'])        
                                inve_line_ids=inve_line_obj.search([('product_id','=',product_id_obj.id),('inventory_id','=',inve_id_obj.id)])
                                if inve_line_ids:
                                    inve_line_ids.write(vals)
                                else:
                                    inve_line_ids.create(vals)
                                break
                        #_logger.info("importazione effettuata con successo-->"+str(line))
            return True  
        except IOError:
                        _logger.info("importazione non effettuata ")
 
                        return False 
                        """
                        raise osv.except_osv(_("Errore %s"), _('ricezione disponibilita'))
                        """

""" importazione Bolla carico e scarico """

class stock_import_ddt_webtex(osv.osv):
    """ partner Import """

    _name = "stock.import.ddt.webtex"
    _description = "ddt  webtex "
    def _default_pick_type(self, cr, uid, context=None):
        context = context or {}
        if context.get('default_picking_type_id', False):
            pick_type = self.pool.get('stock.picking.type').browse(cr, uid, context['default_picking_type_id'], context=context)
            return pick_type and pick_type.id or False
        return False

    _columns = {
        'name': fields.char('identificativo di ricezione  clienti', size=128 , required=True),
        'data': fields.binary('File', required=False),
        'pick_type_id':fields.many2one('stock.picking.type', 'Tipo picking', required=False), 
        'del_ddt': fields.boolean('Elimina ddt  esistente  se picking in bozza',
                                    help=" Elimina ddt  "
                                         ""),

        'prima': fields.boolean('usa codice prima colonna',
                                    help=" prima colonna  "
                                         ""),
        'seconda': fields.boolean('usa codice seconda colonna',
                                    help=" prima colonna  "
                                         ""),

     }
    _defaults = {  
                            'prima': True,
                           'seconda': False,
                            'pick_type_id': _default_pick_type,
                            'name': 'inve-/'+str(time.strftime('%Y-%m-%d %H:%M')),  
                            }
    @api.multi
    def ddt_open_tx(self):
        view_ref = self.env['ir.model.data'].get_object_reference('prof_webtex', 'view_import_ddt_webtex')
        view_id = view_ref and view_ref[1] or False,
        my_id=self.create({
                                   'name':   'ddt-' + time.strftime('%Y-%m-%d') ,  
                           })
        print 'self.env.context',self.env.context
        print 'my_id',my_id.id
        return {'name':_("Importazione ddt"),
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'stock.import.ddt.webtex',
                'res_id': my_id.id,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new',
                'domain': ['id','=',my_id.id],                                 
                'context': self.env.context,                                 
            }


    @api.multi
    def import_ddt(self):
        fileobj = TemporaryFile('w+')
        this = self
        try:
            fileobj.write(base64.decodestring(this.data))
    
            # now we determine the file format
            fileobj.seek(0)
            first_line = fileobj.readline().strip().replace('"', '').replace(' ', '')
            fileformat = first_line.endswith("codice_webtex,codice_amazon,quantita,prezzo"#3
                ) and 'csv' or 'csv'#46
            fileobj.seek(0)               
            self.load_data_ddt(fileobj, fileformat)
        finally:
            fileobj.close()
        return True
    @api.multi
    def load_data_ddt(self,fileobj, fileformat):
        date_today=datetime.today()
        if not self.id:
                vals={
                'name':'ddt-' + time.strftime('%Y-%m-%d'),
                'prima':True,
                'seconda':False,
                }
                ids_id=self.create(vals)
        else:      
            ids_id= self.id
        active_ids = self.env.context and self.env.context.get('active_ids', False)
        active_model = self.env.context and self.env.context.get('active_model', False)
        this = self
        product_obj=self.env['product.product']
        templ_obj=self.env['product.template']
        picking_obj = self.env['stock.picking']
        stock_move_obj = self.env['stock.move']
        sale_line_obj = self.env['sale.order.line']
        sale_obj = self.env['sale.order']
        try:
           # now, the serious things: we read the language file
            """leggo l'intestazione"""
            fileobj.seek(0)
            if fileformat == 'csv':
                reader = csv.reader(fileobj, quotechar='"', delimiter=',')
                # read the first line of the file (it contains columns titles)
                for row in reader:
                    f = row
                    break

            else:
                raise osv.except_osv(('Bad file format: %s'), (fileformat))
                raise Exception(_('Bad file format'))
    
            # read the rest of the file
                
            line=0
            if active_model=='sale.order':
                for sale_id_obj in sale_obj.browse(active_ids):
                    if sale_id_obj.state!='draft':
                        continue
                    if self.del_ddt==True:
                        for line_obj in sale_id_obj.order_line:
                            line_obj.unlink()
                    
                    for row in reader:
                                line +=1        
                                """ trovo prodotto"""
                                
                                print 'row[0]',row[0],'row[1]',row[1]
                                product_ids=[]
                                if self.prima:
                                    if len(row[0].strip())>0:
                                            product_ids = product_obj.search([('default_code','=',row[0].strip()),('active','=',True)])    
                                    if product_ids==[]:
                                            product_ids = product_obj.search([('default_code','=',row[1].strip()),('active','=',True)])    
                                if self.seconda:
                                    if len(str(row[1]).strip())>0:
                                            product_ids = product_obj.search([('default_code','=',row[1].strip()),('active','=',True)])    
                                    if product_ids==[]:
                                            product_ids = product_obj.search([('default_code','=',row[0].strip()),('active','=',True)])    
                                if self.prima==False and self.seconda==False:
                                    if len(row[0].strip())>0:
                                            product_ids = product_obj.search([('default_code','=',row[0].strip()),('active','=',True)])    
                                    if product_ids==[]:
                                            product_ids = product_obj.search([('default_code','=',row[1].strip()),('active','=',True)])    
                                if product_ids:
                                    print 'product_ids',product_ids
                                else:
                                    continue
                                active=True#xxxhhh
                                for product_id_obj in product_ids:
                                    result=sale_line_obj.product_id_change_with_wh(sale_id_obj.pricelist_id.id, product_id_obj.id, qty=float(row[2]),
                                            uom=False, qty_uos=0, uos=False, name='', partner_id=sale_id_obj.partner_id.id,
                                            lang=sale_id_obj.partner_id.lang, update_tax=True, date_order=sale_id_obj.date_order, packaging=False, fiscal_position=sale_id_obj.fiscal_position.id, flag=False, warehouse_id=False)

                                    vals={
                                            'name': result['value']['name'],
                                            'product_id':product_id_obj.id,
                                            'product_uom_qty':row[2],
                                            'price_unit':result['value']['price_unit'],
                                            'tax_id':[(6, 0, [x.id for x in product_id_obj.taxes_id ])],
                                            'product_uom':result['value']['product_uom'],
                                            #'product_uos_qty':row[2],
                                            'order_id':sale_id_obj.id,
                                            'x_imb_x':product_id_obj.x_imb_x,
                                            'x_imb_x':product_id_obj.x_imb_x,
                                            'x_imb_z':product_id_obj.x_imb_z,
                                           }# skip empty rows and rows where the translation field (=last fiefd) is empty
                                    #print 'banca-->'+str(line)+'name->'+str(vals['name'])+'city->'+str(vals['street'])        
                                    sale_line_ids=sale_line_obj.search([('product_id','=',product_id_obj.id),('order_id','=',sale_id_obj.id)])
                                    if sale_line_ids:
                                        sale_line_ids.write(vals)
                                    else:
                                        sale_line_ids.create(vals)
                                    break
                            #_logger.info("importazione effettuata con successo-->"+str(line))
                    
            else:
                line = 1  ### 
                for picking_id_obj in picking_obj.browse(active_ids):
                    if picking_id_obj.state!='draft':
                        continue
                    if self.pick_type_id:
                        picking_id_obj.write({'picking_type_id':self.pick_type_id.id,
                                              'location_id':self.pick_type_id.default_location_src_id.id,
                                              'location_dest_id':self.pick_type_id.default_location_dest_id.id,
                                              
                                              })
                        pick_type_id=self.pick_type_id.id
                    else:
                        pick_type_id=picking_id_obj.picking_type_id.id
                    
                    if self.del_ddt==True:
                        for move_obj in picking_id_obj.move_lines:
                            move_obj.unlink()
                    
                    for row in reader:
                                line +=1        
                                """ trovo prodotto"""
                                
                                print 'row[0]',row[0],'row[1]',row[1]
                                product_ids=[]
                                if self.prima:
                                    if len(row[0].strip())>0:
                                            product_ids = product_obj.search([('default_code','=',row[0].strip()),('active','=',True)])    
                                    if product_ids==[]:
                                            product_ids = product_obj.search([('default_code','=',row[1].strip()),('active','=',True)])    
                                if self.seconda:
                                    if len(str(row[1]).strip())>0:
                                            product_ids = product_obj.search([('default_code','=',row[1].strip()),('active','=',True)])    
                                    if product_ids==[]:
                                            product_ids = product_obj.search([('default_code','=',row[0].strip()),('active','=',True)])    
                                if self.prima==False and self.seconda==False:
                                    if len(row[0].strip())>0:
                                            product_ids = product_obj.search([('default_code','=',row[0].strip()),('active','=',True)])    
                                    if product_ids==[]:
                                            product_ids = product_obj.search([('default_code','=',row[1].strip()),('active','=',True)])    
                                if product_ids:
                                    print 'product_ids',product_ids
                                else:
                                    continue
                                active=True#xxxhhh
                                for product_id_obj in product_ids:
                                    vals={
                                            'name':product_id_obj.name,
                                            'product_id':product_id_obj.id,
                                            'picking_type_id':pick_type_id,
                                            'location_dest_id':picking_id_obj.location_dest_id and picking_id_obj.location_dest_id.id or picking_id_obj.picking_type_id.default_location_dest_id.id,
                                            'location_id':picking_id_obj.location_id and picking_id_obj.location_id.id or picking_id_obj.picking_type_id.default_location_src_id.id,
                                            #'product_qty':row[2],
                                            'product_uom_qty':row[2],
                                            'product_uom': product_id_obj.uom_id.id,
                                            #'product_uos': product_id_obj.uos_id.id,
                                            #'product_uos_qty':row[2],
                                            'picking_id':picking_id_obj.id,
                                           }# skip empty rows and rows where the translation field (=last fiefd) is empty
                                    #print 'banca-->'+str(line)+'name->'+str(vals['name'])+'city->'+str(vals['street'])        
                                    stock_move_ids=stock_move_obj.search([('product_id','=',product_id_obj.id),('picking_id','=',picking_id_obj.id)])
                                    if stock_move_ids:
                                        stock_move_ids.write(vals)
                                    else:
                                        stock_move_ids.create(vals)
                                    break
                            #_logger.info("importazione effettuata con successo-->"+str(line))
            return True  
        except IOError:
                        _logger.info("importazione ddt non effettuata ")
 
                        return False 
                        """
                        raise osv.except_osv(_("Errore %s"), _('ricezione disponibilita'))
                        """

class understock(osv.osv):
    _name = "product.product.understock"
    _description = "prodotti sotto scorta "
    _columns = {
        'name': fields.char('identificativo prodotto', size=128 , required=False),
        'product_id':fields.many2one('product.product', 'Prodotto sotto scorta', required=False), 
        'partner_id':fields.many2one('res.partner', 'fornitore', required=False,domain=[('supplier','=',True)]), 
        'virtual_available': fields.float('Disponibile', digits_compute=dp.get_precision('Product Unit of Measure'),required=False),
        'x_min_stock': fields.float('stock minimo', digits_compute=dp.get_precision('Product Unit of Measure'),required=False),
        'x_rio_stock': fields.float('Riordino', digits_compute=dp.get_precision('Product Unit of Measure'),required=False),
        'bom_count':fields.integer('Con distinta'),
        'kit':fields.boolean('kit')
     }
    _defaults = {  
                            'name': 'understock-/'+str(time.strftime('%Y-%m-%d %H:%M')),  
                            }
    _order = 'bom_count desc,id desc' 
    def product_available_cron(self, cr, uid,ids=None,context=None):
        res = {}###
        product_obj=self.pool.get('product.product')
        understock_obj=self.pool.get('product.product.understock')
        
        understock_ids=understock_obj.search(cr,uid,[('id','>', 0)],context=context)
        for understock_id_obj in understock_obj.browse(cr,uid,understock_ids,context=context):
            if understock_id_obj.product_id:
                if understock_id_obj.product_id.x_rio_stock <= 0:
                                understock_obj.unlink(cr,uid,understock_id_obj.id,context=context)
        
        product_ids=product_obj.search(cr,uid,[('active','=', True),('x_rio_stock','>', 0)],context=context)#
        for product in product_obj.browse(cr, uid, product_ids, context=context):#
            if product.x_rio_stock <= 0:
                continue
            understock_ids=understock_obj.search(cr,uid,[('product_id','=',product.id)],context=context)
            partner_id=None
            if product.seller_ids:
                partner_id=product.seller_ids[0].name.id
            if understock_ids:
                for understock_id in understock_ids:
                    if product.x_rio_stock>0:
                        understock_obj.write(cr,uid,understock_id,{'virtual_available':product.virtual_available,
                                                                   'x_min_stock':product.x_min_stock,
                                                                   'x_rio_stock':product.x_rio_stock,
                                                                   'bom_count':product.bom_count,
                                                                   'kit':product.x_imposta,
                                                                   'partner_id':partner_id
                                                               },context=context)
                    else:                        
                        understock_obj.unlink(cr,uid,understock_id)
            else:
                if product.x_rio_stock>0:
                    understock_obj.create(cr,uid,{'virtual_available':product.virtual_available,
                                              'x_min_stock':product.x_min_stock,
                                              'x_rio_stock':product.x_rio_stock,
                                              'bom_count':product.bom_count,
                                              'kit':product.x_imposta,
                                              'product_id':product.id,
                                              'partner_id':partner_id                              },context=context) 
        
        return {}
    @api.multi
    def create_mo(self):
        active_ids=self.env.context.get('active_ids',[])
        cr, uid, context = self.env.args
        for understock_id_obj in  self.browse(active_ids):#0000000#####
            understock_id_obj.product_id.with_context(lang=context.get('lang','it_IT'),active_ids=[understock_id_obj.product_id.id],active_id=understock_id_obj.product_id.id).create_mo()

    @api.multi
    def purchase_open(self):
        active_ids=self.env.context.get('active_ids',[])
        
        cr, uid, context = self.env.args
        product_ids=[]
        for understock_id_obj in  self.browse(active_ids):#0000000#####
                product_ids.append(understock_id_obj.product_id.id)
        purchase_webtex_obj=self.env['product.product.purchase.webtex']
        
        context={}
        context['active_ids']=product_ids
        return purchase_webtex_obj.with_context(lang=context.get('lang','it_IT'),active_ids=product_ids).purchase_open_webtex()
        
"""
crezione ordine di acquisto dalle varianti
"""
class product_product_purchase(osv.osv_memory):
    """ partner Import """

    _name = "product.product.purchase.webtex"
    _description = "ordine di acquisto da variente  webtex "
    def _default_location_destination(self, cr, uid, context=None):
        context = context or {}
        if context.get('default_picking_type_id', False):
            pick_type = self.pool.get('stock.picking.type').browse(cr, uid, context['default_picking_type_id'], context=context)
            return pick_type.default_location_dest_id and pick_type.default_location_dest_id.id or False
        return False
    def _default_picking_type_id(self, cr, uid, context=None):
        context = context or {}
        if context.get('default_picking_type_id', False):
            pick_type = self.pool.get('stock.picking.type').browse(cr, uid, context['default_picking_type_id'], context=context)
            return pick_type and pick_type.id or False
        return False

    def _default_partner_search(self, cr, uid, context=None):
        context = context or {}
        if context.get('default_partner_id', False):
            partner_id = self.pool.get('res.partner').browse(cr, uid, context['default_partner_id'], context=context)
            return partner_id and partner_id.id or False
        return False

    _columns = {
        'name': fields.char('identificativo di ordine di acquisto', size=128 , required=True),
        'partner_id':fields.many2one('res.partner', 'Fornitore non predefinito', required=False,domain=[('supplier','=',True)]), 
        'picking_type_id': fields.many2one('stock.picking.type', 'tipo entrata merce', help="This will determine picking type of incoming shipment", required=False),
        'location_id':fields.many2one('stock.location', 'Punto di stoccaggio', required=False,domain=[('usage','=','internal')]), 
     }
    _defaults = {  
                            'picking_type_id': _default_picking_type_id,
                            'location_id': _default_location_destination,
                            'partner_id': _default_partner_search,
                            'name': 'purchase-/'+str(time.strftime('%Y-%m-%d %H:%M')),  
                            }
    @api.multi
    def purchase_open_webtex(self):
        view_ref = self.env['ir.model.data'].get_object_reference('prof_webtex', 'view_product_product_purchase_webtex')
        view_id = view_ref and view_ref[1] or False,
        my_id=self.create({
                                   'name':   'purchase-' + time.strftime('%Y-%m-%d') ,  
                           })
        #print 'self.env.context',self.env.context
        #print 'my_id',my_id.id
        return {'name':_("Creazione  ordine di acquisto"),
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'product.product.purchase.webtex',
                'res_id': my_id.id,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new',
                'domain': self.env.context,                                 
                'context': self.env.context,                                 
            }


    @api.multi
    def purchase_create_webtex(self):
        date_today=datetime.today()
        if not self.id:
                vals={
                'name':str(date_today),
                }
                ids_id=self.create(vals)
        else:      
            ids_id= self.id
        active_ids = self.env.context and self.env.context.get('active_ids', False)
        this = self
        product_obj=self.env['product.product']
        product_supplier_obj=self.env['product.supplierinfo']
        puchase_obj=self.env['purchase.order']
        purchase_line_obj=self.env['purchase.order.line']
        try:                
            line = 1  ### 
            prod_supp=[]
            purchase_ord=[]
            purchase_order={}
            partner_ids=[]
            for product_id_obj in product_obj.browse(active_ids):
                supplier_ids=product_supplier_obj.search([('product_tmpl_id','=',product_id_obj.product_tmpl_id.id)])
                if supplier_ids:
                    prod_supp.append({'partner_id':supplier_ids[0].name,'product_id':product_id_obj,'product_qty':supplier_ids[0].qty,'supplierinfo':supplier_ids[0],'min_qty':supplier_ids[0].min_qty})
                else:
                    prod_supp.append({'partner_id':self.partner_id,'product_id':product_id_obj,'product_qty':1,'supplierinfo':None,'min_qty':0})
            print 'prod_supp',prod_supp
            for prod_supp_id in prod_supp:
                if prod_supp_id['partner_id'].id in partner_ids:
                    purchase_id=purchase_order[prod_supp_id['partner_id'].id]
                else:
                    partner_ids.append(prod_supp_id['partner_id'].id)
                    vals = {
                        'partner_id': prod_supp_id['partner_id'].id,
                        'date_order':  date_today,
                        'picking_type_id':self.picking_type_id.id,
                        'location_id': self.location_id.id,
                        'invoice_method': 'picking',
                        'pricelist_id': prod_supp_id['partner_id'].property_product_pricelist_purchase and prod_supp_id['partner_id'].property_product_pricelist_purchase.id,
        #                'state': 'confirmed',
                        'validator' : self.env.uid,
                       'payment_term_id': prod_supp_id['partner_id'].property_supplier_payment_term.id
                    }
                    purchase_id_obj=puchase_obj.create(
                                                   vals
                                                   )
                    purchase_order[prod_supp_id['partner_id'].id]=purchase_id_obj.id
                    purchase_ord.append(purchase_id_obj.id)
                    purchase_id=purchase_id_obj.id
                if prod_supp_id['partner_id'].id:
                        lang = prod_supp_id['partner_id'].lang
                        context = self._context.copy()
                        #context['lang']=lang,
                        context['partner_id']=prod_supp_id['partner_id'].id
                        self.env.context=context
                date_order = date_today
                product=prod_supp_id['product_id']
                dummy, name = product.name_get()[0]
                if product.description_purchase:
                            name += '\n' + product.description_purchase
                precision =self.env['decimal.precision'].precision_get('Product Unit of Measure')
                if prod_supp_id['supplierinfo']:
                    dt = purchase_line_obj._get_date_planned(prod_supp_id['supplierinfo'], str(date_order.strftime('%Y-%m-%d  %H:%M:%S'))).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                else:
                    dt= date_today
                result_product_purchase=purchase_line_obj.onchange_product_id(prod_supp_id['partner_id'].property_product_pricelist_purchase.id, product.id, prod_supp_id['product_qty'], product.uom_id.id,prod_supp_id['partner_id'].id)
                if product.x_rio_stock>0:
                        pruchase_qty=product.x_rio_stock
                else:
                    if product.virtual_available<0:
                        pruchase_qty=product.virtual_available*-1
                    else:
                        pruchase_qty=prod_supp_id['product_qty']
                if pruchase_qty<prod_supp_id['min_qty']:
                    pruchase_qty=prod_supp_id['min_qty']
                values = {
                            'product_id': product.id,
                            'name': name,
                            'date_planned': dt,
                            'product_qty':  pruchase_qty,
                            'price_unit':result_product_purchase['value']['price_unit'],
                            #'price_subtotal': line.subtotal,
                            #'price_subtotal': line.subtotal,
                            'order_id': purchase_id,
                            'sale_order_id': None,
    #                        'state': 'confirmed',
                            'taxes_id':[(6, 0, [x.id for x in product.supplier_taxes_id ])],

                        }
                #print 'values',values
                line_id = purchase_line_obj.create(values)
            if len(purchase_ord)==1:
                view_ref = self.env['ir.model.data'].get_object_reference('purchase', 'purchase_order_form')
            else:
                view_ref = self.env['ir.model.data'].get_object_reference('purchase', 'purchase_order_tree')
                
            view_id = view_ref and view_ref[1] or False,
            return {'name':_("ordini creati"),
                'view_mode': 'form' if len(purchase_ord)==1 else 'tree,form',
                'view_id': view_id if len(purchase_ord)==1 else False,
                'view_type': 'form',
                'res_model': 'purchase.order',
                'res_id': purchase_ord[0] if len(purchase_ord)==1 else None,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'normal',
                'domain': [('id','in',tuple(purchase_ord))],                                 
                'context': self.env.context,                                 
            }
        except IOError:
                        _logger.info("creazione non effettuata ")
 
                        return False 
                        """
                        raise osv.except_osv(_("Errore %s"), _('ricezione disponibilita'))
                        """

        
class product_template(osv.osv):
    def _price_subtax_(self, cr, uid, ids, field_name, arg, context=None):
        cur_obj = self.pool.get('res.currency')
        tax_obj = self.pool.get('account.tax')
        product_obj = self.pool.get('product.product')
        res = {}
        if context is None:
            context = {}
        """"---"""
        for templ_id_obj in self.browse(cr, uid, ids, context=context):
            price = templ_id_obj.lst_price
            qty = 1.0
            if templ_id_obj.product_variant_ids:
                product_id=templ_id_obj.product_variant_ids[0].id
            else:
                product_ids=product_obj.search(cr, uid, [('product_tmpl_id','=',templ_id_obj.id)], context=context)
                if product_ids:
                    product_id=product_ids[0]
                else:
                    product_id=None
            taxes = tax_obj.compute_all(cr, uid, templ_id_obj.taxes_id, price, qty,
                                        product_id,
                                        templ_id_obj.company_id.partner_id)
            if templ_id_obj.pricelist_id.currency_id:
                cur = templ_id_obj.pricelist_id.currency_id
            else:
                cur= templ_id_obj.company_id.partner_id.property_product_pricelist.currency_id
            res[templ_id_obj.id] = cur_obj.round(cr, uid, cur, taxes['total_included'])
        return res
    _inherit = "product.template"
    _columns = {
        'description': fields.html('Description', translate=True, sanitize=False, help="Rich-text/HTML version of the message (placeholders may be used here)"),
        'x_price_subtax': fields.function(_price_subtax_, string='Sub_tax', digits_compute= dp.get_precision('Product Price')),
        'x_imb_x': fields.float('Lunghezza', digits_compute=dp.get_precision('Product Price'),required=False),
        'x_imb_y': fields.float('Altezza', digits_compute=dp.get_precision('Product Price'),required=False),
        'x_imb_z': fields.float('Profondità', digits_compute=dp.get_precision('Product Price'),required=False),

    }
    def create_variant_ids(self, cr, uid, ids, context=None):
        res=super(product_template, self).create_variant_ids(cr, uid, ids, context=context)
        if res:
            tmpl_ids = self.browse(cr, uid, ids, context=context)
            product_obj = self.pool.get("product.product")
            for tmpl_id in tmpl_ids:
    
                # list of values combination
                for variant_id in tmpl_id.product_variant_ids:
                    if variant_id.standard_price==0:
                            product_obj.write(cr,uid,variant_id.id,{'standard_price':tmpl_id.standard_price})

        return res
    def onchange_dim(self, cr, uid, ids, x_imb_x=0, x_imb_y=0,x_imb_z=0, context=None):
        """ Changes UoM if product_id changes.
        @param x_imb_x: x_imb_y x_imb_z
        @return:  Dictionary of changed values
        """
        res = {}
        res['value'] = {
                'volume': x_imb_x*x_imb_y*x_imb_z,
            }
        return res

class product_attribute_value(osv.osv):
    _inherit = "product.attribute.value"
    _columns = {
                    'x_fatt_molt': fields.float('Fatt.Moltiplicativo', digits_compute=dp.get_precision('Product UoS')),

                    } 
    _defaults = {  
        'x_fatt_molt': 1,  
        }
    _order = 'attribute_id,name'

class product_product(osv.osv):
    def _price_subtax_(self, cr, uid, ids, field_name, arg, context=None):
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        res = {}
        if context is None:
            context = {}
        """"---"""
        for product_id_obj in self.browse(cr, uid, ids, context=context):
            price = product_id_obj.lst_price
            qty = 1.0
            taxes = tax_obj.compute_all(cr, uid, product_id_obj.taxes_id, price, qty,
                                        product_id_obj.id,
                                        product_id_obj.company_id.partner_id)
            if product_id_obj.pricelist_id.currency_id:
                cur = product_id_obj.pricelist_id.currency_id
            else:
                cur= product_id_obj.company_id.partner_id.property_product_pricelist.currency_id
            res[product_id_obj.id] = cur_obj.round(cr, uid, cur, taxes['total_included'])
        return res

    def _product_available_webtex(self, cr, uid, ids, field_names=None, arg=False, context=None):
        context = context or {}
        field_names = field_names or []
        order_point_obj=self.pool.get('stock.warehouse.orderpoint')
        #understock_obj=self.pool.get('product.product.understock')
        min_stock_ids=[]
        domain_products = [('product_id', 'in', ids)]
                    
        domain_quant, domain_move_in, domain_move_out = [], [], []
        domain_quant_loc, domain_move_in_loc, domain_move_out_loc = self._get_domain_locations(cr, uid, ids, context=context)
        domain_move_in += self._get_domain_dates(cr, uid, ids, context=context) + [('state', 'not in', ('done', 'cancel', 'draft'))] + domain_products
        domain_move_out += self._get_domain_dates(cr, uid, ids, context=context) + [('state', 'not in', ('done', 'cancel', 'draft'))] + domain_products
        domain_quant += domain_products

        if context.get('lot_id'):
            domain_quant.append(('lot_id', '=', context['lot_id']))
        if context.get('owner_id'):
            domain_quant.append(('owner_id', '=', context['owner_id']))
            owner_domain = ('restrict_partner_id', '=', context['owner_id'])
            domain_move_in.append(owner_domain)
            domain_move_out.append(owner_domain)
        if context.get('package_id'):
            domain_quant.append(('package_id', '=', context['package_id']))

        domain_move_in += domain_move_in_loc
        domain_move_out += domain_move_out_loc
        moves_in = self.pool.get('stock.move').read_group(cr, uid, domain_move_in, ['product_id', 'product_qty'], ['product_id'], context=context)
        moves_out = self.pool.get('stock.move').read_group(cr, uid, domain_move_out, ['product_id', 'product_qty'], ['product_id'], context=context)

        #min_stock = self.pool.get('stock.warehouse.orderpoint').read_group(cr, uid, domain_products, ['product_id', 'product_min_qty','product_max_qty','qty_multiple'], ['product_id'], context=context)
        min_stock_sv = self.pool.get('stock.warehouse.orderpoint').read_group(cr, uid, domain_products, ['product_id', 'product_min_qty','product_max_qty','qty_multiple'], ['product_id'], context=context)
        multi_stock=min_stock_sv
        max_stock=min_stock_sv
        #print 'read_min_stock',moves_out
        #print 'read_min_stock',min_stock

        domain_quant += domain_quant_loc
        quants = self.pool.get('stock.quant').read_group(cr, uid, domain_quant, ['product_id', 'qty'], ['product_id'], context=context)
        quants = dict(map(lambda x: (x['product_id'][0], x['qty']), quants))

        moves_in = dict(map(lambda x: (x['product_id'][0], x['product_qty']), moves_in))
        moves_out = dict(map(lambda x: (x['product_id'][0], x['product_qty']), moves_out))
        min_stock_sv = dict(map(lambda x: (x['product_id'][0], x['product_min_qty']), min_stock_sv))
        max_stock = dict(map(lambda x: (x['product_id'][0], x['product_max_qty']), max_stock))
        multi_stock = dict(map(lambda x: (x['product_id'][0], x['qty_multiple']), multi_stock))
        #print 'min_stock','multi_stock',min_stock,multi_stock
        res = {}###
        for product in self.browse(cr, uid, ids, context=context):
            id = product.id
            prod_var_ids=[]
            # rocco li 09-07-2018 tolto l'assegnazione dell'order point per tutte le varianti
            #if product.product_tmpl_id.product_variant_ids:
            """ if fittizio ripristinare quello sopra"""
            if prod_var_ids:
                prod_var_ids += [x.id for x in product.product_tmpl_id.product_variant_ids]
                domain_prod_orderpoint = [('product_id', 'in', prod_var_ids)]
                order_point = self.pool.get('stock.warehouse.orderpoint').read_group(cr, uid, domain_prod_orderpoint, ['product_id', 'product_min_qty','product_max_qty','qty_multiple'], ['product_id'], context=context)
                #print 'order_point',order_point
                
                min_stock = dict(map(lambda x: (x['product_id'][0], x['product_min_qty']), order_point))
                #print 'min_stock',min_stock
                if min_stock:
                    min_id=order_point[0]['product_id'][0]
                else:
                    min_id=id
                    min_stock=min_stock_sv
            else:
                min_id=id
                min_stock=min_stock_sv
            qty_available = float_round(quants.get(id, 0.0), precision_rounding=product.uom_id.rounding)
            incoming_qty = float_round(moves_in.get(id, 0.0), precision_rounding=product.uom_id.rounding)
            outgoing_qty = float_round(moves_out.get(id, 0.0), precision_rounding=product.uom_id.rounding)
            virtual_available = float_round(quants.get(id, 0.0) + moves_in.get(id, 0.0) - moves_out.get(id, 0.0), precision_rounding=product.uom_id.rounding)
            x_multi_stock = float_round(multi_stock.get(id, 0.0), precision_rounding=product.uom_id.rounding)
            if min_stock_sv.get(id, 0.0)>0:
                x_min_stock = float_round(min_stock_sv.get(id, 0.0), precision_rounding=product.uom_id.rounding)
            else:
                x_min_stock = float_round(min_stock.get(min_id, 0.0), precision_rounding=product.uom_id.rounding)
                
            x_max_stock = float_round(max_stock.get(id, 0.0), precision_rounding=product.uom_id.rounding)
            x_imposta=False
            if product.bom_ids:
                if product.bom_ids[0].type=='phantom':
                   x_imposta=True         
            if min_stock or min_stock_sv:
                if x_min_stock>0:
                    if  virtual_available<x_min_stock:
                        if x_multi_stock>0:
                            x_rio_stock=(virtual_available-x_min_stock)/x_multi_stock
                            if x_rio_stock<0:
                                x_rio_stock*=-1
                            if int(x_rio_stock)!=x_rio_stock:
                                   x_rio_stock=int(x_rio_stock)+1
                            x_rio_stock= x_rio_stock*(x_multi_stock)
                            x_rio_stock=float_round(x_rio_stock, precision_rounding=product.uom_id.rounding)    
                        else:
                            x_rio_stock=float_round(x_min_stock , precision_rounding=product.uom_id.rounding)    
                            
                    else:
                        x_rio_stock=float_round(0.0, precision_rounding=product.uom_id.rounding)    
            
                else:
                        if virtual_available<0:
                            x_rio_stock=float_round(-1*virtual_available, precision_rounding=product.uom_id.rounding)    
                        else:
                            x_rio_stock=float_round(0.0, precision_rounding=product.uom_id.rounding)                                
            else:
                if  virtual_available<0:
                    x_rio_stock=float_round(-1* virtual_available , precision_rounding=product.uom_id.rounding)    
                else:
                    x_rio_stock=float_round(0.0, precision_rounding=product.uom_id.rounding)    
                    
            if product.product_tmpl_id.seller_ids:
                product_code = (product.product_tmpl_id.seller_ids[0].product_code or '') +''+ (product.product_tmpl_id.seller_ids[0].product_name or '')
            else:
                product_code=None

            """  
            understock_ids=understock_obj.search(cr,uid,[('product_id','=',id)],context=context)
            if understock_ids:
                for understock_id in understock_ids:
                    if x_rio_stock>0:
                        understock_obj.write(cr,uid,understock_id,{'virtual_available':virtual_available,
                                                                   'x_min_stock':x_min_stock,
                                                                   'x_rio_stock':x_rio_stock,
                                                                   'bom_count':product.bom_count
                                                               },context=context)
                    else:
                        understock_obj.unlink(cr,uid,understock_id)
            else:
                if x_rio_stock>0:
                    understock_obj.create(cr,uid,{'virtual_available':virtual_available,
                                              'x_min_stock':x_min_stock,
                                              'x_rio_stock':x_rio_stock,
                                              'bom_count':product.bom_count},context=context) 
            """
            res[id] = {
                'qty_available': qty_available,
                'incoming_qty': incoming_qty,
                'outgoing_qty': outgoing_qty,
                'virtual_available': virtual_available,
                'x_min_stock': x_min_stock,
                'x_rio_stock': x_rio_stock,
                'x_imposta': x_imposta,
                'x_cod_for': product_code,
            }
        return res
    def _search_product_quantity_webtex(self, cr, uid, obj, name, domain, context):

        res = []
        for field, operator, value in domain:
            #to prevent sql injections
            assert field in ('qty_available', 'virtual_available', 'incoming_qty', 'outgoing_qty','x_min_stock','x_rio_stock','x_imposta',), 'Invalid domain left operand'
            assert operator in ('<', '>', '=', '!=', '<=', '>=','||','|','OR'), 'Invalid domain operator'
            assert isinstance(value, (float, int, str)), 'Invalid domain right operand'

            if operator == '=':
                operator = '=='

            ids = []
            if name == 'qty_available' and (value != 0.0 or operator not in  ('==', '>=', '<=')):
                res.append(('id', 'in', self._search_qty_available(cr, uid, operator, value, context)))
            else:
                product_ids = self.search(cr, uid, [], context=context)
                if product_ids:
                    #TODO: Still optimization possible when searching virtual quantities
                    for element in self.browse(cr, uid, product_ids, context=context):
                        if isinstance(value,(float,int)):
                            if eval(str(element[field]) + operator + str(value)):##
                                ids.append(element.id)
                        else:
                            if eval(str(element[field]) + operator + str(element[value])):##
                                ids.append(element.id)
                            
                    res.append(('id', 'in', ids))
        return res


    _inherit = "product.product"
    _columns = {
        'description': fields.html('Description', translate=True, sanitize=False, help="Rich-text/HTML version of the message (placeholders may be used here)"),
        'x_qta_dist': fields.float('qta per distinta', digits_compute=dp.get_precision('Product Price')),
        'x_price_subtax': fields.function(_price_subtax_, string='Subtax', digits_compute= dp.get_precision('Product Price')),
        'standard_price': fields.property(type = 'float', digits_compute=dp.get_precision('Product Price'), 
                                          help="Cost price of the product template used for standard stock valuation in accounting and used as a base price on purchase orders. "
                                               "Expressed in the default unit of measure of the product.",
                                          groups="base.group_user", string="Cost Price"),
        'x_imb_x': fields.float('Lunghezza', digits_compute=dp.get_precision('Product Price'),required=False),
        'x_imb_y': fields.float('Altezza', digits_compute=dp.get_precision('Product Price'),required=False),
        'x_imb_z': fields.float('Profondità', digits_compute=dp.get_precision('Product Price'),required=False),
        'volume': fields.float('Volume', help="The volume in m3."),
        'description_purchase': fields.text('Purchase Description',translate=True,
            help="A description of the Product that you want to communicate to your suppliers. "
                 "This description will be copied to every Purchase Order, Receipt and Supplier Invoice/Refund."),
        'qty_available': fields.function(_product_available_webtex, multi='qty_available',
            type='float', digits_compute=dp.get_precision('Product Unit of Measure'),
            string='Quantity On Hand',
            fnct_search=_search_product_quantity_webtex,
            help="Current quantity of products.\n"
                 "In a context with a single Stock Location, this includes "
                 "goods stored at this Location, or any of its children.\n"
                 "In a context with a single Warehouse, this includes "
                 "goods stored in the Stock Location of this Warehouse, or any "
                 "of its children.\n"
                 "stored in the Stock Location of the Warehouse of this Shop, "
                 "or any of its children.\n"
                 "Otherwise, this includes goods stored in any Stock Location "
                 "with 'internal' type."),
        'virtual_available': fields.function(_product_available_webtex, multi='qty_available',
            type='float', digits_compute=dp.get_precision('Product Unit of Measure'),
            string='Forecast Quantity',
            fnct_search=_search_product_quantity_webtex,
            help="Forecast quantity (computed as Quantity On Hand "
                 "- Outgoing + Incoming)\n"
                 "In a context with a single Stock Location, this includes "
                 "goods stored in this location, or any of its children.\n"
                 "In a context with a single Warehouse, this includes "
                 "goods stored in the Stock Location of this Warehouse, or any "
                 "of its children.\n"
                 "Otherwise, this includes goods stored in any Stock Location "
                 "with 'internal' type."),

        'x_min_stock': fields.function(_product_available_webtex, multi='qty_available',
            type='float', digits_compute=dp.get_precision('Product Unit of Measure'),
            string='Scorta minima',
            fnct_search=_search_product_quantity_webtex,
            help="Scorta minima "),
        'x_rio_stock': fields.function(_product_available_webtex, multi='qty_available',
            type='float', digits_compute=dp.get_precision('Product Unit of Measure'),
            string='qtà Riordino',
            fnct_search=_search_product_quantity_webtex,
            help="quantità da riordinare"),
        'x_imposta': fields.function(_product_available_webtex, multi='qty_available',
            type='boolean', 
            string='kit',
            fnct_search=_search_product_quantity_webtex,
            help="Kit"),

        'x_cod_for': fields.function(_product_available_webtex, multi='qty_available',
            type='char', 
            string='Cod.fornitore',
            #fnct_search=_search_product_quantity_webtex,
            help="Codice fornitore"),


     }
    def name_get(self, cr, user, ids, context=None):
                if context is None:##xx##
                    context = {}
                
                #if context.get('x_name_attr',None)==None:
                   #res=super(product_product, self).name_get(cr, user, ids, context)
                   #return res

                if isinstance(ids, (int, long)):
                    ids = [ids]
                if not len(ids):
                    return []
        
                def _name_get(d):#xxx
                    name = d.get('name','')
                    code = context.get('display_default_code', True) and d.get('default_code',False) or False
                    if code:
                        """ 15-07-2017 rocco Cesetti """
                        name = '%s [%s]' % (name,code)
                        """ 15-07-2017 rocco Cesetti """
                    return (d['id'], name)
        
                partner_id = context.get('partner_id', False)
                if partner_id:
                    partner_ids = [partner_id, self.pool['res.partner'].browse(cr, user, partner_id, context=context).commercial_partner_id.id]
                else:
                    partner_ids = []
        
                # all user don't have access to seller and partner
                # check access and use superuser
                self.check_access_rights(cr, user, "read")
                self.check_access_rule(cr, user, ids, "read", context=context)
        
                result = []
                for product in self.browse(cr, SUPERUSER_ID, ids, context=context):
                    variant = ", ".join([v.name for v in product.attribute_value_ids ])
                    if context.get('x_name_attr',None):
                        if  variant.lower().find(context['x_name_attr'].lower())<0:
                            continue  
                    name = variant and "%s (%s)" % (product.name, variant) or product.name
                    sellers = []
                    if partner_ids:
                        sellers = filter(lambda x: x.name.id in partner_ids, product.seller_ids)
                        #sellers=[]
                    if sellers:
                        for s in sellers:
                            seller_variant = s.product_name and (
                                variant and "%s (%s)" % (s.product_name, variant) or s.product_name
                                ) or False
                            mydict = {
                                      'id': product.id,
                                      'name': seller_variant or name,
                                      'default_code': s.product_code or product.default_code,
                                      }
                            result.append(_name_get(mydict))
                    else:
                        mydict = {
                                  'id': product.id,
                                  'name': name,
                                  'default_code': product.default_code,
                                  }
                        result.append(_name_get(mydict))
                #print 'get_name',result
                return result

    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
        if name.find('%%%')<0:
            res=super(product_product, self).name_search(cr, user,name=name, args=args, operator=operator,context=context, limit=limit)
            return res
        else:
                    name_attr=name[name.find('%%%')+3:len(name)]
                    name=name[0:name.find('%%%')]
                    if not args:
                        args = []
                    if name:
                        positive_operators = ['=', 'ilike', '=ilike', 'like', '=like']
                        ids = []
                        if operator in positive_operators:
                            ids = self.search(cr, user, [('default_code','=',name)]+ args, limit=limit, context=context)
                            if not ids:
                                ids = self.search(cr, user, [('ean13','=',name)]+ args, limit=limit, context=context)
                        if not ids and operator not in expression.NEGATIVE_TERM_OPERATORS:
                            # Do not merge the 2 next lines into one single search, SQL search performance would be abysmal
                            # on a database with thousands of matching products, due to the huge merge+unique needed for the
                            # OR operator (and given the fact that the 'name' lookup results come from the ir.translation table
                            # Performing a quick memory merge of ids in Python will give much better performance
                            ids = self.search(cr, user, args + [('default_code', operator, name)], limit=limit, context=context)
                            if not limit or len(ids) < limit:
                                # we may underrun the limit because of dupes in the results, that's fine
                                limit2 = (limit - len(ids)) if limit else False
                                ids += self.search(cr, user, args + [('name', operator, name), ('id', 'not in', ids)], limit=limit2, context=context)
                        elif not ids and operator in expression.NEGATIVE_TERM_OPERATORS:
                            ids = self.search(cr, user, args + ['&', ('default_code', operator, name), ('name', operator, name)], limit=limit, context=context)
                        if not ids and operator in positive_operators:
                            ptrn = re.compile('(\[(.*?)\])')
                            res = ptrn.search(name)
                            if res:
                                ids = self.search(cr, user, [('default_code','=', res.group(2))] + args, limit=limit, context=context)
                    else:
                        ids = self.search(cr, user, args, limit=limit, context=context)
                    if context is None:
                        context = {}
                    context['x_name_attr']=name_attr
                    result = self.name_get(cr, user, ids, context=context)
        return result
    @api.model
    @api.returns('self', lambda value:value.id)
    def create(self, vals):
        if hasattr(self._ids, '__iter__'):
            if self._ids:
                for myself in self:#0000000
                        if vals.get('description_purchase',None)==None:
                            vals['description_purchase']=myself.product_tmpl_id.description_purchase
                        
                        if vals.get('standard_price',0)<=0:
                            vals['standard_price']=myself.product_tmpl_id.standard_price
                        if vals.get('x_imb_x',0)<=0:
                            vals['x_imb_x']=myself.product_tmpl_id.x_imb_x
                        if vals.get('x_imb_y',0)<=0:
                            vals['x_imb_y']=myself.product_tmpl_id.x_imb_y
                        if vals.get('x_imb_z',0)<=0:
                            vals['x_imb_z']=myself.product_tmpl_id.x_imb_z
                        if vals.get('volume',0)<=0:
                            vals['volume']=myself.product_tmpl_id.x_imb_z*myself.product_tmpl_id.x_imb_y*myself.product_tmpl_id.x_imb_x
            else:
                        if vals.get('description_purchase',None)==None:
                            vals['description_purchase']=self.product_tmpl_id.description_purchase
                        
                        if vals.get('standard_price',0)<=0:
                            vals['standard_price']=self.product_tmpl_id.standard_price
                        if vals.get('x_imb_x',0)<=0:
                            vals['x_imb_x']=self.product_tmpl_id.x_imb_x
                        if vals.get('x_imb_y',0)<=0:
                            vals['x_imb_y']=self.product_tmpl_id.x_imb_y
                        if vals.get('x_imb_z',0)<=0:
                            vals['x_imb_z']=self.product_tmpl_id.x_imb_z
                        if vals.get('volume',0)<=0:
                            vals['volume']=self.product_tmpl_id.x_imb_z*self.product_tmpl_id.x_imb_y*self.product_tmpl_id.x_imb_x
                
        else:
                    if vals.get('description_purchase',None)==None:
                            vals['description_purchase']=self.product_tmpl_id.description_purchase
                    if vals.get('standard_price',0)<=0:
                        vals['standard_price']=self.product_tmpl_id.standard_price
                    if vals.get('x_imb_x',0)<=0:
                            vals['x_imb_x']=self.product_tmpl_id.x_imb_x
                    if vals.get('x_imb_y',0)<=0:
                            vals['x_imb_y']=self.product_tmpl_id.x_imb_y
                    if vals.get('x_imb_z',0)<=0:
                            vals['x_imb_z']=self.product_tmpl_id.x_imb_z
                    if vals.get('volume',0)<=0:
                            vals['volume']=self.product_tmpl_id.x_imb_z*self.product_tmpl_id.x_imb_y*self.product_tmpl_id.x_imb_x
        res=super(product_product, self).create(vals)
        return res
    @api.multi
    def write(self, vals):
        print 'product_write',vals
        if hasattr(self._ids, '__iter__'):
            if self._ids:
                for myself in self:
                   if vals.has_key('description_purchase'):
                       if vals.get('description_purchase',None)==None:#
                                vals['description_purchase']=myself.product_tmpl_id.description_purchase
                   if vals.get('standard_price',None)==None:
                        if myself.standard_price:
                            vals['standard_price']=myself.standard_price
                        else:
                                vals['standard_price']=myself.product_tmpl_id.standard_price
                   if vals.get('x_imb_x',0)<=0:
                            vals['x_imb_x']=myself.product_tmpl_id.x_imb_x###
                   if vals.get('x_imb_y',0)<=0:
                            vals['x_imb_y']=myself.product_tmpl_id.x_imb_y
                   if vals.get('x_imb_z',0)<=0:
                            vals['x_imb_z']=myself.product_tmpl_id.x_imb_z
                   if vals.get('volume',0)<=0:
                            vals['volume']=myself.product_tmpl_id.x_imb_z*myself.product_tmpl_id.x_imb_y*myself.product_tmpl_id.x_imb_x
                
            else:
                    if vals.has_key('description_purchase'):
                        if vals.get('description_purchase',None)==None:
                            vals['description_purchase']=self.product_tmpl_id.description_purchase
                    if vals.get('standard_price',None)==None:
                        if self.standard_price:
                            vals['standard_price']=self.standard_price
                        else:
                                vals['standard_price']=self.product_tmpl_id.standard_price
                    if vals.get('x_imb_x',0)<=0:
                            vals['x_imb_x']=self.product_tmpl_id.x_imb_x
                    if vals.get('x_imb_y',0)<=0:
                            vals['x_imb_y']=self.product_tmpl_id.x_imb_y
                    if vals.get('x_imb_z',0)<=0:
                            vals['x_imb_z']=self.product_tmpl_id.x_imb_z
                    if vals.get('volume',0)<=0:
                            vals['volume']=self.product_tmpl_id.x_imb_z*self.product_tmpl_id.x_imb_y*self.product_tmpl_id.x_imb_x
                
        else:
            if vals.has_key('description_purchase'):
                if vals.get('description_purchase',None)==None:
                            vals['description_purchase']=self.product_tmpl_id.description_purchase
            if vals.get('standard_price',None)==None:
                        if self.standard_price:
                                vals['standard_price']=self.standard_price
                        else:
                                vals['standard_price']=self.product_tmpl_id.standard_price
                            
            if vals.get('x_imb_x',0)<=0:
                            vals['x_imb_x']=self.product_tmpl_id.x_imb_x
            if vals.get('x_imb_y',0)<=0:
                            vals['x_imb_y']=self.product_tmpl_id.x_imb_y
            if vals.get('x_imb_z',0)<=0:
                            vals['x_imb_z']=self.product_tmpl_id.x_imb_z
            if vals.get('volume',0)<=0:
                            vals['volume']=self.product_tmpl_id.x_imb_z*self.product_tmpl_id.x_imb_y*self.product_tmpl_id.x_imb_x
        res=super(product_product, self).write(vals)
        return res
    def onchange_dim(self, cr, uid, ids, x_imb_x=0, x_imb_y=0,x_imb_z=0, context=None):
        """ Changes UoM if product_id changes.
        @param x_imb_x: x_imb_y x_imb_z
        @return:  Dictionary of changed values
        """
        res = {}
        res['value'] = {
                'volume': x_imb_x*x_imb_y*x_imb_z,
            }
        return res
    @api.multi
    def create_mo(self):
        proc_obj = self.env["procurement.order"]
        warehouse_obj = self.env["stock.warehouse"]
        active_ids=self.env.context.get('active_ids',[])
        cr, uid, context = self.env.args
        production_ord=[]
        ware_id_obj=warehouse_obj.search([('manufacture_to_resupply','=',True)])
        for product_id_obj in  self.browse(active_ids):#0000000#####
                        if product_id_obj.x_rio_stock>0 and len(product_id_obj.bom_ids):
                                    #newdate = datetime.strptime(datetime.today(), '%Y-%m-%d %H:%M:%S') - relativedelta(days=product_id_obj.product_id.produce_delay or 0.0)
                                    for bom_id in product_id_obj.bom_ids:
                                        if bom_id.product_id.id==product_id_obj.id:
                                            newdate = datetime.today()
                                            vals = {
                                                            'name': product_id_obj.name,
                                                            'origin': product_id_obj.name,
                                                            'company_id': product_id_obj.company_id.id,
                                                            'date_planned': newdate,
                                                            'product_id': product_id_obj.id,
                                                            'bom_id':bom_id.id,
                                                            'product_qty': product_id_obj.x_rio_stock,
                                                            'product_uom': product_id_obj.uom_id.id,
                                                            'product_uos_qty': product_id_obj.x_rio_stock,
                                                            'product_uos': product_id_obj.uos_id.id,
                                                            'location_id': ware_id_obj[0].lot_stock_id.id,
                                                            #'warehouse_id': 1,
                                            }
                                            proc_id=proc_obj.create(vals)
                                            res_proc=proc_id.make_mo()
                                            production_ord.append(proc_id.production_id.id)
                                            proc_id.production_id.action_assign()
                                            proc_id.production_id.force_production()
                                            proc_id.production_id.action_produce(production_id=proc_id.production_id.id,production_qty=proc_id.production_id.product_qty,production_mode='consume_produce')
                                            break
        if len(production_ord)==1:
                view_ref = self.env['ir.model.data'].get_object_reference('mrp', 'mrp_production_form_view')
        else:
                view_ref = self.env['ir.model.data'].get_object_reference('mrp', 'mrp_production_tree_view')
                
        view_id = view_ref and view_ref[1] or False,
        return {'name':_("ordini creati"),
                'view_mode': 'form' if len(production_ord)==1 else 'tree,form',
                'view_id': view_id if len(production_ord)==1 else False,
                'view_type': 'form',
                'res_model': 'mrp.production',
                'res_id': production_ord[0] if len(production_ord)==1 else None,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'normal',
                'domain': [('id','in',tuple(production_ord))],                                 
                'context': self.env.context,                                 
            }





class sale_order_line(osv.osv):
    _inherit='sale.order.line'
    def _attribute_value_id_(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if context is None:
            context = {}
        """"---"""
        for line_id_obj in self.browse(cr, uid, ids, context=context):
            res[line_id_obj.id] = tuple([line.name.encode() for line in line_id_obj.product_id.attribute_value_ids])
        return res
    
    _columns = {
        'x_attribute_value_ids': fields.function(_attribute_value_id_, string='Attributi',type='char'),
                                    }
    @api.model
    @api.returns('self', lambda value:value.id)
    def create(self, vals):
        sale_obj=self.env['sale.order']##
        tax_obj=self.env['account.tax']
        tax_incl=[]
        precision = self.env['decimal.precision'].precision_get('Account')
        tax_id=vals.get('tax_id',None)
        print 'tax_id',tax_id,vals['order_id']
        partner_id_obj=self.env['sale.order'].browse(vals.get('order_id',None)).partner_id
        pos_fiscal_obj=self.pool.get('account.fiscal.position')##
        if  partner_id_obj:
            if partner_id_obj.property_account_position:
                            pos_fiscal_obj = self.env['account.fiscal.position'].browse(partner_id_obj.property_account_position.id)
            else:    
                            pos_fiscal_obj = self.env['account.fiscal.position'].search([('country_id','=',partner_id_obj.country_id.id)])
                            if pos_fiscal_obj:
                                pos_fiscal_obj=pos_fiscal_obj[0]

        else:
            pos_fiscal_obj=None
        if sale_obj.browse(vals['order_id']).name.find('SO')<0:
            if tax_id:#
                if hasattr(tax_id, '__iter__'):
                    if hasattr(tax_id[0][2], '__iter__'):
                        tax_ids_obj=tax_obj.search([('id','in',tax_id[0][2])])
                    else:
                        tax_ids_obj=tax_obj.search([('id','=',tax_id[0][2])])

                    for  tax_id_obj in tax_ids_obj:
                       tax_id_old_obj=tax_id_obj#x
                       if pos_fiscal_obj:
                           if tax_id_obj.price_include==False:
                               tax_amount_old=float(1+tax_id_old_obj.amount)
                               price_unit_old=float(vals['price_unit'])
                               campo_appox_old=(price_unit_old * (tax_amount_old))*(10**precision)
                               compo_int_old=int(campo_appox_old)
                               diff_old=campo_appox_old-compo_int_old
                               print 'create_diff',diff_old,compo_int_old,campo_appox_old
                               if diff_old>=0.51:#0,60:
                                           valore_old=price_unit_old * (tax_amount_old)
                               else:
                                           valore_old=0.00
                                           valore_old=float(compo_int_old)
                                           print 'valore_old',valore_old
                                           valore_old=valore_old/(10**precision)
                                           print 'valore_old',valore_old
                               vals['price_unit']=round(valore_old, precision)
                               """ nuova aliquota """
                               tax_id_obj = pos_fiscal_obj.map_tax(tax_id_obj)
                               tax_amount_new=float(1+tax_id_obj.amount)                               
                               price_unit_new=float(vals['price_unit'])
                               campo_appox_new=(price_unit_new / (tax_amount_new))*(10**precision)
                               compo_int_new=int(campo_appox_new)
                               diff_new=campo_appox_new-compo_int_new
                               print 'create_diff',diff_new,compo_int_new,campo_appox_new
                               if diff_new>=0.51:#0,60:
                                           valore_new=price_unit_new / (tax_amount_new)
                               else:
                                           valore_new=0.00
                                           valore_new=float(compo_int_new)
                                           print 'valore_new',valore_new
                                           valore_new=valore_new/(10**precision)
                                           print 'valore_new',valore_new
                               vals['price_unit']=round(valore_new, precision)

                       tax_id_obj = pos_fiscal_obj.map_tax(tax_id_obj)
                       tax_incl_ids_obj=tax_obj.search([('active','=',True),('company_id','=',sale_obj.browse(vals['order_id']).company_id.id),('type_tax_use','in',('sale','all')),('active','=',True),('amount','=',tax_id_obj.amount),('price_include','=',True)])
                       for tax_incl_id_obj in tax_incl_ids_obj: 
                           tax_incl.append(tax_incl_id_obj.id)
                           if vals.get('price_unit',None):
                               price_unit=float(vals['price_unit'])
                               tax_amount=float(1+tax_incl_id_obj.amount)
                               campo_appox=(price_unit * (tax_amount))*(10**precision)
                               compo_int=int(campo_appox)
                               diff=campo_appox-compo_int
                               print 'create_diff',diff,compo_int,campo_appox
                               if diff>=0.51:#0,60:
                                   valore=price_unit * (tax_amount)
                               else:
                                   valore=0.00
                                   valore=float(compo_int)
                                   print 'valore',valore
                                   valore=valore/(10**precision)
                                   print 'valore',valore
                               if tax_id_old_obj.price_include==False:
                                   vals['price_unit']=round(valore, precision)
                               vals['tax_id']=[(6, 0, [tax_incl[0]])]
                               break
                       break
                    
                       
    
        res=super(sale_order_line, self).create(vals)
        return res


class account_invoice_tax(models.Model):
    _inherit = 'account.invoice.tax' 
                            #Do not touch _name it must be same as _inherit
    @api.v8
    def compute(self, invoice):
        tax_grouped = {}
        currency = invoice.currency_id.with_context(date=invoice.date_invoice or x_fields.Date.context_today(invoice))
        company_currency = invoice.company_id.currency_id
        for line in invoice.invoice_line:
            #sub_tot=(line.price_unit*line.quantity)*(1 - (line.discount or 0.0) / 100.0)
            #""" rocco cesetti 29-08-2018
            taxes = line.invoice_line_tax_id.compute_all(
                (line.price_unit * (1 - (line.discount or 0.0) / 100.0)),
                line.quantity, line.product_id, invoice.partner_id)['taxes']
            #""" 
            #taxes = line.invoice_line_tax_id.compute_all(
            #    sub_tot,
            #    1.00, line.product_id, invoice.partner_id)['taxes']
            #print 'sub_tot',sub_tot
            #print 'taxes',taxes
            for tax in taxes:
                val = {
                    'invoice_id': invoice.id,
                    'name': tax['name'],
                    'amount': tax['amount'],
                    'manual': False,
                    'sequence': tax['sequence'],
                    'base': currency.round(tax['price_unit'] * line['quantity']),
                    #'base': currency.round(tax['price_unit']),
                }
                tax_ids_obj = self.env['account.tax'].search([('name','=',tax['name'])])
                if tax_ids_obj:
                    val['tax_val_code'] = tax_ids_obj[0].amount
                else:
                    val['tax_val_code']=0.0
                #print 'tax_val_code',tax['tax_code_id'],val['tax_val_code']
                if invoice.type in ('out_invoice','in_invoice'):
                    val['base_code_id'] = tax['base_code_id']
                    val['tax_code_id'] = tax['tax_code_id']
                    val['base_amount'] = currency.compute(val['base'] * tax['base_sign'], company_currency, round=False)
                    val['tax_amount'] = currency.compute(val['amount'] * tax['tax_sign'], company_currency, round=False)
                    val['account_id'] = tax['account_collected_id'] or line.account_id.id
                    val['account_analytic_id'] = tax['account_analytic_collected_id']
                else:
                    val['base_code_id'] = tax['ref_base_code_id']
                    val['tax_code_id'] = tax['ref_tax_code_id']
                    val['base_amount'] = currency.compute(val['base'] * tax['ref_base_sign'], company_currency, round=False)
                    val['tax_amount'] = currency.compute(val['amount'] * tax['ref_tax_sign'], company_currency, round=False)
                    val['account_id'] = tax['account_paid_id'] or line.account_id.id
                    val['account_analytic_id'] = tax['account_analytic_paid_id']

                # If the taxes generate moves on the same financial account as the invoice line
                # and no default analytic account is defined at the tax level, propagate the
                # analytic account from the invoice line to the tax line. This is necessary
                # in situations were (part of) the taxes cannot be reclaimed,
                # to ensure the tax move is allocated to the proper analytic account.
                if not val.get('account_analytic_id') and line.account_analytic_id and val['account_id'] == line.account_id.id:
                    val['account_analytic_id'] = line.account_analytic_id.id

                key = (val['tax_code_id'], val['base_code_id'], val['account_id'])
                if not key in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['base'] += val['base']
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base_amount'] += val['base_amount']
                    tax_grouped[key]['tax_amount'] += val['tax_amount']

        for t in tax_grouped.values():
            t['base'] = currency.round(t['base'])
            t['amount'] = currency.round(t['base']* t['tax_val_code'])
            #t['amount'] = currency.round(t['amount'])
            t['base_amount'] = currency.round(t['base_amount'])

            #t['tax_amount'] = currency.round(t['tax_amount'])
            t['tax_amount'] = currency.round(t['base_amount'] * t['tax_val_code'])
        #if 'tax_val_code' in tax_grouped:
        
        return tax_grouped

    @api.v7
    def compute(self, cr, uid, invoice_id, context=None):
        recs = self.browse(cr, uid, [], context)
        invoice = recs.env['account.invoice'].browse(invoice_id)
        return account_invoice_tax.compute(recs, invoice)
class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.multi
    def _check_routing(self,product, warehouse_id):
        return super(SaleOrderLine, self)._check_routing(product, warehouse_id)
    @api.multi
    def product_id_change_with_wh(
            self, pricelist, product, qty=0, uom=False, qty_uos=0,
            uos=False, name='', partner_id=False, lang=False,
            update_tax=True, date_order=False, packaging=False,
            fiscal_position=False, flag=False, warehouse_id=False
    ):
        res = super(SaleOrderLine, self).product_id_change(
            pricelist=pricelist, product=product, qty=qty, uom=uom,
            qty_uos=qty_uos, uos=uos, name=name,
            partner_id=partner_id, lang=lang, update_tax=update_tax,
            date_order=date_order, packaging=packaging,
            fiscal_position=fiscal_position, flag=flag)
        product_id_obj=None
        product_stock=False
        if product:
            product_obj = self.env['product.product']
            product_uom_obj = self.env['product.uom']
            lang = self.env['res.partner'].browse(partner_id).lang
            product_id_obj = product_obj.with_context(lang=lang,partner_id=partner_id).browse(product)
        if product_id_obj:
            variant = ", ".join([v.name for v in product_id_obj.attribute_value_ids ])
            res['value']['name'] = variant and "%s (%s)" % (product_id_obj.name, variant) or product_id_obj.name      

        if not product:
            res['value'].update({'product_packaging': False})
            return res

        # set product uom in context to get virtual stock in current uom
        context=self.env.context
        if 'product_uom' in res.get('value', {}):
            # use the uom changed by super call
            context = dict(context, uom=res['value']['product_uom'])
        elif uom:
            # fallback on selected
            context = dict(context, uom=uom)

        #update of result obtained in super function
        product_obj = product_obj.with_context(context).browse(product)
        res['value'].update({'product_tmpl_id': product_obj.product_tmpl_id.id, 'delay': (product_obj.sale_delay or 0.0)})

        # Calling product_packaging_change function after updating UoM
        res_packing = self.product_packaging_change(pricelist, product, qty, uom, partner_id, packaging )
        res['value'].update(res_packing.get('value', {}))
        return res

class sale_shop(osv.osv):
    _inherit = "sale.shop"
    _columns = {
        'x_tag':fields.char('Tag id Negozio', size=64, required=False, readonly=False),
        'warehouse':fields.many2one('stock.warehouse', 'Magazzino', required=False),
        'x_chiudi':fields.boolean('Chiudi Picking', required=False), 
        'x_from_journal_id':fields.many2one('account.journal', 'Sezionale di pagamento da sostituire', required=False),
        'x_to_journal_id':fields.many2one('account.journal', 'Sezionale di pagamento in sostituzione', required=False),
       'x_no_mail':fields.boolean('no mail Picking', required=False), 
       'x_no_change':fields.boolean('no cambio stato', required=False), 
       'x_id_order_state':fields.integer('stato da inviare')
           }
class sale_order(osv.osv):
    _inherit = 'sale.order'

    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        res=super(sale_order, self)._amount_all(cr, uid, ids, field_name=field_name, arg=arg, context=context)
        cur_obj = self.pool.get('res.currency')
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id]['amount_qty'] =  0.0
            val2 = 0.0
            for line in order.order_line:
                val2 += line.product_uom_qty
                #print 'val2',val2
            res[order.id]['amount_qty'] = val2
        return res

    def _state_invoice(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if context is None:
            context = {}
        """"---"""
        
        for sale_id_obj in self.browse(cr, SUPERUSER_ID, ids, context):
            #for invoice_id_obj in sale_ids_obj.invoice_ids:
                res[sale_id_obj.id]=''
                if sale_id_obj.partner_id.vat:
                    res[sale_id_obj.id]='CONVERTIRE-IN-FATTURA-'
                    for invoice_id_obj in sale_id_obj.invoice_ids:
                            if invoice_id_obj.journal_id.name.lower().find('corrispe')<0:
                                    res[sale_id_obj.id]='CONVERTITO-IN_FATTURA-'
                                    break
                for invoice_id_obj in sale_id_obj.invoice_ids:
                    if invoice_id_obj.state =='cancel':
                        state='Fattura annullata'
                    elif invoice_id_obj.state !='paid':
                        state='In attesa di pagamento'
                    elif invoice_id_obj.state  == 'paid' and  invoice_id_obj.payment_ids and invoice_id_obj.payment_ids[0].journal_id.name.lower().find('contrassegno')>=0 :
                        state='Contrassegno'
                    elif invoice_id_obj.state  == 'paid' and invoice_id_obj.payment_ids and invoice_id_obj.payment_ids[0].journal_id.name.lower().find('contrassegno')<0:
                        state='Pagato'             
                    else:
                        state='In attesa di pagamento'                        
                    res[sale_id_obj.id] += state +'-'+ str(invoice_id_obj.number or '')+' '#...ggg
                if res[sale_id_obj.id]=='':
                    res[sale_id_obj.id]='attesa corrispettivo o fattura'
                if sale_id_obj.x_invoice_state!=res[sale_id_obj.id]:
                    self.write(cr,SUPERUSER_ID,sale_id_obj.id,{'x_invoice_state':res[sale_id_obj.id]})
                #break
            #break
        return res
    def _state_picking(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if context is None:
            context = {}
        """"---"""
        
        
        for sale_id_obj in self.browse(cr, SUPERUSER_ID, ids, context):
            res[sale_id_obj.id]=''
            for picking_id_obj in sale_id_obj.picking_ids:
                if picking_id_obj.state in ['confirmed','waiting']:
                    state='Attesa merce'
                elif picking_id_obj.state == 'cancel':
                    state='Annullato'
                elif picking_id_obj.state == 'done':
                    state='spedito'
                elif picking_id_obj.state == 'assigned':
                    state='pronto da preparare'
                else:
                    state='Attesa merce'
                    
                if picking_id_obj.name.find('OUT')>=0 or picking_id_obj.name.find('DS')>=0:
                    res[sale_id_obj.id] += state + '-'+ picking_id_obj.name + ' '
            if res[sale_id_obj.id]=='':
                    res[sale_id_obj.id]='Creare picking'
            if sale_id_obj.x_picking_state!=res[sale_id_obj.id]:
                self.write(cr,SUPERUSER_ID,sale_id_obj.id,{'x_picking_state':res[sale_id_obj.id]})
                #break
            
            #break
        return res
    def _amount_all_wrapper(self, cr, uid, ids, field_name, arg, context=None):
        """ Wrapper because of direct method passing as parameter for function fields """
        return self._amount_all(cr, uid, ids, field_name, arg, context=context)
    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('sale.order.line').browse(cr, uid, ids, context=context):
            result[line.order_id.id] = True
        return result.keys()
    _columns = {
        'x_y_invoice_state': fields.function(_state_invoice, string='Stato Fattura',type='char'),
        'x_y_picking_state': fields.function(_state_picking, type='char', string='Stato picking'),          
        'x_invoice_state':fields.char('Stato Fattura', size=256, required=False, readonly=True),
        'x_picking_state': fields.char('Stato picking', size=256, required=False, readonly=True),
        'amount_untaxed': fields.function(_amount_all_wrapper, digits_compute=dp.get_precision('account_2_cifre'), string='Untaxed Amount',
            store={
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },
            multi='sums', help="The amount without tax.", track_visibility='always'),
        'amount_tax': fields.function(_amount_all_wrapper, digits_compute=dp.get_precision('account_2_cifre'), string='Taxes',
            store={
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },
            multi='sums', help="The tax amount."),
        'amount_total': fields.function(_amount_all_wrapper, digits_compute=dp.get_precision('account_2_cifre'), string='Total',
            store={
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },
            multi='sums', help="The total amount."),

        'amount_qty': fields.function(_amount_all_wrapper, digits_compute=dp.get_precision('account_2_cifre'), string='Totale qtà',
            store={
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },
            multi='sums', help="The total amount."),
        
                                
                
        
                                }
    def create(self,cr,uid, vals, context=None):
        if vals.get('origin',None):
            shop_obj=self.pool.get('sale.shop')    
            shop_ids=shop_obj.search(cr,uid,[('id','>',0)],context=context)
            for shop_id_obj in shop_obj.browse(cr,uid,shop_ids,context=context):
                    print 'shop_id_obj.x_tag',shop_id_obj.x_tag
                    if shop_id_obj.x_tag:
                        print 'vals',vals
                        if vals.get('origin',None).find(shop_id_obj.x_tag)>=0:
                            inizio=vals.get('origin',None).find(shop_id_obj.x_tag)
                            fine=len(vals.get('origin',None))
                            print 'vals_name',vals.get('name',''),'shop_id_obj.x_tag',shop_id_obj.x_tag
                            sale_ids=self.search(cr, uid, [('origin','=',vals.get('origin','xxxxxx')),('company_id','=',vals.get('company_id',1))],context=context)
                            if sale_ids:#pppp
                                vals['name']=vals['origin'][inizio:fine].replace('(','').replace(')','')+'.ref'                             
                                vals['origin']=vals['origin']+'.ref'                              
                            else:
                                vals['name']=vals['origin'][inizio:fine].replace('(','').replace(')','')
                            vals['shop_id']=shop_id_obj.id
                            vals['warehouse_id']=shop_id_obj.warehouse.id

        if vals.get('partner_id',None):
                partner_obj=self.pool.get('res.partner')    
                partner_id_obj=partner_obj.browse(cr,uid,vals.get('partner_id',None),context=context)
                if partner_id_obj:
                    vals['company_id']=partner_id_obj.company_id.id
                """
                partner_invoice_id_obj=partner_obj.browse(cr,uid,vals.get('partner_invoice_id',None),context=context)
                if partner_invoice_id_obj and partner_invoice_id_obj!=partner_id_obj:
                        partner_obj.write(cr,uid,partner_invoice_id_obj.id,{})
                partner_shipping_id_obj=partner_obj.browse(cr,uid,vals.get('partner_shipping_id',None),context=context)
                if partner_shipping_id_obj and partner_shipping_id_obj!=partner_id_obj:
                        partner_obj.write(cr,uid,partner_shipping_id_obj.id,{})
                """
                pricelist_obj=self.pool.get('product.pricelist')
                print 'pricelist_id',vals['pricelist_id']
                pricelist_id_obj=pricelist_obj.browse(cr,uid,int(vals['pricelist_id']),context=context)
                print 'pricelist_id_obj',pricelist_id_obj
                pos_fiscal_obj=self.pool.get('account.fiscal.position')
                pos_fiscal_ids=pos_fiscal_obj.search(cr,uid,[('active','=',True),('country_id','=',partner_id_obj.country_id.id)],context=context)
                print 'pos_fiscal_ids',pos_fiscal_ids
                for pos_fiscal_id_obj in pos_fiscal_obj.browse(cr,uid,pos_fiscal_ids,context=context):
                        print 'pos_fiscal_id_obj',pos_fiscal_id_obj
                        print 'listino currency',pricelist_id_obj.currency_id.id
                        print 'company currency',pos_fiscal_id_obj.company_id.currency_id.id
                        if pos_fiscal_id_obj.company_id.currency_id.id==pricelist_id_obj.currency_id.id:
                            vals['fiscal_position']=pos_fiscal_id_obj.id
                            vals['company_id']=pos_fiscal_id_obj.company_id.id
                            break
                        else:
                            vals['fiscal_position']=pos_fiscal_id_obj.id
                            vals['company_id']=pos_fiscal_id_obj.company_id.id
                        
        print 'prima_create_vals', vals                   
        res=super(sale_order, self).create(cr,uid,vals,context=context)
        print 'dopo_res',res
        my_ord=self.browse(cr,uid,res,context=context)
        if my_ord.currency_id.name=='GBP':
                    pos_fiscal_ids=pos_fiscal_obj.search(cr,uid,[('active','=',True),('country_id','=',partner_id_obj.country_id.id)],context=context)
                    for pos_fiscal_id_obj in pos_fiscal_obj.browse(cr,uid,pos_fiscal_ids,context=context):
                            if pos_fiscal_id_obj.company_id.currency_id.id==my_ord.currency_id.id:
                                vals={}
                                vals['fiscal_position']=pos_fiscal_id_obj.id
                                vals['company_id']=pos_fiscal_id_obj.company_id.id
                                self.write(cr,uid,res,vals,context=context)
                                property_account_payable=my_ord.partner_id.property_account_payable
                                property_account_receivable=my_ord.partner_id.property_account_receivable
                                property_account_payable = pos_fiscal_id_obj.map_account(property_account_payable)
                                property_account_receivable = pos_fiscal_id_obj.map_account(property_account_receivable)
                                self.pool.get('res.partner').write(cr,uid,my_ord.partner_id.id,{
                                    'company_id':vals['company_id'],
                                    'property_account_position':vals['fiscal_position'],
                                    'property_account_payable':property_account_payable,
                                    'property_account_receivable':property_account_receivable,
                                    'property_product_pricelist':my_ord.pricelist_id.id,
                                    },context=context)       
                                break
            
        return res
    @api.multi
    def write(self, vals):
        try:
            if vals.get('x_invoice_state',None):
                if vals['x_invoice_state'].find('Pagato')<0:
                    if self.x_invoice_state.find('Pagato')>=0:
                        ps_obj = self.env['prestashop.order']
                        ps_ids_obj=ps_obj.search([('erp_id','=',self.id)])
                        for ps_id_obj in ps_ids_obj:
                            log_presa_obj=self.env['prestashop.order.log']
                            log_presa_obj.create({'name':self.name,
                                         'object_name_save':ps_id_obj.object_name,
                                         'object_name':'LINK_ORDER_ERROR_PAGA',
                                         'ur_id':self.id,
                                         'erp_id':self.id,
                                         'presta_id':ps_id_obj.presta_id
                                         })
                if vals['x_invoice_state'].find('Contrassegno')<0:
                    if self.x_invoice_state.find('Contrassegno')>=0:
                        ps_obj = self.env['prestashop.order']
                        ps_ids_obj=ps_obj.search([('erp_id','=',self.id)])
                        for ps_id_obj in ps_ids_obj:
                            log_presa_obj=self.env['prestashop.order.log']
                            log_presa_obj.create({'name':self.name,
                                         'object_name_save':ps_id_obj.object_name,
                                         'object_name':'LINK_ORDER_ERROR_CONTRA',
                                         'ur_id':self.id,
                                         'erp_id':self.id,
                                         'presta_id':ps_id_obj.presta_id
                                         })
        except:
            print 'sale_order_write_error'
            
        res=super(sale_order, self).write(vals)
        
        if vals.get('state',None):
            if vals['state']=='done':
                ps_obj = self.env['prestashop.order']
                ps_ids_obj=ps_obj.search([('erp_id','=',self.id)])
                for ps_id_obj in ps_ids_obj:
                    log_presa_obj=self.env['prestashop.order.log']
                    log_presa_obj.create({'name':self.name,
                                 'object_name_save':ps_id_obj.object_name,
                                 'object_name':'UNLINK_ORDER',
                                 'ur_id':self.id,
                                 'erp_id':self.id,
                                 'presta_id':ps_id_obj.presta_id
                                 })
                    #ps_id_obj.unlink()
                
                
        return res

    @api.multi
    def del_unlink_ps_order_paid(self):
                log_presta_obj=self.env['prestashop.order.log']
                log_presta_ids_obj=log_presta_obj.search([('erp_id','=',self.id)])
                for log_presta_id_obj in log_presta_ids_obj:
                    ps_obj = self.env['prestashop.order']
                    ps_ids_obj=ps_obj.search([('erp_id','=',log_presta_id_obj.erp_id)])
                    for ps_id_obj in ps_ids_obj:
                        ps_id_obj.unlink()
                        
                    log_presta_id_obj.write({
                                     'object_name':'UNLINK_ORDER_OK_PAID',
                                     })
                    #ps_id_obj.unlink()
                return {}
    @api.multi
    def ps_order_state(self,state):
                log_presta_obj=self.env['prestashop.order.log']
                log_presta_ids_obj=log_presta_obj.search([('erp_id','=',self.id)])
                for log_presta_id_obj in log_presta_ids_obj:
                    log_presta_id_obj.create({'name':log_presta_id_obj.name,
                                     'object_name_save':log_presta_id_obj.object_name_save,
                                     'object_name':'LINK_ORDER_STATE_%s' % state,
                                     'ur_id':log_presta_id_obj.erp_id,
                                     'erp_id':log_presta_id_obj.erp_id,
                                     'presta_id':log_presta_id_obj.presta_id
                                     })
                
                return {}

    @api.multi
    def del_unlink_ps_order(self):
                log_presta_obj=self.env['prestashop.order.log']
                log_presta_ids_obj=log_presta_obj.search([('object_name','=','UNLINK_ORDER')])
                for log_presta_id_obj in log_presta_ids_obj:
                    ps_obj = self.env['prestashop.order']
                    ps_ids_obj=ps_obj.search([('erp_id','=',log_presta_id_obj.erp_id)])
                    for ps_id_obj in ps_ids_obj:
                        ps_id_obj.unlink()
                        
                    log_presta_id_obj.write({
                                     'object_name':'UNLINK_ORDER_OK',
                                     })
                    #ps_id_obj.unlink()
                print 'del_unlink_ps_order'
                return {}

    def del_unlink_ps_order_80(self,cr,uid,ids=None,context=None):
                log_presta_obj=self.pool.get('prestashop.order.log')
                log_presta_ids_obj=log_presta_obj.search(cr,uid,[('object_name','=','UNLINK_ORDER')],context=context)
                for log_presta_id_obj in log_presta_ids_obj:
                    ps_obj = self.pool.get('prestashop.order')
                    ps_ids=ps_obj.search(cr,uid,[('erp_id','=',log_presta_id_obj.erp_id)],context=context)
                    for ps_id_obj in ps_obj.browse(cr,uid,ps_ids,context=context):
                        ps_obj.unlink(cr,uid,ps_id_obj.id,context=context)
                        
                    log_presta_obj.write(cr,uid,log_presta_id_obj.id,{
                                     'object_name':'UNLINK_ORDER_OK',
                                     })
                    #ps_id_obj.unlink()
                print 'del_unlink_ps_order'
                return {}
    def del_unlink_ps_order_70(self,cr,uid,ids=None,tag_search='UNLINK_ORDER',tag_write='UNLINK_ORDER_OK',context=None):
                log_presta_obj=self.pool.get('prestashop.order.log')
                log_presta_ids=log_presta_obj.search(cr,uid,[('object_name','=',tag_search)],context=context)
                for log_presta_id_obj in log_presta_obj.browse(cr,uid,log_presta_ids,context=context):
                    ps_obj = self.pool.get('prestashop.order')
                    ps_ids=ps_obj.search(cr,uid,[('erp_id','=',log_presta_id_obj.erp_id)],context=context)
                    for ps_id_obj in ps_obj.browse(cr,uid,ps_ids,context=context):
                        ps_obj.unlink(cr,uid,ps_id_obj.id,context=context)
                        
                    log_presta_obj.write(cr,uid,log_presta_id_obj.id,{
                                     'object_name':tag_write,
                                     })
                    #ps_id_obj.unlink()
                print 'del_unlink_ps_order'
                return {}
    """
    traferimento merce
    """
    
    @api.multi
    def move_assigned(self,cron=False):
        date_today=datetime.today()
        sale_obj = self.env['sale.order']##òàòàòà
        pick_obj = self.env['stock.picking']#'''''ddklklkl
        pick_wave_obj = self.env['stock.picking.wave']#'''''ddklklkl
        if self.env.context:
            active_ids=self.env.context.get('active_ids', [])
            active_id=self.env.context.get('active_id', None)
            active_model=self.env.context.get('active_model', 'sale.order')
        else:
            active_ids=[self.id]
            active_id=self.id
            active_model='sale.order'
            
        print 'context',self.env.context
        
        if cron==True:
            obj_ids=pick_obj.search([('state','ilike','assigned')])
        else:
            if active_model=='sale.order':
                obj_ids=sale_obj.search([('id','in',tuple(active_ids))])
            elif active_model=='stock.picking':
                obj_ids=pick_obj.search([('id','in',tuple(active_ids))])
            else:
                #obj_ids=sale_obj.search([('state','ilike','assigned')])
                obj_ids=sale_obj.search([('id','in',tuple(active_ids))])
        conta=0
        wave_id_obj=pick_wave_obj.create({'user_id':self.env.uid,'state': 'in_progress'})
        for obj_id_obj in obj_ids:
            conta+=1
            if active_model=='sale.order': 
                    for pick_id_obj in obj_id_obj.picking_ids:
                        if pick_id_obj.state=='assigned':
                            """
                            for move_id_obj in pick_id_obj.move_lines:
                                move_id_obj.write({'state':'done'})
                            """
                            processed_ids=[]
                            for prod in pick_id_obj.move_lines:
                                pack_datas = {
                                    'product_id': prod.product_id.id,
                                    'product_uom_id': prod.product_uom.id,
                                    'product_qty': prod.product_qty,
                                    'package_id': None,
                                    'lot_id': None,
                                    'location_id': prod.location_id.id,
                                    'location_dest_id': prod.location_dest_id.id,
                                    'result_package_id': None,
                                    'date': prod.date if prod.date else datetime.now(),
                                    'owner_id':  pick_id_obj.owner_id.id,
                                }
                                #21-07-2017_rocco_pack_datas['picking_id'] = pick_id_obj.id
                                #21-07-2017_rocco_packop_id = self.env['stock.pack.operation'].create(pack_datas)
                                #21-07-2017_rocco_processed_ids.append(packop_id.id)
                            # Delete the others
                            #21-07-2017_rocco_pick_id_obj.write({'wave_id':wave_id_obj.id})
                            if pick_id_obj.pack_operation_ids:
                                for pack_operation_id in pick_id_obj.pack_operation_ids:
                                        pack_operation_id.write({'picking_id':None})
                            
                            pick_id_obj.do_transfer()
                            #21-07-2017_rocco_packops = self.env['stock.pack.operation'].search(['&', ('picking_id', '=', pick_id_obj.id), '!', ('id', 'in', processed_ids)])
                            #21-07-2017_rocco_packops.unlink()

            elif active_model=='stock.picking':
                        if obj_id_obj.state=='assigned':
                            """
                            for move_id_obj in obj_id_obj.move_lines:
                                move_id_obj.write({'state':'done'})
                            """
                            processed_ids=[]
                            for prod in obj_id_obj.move_lines:
                                pack_datas = {
                                    'product_id': prod.product_id.id,
                                    'product_uom_id': prod.product_uom.id,
                                    'product_qty': prod.product_qty,
                                    'package_id': None,
                                    'lot_id': None,
                                    'location_id': prod.location_id.id,
                                    'location_dest_id': prod.location_dest_id.id,
                                    'result_package_id': None,
                                    'date': prod.date if prod.date else datetime.now(),
                                    'owner_id':  obj_id_obj.owner_id.id,
                                }
                                #21-07-2017_rocco_pack_datas['picking_id'] = pick_id_obj.id
                                #21-07-2017_rocco_packop_id = self.env['stock.pack.operation'].create(pack_datas)
                                #21-07-2017_rocco_processed_ids.append(packop_id.id)
                            #21-07-2017_rocco_obj_id_obj.write({'wave_id':wave_id_obj.id})
                            # Delete the others
                            if obj_id_obj.pack_operation_ids:
                                for pack_operation_id in obj_id_obj.pack_operation_ids:
                                        pack_operation_id.write({'picking_id':None})
                            obj_id_obj.do_transfer()
                            #21-07-2017_rocco_packops = self.env['stock.pack.operation'].search(['&', ('picking_id', '=', obj_id_obj.id), '!', ('id', 'in', processed_ids)])
                            #21-07-2017_rocco_packops.unlink()
            else:
                    for pick_id_obj in obj_id_obj.picking_ids:
                        if pick_id_obj.state=='assigned':
                            """
                            for move_id_obj in pick_id_obj.move_lines:
                                move_id_obj.write({'state':'done'})
                            """
                            processed_ids=[]
                            for prod in pick_id_obj.move_lines:
                                pack_datas = {
                                    'product_id': prod.product_id.id,
                                    'product_uom_id': prod.product_uom.id,
                                    'product_qty': prod.product_qty,
                                    'package_id': None,
                                    'lot_id': None,
                                    'location_id': prod.location_id.id,
                                    'location_dest_id': prod.location_dest_id.id,
                                    'result_package_id': None,
                                    'date': prod.date if prod.date else datetime.now(),
                                    'owner_id':  pick_id_obj.owner_id.id,
                                }
                                #21-07-2017_rocco_pack_datas['picking_id'] = pick_id_obj.id
                                #21-07-2017_rocco_packop_id = self.env['stock.pack.operation'].create(pack_datas)
                                #21-07-2017_rocco_processed_ids.append(packop_id.id)
                            # Delete the others
                            #21-07-2017_rocco_pick_id_obj.write({'wave_id':wave_id_obj.id})
                            if pick_id_obj.pack_operation_ids:
                                for pack_operation_id in pick_id_obj.pack_operation_ids:
                                        pack_operation_id.write({'picking_id':None})
                            pick_id_obj.do_transfer()
                            #21-07-2017_rocco_packops = self.env['stock.pack.operation'].search(['&', ('picking_id', '=', pick_id_obj.id), '!', ('id', 'in', processed_ids)])
                            #21-07-2017_rocco_packops.unlink()
        wave_id_obj.write({'state': 'in_progress'})
        wave_id_obj.write({'state': 'done'})

        #wave_id_obj.done()
        #wave_id_obj.write(self.env.cr,self.env.uid,{'state': 'in_progress'},context=self.env.context)
        #wave_id_obj.done(self.env.cr,self.env.uid,[wave_id_obj.id],context=self.env.context)
        
        if cron==False:
            if active_model=='sale.order':
                    view_tree = self.env['ir.model.data'].get_object_reference('sale', 'view_order_tree')
                    view_form = self.env['ir.model.data'].get_object_reference('sale', 'view_order_form')
            elif active_model=='stock.picking':
                    view_tree = self.env['ir.model.data'].get_object_reference('stock', 'view_picking_tree')
                    view_form = self.env['ir.model.data'].get_object_reference('stock', 'view_picking_form')                    
            else:
                    view_tree = self.env['ir.model.data'].get_object_reference('sale', 'view_order_tree')
                    view_form = self.env['ir.model.data'].get_object_reference('sale', 'view_order_form')                
            if len(active_ids)>=2:
                view_id = view_tree and view_tree[1] or False,
            else:
                view_id = view_form and view_form[1] or False,
                
            """
            return {'name':_("Message"),
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'tree,form',
                'res_model': self.env.context['active_model'],
                'res_id': active_id,
                'type': 'ir.actions.act_window',
                'nodestroy': False,
                'target': 'normal',
                'domain': self.env.context.get('domain',{}),                                 
                'context': self.env.context,                                 
            }
            """
            """
            return {
                'name': _('Message'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.picking.wave',
                'domain': [('id','in',[wave_id_obj.id])],
                'res_id': wave_id_obj.id,
                'view_id': None,
                'type': 'ir.actions.act_window',
                'context': self.env.context
            }
            """
            #print 'view_id',view_id,'len(active_ids',len(active_ids),'view_tree',view_tree,'view_form',view_form,'active_model',self.env.context['active_model'],'active_id',active_id
            return {'name':_("Ordini trasferti"),
                'view_mode': 'tree,form',
                'view_id': None ,
                'view_type': 'form',
                'res_model': self.env.context.get('active_model','sale.order'),
                'res_id': active_id if len(active_ids)==1 else None ,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'normal',
                'domain': [('id','in',tuple(active_ids))],                                 
                'context': self.env.context,                                 
                    }
            return {
                'name': _('Message'),
                'view_type': 'form'  ,
                'view_mode': 'tree, form',
                'res_model': self.env.context['active_model'],
                'domain': [('id','in',tuple(active_ids))],
                'res_id': active_id if len(active_ids)==1 else None ,
                'view_id': view_id,
                'views': [(view_form[0] or False, 'form'),
                          (view_tree[0] or False, 'tree'), (False, 'kanban'),
                          (False, 'calendar'), (False, 'graph')],
                'nodestroy': True,
                'target': 'normal',
                'type': 'ir.actions.act_window',
                'context': self.env.context
            }

        else:
            return True
    @api.multi    
    def action_ship_create(self):
        pick_obj = self.env['stock.picking']#'''''ddklklkl
        pick_wave_obj = self.env['stock.picking.wave']#'''''ddklklkl
        active_ids=self.env.context.get('active_ids', [])
        active_id=self.env.context.get('active_id', None)
        res=super(sale_order, self).action_ship_create()
        if res:
            for pick_id_obj in self.picking_ids:
                pick_id_obj.action_assign()
            if self.shop_id.x_chiudi==True:
                if self.name.find(self.shop_id.x_tag)>=0:
                    for pick_id_obj in self.picking_ids:
                                    pick_id_obj.force_assign()
                    
                    if self.env.context=={}:
                        context={}
                    
                    context['active_ids']=[self.id]
                    context['active_id']=self.id
                    context['active_model']='sale.order'
                    self.with_context(context)
                    self.move_assigned()
        
        return res
    @api.multi
    def action_invoice_create(self,grouped=False, states=None, date_invoice = False):
        if date_invoice==False:
            date_invoice=datetime.today()
        print 'date_invoice',date_invoice
        res=super(sale_order, self).action_invoice_create(grouped=grouped, states=states, date_invoice = date_invoice)
        return res
    def manual_prestashop_invoice_cancel(self,cr,uid,ids,context=None):
        error_message=''
        status='yes'
        config_id=self.pool.get('prestashop.configure').search(cr,uid,[('active','=',True)])
        sale_id_obj=self.browse(cr, uid, ids[0], context)
        if not config_id:
            error_message='Connection needs one Active Configuration setting.'
            status='no'
        if len(config_id)>1:
            error_message='Sorry, only one Active Configuration setting is allowed.'
            status='no'
        else:
            obj=self.pool.get('prestashop.configure').browse(cr,uid,config_id[0])
            url=obj.api_url
            key=obj.api_key
            try:
                prestashop = PrestaShopWebServiceDict(url,key)
            except PrestaShopWebServiceError,e:
                error_message='Invalid Information, Error %s'%e
                status='no'
            except IOError, e:
                error_message='Error %s'%e
                status='no'
            except Exception,e:
                error_message="Error,Prestashop Connection in connecting: %s" % e
                status='no'
            if prestashop:
                order_id=self.pool.get('prestashop.order').get_id(cr,uid,'prestashop','order',ids[0])
                if order_id:
                    try:
                        order_his_data=prestashop.get('order_histories', options={'schema': 'blank'})
                    except Exception,e:
                        error_message="Error %s, Error in getting Blank XML"%str(e)
                        status='no'
                    order_his_data['order_history'].update({
                    'id_order' : order_id,
                    'id_order_state':6
                    })
                    if sale_id_obj.shop_id.x_no_mail==False:
                        state_update=prestashop.add('order_histories?sendemail=1', order_his_data)
                    else:
                        state_update=prestashop.add('order_histories?sendemail=0', order_his_data)
                        
                else:
                    return True
                    #Do not touch _name it must be same as _inherit
    @api.multi
    def action_reopen(self):
        #try:
        #    self.env.cr.commit()
        #except:
        #    self.env.cr.rollback()
        ps_obj=self.env['prestashop.order']
        log_ps_obj=self.env['prestashop.order.log']
        if self.env.context.get('active_ids',[])>0:
            active_ids=self.env.context.get('active_ids',[])
        else:
            active_ids=[self.id]
        ps_ids_obj=ps_obj.search([('erp_id','in',active_ids)])
        log_ps_ids_obj=[]
        for ps_id_obj in ps_ids_obj:
            log_ps_ids_obj=log_ps_obj.search([('erp_id','=',ps_id_obj.erp_id),('object_name','=','UNLINK_ORDER')])
            if log_ps_ids_obj:
                print 'nn_01'
            else:
                log_ps_ids_obj=log_ps_obj.search([('erp_id','=',ps_id_obj.erp_id)])
            if log_ps_ids_obj:
                print 'nn_02'
            else:
                log_ps_ids_obj.create({'name':ps_id_obj.name,
                                 'object_name_save':ps_id_obj.object_name,
                                 'object_name':'UNLINK_ORDER',
                                 'ur_id':ps_id_obj.erp_id,
                                 'erp_id':ps_id_obj.erp_id,
                                 'presta_id':ps_id_obj.presta_id
                                 })
                
            print 'log_ps_ids_obj_01',log_ps_ids_obj
            for log_ps_id_obj in log_ps_ids_obj:
                    log_ps_id_obj.del_ps_key(False)
        new_sale_ids=[]
        for  sale_id_obj in self.browse(active_ids):
            if sale_id_obj.id in new_sale_ids:
                continue
            for invoice_id_obj in sale_id_obj.invoice_ids:
                move_ids=[]
                riconcile_ids=[]
                pay_ids=[]
                print 'invoice_id_obj.payment_ids',invoice_id_obj.payment_ids
                for payment_id_obj in invoice_id_obj.payment_ids:
                    pay_ids.append(payment_id_obj.id)
                    move_ids.append(payment_id_obj.move_id.id)
                    riconcile_ids.append(payment_id_obj.reconcile_id.id)
                    payment_id_obj.reconcile_id.unlink()
                    payment_id_obj.move_id.write({'state':'draft'})
                    payment_id_obj.write({'reconcile_id':None,'reconcile_ref':None,'state':'draft'})
                    
                    payment_id_obj.move_id.unlink()
                    print 'delete.payment_ids'
                move_line_ids=[]
                for move_id_obj in invoice_id_obj.move_id:
                    move_ids.append(move_id_obj.id)
                    move_line_ids=[]
                    for line_id_obj in move_id_obj.line_id:
                            move_line_ids.append(line_id_obj.id)
                            if line_id_obj.reconcile_id:
                                    riconcile_ids.append(line_id_obj.reconcile_id.id)
                                    line_id_obj.write({'reconcile_id':None,'reconcile_ref':None})#xxxxx

                print 'riconcile_ids.pay_ids.move_line_ids.move_ids',riconcile_ids,pay_ids,move_line_ids,move_ids
                if riconcile_ids:##x
                    """ del riconciliazione """
                    self.env.cr.execute('delete from account_move_reconcile where id in %s',(tuple(riconcile_ids),))
                if pay_ids:
                    """ delete movimenti pagamenti """
                    self.env.cr.execute('delete from account_move_line where id in %s',(tuple(pay_ids),))
                if move_line_ids:
                    """ delete movimenti fattura """
                    self.env.cr.execute('delete from account_move_line where id in %s',(tuple(move_line_ids),))
                invoice_id_obj.write({'internal_number':None})
                invoice_id_obj.action_cancel()
                invoice_id_obj.unlink()
                if move_ids:
                    print 'delete.invoice_id_obj.move_id'
                    """ delete movimenti testata"""
                    self.env.cr.execute('delete from account_move where id in %s',(tuple(move_ids),))
                #self.env.cr.execute('delete from account_invoice where id in %s',(tuple([invoice_id_obj.id]),))
            new_order=False    
            old_name=str(time.strftime('_(old)_%Y_%m_%d_%H_%M_%S'))
            new_vals={'name':sale_id_obj.name,'origin':sale_id_obj.origin,'shop_id':sale_id_obj.shop_id.id}
            old_vals={'name':sale_id_obj.name+(old_name),'origin':sale_id_obj.name+(old_name)}
            if new_order==True:
                sale_id_obj.write(old_vals)
                sale_new_id=sale_id_obj.copy(new_vals)
                new_sale_ids.append(sale_new_id.id)
                for picking_id_obj in sale_id_obj.picking_ids:
                        if picking_id_obj.picking_type_id.code not in ('outgoing',):
                            picking_id_obj.write({'origin':picking_id_obj.origin+'('+old_name+')'})
                            if picking_id_obj.invoice_state=='invoiced':
                                continue
                            #if picking_id_obj.state in ('done','assigned'):
                            #    continue
                            for sale_line_id_obj in sale_id_obj.order_line:
                                for move_line_id_obj in picking_id_obj.move_lines:
                                        if sale_line_id_obj.product_id.id!=move_line_id_obj.product_id.id:
                                            continue
                                        #if move_line_id_obj.state in ('assigned','done'):
                                        #    continue
                                        move_line_id_obj.write({'state':'draft'})
                                        for quant in move_line_id_obj.quant_ids:
                                            quant.write({'qty':quant.qty-move_line_id_obj.product_qty})
                                        move_line_id_obj.unlink()
                            
                        if picking_id_obj.location_dest_id.usage!='customer':
                                continue
                        picking_id_obj.write({'state':'draft'})
                        for pack_operation_id_obj in picking_id_obj.pack_operation_ids:
                            pack_operation_id_obj.unlink()
                        for move_line_id_obj in picking_id_obj.move_lines:
                                move_line_id_obj.write({'state':'draft'})
                                for quant in move_line_id_obj.quant_ids:
                                    quant.write({'qty':quant.qty-move_line_id_obj.product_qty})
                                move_line_id_obj.unlink()
                        
            else:
                sale_new_id=sale_id_obj
                new_sale_ids.append(sale_new_id.id)

            """ ripristino nuova chiave la chiave """                
            log_ps_ids_obj=log_ps_obj.search([('erp_id','=',sale_id_obj.id)])
            #print 'log_ps_ids_obj_02',log_ps_ids_obj
            for log_ps_id_obj in log_ps_ids_obj:
                     #print 'log_ps_id_obj_erp_id_01',log_ps_id_obj.erp_id
                     ps_ids_obj=ps_obj.search([('erp_id','=',log_ps_id_obj.erp_id)])
                     for ps_id_obj in ps_ids_obj:
                         ps_id_obj.unlink()
                     log_ps_id_obj.write({'erp_id':sale_new_id.id})

                     #print 'log_ps_id_obj_erp_id_02',log_ps_id_obj.erp_id
                     log_ps_id_obj.rip_ps_key(False)
            if new_order==True:
                sale_id_obj.write({'state':'cancel'})  
            else:
                old_vals['state']='cancel'
                work_fl_id_obj=self.env['workflow.instance'].search([('res_type','=','sale.order'),('res_id','=',sale_id_obj.id)])
                #if work_fl_id_obj:
                    #work_fl_id_obj.write({'active':True,'state':'active'})
                sale_id_obj.write(old_vals)
                  
                      
            #try:
            #    self.env.cr.commit()
            #except:
            #    self.env.cr.rollback()
        view_ref = self.env['ir.model.data'].get_object_reference('prof_webtex', 'view_order_tree_prof_webtex_state_inv_pick')
        view_ref_form = self.env['ir.model.data'].get_object_reference('sale', 'view_order_form')
        view_id = view_ref and view_ref[1] or False,
        view_form_id = view_ref_form and view_ref_form[1] or False,
        #print 'self.env.context',self.env.context
        #print 'view_id.view_form_id',view_id,view_form_id
        return {'name':_("Riapertura Ordine"),
                'view_mode': 'tree,form',
                'view_id': None ,
                'view_type': 'form',
                'res_model': 'sale.order',
                'res_id': None,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'normal',
                'domain': [('id','in',tuple(new_sale_ids))],                                 
                'context': self.env.context,                                 
            }
    """ chiusra ordine Ps """
    @api.multi
    def action_reclose(self):
        #try:
        #    self.env.cr.commit()
        #except:
        #    self.env.cr.rollback()
        ps_obj=self.env['prestashop.order']
        log_ps_obj=self.env['prestashop.order.log']
        if self.env.context.get('active_ids',[])>0:
            active_ids=self.env.context.get('active_ids',[])
        else:
            active_ids=[self.id]
        ps_ids_obj=ps_obj.search([('erp_id','in',active_ids)])
        log_ps_ids_obj=[]
        for ps_id_obj in ps_ids_obj:
            log_ps_ids_obj=log_ps_obj.search([('erp_id','=',ps_id_obj.erp_id),('object_name','=','UNLINK_ORDER')])
            if log_ps_ids_obj:
                print 'nn_01'
            else:
                log_ps_ids_obj=log_ps_obj.search([('erp_id','=',ps_id_obj.erp_id)])
            if log_ps_ids_obj:
                print 'nn_02'
            else:
                log_ps_ids_obj.create({'name':ps_id_obj.name,
                                 'object_name_save':ps_id_obj.object_name,
                                 'object_name':'UNLINK_ORDER',
                                 'ur_id':ps_id_obj.erp_id,
                                 'erp_id':ps_id_obj.erp_id,
                                 'presta_id':ps_id_obj.presta_id
                                 })
                
            print 'log_ps_ids_obj_01',log_ps_ids_obj
            for log_ps_id_obj in log_ps_ids_obj:
                    log_ps_id_obj.del_ps_key(False)
        new_sale_ids=[]
        for  sale_id_obj in self.browse(active_ids):
            if sale_id_obj.id in new_sale_ids:
                continue
            for invoice_id_obj in sale_id_obj.invoice_ids:
                move_ids=[]
                riconcile_ids=[]
                pay_ids=[]
                print 'invoice_id_obj.payment_ids',invoice_id_obj.payment_ids
                for payment_id_obj in invoice_id_obj.payment_ids:
                    pay_ids.append(payment_id_obj.id)
                    move_ids.append(payment_id_obj.move_id.id)
                    riconcile_ids.append(payment_id_obj.reconcile_id.id)
                    payment_id_obj.move_id.write({'state':'draft'})
                    payment_id_obj.write({'reconcile_id':None,'reconcile_ref':None,'state':'draft'})
                    payment_id_obj.move_id.unlink()
                    print 'delete.payment_ids'
                move_line_ids=[]
                for move_id_obj in invoice_id_obj.move_id:
                    move_ids.append(move_id_obj.id)
                    move_line_ids=[]
                    for line_id_obj in move_id_obj.line_id:
                            move_line_ids.append(line_id_obj.id)
                            if line_id_obj.reconcile_id:
                                    riconcile_ids.append(line_id_obj.reconcile_id.id)
                                    line_id_obj.write({'reconcile_id':None,'reconcile_ref':None})#xxxxx

                print 'riconcile_ids.pay_ids.move_line_ids.move_ids',riconcile_ids,pay_ids,move_line_ids,move_ids
                if riconcile_ids:##x
                    """ del riconciliazione """
                    self.env.cr.execute('delete from account_move_reconcile where id in %s',(tuple(riconcile_ids),))
                if pay_ids:
                    """ delete movimenti pagamenti """
                    self.env.cr.execute('delete from account_move_line where id in %s',(tuple(pay_ids),))
                if move_line_ids:
                    """ delete movimenti fattura """
                    self.env.cr.execute('delete from account_move_line where id in %s',(tuple(move_line_ids),))
                invoice_id_obj.write({'internal_number':None})
                invoice_id_obj.action_cancel()
                invoice_id_obj.unlink()
                if move_ids:
                    print 'delete.invoice_id_obj.move_id'
                    """ delete movimenti testata"""
                    self.env.cr.execute('delete from account_move where id in %s',(tuple(move_ids),))
                #self.env.cr.execute('delete from account_invoice where id in %s',(tuple([invoice_id_obj.id]),))
                
            old_name=str(time.strftime('_(old)_%Y_%m_%d_%H_%M_%S'))
            new_vals={'name':sale_id_obj.name,'origin':sale_id_obj.origin,'shop_id':sale_id_obj.shop_id.id}
            old_vals={'name':sale_id_obj.name+(old_name),'origin':sale_id_obj.name+(old_name)}
            sale_id_obj.write(old_vals)
            sale_new_id=sale_id_obj.copy(new_vals)
            new_sale_ids.append(sale_new_id.id)
            for picking_id_obj in sale_id_obj.picking_ids:
                    if picking_id_obj.picking_type_id.code not in ('outgoing',):
                        picking_id_obj.write({'sale_id':sale_new_id.id,'origin':picking_id_obj.origin+'('+sale_new_id.name+')'})
                        continue
                    picking_id_obj.write({'state':'draft'})
                    for pack_operation_id_obj in picking_id_obj.pack_operation_ids:
                        pack_operation_id_obj.unlink()
                    for move_line_id_obj in picking_id_obj.move_lines:
                            move_line_id_obj.write({'state':'draft'})
                            move_line_id_obj.unlink()
                        
            """ ripristino nuova chiave la chiave """                
            log_ps_ids_obj=log_ps_obj.search([('erp_id','=',sale_id_obj.id)])
            #print 'log_ps_ids_obj_02',log_ps_ids_obj
            for log_ps_id_obj in log_ps_ids_obj:
                     #print 'log_ps_id_obj_erp_id_01',log_ps_id_obj.erp_id
                     ps_ids_obj=ps_obj.search([('erp_id','=',log_ps_id_obj.erp_id)])
                     for ps_id_obj in ps_ids_obj:
                         ps_id_obj.unlink()
                     log_ps_id_obj.write({'erp_id':sale_new_id.id})

                     #print 'log_ps_id_obj_erp_id_02',log_ps_id_obj.erp_id
                     log_ps_id_obj.rip_ps_key(False)
            sale_id_obj.write({'state':'cancel'})        
            #try:
            #    self.env.cr.commit()
            #except:
            #    self.env.cr.rollback()
        view_ref = self.env['ir.model.data'].get_object_reference('prof_webtex', 'view_order_tree_prof_webtex_state_inv_pick')
        view_ref_form = self.env['ir.model.data'].get_object_reference('sale', 'view_order_form')
        view_id = view_ref and view_ref[1] or False,
        view_form_id = view_ref_form and view_ref_form[1] or False,
        #print 'self.env.context',self.env.context
        #print 'view_id.view_form_id',view_id,view_form_id
        return {'name':_("Riapertura Ordine"),
                'view_mode': 'tree,form',
                'view_id': None ,
                'view_type': 'form',
                'res_model': 'sale.order',
                'res_id': None,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'normal',
                'domain': [('id','in',tuple(new_sale_ids))],                                 
                'context': self.env.context,                                 
            }
    
    @api.multi
    def convert_2float(self, value, precision=dp.get_precision('account_2_cifre'), currency_obj=None, context=None):
    
        fmt = '%f' if precision is None else '%.{precision}f'
    
        lang_code = self.env.context.get('lang') or 'en_US'
    
        lang = self.pool['res.lang']
    
        formatted = lang.format(self.env.cr, self.env.uid, [lang_code], fmt.format(precision=precision), value, grouping=True,     monetary=True)
    
        if currency_obj:
    
            if currency_obj.position == 'before':
        
                formatted = currency_obj.symbol + ' ' + formatted
        
            else:
        
                formatted = formatted + ' ' + currency_obj.symbol
        
            return formatted
    @api.multi
    def sale_order_open_webtex(self):
        view_ref = self.env['ir.model.data'].get_object_reference('prof_webtex', 'view_sale_order_open_webtex')
        view_id = view_ref and view_ref[1] or False,
        print 'self.env.context',self.env.context
        return {'name':_("Riapertura Ordine"),
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'sale.order',
                'res_id': self.env.context.get('active_id',[]),
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new',
                'domain': ['id','in',self.env.context.get('active_ids',[])],                                 
                'context': self.env.context,                                 
            }

class purchase_order_line(osv.osv):
    _inherit='purchase.order.line'
    _order = 'name,id desc'
    def _attribute_value_id_(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if context is None:
            context = {}
        """"---"""
        for line_id_obj in self.browse(cr, uid, ids, context=context):
            res[line_id_obj.id] = tuple([line.name.encode() for line in line_id_obj.product_id.attribute_value_ids])
        return res

    _columns = {
        'x_attribute_value_ids': fields.function(_attribute_value_id_, string='Attributi',type='char'),
        'date_planned': fields.date('Scheduled Date', required=False, select=True),
                                    }
    _defaults = {  
        'date_planned': lambda *a: time.strftime('%Y-%m-%d'),  
        }
class account_journal(osv.osv):
    _inherit = 'account.journal'
    _columns = {
        'x_to_journal_id':fields.many2one('account.journal', 'Sezionale di pagamento in sostituzione', required=False),            
        'x_to_company_journal_id':fields.many2many('account.journal','journal_journal_rel','comp_journal_id','journal_id', 'Sezionale per Cambio Ditta ', required=False),            
        #'x_payment_term_id':fields.many2many('account.journal','journal_journal_rel','comp_journal_id','journal_id', 'Sezionale per Cambio Ditta ', required=False),            
        'x_payment_term_id':fields.many2one('account.payment.term', 'Payment Terms', required=False),            
}
class StockPickingPackagePreparation(osv.osv):
    _inherit = 'stock.picking.package.preparation'
    date_done = x_fields.Datetime(
        string='Shipping Date',
        readonly=False,
    )
    @api.constrains('picking_ids')
    def _check_multiple_picking_ids(self):
        for package in self:
            if not package.ddt_type_id:
                continue
            if not package.ddt_type_id.restrict_pickings:
                continue
            for picking in package.picking_ids:
                other_ddts = picking.ddt_ids - package
                if other_ddts:
                    raise ValidationError(
                        _("The picking %s is already in DDT %s")
                        % (picking.name_get()[0][1],
                           other_ddts.name_get()[0][1]))


class DdTCreateInvoice(models.TransientModel):
    _inherit = "ddt.create.invoice"
    @api.multi
    def create_invoice(self):
        res=super(DdTCreateInvoice, self).create_invoice()
        ddt_str=''
        ddt_ids_obj=self.env['stock.picking.package.preparation'].browse(self.env.context.get('active_ids',[]))
        
        ddt_str=''
        for ddt_id_obj in ddt_ids_obj:
                if ddt_id_obj:
                    if ddt_id_obj.ddt_number==False:
                       ddt_id_obj.write({'ddt_number':'NO_DDT_NUM'})

                ddt_str+= '-' + ddt_id_obj.ddt_number
            
        for ddt_id_obj in ddt_ids_obj:
            invoice_id_obj = ddt_id_obj.invoice_id.write(
                                                      {
                                            'origin': ddt_str,       
                                            'x_pack_ids':[(6, 0, [ddt_id_obj.id])],
                                                       }
                                                      )
        return res
class stock_picking_val(models.Model):
    _inherit = 'stock.picking'
    @api.one
    @api.depends('move_lines.price_unit', 'move_lines.product_qty')
    def _compute_amount(self):
        def approx(valore_old,precision):
                               campo_appox_old=(valore_old)*(10**precision)
                               compo_int_old=int(campo_appox_old)
                               diff_old=campo_appox_old-compo_int_old
                               if diff_old>=0.51:#0,60:
                                           valore=valore_old 
                               else:
                                           valore=0.00
                                           valore=float(compo_int_old)
                                           #print 'valore_old',valore_old
                                           valore=valore_old/(10**precision)
                                           #print 'valore_old',valore_old
                               return round(valore, precision)
        self.amount_untaxed = sum(line.price_unit*line.product_qty for line in self.move_lines)
        #print 'invoice_compute_amount',self.amount_untaxed,self.amount_tax,self.amount_total

    amount_untaxed = x_fields.Float(string='Totale valore', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_amount', track_visibility='always')

class account_invoice_osv(osv.osv):
    _inherit = 'account.invoice'
    _columns = {
        'x_country_id': fields.related('partner_id', 'country_id', type="many2one", relation="res.country", string="Nazione", readonly=True),
        
        }
class account_invoice(models.Model):
    _inherit = 'account.invoice'
    @api.one
    @api.depends('invoice_line.journal_id')
    def _default_x_pay(self):
        x_pay="-"
        for pay in self.payment_ids:
            x_pay+=pay.journal_id.name
        print 'x_pay',x_pay
        return x_pay
    
    @api.one
    @api.depends('partner_id')
    def _default_x_country(self):
        x_country="-"
        if self.partner_id and self.partner_id.country_id :
            x_country="%s-%s" % (self.partner_id.country_id.code,self.partner_id.country_id.name)
        elif self.partner_id.parent_id and self.partner_id.parent_id.country_id :
            x_country="%s-%s" % (self.partner_id.parent_id.country_id.code,self.partner_id.parent_id.country_id.name)
        
        print 'x_country',x_country
        return x_country
    @api.one
    @api.depends('invoice_line.price_subtotal', 'tax_line.amount')
    def _compute_amount(self):
        def approx(valore_old,precision):
                               campo_appox_old=(valore_old)*(10**precision)
                               compo_int_old=int(campo_appox_old)
                               diff_old=campo_appox_old-compo_int_old
                               if diff_old>=0.51:#0,60:
                                           valore=valore_old 
                               else:
                                           valore=0.00
                                           valore=float(compo_int_old)
                                           #print 'valore_old',valore_old
                                           valore=valore_old/(10**precision)
                                           #print 'valore_old',valore_old
                               return round(valore, precision)
        
        res=super(account_invoice, self)._compute_amount()
        self.x_pay = self._default_x_pay
        #self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line)
        #for line in self.tax_line:
            #print 'amount',line.base,line.amount
        self.amount_untaxed = sum(line.base for line in self.tax_line)
        self.amount_tax = sum(line.amount for line in self.tax_line)
        self.amount_total = self.amount_untaxed + self.amount_tax
        self.amount_sp = 0
        if self.fiscal_position.split_payment:
            self.amount_sp = self.amount_tax
            self.amount_tax = 0
        self.amount_total = self.amount_untaxed + self.amount_tax
        #print 'invoice_compute_amount',self.amount_untaxed,self.amount_tax,self.amount_total

    amount_untaxed = x_fields.Float(string='Subtotal', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_tax = x_fields.Float(string='Tax', digits=dp.get_precision('account_2_cifre'),
        store=True, readonly=True, compute='_compute_amount')
    amount_total = x_fields.Float(string='Total', digits=dp.get_precision('account_2_cifre'),
        store=True, readonly=True, compute='_compute_amount')
    internal_number = x_fields.Char(string='Invoice Number', readonly=False,
        default=False, copy=False,
        help="Unique number of the invoice, computed automatically when the invoice is created.")
    x_pack_ids = x_fields.Many2many('stock.picking.package.preparation',
        'stock_picking_package_preparation_invoice',  'invoice_id','pack_id',
        string='DDT')
    x_pay = x_fields.Char(function='_default_x_pay', string='Pagamento',
         readonly=True,store=True)
    #x_country_id = x_fields.Char(function='_default_x_country', string='Nazione',
    #     readonly=True,store=True)
    @api.multi
    def confirm_paid(self):
        """
        sale_obj=self.env['sale.order']
        sale_ids=sale_obj.search([('name','ilike',self.origin)])###lòlò
        for sale_id in sale_ids:####
                if sale_id.shop_id:
                    if sale_id.shop_id.x_from_journal_id:
                        for pay_id_obj in self.payment_ids:
                            if pay_id_obj.journal_id.id==sale_id.shop_id.x_from_journal_id.id:
                                pay_id_obj.write({'journal_id':sale_id.shop_id.x_to_journal_id.id})
        """
        res=super(account_invoice, self).confirm_paid()
        if self.payment_ids:
             if self.payment_ids[0].move_id.journal_id.x_payment_term_id:
                 self.write({'payment_term':self.payment_ids[0].move_id.journal_id.x_payment_term_id.id})

        return res
    @api.multi
    def invoice_print(self):
        """ Print the invoice and mark it as sent, so that we can see more
            easily the next step of the workflow
        """
        assert len(self) == 1, 'This option should only be used for a single id at a time.'
        self.sent = True
        return self.env['report'].get_action(self, 'prof_webtex.report_invoice')
    def manual_prestashop_paid(self,cr,uid,ids,context=None):
        invoice_id_obj=self.browse(cr,uid,ids[0])
        order_name=invoice_id_obj.origin                
        
        sale_id=self.pool.get('sale.order').search(cr,uid,[('name','=',order_name)])
        
        if sale_id:
            error_message=''
            status='yes'
            config_id=self.pool.get('prestashop.configure').search(cr,uid,[('active','=',True)])
            sale_id_obj=self.pool.get('sale.order').browse(cr,uid,sale_id[0],context=context)
            
            if not config_id:
                error_message='Connection needs one Active Configuration setting.'
                status='no'
            if len(config_id)>1:
                error_message='Sorry, only one Active Configuration setting is allowed.'
                status='no'
            else:
                obj=self.pool.get('prestashop.configure').browse(cr,uid,config_id[0])
                url=obj.api_url
                key=obj.api_key
                try:
                    prestashop = PrestaShopWebServiceDict(url,key)
                except PrestaShopWebServiceError,e:
                    error_message='Invalid Information, Error %s'%e
                    status='no'
                except IOError, e:
                    error_message='Error %s'%e
                    status='no'
                except Exception,e:
                    error_message="Error,Prestashop Connection in connecting: %s" % e
                    status='no'
                if prestashop:
                    order_id=self.pool.get('prestashop.order').get_id(cr,uid,'prestashop','order',sale_id[0])
                    if order_id:
                        try:
                            order_his_data=prestashop.get('order_histories', options={'schema': 'blank'})
                        except Exception,e:
                            error_message="Error %s, Error in getting Blank XML"%str(e)
                            status='no'
                        if order_his_data['order_history'].get('id_order_state',0)<2:
                            order_his_data['order_history'].update({
                            'id_order' : order_id,
                            'id_order_state':2
                            })
                            if sale_id_obj.shop_id.x_no_mail==False:
                                state_update=prestashop.add('order_histories?sendemail=1', order_his_data)
                            else:
                                state_update=prestashop.add('order_histories?sendemail=0', order_his_data)
                    else:
                        return True
    
    _columns = {
        'ps_inv_ref': fields.char('Prestashop invoice Ref.',size=100),
    }                        

    
    def convert_2float(self, value, precision=dp.get_precision('account_2_cifre'), currency_obj=None, context=None):
    
        fmt = '%f' if precision is None else '%.{precision}f'
    
        lang_code = self.env.context.get('lang') or 'en_US'
    
        lang = self.pool['res.lang']
    
        formatted = lang.format(self.env.cr, self.env.uid, [lang_code], fmt.format(precision=precision), value, grouping=True,     monetary=True)
    
        if currency_obj:
    
            if currency_obj.position == 'before':
        
                formatted = currency_obj.symbol + ' ' + formatted
        
            else:
        
                formatted = formatted + ' ' + currency_obj.symbol
        
            return formatted
    @api.model
    @api.returns('self', lambda value:value.id)
    def create(self, vals):
        journal_obj=self.env['account.journal']#
        partner_obj=self.env['res.partner']
        period_obj=self.env['account.period']
        fpos_obj = self.env['account.fiscal.position']
        partner_id_obj=partner_obj.browse( vals.get('partner_id',None))
        if  vals.get('journal_id',None):
            journal_id_obj=journal_obj.browse(vals.get('journal_id',None))
            print 'prima_journal_id',journal_id_obj.id,journal_id_obj.name,journal_id_obj.company_id.name,vals.get('origin',None)
            print 'vals',vals
            if  vals.get('fiscal_position',None):
                    fpos_id_obj=fpos_obj.browse( vals.get('fiscal_position',None))
                    if  vals.get('reference',None):
                     if  vals.get('reference','').find("AFN") or vals.get('reference','').find("MFN") or vals.get('origin','').find("AFN") or vals.get('origin','').find("MFN"): 
                        if fpos_id_obj.country_id.code=="FR":
                            journal_scarto_ids_obj=journal_obj.search([('company_id','=',fpos_id_obj.company_id.id),('type','=',journal_id_obj.type)])
                            for journal_scarto_id_obj in journal_scarto_ids_obj:
                                print 'journal_scarto_id_obj',journal_scarto_id_obj.id,journal_scarto_id_obj.name
                                if journal_scarto_id_obj.name.find("SCARTO")>0:
                                    vals['journal_id']=journal_scarto_id_obj.id
                                    journal_id_obj=journal_scarto_id_obj
                                    print 'dopo_journal_id',journal_id_obj.id,journal_id_obj.name,vals.get('period_id',None)
                                    if vals.get('period_id',None):
                                        period_ids_obj=period_obj.search([('id','=',vals['period_id'])])
                                        period_comp_2_ids_obj=period_obj.search([('name','=',period_ids_obj[0].name),('company_id','=',fpos_id_obj.company_id.id)])
                                        vals['period_id']=period_comp_2_ids_obj[0].id
                                        print 'dopo_period_id',vals.get('period_id',None)
                                    else:
                    
                                        date_invoice=vals.get('date_invoice',datetime.today())
                                        print'date_invoice',date_invoice,'company_pos',fpos_id_obj.company_id.id,fpos_id_obj
                                        period_ids_obj=period_obj.search([('date_start','<=',date_invoice),('date_stop','>=',date_invoice),('company_id','=',fpos_id_obj.company_id.id)])
                                        print 'period_ids_obj',period_ids_obj
                                        period_comp_2_ids_obj=period_obj.search([('name','=',period_ids_obj[0].name),('company_id','=',fpos_id_obj.company_id.id)])
                                        vals['period_id']=period_comp_2_ids_obj[0].id
                                        print  'date_invoice',date_invoice,'period_id',vals['period_id']
                                    res=super(account_invoice, self).create(vals)
                                    return res
                                    break
                                    
                    if fpos_id_obj.name.find('GBP')>=0:
                            journal_gbp_ids_obj=journal_obj.search([('company_id','=',fpos_id_obj.company_id.id),('type','=',journal_id_obj.type),('corrispettivi','=',journal_id_obj.corrispettivi)])
                            if journal_gbp_ids_obj==None or journal_gbp_ids_obj==False or journal_gbp_ids_obj==[]:
                                journal_gbp_ids_obj=journal_obj.search([('company_id','=',fpos_id_obj.company_id.id),('type','=',journal_id_obj.type)])
                            if journal_gbp_ids_obj:
                                vals['journal_id']=journal_gbp_ids_obj[0].id    
                            for journal_gbp_id_obj in journal_gbp_ids_obj:
                                if journal_gbp_id_obj.currency.name=='GBP':
                                    vals['journal_id']=journal_gbp_id_obj.id
                                    break
                                
                    for x_to_company_journal_id in journal_id_obj.x_to_company_journal_id:
                        if fpos_id_obj.company_id==x_to_company_journal_id.company_id:
                                vals['journal_id']=x_to_company_journal_id.id
                                if vals.get('period_id',None):
                                    period_ids_obj=period_obj.search([('id','=',vals['period_id'])])
                                    period_comp_2_ids_obj=period_obj.search([('name','=',period_ids_obj[0].name),('company_id','=',fpos_id_obj.company_id.id)])
                                    vals['period_id']=period_comp_2_ids_obj[0].id
                                else:
                                    date_invoice=vals.get('date_invoice',datetime.today())
                                    period_ids_obj=period_obj.search([('date_start','<=',date_invoice),('date_stop','>=',date_invoice),('company_id','=',fpos_id_obj.company_id.id)])
                                    period_comp_2_ids_obj=period_obj.search([('name','=',period_ids_obj[0].name),('company_id','=',fpos_id_obj.company_id.id)])
                                    vals['period_id']=period_comp_2_ids_obj[0].id
                                break
                                    
        res=super(account_invoice, self).create(vals)
        """
        if vals.get('state',None)=='paid':
                    sale_obj=self.env['sale.order']
                    sale_ids_obj=sale_obj.search([('name','=',vals.get('origin',"xxxyyyzzz"))])
                    for sale_id_obj in sale_ids_obj:
                            sale_id_obj.del_unlink_ps_order_paid()
        
        """
        return res
    @api.v8
    def pay_and_reconcile(self, pay_amount, pay_account_id, period_id, pay_journal_id,
                          writeoff_acc_id, writeoff_period_id, writeoff_journal_id, name=''):
        # TODO check if we can use different period for payment and the writeoff line
        assert len(self)==1, "Can only pay one invoice at a time."
        # Take the seq as name for move
        SIGN = {'out_invoice': -1, 'in_invoice': 1, 'out_refund': 1, 'in_refund': -1}
        direction = SIGN[self.type]
        # take the chosen date
        date = self._context.get('date_p') or x_fields.Date.context_today(self)

        # Take the amount in currency and the currency of the payment
        if self._context.get('amount_currency') and self._context.get('currency_id'):
            amount_currency = self._context['amount_currency']
            currency_id = self._context['currency_id']
        else:
            amount_currency = False
            currency_id = False

        pay_journal = self.env['account.journal'].browse(pay_journal_id)
            
        if self.type in ('in_invoice', 'in_refund'):
            ref = self.reference
        else:
            ref = self.number
        partner = self.partner_id._find_accounting_partner(self.partner_id)
        name = name or self.invoice_line[0].name or self.number
        # Pay attention to the sign for both debit/credit AND amount_currency
        l1 = {
            'name': name,
            'debit': direction * pay_amount > 0 and direction * pay_amount,
            'credit': direction * pay_amount < 0 and -direction * pay_amount,
            'account_id': self.account_id.id,
            'partner_id': partner.id,
            'ref': ref,
            'date': date,
            'currency_id': currency_id,
            'amount_currency': direction * (amount_currency or 0.0),
            'company_id': self.company_id.id,
        }
        l2 = {
            'name': name,
            'debit': direction * pay_amount < 0 and -direction * pay_amount,
            'credit': direction * pay_amount > 0 and direction * pay_amount,
            'account_id': pay_account_id,
            'partner_id': partner.id,
            'ref': ref,
            'date': date,
            'currency_id': currency_id,
            'amount_currency': -direction * (amount_currency or 0.0),
            'company_id': self.company_id.id,
        }
        move = self.env['account.move'].create({
            'ref': ref,
            'line_id': [(0, 0, l1), (0, 0, l2)],
            'journal_id': pay_journal_id,
            'period_id': period_id,
            'date': date,
            'company_id': self.company_id.id,

        })

        move_ids = (move | self.move_id).ids
        self._cr.execute("SELECT id FROM account_move_line WHERE move_id IN %s",
                         (tuple(move_ids),))
        lines = self.env['account.move.line'].browse([r[0] for r in self._cr.fetchall()])
        lines2rec = lines.browse()
        total = 0.0
        for line in itertools.chain(lines, self.payment_ids):
            if line.account_id == self.account_id:
                lines2rec += line
                total += (line.debit or 0.0) - (line.credit or 0.0)

        inv_id, name = self.name_get()[0]
        if not round(total, self.env['decimal.precision'].precision_get('Account')) or writeoff_acc_id:
            lines2rec.reconcile('manual', writeoff_acc_id, writeoff_period_id, writeoff_journal_id)
        else:
            code = self.currency_id.symbol
            # TODO: use currency's formatting function
            msg = _("Invoice partially paid: %s%s of %s%s (%s%s remaining).") % \
                    (pay_amount, code, self.amount_total, code, total, code)
            self.message_post(body=msg)
            lines2rec.reconcile_partial('manual')

        # Update the stored value (fields.function), so we write to trigger recompute
        if pay_journal.x_payment_term_id:
            return self.write({'payment_term':pay_journal.x_payment_term_id.id})
        return self.write({})
    @api.multi
    def write(self, vals):
        res=models.Model.write(self, vals)
        if vals.get('state',None)=='paid':
                    sale_obj=self.env['sale.order']
                    sale_ids_obj=sale_obj.search([('name','=',self.origin)])
                    for sale_id_obj in sale_ids_obj:
                            #sale_id_obj.del_unlink_ps_order_paid()
                            sale_id_obj.ps_order_state(vals.get('state',None))
        elif vals.get('state',None) != None:
                    sale_obj=self.env['sale.order']
                    sale_ids_obj=sale_obj.search([('name','=',self.origin)])
                    for sale_id_obj in sale_ids_obj:
                            sale_id_obj.ps_order_state(vals.get('state',None))
            
        return res


    @api.multi
    def name_get(self):
        TYPES = {
            'out_invoice': _('Invoice'),
            'in_invoice': _('Supplier Invoice'),
            'out_refund': _('Refund'),
            'in_refund': _('Supplier Refund'),
        }
        result = []
        for inv in self:
            if inv.type in ('in_invoice','in_refund'):
                result.append((inv.id, "%s %s" % (inv.supplier_invoice_number or inv.number or TYPES[inv.type], inv.name or '')))
            else:
                result.append((inv.id, "%s %s" % (inv.number or TYPES[inv.type], inv.name or '')))
        return result

    @api.v7
    def name_search(self, cr,uid,name, args=None, operator='ilike', context=None,limit=100):
        args = args or []
        recs=[]
        if context.get('default_type',None) in ('in_invoice','in_refund'):
            if name:
                recs = self.search(cr,uid,[('supplier_invoice_number', '=', name)] + args, limit=limit, context=context )

           
            if not recs:
                recs = self.search(cr,uid,[('supplier_invoice_number', operator, name)] + args,  limit=limit, context=context)
        else:
            if name:
                recs = self.search(cr,uid,[('number', '=', name)] + args, limit=limit, context=context)
            if not recs:
                recs = self.search(cr,uid,[('name', operator, name)] + args,  limit=limit, context=context)
            
            
        return self.name_get(cr,uid,recs,context=context)

    @api.v8
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if recs.type in ('in_invoice','in_refund'):
            if name:
                recs = self.search([('supplier_invoice_number', '=', name)] + args, limit=limit)
            if not recs:
                recs = self.search([('supplier_invoice_number || name', operator, name)] + args, limit=limit)
        else:
            if name:
                recs = self.search([('number', '=', name)] + args, limit=limit)
            if not recs:
                recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()

account_invoice()

class account_move_line(osv.osv):
     
    _inherit = 'account.move.line'
    @api.model
    @api.returns('self', lambda value:value.id)
    def create(self, vals):
        if vals.get('journal_id',None):###
            move_obj=self.env['account.move']
            journal_obj=self.env['account.journal']
            partner_obj=self.env['res.partner']
            period_obj=self.env['account.period']
            journal_id_obj=journal_obj.browse(vals.get('journal_id',None))
            if journal_id_obj.x_to_journal_id:
                vals['journal_id']=journal_id_obj.x_to_journal_id.id
            if  vals.get('partner_id',None):
                partner_id_obj=partner_obj.browse( vals.get('partner_id',None))
                if partner_id_obj.company_id!=journal_id_obj.company_id:
                    if partner_id_obj.property_account_position:
                        fpos = self.env['account.fiscal.position'].browse(partner_id_obj.property_account_position.id)
                    else:    
                        fpos = self.env['account.fiscal.position'].search([('country_id','=',partner_id_obj.country_id.id)])
                        if fpos:
                            fpos=fpos[0]
                    account_id=self.env['account.account'].browse(vals['account_id'])
                    account_tax_id=self.env['account.tax'].browse(vals.get('account_tax_id',None))
                    account_id = fpos.map_account(account_id)
                    account_tax_id = fpos.map_tax(account_tax_id)
                    
                    
                    for x_to_company_journal_id in journal_id_obj.x_to_company_journal_id:
                        if x_to_company_journal_id.company_id.id!=fpos.company_id.id:
                            continue
                        vals['journal_id']=x_to_company_journal_id.id
                        vals['company_id']=x_to_company_journal_id.company_id.id
                        vals['account_id']=account_id.id
                        vals['account_tax_id']=account_tax_id or account_tax_id.id or None
                        if  vals.get('period_id',None):
                            period_ids_obj=period_obj.search([('id','=',vals['period_id'])])
                            period_comp_2_ids_obj=period_obj.search([('name','=',period_ids_obj[0].name),('company_id','=',vals['company_id'])])
                            if period_comp_2_ids_obj:
                                vals['period_id']=period_comp_2_ids_obj[0].id
                        move_ids_obj=move_obj.search([('id','=',vals['move_id'])])
                        for move_id_obj in move_ids_obj:
                            
                            move_id_obj.write({'period_id':vals['period_id'],
                                               'journal_id':x_to_company_journal_id.id,
                                               'company_id':x_to_company_journal_id.company_id.id
                                               })
                        
                
        res=super(account_move_line, self).create(vals)
        return res
    @api.multi
    def reconcile(self,type='auto', writeoff_acc_id=False, writeoff_period_id=False, writeoff_journal_id=False):
        """
        journal_obj=self.env['account.journal']
        if writeoff_journal_id:##
            journal_id_obj=journal_obj.browse(writeoff_journal_id)
            if journal_id_obj.x_to_journal_id:
                writeoff_journal_id=journal_id_obj.x_to_journal_id.id
                self.write({'journal_id':journal_id_obj.x_to_journal_id.id})
        """
        return super(account_move_line, self).reconcile(type='auto', writeoff_acc_id=writeoff_acc_id, writeoff_period_id=writeoff_period_id, writeoff_journal_id=writeoff_journal_id)
    def name_get(self, cr, uid, ids, context=None):
        #result=super(account_move_line, self).name_get(cr,uid,ids=ids,context=context)
        if not ids:
            return []
        #result=super(account_move_line, self).name_get( cr, uid, ids, context=context)
        result = []
        for line in self.browse(cr, uid, ids, context=context):
            if line.ref:
                result.append((line.id, (line.journal_id.name+'-' or '')+(line.move_id.name or '')+' ('+line.ref+')'))
            else:
                result.append((line.id, (line.journal_id.name+'-' or '')+line.move_id.name))
        return result

class stock_picking(osv.osv):
    _inherit="stock.picking"
    def manual_prestashop_shipment(self,cr,uid,ids,context=None):
        order_name=self.pool.get('stock.picking').browse(cr,uid,ids[0]).origin                
        sale_id=self.pool.get('sale.order').search(cr,uid,[('name','=',order_name)])
        if sale_id:
            error_message=''
            status='yes'
            config_id=self.pool.get('prestashop.configure').search(cr,uid,[('active','=',True)])
            sale_id_obj=self.pool.get('sale.order').browse(cr,uid,sale_id[0],context=context)
            if not config_id:
                error_message='Connection needs one Active Configuration setting.'
                status='no'
            if len(config_id)>1:
                error_message='Sorry, only one Active Configuration setting is allowed.'
                status='no'
            else:
                obj=self.pool.get('prestashop.configure').browse(cr,uid,config_id[0])
                url=obj.api_url
                key=obj.api_key
                try:
                    prestashop = PrestaShopWebServiceDict(url,key)
                except PrestaShopWebServiceError,e:
                    error_message='Invalid Information, Error %s'%e
                    status='no'
                except IOError, e:
                    error_message='Error %s'%e
                    status='no'
                except Exception,e:
                    error_message="Error,Prestashop Connection in connecting: %s" % e
                    status='no'
                if prestashop:
                    order_id=self.pool.get('prestashop.order').get_id(cr,uid,'prestashop','order',sale_id[0])
                    if order_id:
                        try:
                            order_his_data=prestashop.get('order_histories', options={'schema': 'blank'})
                        except Exception,e:
                            error_message="Error %s, Error in getting Blank XML"%str(e)
                            status='no'
                        if sale_id_obj.shop_id.x_no_change==True:
                                if sale_id_obj.shop_id.x_id_order_state>=0:
                                        order_his_data['order_history'].update({
                                        'id_order' : order_id,
                                        'id_order_state':sale_id_obj.shop_id.x_id_order_state
                                        })
                                        if sale_id_obj.shop_id.x_no_mail==False:
                                            state_update=prestashop.add('order_histories?sendemail=1', order_his_data)
                                        else:
                                            state_update=prestashop.add('order_histories?sendemail=0', order_his_data)
                        else:
                                        order_his_data['order_history'].update({
                                        'id_order' : order_id,
                                        'id_order_state':4
                                        })                                    
                                        if sale_id_obj.shop_id.x_no_mail==False:
                                            state_update=prestashop.add('order_histories?sendemail=1', order_his_data)
                                        else:
                                            state_update=prestashop.add('order_histories?sendemail=0', order_his_data)
                            
        return True
    def action_assign_cron(self,cr,uid,ids=None,cron=False,context=None):
        print 'context',context
        if cron==True:
            ids = self.search(cr,uid,[('state','in',('confirmed', 'waiting'))])
        else:
            if context:
                ids=context.get('active_ids',None)
            else:
                ids=None
        if ids:
            if context.get('active_model',None)=='sale.order':
                ids_pick=[]
                for sale in self.pool.get('sale.order').browse(cr,uid,ids,context):
                    for pick in sale.picking_ids:
                        ids_pick.append(pick.id)
            else:
                ids_pick=ids   
            for pick in self.browse(cr, uid, ids_pick, context):
                if pick.state in ('cancel', 'assigned','done'):
                    ids_pick.remove(pick.id)
                    continue
                if pick.state == 'draft':
                    self.action_confirm(cr, uid, [pick.id], context=context)

                self.do_unreserve(cr, uid, [pick.id], context=context)
                self.action_assign(cr, uid, [pick.id], context=context)
            if cron==False:
                    if len(ids_pick)>0:
                        view_ref = self.pool.get('ir.model.data').get_object_reference(cr,uid,'stock', 'view_picking_form')
                        view_id = view_ref and view_ref[1] or False,
                        return {'name':_("Picking elaborati"),
                            'view_mode': 'form' if len(ids_pick)==1 else 'tree,form',
                            'view_id': view_id if len(ids_pick)==1 else False,
                            'view_type': 'form',
                            'res_model': 'stock.picking',
                            'res_id': ids_pick[0] if len(ids_pick)==1 else None,
                            'type': 'ir.actions.act_window',
                            'nodestroy': True,
                            'target': 'normal',
                            'domain': [('id','in',tuple(ids_pick))],                                 
                            'context': context,                                 
                        }
                    else:
                            return {'name':_("Gli ordini  erano già disponibili"),
                        'view_mode': 'tree,form',
                        'view_id': None ,
                        'view_type': 'form',
                        'res_model': context.get('active_model',None),
                        'res_id': None,
                        'type': 'ir.actions.act_window',
                        'nodestroy': True,
                        'target': 'normal',
                        'domain': [('id','in',tuple(context.get('active_ids',None)))],                                 
                        'context': context,                                 
                    }

            else:
                    return True
        else:
            return False
    def _invoice_create_line(self, cr, uid, moves, journal_id, inv_type='out_invoice', context=None):
        invoice_obj = self.pool.get('account.invoice')
        move_obj = self.pool.get('stock.move')
        invoices = {}
        is_extra_move, extra_move_tax = move_obj._get_moves_taxes(cr, uid, moves, inv_type, context=context)
        product_price_unit = {}
        for move in moves:
            company = move.company_id
            origin = move.picking_id.name
            partner, user_id, currency_id = move_obj._get_master_data(cr, uid, move, company, context=context)
            """ rocco li 13-07-2017 rottura fattura solo partner e non per utente"""
            #key = (partner, currency_id, company.id, user_id)
            key = (partner, currency_id, company.id, uid)
            """ rocco li 13-07-2017 """
            
            invoice_vals = self._get_invoice_vals(cr, uid, key, inv_type, journal_id, move, context=context)

            if key not in invoices:
                # Get account and payment terms
                invoice_id = self._create_invoice_from_picking(cr, uid, move.picking_id, invoice_vals, context=context)
                invoices[key] = invoice_id
            else:
                invoice = invoice_obj.browse(cr, uid, invoices[key], context=context)
                merge_vals = {}
                if not invoice.origin or invoice_vals['origin'] not in invoice.origin.split(', '):
                    invoice_origin = filter(None, [invoice.origin, invoice_vals['origin']])
                    merge_vals['origin'] = ', '.join(invoice_origin)
                if invoice_vals.get('name', False) and (not invoice.name or invoice_vals['name'] not in invoice.name.split(', ')):
                    invoice_name = filter(None, [invoice.name, invoice_vals['name']])
                    merge_vals['name'] = ', '.join(invoice_name)
                if merge_vals:
                    invoice.write(merge_vals)
            invoice_line_vals = move_obj._get_invoice_line_vals(cr, uid, move, partner, inv_type, context=dict(context, fp_id=invoice_vals.get('fiscal_position', False)))
            invoice_line_vals['invoice_id'] = invoices[key]
            invoice_line_vals['origin'] = origin
            if not is_extra_move[move.id]:
                product_price_unit[invoice_line_vals['product_id'], invoice_line_vals['uos_id']] = invoice_line_vals['price_unit']
            if is_extra_move[move.id] and (invoice_line_vals['product_id'], invoice_line_vals['uos_id']) in product_price_unit:
                invoice_line_vals['price_unit'] = product_price_unit[invoice_line_vals['product_id'], invoice_line_vals['uos_id']]
            if is_extra_move[move.id]:
                desc = (inv_type in ('out_invoice', 'out_refund') and move.product_id.product_tmpl_id.description_sale) or \
                    (inv_type in ('in_invoice','in_refund') and move.product_id.product_tmpl_id.description_purchase)
                invoice_line_vals['name'] += ' ' + desc if desc else ''
                if extra_move_tax[move.picking_id, move.product_id]:
                    invoice_line_vals['invoice_line_tax_id'] = extra_move_tax[move.picking_id, move.product_id]
                #the default product taxes
                elif (0, move.product_id) in extra_move_tax:
                    invoice_line_vals['invoice_line_tax_id'] = extra_move_tax[0, move.product_id]

            move_obj._create_invoice_line_from_vals(cr, uid, move, invoice_line_vals, context=context)
            move_obj.write(cr, uid, move.id, {'invoice_state': 'invoiced'}, context=context)

        invoice_obj.button_compute(cr, uid, invoices.values(), context=context, set_total=(inv_type in ('in_invoice', 'in_refund')))
        return invoices.values()
class report_invoice_acc(models.AbstractModel):
    #Do not touch _name it must be same as _inherit
    #_name = 'report.report_invoice'
    _name = 'report.prof_webtex.report_invoice_acc'
    
    def convert_2float(self, value, precision=dp.get_precision('account_2_cifre'), currency_obj=None, context=None):
    
        fmt = '%f' if precision is None else '%.{precision}f'
    
        lang_code = self.env.context.get('lang') or 'en_US'
    
        lang = self.pool['res.lang']
    
        formatted = lang.format(self.env.cr, self.env.uid, [lang_code], fmt.format(precision=precision), value, grouping=True,     monetary=True)
    
        if currency_obj:
    
            if currency_obj.position == 'before':
        
                formatted = currency_obj.symbol + ' ' + formatted
        
            else:
        
                formatted = formatted + ' ' + currency_obj.symbol
        
            return formatted

    @api.multi
    def render_html(self, data=None):
        report_obj = self.env['report']#xx
        report = report_obj._get_report_from_name('prof_webtex.report_invoice_acc')
        docargs = {
    'convert_2float': self.convert_2float,
     'doc_ids': self._ids,
    'doc_model': report.model,
    'docs': self,
        }
        return report_obj.render('prof_webtex.report_invoice_acc', docargs)

class report_invoiceproforma(models.AbstractModel):

    _name = 'report.prof_webtex.report_invoiceproforma'
    
    def convert_2float(self, value, precision=dp.get_precision('account_2_cifre'), currency_obj=None, context=None):
    
        fmt = '%f' if precision is None else '%.{precision}f'
    
        lang_code = self.env.context.get('lang') or 'en_US'
    
        lang = self.pool['res.lang']
    
        formatted = lang.format(self.env.cr, self.env.uid, [lang_code], fmt.format(precision=precision), value, grouping=True,     monetary=True)
    
        if currency_obj:
    
            if currency_obj.position == 'before':
        
                formatted = currency_obj.symbol + ' ' + formatted
        
            else:
        
                formatted = formatted + ' ' + currency_obj.symbol
        
            return formatted

    @api.multi
    def render_html(self, data=None):
        report_obj = self.env['report']#xx
        report = report_obj._get_report_from_name('prof_webtex.report_invoiceproforma')
        docargs = {
    'convert_2float': self.convert_2float,
     'doc_ids': self._ids,
    'doc_model': report.model,
    'docs': self,
        }
        return report_obj.render('prof_webtex.report_invoiceproforma', docargs)

class report_invoice_document(models.AbstractModel):
    #Do not touch _name it must be same as _inherit
    #_name = 'report.report_invoice'
    _name = 'report.account.report_invoice_document'
    
    def convert_2float(self, value, precision=dp.get_precision('account_2_cifre'), currency_obj=None, context=None):
    
        fmt = '%f' if precision is None else '%.{precision}f'
    
        lang_code = self.env.context.get('lang') or 'en_US'
    
        lang = self.pool['res.lang']
    
        formatted = lang.format(self.env.cr, self.env.uid, [lang_code], fmt.format(precision=precision), value, grouping=True,     monetary=True)
    
        if currency_obj:
    
            if currency_obj.position == 'before':
        
                formatted = currency_obj.symbol + ' ' + formatted
        
            else:
        
                formatted = formatted + ' ' + currency_obj.symbol
        
            return formatted
    @api.multi
    def render_html(self, data=None):
        report_obj = self.env['report']#xx
        report = report_obj._get_report_from_name('account.report_invoice_document')
        docargs = {
    'convert_2float': self.convert_2float,
     'doc_ids': self._ids,
    'doc_model': report.model,
    'docs': self,
        }
        return report_obj.render('account.report_invoice_document', docargs)

class report_saleorderproforma(models.AbstractModel):

    _name = 'report.prof_webtex.report_saleorderproforma'
    
    def convert_2float(self, value, precision=dp.get_precision('account_2_cifre'), currency_obj=None, context=None):
    
        fmt = '%f' if precision is None else '%.{precision}f'
    
        lang_code = self.env.context.get('lang') or 'en_US'
    
        lang = self.pool['res.lang']
    
        formatted = lang.format(self.env.cr, self.env.uid, [lang_code], fmt.format(precision=precision), value, grouping=True,     monetary=True)
    
        if currency_obj:
    
            if currency_obj.position == 'before':
        
                formatted = currency_obj.symbol + ' ' + formatted
        
            else:
        
                formatted = formatted + ' ' + currency_obj.symbol
        
            return formatted

    @api.multi
    def render_html(self, data=None):
        report_obj = self.env['report']#xx
        report = report_obj._get_report_from_name('prof_webtex.report_saleorderproforma')
        docargs = {
    'convert_2float': self.convert_2float,
     'doc_ids': self._ids,
    'doc_model': report.model,
    'docs': self,
        }
        return report_obj.render('prof_webtex.report_saleorderproforma', docargs)

class prestashop_order_log(osv.osv):            
    _name="prestashop.order.log"
    _columns = {
        'name': fields.char('Order Ref Name',size=100),
        'object_name':fields.char('type',size=100),
         'ur_id':fields.integer('id name',required=False),    
        'erp_id':fields.integer('Openerp`s Order Id',required=False),    
        'presta_id':fields.integer('PrestaShop`s Order Id',required=False),            
        'data_log':fields.datetime('DataLOG',readonly=True),
        'object_name_save':fields.char('type_save',size=100),
   }
    _defaults = {  
            'data_log': lambda *a:  time.strftime('%Y-%m-%d %H:%M:%S'),  
            }
    @api.multi
    def rip_ps_key(self,multi=False):
        print 'rip_ps_key',multi#xxx
        ps_obj = self.env['prestashop.order']
        if multi==True:
            log_ids_obj=self.search([('id','in',self.env.context['active_ids'])])
            if log_ids_obj:
                ps_ids_obj=ps_obj.search([('erp_id','in',[x.erp_id for  x in log_ids_obj])])
            else:
                ps_ids_obj=None
        else:
            log_ids_obj=self.search([('id','=',self.id)])
            ps_ids_obj=ps_obj.search([('erp_id','=',self.erp_id)])
        for log_id_obj in log_ids_obj:
            if ps_ids_obj:
                    for ps_id_obj in ps_ids_obj:
                        ps_id_obj.unlink()
                    ps_obj.create({
                                             'name':log_id_obj.name,
                                             'object_name':log_id_obj.object_name_save,
                                             'ur_id':log_id_obj.ur_id,
                                             'erp_id':log_id_obj.erp_id,
                                             'presta_id':log_id_obj.presta_id
                                             })
            else:
                    ps_obj.create({
                                         'name':log_id_obj.name,
                                         'object_name':log_id_obj.object_name_save,
                                         'ur_id':log_id_obj.ur_id,
                                         'erp_id':log_id_obj.erp_id,
                                         'presta_id':log_id_obj.presta_id
                                         })
                
        if multi==True:
                for log_id_obj in log_ids_obj:
                    log_id_obj.write({'object_name':'UNLINK_ORDER'})
        else:
            self.write({'object_name':'UNLINK_ORDER'})
        return {}
    @api.multi
    def del_ps_key(self,multi=False):
        print 'del_ps_key',multi#xxx
        ps_obj = self.env['prestashop.order']
        if multi==True:
            log_ids_obj=self.search([('id','in',self.env.context['active_ids'])])
            if log_ids_obj:
                ps_ids_obj=ps_obj.search([('erp_id','in',[x.erp_id for  x in log_ids_obj])])
            else:
                ps_ids_obj=[]
        else:
            ps_ids_obj=ps_obj.search([('erp_id','=',self.erp_id)])
        for ps_id_obj in ps_ids_obj:
                ps_id_obj.unlink()  
                    #ps_id_obj.unlink()
        if multi==True:
                for log_id_obj in log_ids_obj:
                    log_id_obj.write({'object_name':'UNLINK_ORDER_OK'})
        else:
            self.write({'object_name':'UNLINK_ORDER_OK'})
        return {}
    @api.multi
    def del_all_ps_key(self):
                sale_obj=self.env['sale.order']
                res=sale_obj.del_unlink_ps_order()
                print 'all_del_ps_key'
                return res

class prestashop_order(osv.osv):            
    _inherit="prestashop.order"
    def get_id(self,cr,uid,shop,object,ur_id,context=None):
        result_id=super(prestashop_order, self).get_id(cr,uid,shop=shop,object=object,ur_id=ur_id,context=context)
        #ftry=True
        #if ftry:
        try:
                print 'get_id'    
                name='-'
                object_name='-'
                erp_id=False
                presta_id=False
                if context is None:
                    context = {}
                if shop=='prestashop':
                    presta_id=False
                    got_id=self.search(cr,uid,[('erp_id','=',ur_id)])
                    if got_id:
                        presta_id_obj=self.browse(cr,uid,got_id[0])
                        presta_id=presta_id_obj.presta_id
                        name=presta_id_obj.name
                        object_name=presta_id_obj.object_name
                elif shop=='openerp':
                    erp_id=False
                    got_id=self.search(cr,uid,[('presta_id','=',ur_id)])
                    if got_id:
                        erp_id_obj=self.browse(cr,uid,got_id[0])
                        erp_id=erp_id_obj.erp_id
                        name=erp_id_obj.name
                        object_name=erp_id_obj.object_name
                else:
                        name='-'
                        object_name='-'
                        erp_id=False
                        presta_id=False
                   
        
                log_presa_obj=self.pool.get('prestashop.order.log')
                log_presa_obj.create(cr,uid,{'name':name + '_' + shop,
                             'object_name':object_name,
                             'ur_id':ur_id,
                             'erp_id':erp_id,
                             'presta_id':presta_id
                             })
        except:
                print 'Errore_get_id'    
        return result_id
    def get_all_ids(self,cr,uid,shop,object,context=None):
        result_id=super(prestashop_order, self).get_all_ids(cr,uid,shop=shop,object=object,context=context)
        try:
            print 'get_all_ids'    
    
            if context is None:
                context = {}
            all_ids=[]
            if shop=='prestashop':
                got_ids=self.search(cr,uid,[('object_name','=',object)])
                for i in got_ids:
                    all_ids.append(i.presta_id)
            elif shop=='openerp':
                got_ids=self.search(cr,uid,[('object_name','=',object)])
                for i in got_ids:
                    all_ids.append(self.browse(cr,uid,i).erp_id)        
            log_presa_obj=self.pool.get('prestashop.order.log')
            for all_id in self.browse(cr,uid,all_ids,context=context):
                log_presa_obj.create(cr,uid,{'name':all_id.name+'_' + shop,
                                             'object_name':all_id.object_name,
                                             'ur_id':None,
                                             'erp_id':all_id.erp_id,
                                             'presta_id':all_id.presta_id,
    
                         })
        except:
            print 'Errore_get_all_ids'    
        return result_id
    @api.model
    @api.returns('self', lambda value:value.id)
    def create(self, vals):
        res=super(prestashop_order, self).create(vals)
        log_presa_obj=self.env['prestashop.order.log']
        log_presa_obj.create({'name':vals.get('name','/')+'_create',
                     'object_name':vals.get('object_name','/'),
                     'erp_id':vals.get('erp_id',None),
                     'presta_id':vals.get('presta_id',None)
                     })
        return res
    @api.multi
    def write(self, vals):
        res=super(prestashop_order, self).create(vals)
        log_presa_obj=self.env['prestashop.order.log']
        log_presa_obj.create({'name':vals.get('name','//')+'_write',
                     'object_name':vals.get('object_name','//'),
                     'erp_id':vals.get('erp_id',None),
                     'presta_id':vals.get('presta_id',None)
                     })
        return res
    def unlink(self, cr, uid, ids, context=None):
        
        for ps_obj_id in self.browse(cr, uid, ids, context):
            log_presa_obj=self.pool.get('prestashop.order.log')
            log_presa_obj.create(cr,uid,{'name':ps_obj_id.name +'_delete',
                         'object_name':ps_obj_id.object_name,
                         'ur_id':None,
                          'erp_id':ps_obj_id.erp_id,
                         'presta_id':ps_obj_id.presta_id
                         })
        res=super(prestashop_order, self).unlink( cr, uid, ids, context=context)
        
        return res
        #Do not touch _name it must be same as _inherit
        #_name = 'account.invoice'                            #_name = 'account.invoice'     
        #Do not touch _name it must be same as _inherit
        #_name = 'stock.picking'                                    #Do not touch _name it must be same as _inherit
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
     
                        #Do not touch _name it must be same as _inherit
                        #_name = 'account.invoice'_
class force_done(osv.osv):            
    _inherit="force.done"
    def create_n_confirm_order(self,cr,uid,order_data,line_data,context=None):
        result=super(force_done, self).create_n_confirm_order(cr,uid,order_data=order_data,line_data=line_data,context=context)
        try:
            print 'force_done'    
            if result:
                for res_id in result:
                    log_presa_obj=self.pool.get('prestashop.order.log')
                    log_presa_obj.create(cr,uid,{'name':res_id['erp_order_name'] +'_Force',
                                 'object_name':'order',
                                 'ur_id':None,
                                  'erp_id':res_id['erp_order_id'],
                                 'presta_id':res_id['prst_order_id']
                                 })
        except:
            print 'Errore_force_done'    
        return  result
class procurement_order(osv.osv):
    """
    Procurement Orders
    """
    _inherit = "procurement.order"
    @api.multi
    def cancel_ids(self):
        active_ids= self.env.context.get('active_ids',[])
        for proc_id_obj in self.browse(active_ids):
            proc_id_obj.cancel()
        return 