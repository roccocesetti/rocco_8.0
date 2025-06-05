# coding: utf-8
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C)2010-  OpenERP SA (<http://openerp.com>). All Rights Reserved
#    App Author: Vauxoo
#
#    Developed by Oscar Alcala
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import time
import datetime
from email import utils
import openerp
from openerp import models, api, fields as opn_fields
from openerp.http import request as req_2
import xml.etree.ElementTree as ET
import base64
try:
    import simplejson as json
except ImportError:
    import json
import logging
import openerp.addons.decimal_precision as dp
from openerp.osv import orm, osv, fields


class res_company(models.Model):
    _inherit = 'res.company'
    @api.multi
    def get_2nd_company(self, company=None):
        cr, uid, context = req_2.cr, req_2.uid, req_2.context
        uid=openerp.SUPERUSER_ID
        if not company:
            return None
        ids =  self.search(cr, uid, [('parent_id','child_of',[company])])
        if ids:
            return ids[0]
        return None


class BlogPost(models.Model):
    
    
    _inherit = 'blog.post'
    _columns = {
         'website_noindex':fields.boolean('Blocca indicizzazione', required=False), 
    }
    @api.multi
    def _get_date(self):
        posts = self
        for post in posts:
            date_obj = time.strptime(post.write_date, "%Y-%m-%d %H:%M:%S")
            dt = datetime.datetime.fromtimestamp(time.mktime(date_obj))
            write_tuple = dt.timetuple()
            timestamp = time.mktime(write_tuple)
            post.date_rfc2822 = utils.formatdate(timestamp)

    date_rfc2822 = opn_fields.Char(
        compute=_get_date,
        string="Date RFC-2822")
    def get_price(self, pricelist_id, product_id):
        cr, uid, context = req_2.cr, openerp.SUPERUSER_ID, req_2.context
        uid=openerp.SUPERUSER_ID
        price_digits = dp.get_precision('Product Price')
        pricelist = req_2.registry.get('product.pricelist').browse(cr, uid, [pricelist_id], context=context)[0]
        price_dict = req_2.registry.get('product.pricelist').price_get(cr, uid, [pricelist_id], product_id, 0.0,partner=None, context=context)
        return price_dict[pricelist_id]

    def rss_product(self, new_get={'lang':None,'partner_id':None}):
        cr, uid, context = req_2.cr, req_2.uid, req_2.context
        uid=openerp.SUPERUSER_ID
        # new_get = dict(get)
        lang=new_get.get('lang','it_IT').decode('utf-8').encode('utf-8')
        partner_id=int(new_get.get('partner_id',1).decode('utf-8').encode('utf-8'))
        print 'entrata_mia_logistica',uid,openerp.SUPERUSER_ID,lang,partner_id,context
        rml_parser = report_sxw.rml_parse(cr, uid, 'reconciliation_widget_aml', context=context)

        if context is None:
            context={}
        context['lang']=lang
        print 'context',context
        date_today=time.strftime('%Y-%m-%d')
        db_name = cr.dbname
        product_obj = req_2.registry.get('product.product')
        warehouse_obj = req_2.registry.get('stock.warehouse')
        stock_move_obj = req_2.registry.get('stock.move')
        product_site_export_obj = req_2.registry.get('product.site.export')                
        pricelist_obj = req_2.registry.get('product.pricelist')
        pricelist_version_obj = req_2.registry.get('product.pricelist.version')
        pricelist_item_obj = req_2.registry.get('product.pricelist.item')
        partner_obj = req_2.registry.get('res.partner')
        user_obj = req_2.registry.get('res.users')
        user_id_obj=user_obj.browse(cr,uid,uid,context=context)
        partner_company_id=user_id_obj.company_id.partner_id.id
        prod_ids=None
        warehouse_ids=None
        partner_id_obj=partner_obj.browse(cr,uid,partner_id,context=context)
        request ='<?xml version="1.0" encoding="utf-8" ?><root><pagine><CurPage>1</CurPage><LastPage>1</LastPage><PageSize>1</PageSize><TotSize>1</TotSize><customer>'+str(partner_id)+'</customer></pagine><Products>'
        warehouse_id=True
        if warehouse_id:
                product_ids = product_obj.search(cr, uid, [('active','=', True)])    
                conta=0
                for product_id in product_ids:
                            conta+=1
                            if conta>20:
                                continue
                            product_id_obj=product_obj.browse(cr,uid,product_id,context=context)
                            if product_id_obj.default_code:
                                prod_ids_rec=product_id_obj
                                #price_surcharge = pricelist_obj.price_get(cr, uid, [partner_id_obj.property_product_pricelist.id],prod_ids_rec.id, 1.0, partner_id, {'uom': prod_ids_rec.uom_id.id,'date': date_today}) [partner_id_obj.property_product_pricelist.id]
                                price_surcharge = self.get_price(partner_id_obj.property_product_pricelist[0].id,prod_ids_rec.id)
    
                                try:
                                            codice=str(prod_ids_rec.default_code).replace("è", "e'").replace("à", "a'").replace("ù", "u'").replace("É", "E").replace("È", "E").replace("À", "A").replace("Ù", "U")
                                            nome=str(prod_ids_rec.name).replace("è", "e'").replace("à", "a'").replace("ù", "u'").replace("É", "E").replace("È", "E").replace("À", "A").replace("Ù", "U")
                                            codice=codice.decode('ascii', 'ignore').encode('utf-8')
                                            nome=nome.decode('ascii', 'ignore').encode('utf-8')
                                except:
                                            #nome='Errore codifica unicode'
                                            nome=u'{string}'.format(string=nome or '')
                                            #codice=str(prod_ids_rec.default_code).decode('ascii', 'ignore').encode('utf-8')
                                            codice=u'{string}'.format(string=codice or '')
                                try:
                                    categoria=prod_ids_rec.categ_id.name
                                    if prod_ids_rec.categ_id:
                                            categoria=str(prod_ids_rec.categ_id.name).decode('ascii', 'ignore').encode('utf-8')
                                    else:
                                            categoria=''.decode('ascii', 'ignore').encode('utf-8')
                                except:
                                    categoria=u'{string}'.format(string=categoria or '')
                                    #categoria='errore unicode'
                                try:
                                    Categoria_padre=prod_ids_rec.categ_id.parent_id.name
                                    if prod_ids_rec.categ_id.parent_id:
                                            Categoria_padre=str(prod_ids_rec.categ_id.parent_id.name).decode('ascii', 'ignore').encode('utf-8')
                                    else:
                                            Categoria_padre=''.decode('ascii', 'ignore').encode('utf-8')
                                except:
                                    Categoria_padre=u'{string}'.format(string=Categoria_padre or '')
                                    #Categoria_padre='errore unicode'
                                attributo=''
                                for attribute_values_id in prod_ids_rec.attribute_value_ids:
                                    attributo+=attribute_values_id.name
                                #"'data:image/png;base64,%s' % get_image(p['id'])"
                                try:
                                    attributo=attributo.decode('utf-8')
                                    attributo=attributo.decode('ascii', 'ignore')
                                    #attributo=attributo.replace("è", "e'").replace("à", "a'").replace("ù", "u'").replace("É", "E").replace("È", "E").replace("À", "A").replace("Ù", "U")
                                except:
                                    attributo=u'{string}'.format(string=attributo or '')
                                    attributo='-'
                                request =request+"<Product><Code>"+codice.replace("&", "")+"</Code><AvailableQty>"+str(str(prod_ids_rec.virtual_available)).decode('ascii', 'ignore').encode('utf-8')+"</AvailableQty><Nome-Brand-Variante>"+nome.replace("&" or "ù" or "®", "")+"</Nome-Brand-Variante><category>"+categoria+"</category><Category_first>"+Categoria_padre+"</Category_first><Price>"+str(price_surcharge)+"</Price><attibute>" + attributo + "</attibute><binary>" + str(prod_ids_rec.image) + "</binary></Product>" 
        request =request+"</Products></root>"            
        #print request
        """
        request.decode('utf-8')
        request.decode('ascii', 'ignore')
        """
        #request.encode('utf-8')
        """
        xml_root = ET.fromstring(request)
        """
        #send_request(site_ids.name_site,request,context)
        #print request
        #mimetype = 'application/xml;charset=utf-8'
        mimetype = 'application/xml'
        #return req_2.make_response(request, [('Content-Type', mimetype)])
        return request
    
    
class website_seo_metadata(osv.Model):
    _inherit = 'website.seo.metadata'
    _columns = {
        'website_meta_google_site_verification': fields.char("Website meta google verification", translate=True),
        'website_noindex':fields.boolean('Blocca indicizzazione', required=False), 
    }
website_seo_metadata()

    
class view(osv.osv):
    _inherit = "ir.ui.view"
    _columns = {
        'website_meta_google_site_verification': fields.char("Website meta google verification", translate=True),
        'website_noindex':fields.boolean('Blocca indicizzazione', required=False), 
    }
view()


class res_users(osv.osv):
    _inherit = 'res.users' 
    _columns = {
        'x_fix_top_menu':fields.boolean('Fixed top menu,user public', required=False), 
     }
    _defaults = {  
            'x_fix_top_menu': True,  
            }
res_users()


class website(orm.Model):
    _inherit = "website"
    _columns = {
                'x_field_footer':fields.text(string='Footer description', translate=True,),
                'x_fix_top_menu':fields.boolean('Fixed top menu,user public', required=False), 

                        }
    @openerp.tools.ormcache(skiparg=4)
    def _get_current_website_id(self, cr, uid, domain_name, context=None):
        ids = self.search(cr, uid, [('name', 'ilike', domain_name)], context=context)
        if ids==[]:
            ids=super(website, self)._get_current_website_id(cr, uid, domain_name, context=context)
        return ids and ids[0] or None
website()
