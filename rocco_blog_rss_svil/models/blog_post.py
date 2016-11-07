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

from openerp.http import request as req_2
import xml.etree.ElementTree as ET
import base64
try:
    import simplejson as json
except ImportError:
    import json
import logging
import openerp.addons.decimal_precision as dp
from openerp.addons.website.models import website
from openerp import tools
from openerp import models, fields as new_fields, api
from openerp.osv import orm, osv,fields
MENU_ITEM_SEPARATOR = "/"
class ir_ui_menu(osv.osv):
    _inherit ="ir.ui.menu"
            #Do not touch _name it must be same as _inherit
            #_name = 'openerpmodel' = 'ir.ui.menu'

    def x_get_user_roots(self, cr, uid,company_id, context=None):
        """ Return all root menu ids visible for the user.

        :return: the root menu ids
        :rtype: list(int)
        """
        uid=openerp.SUPERUSER_ID
        website_obj=self.pool.get('website')
        website_menu_obj=self.pool.get('website.menu')
        menu_obj=self.pool.get('ir.ui.menu')
        website_ids=website_obj.search(cr, uid, [('company_id','=',company_id)], context=context)
        if website_ids:
            website_menu_ids=website_menu_obj.search(cr, uid, [('website_id','=',website_ids[0])], context=context)
        else:
            website_menu_ids=None
        if website_menu_ids:
            menu_domain = [('parent_id', '=', False)]
        else:
            menu_domain = [('parent_id', '=', False)]
            
        return self.search(cr, uid, menu_domain, context=context)

    @api.cr_uid_context
    @tools.ormcache_context(accepted_keys=('lang',))
    def x_load_menus_root(self, cr, uid,company_id, context=None):
        uid=openerp.SUPERUSER_ID
        my_fields = ['name', 'sequence', 'parent_id', 'action']
        menu_root_ids = self.x_get_user_roots(cr, uid,company_id, context=context)
        menu_roots = self.read(cr, uid, menu_root_ids, my_fields, context=context) if menu_root_ids else []
        return {
            'id': False,
            'name': 'root',
            'parent_id': [-1, ''],
            'children': menu_roots,
            'all_menu_ids': menu_root_ids,
        }
ir_ui_menu()
class ir_ui_view(osv.osv):
    _inherit = "ir.ui.view"
    @api.cr_uid_ids_context
    def x_render(self, cr, uid, id_or_xml_id, values=None, engine='ir.qweb', context=None):
        if req_2 and getattr(req_2, 'website_enabled', False):
            engine='website.qweb'

            if isinstance(id_or_xml_id, list):
                id_or_xml_id = id_or_xml_id[0]

            if not context:
                context = {}
            company_id= context.get('company_id',None) 
            company = self.pool['res.company'].browse(cr, openerp.SUPERUSER_ID, company_id or req_2.website.company_id.id, context=context)
            menu_data=req_2.registry['ir.ui.menu'].x_load_menus_root(cr, uid,company_id, context=context) 
            qcontext = dict(
                context.copy(),
                website=req_2.website,
                url_for=website.url_for,#req_2.website.url_for,
                slug=website.slug,
                res_company=company,
                user_id=req_2.registry["res.users"].browse(cr, uid, uid),
                translatable=context.get('lang') != req_2.website.default_lang_code,
                editable=req_2.website.is_publisher(),
                menu_data=menu_data ,
            )

            # add some values
            if values:
                qcontext.update(values)

            # in edit mode ir.ui.view will tag nodes
            if not qcontext.get('rendering_bundle'):
                if qcontext.get('editable'):
                    context = dict(context, inherit_branding=True)
                elif req_2.registry['res.users'].has_group(cr, uid, 'base.group_website_publisher'):
                    context = dict(context, inherit_branding_auto=True)

            view_obj = req_2.website.get_template(id_or_xml_id)
            if 'main_object' not in qcontext:
                qcontext['main_object'] = view_obj

            values = qcontext
            return super(ir_ui_view, self).render(cr, uid, id_or_xml_id, values=values, engine=engine, context=context)
ir_ui_view()


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
    @api.multi
    def _get_date(self):
        posts = self
        for post in posts:
            date_obj = time.strptime(post.write_date, "%Y-%m-%d %H:%M:%S")
            dt = datetime.datetime.fromtimestamp(time.mktime(date_obj))
            write_tuple = dt.timetuple()
            timestamp = time.mktime(write_tuple)
            post.date_rfc2822 = utils.formatdate(timestamp)
    date_rfc2822 = new_fields.Char(
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
        #new_get = dict(get)
        lang=new_get.get('lang','it_IT').decode('utf-8').encode('utf-8')
        partner_id=int(new_get.get('partner_id',1).decode('utf-8').encode('utf-8'))
        print 'entrata_mia_logistica',uid,openerp.SUPERUSER_ID,lang,partner_id,context
        rml_parser = report_sxw.rml_parse(cr, uid, 'reconciliation_widget_aml', context=context)

        if context==None:
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

class website_mm(osv.osv):
    _inherit = 'website' 
    _columns = {
                    'menu_id': fields.many2one('website.menu', string="Menu' sito"),
                    }
    def get_current_website(self, cr, uid, context=None):
        # TODO: Select website, currently hard coded
        res=super(website_mm, self).get_current_website(cr, uid, context=context)
        if context is None:
            context={}
        if context.get('company',None):
            company_id=context.get('company',None).id
            print 'get_current_website_company_id',company_id
            return self.pool['website'].browse(cr, uid, company_id, context=context)
        return res
    def _render(self, cr, uid, ids, template, values=None, context=None):
        # TODO: remove this. (just kept for backward api compatibility for saas-3)
        if context is None:
            context={}
        if context.get('company',None):
            company_id=context.get('company',None).id
            company=context.get('company',None)
        else:
            company_id=None
            company=None
        if values is None:
            values={}
        if values.get('company_id',None):
            values['company_id']  =company_id
        if values.get('company',None):
            values['company']  =company
        print '_render_company_id',company_id,values
        res=super(website_mm, self)._render(cr, uid, ids, template, values=values, context=context)              
        return res

    def render(self, cr, uid, ids, template, values=None, status_code=None, context=None):
        # TODO: remove this. (just kept for backward api compatibility for saas-3)
        if context is None:
            context={}
        if context.get('company',None):
            company_id=context.get('company',None).id
            company=context.get('company',None)
        else:
            company_id=None
            company=None
        if values is None:
            values={}
        if values.get('company_id',None):
            values['company_id']  =company_id
        if values.get('company',None):
            values['company']  =company
        print 'render_company_id',company_id,values
        res=super(website_mm, self).render(cr, uid, ids, template, values=values, status_code=status_code, context=context)
        
        return res
        
    #Do not touch _name it must be same as _inherit
    #_name = 'website' = "website" # Avoid website.website convention for conciseness (for new api). Got a special authorization from xmo and rco
