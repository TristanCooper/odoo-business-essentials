from odoo import models, fields, api

class WeeklyBoardItem(models.Model):
    _name = 'weekly.board.item'
    _description = 'Weekly Customer Board Item'
    _order = 'sequence, id'

    name = fields.Char(string='Title', compute='_compute_name', store=True)
    customer_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        domain=[('weekly_board_customer', '=', True), '|', ('is_company', '=', True), ('parent_id', '=', False)],
        index=True,
        ondelete='restrict',
    )
    stage_id = fields.Many2one(
        'weekly.board.stage',
        string='Stage',
        required=True,
        index=True,
        ondelete='restrict',
        default=lambda self: self.env.ref('weekly_orders_kanban.stage_schedule').id,
        group_expand='_group_expand_stage_ids',
    )
    notes = fields.Text(string='Notes')
    sequence = fields.Integer(default=10)
    phone = fields.Char(string='Phone', related='customer_id.phone', store=False)
    email = fields.Char(string='Email', related='customer_id.email', store=False)

    _sql_constraints = [
        ('uniq_customer', 'unique(customer_id)', 'This customer already has a board item.'),
    ]

    @api.depends('customer_id')
    def _compute_name(self):
        for rec in self:
            name = rec.customer_id.display_name if rec.customer_id else 'Item'
            rec.name = name

    @api.model
    def _group_expand_stage_ids(self, stages, domain, order):
        return self.env['weekly.board.stage'].search([], order='sequence,id')

    @api.model
    def ensure_all_records(self):
        schedule_stage = self.env.ref('weekly_orders_kanban.stage_schedule')
        partners = self.env['res.partner'].search([
            ('weekly_board_customer', '=', True),
            '|', ('is_company', '=', True), ('parent_id', '=', False),
        ])
        existing = self.search_read([], ['customer_id'])
        existing_partner_ids = {rec['customer_id'][0] for rec in existing if rec.get('customer_id')}
        to_create = []
        for p in partners:
            if p.id not in existing_partner_ids:
                to_create.append({
                    'customer_id': p.id,
                    'stage_id': schedule_stage.id,
                    'name': p.display_name,
                })
        if to_create:
            self.create(to_create)
        return True

    @api.model
    def ensure_records_and_open(self):
        self.ensure_all_records()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Weekly Customer Board',
            'res_model': 'weekly.board.item',
            'view_mode': 'kanban,tree,form',
            'context': {'search_default_group_by_stage_id': 1},
        }

    @api.model
    def reset_all_to_schedule(self):
        schedule_stage = self.env.ref('weekly_orders_kanban.stage_schedule')
        items = self.search([])
        items.write({'stage_id': schedule_stage.id})
        return True

    def action_open_customer(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Customer',
            'res_model': 'res.partner',
            'res_id': self.customer_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

