
from openerp.osv import osv,fields

class product_public_category(osv.Model):
    _inherit = ["product.public.category", "website.seo.metadata"]
    _name = 'product.public.category'
    
    _columns = {
            'description' : fields.html('Description for Category', translate=True),
        }

product_public_category()


