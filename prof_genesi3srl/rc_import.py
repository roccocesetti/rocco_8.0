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
try:
    import vatnumber
except ImportError:
    _logger.warning("VAT validation partially unavailable because the `vatnumber` Python library cannot be found. "
                                          "Install it to support more countries, for example with `easy_install vatnumber`.")
    vatnumber = None
from openerp import models, fields as x_fields, _


class res_bank(osv.osv):
    _inherit = "res.bank"
    _columns = {
        'x_code': fields.char('Codice Banca', size=64 , required=False),
     }
class res_partner_import_genesi3srl(osv.osv):
    """ partner Import """

    _name = "res.partner.import.genesi3srl"
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
    _columns = {
        'description': fields.html('Description', translate=True, sanitize=False, help="Rich-text/HTML version of the message (placeholders may be used here)"),
    }
class product_product(osv.osv):
    _inherit = "product.product"
    _columns = {
        'description': fields.html('Description', translate=True, sanitize=False, help="Rich-text/HTML version of the message (placeholders may be used here)"),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4class StockPickingPackagePreparation(osv.osv):
class StockPickingPackagePreparation(osv.osv):
    _inherit = 'stock.picking.package.preparation'
    date_done = x_fields.Datetime(
        string='Shipping Date',
        readonly=False,
    )

"""
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
            
        invoice_id_obj = ddt_ids_obj.invoice_id.write(
                                                      {
                                            'origin': ddt_str,       
                                            'x_pack_ids':[(6, 0, [ddt_ids_obj.id])],
                                                       }
                                                      )
        return res
"""
class DdTCreateInvoice(models.TransientModel):

    _inherit = 'ddt.create.invoice' 
                        #Do not touch _name it must be same as _inherit
                        #_name = 'ddt.create.invoice' = "ddt.create.invoice"
    @api.multi
    def create_invoice(self):
        res=super(DdTCreateInvoice, self).create_invoice()
        ddt_model = self.env['stock.picking.package.preparation']
        invoice_obj = self.env['account.invoice']
        ddts = ddt_model.search(
            [('id', 'in', self.env.context['active_ids'])],
            order='partner_invoice_id')
        
        ddt_str=''
        for ddt_id_obj in ddts:
                if ddt_id_obj:
                    if ddt_id_obj.ddt_number==False:
                       ddt_id_obj.write({'ddt_number':'NO_DDT_NUM'})

                ddt_str+= '-' + ddt_id_obj.ddt_number
            
                for invoice_id_obj in invoice_obj.browse([ddt_id_obj.invoice_id.id]):
                    invoice_id_obj.write({
                                'x_pack_ids':[(6, 0, [ddts.id])],
                                'origin': ddt_str,       
        
                                          })
        return res
  
class account_move_line(osv.osv):
    _inherit = 'account.move.line'
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

class account_invoice(models.Model):
    _inherit = 'account.invoice'
    @api.model
    def _default_x_pay(self):
        x_pay="-"
        for pay in self.payment_ids:
            x_pay+=pay.journal_id.name
        print 'x_pay',x_pay
        return x_pay
    @api.one
    @api.depends('invoice_line.price_subtotal', 'tax_line.amount')
    def _compute_amount(self):
        res=super(account_invoice, self)._compute_amount()
        self.x_pay = self._default_x_pay
        

    amount_untaxed = x_fields.Float(string='Subtotal', digits=dp.get_precision('account_2_cifre'),
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
        return res
    @api.multi
    def invoice_print(self):
        """ Print the invoice and mark it as sent, so that we can see more
            easily the next step of the workflow
        """
        assert len(self) == 1, 'This option should only be used for a single id at a time.'
        self.sent = True
        return self.env['report'].get_action(self, 'prof_genesi3srl.report_invoice')
    @api.multi
    def crea_spedizione(self):
        #view_ref = self.env['ir.model.data'].get_object_reference('prof_webtex', 'view_sale_order_open_webtex')
        #view_id = view_ref and view_ref[1] or False,
        context = self._context.copy()
        if context is None:
            context = {}
        context.update({'default_invoice_package_id': self.id })
        package_obj=self.env['stock.picking.package.preparation']
        res_id_boj=package_obj.create({
                                           'partner_id':self.partner_id.id,
                                           'partner_invoice_id':self.partner_id.id,
                                           'partner_shipping_id':self.partner_id.id,
                                           'goods_description_id':self.partner_id.goods_description_id.id or None,
                                           'carriage_condition_id':self.partner_id.carriage_condition_id.id or None,
                                           'transportation_reason_id':self.partner_id.transportation_reason_id.id or None,
                                           'transportation_method_id':self.partner_id.transportation_method_id.id or None,
                                           'invoice_id':self.id,
                                           'parcels':1
                                           })
        self.write( {
                                            'origin': '',       
                                            'x_pack_ids':[(6, 0, [res_id_boj.id])],
                                                       }
                                                      )

        self.with_context(context)

        print 'self.env.context',self.env.context
        return {'name':_("Dati di Spedizione"),
                'view_mode': 'form',
                'view_id': None,
                'view_type': 'form',
                'res_model': 'stock.picking.package.preparation',
                'res_id': res_id_boj.id,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'normal',
                'domain': [('partner_id','=',self.partner_id.id)],                                 
                'context': context,                                 
            }

account_invoice()
class StockPickingPackagePreparation(osv.osv):

    _inherit = 'stock.picking.package.preparation'
    @api.multi
    def view_init(self,fields_list):
        #res=super(StockPickingPackagePreparation, self).view_init__(fields_list=fields_list)
        res=super(StockPickingPackagePreparation, self).view_init(fields_list)
        if res==None:###ll
            res={'value':{}}
        print 'view_init',res
        context = self.env.context
        if context.get('active_model') == 'account.invoice':
             invoice_ids_obj=self.env['account.invoice'].browse(context.get('active_ids'))
             for invoice_id_obj in invoice_ids_obj:
                res['value']['partner_id']=invoice_id_obj.partner_id.id
                res['value']['partner_invoice_id']=invoice_id_obj.partner_id.id
                res['value']['partner_shipping_id']=invoice_id_obj.partner_id.id
        return res
class report_invoice_acc(models.AbstractModel):
    #Do not touch _name it must be same as _inherit
    #_name = 'report.report_invoice'
    _name = 'report.prof_genesi3srl.report_invoice_acc'
    
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
        report = report_obj._get_report_from_name('prof_genesi3srl.report_invoice_acc')
        docargs = {
    'convert_2float': self.convert_2float,
     'doc_ids': self._ids,
    'doc_model': report.model,
    'docs': self,
        }
        return report_obj.render('prof_genesi3srl.report_invoice_acc', docargs)

class report_invoiceproforma(models.AbstractModel):

    _name = 'report.prof_genesi3srl.report_invoiceproforma'
    
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
        report = report_obj._get_report_from_name('prof_genesi3srl.report_invoiceproforma')
        docargs = {
    'convert_2float': self.convert_2float,
     'doc_ids': self._ids,
    'doc_model': report.model,
    'docs': self,
        }
        return report_obj.render('prof_genesi3srl.report_invoiceproforma', docargs)

class report_saleorderproforma(models.AbstractModel):

    _name = 'report.prof_genesi3srl.report_saleorderproforma'
    
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
        report = report_obj._get_report_from_name('prof_genesi3srl.report_saleorderproforma')
        docargs = {
    'convert_2float': self.convert_2float,
     'doc_ids': self._ids,
    'doc_model': report.model,
    'docs': self,
        }
        return report_obj.render('prof_genesi3srl.report_saleorderproforma', docargs)
