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
class res_company(osv.osv):
    _inherit = 'res.company'
    _columns = {
        'x_pubblico_id': fields.many2one('product.pricelist', 'Pubblico', required=False),
        'x_ingrosso_id': fields.many2one('product.pricelist', 'Ingrosso', required=False),
        'x_costo_id': fields.many2one('product.pricelist', 'Costo', required=False),
        'x_iva_ven_id':fields.many2one('account.tax', 'Aliquota Vendite', required=False,domain=[('type_tax_use','=','sale')]), 
        'x_iva_acq_id':fields.many2one('account.tax', 'Aliquota acquisti', required=False,domain=[('type_tax_use','=','purchase')]), 
        'x_uom_id':fields.many2one('product.uom', 'unità di misura', required=False), 
        'x_row_ini': fields.integer('Riga iniziale'),
        'x_row_fin': fields.integer('Riga Finale') 
                    }
res_company()
class stock_move(osv.osv):
    _inherit = 'stock.move' 
    def _prod_image(self, cr, uid, ids, name, args, context=None):
        prod_obj = self.pool.get('product.product')
        res = dict.fromkeys(ids, None)
        for move_id_obj in self.browse(cr, uid, ids, context=context):
            res[move_id_obj.id] = move_id_obj.product_id.image
        return res
    _columns = {
            'x_image':fields.function(_prod_image, method=True, type='binary', string='Img', store=False), 
                    }
        
    @api.returns('self', 
        upgrade=lambda self, value, args, offset=0, limit=None, order=None, count=False:value if count else self.browse(value), 
        downgrade=lambda self, value, args, offset=0, limit=None, order=None, count=False:value if count else value.ids)
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        print 'search_stock_move_start'
        if uid!=SUPERUSER_ID:
            user_id=uid
        
        else:
            user_id=SUPERUSER_ID
        if hasattr(user_id, '__iter_'):
            user_id=user_id
        else:
            user_id=[user_id]
        user_obj=self.pool.get('res.users')
        for user_id_obj in user_obj.browse(cr,uid,user_id,context=context):
                if user_id_obj.x_location_id.id:
                    domains = [['location_id', '=', user_id_obj.x_location_id.id],['location_dest_id', '=', user_id_obj.x_location_id.id]]
                    #args1=expression.AND([args,[['location_id', '=', user_id_obj.x_location_id.id]]])
                    #args2=expression.AND([args,[['location_dest_id', '=', user_id_obj.x_location_id.id]]])
                    #args=expression.OR([args1,args2])
                    #args.append(domains)
                    args1=expression.OR([[['location_id', '=', user_id_obj.x_location_id.id]],[['location_dest_id', '=', user_id_obj.x_location_id.id]]])
                    args=expression.AND([args,args1])
                else:
                    domain=''
        #print 'search_stock_move_domain',domains,args
        res=super(stock_move, self).search(cr, uid, args, offset=offset, limit=limit, order=order, context=context, count=count)
        return res

class stock_picking(osv.osv):
    _inherit = 'stock.picking' 
    def _get_default_user_id(self, cr, uid, context=None):
        user_id = uid
        return user_id
    _columns = {
        'x_user_id':fields.many2one('res.users', 'Utente', required=False), 
        #'picking_type_id': fields.function(_get_operation_id, type='many2one', relation='stock.picking.type', string='Tipo operazione'),
        #'contract_id': fields.function(_get_latest_contract, string='Contract', type='many2one', relation="hr.contract", help='Latest contract of the employee'),
        'picking_type_id':fields.many2one('stock.picking.type', 'Type Operation', required=False), 
      }
    _defaults = {  
        'x_user_id': lambda self, cr, uid, c=None: self._get_default_user_id(cr, uid, context=c)
        }
    def user_id_change(self, cr, uid, ids,partner_id, user_id, context=None):
        result={}
        if uid!=SUPERUSER_ID:
            user_id=uid
            result['x_user_id']=user_id
        user_obj=self.pool.get('res.users')
        
        if hasattr(user_id, '__iter_'):
            user_id=user_id
        else:
            user_id=[user_id]
        type_op=[]
        war={}
        partner_id_obj=self.pool.get('res.partner').browse(cr,uid,partner_id,context=context)
        print 'parter',partner_id_obj.name,partner_id_obj.x_property_stock_internal.name
        for user_id_obj in user_obj.browse(cr,uid,user_id,context=context):
            print 'user_id_obj',user_id,user_id_obj.name,user_id_obj.x_picking_type_ids,partner_id_obj.x_property_stock_internal.name

            for picking_type in user_id_obj.x_picking_type_ids:
                    print 'picking_type_in','loc_partner',picking_type.name,partner_id_obj.x_property_stock_internal.name,'loc_type_in',picking_type.default_location_src_id.name,'loc_type_out',picking_type.default_location_dest_id.name
                    if partner_id_obj.x_property_stock_internal:
                        print 'conf',partner_id_obj.x_property_stock_internal,'src',picking_type.default_location_src_id.id,'dest',picking_type.default_location_dest_id.id
                        if (partner_id_obj.x_property_stock_internal.id==picking_type.default_location_src_id.id) or (partner_id_obj.x_property_stock_internal.id==picking_type.default_location_dest_id.id):
                            print 'picking_type',picking_type.name,partner_id_obj.x_property_stock_internal.name,picking_type.default_location_src_id.name,picking_type.default_location_dest_id.name
                            type_op.append(picking_type.id)
                    else:
                            print 'picking_type',picking_type.id
                            type_op.append(picking_type.id)
        domain = {'picking_type_id':
                        [('id', '=',tuple(type_op))],}

        res_part=self.onchange_partner_in(cr,uid,partner_id,context=context)
        print 'res_part',res_part
        if res_part:
            result['partner_id']=res_part['value']['partner_id']
            war['warning']=res_part['warning']
        print 'domain',domain
        return { 'value': result,'domain': domain,'warning':war}

class res_partner(osv.osv):
    _inherit = 'res.partner' 
    _columns = {
        'x_property_stock_internal':fields.many2one('stock.location', 'Punto di Stoccaggio Interno', required=False), 
     }
class res_users(osv.osv):
    _inherit = 'res.users' 
    _columns = {
        'x_location_id':fields.many2one('stock.location', 'Punto di Stoccaggio', required=False), 
        'x_picking_type_ids':fields.many2many('stock.picking.type', 'stock_picking_type_user_rel', 'user_id', 'pick_type_id', 'Operazioni ammesse'), 
     }
res_users()
class rc_stock_key(osv.osv):
    """ api key  magazzino"""

    _name = "rc.stock.key"
    _description = "chiavi utilizzo magazzino"
    _columns = {
        'name': fields.char('name', size=128 , required=True),
        'apiuser': fields.char('apyuser', size=128 , required=True),
        'apikey': fields.char('apykey', size=128 , required=True),
        'apiconta': fields.integer('Contatotore'), 
        'data_key': fields.date('Data'), 
     }
    _defaults = {  
        'name': 'Ricevi apikey_apiuser',  
        'apiuser': '[-------------]',  
        'apikey': '[--------------]',  
        'data_key': lambda *a: time.strftime('%Y-%m-%d'),  
        }
    def key_active_call(self, cr, uid, ids=None,context=None):
        #import pdb; pdb.set_trace()
        if ids==None:
            ids=self.search(cr,uid,[('id','>',0)],context=context)
        if hasattr(ids, '__iter__'):
            ids=ids
        else:
            ids=[ids]
        fl_user=False
        fl_key=False
        apimsg=None
        for key_active_obj in self.browse(cr, uid, ids, context=context):
            try:
                    url = str('http://www.ideawork.it/check_module/apiserver.php')
                    http = httplib2.Http()
                    hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
           'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
           'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
           'Accept-Encoding': 'none',
           'Accept-Language': 'en-US,en;q=0.8',
           'Connection': 'keep-alive'}
                    #import pdb; pdb.set_trace()
                    request ='<customers><customer><apiuser>'+key_active_obj.apiuser+'</apiuser><apikey>'+key_active_obj.apikey+'</apikey></customer></customers>'
                    urequest = urllib2.Request(url+"?request="+request,headers=hdr)
                    uopen = urllib2.urlopen(urequest)
                    resp = uopen.read()

                    if resp:
                        root = ET.fromstring(resp)
                        fl_user=False
                        fl_key=False
                        for nodes in root.getchildren():
                            if nodes.tag!='customer':
                                continue
                            apikey=None
                            apiuser=None
                            apimsg=None
                            apidata=None
                            apiconta=None
                            for node in nodes.getchildren():
                                if node.tag=='apiuser':
                                   apiuser=node.text
                                if node.tag=='apikey':
                                   apikey=node.text
                                if node.tag=='apiconta':
                                   apiconta=int(node.text)
                                if node.tag=='apimsg':
                                   apimsg=node.text
                                if node.tag=='apidata':
                                   apidata=datetime.strptime(node.text,"%d/%m/%Y").strftime("%Y-%m-%d")
                                   data_today=str(datetime.today().date())
                                   if apiuser==key_active_obj.apiuser:
                                         #import pdb; pdb.set_trace()
                                         if apikey==key_active_obj.apikey:
                                             if apiconta==1:
                                                    fl_key=True
                                                    break
                                             else:
                                                if apidata>=data_today:
                                                    fl_key=True
                                                    break
                                                    
                                                else:
                                                    fl_key=False
                                                    break
                        if fl_key==False:
                            return {'apiflag':False,'apimsg':apimsg}
                            #raise osv.except_osv(_("Attenzione impossibile continuare il servizio è scaduto %s"), _("contattare l'amministratore"))
            except:
                        return {'apiflag':True,'apimsg':apimsg}                   
            #print 'fl_key--->',fl_key,apimsg
            #import pdb; pdb.set_trace()
            return {'apiflag':fl_key,'apimsg':apimsg}
rc_stock_key()

class product_product(osv.osv):
    _inherit = 'product.product'
    def _default_price_pubblic(self, cr, uid,ids,name, arg,context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id:
            if user.company_id.x_pubblico_id:
                x_pubblico_id=user.company_id.x_pubblico_id.id
                
            else:
                x_pubblico_id=None
        res = {}
        sale_price_digits =dp.get_precision('Product Price')
        pricelist = self.pool.get('product.pricelist').browse(cr, uid, [x_pubblico_id], context=context)[0]
        for id in ids:
            price_dict = self.pool.get('product.pricelist').price_get(cr, uid, [x_pubblico_id], id, 0.0,partner=None, context=context)
            if price_dict[x_pubblico_id]:
                #price = self.formatLang(price_dict[x_pubblico_id], digits=sale_price_digits, currency_obj=pricelist.currency_id)
                res[id] =price_dict[x_pubblico_id]
            else:
                res_prod = self.pool.get('product.product').browse(cr, uid, id,context=context)
                #price =  self.formatLang(res_prod.list_price, digits=sale_price_digits, currency_obj=pricelist.currency_id)
                res[id] =res_prod.list_price

        return res
    def _default_price_ingrosso(self, cr, uid,ids,name, arg,context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id:
            if user.company_id.x_ingrosso_id:
                x_ingrosso_id=user.company_id.x_ingrosso_id.id
                
            else:
                x_ingrosso_id=None
        res = {}
        sale_price_digits =dp.get_precision('Product Price')
        pricelist = self.pool.get('product.pricelist').browse(cr, uid, [x_ingrosso_id], context=context)[0]
        for id in ids:
            price_dict = self.pool.get('product.pricelist').price_get(cr, uid, [x_ingrosso_id], id, 0.0,partner=None, context=context)
            if price_dict[x_ingrosso_id]:
                #price = self.formatLang(price_dict[x_ingrosso_id], digits=sale_price_digits, currency_obj=pricelist.currency_id)
                res[id] =price_dict[x_ingrosso_id]
            else:
                res_prod = self.pool.get('product.product').browse(cr, uid, id,context=context)
                #price =  self.formatLang(res_prod.list_price, digits=sale_price_digits, currency_obj=pricelist.currency_id)
                res[id] =res_prod.list_price

        return res
    def _default_costo(self, cr, uid,ids,name, arg,context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id:
            if user.company_id.x_costo_id:
                x_costo_id=user.company_id.x_costo_id.id
                
            else:
                x_costo_id=None
        res = {}
        sale_price_digits = dp.get_precision('Product Price')
        pricelist = self.pool.get('product.pricelist').browse(cr, uid, [x_costo_id], context=context)[0]
        for id in ids:
            price_dict = self.pool.get('product.pricelist').price_get(cr, uid, [x_costo_id], id, 0.0,partner=None, context=context)
            if price_dict[x_costo_id]:
                #price = self.formatLang(price_dict[x_costo_id], digits=sale_price_digits, currency_obj=pricelist.currency_id)
                res[id] =price_dict[x_costo_id]
            else:
                res_prod = self.pool.get('product.product').browse(cr, uid, id,context=context)
                #price =  self.formatLang(res_prod.list_price, digits=sale_price_digits, currency_obj=pricelist.currency_id)
                res[id] =res_prod.list_price

        return res
    _columns = {
                 'pubblico_default': fields.function(_default_price_pubblic, type='float', string='Pubblico', digits_compute=dp.get_precision('Product Price')),
                 'ingrosso_default': fields.function(_default_price_ingrosso, type='float', string='Ingrosso', digits_compute=dp.get_precision('Product Price')),    
                 'costo_default': fields.function(_default_costo, type='float', string='Costo', digits_compute=dp.get_precision('Product Price')),
   
                        }
    
class product_import(osv.osv):
    """ product Import """
     
        #Do not touch _name it must be same as _inherit
        #_name = 'product.product'
    def _default_uom_id(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id:
            if user.company_id.x_uom_id:
                return user.company_id.x_uom_id.id
                
            else:
                return None
        return None
    def _default_tax_id(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id:
            if user.company_id.x_iva_ven_id:
                return user.company_id.x_iva_ven_id.id
                
            else:
                return None
        return None
    def _default_tax_acq_id(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id:
            if user.company_id.x_iva_acq_id:
                return user.company_id.x_iva_acq_id.id
                
            else:
                return None
        return None
    def _default_x_row_ini(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id:
            if user.company_id.x_row_ini:
                return user.company_id.x_row_ini
                
            else:
                return None
        return None
    def _default_x_row_fin(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id:
            if user.company_id.x_row_fin:
                return user.company_id.x_row_fin
                
            else:
                return None
        return None

    _name = "product.import"
    _description = "Product Import"
    _columns = {
        'name': fields.char('identificativo di  Importazione', size=64 , required=True),
        'data': fields.binary('File', required=True),
        'overwrite': fields.boolean('Sovrascrivi i codici esistenti',
                                    help=" i codici esistenti  "
                                         "saranno sostituiti  le giacenza i prezzi e i costi"),
        'tax_id':fields.many2one('account.tax', 'Aliquota Vendite', required=True,domain=[('type_tax_use','=','sale')]), 
        'tax_id_acq':fields.many2one('account.tax', 'Aliquota acquisti', required=True,domain=[('type_tax_use','=','purchase')]), 
        'uom_id':fields.many2one('product.uom', 'unità di misura', required=True,), 
        'row_ini': fields.integer('Riga iniziale'),
        'rows': fields.integer('Riga Finale') 
     }
    _defaults = {  
            'name': '\importa',  
            'uom_id': _default_uom_id,  
            'tax_id': _default_tax_id,  
            'tax_id_acq': _default_tax_acq_id,  
             'row_ini': _default_x_row_ini,  
            'rows': _default_x_row_fin,  
            }
    def import_product(self, cr, uid, ids, context=None):
        
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
            self.load_data( cr, uid, ids ,filepath, context=context)
        finally:
            os.unlink(filepath)  # delete t
        return True
    def load_data(self, cr, uid, ids, filepath,  context=None):
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
                track_yes=False
                
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
                supplier_ids = supplier_obj.search(cr, uid, [('product_id','=', prod_ids_id),('name','=', produttore_ids_id)])    
                vals={
                     'name':produttore_ids_id,#codice
                     'product_name':None,#qta_gicanza
                     'product_code':None,#marca
                     'product_uom':None,#codice prodotto fornitore
                     'min_qty':1,
                     'product_id':prod_ids_id,
                     
                     }# skip empty rows and rows where the translation field (=last fiefd) is empty
                if not supplier_ids:
                # lets create the language with locale information
 
                   supplier_obj.create(cr, uid, vals, context=context)
                else:
                    if this.overwrite==True: 
                       supplier_obj.write(cr, uid, supplier_ids[0], vals, context)                        
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
