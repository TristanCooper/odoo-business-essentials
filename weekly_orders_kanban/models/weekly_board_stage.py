from odoo import models, fields

class WeeklyBoardStage(models.Model):
    _name = 'weekly.board.stage'
    _description = 'Weekly Board Stage'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    fold = fields.Boolean(string='Folded in Kanban', default=False)
