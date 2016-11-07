# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012-Today OpenERP SA (<http://www.openerp.com>)
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
##############################################################################

from openerp import tools
from openerp.osv import osv
from openerp.osv import fields
from openerp.tools.translate import _


class invite_wizard(osv.osv_memory):
    _inherit = 'mail.wizard.invite'
    def default_get(self, cr, uid, fields, context=None):
        result = super(invite_wizard, self).default_get(cr, uid, fields, context=context)
        user_name = self.pool.get('res.users').name_get(cr, uid, [uid], context=context)[0][1]
        model = result.get('res_model')
        res_id = result.get('res_id')
        if 'message' in fields and model and res_id:
            ir_model = self.pool.get('ir.model')
            model_ids = ir_model.search(cr, uid, [('model', '=', self.pool[model]._name)], context=context)
            model_name = ir_model.name_get(cr, uid, model_ids, context=context)[0][1]

            document_name = self.pool[model].name_get(cr, uid, [res_id], context=context)[0][1]
            message = _('<div><p>Ciao,inviamo questa comunicazione per informarti che:</p><p>%s ti invita a seguire la nuova %s denominata: %s.<p></div>') % (user_name, model_name, document_name)
            message=message+'<p>Questo nuovo servizio ti permettera di ricevere notifiche sugli avanzamenti della tua attivita e di poter interagire con il nostro staff. Puoi: </p><br>'
            message=message+'<p>1- Accedere al portale (cerca nella cartella posta in arrivo o spam della tua mail, la comunicazione inviata, precedentemente a '
            message=message+'questo messaggio, per l'+'"'+'accesso al portale di Cloudonthecloud ) e selezionare la voce PROGETTO o cliccare sul link '
            message=message+'ATTIVITA/PROGETTO in fondo a questa mail, SOLO dopo aver fatto un primo accesso al portale.</p><br>'
            message=message+'<p>(se non trovi questa mail passa al punto 2)</p><br>'
            message=message+'<p></p><br>'
            message=message+'<p>2- Senza effettuare l'+'"'+'accesso al portale riceverai comunque, tramite mail, gli avanzamenti lavori e potrai, quando vuoi, e quando richiesto, intervenire '
            message=message+'semplicemente rispondendo alla mail ricevuta (si raccomanda di fare un RISPONDI e non un RISPONDI A TUTTI lasciando invariato '
            message=message+' l'+'"'+'indirizzo mail del destinatario ) </p><br>'
            message=message+'<p></p><br>'
            message=message+'<p>Per qualunque informazione rimaniamo disponibili - info@cloudonthecloud.com </p><br>'
            result['message'] = message
        elif 'message' in fields:
            message = _('<div><p>Ciao,inviamo questa comunicazione per informarti che:</p><p>%s ti invita a seguire la nuova %s denominata: </p></div>') % user_name
            message=message+'<p>Questo nuovo servizio ti permettera di ricevere notifiche sugli avanzamenti della tua attivita e di poter interagire con il nostro staff. Puoi: </p><br>'
            message=message+'<p>1- Accedere al portale (cerca nella cartella posta in arrivo o spam della tua mail, la comunicazione inviata, precedentemente a '
            message=message+'questo messaggio, per l'+'"'+'accesso al portale di Cloudonthecloud ) e selezionare la voce PROGETTO o cliccare sul link '
            message=message+'ATTIVITA/PROGETTO in fondo a questa mail, SOLO dopo aver fatto un primo accesso al portale.'
            message=message+'(se non trovi questa mail passa al punto 2)</p><br>'
            message=message+'<p></p><br>'
            message=message+'<p>2- Senza effettuare l'+'"'+'accesso al portale riceverai comunque, tramite mail, gli avanzamenti lavori e potrai, quando vuoi, intervenire '
            message=message+'semplicemente rispondendo alla mail ricevuta (si raccomanda di fare un RISPONDI e non un RISPONDI A TUTTI lasciando invariato '
            message=message+' l'+"'"+'indirizzo mail del destinatario ) </p><br>'
            message=message+'<p></p><br>'
            message=message+'<p>Per qualunque informazione rimaniamo disponibili - info@cloudonthecloud.com </p><br>'
            result['message'] = message
        return result


    def add_followers(self, cr, uid, ids, context=None):
        for wizard in self.browse(cr, uid, ids, context=context):
            model_obj = self.pool[wizard.res_model]
            document = model_obj.browse(cr, uid, wizard.res_id, context=context)

            # filter partner_ids to get the new followers, to avoid sending email to already following partners
            new_follower_ids = [p.id for p in wizard.partner_ids if p not in document.message_follower_ids]
            model_obj.message_subscribe(cr, uid, [wizard.res_id], new_follower_ids, context=context)

            ir_model = self.pool.get('ir.model')
            model_ids = ir_model.search(cr, uid, [('model', '=', model_obj._name)], context=context)
            model_name = ir_model.name_get(cr, uid, model_ids, context=context)[0][1]

            # send an email if option checked and if a message exists (do not send void emails)
            if wizard.send_mail and wizard.message and not wizard.message == '<br>':  # when deleting the message, cleditor keeps a <br>
                # add signature
                # FIXME 8.0: use notification_email_send, send a wall message and let mail handle email notification + message box
                signature_company = self.pool.get('mail.notification').get_signature_footer(cr, uid, user_id=uid, res_model=wizard.res_model, res_id=wizard.res_id, context=context)
                wizard.message = tools.append_content_to_html(wizard.message, signature_company, plaintext=False, container_tag='div')

                # send mail to new followers
                # the invite wizard should create a private message not related to any object -> no model, no res_id
                mail_mail = self.pool.get('mail.mail')
                mail_id = mail_mail.create(cr, uid, {
                    'model': wizard.res_model,
                    'res_id': wizard.res_id,
                    'record_name': document.name_get()[0][1],
                    'email_from': self.pool['mail.message']._get_default_from(cr, uid, context=context),
                    'reply_to': self.pool['mail.message']._get_default_from(cr, uid, context=context),
                    'subject': _('CLOUDONTHECLOUD TI INVITA A SEGUIRE: nome attività Cloudonthecloud LTD %s: %s') % (model_name, document.name_get()[0][1]),
                    'body_html': '%s' % wizard.message,
                    'auto_delete': True,
                    'message_id': self.pool['mail.message']._get_message_id(cr, uid, {'no_auto_thread': True}, context=context),
                    'recipient_ids': [(4, id) for id in new_follower_ids]
                }, context=context)
                mail_mail.send(cr, uid, [mail_id], context=context)
        return {'type': 'ir.actions.act_window_close'}
