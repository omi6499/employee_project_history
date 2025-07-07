from odoo import models, api, fields, _
from datetime import date, timedelta
from odoo.exceptions import ValidationError
import calendar


class EmployeeTimesheetLine(models.Model):
    _name = "employee.timesheet.line"
    _description = 'Employee Timesheet lines'
    _rec_name = "employee_id"

    def _get_day_selections(self):
        return [('present', 'P'), ('overtime', 'OT'), ('absent', 'A'), ('paid_off', 'OFF'), ('sick', 'SL'), ('weekoff', 'F'),
         ('leave', 'VL'), ('surplus', 'S'), ('rotational_off', 'ROT'), ('unpaid_vacation', 'VL-D')]

    is_rotational_off = fields.Boolean(related='employee_timesheet_id.is_rotational_off', store=True)
    project_id = fields.Many2one(related='employee_timesheet_id.project_id', string="Project")
    emp_history_id = fields.Many2one("employee.project.history", string="Employee Project History", required=True)
    employee_id = fields.Many2one("hr.employee", string="Employee", required=True)
    employee_num = fields.Char(related='employee_id.employee_number', store=True)
    designation = fields.Many2one(related="emp_history_id.designation_id", store=True)
    employee_timesheet_id = fields.Many2one("employee.timesheet", string="Timesheet", ondelete='cascade')
    day_1 = fields.Selection(selection=_get_day_selections, string='1')
    day_2 = fields.Selection(selection=_get_day_selections, string='2')
    day_3 = fields.Selection(selection=_get_day_selections, string='3')
    day_4 = fields.Selection(selection=_get_day_selections, string='4')
    day_5 = fields.Selection(selection=_get_day_selections, string='5')
    day_6 = fields.Selection(selection=_get_day_selections, string='6')
    day_7 = fields.Selection(selection=_get_day_selections, string='7')
    day_8 = fields.Selection(selection=_get_day_selections, string='8')
    day_9 = fields.Selection(selection=_get_day_selections, string='9')
    day_10 = fields.Selection(selection=_get_day_selections, string='10')
    day_11 = fields.Selection(selection=_get_day_selections, string='11')
    day_12 = fields.Selection(selection=_get_day_selections, string='12')
    day_13 = fields.Selection(selection=_get_day_selections, string='13')
    day_14 = fields.Selection(selection=_get_day_selections, string='14')
    day_15 = fields.Selection(selection=_get_day_selections, string='15')
    day_16 = fields.Selection(selection=_get_day_selections, string='16')
    day_17 = fields.Selection(selection=_get_day_selections, string='17')
    day_18 = fields.Selection(selection=_get_day_selections, string='18')
    day_19 = fields.Selection(selection=_get_day_selections, string='19')
    day_20 = fields.Selection(selection=_get_day_selections, string='20')
    day_21 = fields.Selection(selection=_get_day_selections, string='21')
    day_22 = fields.Selection(selection=_get_day_selections, string='22')
    day_23 = fields.Selection(selection=_get_day_selections, string='23')
    day_24 = fields.Selection(selection=_get_day_selections, string='24')
    day_25 = fields.Selection(selection=_get_day_selections, string='25')
    day_26 = fields.Selection(selection=_get_day_selections, string='26')
    day_27 = fields.Selection(selection=_get_day_selections, string='27')
    day_28 = fields.Selection(selection=_get_day_selections, string='28')
    day_29 = fields.Selection(selection=_get_day_selections, string='29')
    day_30 = fields.Selection(selection=_get_day_selections, string='30')
    day_31 = fields.Selection(selection=_get_day_selections, string='31')
    over_time = fields.Float("Over Time")
    trip_allowance = fields.Float("Trip Allowance")
    other_deduction = fields.Float("Other Deduction")
    over_time_sar = fields.Float("Over Time (Sar)")
    other_allowances = fields.Float("Other Allowances")
    miscellaneous = fields.Float("Miscellaneous")
    start_day = fields.Integer(string="Start day", compute='_compute_start_end_day', store=True)
    end_day = fields.Integer(string="End day", compute='_compute_start_end_day', store=True)
    payslip_id = fields.Many2one("hr.payslip", string="Payslip")
    attendance_percentage = fields.Float(string="Attendance (%)", compute="_compute_cal_attendance")

    def _compute_cal_attendance(self):
        for rec in self:
            if not rec.employee_timesheet_id or not rec.employee_timesheet_id.start_date:
                rec.attendance_percentage = 0.00
                continue
            year = rec.employee_timesheet_id.start_date.year
            month = rec.employee_timesheet_id.start_date.month
            total_days_in_month = calendar.monthrange(year, month)[1]
            all_fields = self.fields_get()
            selection_fields = {field: details for field, details in all_fields.items() if details.get('type') == 'selection'}
            existing_selection_fields = list(selection_fields.keys())
            filled_days = sum(1 for field in existing_selection_fields if getattr(rec, field, None))
            cal_attendance = (filled_days / total_days_in_month) * 100 if total_days_in_month else 0.00
            rec.attendance_percentage = cal_attendance

    @api.depends('emp_history_id.date_start', 'emp_history_id.date_end', 'employee_timesheet_id.start_day', 'employee_timesheet_id.end_day')
    def _compute_start_end_day(self):
        for rec in self:
            if rec.emp_history_id and rec.employee_timesheet_id:
                rec.write({
                    'start_day': max(rec.emp_history_id.date_start.day,
                                     rec.employee_timesheet_id.start_day) if rec.emp_history_id.date_start.month == rec.employee_timesheet_id.start_date.month else rec.employee_timesheet_id.start_day,
                    'end_day': min(rec.emp_history_id.date_end.day,
                                   rec.employee_timesheet_id.end_day) if rec.emp_history_id.date_end and rec.emp_history_id.date_end.month == rec.employee_timesheet_id.end_date.month else rec.employee_timesheet_id.end_day,
                })
            else:
                rec.write({'start_day': 1, 'end_day': 31})

    @api.constrains('day_1', 'day_2', 'day_3', 'day_4', 'day_5', 'day_6', 'day_7', 'day_8', 'day_9', 'day_10', 'day_11',
        'day_12', 'day_13', 'day_14', 'day_15', 'day_16', 'day_17', 'day_18', 'day_19', 'day_20', 'day_21', 'day_22',
        'day_23', 'day_24', 'day_25', 'day_26', 'day_27', 'day_28', 'day_29', 'day_30', 'day_31', 'project_id')
    def _check_rotation_off(self):
        for rec in self:
            visible_fields = ['day_%s'%day for day in range(rec.start_day, rec.end_day + 1)]
            friday_fields = ['day_%s'%day for day in range(rec.start_day, rec.end_day + 1) if date(rec.employee_timesheet_id.start_date.year, rec.employee_timesheet_id.start_date.month, day).weekday() == 4]
            # has_rotational_off = any(getattr(rec, field) == 'rotational_off' for field in visible_fields if hasattr(rec, field))
            rotational_off_count = sum(1 for field in visible_fields if getattr(rec, field) == 'rotational_off')
            if rotational_off_count and not rec.is_rotational_off:
                raise ValidationError(_("Rotational Off is not allowed for this project. Please check project configuration."))
            if rotational_off_count > len(friday_fields):
                raise ValidationError(_("Only %s Rotational Off Allowed."%len(friday_fields)))

    @api.constrains('start_day', 'end_day')
    def _check_start_end_day(self):
        """
        Check if any day field is blank after date change in Employee project history. If blank then set Default (Present).
        Check if any day field having value outside employee's assigned days. If available then set it to Blank.
        Auto set Fridays to 'weekoff' (F).
        """
        for rec in self:
            visible_fields = ['day_%s'%day for day in range(rec.start_day, rec.end_day + 1)]
            timesheet_start_date = rec.employee_timesheet_id.start_date
            friday_fields = ['day_%s'%day for day in range(rec.start_day, rec.end_day + 1) if date(timesheet_start_date.year, timesheet_start_date.month, day).weekday() == 4]
            set_weekoff_vals = {field_name: 'weekoff' for field_name in friday_fields if field_name in visible_fields}
            if set_weekoff_vals:
                rec.write(set_weekoff_vals)
            def_selction = rec.project_id.day_selection if rec.project_id.day_selection else 'present'
            set_present_vals = {field_name: def_selction for field_name in visible_fields if not getattr(rec, field_name)}
            if set_present_vals:
                rec.write(set_present_vals)
            fields_to_set_blank = ['day_%s'%day for day in range(1,32) if 'day_%s'%day not in visible_fields]
            set_blank_vals = {field_name : False for field_name in fields_to_set_blank if getattr(rec, field_name)}
            if set_blank_vals:
                rec.write(set_blank_vals)
