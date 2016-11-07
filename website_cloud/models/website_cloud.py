from openerp.osv import orm

class cloud(orm.Model):
    _name = 'account.x.service.notify'
    _inherit = ['account.x.service.notify','website.seo.metadata']

