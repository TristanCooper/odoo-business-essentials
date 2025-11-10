from odoo import models, fields, api
from datetime import timedelta

class ResPartner(models.Model):
    _inherit = 'res.partner'

    weekly_board_customer = fields.Boolean(
        string='Show on Weekly Board',
        help='Flag this partner to appear as a customer on the weekly board.'
    )

    weekly_stage_id = fields.Many2one(
        'weekly.board.stage',
        string='Weekly Board Stage',
        default=lambda self: self.env.ref('weekly_orders_kanban.stage_schedule').id,
        index=True,
        group_expand='_group_expand_weekly_stage_id',
    )

    @api.model
    def _group_expand_weekly_stage_id(self, stages, domain, order):
        return self.env['weekly.board.stage'].search([], order='sequence,id')

    # Helpers
    @api.model
    def _current_week_monday(self):
        today = fields.Date.context_today(self)
        weekday = today.weekday()  # Monday=0
        return today - timedelta(days=weekday)

    @api.model
    def _stage_to_weekday_index(self, stage_name):
        mapping = {
            'Monday': 0,
            'Tuesday': 1,
            'Wednesday': 2,
            'Thursday': 3,
            'Friday': 4,
        }
        return mapping.get(stage_name)

    def _schedule_call_for_stage(self):
        Activity = self.env['mail.activity']
        # Prefer phone call activity if present, else fallback to todo
        activity_type = self.env.ref('mail.mail_activity_data_call', raise_if_not_found=False) or \
                        self.env.ref('mail.mail_activity_data_todo')
        model_id = self.env['ir.model']._get('res.partner').id
        monday = self._current_week_monday()
        for partner in self:
            stage = partner.weekly_stage_id
            if not stage:
                continue
            idx = self._stage_to_weekday_index(stage.name)
            if idx is None:
                continue  # only schedule for weekday columns
            date_deadline = monday + timedelta(days=idx)
            # avoid duplicate for same day
            existing = Activity.search([
                ('res_model_id', '=', model_id),
                ('res_id', '=', partner.id),
                ('activity_type_id', '=', activity_type.id),
                ('date_deadline', '=', date_deadline),
            ], limit=1)
            if existing:
                continue
            Activity.create({
                'res_model_id': model_id,
                'res_id': partner.id,
                'activity_type_id': activity_type.id,
                'summary': 'Call',
                'user_id': partner.user_id.id or self.env.user.id,
                'date_deadline': date_deadline,
            })

    def write(self, vals):
        res = super().write(vals)
        if 'weekly_stage_id' in vals:
            # schedule calls for records whose stage moved to a weekday
            self._schedule_call_for_stage()
        return res
