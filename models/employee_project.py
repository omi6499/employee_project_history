from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class EmployeeProject(models.Model):
    _name = 'employee.project'
    _description = 'Employee Project'

    name = fields.Char(string='Project Name', required=True)
    project_region_id = fields.Many2one('employee.project.region', string='Project Region')
    description = fields.Text(string='Description')
    project_controler_id = fields.Many2one("res.users", string="Project Controler",)
    operation_manager_id = fields.Many2one("res.users", string="Operation Manager")
    division_head_id = fields.Many2one("res.users", string="Division head")
    mrm_id = fields.Many2one("res.users", string="MRM")
    hr_id = fields.Many2one("res.users", string="HR")
    auditor_id = fields.Many2one("res.users", string="Auditor")
    finance_id = fields.Many2one("res.users", string="Finance")
    coo_id = fields.Many2one("res.users", string="COO")
    client_id = fields.Many2one("res.partner", string="Client")
    is_rotational_off = fields.Boolean(string="Is Rotational Off ?")
    employee_history_ids = fields.One2many('employee.project.history', 'employee_project_id', string='Employee History')
    company_analytic_account_ids = fields.One2many('company.analytic.account', 'project_analytic_id',
        string="Company Analytic Account")
    day_selection = fields.Selection([('present', 'P'), ('overtime', 'OT'), ('absent', 'A'),
        ('paid_off', 'OFF'), ('sick', 'SL'), ('weekoff', 'F'), ('leave', 'VL'), ('surplus', 'SP'),
        ('rotational_off', 'ROT'), ('unpaid_vacation', 'VL-D')], string="Day Selection")

class CompanyAnalyticAccount(models.Model):
    _name = 'company.analytic.account'
    _description = "Company Analytic Account"

    project_analytic_id = fields.Many2one('employee.project', string="Employee Project")
    company_id = fields.Many2one('res.company', string="Company")
    analytic_precision = fields.Integer(
        store=False,
        default=lambda self: self.env['decimal.precision'].precision_get("Percentage Analytic"))
    analytic_distribution = fields.Json('Analytic Distribution')

class EmployeeProjectHistory(models.Model):
    _name = 'employee.project.history'
    _description = 'Employee Project History'
    _order = "date_end desc, date_start desc"

    def _default_line_type_id(self):
        return self.env.ref('employee_project_history.employee_project_type_demo')

    name = fields.Char(string='Project Name')
    description = fields.Text(string='Description')
    display_type = fields.Selection([('classic', 'Classic')], string="Display Type", default='classic')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    employee_project_id = fields.Many2one('employee.project', string='Project')
    employee_project_region_id = fields.Many2one('employee.project.region', string='Project Region')
    change_reason_id = fields.Many2one('project.history.reason', string='Reason')
    designation_id = fields.Many2one('project.history.designation', string='Designation')
    date_start = fields.Date(string='Start Date')
    date_end = fields.Date(string='End Date')
    line_type_id = fields.Many2one('employee.project.type', string="Type", default=_default_line_type_id)

    @api.constrains('date_start', 'date_end')
    def check_dates(self):
        for rec in self:
            if rec.date_end and rec.date_end < rec.date_start:
                raise ValidationError(_('End date should be later than the start date.'))


class EmployeeProjectType(models.Model):
    _name = 'employee.project.type'
    _description = 'Employee Project Type'

    name = fields.Char(string='Project Type')


class EmployeeProjectRegion(models.Model):
    _name = 'employee.project.region'
    _description = 'Employee Project Region'

    name = fields.Char()


class projectHistoryDesignation(models.Model):
    _name = 'project.history.designation'
    _description = 'Project History Designation'

    name = fields.Char()


class projectHistoryReason(models.Model):
    _name = 'project.history.reason'
    _description = 'Project History Reason'

    name = fields.Char()


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    @api.depends('company_id')
    def _compute_display_name(self):
        for acc in self:
            acc.display_name = f"{acc.name} - ( {acc.company_id.name} )"


class EmployeeCategory(models.Model):
    _name = 'employee.category'
    _description = 'Employee Category'

    name = fields.Char(string="Name", required=True)
