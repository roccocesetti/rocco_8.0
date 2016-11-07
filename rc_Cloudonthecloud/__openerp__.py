# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
    'name': 'Gestione Servizi Cloud CloudonTheCloud',
    'version': '1.0',
    'category': 'Human Resources',
    'description': """
gestione completa dei Servizi Cloud.
=============================================================

    * Contratti,
    * Nodi, 
    * Scadenze,
    * Ricorrenze
    * Notifiche,
    * Fatturazione 

Possiamo assegnare al cliente tutte le attività cloud.
    """,
    'author': 'Rocco Cesetti ',
    'website': 'http://www.ideawork.it',
    'images': ['images/hr_contract.jpeg'],
    'depends': ['account','base','sale','payment','payment_paypal','crm','crm_claim'],
    'data': [
        'res_company_view.xml',
        'wizard/account_x_service_make_invoice.xml',
        'rc_hr_contract_view.xml',
        'views/report_account_x_service.xml',
        'security/account_x_service_security.xml',
        'security/ir.model.access.csv',
        'wizard/account_x_service_notify.xml',
        'account_x_service_report.xml',
        'edi/account_x_service_action_data.xml',
        'report/account_x_service_report_view.xml',
        'partner_import_view.xml',
        'portal_cloud_view.xml',
        'cloud_crm_view.xml',
        'crm_claim_view.xml',
        #'mail_thread_view.xml'
        
    ],
    'demo': [],
    'test': ['test/rc_wf_test_hr_contract.yml'],
    'installable': True,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
