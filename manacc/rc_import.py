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
import addons.decimal_precision as dp
import xxsubtype
import itertools
from lxml import etree
from openerp import api
from openerp import SUPERUSER_ID
import tempfile
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

class res_bank(osv.osv):
    _inherit = "res.bank"
    _columns = {
        'x_code': fields.char('Codice Banca', size=64 , required=False),
     }
class res_partner_import_tecno(osv.osv):
    """ partner Import """

    _name = "res.partner.import.tecno"
    _description = "partner Import "
    _columns = {
        'name': fields.char('identificativo di ricezione  clienti', size=128 , required=True),
        'data': fields.binary('File', required=False),
        'f_clienti': fields.boolean('Clienti', required=False),
        'f_fornitori': fields.boolean('Fornitori', required=False),
        'overwrite': fields.boolean('Sovrascrivi i clienti esistenti',
                                    help=" i clienti esistenti  "
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
                fileformat = first_line.endswith("codice,RAGSOCIALE,indirizzo,cap"#3 
                "cap,citta,prov,reg,nazione,referente,tel,cell,fax,email,pec,cod_fisc,part_iva,"#16
                "codice_tess,punti_fed,"#18
                "listino,fido,agente,pagamento,banca,ns_banca,mandato,emissione_fdd,ffatt_con_iva,"#27
                "ac,ad,porto,rit_di_acconto,ag,ah,al,aj,ak,al,am,AN,AO,AP,AQ,AR,AS,NOTE"#45
                ) and 'csv' or 'csv'#46
                fileobj.seek(0)               
                self.load_data( cr, uid, ids ,fileobj, fileformat, context=context)
            elif  this.f_fornitori:
                        fileformat = first_line.endswith("codice,RAGSOCIALE,indirizzo,cap"#3 
                "cap,citta,prov,reg,nazione,referente,tel,cell,fax,email,pec,cod_fisc,part_iva,"#16
                "codice_tess,punti_fed,"#18
                "listino,fido,agente,pagamento,banca,ns_banca,mandato,emissione_fdd,ffatt_con_iva,"#27
                "ac,ad,porto,rit_di_acconto,ag,ah,al,aj,ak,al,am,AN,AO,AP,AQ,AR,AS,NOTE"#46
                ) and 'csv' or 'csv'#46
                        fileobj.seek(0)
                        
                        self.load_data_for( cr, uid, ids ,fileobj, fileformat, context=context)
                  
        finally:
            fileobj.close()
        return True
    def import_res_bank(self, cr, uid, ids, context=None):
        fileobj = TemporaryFile('w+')
        this = self.browse(cr, uid, ids[0])
        try:
            fileobj.write(base64.decodestring(this.data))
    
            # now we determine the file format
            fileobj.seek(0)
            first_line = fileobj.readline().strip().replace('"', '').replace(' ', '')
            fileformat = first_line.endswith("codice,RAGSOCIALE,indirizzo,cap"#3 
                "cap,citta,prov,reg,nazione,referente,tel,cell,fax,email,pec,cod_fisc,part_iva,"#16
                "codice_tess,punti_fed,"#18
                "listino,fido,agente,pagamento,banca,ns_banca,mandato,emissione_fdd,ffatt_con_iva,"#27
                "ac,ad,porto,rit_di_acconto,ag,ah,al,aj,ak,al,am,AN,AO,AP,AQ,AR,AS,NOTE"#9 
                ) and 'csv' or 'csv'#46
            fileobj.seek(0)               
            self.load_data_bank( cr, uid, ids ,fileobj, fileformat, context=context)
        finally:
            fileobj.close()
        return True
    def import_account_account(self, cr, uid, ids, context=None):
        fileobj = TemporaryFile('w+')
        this = self.browse(cr, uid, ids[0])
        try:
            fileobj.write(base64.decodestring(this.data))
    
            # now we determine the file format
            fileobj.seek(0)
            first_line = fileobj.readline().strip().replace('"', '').replace(' ', '')
            fileformat = first_line.endswith("codice,ragsoc,indirizzo,"#3 
                "cap,citta,abi,cab,swf,mia_ditta,piva_ditta,iban,"#9 
                ) and 'csv' or 'csv'#46
            fileobj.seek(0)               
            self.load_data_bank( cr, uid, ids ,fileobj, fileformat, context=context)
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
        province_obj = pool.get('res.province')
        country_obj = pool.get('res.country')
        tax_obj=pool.get('account.tax')
        payment_term_obj=pool.get('account.payment.term')
        porto_obj=pool.get('stock.picking.carriage_condition')
        bank_partner_obj = pool.get('res.partner.bank') 
        bank_obj = pool.get('res.bank')
        pricelist_obj = pool.get('product.pricelist')
 
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
                        if row[14]=='':
                                    row[14]=None
                        if row[15]=='':
                                    row[15]=None
                        """creo il termine di pagamento"""    
                        if row[22]=='':
                             row[22]='Da definire'
                        payment_term_ids = payment_term_obj.search(cr, uid, [('name','=',row[22])])    
                        if not payment_term_ids:
                     # lets create the language with locale information
                             vals={
                              'name':row[22],
                              'note':row[22],
                             }# skip empty rows and rows where the translation field (=last fiefd) is empty
                             payment_term_ids_id=payment_term_obj.create(cr, uid, vals, context=context)
                        else:
                             payment_term_ids_id=payment_term_ids[0]
                        '''trovo il listino'''
                        price_list_ids = pricelist_obj.search(cr, uid, [('name','=',row[19])],context=context)
                        if price_list_ids:
                            price_list_id=price_list_ids[0]
                        else:
                            price_list_id=None
                        """ creo il fornitore"""
                        if row[14]:
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
                            row[7]='Italia'
                            country_ids= country_obj.search(cr, uid, [('code','=',"IT")])     
                        porto_ids= porto_obj.search(cr, uid, [('note','=',row[30])])     
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
                        #if len(row[9])<=11:
                        #         row[9]=str(row[9]).zfill(11)
                        print 'row[15]-->',row[15]
                        if row[15]=='':
                                    row[15]=''
                                    vat=None
                        if row[15]:
                                 while len(str(row[15]).strip())<11:
                                        row[15]='0'+str(row[15]).strip()
                        if country_code != None:
                                 vat=country_code+str(row[15])
                        else:
                                 if row[15]!=None:
                                     vat='IT'+str(row[15])
                                 else:    
                                     vat=None
                        #if not isnumeric(str(row[9])):        
                        #            vat=None

                        if row[15]=='SI':
                            wht_account_id=1
                        else:
                            wht_account_id=None
                        vals={
                              'is_company':True,
                              'ref':row[8],
                              'name':row[1],
                              'street':row[2],
                              'zip':row[3],
                              'city':row[4],
                              'province':province_ids_id,
                              'country':country_ids_id,
                              'email':row[12],
                              #'customer':this.f_clienti,
                              'supplier':this.f_fornitori,
                              'phone':row[9],
                              'fax':row[11],
                              'vat_subjected':True,
                              'vat':vat,
                              'fiscalcode':row[14],
                              'carriage_condition_id':porto_ids_id,
                              'transportation_reason_id':1,
                              'goods_description_id':1,
                              'wht_account_id':wht_account_id,
                              'comment':row[45],
                              'property_payment_term':payment_term_ids_id,
                              'property_product_pricelist':price_list_id       
                               }# skip empty rows and rows where the translation field (=last fiefd) is empty
                        print 'fornitore-->'+str(line)+'cod_fis->'+str(vals['fiscalcode'])+'par_iva->'+str(vals['vat'])        
                        if not partner_ids:
                                partner_ids_id=partner_obj.create(cr, uid, vals, context=context)
                        else:
                              partner_ids_id=partner_ids[0]
                              if F_fiscode:
                                vals['Individual']=this.f_fornitori
                              if this.overwrite:
                               partner_obj.write(cr, uid, partner_ids_id,vals, context=context)
                        #_logger.info("importazione effettuata con successo-->"+str(line))
                        '''aggiungi aggiungi banca''' 
                        if row[23]!='':        
                            bank_ids = bank_obj.search(cr, uid, [('x_code','=',row[23])])    
                            if bank_ids:
                                 bank_ids_obj=bank_obj.browse(cr, uid, bank_ids[0], context=context)
                                 #bank_partner_ids = bank_partner_obj.search(cr, uid, [('bank','=',bank_ids[0])]) 
                                 bank_partner_ids = bank_partner_obj.search(cr, uid, [('bank','=',bank_ids[0]),('partner_id','=',partner_ids_id)]) 
                                 vals={
                                       'bank_name':bank_ids_obj.name,
                                       'owner_name':row[1],
                                       'partner_id':partner_ids_id,
                                       'acc_number':'00000000',
                                       'state':'bank',
                                       'bank':bank_ids[0],
                                       'journal_id':8,
                                       'zip':row[2],
                                       'street':row[3],
                                       'city':row[4]
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
        province_obj = pool.get('res.province')
        country_obj = pool.get('res.country')
        tax_obj=pool.get('account.tax')
        payment_term_obj=pool.get('account.payment.term')
        porto_obj=pool.get('stock.picking.carriage_condition')
        bank_partner_obj = pool.get('res.partner.bank') 
        bank_obj = pool.get('res.bank') 
        pricelist_obj = pool.get('product.pricelist')
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
                        if row[14]=='':
                                    row[14]=None
                        if row[15]=='':
                                    row[15]=None
                        '''trovo il listino'''
                        price_list_ids = pricelist_obj.search(cr, uid, [('name','=',row[19])],context=context)
                        if price_list_ids:
                            price_list_id=price_list_ids[0]
                        else:
                            price_list_id=None
                        """creo il termine di pagamento"""    
                        if row[22]=='':
                             row[22]='Da definire'
                        payment_term_ids = payment_term_obj.search(cr, uid, [('name','=',row[22])])    
                        if not payment_term_ids:
                     # lets create the language with locale information
                             vals={
                              'name':row[22],
                              'note':row[22],
                             }# skip empty rows and rows where the translation field (=last fiefd) is empty
                             payment_term_ids_id=payment_term_obj.create(cr, uid, vals, context=context)
                        else:
                             payment_term_ids_id=payment_term_ids[0]

                        """ creo il cliente"""
                        if row[14]:
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
                            row[7]='Italia'
                            country_ids= country_obj.search(cr, uid, [('code','=',"IT")])     
                        porto_ids= porto_obj.search(cr, uid, [('note','=',row[30])])     
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
                        #if len(row[9])<=11:
                        #         row[9]=str(row[9]).zfill(11)
                        print 'row[15]-->',row[15]
                        if row[15]=='':
                                    row[15]=''
                                    vat=None
                        if row[15]:
                                 while len(str(row[15]).strip())<11:
                                        row[15]='0'+str(row[15]).strip()
                        if country_code != None:
                                 vat=country_code+str(row[15])
                        else:
                                 if row[15]!=None:
                                     vat='IT'+str(row[15])
                                 else:    
                                     vat=None
                        #if not isnumeric(str(row[9])):        
                        #            vat=None

                        vals={
                              'is_company':True,
                              'ref':row[8],
                              'name':row[1],
                              'street':row[2],
                              'zip':row[3],
                              'city':row[4],
                              'province':province_ids_id,
                              'country':country_ids_id,
                              'email':row[12],
                              'customer':this.f_clienti,
                              #'supplier':this.f_fornitori,
                              'phone':row[9],
                              'fax':row[11],
                              'vat_subjected':True,
                              'vat':vat,
                              'fiscalcode':row[14],
                              'carriage_condition_id':porto_ids_id,
                              'transportation_reason_id':1,
                              'goods_description_id':1,
                              'comment':row[45],
                              'property_payment_term':payment_term_ids_id,       
                              'property_product_pricelist':price_list_id       
                               }# skip empty rows and rows where the translation field (=last fiefd) is empty
                        print 'cliente-->'+str(line)+'cod_fis->'+str(vals['fiscalcode'])+'par_iva->'+str(vals['vat'])        
                        if not partner_ids:
                                partner_ids_id=partner_obj.create(cr, uid, vals, context=context)
                        else:
                              partner_ids_id=partner_ids[0]
                              if F_fiscode:
                                vals['Individual']=this.f_clienti
                              if this.overwrite:
                               partner_obj.write(cr, uid, partner_ids_id,vals, context=context)
                        #_logger.info("importazione effettuata con successo-->"+str(line))
                        '''aggiungi aggiungi banca''' 
                        if row[23]!='':
                            bank_ids = bank_obj.search(cr, uid, [('name','=',row[23])])    
                            if bank_ids:
                                 bank_ids_obj=bank_obj.browse(cr, uid, bank_ids[0], context=context)
                                 bank_partner_ids = bank_partner_obj.search(cr, uid, [('bank','=',bank_ids[0]),('partner_id','=',partner_ids_id)]) 
                                 vals={
                                       'bank_name':bank_ids_obj.name,
                                       'owner_name':row[1],
                                       'partner_id':partner_ids_id,
                                       'acc_number':'00000000',
                                       'state':'bank',
                                       'bank':bank_ids[0],
                                       'journal_id':8,
                                       'zip':row[2],
                                       'street':row[3],
                                       'city':row[4]
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
        pricelist_obj = pool.get('product.pricelist')
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
                        if row[23]!='':
                            line +=1        
                            """ creo il banca"""
                            bank_ids = bank_obj.search(cr, uid, [('name','=',row[23])])    
                            if str(row[23]).find("ABI"): 
                                ini=str(row[23]).find("ABI")
                            else:
                                ini=0    
                            if str(row[23]).find("CAB"): 
                                fin=str(row[23]).find("CAB")
                            else:
                                fin=0    
                            if ini>0:    
                                ABI=str(row[23])[ini+3:fin-1]
                                CAB=str(row[23])[fin+3:fin+9]
                                ABI=ABI.replace('.', '0').replace('-', '0').strip()
                                if len(ABI)<5:
                                    ABI='0'+ABI
                                CAB=CAB.replace('.', '0').replace('-', '0').strip()
                    
                            else:
                                ABI=''
                                CAB=''
                            vals={
                                  'name':row[23],
                                  'x_abi':ABI,
                                  'x_cab':CAB,
                                  'bic':None,
           
                                   }# skip empty rows and rows where the translation field (=last fiefd) is empty
                            print 'banca-->'+str(line)+'name->'+str(vals['name'])        
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
 