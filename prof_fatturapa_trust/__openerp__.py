# -*- coding: utf-8 -*-
# Copyright (C) 2014 Davide Corio
# Copyright 2015-2016 Lorenzo Battistini - Agile Business Group

{
    'name': 'Italian Localization - FatturaPA - trust patch',
    'version': '8.0.2.0.0',
    'category': 'Localization/Italy',
    'summary': 'Electronic invoices emission ref 1.2',
    'author': 'Rocco Cesetti, '
              'Odoo Community Association (OCA)',
    'website': 'http://www.ideawork.link',
    'license': 'AGPL-3',
    "depends": ['base',
        'prof_fatturapa_out',
        ],
    "data": [
        'views/attachment_view.xml',
    ],
    "test": [],
    "installable": True,
    'external_dependencies': {
                'python': ['requests_toolbelt'],
    }
}
