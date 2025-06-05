# -*- coding: utf-8 -*-
#
#
#    Tech-Receptives Solutions Pvt. Ltd.
#    Copyright (C) 2009-TODAY Tech-Receptives(<http://www.techreceptives.com>).
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
#

import logging
from openerp import fields, _
from openerp.addons.connector.queue.job import job, related_action
from openerp.addons.connector.unit.synchronizer import Importer
from openerp.addons.connector.exception import IDMissingInBackend
from ..connector import get_environment
from ..related_action import link
from datetime import datetime
_logger = logging.getLogger(__name__)


class WooImporter(Importer):

    """ Base importer for WooCommerce """

    def __init__(self, connector_env):
        """
        :param connector_env: current environment (backend, session, ...)
        :type connector_env: :class:`connector.connector.ConnectorEnvironment`
        """
        super(WooImporter, self).__init__(connector_env)
        self.woo_id = None
        self.woo_record = None

    def _get_woo_data(self):
        """ Return the raw WooCommerce data for ``self.woo_id`` """
        return self.backend_adapter.read(self.woo_id)

    def _before_import(self):
        """ Hook called before the import, when we have the WooCommerce
        data"""

    def _is_uptodate(self, binding):
        """Return True if the import should be skipped because
        it is already up-to-date in OpenERP"""
        WOO_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
        dt_fmt = WOO_DATETIME_FORMAT
        assert self.woo_record
        if not self.woo_record:
            return  # no update date on WooCommerce, always import it.
        if not binding:
            return  # it does not exist so it should not be skipped
        sync = binding.sync_date
        if not sync:
            return
        from_string = fields.Datetime.from_string
        sync_date = from_string(sync)
        self.woo_record['updated_at'] = {}
        self.woo_record['updated_at'] = {'to': datetime.now().strftime(dt_fmt)}
        woo_date = from_string(self.woo_record['updated_at']['to'])
        # if the last synchronization date is greater than the last
        # update in woo, we skip the import.
        # Important: at the beginning of the exporters flows, we have to
        # check if the woo_date is more recent than the sync_date
        # and if so, schedule a new import. If we don't do that, we'll
        # miss changes done in WooCommerce
        return woo_date < sync_date

    def _import_dependency(self, woo_id, binding_model,
                           importer_class=None, always=False):
        """ Import a dependency.

        The importer class is a class or subclass of
        :class:`WooImporter`. A specific class can be defined.

        :param woo_id: id of the related binding to import
        :param binding_model: name of the binding model for the relation
        :type binding_model: str | unicode
        :param importer_cls: :class:`openerp.addons.connector.\
                                     connector.ConnectorUnit`
                             class or parent class to use for the export.
                             By default: WooImporter
        :type importer_cls: :class:`openerp.addons.connector.\
                                    connector.MetaConnectorUnit`
        :param always: if True, the record is updated even if it already
                       exists, note that it is still skipped if it has
                       not been modified on WooCommerce since the last
                       update. When False, it will import it only when
                       it does not yet exist.
        :type always: boolean
        """
        if not woo_id:
            return
        if importer_class is None:
            importer_class = WooImporter
        binder = self.binder_for(binding_model)
        if always or binder.to_openerp(woo_id) is None:
            importer = self.unit_for(importer_class, model=binding_model)
            importer.run(woo_id)

    def _import_dependencies(self):
        """ Import the dependencies for the record

        Import of dependencies can be done manually or by calling
        :meth:`_import_dependency` for each dependency.
        """
        return

    def _map_data(self):
        """ Returns an instance of
        :py:class:`~openerp.addons.connector.unit.mapper.MapRecord`

        """
        #import pdb; pdb.set_trace()
        print 'WooImporter-_map_data_self.woo_record',self.woo_record
        _logger.debug('_map_data_self.woo_record: %s', self.woo_record,)
        self.woo_record=self._add_data_woo_record(self.woo_record)
        return self.mapper.map_record(self.woo_record)
    """ rocco Cesetti 06-09-2017 """ 
    def _add_data_woo_record(self,woo_record=None):
        print 'WooImporter-_add_data_woo_record'
        if woo_record==None:
            woo_record=self.woo_record
        if woo_record.get('order',None):
                 if float(woo_record['order']['total_shipping'])>0:
                     prezzo_sped=float(woo_record['order']['shipping_lines'][0]['total']) if woo_record['order']['shipping_lines'] else self.backend_record.delivery_product_id.price
                     prezzo_sped+=float(woo_record['order']['fee_lines'][0].get('total',0)) if woo_record['order'].get('fee_lines',[]) else 0
                     woo_record['items'].append(
                                                {'total_tax': '0.00', 
                                                 'price': str(prezzo_sped),
                                                  'meta': [], 
                                                  'subtotal_tax': '0.00',
                                                   'total': str(prezzo_sped), 
                                                   'subtotal':str(prezzo_sped), 
                                                   'id': 999, 
                                                   'name': self.backend_record.delivery_product_id.name, 
                                                   'sku': 'TRASPORTO', 
                                                   'product_id': self.backend_record.delivery_product_id.id, 
                                                   'tax_class': '', 
                                                   'quantity': 1})
        return woo_record
    def _validate_data(self, data):
        """ Check if the values to import are correct

        Pro-actively check before the ``_create`` or
        ``_update`` if some fields are missing or invalid.

        Raise `InvalidDataError`
        """
        return

    def _must_skip(self):
        """ Hook called right after we read the data from the backend.

        If the method returns a message giving a reason for the
        skipping, the import will be interrupted and the message
        recorded in the job (if the import is called directly by the
        job, not by dependencies).

        If it returns None, the import will continue normally.

        :returns: None | str | unicode
        """
        return

    def _get_binding(self):
        return self.binder.to_openerp(self.woo_id, browse=True)

    def _create_data(self, map_record, **kwargs):
        #import pdb; pdb.set_trace()
        print '_create_data',map_record
        #print '_create_data_kwargs',kwargs
        return map_record.values(for_create=True, **kwargs)

    def _create(self, data):
        """ Create the OpenERP record """
        # special check on data before import
        #import pdb; pdb.set_trace()

        self._validate_data(data)
        model = self.model.with_context(connector_no_export=True)
        model = str(model).split('()')[0]
        print 'WooImporter-_create',data
        #data=self._add_order_data(data,model)
        binding = self.env[model].create(data)
        _logger.debug('%d created from woo %s', binding, self.woo_id)
        return binding

    def _update_data(self, map_record, **kwargs):
        #import pdb; pdb.set_trace()
        return map_record.values(**kwargs)
    """ rocco cesetti 06-09-2017 """
    def _add_order_data(self, data,model):
                         print 'WooImporter-_add_order_data'    
                         if model=='woo.sale.order' or model=='woo.res.partner':
                             data['goods_description_id']=self.backend_record.goods_description_id.id or None
                             data['carriage_condition_id']=self.backend_record.carriage_condition_id.id or None
                             data['transportation_method_id']=self.backend_record.transportation_method_id.id or None
                             data['transportation_reason_id']=self.backend_record.transportation_reason_id.id or None
                             data['workflow_process_id']=self.backend_record.workflow_process_id.id or None
                             data['payment_method_id']=self.backend_record.payment_method_id.id or None

                             if self.woo_record.get('role',None):
                                 if model=='woo.res.partner':
                                     data['property_product_pricelist']=self.backend_record.pricelist_id.id or None
                                 if model=='woo.sale.order':
                                    data['pricelist_id']=self.backend_record.pricelist_id.id or None
                                 
                         return data

    def _update(self, binding, data):
        """ Update an OpenERP record """
        # special check on data before import
        #import pdb; pdb.set_trace()
        self._validate_data(data)
        binding.with_context(connector_no_export=True).write(data)
        _logger.debug('%d updated from woo %s', binding, self.woo_id)
        return

    def _after_import(self, binding):
        """ Hook called at the end of the import """
        return

    def run(self, woo_id, force=False):
        """ Run the synchronization

        :param woo_id: identifier of the record on WooCommerce
        """
        #import pdb; pdb.set_trace()

        self.woo_id = woo_id
        try:
            print 'run.woo_record_00',woo_id
            self.woo_record = self._get_woo_data()
            print 'run.woo_record',self.woo_record
            _logger.debug('run_self.woo_record: %s', self.woo_record,)
        except IDMissingInBackend:
            return _('Record does no longer exist in WooCommerce')

        skip = self._must_skip()
        if skip:
            return skip

        binding = self._get_binding()
        if not force and self._is_uptodate(binding):
            return _('Already up-to-date.')
        self._before_import()

        # import the missing linked resources
        print 'run_binding_00',binding
        self._import_dependencies()

        map_record = self._map_data()

        print 'run_binding',binding,'map_record',map_record
        if binding:
            record = self._update_data(map_record)
            self._update(binding, record)
        else:
            record = self._create_data(map_record)
            binding = self._create(record)
        self.binder.bind(self.woo_id, binding)

        self._after_import(binding)


WooImportSynchronizer = WooImporter


class BatchImporter(Importer):

    """ The role of a BatchImporter is to search for a list of
    items to import, then it can either import them directly or delay
    the import of each item separately.
    """

    def run(self, filters=None):
        """ Run the synchronization """
        #import pdb; pdb.set_trace()
        print 'BatchImporter-run'
        record_ids = self.backend_adapter.search(filters)
        for record_id in record_ids:
            self._import_record(record_id)

    def _import_record(self, record_id):
        """ Import a record directly or delay the import of the record.

        Method to implement in sub-classes.
        """
        raise NotImplementedError


BatchImportSynchronizer = BatchImporter


class DirectBatchImporter(BatchImporter):

    """ Import the records directly, without delaying the jobs. """
    _model_name = None

    def _import_record(self, record_id):
        """ Import the record directly """
        #import pdb; pdb.set_trace()
        print 'DirectBatchImporter-_import_record'
        import_record(self.session,
                      self.model._name,
                      self.backend_record.id,
                      record_id)


DirectBatchImport = DirectBatchImporter


class DelayedBatchImporter(BatchImporter):

    """ Delay import of the records """
    _model_name = None

    def _import_record(self, record_id, **kwargs):
        """ Delay the import of the records"""
        #_import_recordimport pdb; pdb.set_trace()
        print 'DelayedBatchImporter-_import_record'
        import_record.delay(self.session,
                            self.model._name,
                            self.backend_record.id,
                            record_id,
                            **kwargs)

DelayedBatchImport = DelayedBatchImporter


@job(default_channel='root.woo')
@related_action(action=link)
def import_record(session, model_name, backend_id, woo_id, force=False):
    """ Import a record from Woo """
    print 'DelayedBatchImporter-import_record',session,model_name,backend_id,woo_id
    env = get_environment(session, model_name, backend_id)
    print 'DelayedBatchImporter_01-import_record',session,model_name,backend_id,woo_id
    #import pdb; pdb.set_trace()
    importer = env.get_connector_unit(WooImporter)
    print 'DelayedBatchImporter_02-import_record',session,model_name,backend_id,woo_id
    importer.run(woo_id, force=force)
