# -*- coding: utf-8 -*-
#############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012-Today Serpent Consulting Services Pvt. Ltd.
#    (<http://www.serpentcs.com>)
#    Copyright (C) 2004 OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
#############################################################################

{
    "name": "Hotel Management",
    "version": "0.10",
    "author": "Serpent Consulting Services Pvt. Ltd., OpenERP SA,\
    Odoo Community Association (OCA)",
    "images": [],
    "license": "",
    "category": "Generic Modules/Hotel Management",
    "website": "http://www.serpentcs.com",
    "depends": ["sale_stock", "point_of_sale", "hotel_report_layout"],
    "demo": ["views/hotel_data.xml"],
    "data": [
        "security/hotel_security.xml",
        "security/ir.model.access.csv",
        "views/hotel_sequence.xml",
        "views/hotel_folio_workflow.xml",
        "views/hotel_report.xml",
        "views/report_hotel_management.xml",
        "views/hotel_view.xml",
        "wizard/hotel_wizard.xml",
    ],
    'css': ["static/src/css/room_kanban.css"],
    "auto_install": False,
    "installable": True
}
