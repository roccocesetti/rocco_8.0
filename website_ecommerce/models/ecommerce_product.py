from openerp import api, fields, models
from urlparse import urlparse
import openerp

class EcommerceProducts(models.Model):
    _inherit = 'product.template'

    is_feture_product = fields.Boolean('Fetures Products')
    is_recommended_product = fields.Boolean('Recommended Products')
    is_shop_product = fields.Boolean('shop Products')

class Website(models.Model):
    _inherit = 'website'

    def get_feture_products(self):

        feture_products_ids = self.env['product.template'].search([('is_feture_product', '=', True)], limit = 3 )
        return feture_products_ids

    def get_recommended_products(self):

        recommended_products_ids = self.env['product.template'].search([('is_recommended_product', '=', True)])
        return recommended_products_ids

    def get_shop_products(self):

        shop_products_ids = self.env['product.template'].search([('is_shop_product', '=', True)])
        
        return shop_products_ids

    def get_recommended_length(self):
        r_length = []
        r_items_is = []
        count = 1
        
        recommended_products_ids = self.env['product.template'].search([('is_recommended_product', '=', True)])
        for record in recommended_products_ids:
            con = count % 3
            r_length.append(record)
            if con == 0:
                r_items_is.append(r_length)
                r_length = []

            count = count + 1

        return r_items_is


    def get_product_category(self):  

        category_ids = self.env['product.public.category'].search([], limit = 5)
        if category_ids and len(category_ids) > 5:
            category_ids = category_ids[:5]
        elif category_ids and len(category_ids) <= 5:
            category_ids = category_ids
        return category_ids

    def get_category_products(self, cid):

        Cate_Products = self.env['product.template'].search([('sale_ok', '=', True),('public_categ_ids', 'child_of', cid)], limit = 4)
       
        return Cate_Products

    def get_product_categories(self):
        return self.env['product.public.category'].search([('parent_id', '=', False)])

class website(models.Model):
    _inherit = 'website'

    social_skype = fields.Char('Skype Call')

class BlogPost(models.Model):
    _inherit = "blog.post"

    image_thumb = fields.Binary('Thumb Image', compute="_get_image", store=True, attachment=True)

    @api.depends('background_image')
    def _get_image(self):
        for record in self:
            if record.background_image:
                image_source = urlparse(record.background_image).path.split('/')
                image_path = openerp.modules.get_module_resource(image_source[-6], ('/').join(image_source[-5:]))
                if image_path:
                    record.image_thumb = image.image_resize_image(open(image_path, 'rb').read().encode('base64'), size=(400, 300))
            else:
                record.iamge_thumb = False

