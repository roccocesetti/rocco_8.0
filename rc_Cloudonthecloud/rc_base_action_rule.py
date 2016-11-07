# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2013 OpenERP S.A. <http://www.openerp.com>
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

from openerp.addons.base_action_rule.base_action_rule import get_datetime
from openerp.osv import fields, osv


class base_action_rule(osv.Model):
    """ Add resource and calendar for time-based conditions """
    _name = 'base.action.rule'
    _inherit = ['base.action.rule']
    def _check_delay(self, cr, uid, action, record, record_dt, context=None):
        """ Override the check of delay to try to use a user-related calendar.
        If no calendar is found, fallback on the default behavior. """
        return super(base_action_rule, self)._check_delay(cr, uid, action, record, record_dt, context=context)
