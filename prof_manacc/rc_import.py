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
#from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare, float_is_zero

from openerp import netsvc
#import addons.decimal_precision as dp
import openerp.addons.decimal_precision as dp
import xxsubtype
import itertools
from lxml import etree
from openerp import api
from openerp import SUPERUSER_ID
import tempfile
import csv
from openerp.tools.misc import ustr
from openerp.osv.fields import _column
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
import logging
_logger = logging.getLogger(__name__)
from openerp import models, fields as x_fields, _
class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
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
                res['value']['name'] = variant and "[%s]%s (%s)" % (product_id_obj.default_code,product_id_obj.name, variant) or  "[%s]%s" % (product_id_obj.default_code,product_id_obj.name)      
                
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

class sale_order(osv.osv):
    _inherit = "sale.order"
    def _state_invoice(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if context is None:
            context = {}
        """"---"""
        state='Da_fatturare'
        for sale_id_obj in self.browse(cr, uid, ids, context):
            res[sale_id_obj.id]=''
            state='Da_fatturare'
            num_ddt_nofat=0
            for picking_id_obj in sale_id_obj.picking_ids:
                for ddt_id in picking_id_obj.ddt_ids:
                        if ddt_id.invoice_id:
                            if ddt_id.invoice_id.state != 'cancel':
                                       state='Fatturate'
                        else:
                            num_ddt_nofat+=1
            if state=='Fatturate' and num_ddt_nofat>0:
                        state='Fatturate_parzialmente'
            if sale_id_obj.state=='done' and num_ddt_nofat<=0:
                    state='Fatturate'

            res[sale_id_obj.id]=state
            if sale_id_obj.x_invoice_state!=res[sale_id_obj.id]:
                    self.write(cr,uid,sale_id_obj.id,{'x_invoice_state':res[sale_id_obj.id]})
        return res
    _columns = {
        'x_y_invoice_state': fields.function(_state_invoice, string='Fattura DDT',type='char'),
         'x_invoice_state':fields.char('Fattura DDT', size=256, required=False, readonly=True),
                    } 

class product_attribute_value(osv.osv):
    _inherit = "product.attribute.value"
    _columns = {
                    'x_fatt_molt': fields.float('Fatt.Moltiplicativo', digits_compute=dp.get_precision('Product UoS')),

                    } 
    _defaults = {  
        'x_fatt_molt': 1,  
        }
    _order = 'attribute_id,name'
class res_partner(osv.osv):
    _inherit = "res.partner"
    def simple_vat_check(self, cr, uid, country_code, vat_number, context=None):
        '''
        Check the VAT number depending of the country.
        http://sima-pc.com/nif.php
        '''
        if not ustr(country_code).encode('utf-8').isalpha():
            return False
        check_func_name = 'check_vat_' + country_code
        check_func = getattr(self, check_func_name, None) or \
                        getattr(vat_number, check_func_name, None)
        if not check_func:
            # No VAT validation available, default to check that the country code exists
            check_func_name = 'check_vat_' + 'xx'
            return check_func(vat_number)
            res_country = self.pool.get('res.country')
            return bool(res_country.search(cr, uid, [('code', '=ilike', country_code)], context=context))
        return check_func(vat_number)
    def check_vat_se(self, vat):
        return 12
    def check_vat_xx(self, vat):
        return 11
    def check_vat_it(self, vat):
        return 11
    def check_vat_es(self, vat):
        return 9
    def check_vat_be(self, vat):
        return 10
    def check_vat_gr(self, vat):
        return 8
    def check_vat_pt(self, vat):
        return 9
    def check_vat_ru(self, vat):
        return 10
    def check_vat_fr(self, vat):
        return 11

class res_bank(osv.osv):
    _inherit = "res.bank"
    _columns = {
        'x_code': fields.char('Codice Banca', size=64 , required=False),
     }
class res_partner_import_manacc(osv.osv):
    """ partner Import """

    _name = "res.partner.import.manacc"
    _description = "partner Import "
    _columns = {
        'name': fields.char('identificativo di ricezione  clienti', size=128 , required=True),
        'data': fields.binary('File', required=False),
        'f_clienti': fields.boolean('Clienti', required=False),
        'f_fornitori': fields.boolean('Fornitori', required=False),
        'overwrite': fields.boolean('Sovrascrivi record esistenti',
                                    help=" i record esistenti  "
                                         ""),

     }
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
                fileformat = first_line.endswith("codice,ragsoc,citta,indirizzo,"#3 
                "prov,nazione,cap,tele,fax,part_iva,c_fisca,"#11
                "zona,age,divisa,listino,cod_pers,classe,commerciale,tipo_sped,porto,mezzo"#21
                "sconto_cassa,sconto_1,sconto_2,sconto_3,codice_pagamento,"#26
                "b_app,fido,abi_clie,cab_cli,p_fis,escusione_mesi,an_ccon,"#33
                "codice_banca,ccorr_bancario,anceiv,"#36
                "anclin,apimb,anptra,antana,ancfor,ancana,ancsco,anpseudo,anute,anfdif,"#46
                "ancord,anciso,annome,ancognome,anrefer,antcell,anesten,"#53
                "anlettera,annota,ancocli,ancocpar,ancclicont,ancivacont,ancage2,ancodpag,"#61
                "anaccorpa,anrubrica,ancmail"#64
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
                self.load_data( cr, uid, ids ,fileobj, fileformat, context=context)
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
    def load_data(self, cr, uid, ids, fileobj, fileformat,  context=None):
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
        bank_partner_obj = pool.get('res.partner.bank') 
        bank_obj = pool.get('res.bank') 
        bank_obj = pool.get('res.bank') 
        list_obj = pool.get('product.pricelist') 
        list_ver_obj = pool.get('product.pricelist.version') 
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
                        if row[8]=='':
                                    row[8]=None

                        """ creo il cliente"""
                        if len(str(row[10]).strip())==16:
                            partner_ids = partner_obj.search(cr, uid, [('fiscalcode','=',row[10])])    
                            if  not partner_ids:   
                                partner_ids = partner_obj.search(cr, uid, [('name','=',row[1])])    
                                F_fiscode=False
                            else:
                                F_fiscode=True
                        else:
                                partner_ids = partner_obj.search(cr, uid, [('name','=',row[1])])    
                        province_ids= province_obj.search(cr, uid, [('code','=',row[4])])
                        if str(row[5]).upper()=='ITA':
                            row[5]='IT'
                        country_ids= country_obj.search(cr, uid, [('code','=',row[5])])     
                        if not country_ids:
                            country_ids= country_obj.search(cr, uid, [('code','=',"IT")])     
                        if row[19]=='0':
                            row[19]='porto franco'.upper()
                        porto_ids= porto_obj.search(cr, uid, [('note','=',row[19])])     
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
                        zip_ids= zip_obj.search(cr, uid, [('name','=',row[6]),('country_id','=',country_ids_id)])
                        if zip_ids:
                            zip_id_obj=zip_obj.browse(cr,uid,zip_ids[0])
                        else:
                            zip_id_obj=None
                        if not porto_ids:
                                porto_ids_id=1
                        else:
                                porto_ids_id=porto_ids[0]
 
                        
                    # lets create the language with locale information
                        #if len(row[9])<=11:
                        #         row[9]=str(row[9]).zfill(11)
                                  
                        if row[9]=='00000000000':
                            row[9]=''
                        if row[9]=='0':
                            row[9]=''
                        if len(row[9])>9:
                            if country_code != None:
                                     vat=country_code+row[9]
                            else:
                                     vat=row[9]
                            if row[9]=='':
                                        row[9]=None
                                        vat=None
                        else:
                            vat=None
                                               
                        #if not isnumeric(str(row[9])):        
                        #            vat=None 
                        print 'ancpag-->',row[25]
                        pay_ids=payment_term_obj.search(cr,uid,[('id','>',0)])
                        
                        print 'pay_ids-->',pay_ids
                        pay_id=None
                        if pay_ids:
                            for pay_id_obj in payment_term_obj.browse(cr,uid,pay_ids,context=context):
                                if pay_id_obj.note.find(row[25]):
                                    pay_id=pay_id_obj.id
                                    exit
                        vals={
                              'is_company':True if vat else False ,
                              'ref':row[0],
                              'name':row[1],
                              'x_rsoc_est':row[52],
                              'street':row[3],
                              'zip':row[6],
                              'city':row[2],
                              'province':province_ids_id,
                              'country':country_ids_id,
                              'email':row[53],
                              'customer':True if row[39]=='C' else False,
                              'supplier':True if row[39]=='F' else False,
                              'phone':row[7],
                              'fax':row[8],
                              'vat_subjected':True if (vat) else False,
                              'vat':vat,
                              'fiscalcode':row[10] if len(row[10])==16 else None,
                              'carriage_condition_id':porto_ids_id,
                              'transportation_reason_id':1,
                              'goods_description_id':1,
                              'property_payment_term':pay_id if row[39]=='C' else False,
                              'property_supplier_payment_term':pay_id if row[39]=='F' else False,
                              'x_spese_id':1 if pay_id_obj.riba==True else False
                               }# skip empty rows and rows where the translation field (=last fiefd) is empty
                        list_ids=list_obj.search(cr,uid,[('name','=',row[14])],context=context)
                        if list_ids:
                            vals.update({'property_product_pricelist':list_ids[0]})
                        else:
                            list_id=list_obj.create(cr,uid,{
                                'name':row[14],
                                'type':'sale',
                                },context=context)
                            list_ver_id=list_ver_obj.create(cr,uid,{
                                'name':row[14],
                                'pricelist_id':list_id,
                                
                                })
                            vals.update({'property_product_pricelist':list_id})
                        print 'cliente-->'+str(line)+'cod_fis->'+str(vals['fiscalcode'])+'par_iva->'+str(vals['vat'])        
                        if not partner_ids:
                                partner_ids_id=partner_obj.create(cr, uid, vals, context=context)
                                
                        else:
                              partner_ids_id=partner_ids[0]
                              if this.overwrite:
                               partner_obj.write(cr, uid, partner_ids_id,vals, context=context)
                        #_logger.info("importazione effettuata con successo-->"+str(line))
                        '''aggiungi aggiungi banca''' 
                        bank_ids = bank_obj.search(cr, uid, [('x_code','=',row[33])])    
                        if bank_ids==[]:
                            bank_ids = bank_obj.search(cr, uid, [('abi','=',row[28]),('cab','=',row[29])])    
                        if bank_ids:
                             bank_ids_obj=bank_obj.browse(cr, uid, bank_ids[0], context=context)
                             bank_partner_ids = bank_partner_obj.search(cr, uid, [('partner_id','=',partner_ids_id)]) 
                             vals={
                                   'bank_name':bank_ids_obj.name,
                                   'owner_name':row[1],
                                   'partner_id':partner_ids_id,
                                   'acc_number':'00000000',
                                   'state':'bank',
                                   'bank':bank_ids[0],
                                   'journal_id':8,
                                   'zip':row[6],
                                   'street':row[3],
                                   'city':row[2]
                                   }
                             if bank_partner_ids:
                                 bank_partner_ids_id=bank_partner_ids[0]
                                 bank_partner_obj.write(cr, uid, bank_partner_ids[0], vals, context)
                             else:
                                 bank_partner_ids_id=bank_partner_obj.create(cr, uid, vals, context)       
                                 
            return True  
        except IOError:
                        _logger.info("importazione non effettuata ")
 
                        return False 
                        """
                        raise osv.except_osv(_("Errore %s"), _('ricezione disponibilita'))
                        """
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
                              'abi':row[4],
                              'cab':row[5],
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
                        bank_ids = bank_obj.search(cr, uid, [('abi','=',row[0]),('cab','=',row[1])])    

                        
                    # lets create the language with locale information
                        
                        
                        #if not isnumeric(str(row[9])):        
                        #            vat=None

                        vals={
                              'name':row[2],
                              'street':row[3],
                              'abi':row[0],
                              'cab':row[1],
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
                        product_ids = product_obj.search(cr, uid, [('default_code','=',str(row[0]))])    
                        
                        vals={
                              'default_code':str(row[0]),
                              'name':str(row[1])[0:63],
                             'list_price':0.00,
                             'standard_price':0.00,
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
        templ_obj=self.pool.get('product.template')
        product_obj=self.pool.get('product.product')
        var_obj=self.pool.get('product.product')
        categ_obj=self.pool.get('product.category')
        attrib_obj = self.pool.get('product.attribute')
        attrib_price_obj = self.pool.get('product.attribute.price')
        attrib_value_obj = self.pool.get('product.attribute.value')
        attrib_line_obj = self.pool.get('product.attribute.line')
        list_obj = self.pool.get('product.pricelist') 
        list_ver_obj = self.pool.get('product.pricelist.version') 
        list_item_obj = self.pool.get('product.pricelist.item') 

        tax_obj=pool.get('account.tax')
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
            line = 1.0000   
            seq =  0
            col_attr=[]
            model={}
            for row in reader:
                        """ trovo prodotto"""
                        product_ids = product_obj.search(cr, uid, [('default_code','=',str(row[1]))])    
                        if product_ids:
                            product_id_obj=product_obj.browse(cr,uid,product_ids[0],context=context)
                        else:
                            continue
                        prod_tmp_ids_id=product_id_obj.product_tmpl_id.id
                        tax_ids = tax_obj.search(cr, uid, [('amount','=', 0.22),('type_tax_use','in',['sale','all'])])
                        if not tax_ids:
                                 raise osv.except_osv(_("imposta   non trovata caricare imposta e riprovare"),_(""))
                          # lets create the language with locale information
                                 break
                        tax_ids_id=tax_ids[0]
                        tax_ids = tax_obj.search(cr, uid, [('amount','=', 0.22),('type_tax_use','in',['purchase','all'])])
                        if not tax_ids:
                                 raise osv.except_osv(_("imposta   non trovata caricare imposta e riprovare"),_(""))
                          # lets create the language with locale information
                                 break
                        tax_ids_acq=tax_ids[0]
                        #attributo finitura
                        if row[3]:
                                    attrib_ids = attrib_obj.search(cr, uid, [('name','=', 'FINITURA')])    
                                    if attrib_ids:
                                        attribute_id=attrib_ids[0]
                                    else:
                                        attribute_id=attrib_obj.create(cr,uid,{'name':'FINITURA'})
                                    FINITURA=None  
                                    if str(row[3]).strip()!='':
                                            try:
                                              FINITURA=str(row[3]).encode('UTF-8')
                                            except:
                                              FINITURA='ERRORE-'+str(row)+'-2'
                                      
                                    else:
                                          FINITURA='-'
                                    #attributo valore
                                    if FINITURA:
                                            if attribute_id:
                                                attrib_value_ids = attrib_value_obj.search(cr, uid, [('attribute_id','=',attribute_id),('name','=', FINITURA)])
                                            else:
                                                attrib_value_ids=[]
                                            if attrib_value_ids:
                                                attrib_value_id=attrib_value_ids[0]
                                                col_attr.append(attrib_value_id)
                                            else:
                                                seq+=10
                                                attrib_value_id=attrib_value_obj.create(cr,uid,{'attribute_id':attribute_id,'name':FINITURA,'sequence':seq,})
                                                col_attr.append(attrib_value_id)
                                    else:
                                            attrib_value_id=None
                        if   model.get(str(row[1]+'_FINI'),None)==None:                  
                            model[str(row[1])+'_FINI']=[]
                        if attrib_value_id not in model.get(row[1]+'_FINI',[]):
                            model[str(row[1])+'_FINI'].append(attrib_value_id)
                        if row[2]:
                            attrib_price_ids = attrib_price_obj.search(cr, uid, [('product_tmpl_id','=',prod_tmp_ids_id),('value_id','=', attrib_value_id)])    
                            if attrib_price_ids:
                                attrib_price_id=attrib_price_ids[0]
                            else:
                                attrib_price_id=attrib_price_obj.create(cr,uid,{'product_tmpl_id':prod_tmp_ids_id,'value_id':attrib_value_id,'price_extra':0})
                        #colore al modello
                        if row[3]:
                            attrib_value_ids = attrib_value_obj.search(cr, uid, [('attribute_id','=',attribute_id)])    
                            attrib_value_ids_obj=attrib_value_obj.browse(cr,uid,attrib_value_ids,context=context)
                            attrib_line_ids = attrib_line_obj.search(cr, uid, [('product_tmpl_id','=', prod_tmp_ids_id),('attribute_id','=',attribute_id)])    
                            if attrib_line_ids:
                                attrib_line_id=attrib_line_ids[0]
                                attrib_line_obj.write(cr,uid,attrib_line_id,{'value_ids':[(6, 0, model[str(row[1])+'_FINI'])]})
                            else:
                                
                                attrib_line_id=attrib_line_obj.create(cr,uid,{'product_tmpl_id':prod_tmp_ids_id,'attribute_id':attribute_id,'value_ids':[(6, 0, model[str(row[1]+'_FINI')])]})
                        line +=1        
                        """ trovo variante"""
                        var_ids = var_obj.search(cr, uid, [('default_code','=',str(row[1]+'-'+row[3]))])    
                        if var_ids:
                            
                            vals={
                               'list_price':0,
                              'wk_extra_price':0,
                                   'taxes_id': [(6, 0, [x.id for x in tax_obj.browse(cr,uid,[tax_ids_id],context=context)])],
                                   'supplier_taxes_id':[(6, 0, [x.id for x in tax_obj.browse(cr,uid,[tax_ids_acq],context=context)])],
                                   'attribute_value_ids':[(6,0,[attrib_value_id,])]
                                   }# skip empty rows and rows where the translation field (=last fiefd) is empty
                            #print 'banca-->'+str(line)+'name->'+str(vals['name'])+'city->'+str(vals['street'])        
                        else:
                            vals={
                                   'product_tmpl_id':product_id_obj.product_tmpl_id.id,
                                   'default_code':str(row[1]+'-'+row[3]),
                                   'name':product_id_obj.name,
                                   'list_price':0,
                                   'wk_extra_price':0,
                                   'standard_price':0,
                                   'type':'product',
                                   'categ_id': product_id_obj.product_tmpl_id.categ_id.id,
                                   'rental':True,
                                   'state':'sellable',
                                   'taxes_id': [(6, 0, [x.id for x in tax_obj.browse(cr,uid,[tax_ids_id],context=context)])],
                                   'supplier_taxes_id':[(6, 0, [x.id for x in tax_obj.browse(cr,uid,[tax_ids_acq],context=context)])],
                                   'attribute_value_ids':[(6,0,[attrib_value_id,])]
                                   }# skip empty rows and rows where the translation field (=last fiefd) is empty
                        #print 'banca-->'+str(line)+'name->'+str(vals['name'])+'city->'+str(vals['street'])        
                        if not var_ids:
                                product_id=var_obj.create(cr, uid, vals, context=context)
                        else:
                            product_id=var_ids[0]
                            if this.overwrite:
                                var_obj.write(cr, uid, product_id,vals, context=context)
                        #_logger.info("importazione effettuata con successo-->"+str(line))
                        var_id_obj=var_obj.browse(cr,uid,product_id,context=context)
                        #""" trovo listino"""
                        #list_ids = list_obj.search(cr, uid, [('name','=',str(row[0]))])    
                        #""" trovo listino versione 
                        #"""
                        ver_ids = list_ver_obj.search(cr, uid, [('name','=',str(row[0]))])    
                        if ver_ids:
                            ver_id_obj=list_ver_obj.browse(cr,uid,ver_ids[0],context=context)
                            list_id_obj=ver_id_obj.pricelist_id
                            #list_id_obj=list_obj_ver.browse(cr,uid,list_ids[0],context=context)
                            list_item_ids = list_item_obj.search(cr, uid, [
                                                                           ('price_version_id','=',ver_id_obj.id),
                                                                           ('product_id','=',product_id)])    
                            if list_item_ids:
                                if this.overwrite:
                                    list_item_id=list_item_obj.write(cr,uid,list_item_ids[0],{
                                        'price_surcharge':row[5].replace(',','.'),
                                        'base':1,
                                        'name':var_id_obj.default_code
                                    
                                        }
                                    )
                            else:    
                                print 'voce_listino',row[0],row[1]+'-'+row[3]
                                list_item_id=list_item_obj.create(cr,uid,{
                                    'product_id':product_id,
                                    'price_surcharge':row[5].replace(',','.'),
                                    'base':1,
                                    'price_version_id':list_id_obj.version_id[0].id,
                                    'name':var_id_obj.default_code
                                    }
                                    ,context=context)
                        decimale=float(line/1000)
                        intero=int(line/1000)
                        if decimale == intero:
                            print 'line_1000',line,decimale,intero
                        try:
                                cr.commit()
                        except:
                                cr.rollback()
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
                     'volume':row[22] or 0.0,
                     'weight_net':row[28] or 0.0,
                     'weight':row[29] or 0.0,
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
                     'volume':row[22] or 0.0 ,
                     'weight_net':row[28] or 0.0,
                     'weight':row[29] or 0.0,
                     }# skip empty rows and rows where the translation field (=last fiefd) is empty

                       print 'val_prodotto_2',row[1],vals
                       product_obj.write(cr, uid, prod_ids_id, vals, context)
                       
                prod_ids_rec=product_obj.browse(cr, uid,prod_ids_id,context)
                if prod_ids_id:
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
            filename = '[lang: %s][format: %s]' % (iso_lang or 'new', fileformat)
            raise osv.except_osv(_("Impossibile leggere ilfile %s"), _(filename))
class product_template(osv.osv):
    _inherit = "product.template"
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

    _columns = {
        'x_price_subtax': fields.function(_price_subtax_, string='Sub_tax', digits_compute= dp.get_precision('Product Price')),
        'description': fields.html('Description', translate=True, sanitize=False, help="Rich-text/HTML version of the message (placeholders may be used here)"),
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

class product_product(osv.osv):
    _inherit = "product.product"
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
    _columns = {
        'description': fields.html('Description', translate=True, sanitize=False, help="Rich-text/HTML version of the message (placeholders may be used here)"),
        'x_price_subtax': fields.function(_price_subtax_, string='Subtax', digits_compute= dp.get_precision('Product Price')),
        'standard_price': fields.property(type = 'float', digits_compute=dp.get_precision('Product Price'), 
                                          help="Cost price of the product template used for standard stock valuation in accounting and used as a base price on purchase orders. "
                                               "Expressed in the default unit of measure of the product.",
                                          groups="base.group_user", string="Cost Price"),
    }
    @api.model
    @api.returns('self', lambda value:value.id)
    def create(self, vals):
        print 'vals',vals
        if hasattr(self._ids, '__iter__'):
                        if vals.get('default_code',None)==None:
                            codice=None
                            if 'product_tmpl_id' in vals:
                                variants=self.search([('product_tmpl_id','=',vals['product_tmpl_id'])])
                                print 'product_tmpl_id',self.product_tmpl_id.id
                            else:
                                variants=[]
                            for variant in variants:
                                print 'codice_iter_self',codice
                                if variant.default_code:
                                    codice=variant.default_code
                                    break
                            print 'codice_self',codice
                            if codice:
                                #lung=codice.find('-')
                                #if lung > -1 :
                                #    codice=codice[0:lung]
                                #else:
                                    #codice=codice
                                vals['default_code']= codice
                         
                        if vals.get('standard_price',0)<=0:
                            vals['standard_price']=self.product_tmpl_id.standard_price
                
        else:
                    if vals.get('default_code',None)==None:
                            codice=None
                            variants=self.search([('product_tmpl_id','=',vals['product_tmpl_id'])])
                            for variant in variants:
                                if variant.default_code:
                                    codice=variant.default_code
                                    break
                            if codice:
                            #    lung=codice.find('-')
                            #    if lung > -1 :
                            #        codice=codice[0:lung]
                            #    else:
                            #        codice=codice
                                vals['default_code']=codice
                    if vals.get('standard_price',0)<=0:
                        vals['standard_price']=self.product_tmpl_id.standard_price
        res=super(product_product, self).create(vals)
        return res
    @api.multi
    def write(self, vals):
        print 'product_write',vals
        if hasattr(self._ids, '__iter__'):
            if self._ids:
                for myself in self:
                   if vals.has_key('default_code'):
                            codice=None
                            for variant in myself.product_tmpl_id.product_variant_ids:
                                if variant.default_code:
                                    codice=variant.default_code
                                    break
                            print 'codice_myw',codice
                            #if codice:
                            #    lung=codice.find('-')
                            #    if lung > -1 :
                            #        codice=codice[0:lung]
                            #    else:
                            #        codice=codice
                            if vals.get('default_code',None)==None:
                                vals['default_code']= codice
                   if vals.get('standard_price',None)==None:
                        if myself.standard_price:
                            vals['standard_price']=myself.standard_price
                        else:
                                vals['standard_price']=myself.product_tmpl_id.standard_price
            else:
                    if vals.has_key('default_code'):
                        if vals.get('default_code',None)==None:
                            codice=None
                            for variant in self.product_tmpl_id.product_variant_ids:
                                if variant.default_code:
                                    codice=variant.default_code
                                    break
                            print 'codice_selfw',codice
                            #if codice:
                            #    lung=codice.find('-')
                            #    if lung > -1 :
                            #        codice=codice[0:lung]
                            #    else:
                            #        codice=codice
                            if vals.get('default_code',None)==None:
                                vals['default_code']= codice
                    if vals.get('standard_price',None)==None:
                        if self.standard_price:
                            vals['standard_price']=self.standard_price
                        else:
                                vals['standard_price']=self.product_tmpl_id.standard_price
                
        else:
            if vals.has_key('default_code'):
                        if vals.get('default_code',None)==None:
                            codice=None
                            for variant in self.product_tmpl_id.product_variant_ids:
                                if variant.default_code:
                                    codice=variant.default_code
                                    break
                            print 'codice_selfw',codice
                            #if codice:
                            #    lung=codice.find('-')
                            #    if lung > -1 :
                            #        codice=codice[0:lung]
                            #    else:
                            #        codice=codice
                            if vals.get('default_code',None)==None:
                                vals['default_code']=codice
            if vals.get('standard_price',None)==None:
                        if self.standard_price:
                                vals['standard_price']=self.standard_price
                        else:
                                vals['standard_price']=self.product_tmpl_id.standard_price
        res=super(product_product, self).write(vals)
        return res

class StockPickingPackagePreparation(osv.osv):

    _inherit = 'stock.picking.package.preparation'
    _columns = {
    'show_price' : fields.boolean(string='Prezzi in bolla')
 }

class stock_move(osv.osv):

    _inherit = 'stock.move'
    _columns = {
    'price_unit': fields.float('Unit Price', required=True, digits_compute= dp.get_precision('Product Price'), ),
            
                    }

    @api.model
    @api.returns('self', lambda value:value.id)
    def create(self, vals):
        res=super(stock_move, self).create(vals)
        if res.price_unit==0.00:
                if res.procurement_id:
                    if res.procurement_id.sale_line_id:
                        sale_line_id_obj = res.procurement_id.sale_line_id
                        #sale_line_obj=self.env['sale.order.line']
                        #sale_line_id_obj=sale_line_obj.browse(vals.get('sale_line_id',None))
                        vals_upd={'price_unit':sale_line_id_obj.price_unit}
                        res.write(vals_upd)
        return res
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

class product_pricelist_item(osv.osv):

    _inherit = 'product.pricelist.item'
    _order = 'name DESC,id DESC'     
    @api.multi
    def product_id_change(self, product_id):
        res=super(product_pricelist_item, self).product_id_change( product_id)
        prod = self.env['product.product'].browse(product_id)
        print  'res_product_id_change', res
        print  'attribute_value_ids', prod.attribute_value_ids
        if prod.attribute_value_ids:
            name='['+ (prod.code or '') + ']' + prod.name + '-(' + prod.attribute_value_ids[0].name+')'
            return {'value': {'name': name}}
        return {}
    
    @api.multi
    def view_init(self,fields_list):
        print  'self.env.context', self.env.context
        #price_version_id = self.env.context and self.env.context.get('active_id', False)
        #self.price_version_id=self.env.context and self.env.context.get('active_id', False)
