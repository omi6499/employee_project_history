"""Wizard for generating employee service completion report."""

from datetime import datetime

from odoo import api, fields, models


class EmployeeServiceCompletionWizard(models.TransientModel):
    """Transient model used to select month and year for the report."""

    _name = "employee.service.completion.wizard"
    _description = "Employee Service Completion Report Wizard"

    @api.model
    def _get_year_selection(self):
        """Provide a small range around the current year for selection."""
        current_year = datetime.today().year
        return [
            (str(year), str(year))
            for year in range(current_year - 1, current_year + 2)
        ]

    month = fields.Selection([
        ('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'),
        ('5', 'May'), ('6', 'June'), ('7', 'July'), ('8', 'August'),
        ('9', 'September'), ('10', 'October'), ('11', 'November'),
        ('12', 'December')
    ], string='Month', required=True,
        default=lambda self: str(datetime.today().month))
    year = fields.Selection(
        selection=_get_year_selection,
        string='Year',
        required=True,
        default=lambda self: str(datetime.today().year),
    )

    def action_generate_report(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/download/service_completion_report?wiz_id=%s' % self.id,
            'target': 'self'
        }
