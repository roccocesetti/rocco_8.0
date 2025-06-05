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

import time
from openerp.osv import osv
from openerp.report import report_sxw
import tempfile
from tempfile import TemporaryFile
import base64
import os, sys
class product_pricelist_heartwood(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(product_pricelist_heartwood, self).__init__(cr, uid, name, context=context)
        self.pricelist={}
        self.localcontext.update({
            'time': time,
            'get_pricelist': self._get_pricelist,
            'get_currency': self._get_currency,
            'get_categories': self._get_categories,
            'get_price': self._get_price,
            'get_titles': self._get_titles,
            'get_image': self._get_image,
            'get_marchio': self._get_marchio,
        })

    def _get_pricelist(self, pricelist_id):
        pricelist = self.pool.get('product.pricelist').read(self.cr, self.uid, [pricelist_id], ['name'], context=self.localcontext)[0]
        return pricelist['name']

    def _get_titles(self, form):
        lst = []
        vals = {}
        if form['price_list_pubblico']:
                vals = {}
                vals['price_list_pubblico'] =  self._get_pricelist(form['price_list_pubblico'])
                lst.append(vals)
        if form['price_list_ingrosso']:
                vals = {}
                vals['price_list_ingrosso'] =  self._get_pricelist(form['price_list_ingrosso'])
                lst.append(vals)
        if form['price_list_costo']:
                vals = {}
                vals['price_list_costo'] =  self._get_pricelist(form['price_list_costo'])
                lst.append(vals)
        return lst



    def _get_currency(self, pricelist_id):
        pricelist = self.pool.get('product.pricelist').read(self.cr, self.uid, [pricelist_id], ['currency_id'], context=self.localcontext)[0]
        return pricelist['currency_id'][1]

    def _get_categories(self, products, data):
        form=data['form']
        cat_ids=[]
        res=[]
        self.pricelist['price_list_pubblico'] = form['price_list_pubblico']
        self.pricelist['price_list_ingrosso'] = form['price_list_ingrosso']
        self.pricelist['price_list_costo'] = form['price_list_costo']
        pro_ids=[]
        if data.get('select',True):
            products=products
        else:
            products=self.pool.get('product.product').browse(self.cr,self.uid,data['ids'],context=self.localcontext)
        for product in products:
            pro_ids.append(product.id)
            if product.categ_id.id not in cat_ids:
                cat_ids.append(product.categ_id.id)

        cats = self.pool.get('product.category').name_get(self.cr, self.uid, cat_ids, context=self.localcontext)
        if not cats:
            return res
        for cat in cats:
            product_ids=self.pool.get('product.product').search(self.cr, self.uid, [('id', 'in', pro_ids), ('categ_id', '=', cat[0])], context=self.localcontext)
            products = []
            for product in self.pool.get('product.product').read(self.cr, self.uid, product_ids, ['image','attribute_value_ids', 'code','name','virtual_available'], context=self.localcontext):

                attrib_val=[]
                for value_id in product['attribute_value_ids']:
                    att_val_obj=self.pool.get('product.attribute.value').read(self.cr,self.uid,value_id,['name'],context=self.localcontext)
                    attrib_val.append(att_val_obj['name'].encode('UTF-8'))
                if form['dispo']:
                    dispo=product['virtual_available']
                else:
                    dispo=None
                val = {
                     'id':product['id'],
                     'name':attrib_val,
                     'code':product['name'],
                     'dispo':dispo
                }
                val['price_list_pubblico']=self._get_price(self.pricelist['price_list_pubblico'], product['id'])
                if self.pricelist['price_list_ingrosso']:
                    val['price_list_ingrosso']=self._get_price(self.pricelist['price_list_ingrosso'], product['id'])
                else:
                     val['price_list_ingrosso']=None
                if self.pricelist['price_list_costo']:
                    val['price_list_costo']=self._get_price(self.pricelist['price_list_costo'], product['id'])
                else:
                    val['price_list_costo']=None
                products.append(val)
            res.append({'name':cat[1],'products': products})
        return res

    def _get_price(self, pricelist_id, product_id):
        sale_price_digits = self.get_digits(dp='Product Price')
        pricelist = self.pool.get('product.pricelist').browse(self.cr, self.uid, [pricelist_id], context=self.localcontext)[0]
        price_dict = self.pool.get('product.pricelist').price_get(self.cr, self.uid, [pricelist_id], product_id, 0.0,partner=None, context=self.localcontext)
        if price_dict[pricelist_id]:
            price = self.formatLang(price_dict[pricelist_id], digits=sale_price_digits, currency_obj=pricelist.currency_id)
        else:
            res = self.pool.get('product.product').read(self.cr, self.uid, [product_id])
            price =  self.formatLang(res[0]['list_price'], digits=sale_price_digits, currency_obj=pricelist.currency_id)
        return price
    def _get_image(self, product_id):
                """
                if product['image']:
                    try:
                        handle, filepath = tempfile.mkstemp()
                        fileobj = os.fdopen(handle,'w+')  # convert raw handle to file object        try:
                        
                        fileobj.write(base64.decodestring(product['image']))
                        fileobj.close()
                    except:
                        os.unlink(filepath)
                        filepath=None    
                else:
                    filepath=None
                """

                
                product_id_obj = self.pool.get('product.product').browse(self.cr, self.uid, product_id, context=self.localcontext)
                if product_id_obj.image:                    
                    return product_id_obj.image_small
                else:
                    return None
    def _get_marchio(self, partner_id):
                """
                if product['image']:
                    try:
                        handle, filepath = tempfile.mkstemp()
                        fileobj = os.fdopen(handle,'w+')  # convert raw handle to file object        try:
                        
                        fileobj.write(base64.decodestring(product['image']))
                        fileobj.close()
                    except:
                        os.unlink(filepath)
                        filepath=None    
                else:
                    filepath=None
                """

                
                partner_id_obj = self.pool.get('res.partner').browse(self.cr, self.uid, partner_id, context=self.localcontext)
                if partner_id_obj.image:                    
                    return partner_id_obj.image_medium
                else:
                    return None


class report_product_pricelist_heartwood(osv.AbstractModel):
    _name = 'report.heartwood.report_pricelist_heartwood'
    _inherit = 'report.abstract_report'
    _template = 'heartwood.report_pricelist_heartwood'
    _wrapped_report_class = product_pricelist_heartwood

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
