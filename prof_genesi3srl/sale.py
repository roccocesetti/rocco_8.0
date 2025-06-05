
import logging
import xmlrpclib
from openerp import models, fields, api
from openerp.osv import osv,expression
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.unit.mapper import (mapping,
                                                  ImportMapper
                                                  )
from openerp.addons.connector.exception import IDMissingInBackend
from ..unit.backend_adapter import (GenericAdapter)
from ..unit.import_synchronizer import (DelayedBatchImporter, WooImporter)
from ..connector import get_environment
from ..backend import woo
_logger = logging.getLogger(__name__)

@woo
class SaleOrderAdapter(osv.osv):
    _inherit = 'woo.sale.order'
     
    #Do not touch _name it must be same as _inherit
    #_name = 'woo.sale.order'