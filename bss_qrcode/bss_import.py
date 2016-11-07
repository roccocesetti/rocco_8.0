# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014 Bluestar Solutions Sàrl (<http://www.blues2.ch>).
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

from openerp.osv import osv, fields

# Pseudo constants
SUCCESS_MSG = "The document is successfully added."
FAIL_QRCODE_MSG = "OpenERP QR Code cannot be found."
FAIL_OBJECT_MSG = "OpenERP object cannot be found."
NOT_FOUND_MSG = "The QR Code cannot be found."
SUCCESS = "success"
FAIL = "fail"
NOT_FOUND = "not_found"
FILENAME_QRCODE_NOT_FOUND = "qrcode_not_found"
PROCESSED = "processed"
UNPROCESSED = "unprocessed"
   
""" Imported document. """            
class bss_imported_document(osv.osv):

    _name = 'bss_qrcode.imported_document'
    _description = "Imported QR Code documented"
    _rec_name = 'qrcode_id'
   
    _columns = {
        'import_id': fields.many2one('bss_qrcode.import', string="Imported date", ondelete='cascade', required=True, readonly=True),
        'status': fields.selection([('success','Success'), ('fail','Fail'), ('not_found', 'QR Code not found')], string='Status', required=True),
        'state': fields.selection([('unprocessed','Unprocessed'), ('processed','Processed')], string='State', required=True),
        'qrcode_id': fields.many2one('bss_qrcode.qrcode', string='File'),
        'message': fields.char('Message'),
        'qrcode_create_date': fields.related('qrcode_id', 'create_date', type='char', string='First download date', store=False),
        'oe_version': fields.related('qrcode_id', 'oe_version', type='char', string='Version', store=False),
        'oe_object': fields.related('qrcode_id', 'oe_object', type='char', string='Object', store=False),
        'oe_id': fields.related('qrcode_id', 'oe_id', type='char', string='Id', store=False),
        'user_id': fields.related('qrcode_id', 'user_id', type='char', string='User id', store=False),
        'report': fields.related('qrcode_id', 'report', type='char', string='Report', store=False),
        'filename': fields.related('qrcode_id', 'filename', type='char', string='Filename', store=False),
    }
    
    _defaults = {
        'state': 'unprocessed',
    }
        
    """ Trigger import state when state of the document import change. """
    def onchange_state(self, cr, uid, ids, context=None):
        for imported_document in self.browse(cr, uid, ids, context):
            myimport = self.pool.get('bss_qrcode.import').browse(cr, uid, imported_document.import_id.id)
            count_unprocessed = self.search(cr, uid, [('import_id', '=', myimport.id), ('state', '=', UNPROCESSED)], count=True)
            if count_unprocessed > 0:
                myimport.write({'state': UNPROCESSED})
            else:
                myimport.write({'state': PROCESSED})
            
    """ Set the state to processed. """
    def action_processed(self, cr, uid, ids, context=None):
        for imported_document in self.browse(cr, uid, ids, context):
            self.write(cr, uid, imported_document.id, {'state': PROCESSED}, context)
            self.onchange_state(cr, uid, ids)
        return 1

    """ Set the state to unprocessed. """
    def action_unprocessed(self, cr, uid, ids, context=None):
        for imported_document in self.browse(cr, uid, ids, context):
            self.write(cr, uid, imported_document.id, {'state': UNPROCESSED}, context)
            self.onchange_state(cr, uid, ids)
        return 1

bss_imported_document()

""" Class which contains all imported files of an xmlrpc call. """
class bss_import(osv.osv):
    
    _name = 'bss_qrcode.import'
    _description = 'Imported files from xmlrpc'
    _order = 'create_date DESC'
  
    """ Get the child number (i.e imported documents) which have a specific status. """
    def get_nb(self, cr, uid, ids, name, arg, context=None):
        res = {}
        bss_imported_document = self.pool.get('bss_qrcode.imported_document')
        
        for import_id in ids:
            res[import_id] = bss_imported_document.search(cr, uid, [('import_id', '=', import_id), ('status', 'like', arg['status'])], count=True)

        return res
        
    _columns = {
        'name': fields.char('Date created', readOnly=True),
        'create_date' : fields.datetime('Date created', readonly=True),
        'imported_document_ids': fields.one2many('bss_qrcode.imported_document', 'import_id', string='Imported documents', readOnly=True),
        'status': fields.selection([('success','All documents succeed'), ('fail','At least one failed document')], 'Status', required=True, readOnly=True),
        'state': fields.selection([('unprocessed','Unprocessed'), ('processed','Processed')], string='State', required=True, readOnly=True),
        'progression': fields.selection([('finished','Finished'), ('in_progress','In progress'), ('error','Error')], 'Progression', required=True, readOnly=True),
        'success_nb': fields.function(get_nb, arg={'status': 'success'}, method=True, store=False, string="Number of successes", type="integer", readOnly=True),  
        'fail_nb': fields.function(get_nb, arg={'status': 'fail'}, method=True, store=False, string="Number of fails", type="integer", readOnly=True),  
        'not_found_nb': fields.function(get_nb, arg={'status': 'not_found'}, method=True, store=False, string="Number of not found", type="integer", readOnly=True),  
        'total': fields.function(get_nb, arg={'status': '%'}, method=True, store=False, string="Total", type="integer", readOnly=True),  
    }
       
    _defaults = {
        'state': 'unprocessed',
    }
    
    """ Set the import status to fail. """
    def set_status_to_fail(self, cr, uid, ids, myimport):
        myimport.write({'status': FAIL})
        
    """ Process document by creating the imported document and attach the file to it.
        Moreover attach the file to the concerned object or make a custom action.  """
    def process_document(self, cr, uid, myimport, qrcode_id, document):
        qrcode = None
        
        # 1. The QR Code is not found
        if qrcode_id == 0:
            imported_document = {
                'import_id': myimport.id,
                'status': NOT_FOUND,
                'state': UNPROCESSED,
                'qrcode_id': qrcode_id,
                'message': NOT_FOUND_MSG,
            }
            myimport.set_status_to_fail(myimport)
        else:
            qrcode = self.pool.get('bss_qrcode.qrcode').read(cr, uid, qrcode_id)
        
            # 2. The OpenERP QRCode dont'exist
            if(qrcode is None):
                imported_document = {
                    'import_id': myimport.id,
                    'status': FAIL,
                    'state': UNPROCESSED,
                    'qrcode_id': qrcode_id,
                    'message': FAIL_QRCODE_MSG,
                }
                myimport.set_status_to_fail(myimport)
            else:
                myobject = self.pool.get(qrcode['oe_object']).read(cr, uid, qrcode['oe_id'])
                
                # 3. The specific OpenERP object don't exist
                if(myobject is None):
                    imported_document = {
                        'import_id': myimport.id,
                        'status': FAIL,
                        'state': UNPROCESSED,
                        'qrcode_id': qrcode_id,
                        'message': FAIL_OBJECT_MSG,
                    }
                    myimport.set_status_to_fail(myimport)
                # 4. The document doesn't have any problem  
                else:
                    imported_document = {
                        'import_id': myimport.id,
                        'status': SUCCESS,
                        'state': PROCESSED,
                        'qrcode_id': qrcode_id,
                        'message': SUCCESS_MSG,
                    }

                    # If the qrcode_custom_treatment exists, then we use the specific treatment
                    try:
                        getattr(self.pool.get(qrcode['oe_object']), "qrcode_custom_treatment")
                        self.pool.get(qrcode['oe_object']).qrcode_custom_treatment(cr, uid, qrcode, document)
                    # Else we use the default treatment i.e to attach the file to the object
                    except AttributeError:
                        self.pool.get('bss_qrcode.qrcode').attach_file(cr, uid, qrcode['id'], document)
        
        class_imported_document = self.pool.get('bss_qrcode.imported_document')          
        row_id = class_imported_document.create(cr, uid, imported_document)
        class_imported_document.onchange_state(cr, uid, [row_id])
        
        # Filename attachment
        if qrcode is None:
            filename = FILENAME_QRCODE_NOT_FOUND
        else:
            filename = qrcode['filename']
        
        # Attach the document to the object
        ir_attachment = self.pool.get('ir.attachment')
        ir_attachment.create(cr, uid, {
            'name': filename,
            'datas_fname': filename,
            'res_model': 'bss_qrcode.imported_document',
            'res_id': row_id,
            'type': 'binary',
            'db_datas': document,
        })

        return row_id
        
    """ Function called by an xmlrpc connection. Create an import object with documents. """
    def add_to_import_object(self, cr, uid, import_id, qrcode_id, document):
        
        myimport = self.read(cr, uid, import_id)
        
        # In order to have a dictionary and not an array
        myimport = self.browse(cr, uid, myimport['id'])

        row_id = self.process_document(cr, uid, myimport, qrcode_id, document)
        
        return row_id
                 
bss_import()