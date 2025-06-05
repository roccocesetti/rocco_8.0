# -*- coding: utf-8 -*-
# Copyright (C) 2014 Davide Corio
# Copyright 2015-2016 Lorenzo Battistini - Agile Business Group

{
    'name': 'Italian Localization - FatturaPA - Emission',
    'version': '8.0.2.0.0',
    'category': 'Localization/Italy',
    'summary': 'Electronic invoices emission ref 1.2',
    'author': 'Rocco Cesetti, '
              'Odoo Community Association (OCA)',
    'website': 'http://www.ideawork.link',
    'license': 'AGPL-3',
    "depends": ['base',
        'base',
        'l10n_it_fatturapa',
        'l10n_it_fatturapa_out',
        'l10n_it_fatturapa_in',
        'l10n_it_split_payment',
        ],
    "data": [
        'views/attachment_view.xml',
        'views/account_view.xml',
        'wizard/wizard_export_fatturapa_view.xml',
        'wizard/wizard_import_fatturapa_view.xml',
        'security/ir.model.access.csv',
    ],
    "test": [],
    "installable": True,
    'external_dependencies': {
        'python': ['unidecode'],
    }
}
