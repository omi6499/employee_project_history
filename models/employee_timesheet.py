from odoo import models, api, fields, _
from datetime import date
from odoo.exceptions import ValidationError
import calendar


class EmployeeTimesheet(models.Model):
    _name = "employee.timesheet"
    _description = "Employee Timesheet"

    name = fields.Char(string="Sequence", readonly=True, copy=False)
    start_date = fields.Date(string="Start date", required=True)
    end_date = fields.Date(string="End date", required=True)
    project_id = fields.Many2one("employee.project", string="Project", required=True)
    project_region_id = fields.Many2one("employee.project.region", compute="_compute_region_timesheet_lines", store=True, string="Project region")
    # project_region_id = fields.Many2one(related="project_id.project_region_id", string="Project region")
    timesheet_lines_ids = fields.One2many("employee.timesheet.line", "employee_timesheet_id", string="Timesheet Lines")
    start_day = fields.Integer(string="Start day", compute='_compute_start_end_day', store=True)
    end_day = fields.Integer(string="End day", compute='_compute_start_end_day', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pc', 'Project Controller'),
        ('client', 'Client'),
        ('om', 'Opration Manager'),
        ('dh', 'Division Head'),
        ('mrm', 'MRM'),
        ('hr', 'HR'),
        ('auditor', 'Auditor'),
        ('finance', 'Finance'),
        ('coo', 'COO'),
        ('approved', 'Approved')
    ], string="Status", default='draft')
    payslip_created = fields.Boolean('Is payslip created?', default=False)
    comments = fields.Text(string="Comments")
    payslip_count = fields.Integer(string="Payslip",
                                   compute='compute_payslip_count',
                                   default=0)
    accounting_analytic_id = fields.Many2one('account.analytic.account', string="Accounting Analytic")
    is_rotational_off = fields.Boolean(string="Is Rotational Off", compute="_compute_rotational_off", store=True)
    total_days = fields.Integer(string="Total Days", compute="_compute_start_end_day", store=True)

    @api.depends('project_id', 'state', 'project_id.is_rotational_off')
    def _compute_rotational_off(self):
        for rec in self:
            rot_off = rec.is_rotational_off
            if rec.state == 'draft':
                rot_off = rec.project_id.is_rotational_off
            rec.is_rotational_off = rot_off

    @api.constrains('start_date', 'end_date')
    def check_dates(self):
        for record in self:
            if record.start_date and record.end_date:
                if record.start_date.month != record.end_date.month:
                    raise ValidationError(_('Start Date and End Date should belong to the same month.'))
                if record.end_date < record.start_date:
                    raise ValidationError(_('End date must be later than the start date.'))
                conflicting_record = self.search([
                    ('id', '!=', record.id),
                    ('project_id', '=', record.project_id.id),
                    ('start_date', '<=', record.end_date),
                    ('end_date', '>=', record.start_date),
                ], limit=1)
                if conflicting_record:
                    raise ValidationError(_('Timesheet %s for project %s already exists with conflicting dates.' %(conflicting_record.name, record.project_id.name)))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('seq.employee.timesheet') or 'New'
        return super(EmployeeTimesheet, self).create(vals_list)

    @api.depends('start_date', 'end_date', 'project_id', 'project_id.employee_history_ids')
    def _compute_region_timesheet_lines(self):
        for rec in self.filtered(lambda l: l.state == 'draft'):
            rec.project_region_id = rec.project_id and rec.project_id.project_region_id.id or False
            if rec.project_id and rec.start_date and rec.end_date:
                employee_hist_records = rec.project_id.employee_history_ids.filtered(lambda l: l.date_start <= rec.end_date and \
                                                                                            (l.date_end and l.date_end >= rec.start_date or not l.date_end))
                lines_to_remove = rec.timesheet_lines_ids.filtered(lambda l: l.emp_history_id not in employee_hist_records)
                for hist_rec in employee_hist_records:
                    timesheet_line_vals = []
                    if not rec.timesheet_lines_ids.filtered(lambda l: l.emp_history_id.id == hist_rec.id):
                        timesheet_line_vals.append((0, 0, {
                            'emp_history_id': hist_rec.id,
                            'employee_id': hist_rec.employee_id.id,
                        }))
                    if timesheet_line_vals:
                        rec.timesheet_lines_ids = timesheet_line_vals

    @api.depends('start_date', 'end_date')
    def _compute_start_end_day(self):
        for rec in self:
            rec.start_day = rec.start_date.day if rec.start_date else 1
            rec.end_day = rec.end_date.day if rec.end_date else 31
            if rec.start_date:
                year = rec.start_date.year
                month = rec.start_date.month
                total_days_in_month = calendar.monthrange(year, month)[1]
            else:
                total_days_in_month = 0
            rec.total_days = total_days_in_month

    def action_reset(self):
        self.write({'state':'draft'})

    def action_pc(self):
        self.write({'state': 'pc'})

    def action_om(self):
        self.write({'state': 'om'})

    def action_dh(self):
        self.write({'state': 'dh'})

    def action_mrm(self):
        self.write({'state': 'mrm'})

    def action_hr(self):
        self.write({'state': 'hr'})

    def action_auditor(self):
        self.write({'state': 'auditor'})

    def action_finance(self):
        self.write({'state': 'finance'})

    def action_coo(self):
        self.write({'state': 'coo'})

    def action_client(self):
        self.write({'state': 'client'})

    def action_approved(self):
        self.write({'state': 'approved'})

    def action_generate_payslip(self):
        hr_payslip_obj = self.env['hr.payslip']
        for rec in self:
            year = rec.start_date.year
            month = rec.start_date.month
            # start_date_value = fields.Date.from_string('%s-%s-01'%(rec.start_date.year, rec.start_date.month))
            last_day = calendar.monthrange(year, month)[1]
            start_date_value = date(year, month, 1)
            end_date_value = date(year, month, last_day)
            for line in rec.timesheet_lines_ids:
                payslip_vals = {
                    'name': '%s - %s/%s'%(line.employee_id.name, line.employee_timesheet_id.start_date.month, line.employee_timesheet_id.start_date.year),
                    'employee_id': line.employee_id.id,
                    'company_id': line.employee_id.company_id.id,
                }
                existing_payslip_rec = hr_payslip_obj.search([
                    ('employee_id', '=', line.employee_id.id),
                    ('date_from', '=', start_date_value),
                    ('state', '=', 'draft')], limit=1, order='id desc')
                if existing_payslip_rec:
                    line.payslip_id = existing_payslip_rec
                    existing_payslip_rec.compute_sheet()
                else:
                    line.payslip_id = hr_payslip_obj.with_context(default_date_from=start_date_value, default_date_to=end_date_value).create(payslip_vals)
                    line.payslip_id.compute_sheet()

    def action_get_payslip_record(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payslips',
            'view_mode': 'tree,form',
            'res_model': 'hr.payslip',
            'domain': [('id', 'in', self.timesheet_lines_ids.mapped('payslip_id.id'))],
            'context': "{'create': False}"
        }

    def compute_payslip_count(self):
        for record in self:
            record.payslip_count = len(record.timesheet_lines_ids.filtered(lambda l: l.payslip_id))
            record.payslip_created = False if record.timesheet_lines_ids.filtered(lambda l: not l.payslip_id) else True
