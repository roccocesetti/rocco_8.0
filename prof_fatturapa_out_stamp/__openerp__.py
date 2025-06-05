# -*- coding: utf-8 -*-
# Copyright 2018 rocco cesetti
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "Italian Localization - Fattura elettronica - Integrazione bollo",
    "summary": "Modulo ponte tra emissione fatture elettroniche trust e imposta di "
               "bollo",
    "version": "8.0.1.0.0",
    "development_status": "Beta",
    "category": "Hidden",
    "website": "https://ideawork.link",
    "author": "Rocco cesetti, Odoo Community Association (OCA)",
    "maintainers": ["roccocesetti"],
    "license": "LGPL-3",
    "application": False,
    "installable": True,
    "auto_install": True,
    "depends": [
        "prof_fatturapa_out",
        "l10n_it_account_stamp",
    ],
    "data": [
    ],
}
