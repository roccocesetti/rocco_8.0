# -*- encoding: utf-8 -*-
#
#
#    Copyright (C) 2010-2011 OpenERP Italian Community
#    http://www.openerp-italia.org>
#    All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
{
    'name': 'Italian Localisation - Base',
    'version': '0.1',
    'category': 'Localisation/Italy',
    'description': """Italian Localization module - Base version

Funcionalities:

- Comuni italiani
- res.partner.title italiani
- Province e regioni
- Automatistmi su res.partner.address

""",
    'author': 'OpenERP Italian Community',
    'website': 'http://www.openerp-italia.org',
    'license': 'AGPL-3',
    "depends": ['base'],
    "init_xml": [
    ],
    "update_xml": ['partner/partner_view.xml',
                   "security/ir.model.access.csv",
                   'partner/data/res.region.csv',
                   'partner/data/res.province.csv',
                   'partner/data/res.city.csv',
                   'partner/data/res.partner.title.csv'],
    "demo_xml": [],
    "active": False,
    "installable": True
}

# http://www.istat.it/strumenti/definizioni/comuni/
# i dati dovrebbero essere sincronizzati con questi
