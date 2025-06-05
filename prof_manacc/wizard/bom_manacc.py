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
from openerp import api, _
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
from openerp.osv import fields, osv
import tempfile
from openerp.exceptions import except_orm, Warning, RedirectWarning
from _ast import Break
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
from openerp import models, fields as x_fields, _


class bom_manacc(osv.osv_memory):
    _name = 'mrp.bom.dup'
    _description = 'dup bom'

    _columns = {
        'name':fields.char('Name', size=64, required=False, readonly=False),
        'bom_id': fields.many2one('mrp.bom', 'Distinta origine', required=False),
    }
    _defaults = {
    'name':'duplica',
    }
    def create_bom(self, cr, uid, ids, context=None):
            if hasattr(ids, '_iter_'):
                ids=ids
            else:
                ids=[ids]
            """
            
            To get the date and print the report
            @return : return report
            """
            this=self.browse(cr, uid, ids[0], context=context)
            if this.bom_id.id:
                    ids=this.bom_id.id
            else:
                    ids=[]
            if context is None:
                context = {}
            if ids==[]:
                if context.get('active_ids', []):
                    ids=context.get('active_ids', [])
            if  ids==[]:                   
                raise except_orm(_('Nessuna scelta è Stata Fatta'), 'Selezionare almeno una distinta base')
            bom_obj=self.pool.get('mrp.bom')
            bom_line_obj=self.pool.get('mrp.bom.line')
            product_obj=self.pool.get('product.template')
            F_process=False
            """ leggo la distinta """
            for  bom_id_obj in bom_obj.browse(cr,uid,ids,context=context):
                prod_var=[]
                mat_var=[]
                """ leggo le varianti della distinta base"""
                
                
                for product_id_obj in bom_id_obj.product_tmpl_id.product_variant_ids:
                    if bom_obj.search(cr,uid,[('product_tmpl_id','=',product_id_obj.product_tmpl_id.id),('product_id','=',product_id_obj.id)]):
                        continue
                    if F_process==False:
                        F_process=True 
                    if product_id_obj.is_product_variant==False:
                        continue
                    attributes_var=""
                    io=0
                    x_fatt_molt=1
                    for x in product_id_obj.attribute_value_ids:
                        io+=1
                        attributes_var+= x.name if io==1 else ','+x.name
                        if x.x_fatt_molt<>0:
                            x_fatt_molt*= x.x_fatt_molt
                    bom_new_id=bom_obj.copy(cr, uid,bom_id_obj.id , {'product_id':product_id_obj.id,'name':product_id_obj.name+'('+attributes_var+')'}, context)
                    bom_obj.write(cr,uid,bom_new_id,{'name':product_id_obj.name+'('+attributes_var+')'},context=context)
                    cr.commit()
                    prod_var.append(product_id_obj)
                    bom_new_id_obj=bom_obj.browse(cr,uid,bom_new_id,context=context)
                    for bom_line_id_obj in bom_new_id_obj.bom_line_ids:
                        for product_variant_id_obj in bom_line_id_obj.product_id.product_tmpl_id.product_variant_ids:
                                
                                num_attr=0
                                for attribute_var_id in product_variant_id_obj.attribute_value_ids:
                                    if attribute_var_id.name=="CONSUMO":
                                        num_attr+=1
                                    if attribute_var_id in product_id_obj.attribute_value_ids:
                                        num_attr+=1
                                #if num_attr==len(product_id_obj.attribute_value_ids):
                                if num_attr>0:
                                        bom_line_obj.write(cr,uid,bom_line_id_obj.id,{'product_id':product_variant_id_obj.id,
                                                                                    'product_qty':product_variant_id_obj.x_qta_dist * x_fatt_molt if product_variant_id_obj.x_qta_dist>0 else bom_line_id_obj.product_qty * x_fatt_molt,
                                                                                    'product_uos_qty':product_variant_id_obj.x_qta_dist * x_fatt_molt if product_variant_id_obj.x_qta_dist>0 else bom_line_id_obj.product_uos_qty * x_fatt_molt,
                                                                               #'attribute_value_ids':[(6, 0, [x.id for x in product_variant_id_obj.attribute_value_ids])],
                                                                               'attribute_value_ids':[(6, 0, [x.id for x in product_id_obj.attribute_value_ids])]
                                                                               },context=context)
                                        break
                                      
    
            if F_process==False:
                    raise Warning(_('Attenzione Nessuna distinta è sta generata'))
                    return False
            return True

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
class bom_line(osv.osv):
    _inherit = 'mrp.bom.line'
    def _get_price(self,cr,uid,ids,field_name, arg,context=None):
        cur_obj = self.pool.get('res.currency')
        res = {}
        if context is None:
            context = {}
        """"---"""
        for line in  self.browse(cr,uid,ids,context=context):
            price = line.product_id.standard_price
            if line.product_id.pricelist_id.currency_id:
                cur = line.product_id.pricelist_id.currency_id
            else:
                cur= line.product_id.company_id.partner_id.property_product_pricelist.currency_id
            res[line.id] = price #cur_obj.round(cr, uid,cur, price)
        return res
    def _get_cus_ns_npps(self,cr,uid,ids,field_name, arg,context=None):
        cur_obj = self.pool.get('res.currency')
        res = {}
        if context is None:
            context = {}
        """"---"""
        for line in  self.browse(cr,uid,ids,context=context):
            price = line.product_id.standard_price
            if line.product_id.pricelist_id.currency_id:
                cur = line.product_id.pricelist_id.currency_id
            else:
                cur= line.product_id.company_id.partner_id.property_product_pricelist.currency_id
            #res[line.id] = cur_obj.round(cr, uid,cur, line.product_qty* (line.cu_stampo/line.Num_stp/line.Num_pz_stp))
            res[line.id] = line.product_qty* ((line.cu_stampo/line.Num_stp/line.Num_pz_stp))
        return res
    
    _columns = {
    'cu_stampo': fields.float('Costo unitario Stampo', digits=(16, 8),digits_compute= dp.get_precision('Product Price')),
    'Num_stp': fields.integer('Numero Stampate') ,
    'Num_pz_stp': fields.integer('Numero pezzi x stampo') ,
    #'standard_price': fields.function(_get_price, string='Costo', digits_compute= dp.get_precision('Product Price')),
    'cus_ns_npps': fields.function(_get_cus_ns_npps, string='C.U. STAMPO per Pezzo', digits_compute= dp.get_precision('Product Price'))
                    
                            }
    _defaults = {  
                        'cu_stampo': 0, 
                        'Num_stp': 1,
                        'Num_pz_stp':1
                         
                        }
    def onchange_product_id(self, cr, uid, ids, product_id, product_qty=0, context=None):
        res=super(bom_line, self).onchange_product_id(cr, uid,ids, product_id, product_qty=product_qty, context=context)
        cur_obj = self.pool.get('res.currency')
        #res = {}
        if context is None:
            context = {}
        obj_product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
        price = obj_product.standard_price
        if obj_product.pricelist_id.currency_id:
                cur = obj_product.pricelist_id.currency_id
        else:
                cur= obj_product.company_id.partner_id.property_product_pricelist.currency_id
        if res.get('value',{}):
            res['value']['cu_stampo']=price
        
        return res
    def on_change_cu_stampo(self, cr, uid, ids, product_id, uom, product_qty,cu_stampo,Num_stp,Num_pz_stp, context=None):
        """ Changes UoM
        @param location_id: Location id
        @param product: Changed product_id
        @param uom: UoM product
        @return:  Dictionary of changed values
        """
        cur_obj = self.pool.get('res.currency')
        res = {}
        if context is None:
            context = {}
        obj_product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
        price = obj_product.standard_price
        if obj_product.pricelist_id.currency_id:
                cur = obj_product.pricelist_id.currency_id
        else:
                cur= obj_product.company_id.partner_id.property_product_pricelist.currency_id
        #cus_ns_npps = cur_obj.round(cr, uid,cur, product_qty* (cu_stampo/Num_stp/Num_pz_stp))
        cus_ns_npps = product_qty* ((cu_stampo/Num_stp/Num_pz_stp))
        print 'product_id',product_id,'cus_ns_npps', cus_ns_npps,'product_qty',product_qty,'cu_stampo',cu_stampo,'Num_stp',Num_stp,'Num_pz_stp',Num_pz_stp
        return {'value': {'cus_ns_npps': cus_ns_npps}}

class bom(osv.osv):
    _inherit = 'mrp.bom'
    _columns = {
                'x_perc_scarto': fields.float('% scarto', digits=(16, 8),digits_compute= dp.get_precision('Product Price')),

                        }
    _defaults = {  
        'x_perc_scarto': 0,  
        }
    @api.multi
    def write_product(self):
        tot_price=sum([line.cus_ns_npps for line in self.bom_line_ids])
        tot_price=tot_price*(100+self.x_perc_scarto)/100
        if self.product_id:
            self.product_id.write({'standard_price':tot_price})
        else:
            self.product_tmpl_id.write({'standard_price':tot_price})
    @api.multi
    def write_product_prezzo(self):
        tot_price=sum([line.cus_ns_npps for line in self.bom_line_ids])
        tot_price=tot_price*(100+self.x_perc_scarto)/100
        if self.product_id:
            self.product_id.write({'price':tot_price,'list_price':tot_price})
        else:
            self.product_tmpl_id.write({'price':tot_price,'list_price':tot_price})
    #'x_price_subtax': fields.function(_price_subtax_, string='Subtax', digits_compute= dp.get_precision('Product Price')),
    
    
     
            #Do not touch _name it must be same as _inherit
            #_name = 'mrp.bom.line'        
            
            
            
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
        
            
            
            
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
