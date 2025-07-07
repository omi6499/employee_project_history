from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta
import calendar
from datetime import datetime


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    attendance_days = fields.Json(compute='compute_attendance_days', string="Attendance days", store=True)
    timesheet_lines_ids = fields.One2many('employee.timesheet.line', 'payslip_id', string='Payslips', ondelete='restrict')
    company_id = fields.Many2one(default=None)
    entries = fields.Selection([('completed', 'Completed'), ('not_completed', 'Not Completed')],
        string="Entries", compute="_compute_remaining_entries", store=True, readonly=False)
    remaining_entries = fields.Integer(compute="_compute_remaining_entries", string="Remaining Entries", store=True)
    payment_type = fields.Selection([('bank', 'Bank'), ('cash', 'Cash')], string="Payment Type")
    note = fields.Html(string="Note")
    employee_payment = fields.Selection(related="employee_id.x_studio_mode_of_payment", string="Payment Mode",
        readonly=True, store=True)

    def action_payslip_draft_wizard(self):
        return {
            'name': _('Create Draft Entry'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'hr.payslip.draft.wizard',
            'view_id': self.env.ref('employee_project_history.view_payslip_draft_wizard').id,
            'target': 'new'
        }

    @api.depends('employee_id', 'date_from', 'date_to', 'timesheet_lines_ids')
    def compute_attendance_days(self):
        for rec in self:
            if rec.timesheet_lines_ids and rec.employee_id and rec.date_from and rec.date_to:
                days_excluding_friday = []
                year = rec.date_from.year
                month = rec.date_from.month
                total_days_in_month = calendar.monthrange(year, month)[1]
                for day in range(1, total_days_in_month + 1):
                    weekday = calendar.weekday(year, month, day)
                    if weekday != 4:
                        days_excluding_friday.append(day)
                rec.attendance_days = {'day_%s'%i: 'absent' for i in days_excluding_friday if i != 31}
                for timesheet_line in rec.timesheet_lines_ids:
                    attendance_days_dict = rec.attendance_days or {}
                    attendance_days_dict.update({'day_%s'%i: getattr(timesheet_line, 'day_%s'%i) for i in days_excluding_friday if getattr(timesheet_line, 'day_%s'%i)})
                    if total_days_in_month == 31 and attendance_days_dict.get('day_31', False) and attendance_days_dict.get('day_31') not in ['absent', 'surplus']:
                        attendance_days_dict.pop('day_31')
                    rec.attendance_days = attendance_days_dict

    @api.depends('employee_id', 'date_from', 'date_to', 'timesheet_lines_ids')
    def _compute_remaining_entries(self):
        for rec in self:
            remaining_days = 0
            if rec.employee_id and rec.date_from and rec.date_to:
                total_days = (rec.date_to - rec.date_from).days + 1
                timesheet_entries = rec.timesheet_lines_ids.filtered(lambda l: l.employee_id == rec.employee_id)
                entered_days = sum(
                    1 for i in range(1, total_days + 1)
                    if any(getattr(line, f'day_{i}', False) for line in timesheet_entries)
                )
                remaining_days = total_days - entered_days
                rec.entries = 'completed' if remaining_days == 0 else 'not_completed'

    @api.depends('employee_id', 'contract_id', 'struct_id', 'date_from', 'date_to', 'attendance_days')
    def _compute_worked_days_line_ids(self):
        return super(HrPayslip, self)._compute_worked_days_line_ids()

    def _get_worked_day_lines_values(self, domain=None):
        worked_days_line_vals_list = []
        self.ensure_one()
        res = []
        hours_per_day = self._get_worked_day_lines_hours_per_day()
        work_hours = self.contract_id.get_work_hours(self.date_from, self.date_to, domain=domain)
        if self.attendance_days:
            day_values = list(self.attendance_days.values())
            # for Present and Overtime
            deduct_present = 1 if self.attendance_days.get('day_31', False) else 0 # If 31st day is absent. then deduct 1 present and add absent.
            if day_values.count('present') or day_values.count('overtime') or day_values.count('rotational_off'):
                worked_days_line_vals_list.append({
                    'sequence': len(worked_days_line_vals_list) + 1,
                    'work_entry_type_id': self.env.ref('hr_work_entry.work_entry_type_attendance').id,
                    'name': 'Present Days',
                    'number_of_days': day_values.count('present') + day_values.count('overtime') + day_values.count('rotational_off') - deduct_present,
                    'number_of_hours': (day_values.count('present') + day_values.count('overtime') + day_values.count('rotational_off') - deduct_present) * hours_per_day,
                })
            # for Paid off, Vacation leave and Sick leave
            if day_values.count('paid_off') or day_values.count('leave') or day_values.count('sick'):
                worked_days_line_vals_list.append({
                    'sequence': len(worked_days_line_vals_list) + 1,
                    'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_legal_leave').id,
                    'name': 'Paid Off Days',
                    'number_of_days': day_values.count('paid_off') + day_values.count('leave') + day_values.count('sick'),
                    'number_of_hours': (day_values.count('paid_off') + day_values.count('leave') + day_values.count('sick')) * hours_per_day,
                })
            # for absent
            if day_values.count('absent') or day_values.count('surplus') or day_values.count('unpaid_vacation'):
                worked_days_line_vals_list.append({
                    'sequence': len(worked_days_line_vals_list) + 1,
                    'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_unpaid_leave').id,
                    'name': 'Absent Days',
                    'number_of_days': day_values.count('absent') + day_values.count('surplus') + day_values.count('unpaid_vacation'),
                    'number_of_hours': (day_values.count('absent') + day_values.count('surplus') +  day_values.count('unpaid_vacation')) * hours_per_day,
                })
        return worked_days_line_vals_list

    @api.depends('employee_id', 'contract_id', 'struct_id', 'date_from', 'date_to', 'timesheet_lines_ids')
    def _compute_input_line_ids(self):
        for slip in self:
            input_line_vals = []
            if slip.timesheet_lines_ids:
                # Overtime
                overtime_hours = sum(slip.timesheet_lines_ids.mapped('over_time'))
                if overtime_hours:
                    existing_input_rec = slip.input_line_ids.filtered(lambda l: l.input_type_id == self.env.ref('employee_project_history.input_overtime'))
                    if existing_input_rec:
                        existing_input_rec.amount = overtime_hours
                    else:
                        input_line_vals.append((0, 0, {
                            'name': 'Overtime',
                            'amount': overtime_hours,
                            'input_type_id': self.env.ref('employee_project_history.input_overtime').id,
                        }))
                # Overtime sar
                overtime_hours_sar = sum(slip.timesheet_lines_ids.mapped('over_time_sar'))
                if overtime_hours_sar:
                    existing_input_rec = slip.input_line_ids.filtered(lambda l: l.input_type_id == self.env.ref('employee_project_history.input_overtime_sar'))
                    if existing_input_rec:
                        existing_input_rec.amount = overtime_hours_sar
                    else:
                        input_line_vals.append((0, 0, {
                            'name': 'Overtime (Sar)',
                            'amount': overtime_hours_sar,
                            'input_type_id': self.env.ref('employee_project_history.input_overtime_sar').id,
                        }))
                # Other allownace
                other_allowances = sum(slip.timesheet_lines_ids.mapped('other_allowances'))
                if other_allowances:
                    existing_input_rec = slip.input_line_ids.filtered(lambda l: l.input_type_id == self.env.ref('employee_project_history.input_other_allowances'))
                    if existing_input_rec:
                        existing_input_rec.amount = other_allowances
                    else:
                        input_line_vals.append((0, 0, {
                            'name': 'Other Allowances',
                            'amount': other_allowances,
                            'input_type_id': self.env.ref('employee_project_history.input_other_allowances').id,
                        }))
                # Miscellaneous
                miscellaneous_amount = sum(slip.timesheet_lines_ids.mapped('miscellaneous'))
                if miscellaneous_amount:
                    existing_input_rec = slip.input_line_ids.filtered(lambda l: l.input_type_id == self.env.ref('employee_project_history.input_miscellaneous'))
                    if existing_input_rec:
                        existing_input_rec.amount = miscellaneous_amount
                    else:
                        input_line_vals.append((0, 0, {
                            'name': 'Miscellaneous (Sar)',
                            'amount': miscellaneous_amount,
                            'input_type_id': self.env.ref('employee_project_history.input_miscellaneous').id,
                        }))
                # Trip allowance
                trip_allowances = sum(slip.timesheet_lines_ids.mapped('trip_allowance'))
                if trip_allowances:
                    existing_input_rec = slip.input_line_ids.filtered(lambda l: l.input_type_id == self.env.ref('employee_project_history.input_trip_allowance'))
                    if existing_input_rec:
                        existing_input_rec.amount = trip_allowances
                    else:
                        input_line_vals.append((0, 0, {
                            'name': 'Trip Allowance',
                            'amount': trip_allowances,
                            'input_type_id': self.env.ref('employee_project_history.input_trip_allowance').id,
                        }))
                # Other Deductions
                other_deductions = sum(slip.timesheet_lines_ids.mapped('other_deduction'))
                if other_deductions:
                    existing_input_rec = slip.input_line_ids.filtered(lambda l: l.input_type_id == self.env.ref('hr_payroll.input_deduction'))
                    if existing_input_rec:
                        existing_input_rec.amount = other_deductions
                    else:
                        input_line_vals.append((0, 0, {
                            'name': 'Other Deductions',
                            'amount': other_deductions,
                            'input_type_id': self.env.ref('hr_payroll.input_deduction').id,
                        }))
            # Surplus
            if slip.attendance_days:
                day_values = list(slip.attendance_days.values())
                if day_values.count('surplus'):
                    surplus_days = day_values.count('surplus')
                    existing_input_rec = slip.input_line_ids.filtered(lambda l: l.input_type_id == self.env.ref('employee_project_history.input_surplus'))
                    if existing_input_rec:
                        existing_input_rec.amount = surplus_days
                    else:
                        input_line_vals.append((0, 0, {
                            'name': 'Surplus',
                            'amount': surplus_days,
                            'input_type_id': self.env.ref('employee_project_history.input_surplus').id,
                        }))
            if input_line_vals:
                slip.input_line_ids = input_line_vals


class InheritAccountMoveLines(models.Model):
    _inherit = "account.move.line"
    _description = "Acoount Move Line"

    employee_number = fields.Char(related='employee_id.employee_number', string="Employee Number")


class HrPayslipBatch(models.Model):
    _inherit = 'hr.payslip.run'

    excel_report = fields.Binary(string="Excel Report")
    file_name = fields.Char(string="File Name")
