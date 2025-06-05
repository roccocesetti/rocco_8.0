# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright © 2016 Techspawn Solutions. (<http://techspawn.in>).
#    Copyright (C) 2004-2015 OpenERP S.A. (<http://www.odoo.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Ornate Shop Module',
    'version': '1.0',
    'category': 'Theme/Ecommerce',
    'author': 'Techspawn Solutions',
    'website': 'http://techspawn.in',
    'depends': ['website','product', 'sale', 'website_sale'],
    'summary': "Elegant Module for Website Shop",
    'description':"""
    This module will combine the Collapsible Product Category and Product Multi-image for a better user experience along side with clear cleaner homepage design.
    """,
    'data': [
        'views/categories.xml',
        'views/theme.xml',
        'views/product_images.xml',
        'views/config.xml',
        'views/product.xml',

    ],
    'images': [
        'images/main.jpg',
    ],
    "installable": True,
    "autoinstall": False,
}

