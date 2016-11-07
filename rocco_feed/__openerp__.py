# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012 Bas ubbels (<http://www.ubbels.com>).
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
{
    'name' : 'feed news',
    'author' : 'Rocco Cesetti',
    'website' : "http://www.ideawork.it",
    'version' : "1.0",
    'depends' : ['base',],
    'description': """
	Questo modulo legge i feed
	""",        
    'category' : 'Tools',
    'data': ['view/faxsend_view.xml',
             'data/faxsend_data.xml',               
             'security/res_groups.xml', 
             'security/ir.model.access.csv'],
    'demo': [],
    'test': [],
    'active': False,
    'installable': True,

}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

