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
    'name' : 'prof_fattacc',
    'author' : 'Rocco Cesetti',
    'website' : "http://www.ideawork.link",
    'version' : "1.0",
    'depends' : ['stock','account','sale','l10n_it_ddt'],
    'description': """
	profilazione  Fattura accomagnatoria
	""",        
    'category' : 'Tools',
    'sequence': 1,
    'data': [#'security/res_groups.xml',               
             #'security/ir.model.access.csv',
             'prof_fattacc_view.xml',
             'view/report_invoice.xml',
             'view/account_report.xml',             
            ],
    'demo': [],
    'test': [],
    'active': False,
    'application': True,
    'installable': True,

}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

