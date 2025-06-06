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

{
    'name': 'prof WooCommerce Connector',
    'version': '8.0.1.0.1',
    'category': 'customized',
    'description': """Profile WooCommerce Connector.""",
    'author': 'Tech Receptives',
    'maintainer': 'ideasoft',
    'website': 'http://www.ideawork.link',
    'depends': ['base', 'connector', 'connector_ecommerce','connector_woocommerce'],
    'installable': True,
    'auto_install': False,
    'data': [
        #"security/ir.model.access.csv",
        "views/backend_view.xml",
    ],
    'external_dependencies': {
        'python': ['woocommerce'],
    },
    'js': [],
    'application': True,
    "sequence": 3,
}
