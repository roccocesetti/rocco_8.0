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
import qrcode
import StringIO
import json

class bss_qrcode(osv.osv):

    _name = 'bss_qrcode.qrcode'
    _description = "QR Code generation and files association"
    _rec_name = 'filename'
   
    _columns = {
        'create_date' : fields.datetime('Date created', readonly=True),
        'oe_version': fields.char('Openerp version'),  
        'oe_object': fields.char('Openerp object'),
        'oe_id': fields.integer('Openerp id'),  
        'user_id': fields.integer('User id'),  
        'report': fields.char('Report'),  
        'filename': fields.char('Filename'),  
        'server_id': fields.char('Server id')
    }
    
    """ If the QR Code exists return it, create it else. """
    def get_qrcode(self, cr, uid, qrcode_data):
        # Search if the qrcode exists
        search_qrcode = self.search(cr, uid, [
            ('oe_object', '=', qrcode_data['oe_object']),
            ('oe_id', '=', qrcode_data['oe_id']),
            ('report','=', qrcode_data['report'])
        ])
                        
        # If the QR Code already exists, we use it
        if search_qrcode:
            qrcode_id = search_qrcode[0]
        # Else we create a new QR Code
        else:
            qrcode_id = self.create(cr, uid, qrcode_data)
        
        # Browse the qrcode
        qrcode = self.browse(cr, uid, qrcode_id)
        
        return qrcode  
    
    """ Return a qrcode image. """
    def print_qrcode(self, cr, uid, ids, current_qrcode):        
        # QR Code creation
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            border=1,
        )
        
        # QRCode content
        data = {
             "qr": current_qrcode.id,
             "se": current_qrcode.server_id,
             "pa": "None"
        }
        json_values = json.dumps(data)
        
        # QR Code filling
        qr.add_data(json_values)
        qr.make(fit=True)
        img = qr.make_image()

        # Get the QR Code stream
        output = StringIO.StringIO()
        img.save(output)
        content = output.getvalue()
        output.close()
        
        return content
    
    """ Attach the file to the concerned openerp object. """
    def attach_file(self, cr, uid, ids, document):
        # When I call the function from pyunit test
        if isinstance(ids, list):
            ids = ids[0]
        
        qrcode = self.read(cr, uid, ids, [], {})
        
        ir_attachment = self.pool.get('ir.attachment')
        ir_attachment.create(cr, uid, {
            'name': qrcode['filename'],
            'datas_fname': qrcode['filename'],
            'res_model': qrcode['oe_object'],
            'res_id': qrcode['oe_id'],
            'type': 'binary',
            'db_datas': document,
        })
            
bss_qrcode()