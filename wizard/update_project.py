from odoo import _, fields, models
from datetime import timedelta


class UpdateEmployeeProject(models.TransientModel):
    _name = 'update.employee.project'
    _description = 'Update Employee Project'

    employee_id = fields.Many2one('hr.employee', string='Employee')
    old_project_id = fields.Many2one('employee.project', string='Old Project', related='employee_id.employee_project_id')
    project_id = fields.Many2one('employee.project', string='Project', domain="[('id', '!=', old_project_id)]")
    change_reason_id = fields.Many2one('project.history.reason', string='Reason')
    change_designation_id = fields.Many2one('project.history.designation', string='Designation')

    def update_employee_project(self):
        # Update project in employee
        self.employee_id.employee_project_id = self.project_id.id

        # Update the previous project history record date_end
        previous_project_history = (
            self.employee_id.employee_project_history_ids.filtered(
                lambda rec: not rec.date_end))
        if previous_project_history:
            previous_project_history.date_end = fields.Date.today() - timedelta(days=1)

        # update project history with new line
        self.employee_id.employee_project_history_ids = [(0, 0, {
            'employee_project_id': self.project_id.id,
            'date_start': fields.Date.today(),
            'name': self.project_id.name,
            'description': self.project_id.description,
            'employee_project_region_id': self.project_id.project_region_id.id,
            'change_reason_id': self.change_reason_id.id,
            'designation_id': self.change_designation_id.id
        })]
