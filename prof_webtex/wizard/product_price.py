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
from openerp import api
from openerp import SUPERUSER_ID
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
from openerp.osv import orm
import tempfile
import csv
from os.path import join
import cStringIO
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


class product_price_list(osv.osv_memory):
    _name = 'product.price_list.prof_webtex'
    _description = 'Price List'
    def _default_list_pubblico_id(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id:
            if user.company_id.x_pubblico_id:
                return user.company_id.x_pubblico_id.id
                
            else:
                return None
        return None
    def _default_list_ingrosso_id(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id:
            if user.company_id.x_ingrosso_id:
                return user.company_id.x_ingrosso_id.id
                
            else:
                return None
        return None
    def _default_list_costo_id(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id:
            if user.company_id.x_costo_id:
                return user.company_id.x_costo_id.id
                
            else:
                return None
        return None

    _columns = {
        'price_list_pubblico': fields.many2one('product.pricelist', 'Listino 1', required=True),
        'price_list_ingrosso': fields.many2one('product.pricelist', 'Listino 2', required=False),
        'price_list_costo': fields.many2one('product.pricelist', 'Listino 3', required=False),
        'partner_id':fields.many2one('res.partner', 'Marchio', required=False,domain=[('supplier','=',True)]), 
        'da_prodotto': fields.many2one('product.product', 'da prodotto', required=False),
        'a_prodotto': fields.many2one('product.product', 'a prodotto', required=False),
        'da_categoria': fields.many2one('product.category', 'da categoria', required=False),
        'a_categoria': fields.many2one('product.category', 'a categoria', required=False),
        'dispo':fields.boolean('Stampa Disponibilità', required=False), 
        'x_rio_stock':fields.boolean('Stampa riordino', required=False), 
    }
    _defaults = {
    'price_list_pubblico':_default_list_pubblico_id,
    'price_list_ingrosso':_default_list_ingrosso_id,
    'price_list_costo':_default_list_costo_id,
    }

    def print_report(self, cr, uid, ids, context=None):
            if hasattr(ids, '__iter__'):
                ids=ids
            else:
                ids=[ids]
            """
            
            To get the date and print the report
            @return : return report
            """
            product_obj=self.pool.get('product.product')
            this=self.browse(cr, uid, ids[0], context=context)
            if context is None:
                context = {}
            if context.get('active_ids', []):
                datas = {'select':True,'ids': context.get('active_ids', [])}
            else:
                da_prodotto=None
                a_prodotto=None
                da_categoria=None
                a_categoria=None
                argo=[]
                if this.da_prodotto:
                    da_prodotto=('id','>=',this.da_prodotto.id)
                    argo.append(da_prodotto)
                if this.a_prodotto:
                    a_prodotto=('id','<=',this.a_prodotto.id)
                    argo.append(a_prodotto)
                if this.da_categoria:
                    da_categoria=('categ_id','>=',this.da_categoria.id)
                    argo.append(da_categoria)
                if this.a_categoria:
                    a_categoria=('categ_id','<=',this.a_categoria.id)
                    argo.append(a_categoria)
                
                prod_ids=product_obj.search(cr,uid,argo,context=context)
                datas = {'select':False,'ids': prod_ids}
                
            res = self.read(cr, uid, ids[0], ['price_list_pubblico','price_list_ingrosso', 'price_list_costo','da_prodotto','a_prodotto','da_categoria','a_categoria','dispo','x_rio_stock','partner_id'], context=context)
            res = res and res[0] or {}
            
            res['price_list_pubblico'] = res['price_list_pubblico'][0]
            if res['price_list_ingrosso']:
                res['price_list_ingrosso'] = res['price_list_ingrosso'][0]
            else:
                res['price_list_ingrosso']=None
            if res['price_list_costo']:
                res['price_list_costo'] = res['price_list_costo'][0]
            else:
                res['price_list_costo']=None
            if res['partner_id']:
                res['partner_id'] = res['partner_id'][0]
            else:
                res['partner_id']=None
            if res['da_prodotto']:
                res['da_prodotto'] = res['da_prodotto'][0]
            if res['a_prodotto']:
                res['a_prodotto'] = res['a_prodotto'][0]
            if res['da_categoria']:
                res['da_categoria'] = res['da_categoria'][0]
            if res['a_categoria']:
                res['a_categoria'] = res['a_categoria'][0]
            res['dispo']=res['dispo']
            res['x_rio_stock']=res['x_rio_stock']
            datas['form'] = res
            return self.pool['report'].get_action(cr, uid, [], 'prof_webtex.report_pricelist_prof_webtex', data=datas, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

    def export_product(self,cr,uid,ids,context=None):    
        
        #fileobj = TemporaryFile('w+')
        this = self.browse(cr, uid, ids[0])
        try:
            handle, filepath = tempfile.mkstemp()
            fileobj = os.fdopen(handle,'w+')  # convert raw handle to file object        try:
            
            fileobj.write(base64.decodestring(this.data))
            fileobj.close()
            #base64.decode(open(this.data), open(fileobj))
            #workbook = xlrd.open_workbook(filepath)
            #fileobj.write(base64.decodestring(this.data))
            #fileobj.write(this.data)
            """
            wb = xlwt.Workbook()
            #wb.save(this.data)
            #xlwt.Workbook.save(self, base64.decodestring(this.data))
            wb.set_active_sheet(0)
            wb.active_sheet=0
            as=wb.get_active_sheet()
            wbf = wb.save(base64.decodestring(this.data))
            fileobj=wbf
            """
            # now we determine the file format
            """
            fileobj.seek(0)
            first_line = fileobj.readline().strip().replace('"', '').replace(' ', '')
            fileformat = first_line.endswith("Cod_pro,Descrizione,Tipologia,Categoria,"#3 
            "Sottocategoria,Cod_Udm,Cod_Iva,Listino_1_ivato,Listino_2_ivato,Listino_3_ivato,"#9 
            ",Cod_barre,"#10
            "Produttore,Cod_fornitore,Fornitore,"#13
            "Prezzo_forn,Ubicazione,cod_produttore"#16
            ) and 'csv' or 'csv'#46
            
            fileobj.seek(0)
            """
            #input_file = request.FILES.get(this.data)
            self.export_data( cr, uid, ids ,filepath, context=context)
        finally:
            os.unlink(filepath)  # delete t
        return True


    def export_data(self, cr, uid, ids, filepath,  context=None):
        db_name = cr.dbname
        pool = pooler.get_pool(db_name)
        partner_obj = pool.get('res.partner')
        product_obj = pool.get('product.product')
        product_tmp_obj = pool.get('product.template')
        product_tax = pool.get('product.taxes.rel')
        supplier_obj = pool.get('product.supplierinfo')
        categ_obj=pool.get('product.category')
        um_obj=pool.get('product.uom')
        tax_obj=pool.get('account.tax')
        stock_obj = pool.get('stock.move')
        attrib_obj = pool.get('product.attribute')
        attrib_price_obj = pool.get('product.attribute.price')
        attrib_value_obj = pool.get('product.attribute.value')
        attrib_line_obj = pool.get('product.attribute.line')
        pricelist_obj = pool.get('product.pricelist')
        pricelist_item_obj = pool.get('product.pricelist.item')
        pricelist_version_obj = pool.get('product.pricelist.version')
 
        #book = xlwt.Workbook(encoding="utf-8")
        wb= xlrd.open_workbook(filepath)
        
        this = self.browse(cr, uid, ids[0])
        try:
           # now, the serious things: we read the language file
          """leggo l'intestazione"""
          """
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
          """
                                 

          model={}
          col_attr=[]
          mat_attr=[]
          mod_prod=[]
          prod_temp=[]
          for sheet_name in wb.sheet_names(): 
            sheet = wb.sheet_by_name(sheet_name)           

            #attributo colore
            if sheet.row_values(this.row_ini-1)[2]:
                    attrib_ids = attrib_obj.search(cr, uid, [('name','=', sheet.row_values(this.row_ini-1)[2])])    
                    if attrib_ids:
                        attribute_id=attrib_ids[0]
                    else:
                        attribute_id=attrib_obj.create(cr,uid,{'name':sheet.row_values(this.row_ini-1)[2]})
            #attributo materiale
            if sheet.row_values(this.row_ini-1)[3]:
                    mat_attrib_ids = attrib_obj.search(cr, uid, [('name','=', sheet.row_values(this.row_ini-1)[3])])    
                    if mat_attrib_ids:
                        mat_attribute_id=mat_attrib_ids[0]
                    else:
                        mat_attribute_id=attrib_obj.create(cr,uid,{'name':sheet.row_values(this.row_ini-1)[3]})
            #aliquota vendita
            tax_ids = tax_obj.search(cr, uid, [('id','=', this.tax_id.id)])    
            if not tax_ids:
                     raise osv.except_osv(_("imposta  --> " +  this.tax_id.id + " <-- non trovata caricare imposta e riprovare"),_(""))
              # lets create the language with locale information
                     break
            tax_ids_id=tax_ids[0]
            #aliquota acquisti
            tax_ids_acq = tax_obj.search(cr, uid, [('id','=', this.tax_id_acq.id)])    
            if not tax_ids_acq:
                     raise osv.except_osv(_("imposta  --> " +  this.tax_id_acq.id + " <-- non trovata caricare imposta e riprovare"),_(""))
              # lets create the language with locale information
                     break
            """controllo l'unità di misura"""
            um_ids = um_obj.search(cr, uid, [('id','=', this.uom_id.id)])    
            if not um_ids:
                     
                     raise osv.except_osv(_("Unià di misura --> " +  this.uom_id.id + " <-- non trovata caricare l'unita di misura e riprovare"),_(""))
              # lets create the language with locale information
                     break
            um_ids_id=um_ids[0]
            """creo il fornitore"""
            if sheet.row_values(0)[0]:
                partner_ids = partner_obj.search(cr, uid, [('name','=', sheet.row_values(0)[0])])    
                if not partner_ids:
                 # lets create the language with locale information
                         vals={
                         'name':sheet.row_values(0)[0],
                         'customer':False,
                         'supplier':True
    
                           }# skip empty rows and rows where the translation field (=last fiefd) is empty
                         partner_ids_id=partner_obj.create(cr, uid, vals, context=context)
                else:
                         partner_ids_id=partner_ids[0]
                 
            """creo il produttore"""
            if sheet.row_values(1)[0]:
                produttore_ids = partner_obj.search(cr, uid, [('name','=', sheet.row_values(1)[0])])    
                if not produttore_ids:
                 # lets create the language with locale information
                         vals={
                         'name':sheet.row_values(1)[0],
                         'customer':False,
                         'supplier':True
    
    
                           }# skip empty rows and rows where the translation field (=last fiefd) is empty
                         produttore_ids_id=partner_obj.create(cr, uid, vals, context=context)
                else:
                         produttore_ids_id=produttore_ids[0]
    
            """creo la categoria padre """
            if sheet.row_values(1)[0]:
                categ_ids = categ_obj.search(cr, uid, [('name','=', sheet.row_values(1)[0])])    
                if not categ_ids:
                 # lets create the language with locale information
                         vals={
                         'name':sheet.row_values(1)[0],
                         'complete_name':sheet.row_values(1)[0]
                           }# skip empty rows and rows where the translation field (=last fiefd) is empty
                         pad_categ_ids_id=categ_obj.create(cr, uid, vals, context=context)
                else:
                         pad_categ_ids_id=categ_ids[0]
            else:
                         pad_categ_ids_id=None
            """creo la categoria figlia"""
            if sheet.row_values(2)[0]:
                if pad_categ_ids_id:
                    categ_ids = categ_obj.search(cr, uid, [('parent_id','=',pad_categ_ids_id),('name','=', sheet.row_values(2)[0])])    
                else:
                    categ_ids = categ_obj.search(cr, uid, [('name','=', sheet.row_values(2)[0])])    
                if not categ_ids:
                 # lets create the language with locale information
                         vals={
                         'name':sheet.row_values(2)[0],
                         'complete_name':sheet.row_values(2)[0],
                         'parent_id':pad_categ_ids_id
                           }# skip empty rows and rows where the translation field (=last fiefd) is empty
                         categ_ids_id=categ_obj.create(cr, uid, vals, context=context)
                else:
                         categ_ids_id=categ_ids[0]
            seq =  0
            for row in range(this.row_ini,this.rows):
              colore=None  
              if sheet.row_values(row)[2]:
                  try:
                      colore=str(sheet.row_values(row)[2]).encode('UTF-8')
                  except:
                      colore='ERRORE-'+str(row)+'-2'
              
              if sheet.row_values(row)[0]:
                  print 'immagine',sheet.row_values(row)[0]
              if sheet.row_values(row)[1]:
                seq+=10
                #attributo valore
                if colore:
                        attrib_value_ids = attrib_value_obj.search(cr, uid, [('attribute_id','=',attribute_id),('name','=', colore)])    
                        if attrib_value_ids:
                            attrib_value_id=attrib_value_ids[0]
                            col_attr.append(attrib_value_id)
                        else:
                            attrib_value_id=attrib_value_obj.create(cr,uid,{'attribute_id':attribute_id,'name':colore,'sequence':seq,})
                            col_attr.append(attrib_value_id)
                else:
                        attrib_value_id=None
                #attributo materiale
                
                if sheet.row_values(row)[3]:
                        mat_attrib_value_ids = attrib_value_obj.search(cr, uid, [('attribute_id','=',mat_attribute_id),('name','=', sheet.row_values(row)[3])])    
                        if mat_attrib_value_ids:
                            mat_attrib_value_id=mat_attrib_value_ids[0]
                            mat_attr.append(mat_attrib_value_id)
                        else:
                            mat_attrib_value_id=attrib_value_obj.create(cr,uid,{'attribute_id':mat_attribute_id,'name':sheet.row_values(row)[3],'sequence':seq,})
                            mat_attr.append(mat_attrib_value_id)
                else:
                        mat_attrib_value_id=None
                if model.get(sheet.row_values(row)[1]+'_col',None)==None:
                    model[sheet.row_values(row)[1]+'_col']=[]
                if model.get(sheet.row_values(row)[1]+'_mat',None)==None:
                    model[sheet.row_values(row)[1]+'_mat']=[]
                if attrib_value_id not in model.get(sheet.row_values(row)[1]+'_col',None):
                    model[sheet.row_values(row)[1]+'_col'].append(attrib_value_id)
                if mat_attrib_value_id not in model.get(sheet.row_values(row)[1]+'_mat',None):
                    model[sheet.row_values(row)[1]+'_mat'].append(mat_attrib_value_id)
                if  sheet.row_values(row)[5]:
                        prezzo_=sheet.row_values(row)[5]
                        prezzo_PUBBLICO=prezzo_
                else:
                        prezzo_PUBBLICO=0                
                        #prezzo_A=str(prezzo_).replace('€','').replace('.', '').replace(' ', '')
                        #prezzo_B=prezzo_A.replace(',', '')
                        #prezzo=float(str(prezzo_B))/100
                if  sheet.row_values(row)[6]:
                        prezzo_=sheet.row_values(row)[6]
                        prezzo_INGROSSO=prezzo_
                else:
                        prezzo_INGROSSO= 0        
                        #prezzo_A=str(prezzo_).replace('€','').replace('.', '').replace(' ', '')
                        #prezzo_B=prezzo_A.replace(',', '.')
                        #prezzo_1=float(str(prezzo_B))/100
                if  sheet.row_values(row)[4]:
                        prezzo_=sheet.row_values(row)[4]
                        costo=prezzo_
                else:
                        costo=0                
                        #prezzo_A=str(prezzo_).replace('€','').replace('.', '').replace(' ', '')
                        #prezzo_B=prezzo_A.replace(',', '.')
                        #costo=float(str(prezzo_B))/100
                """creo il modello/template"""
                track_yes=True

                prod_tmp_ids = product_tmp_obj.search(cr, uid, [('name','=', sheet.row_values(row)[1])])    
                vals={
                     #'default_code':sheet.row_values(row)[1]+sheet.row_values(row)[3],#marca
                     'name':sheet.row_values(row)[1],#codice
                     'type':'product',
                     'rental':True,
                     'state':'sellable',
                     'list_price':None,
                     'standard_price':None,
                     'categ_id': categ_ids_id,
                     'uom_id':um_ids[0],
                     'uom_po_id':um_ids[0],
                     'manufacturer':produttore_ids_id,
                     'manufacturer_pname':sheet.row_values(row)[1],
                     'manufacturer_pref':None,
                    'loc_rack':None,
                    'track_outgoing':None,
                    'track_incoming':None,
                    'track_production':None,
                    'loc_case':None,
                     'ean13':None,
                     'taxes_id': [(6, 0, [x.id for x in tax_obj.browse(cr,uid,tax_ids,context=context)])],
                     'supplier_taxes_id':[(6, 0, [x.id for x in tax_obj.browse(cr,uid,tax_ids_acq,context=context)])],
                     #'attribute_line_ids':[(6, 0, [x.id for x in attrib_value_obj.browse(cr,uid,attrib_value_id,context=context)])]
                     }# skip empty rows and rows where the translation field (=last fiefd) is empty
                if not prod_tmp_ids:
                # lets create the language with locale information
                    
                   prod_tmp_ids_id=product_tmp_obj.create(cr, uid, vals, context=context)
                   prod_temp.append({prod_tmp_ids_id})
                   prod_ids = product_obj.search(cr, uid, [('name','=', sheet.row_values(row)[1])])    
                   if prod_ids:
                       #product_obj.write(cr,uid,prod_ids[0],{'product_tmpl_id':None})
                       mod_prod.append(prod_ids[0])
                else:
                    prod_tmp_ids_id=prod_tmp_ids[0]
                   #if this.overwrite==True: 
                    #product_tmp_obj.write(cr, uid, prod_tmp_ids_id, vals, context)
                #attributo price
                #cr = pooler.get_db(db_name).cursor()
                #prod_id_obj=product_obj.browse(cr,uid,prod_ids_id,context=context)
                #prod_tmp_ids_id=prod_id_obj.product_tmpl_id.id
                if sheet.row_values(row)[2]:
                    attrib_price_ids = attrib_price_obj.search(cr, uid, [('product_tmpl_id','=',prod_tmp_ids_id),('value_id','=', attrib_value_id)])    
                    if attrib_price_ids:
                        attrib_price_id=attrib_price_ids[0]
                    else:
                        attrib_price_id=attrib_price_obj.create(cr,uid,{'product_tmpl_id':prod_tmp_ids_id,'value_id':attrib_value_id,'price_extra':0})
                #colore al modello
                if sheet.row_values(row)[2]:
                    attrib_value_ids = attrib_value_obj.search(cr, uid, [('attribute_id','=',attribute_id)])    
                    attrib_value_ids_obj=attrib_value_obj.browse(cr,uid,attrib_value_ids,context=context)
                    attrib_line_ids = attrib_line_obj.search(cr, uid, [('product_tmpl_id','=', prod_tmp_ids_id),('attribute_id','=',attribute_id)])    
                    if attrib_line_ids:
                        attrib_line_id=attrib_line_ids[0]
                        attrib_line_obj.write(cr,uid,attrib_line_id,{'value_ids':[(6, 0, model[sheet.row_values(row)[1]+'_col'])]})
                    else:
                        
                        attrib_line_id=attrib_line_obj.create(cr,uid,{'product_tmpl_id':prod_tmp_ids_id,'attribute_id':attribute_id,'value_ids':[(6, 0, model[sheet.row_values(row)[1]+'_col'])]})
                #materiale al modello
                if sheet.row_values(row)[3]:
                    mat_attrib_value_ids = attrib_value_obj.search(cr, uid, [('attribute_id','=',mat_attribute_id)])    
                    mat_attrib_value_ids_obj=attrib_value_obj.browse(cr,uid,mat_attrib_value_ids,context=context)
                    mat_attrib_line_ids = attrib_line_obj.search(cr, uid, [('product_tmpl_id','=', prod_tmp_ids_id),('attribute_id','=',mat_attribute_id)])    
                    if mat_attrib_line_ids:
                        mat_attrib_line_id=mat_attrib_line_ids[0]
                        attrib_line_obj.write(cr,uid,mat_attrib_line_id,{'value_ids':[(6, 0, model[sheet.row_values(row)[1]+'_mat'])]})
                    else:
                        
                        mat_attrib_line_id=attrib_line_obj.create(cr,uid,{'product_tmpl_id':prod_tmp_ids_id,'attribute_id':mat_attribute_id,'value_ids':[(6, 0, model[sheet.row_values(row)[1]+'_mat'])]})

                F_listino=True
                
                if F_listino==True:
                    """INGROSSO"""
                    pricelist_ids_INGROSSO = pricelist_obj.search(cr, uid, [('name','=', 'INGROSSO')])    
                    if not pricelist_ids_INGROSSO:
                 # lets create the language with locale information
                         vals={
                         'name':'INGROSSO',
                         'type':'sale',
                           }# skip empty rows and rows where the translation field (=last fiefd) is empty
                         pricelist_ids_INGROSSO_id=pricelist_obj.create(cr, uid, vals, context=context)
                    else:
                         pricelist_ids_INGROSSO_id=pricelist_ids_INGROSSO[0]
                    
                    """creo versione INGROSSO"""
                    pricelist_version_ids_INGROSSO = pricelist_version_obj.search(cr, uid, [('name','=', 'INGROSSO'+'_versione')])    
                    if not pricelist_version_ids_INGROSSO:
                 # lets create the language with locale information
                         vals={
                         'name':'INGROSSO'+'_versione',
                         'pricelist_id':pricelist_ids_INGROSSO_id,
     
                           }# skip empty rows and rows where the translation field (=last fiefd) is empty
                         pricelist_version_ids_INGROSSO_id=pricelist_version_obj.create(cr, uid, vals, context=context)
                    else:
                         pricelist_version_ids_INGROSSO_id=pricelist_version_ids_INGROSSO[0]
                        
                    """PUBBLICO"""
                    pricelist_ids_PUBBLICO = pricelist_obj.search(cr, uid, [('name','=', 'PUBBLICO')])    
                    if not pricelist_ids_PUBBLICO:
                 # lets create the language with locale information
                         vals={
                         'name':'PUBBLICO',
                         'type':'sale',
     
                           }# skip empty rows and rows where the translation field (=last fiefd) is empty
                         pricelist_ids_PUBBLICO_id=pricelist_obj.create(cr, uid, vals, context=context)
                    else:
                         pricelist_ids_PUBBLICO_id=pricelist_ids_PUBBLICO[0]
                    """creo PUBBLICO"""
                    pricelist_version_ids_PUBBLICO = pricelist_version_obj.search(cr, uid, [('name','=', 'PUBBLICO'+'_versione')])    
                    if not pricelist_version_ids_PUBBLICO:
                 # lets create the language with locale information
                         vals={
                         'name':'PUBBLICO'+'_versione',
                         'pricelist_id':pricelist_ids_PUBBLICO_id,
                           }# skip empty rows and rows where the translation field (=last fiefd) is empty
                         pricelist_version_ids_PUBBLICO_id=pricelist_version_obj.create(cr, uid, vals, context=context)
                    else:
                         pricelist_version_ids_PUBBLICO_id=pricelist_version_ids_PUBBLICO[0]
                         
                    """COSTO"""
                    pricelist_ids_COSTO = pricelist_obj.search(cr, uid, [('name','=', 'COSTO')])    
                    if not pricelist_ids_COSTO:
                 # lets create the language with locale information
                         vals={
                         'name':'COSTO',
                         'type':'purchase',
     
                           }# skip empty rows and rows where the translation field (=last fiefd) is empty
                         pricelist_ids_COSTO_id=pricelist_obj.create(cr, uid, vals, context=context)
                    else:
                         pricelist_ids_COSTO_id=pricelist_ids_COSTO[0]
                    """creo COSTO"""
                    pricelist_version_ids_COSTO = pricelist_version_obj.search(cr, uid, [('name','=', 'COSTO'+'_versione')])    
                    if not pricelist_version_ids_COSTO:
                 # lets create the language with locale information
                         vals={
                         'name':'COSTO'+'_versione',
                         'pricelist_id':pricelist_ids_COSTO_id,
                           }# skip empty rows and rows where the translation field (=last fiefd) is empty
                         pricelist_version_ids_COSTO_id=pricelist_version_obj.create(cr, uid, vals, context=context)
                    else:
                         pricelist_version_ids_COSTO_id=pricelist_version_ids_COSTO[0]
                track_yes=True
                
                """creo la variante"""
                if sheet.row_values(row)[1]:
                    
                    print 'codice','riga',sheet.row_values(row)[1],row
                    prod_ids = product_obj.search(cr, uid, [('default_code','=', sheet.row_values(row)[1]+'_'+colore+'_'+sheet.row_values(row)[3])])    
                    vals={
                     'default_code':sheet.row_values(row)[1]+'_'+colore+'_'+sheet.row_values(row)[3],#marca
                     #'name':sheet.row_values(row)[2]+'_'+sheet.row_values(row)[3],#codice
                     'type':'product',
                     'rental':True,
                     'state':'sellable',
                     #'price':prezzo,
                     'list_price':None,
                     'standard_price':None,
                     'categ_id': categ_ids_id,
                     'uom_id':um_ids[0],
                     'uom_po_id':um_ids[0],
                     'manufacturer':produttore_ids_id,
                     'manufacturer_pname':sheet.row_values(row)[1],
                     'manufacturer_pref':None,
                    'loc_rack':None,
                    'track_outgoing':track_yes,
                    'track_incoming':track_yes,
                    'track_production':track_yes,
                    'loc_case':None,
                     'ean13':None,
                     'taxes_id': [(6, 0, [x.id for x in tax_obj.browse(cr,uid,tax_ids,context=context)])],
                     'supplier_taxes_id':[(6, 0, [x.id for x in tax_obj.browse(cr,uid,tax_ids_acq,context=context)])],
                     'product_tmpl_id':prod_tmp_ids_id,
                     #'attribute_value_ids':[(6, 0, [x.id for x in attrib_value_ids_obj]),(6, 0, [x.id for x in mat_attrib_value_ids_obj])]
                      'attribute_value_ids':[(6,0,[attrib_value_id,mat_attrib_value_id])]
                     }# skip empty rows and rows where the translation field (=last fiefd) is empty
                    if not prod_ids:
                # lets create the language with locale information
                    
                        print 'default_code',vals['default_code'],vals['list_price']
                        
                        prod_ids_id=product_obj.create(cr, uid, vals, context=context)
           
                    else:
                        prod_ids_id=prod_ids[0]
                        if this.overwrite==True: 
                            product_obj.write(cr, uid, prod_ids_id, vals, context)
                       
                #prod_ids_rec=product_obj.browse(cr, uid,prod_ids_id,context)
                """cre attributo"""
                   

                """creo catena di approvvigionamento"""
                """
                supplier_ids = supplier_obj.search(cr, uid, [('product_code','=', row[0])])    
                vals={
                     'name':partner_ids_id,#codice
                     'product_name':row[1],#qta_gicanza
                     'product_code':row[0],#marca
                     'product_uom':um_ids[0],#codice prodotto fornitore
                     'min_qty':1,
                     'product_id':prod_ids_id,
                     
                     }# skip empty rows and rows where the translation field (=last fiefd) is empty
                if not supplier_ids:
                # lets create the language with locale information
 
                   supplier_obj.create(cr, uid, vals, context=context)
                else:
                    if this.overwrite==True: 
                       supplier_obj.write(cr, uid, supplier_ids[0], vals, context)                        
                """
                if F_listino==True:
    
                    """creo voci di listino personalizzato pubblico"""       
                    pricelist_item_ids = pricelist_item_obj.search(cr, uid, [('name','=', sheet.row_values(row)[1]+'_'+colore+'_'+sheet.row_values(row)[3]),('price_version_id','=',pricelist_version_ids_PUBBLICO_id)])    
                    vals={
                         'name':sheet.row_values(row)[1]+'_'+colore+'_'+sheet.row_values(row)[3],#marca
                         'product_id':prod_ids_id,#codice
                         'price_surcharge':prezzo_PUBBLICO,
                         'price_discount':0,
                         'price_version_id':pricelist_version_ids_PUBBLICO_id,
                         'base':1
                          }# skip empty rows and rows where the translation field (=last fiefd) is empty
                    if prezzo_PUBBLICO!=0:
                        if not pricelist_item_ids:
                        # lets create the language with locale information     
                           pricelist_item_ids_id=pricelist_item_obj.create(cr, uid, vals, context=context)
                   
                        else:
                            pricelist_item_ids_id=pricelist_item_ids[0]
                            if this.overwrite==True: 
                               pricelist_item_obj.write(cr, uid, pricelist_item_ids_id, vals, context) 
                        
                    """creo voci di listino INGROSSO"""       
                    pricelist_item_ids = pricelist_item_obj.search(cr, uid, [('name','=', sheet.row_values(row)[1]+'_'+colore+'_'+sheet.row_values(row)[3]),('price_version_id','=',pricelist_version_ids_INGROSSO_id)])    
                    vals={
                         'name':sheet.row_values(row)[1]+'_'+colore+'_'+sheet.row_values(row)[3],#marca
                         'product_id':prod_ids_id,#codice
                         'price_surcharge':prezzo_INGROSSO,                     
                         'price_discount':0,
                         'price_version_id':pricelist_version_ids_INGROSSO_id,
                          'base':1
                          }# skip empty rows and rows where the translation field (=last fiefd) is empty
                    if prezzo_INGROSSO!=0:
                        if not pricelist_item_ids:
                        # lets create the language with locale information     
                           pricelist_item_ids_id=pricelist_item_obj.create(cr, uid, vals, context=context)
                   
                        else:
                            pricelist_item_ids_id=pricelist_item_ids[0]
                            if this.overwrite==True: 
                               pricelist_item_obj.write(cr, uid, pricelist_item_ids_id, vals, context)  
    
                    """creo voci di listino personalizzato COSTO"""       
                    pricelist_item_ids = pricelist_item_obj.search(cr, uid, [('name','=', sheet.row_values(row)[1]+'_'+colore+'_'+sheet.row_values(row)[3]),('price_version_id','=',pricelist_version_ids_COSTO_id)])    
                    vals={
                         'name':sheet.row_values(row)[1]+'_'+colore+'_'+sheet.row_values(row)[3],#marca
                         'product_id':prod_ids_id,#codice
                         'price_surcharge':costo,                   
                         'price_discount':0,
                         'price_version_id':pricelist_version_ids_COSTO_id,
                          'base':2
                          }# skip empty rows and rows where the translation field (=last fiefd) is empty
                    if costo!=0:
                        if not pricelist_item_ids:
                        # lets create the language with locale information     
                           pricelist_item_ids_id=pricelist_item_obj.create(cr, uid, vals, context=context)
                   
                        else:
                            pricelist_item_ids_id=pricelist_item_ids[0]
                            if this.overwrite==True: 
                               pricelist_item_obj.write(cr, uid, pricelist_item_ids_id, vals, context)  
                
          if mod_prod:
              product_obj.unlink(cr, uid, mod_prod, context)
      #_logger.info("importazione effettuata con successo")
        except IOError:
            filename = '[lang: %s][format: %s]' % (iso_lang or 'new', fileformat)
            raise osv.except_osv(_("Impossibile leggere ilfile %s"), _(filename))
class res_company(osv.osv):
    _inherit = 'res.company'
    _columns = {
        'x_pubblico_id': fields.many2one('product.pricelist', 'Pubblico', required=False),
        'x_ingrosso_id': fields.many2one('product.pricelist', 'Ingrosso', required=False),
        'x_costo_id': fields.many2one('product.pricelist', 'Costo', required=False),
                    }
res_company()
        
class product_categlist(orm.TransientModel):
    _name = 'product.categlist.prof_webtex'
    _description = 'Estrazione Prodotti per categoria'

    _columns = {
        'da_prodotto': fields.many2one('product.product', 'da prodotto', required=False),
        'a_prodotto': fields.many2one('product.product', 'a prodotto', required=False),
        'da_categoria': fields.many2one('product.category', 'da categoria', required=False),
        'a_categoria': fields.many2one('product.category', 'a categoria', required=False),
        'dispo':fields.boolean('Disponibilità', required=False), 
        'x_rio_stock':fields.boolean('riordino', required=False), 
        'data': fields.binary('File', required=False, readonly=True),
        'file_data':fields.char('nome file', readonly=True), 
        'state': fields.selection([('choose', 'choose'),   # choose language
                                       ('get', 'get')]),        # get the file
    }
    _defaults = {
        'state': 'choose'
     }
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        return orm.TransientModel.fields_view_get(self, cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
    def ri_export_productcateg(self, cr, uid, ids, context=None):
                if hasattr(ids, '__iter__'):
                    ids=ids
                else:
                    ids=[ids]
        
                model_data_obj = self.pool.get('ir.model.data')
                view_rec = model_data_obj.get_object_reference(
                    cr, uid, 'prof_webtex', 'view_product_product_categ_list_prof_webtex')
                view_id = view_rec and view_rec[1] or False
                this=self.browse(cr, uid, ids[0], context=context)

                new_id=self.create(cr,uid,{
                    'da_prodotto':None,
                    'a_prodotto':None,
                    'da_categoria':None,
                    'a_categoria':None,

                    })
                return {
                    'view_type': 'form',
                    'view_id': [view_id],
                    'view_mode': 'form',
                    'res_model': 'product.categlist.prof_webtex',
                    'res_id': new_id,
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'context': context,
                }
    def export_productcateg(self, cr, uid, ids, context=None):

                    
                if hasattr(ids, '__iter__'):
                    ids=ids
                else:
                    ids=[ids]
                product_obj=self.pool.get('product.product')
                this=self.browse(cr, uid, ids[0], context=context)
                if context is None:
                    context = {'ok':True}
                if context:
                    da_prodotto=None
                    a_prodotto=None
                    da_categoria=None
                    a_categoria=None
                    argo=[]
                    categ_da=[]
                    if this.da_prodotto:
                        da_prodotto=('id','>=',this.da_prodotto.id)
                        argo.append(da_prodotto)
                    if this.a_prodotto:
                        a_prodotto=('id','<=',this.a_prodotto.id)
                        argo.append(a_prodotto)
                    if this.da_categoria:
                        #da_categoria=('categ_id','>=',this.da_categoria.id)
                        categ_da.append(this.da_categoria.id)
                        loop_categ=this.da_categoria
                        while loop_categ.parent_id:
                            categ_da.append(loop_categ.parent_id.id)
                            loop_categ=loop_categ.parent_id
                            
                    if this.a_categoria:
                        #a_categoria=('categ_id','<=',this.a_categoria.id)
                        categ_da.append(this.a_categoria.id)
                        aloop_categ=this.a_categoria
                        while aloop_categ.parent_id:
                            categ_da.append(aloop_categ.parent_id.id)
                            aloop_categ=aloop_categ.parent_id
                    if categ_da:
                        argo.append(('categ_id','in',categ_da))
                    prod_ids=product_obj.search(cr,uid,argo,order='categ_id,id',context=context)
                    
                handle, filepath = tempfile.mkstemp()
                filename = filepath
                excel_file = xlwt.Workbook()
                sheet = excel_file.add_sheet('articoli')
                row = 0
                col = 0
                ctype = 'string'
                value = 'Rocky1'
                xf = 0
                sheet.write(row, 0, 'id')
                sheet.write(row, 1, 'codice')
                sheet.write(row, 2, 'categoria padre')
                sheet.write(row, 3, 'categoria')
                sheet.write(row, 4, 'nome')
                sheet.write(row, 5, 'attributo')
                sheet.write(row, 6, 'nome fornitore')
                sheet.write(row, 7, 'esistenza')
                sheet.write(row, 8, 'prezzo_extra')
                sheet.write(row, 9, 'prezzo')
                sheet.write(row, 10, 'prezzo netto')
                sheet.write(row, 11, 'costo')
                virtual_available=0
                lst_price=0
                x_price_subtax=0
                standard_price=0
                categoria_old=0
                if prod_ids:
                            product_id_obj=product_obj.browse(cr,uid,prod_ids[0],context=context)
                            categoria_old=product_id_obj.categ_id
                            virtual_available=product_id_obj.virtual_available
                            lst_price=product_id_obj.virtual_available*product_id_obj.lst_price
                            x_price_subtax=product_id_obj.virtual_available*product_id_obj.x_price_subtax
                            standard_price=product_id_obj.virtual_available*product_id_obj.standard_price
                    
                for product_id_obj in product_obj.browse(cr,uid,prod_ids,context=context):
                        row+=1
                        padre=''
                        if product_id_obj.categ_id:
                            
                            if product_id_obj.categ_id.parent_id:
                                padre=product_id_obj.categ_id.parent_id.name
                                if  product_id_obj.categ_id.parent_id.parent_id:
                                   padre+='/'+product_id_obj.categ_id.parent_id.parent_id.name
                        sheet.write(row, 0, product_id_obj.id)
                        sheet.write(row, 1, product_id_obj.default_code)
                        sheet.write(row, 2, padre)
                        sheet.write(row, 3, product_id_obj.categ_id.name)
                        sheet.write(row, 4, product_id_obj.name)
                        variant = ", ".join([v.name for v in product_id_obj.attribute_value_ids ])
                        sheet.write(row, 5,variant)
                        sheet.write(row, 6,product_id_obj.description_purchase)
                        sheet.write(row, 7, product_id_obj.virtual_available)
                        sheet.write(row, 8, product_id_obj.price_extra)
                        sheet.write(row, 9, product_id_obj.lst_price)
                        sheet.write(row, 10, product_id_obj.x_price_subtax)
                        sheet.write(row, 11, product_id_obj.standard_price)
                        if categoria_old==product_id_obj.categ_id:
                            virtual_available+=product_id_obj.virtual_available
                            lst_price+=product_id_obj.virtual_available*product_id_obj.lst_price
                            x_price_subtax+=product_id_obj.virtual_available*product_id_obj.x_price_subtax
                            standard_price+=product_id_obj.virtual_available*product_id_obj.standard_price
                        else:
                            row+=1
                            if categoria_old.parent_id:
                                padre=categoria_old.parent_id.name
                                if  categoria_old.parent_id.parent_id:
                                   if product_id_obj.categ_id.parent_id.parent_id.name:
                                       padre+='/'+product_id_obj.categ_id.parent_id.parent_id.name
                            sheet.write(row, 2, padre)
                            sheet.write(row, 3, categoria_old.name)
                            sheet.write(row, 7, virtual_available)
                            sheet.write(row, 9, lst_price)
                            sheet.write(row, 10, x_price_subtax)
                            sheet.write(row, 11, standard_price)
                            categoria_old=product_id_obj.categ_id
                            virtual_available=product_id_obj.virtual_available
                            lst_price=product_id_obj.virtual_available*product_id_obj.lst_price
                            x_price_subtax=product_id_obj.virtual_available*product_id_obj.x_price_subtax
                            standard_price=product_id_obj.virtual_available*product_id_obj.standard_price
                            
                row+=1
                if categoria_old.parent_id:
                                padre=categoria_old.parent_id.name
                                if  categoria_old.parent_id.parent_id:
                                   padre+='/'+product_id_obj.categ_id.parent_id.parent_id.name
                sheet.write(row, 2, padre)
                sheet.write(row, 3, categoria_old.name)
                sheet.write(row, 7, virtual_available)
                sheet.write(row, 9, lst_price)
                sheet.write(row, 10, x_price_subtax)
                sheet.write(row, 11, standard_price)
                            
                excel_file.save(filename)
                excel_file.get_active_sheet()
                fileobj = os.fdopen(handle,'r')
                buffer=fileobj.read()
                out=base64.encodestring(buffer)
                fileobj.close
                
                #print 'out_ex',out
                self.write(cr,uid,ids[0],{'data':out,
                                          'file_data':'export_productcat.xls','state':'get',
                                          })
                
                model_data_obj = self.pool.get('ir.model.data')
                view_rec = model_data_obj.get_object_reference(
                    cr, uid, 'prof_webtex', 'view_product_product_categ_list_prof_webtex')
                view_id = view_rec and view_rec[1] or False
        
                return {
                    'view_type': 'form',
                    'view_id': [view_id],
                    'view_mode': 'form',
                    'res_model': 'product.categlist.prof_webtex',
                    'res_id': ids[0],
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'context': context,
                }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
           
product_categlist()    
class stock_history_tre(osv.osv):
    _name = 'stock.history.tre'
    _order = 'anno asc,mese asc'

    _columns = {
        'location_id': fields.many2one('stock.location', 'Locazione', required=True),
        'company_id': fields.many2one('res.company', 'Azienda'),
        'product_id': fields.many2one('product.product', 'Prodotto', required=True),
        'product_categ_id': fields.many2one('product.category', 'Categoria', required=True),
        'quantity': fields.float('Progressivo  qta'),
        'anno': fields.integer('anno',index=True),
        'mese': fields.selection([(1,'gennaio'),
                                  (2,'febbraio'),
                                  (3,'marzo'),
                                  (4,'aprile'),
                                  (5,'maggio'),
                                  (6,'giugno'),
                                  (7,'luglio'),
                                  (8,'agosto'),
                                  (9,'settembre'),
                                  (10,'ottobre'),
                                  (11,'novembre'),
                                  (12,'dicembre'),
                                  ],'mese',index=True),
        'price_unit_on_quant': fields.float('Value', group_operator='avg'),
        'inventory_value': fields.float(string="Valore inventario progressivo"),
        'blocco_agg':fields.boolean(string="Blocco aggiornamento")
    }

class stock_history(osv.osv):
    _name='stock.history.due' 
    _order = 'product_categ_id,product_id,location_id,anno asc,mese asc'
    _auto = False
    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
        res = super(stock_history, self).read_group(cr, uid, domain, fields, groupby, offset=offset, limit=limit, context=context, orderby=orderby, lazy=lazy)
        if context is None:
            context = {}
        date = context.get('history_date', datetime.now())
        
        #date_inizio = context.get('history_date_inizio', datetime.now()- timedelta(365))
        #date=datetime.strptime(str(date),"%Y-%m-%d %H:%M:%S.%f").strftime("%Y-%m-%d")
        #date_inizio=datetime.strptime(str(date_inizio),"%Y-%m-%d %H:%M:%S.%f").strftime("%Y-%m-%d")

        if 'inventory_value' in fields:
            group_lines = {}
            for line in res:
                domain = line.get('__domain', domain)
                group_lines.setdefault(str(domain), self.search(cr, uid, domain, context=context))
            line_ids = set()
            for ids in group_lines.values():
                for product_id in ids:
                    line_ids.add(product_id)
            line_ids = list(line_ids)
            lines_rec = {}
            if line_ids:
                cr.execute('SELECT id, product_id, price_unit_on_quant, company_id, quantity FROM stock_history_due WHERE id in %s', (tuple(line_ids),))
                lines_rec = cr.dictfetchall()
            lines_dict = dict((line['id'], line) for line in lines_rec)
            product_ids = list(set(line_rec['product_id'] for line_rec in lines_rec))
            products_rec = self.pool['product.product'].read(cr, uid, product_ids, ['cost_method', 'product_tmpl_id'], context=context)
            products_dict = dict((product['id'], product) for product in products_rec)
            cost_method_product_tmpl_ids = list(set(product['product_tmpl_id'][0] for product in products_rec if product['cost_method'] != 'real'))
            histories = []
            if cost_method_product_tmpl_ids:
                cr.execute('SELECT DISTINCT ON (product_template_id, company_id) product_template_id, company_id, cost FROM product_price_history WHERE product_template_id in %s AND datetime <= %s ORDER BY product_template_id, company_id, datetime DESC', (tuple(cost_method_product_tmpl_ids), date))
                histories = cr.dictfetchall()
            histories_dict = {}
            for history in histories:
                histories_dict[(history['product_template_id'], history['company_id'])] = history['cost']
            for line in res:
                inv_value = 0.0
                lines = group_lines.get(str(line.get('__domain', domain)))
                for line_id in lines:
                    line_rec = lines_dict[line_id]
                    product = products_dict[line_rec['product_id']]
                    if product['cost_method'] == 'real':
                        price = line_rec['price_unit_on_quant']
                    else:
                        price = histories_dict.get((product['product_tmpl_id'][0], line_rec['company_id']), 0.0)
                    inv_value += price * line_rec['quantity']
                line['inventory_value'] = inv_value
        return res

    def _get_inventory_value(self, cr, uid, ids, name, attr, context=None):
        if context is None:
            context = {}
        date = context.get('history_date')
        date_inizio = context.get('history_date_inizio', datetime.now()- timedelta(2190))
        product_tmpl_obj = self.pool.get("product.template")
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            if line.product_id.cost_method == 'real':
                res[line.id] = line.quantity * line.price_unit_on_quant
            else:
                res[line.id] = line.quantity * product_tmpl_obj.get_history_price(cr, uid, line.product_id.product_tmpl_id.id, line.company_id.id, date=date, context=context)
        return res

    _columns = {
        'location_id': fields.many2one('stock.location', 'Locazione', required=True),
        'company_id': fields.many2one('res.company', 'Azienda'),
        'product_id': fields.many2one('product.product', 'Prodotto', required=True),
        'product_categ_id': fields.many2one('product.category', 'Categoria prodotto', required=True),
        'quantity': fields.float('quantità'),
        'anno': fields.char('anno',index=True),
        'mese': fields.char('mese',index=True),
        'price_unit_on_quant': fields.float('Value', group_operator='avg'),
        'inventory_value': fields.function(_get_inventory_value, string=" Valore inventario ", type='float', readonly=True),
    }

    def init(self, cr):
        date=datetime.today()
        date_inizio =datetime.today()- timedelta(2190)
        date=datetime.strptime(str(date),"%Y-%m-%d %H:%M:%S.%f").strftime("%Y-%m-%d")
        date_inizio_mese=datetime.strptime(str(datetime.today()),"%Y-%m-%d %H:%M:%S.%f").strftime("%Y-%m-01")
        date_inizio=datetime.strptime(str(date_inizio),"%Y-%m-%d %H:%M:%S.%f").strftime("%Y-%m-%d")
        anno_inizio=datetime.strptime(str(date_inizio),"%Y-%m-%d").strftime("%Y-%m-%d")[0:4]
        tools.drop_view_if_exists(cr, 'stock_history_due')
        cr.execute("""
                CREATE OR REPLACE VIEW stock_history_due AS (
                  SELECT MIN(id) as id,
                    location_id,
                    company_id,
                    product_id,
                    product_categ_id,
                    SUM(quantity) as quantity,
                    anno,
                    mese,
                    COALESCE(SUM(price_unit_on_quant * quantity) / NULLIF(SUM(quantity), 0), 0) as price_unit_on_quant
                    FROM
                    ((SELECT
                        stock_move.id AS id,
                        dest_location.id AS location_id,
                        dest_location.company_id AS company_id,
                        stock_move.product_id AS product_id,
                        product_template.categ_id AS product_categ_id,
                        quant.qty AS quantity,
                        SUBSTRING (cast (stock_move.date as character varying),0 ,5) AS anno,
                        SUBSTRING (cast (stock_move.date as character varying),6 ,2) AS mese,
                        quant.cost as price_unit_on_quant
                    FROM
                        stock_move
                    JOIN
                        stock_quant_move_rel on stock_quant_move_rel.move_id = stock_move.id
                    JOIN
                        stock_quant as quant on stock_quant_move_rel.quant_id = quant.id
                    JOIN
                       stock_location dest_location ON stock_move.location_dest_id = dest_location.id
                    JOIN
                        stock_location source_location ON stock_move.location_id = source_location.id
                    JOIN
                        product_product ON product_product.id = stock_move.product_id
                    JOIN
                        product_template ON product_template.id = product_product.product_tmpl_id
                    WHERE 
                     quant.qty>0 AND stock_move.state = 'done' AND dest_location.usage in ('internal', 'transit')
                      AND (
                        not (source_location.company_id is null and dest_location.company_id is null) or
                        source_location.company_id != dest_location.company_id or
                        source_location.usage not in ('internal', 'transit'))
                    ) UNION ALL
                    (SELECT
                        (-1) * stock_move.id AS id,
                        source_location.id AS location_id,
                        source_location.company_id AS company_id,
                        stock_move.product_id AS product_id,
                        product_template.categ_id AS product_categ_id,
                        - quant.qty AS quantity,
                        SUBSTRING (cast (stock_move.date as character varying),0 ,5) AS anno,
                        SUBSTRING (cast (stock_move.date as character varying),6 ,2) AS mese,
                        quant.cost as price_unit_on_quant
                    FROM
                        stock_move
                    JOIN
                        stock_quant_move_rel on stock_quant_move_rel.move_id = stock_move.id
                    JOIN
                        stock_quant as quant on stock_quant_move_rel.quant_id = quant.id
                    JOIN
                        stock_location source_location ON stock_move.location_id = source_location.id
                    JOIN
                        stock_location dest_location ON stock_move.location_dest_id = dest_location.id
                    JOIN
                        product_product ON product_product.id = stock_move.product_id
                    JOIN
                        product_template ON product_template.id = product_product.product_tmpl_id
                    WHERE   
                     quant.qty>0 
                    AND stock_move.state = 'done' AND source_location.usage in ('internal', 'transit')
                     AND (
                        not (dest_location.company_id is null and source_location.company_id is null) or
                        dest_location.company_id != source_location.company_id or
                        dest_location.usage not in ('internal', 'transit'))
                    )) 
                    AS foo
                    GROUP BY  product_categ_id,product_id, location_id,  anno,mese ,company_id 
                )""" ) 
            
class wizard_valuation_history(osv.osv):

    _name = 'wizard.valuation.history.log'
    _description = 'Wizard that opens the stock valuation history table'
    _columns = {
        'data': fields.binary('File', required=False, readonly=True),
        'file_data':fields.char('nome file', readonly=True), 
        'data_csv': fields.binary('File', required=False, readonly=True),
        'file_data_csv':fields.char('nome file', readonly=True), 
        'date': fields.datetime('Data Valutazione', required=True),
    }

    _defaults = {
        'date': datetime.today(),
    }
    _order = 'date desc,id desc' 
    def open_table_last_mounth(self, cr, uid, ids=[],last_dates=[], context=None):
        def unicode2encoding(text, encoding='utf-8'):
            if isinstance(text, unicode):
                try:
                    text = text.encode(encoding)
                except Exception:
                    pass
            return text
        
        def encode(text, encoding='utf-8'):
            if isinstance(text, (str, unicode)):
                return unicode2encoding(text, encoding=encoding)
            return str(text)
        def try_coerce_ascii(string_utf8):
                    """Attempts to decode the given utf8-encoded string
                       as ASCII after coercing it to UTF-8, then return
                       the confirmed 7-bit ASCII string.
                
                       If the process fails (because the string
                       contains non-ASCII characters) returns ``None``.
                    """
                    try:
                        if isinstance(string_utf8, str):                   
                             return string_utf8
                             string_utf8.encode('utf8')
                        elif isinstance(string_utf8, unicode):
                             if u'\xbd' in string_utf8 or u'\u20ac' in string_utf8 or u'\xe8' in string_utf8 or u'\xe0' in string_utf8 or u'\xf9' in string_utf8 or u'\u251c' in string_utf8  or u'\u0102' in string_utf8:
                                
                                string_utf8='Caratteri_con_codifica_errata'
                                string_utf8.encode('utf8')
                             else:    
                                string_utf8.encode('utf8')
        
                        else:
                             string_utf8='-'
                             string_utf8.encode('utf8')
                    except:
                        return '-'.encode('utf8')
                    return string_utf8
        if context is None:
            context = {}
        product_obj=self.pool.get('product.product')
        location_obj=self.pool.get('stock.location')
        history_obj_tre=self.pool.get('stock.history.tre')
        anno=datetime.now().year
        mese=int(datetime.today().strftime('%m'))
        product_ids=product_obj.search(cr,uid,[('active','=',True)],order='categ_id,id',context=context)
        loc_ids=location_obj.search(cr,uid,[('usage','=','internal')])
        #last_dates=[datetime.today().strftime('%Y-%m-01'),(datetime.today()- timedelta(30)).strftime('%Y-%m-01')]
        #last_dates=[datetime.today().strftime('%Y-%m-%d'),'2020-02-29','2020-03-31','2020-04-30','2020-04-30',]
        last_dates.append(datetime.today().strftime('%Y-%m-%d'))
        #last_dates=['2020-06-30',]
        _logger.info("last_mounth  last_dates %s ", last_dates)
        for last_date in last_dates:
            anno=int(datetime.strptime(last_date,'%Y-%m-%d').strftime('%Y'))            
            mese=int(datetime.strptime(last_date,'%Y-%m-%d').strftime('%m'))            
            context['to_date']=last_date
            product_id_obj=product_obj.browse(cr,uid,product_ids[0],context=context)
            rt_product_categ_id=product_id_obj.categ_id.id
            for product_id in product_ids:
                        for loc_id in loc_ids:
                            context['location']=loc_id
                            product_id_obj=product_obj.browse(cr,uid,product_id,context=context)
                            virtual_available=product_id_obj.virtual_available
                            lst_price=product_id_obj.virtual_available*product_id_obj.lst_price
                            #x_price_subtax=product_id_obj.virtual_available*product_id_obj.x_price_subtax
                            standard_price=product_id_obj.virtual_available*product_id_obj.standard_price
                            
                            tre_ids=history_obj_tre.search(cr,uid,[('product_id','=',product_id_obj.id),
                                                                        ('anno','=',anno),
                                                                        ('mese','=',mese),
                                                                        ('location_id','=',loc_id)],
                                                                                   context=context)
                            vals={
                                                'location_id': loc_id,
                                                'company_id': product_id_obj.company_id.id,
                                                'product_id': product_id_obj.id,
                                                'product_categ_id': product_id_obj.categ_id.id,
                                                'anno': anno,
                                                'mese': mese,
                                                'price_unit_on_quant': product_id_obj.standard_price,
                                                'blocco_agg':True,
                                                'quantity': virtual_available,
                                                'inventory_value': standard_price
                                                                 }
                            if tre_ids:
                                                history_obj_tre.write(cr,uid,tre_ids[0],vals,context=context)
                            else:
                                                
                                                history_obj_tre.create(cr,uid,vals,context=context)
                            _logger.info("last_mounth categ %s id %s:  nome %s disp. %s", product_id_obj.categ_id.name,product_id_obj.id, product_id_obj.name,virtual_available)
                        if rt_product_categ_id!=product_id_obj.categ_id.id:
                                try:
                                        cr.commit()
                                        _logger.info("last_mounth_categoria %s: rottura %s", rt_product_categ_id, 'rottura')
                                except:
                                        cr.rollback()
                                        _logger.info("last_mounth_errore_categoria %s: rottura %s", rt_product_categ_id, 'rottura')
                                rt_product_categ_id=product_id_obj.categ_id.id
            try:
                                cr.commit()
            except:
                                cr.rollback()
                                _logger.info("last_mounth Errore data %s: rottura %s", last_date, '-')
            _logger.info("last_mounth fine dates %s: rottura %s", last_dates, '-')
        history_id=self.create(cr,uid,{'data':None,
                                       'file_data':'export_valutazione.xls',
                                        'data_csv':None,
                                        'file_data_csv':'export_valutazione.csv',
                                       
                                       'date':last_dates[0]},context=context)
        _logger.info("last_mounth fine blocco_agg %s: rottura %s", '-', '-')
        return  history_id 
                            
        
    def open_table(self, cr, uid, ids=[],date=None, context=None):
        def unicode2encoding(text, encoding='utf-8'):
            if isinstance(text, unicode):
                try:
                    text = text.encode(encoding)
                except Exception:
                    pass
            return text
        
        def encode(text, encoding='utf-8'):
            if isinstance(text, (str, unicode)):
                return unicode2encoding(text, encoding=encoding)
            return str(text)
        def try_coerce_ascii(string_utf8):
                    """Attempts to decode the given utf8-encoded string
                       as ASCII after coercing it to UTF-8, then return
                       the confirmed 7-bit ASCII string.
                
                       If the process fails (because the string
                       contains non-ASCII characters) returns ``None``.
                    """
                    try:
                        if isinstance(string_utf8, str):                   
                             return string_utf8
                             string_utf8.encode('utf8')
                        elif isinstance(string_utf8, unicode):
                             if u'\xbd' in string_utf8 or u'\u20ac' in string_utf8 or u'\xe8' in string_utf8 or u'\xe0' in string_utf8 or u'\xf9' in string_utf8 or u'\u251c' in string_utf8  or u'\u0102' in string_utf8:
                                
                                string_utf8='Caratteri_con_codifica_errata'
                                string_utf8.encode('utf8')
                             else:    
                                string_utf8.encode('utf8')
        
                        else:
                             string_utf8='-'
                             string_utf8.encode('utf8')
                    except:
                        return '-'.encode('utf8')
                    return string_utf8
        annoprec=datetime.now().year - 10
        if date is None:
            
            date=datetime.today().strftime('%Y-%m-%d')
            date_inizio=(datetime.today()- timedelta(2190)).strftime('%Y-%m-%d')
            print 'date',date
        if context is None:
            context = {}
        ctx = context.copy()
        ctx['history_date'] = date
        ctx['history_date_inizio'] = date_inizio
        ctx['search_default_group_by_product'] = True
        ctx['search_default_group_by_location'] = True
        product_obj=self.pool.get('product.product')
        history_obj_tre=self.pool.get('stock.history.tre')
        history_obj=self.pool.get('stock.history.due')
        history_obj.init(cr)
        handle, filepath = tempfile.mkstemp()
        filename = filepath
        excel_file = xlwt.Workbook()
        sheet = excel_file.add_sheet('Valutazione magazzino')
        product_obj=self.pool.get('product.product')
        row = 0
        ctype = 'string'
        value = 'Rocky1'
        xf = 0
        sheet.write(row, 0, 'location_id')
        sheet.write(row, 1, 'company_id')
        sheet.write(row, 2, 'categoria padre')
        sheet.write(row, 3, 'categoria')
        sheet.write(row, 4, 'codice')
        sheet.write(row, 5, 'descrizione')
        sheet.write(row, 6, 'Attributo')
        sheet.write(row, 7, 'quantity')
        sheet.write(row, 8, 'anno')
        sheet.write(row, 9, 'mese')
        sheet.write(row, 10, 'price_unit_on_quant')
        sheet.write(row, 11, 'inventory_value')


        """---"""
        buffer_csv = cStringIO.StringIO()
        writer = csv.writer(buffer_csv, 'UNIX')

        writer.writerow((
            'location_id',
            'company_id',
            'categoria padre',
            'categoria',
            'codice',
            'descrizione',
            'Attributo',
            'quantity',
            'anno',
            'mese',
            'price_unit_on_quant',
            'inventory_value'
))

        
        """---"""
        product_list=[]
        rottura=''
        totquantity=0
        totinventory_value=0
        rt_product_categ_id=''
        #hist_ids=history_obj.search(cr,uid,[('product_categ_id','in',[18,20,21]),('product_id','in',[5360,5362,36427,36291,4964,4965]),('anno','>=',str(annoprec)),],order='product_categ_id asc,product_id,location_id,anno asc,mese asc,id',context=context)
        #hist_ids=history_obj.search(cr,uid,[('product_categ_id','>=',153),('anno','>=',str(annoprec))],order='product_categ_id asc,product_id asc,location_id,anno asc,mese asc,id',context=context)
        cr.execute("SELECT product_categ_id \
                            FROM stock_history_tre \
                            WHERE product_categ_id NOT IN %s \
                            GROUP BY product_categ_id;", (tuple([1999,]),))
        product_categ_ids=[]
        for product_categ_id in cr.fetchall():#len(whole_ven_qty_A[0])
                        if product_categ_id!= (None,):#L(whole_ven_qty_A)[0])
                            product_categ_ids.append(product_categ_id[0])

        hist_ids=history_obj.search(cr,uid,[('anno','>=',str(annoprec)),('product_categ_id','not in',product_categ_ids)],order='product_categ_id asc,product_id asc,location_id,anno asc,mese asc,id',context=context)
        _logger.info("lunghezza %s:", len(hist_ids))
        if hist_ids:
            history_id0_obj=history_obj.browse(cr,uid,hist_ids[0],context=context)
            campirottura={
                                                'location_id': history_id0_obj.location_id.id,
                                                'company_id': history_id0_obj.company_id.id,
                                                'product_id': history_id0_obj.product_id.id,
                                                'product_categ_id': history_id0_obj.product_categ_id.id,
                                                'anno': int(history_id0_obj.anno),
                                                'mese': int(history_id0_obj.mese),
                                                'price_unit_on_quant': history_id0_obj.price_unit_on_quant,
                                                }
            rottura=str(history_id0_obj.product_categ_id.id)+str(history_id0_obj.product_id.id)+str(history_id0_obj.location_id.id)+str(history_id0_obj.anno)+str(history_id0_obj.mese)
            totquantity=0
            totinventory_value=0
            rt_product_categ_id=history_id0_obj.product_categ_id.id
        for history_id_obj in history_obj.browse(cr,uid,hist_ids,context=context):
                        product_id=history_id_obj.product_id.id
                        _logger.info("product_id %s %s %s %s %s %s %s:", history_id_obj.product_id.id,history_id_obj.product_id.name, history_id_obj.product_categ_id.id,history_id_obj.product_categ_id.name,history_id_obj.anno,history_id_obj.mese,history_id_obj.location_id.id)
                        """
                        if product_id not in product_list:
                            tre_ids=history_obj_tre.search(cr,uid,[('product_id','=',product_id),('blocco_agg','=',False)],order='anno,mese',context=context)
                            for tre_id in tre_ids:
                                history_obj_tre.unlink(cr,uid,tre_id,context=context)
                            product_list.append(product_id)   
                        """
                        campitab=str(history_id_obj.product_categ_id.id)+str(history_id_obj.product_id.id)+str(history_id_obj.location_id.id)+str(history_id_obj.anno)+str(history_id_obj.mese)
                        if rt_product_categ_id!=history_id_obj.product_categ_id.id:
                            try:
                                    cr.commit()
                                    _logger.info("categoria %s: rottura %s", rt_product_categ_id, rottura)
                            except:
                                    cr.rollback()
                                    _logger.info("errore categoria %s: rottura %s", rt_product_categ_id, rottura)
                            rt_product_categ_id=history_id_obj.product_categ_id.id
                            
                        if rottura!=campitab:
                                            tre_ids=history_obj_tre.search(cr,uid,[('product_id','=',campirottura['product_id']),
                                                                        ('anno','=',campirottura['anno']),
                                                                        ('mese','=',campirottura['mese']),
                                                                        ('location_id','=',campirottura['location_id'])],
                                                                                   context=context)
                                            
                                            if tre_ids:
                                                """
                                                history_obj_tre_id_obj=history_obj_tre.browse(cr,uid,tre_ids[0],context=context)
                                                if history_obj_tre_id_obj.blocco_agg==False:
                                                    vals.update({'quantity': history_obj_tre_id_obj.quantity+totquantity,
                                                                 'inventory_value': history_obj_tre_id_obj.inventory_value+totinventory_value
                                                                 })
                                                    history_obj_tre.write(cr,uid,tre_ids[0],vals,context=context)
                                                """
                                                ok_tre_ids=True
                                            else:
                                                vals={}
                                                for camporottura in campirottura.keys():
                                                    vals[camporottura]=campirottura[camporottura]
                                                tre_pre_ids=history_obj_tre.search(cr,uid,[('product_id','=',campirottura['product_id']),
                                                                            ('location_id','=',campirottura['location_id']),
                                                                            ],
                                                                            order='anno desc,mese desc',context=context)
                                                
                                                vals.update({'quantity': totquantity,
                                                             'inventory_value': totinventory_value,
                                                             })
                                                if tre_pre_ids:
                                                    tre_pre_id_obj=history_obj_tre.browse(cr,uid,tre_pre_ids[0],context=context)
                                                    vals.update({'quantity': totquantity+tre_pre_id_obj.quantity,
                                                                 'inventory_value': totinventory_value+tre_pre_id_obj.inventory_value,
                                                                 })
                                                
                                                history_obj_tre.create(cr,uid,vals,context=context)
                                            
                                            rottura=campitab
                                            campirottura.update({
                                                'location_id': history_id_obj.location_id.id,
                                                'company_id': history_id_obj.company_id.id,
                                                'product_id': history_id_obj.product_id.id,
                                                'product_categ_id': history_id_obj.product_categ_id.id,
                                                'anno': int(history_id_obj.anno),
                                                'mese': int(history_id_obj.mese),
                                                'price_unit_on_quant': history_id_obj.price_unit_on_quant,
                                                })
                                            try:
                                                totquantity=history_id_obj.quantity
                                            except:
                                                totquantity=0
                                            try:
                                                totinventory_value=history_id_obj.inventory_value
                                            except:
                                                totinventory_value=0


                        else:
                                            try:
                                                totquantity+=history_id_obj.quantity
                                            except:
                                                totquantity+=0
                                            try:
                                                totinventory_value+=history_id_obj.inventory_value
                                            except:
                                                totinventory_value+=0

        """uscita ciclo processo """ 
        
        tre_ids=history_obj_tre.search(cr,uid,[
                                                ('product_id','=',campirottura['product_id']),
                                                ('anno','=',campirottura['anno']),
                                                ('mese','=',campirottura['mese']),
                                                ('location_id','=',campirottura['location_id'])
                                            ],context=context)
        if tre_ids:
                                                """
                                                history_obj_tre_id_obj=history_obj_tre.browse(cr,uid,tre_ids[0],context=context)
                                                if  history_obj_tre_id_obj.blocco_agg==False:
                                                    vals.update({'quantity': history_obj_tre_id_obj.quantity+totquantity,
                                                                 'inventory_value': history_obj_tre_id_obj.inventory_value+totinventory_value
                                                                 })
                                                    history_obj_tre.write(cr,uid,tre_ids[0],vals,context=context)
                                                """
                                                ok_tre_ids=True
        else:
                                                vals={}
                                                for camporottura in campirottura.keys():
                                                                                        vals[camporottura]=campirottura[camporottura]
                                                vals.update({'quantity': totquantity,
                                                            'inventory_value': totinventory_value,
                                                                                                     })
                                                tre_pre_ids=history_obj_tre.search(cr,uid,[('product_id','=',campirottura['product_id']),
                                                                            ('location_id','=',campirottura['location_id']),
                                                                            ],
                                                                            order='anno desc,mese desc',context=context)
                                                
                                                if tre_pre_ids:
                                                    tre_pre_id_obj=history_obj_tre.browse(cr,uid,tre_pre_ids[0],context=context)
                                                    vals.update({'quantity': totquantity+tre_pre_id_obj.quantity,
                                                                 'inventory_value': totinventory_value+tre_pre_id_obj.inventory_value,
                                                                 })
                                                
                                                history_obj_tre.create(cr,uid,vals,context=context)
        try:
                cr.commit()
        except:
                cr.rollback()
                _logger.info("Errore fine categoria %s: rottura %s", rt_product_categ_id, rottura)
        _logger.info("fine categoria %s: rottura %s", rt_product_categ_id, rottura)
                                            
        in_commit=0
        #product_list=[5360,5362,36427,36291,4964,4965]
        product_list=[]
        if product_list==[]:
            product_list=product_obj.search(cr,uid,[('active','=',True)],order='categ_id,id',context=context)
        for product_id in product_list:
                annoprec=datetime.now().year - 6
                annoattu=datetime.now().year
                meseuattu=int(datetime.now().strftime("%m"))
                tre_ids_save=[]
                for anno in range(annoprec,annoattu+1,1):
                                    if anno!=annoattu:
                                        for mese in  range(01,13,1):
                                            tre_ids=history_obj_tre.search(cr,uid,[('product_id','=',product_id),
                                                                                   ('anno','=',anno),
                                                                                   ('mese','=',mese),
                                                                                   ],order='anno,mese',context=context)
                                            if tre_ids:
                                                tre_ids_save=tre_ids
                                            else:
                                                for tre_id_save in tre_ids_save:
                                                    history_obj_tre.copy(cr,uid,tre_id_save,{
                                                        'anno':anno,
                                                        'mese':mese
                                                        })
                                                
                                    else:
                                        for mese in  range(01,int(meseuattu)+1):
                                            tre_ids=history_obj_tre.search(cr,uid,[('product_id','=',product_id),
                                                                                   ('anno','=',anno),
                                                                                   ('mese','=',mese),
                                                                                   ],order='anno,mese',context=context)
                                            if tre_ids:
                                                tre_ids_save=tre_ids
                                            else:
                                                for tre_id_save in tre_ids_save:
                                                    history_obj_tre.copy(cr,uid,tre_id_save,{
                                                        'anno':anno,
                                                        'mese':mese
                                                        })
        
                try:
                                                cr.commit()
                except:
                                                cr.rollback()
                                                _logger.info("errore product_id %s: rottura %s", product_id, '-')
                _logger.info("product_id %s: rottura %s", product_id, '-')
        try:
                cr.commit()
        except:
                cr.rollback()
                _logger.info("errore fine calcolo %s: rottura %s", '-', '-')
        _logger.info("fine calcolo %s: rottura %s", '-', '-')
        tre_ids=history_obj_tre.search(cr,uid,[('blocco_agg','=',False)],order='product_categ_id,product_id,location_id,anno,mese',context=context)
        for  tre_id_obj in history_obj_tre.browse(cr,uid,tre_ids,context=context):
                                history_obj_tre.write(cr,uid,tre_id_obj.id,{'blocco_agg':True},context=context)

        history_id=self.create(cr,uid,{'data':None,
                                       'file_data':'export_valutazione.xls',
                                        'data_csv':None,
                                        'file_data_csv':'export_valutazione.csv',
                                       
                                       'date':date},context=context)
        _logger.info("fine blocco_agg %s: rottura %s", '-', '-')
        return  history_id 
        
        tre_ids=history_obj_tre.search(cr,uid,[('id','>',0)],order='product_categ_id,product_id,location_id,anno,mese',context=context)
        for  tre_id_obj in history_obj_tre.browse(cr,uid,tre_ids,context=context):
                                history_obj_tre.write(cr,uid,tre_id_obj.id,{'blocco_agg':True},context=context)
                                row+=1
                                variant = "-".join([v.name.replace(',','/') for v in history_id_obj.product_id.attribute_value_ids ])
                                variant =  "(%s)" % (variant,)
                                name=tre_id_obj.product_id.name
                                padre=''
                                if tre_id_obj.product_id.categ_id.parent_id:
                                    padre=tre_id_obj.product_id.categ_id.parent_id.name
                                    if  tre_id_obj.product_id.categ_id.parent_id.parent_id:
                                       padre+='/'+tre_id_obj.product_id.categ_id.parent_id.parent_id.name
                                #sheet.write(row, 0, history_id_obj.move_id.name)
                                sheet.write(row, 0, tre_id_obj.location_id.name)
                                sheet.write(row, 1, tre_id_obj.company_id.name)
                                sheet.write(row, 2, padre)
                                sheet.write(row, 3,tre_id_obj.product_categ_id.name)
                                sheet.write(row, 4, tre_id_obj.product_id.default_code)
                                sheet.write(row, 5, name)
                                sheet.write(row, 6, variant)
                                sheet.write(row, 7, tre_id_obj.quantity)
                                sheet.write(row, 8, tre_id_obj.anno)
                                sheet.write(row, 9, tre_id_obj.mese)
                                sheet.write(row, 10, tre_id_obj.price_unit_on_quant)
                                sheet.write(row, 11, tre_id_obj.inventory_value)
                                inventory_value=0.00
                                if tre_id_obj.inventory_value and isinstance(tre_id_obj.inventory_value, (int,long,float)):
                                    inventory_value=tre_id_obj.inventory_value
                                Dettaglio = {
                                    'location_id':tre_id_obj.location_id.name,
                                    'company_id':tre_id_obj.company_id.name,
                                    'categoria padre':padre,
                                    'categoria':tre_id_obj.product_categ_id.name,
                                    'codice':tre_id_obj.product_id.default_code,
                                    'descrizione':name,
                                    'Attributo':variant,
                                    'quantity':tre_id_obj.quantity,
                                    'anno':tre_id_obj.anno,
                                    'mese':tre_id_obj.mese,
                                    'price_unit_on_quant':tre_id_obj.price_unit_on_quant,
                                    'inventory_value':inventory_value
                                    }
                                
                                
                                
                                writer.writerow((
                                    str(Dettaglio['location_id']),
                                    str(Dettaglio['company_id']),
                                    try_coerce_ascii(Dettaglio['categoria padre']),
                                    try_coerce_ascii(Dettaglio['categoria']),
                                    try_coerce_ascii(Dettaglio['codice']),
                                    try_coerce_ascii(Dettaglio['descrizione'].replace(',','-')),
                                    try_coerce_ascii(Dettaglio['Attributo']),
                                    Dettaglio['quantity'],
                                    Dettaglio['anno'],
                                    Dettaglio['mese'],
                                    Dettaglio['price_unit_on_quant'],
                                    Dettaglio['inventory_value']
                                    ))
        excel_file.save(filename)
        excel_file.get_active_sheet()
        fileobj = os.fdopen(handle,'r')
        buffer=fileobj.read()
        out=base64.encodestring(buffer)
        fileobj.close
        #fileobj_csv.write(base64.decodestring(buffer_csv))
        #fileobj = os.fdopen(handle_csv,'r')
        #buffer_csv=fileobj.read()
        mystring=''
        buffer_csv.seek(0)
        reader = csv.reader(buffer_csv, quotechar='"', delimiter=',')
        for row in reader:
            mystring+=",".join(row)+"\r\n"
        out_csv=base64.encodestring(mystring)
        if ids:
            for history_id in ids:
                
                                    self.write(cr,uid,history_id,{'data':out,
                                       'file_data':'export_valutazione.xls',
                                        'data_csv':out_csv,
                                        'file_data_csv':'export_valutazione.csv',
                                       
                                       'date':date},context=context)
        else:
            history_id=self.create(cr,uid,{'data':out,
                                       'file_data':'export_valutazione.xls',
                                        'data_csv':out_csv,
                                        'file_data_csv':'export_valutazione.csv',
                                       
                                       'date':date},context=context)
        return  history_id 
    def view_open_table(self, cr, uid, ids, context=None):
                history_id=self.open_table(cr, uid, ids,None, context=context)
                model_data_obj = self.pool.get('ir.model.data')
                view_rec = model_data_obj.get_object_reference(
                    cr, uid, 'prof_webtex', 'view_wizard_valuation_history_log')
                view_id = view_rec and view_rec[1] or False
        
                return {
                    'view_type': 'form',
                    'view_id': [view_id],
                    'view_mode': 'form',
                    'res_model': 'wizard.valuation.history.log',
                    'res_id': history_id,
                    'type': 'ir.actions.act_window',
                    'target': 'normal',
                    'context': context,
                }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
        
            
            
            
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
