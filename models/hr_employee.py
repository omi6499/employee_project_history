from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    employee_number = fields.Char(string='Employee Number', default=_("NEW"))
    employee_project_history_ids = fields.One2many('employee.project.history', 'employee_id',
                                                   string='Project History')
    employee_project_id = fields.Many2one('employee.project', string='Project')
    employee_project_region_id = fields.Many2one('employee.project.region', 'Project Region',
                                                 related="employee_project_id.project_region_id")
    user_has_project_hist_edit = fields.Boolean(compute='_compute_user_has_group_admin')
    vaction_history_ids = fields.One2many('vaction.history', 'employee_id', string="Vaction History")
    employee_category_id = fields.Many2one('employee.category', string="Employee Category")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['employee_number'] = self.env['ir.sequence'].next_by_code(
                'sequence.hr.employee') or "(NEW)"
        return super(HrEmployee, self).create(vals_list)

    def action_open_project_update_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Update Employee Project'),
            'res_model': 'update.employee.project',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_employee_id': self.id}
        }

    def _compute_user_has_group_admin(self):
        user_has_project_hist_edit = self.user_has_groups('employee_project_history.group_project_history_editable')
        for rec in self:
            rec.user_has_project_hist_edit = user_has_project_hist_edit

    @api.constrains('employee_project_history_ids', 'employee_project_history_ids.date_start', 'employee_project_history_ids.date_end')
    def check_conflicting_dates(self):
        for rec in self:
            for hist_rec in rec.employee_project_history_ids:
                conflicting_record = rec.employee_project_history_ids.filtered(lambda l: l.id != hist_rec.id and \
                                        (hist_rec.date_end and l.date_end and l.date_end >= hist_rec.date_start and l.date_start <= hist_rec.date_end or\
                                        hist_rec.date_end and not l.date_end and l.date_start <= hist_rec.date_end or\
                                        not hist_rec.date_end and l.date_end and l.date_end >= hist_rec.date_start or\
                                        not hist_rec.date_end and not l.date_end))
                if conflicting_record:
                    raise ValidationError(_("Projects '%s' and '%s' Dates are overlapping." %(hist_rec.name, conflicting_record[0].name)))


class VactionHistory(models.Model):
    _name = 'vaction.history'
    _description = 'Vaction History'

    employee_id = fields.Many2one("hr.employee", string="Employee")
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    total_days = fields.Integer(string="Total Days", compute="_compute_total_days", store=True)

    @api.depends('start_date', 'end_date')
    def _compute_total_days(self):
        for record in self:
            if record.start_date and record.end_date:
                days = (record.end_date - record.start_date).days + 1
                record.total_days = max(days, 0)
            else:
                record.total_days = 0
