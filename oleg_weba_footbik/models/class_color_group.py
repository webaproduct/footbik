from odoo import models, fields


class ClassColorGroup(models.Model):
    _name = "class.color.group"
    _description = "Class Color Group"

    def _compute_display_name(self):
        for rec in self:
            program = rec.class_program_id.name if rec.class_program_id else ""
            age = rec.class_age_id.name if rec.class_age_id else ""
            rec.display_name = f"{program} -> {age}"

    class_program_id = fields.Many2one(
        comodel_name="class.program", string="Program", index=True, required=True)
    class_age_id = fields.Many2one(
        comodel_name="class.age", string="Age", index=True, required=True)
    color = fields.Char(string="Color", required=True)
