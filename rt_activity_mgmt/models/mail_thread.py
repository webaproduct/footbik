# -*- coding: utf-8 -*-

from odoo import models


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    # ---------------------------------------------------------
    # Messaging
    # ---------------------------------------------------------

    def message_post_with_source(self, source_ref, render_values=None,
                                 message_type='notification',
                                 subtype_xmlid=False, subtype_id=False,
                                 **kwargs):
        
        if render_values and source_ref == 'mail.message_activity_done' and subtype_xmlid == 'mail.mt_activities':
            values = render_values or dict()
            if values and values.get('activity', False) and kwargs.get('subject', False) == False:
                activity = values.get('activity')
                if len(activity) == 1 and activity.summary:
                    kwargs.update({
                        'subject': activity.summary
                    })

        return super(MailThread,self).message_post_with_source(
            source_ref=source_ref,
            render_values=render_values,
            message_type=message_type,
            subtype_xmlid=subtype_xmlid,
            subtype_id=subtype_id, 
            **kwargs)
