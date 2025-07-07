from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, date
from dateutil.relativedelta import relativedelta


class EmployeeCategoryReportWizard(models.TransientModel):
    _name = 'employee.category.report.wizard'
    _description = 'Employee Category Report Wizard'

    def _get_year_selections(self):
        payslips = self.env['hr.payslip'].search([('state', '=', 'done')])
        years = list(set(payslip.date_from.year for payslip in payslips if payslip.date_from))
        years.sort()
        return [(str(year), str(year)) for year in years]

    wizard_type = fields.Selection([('summary', 'Summary'), ('region', 'Region')], string="Wizard Type")
    month = fields.Selection([
    ('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'), ('5', 'May'), ('6', 'June'),
    ('7', 'July'), ('8', 'August'), ('9', 'September'), ('10', 'October'), ('11', 'November'),
    ('12', 'December')], string="Month")
    year = fields.Selection(selection=_get_year_selections, string="Year")
    employee_region_id = fields.Many2one('employee.project.region', string="Region")
    employee_category_ids = fields.Many2many('employee.category', string="Categories",
        default=lambda self: self.env['employee.category'].search([]))
    employee_project_region_ids = fields.Many2many('employee.project.region', string="Regions",
        default=lambda self: self.env['employee.project.region'].search([]))

    @api.constrains('wizard_type', 'employee_project_region_ids', 'employee_category_ids')
    def _check_summary_selection_constraints(self):
        for rec in self:
            if rec.wizard_type == 'summary':
                if len(rec.employee_project_region_ids) <= 1:
                    raise ValidationError("Please select more than one Employee Region for Summary report.")
                if len(rec.employee_category_ids) <= 1:
                    raise ValidationError("Please select more than one Employee Category for Summary report.")

    def action_generate_report(self):
        date_from = datetime(int(self.year), int(self.month), 1)
        date_to = (date_from + relativedelta(months=1)) - relativedelta(days=1)

        filtered_payslips = self.env['hr.payslip'].search([
            ('state', '=', 'done'),
            ('date_from', '>=', date_from.date()),
            ('date_to', '<=', date_to.date()),
            ('employee_id.employee_project_region_id', '=', self.employee_region_id.id),
            ('employee_id.employee_category_id', 'in', self.employee_category_ids.ids),
        ])

        if not filtered_payslips:
            raise ValidationError(_("Record Not Found!"))

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/download/xlsx_report?wiz_id=%s'%self.id,
            'target': 'self'
        }

    def action_summary_report(self):
        date_from = datetime(int(self.year), int(self.month), 1)
        date_to = (date_from + relativedelta(months=1)) - relativedelta(days=1)
        payslips = self.env['hr.payslip'].search([
            ('state', '=', 'done'),
            ('date_from', '>=', date_from.date()),
            ('date_to', '<=', date_to.date()),
            ('employee_id.employee_project_region_id', 'in', self.employee_project_region_ids.ids),
            ('employee_id.employee_category_id', 'in', self.employee_category_ids.ids),
        ])

        if not payslips:
            raise ValidationError(_("Record Not Found!"))

        return {
        'type': 'ir.actions.act_url',
        'url': 'web/download/summary_report?wiz_id=%s'%self.id,
        'target': 'self'
        }
