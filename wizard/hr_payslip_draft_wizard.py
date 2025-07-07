from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import re
import xlsxwriter
import base64
from io import BytesIO

class HrPayslipDraftWizard(models.TransientModel):
    _name = 'hr.payslip.draft.wizard'
    _description = 'Payslip Draft Entry Confirmation'

    payment_type = fields.Selection([('bank', 'Bank'), ('cash', 'Cash')], string="Payment Type")
    note = fields.Html(string="Note")

    @api.model
    def default_get(self, fields_list):
        res = super(HrPayslipDraftWizard, self).default_get(fields_list)
        active_ids = self.env.context.get('active_ids', [])
        if active_ids:
            payslips = self.env['hr.payslip'].browse(active_ids)
            not_completed_payslips = payslips.filtered(lambda l: l.entries == 'not_completed')
            # Check if the current user is an administrator
            is_admin = self.env.user.has_group('base.group_system')
            if not is_admin and not_completed_payslips:
                payslip_names = ', '.join(not_completed_payslips.mapped('name'))
                raise ValidationError(_("Entries Not Completed for Payslips: %s" % payslip_names))
            companies = payslips.mapped('company_id')
            if len(companies) > 1:
                raise ValidationError(_("You cannot process payslips from multiple companies."))
            # Manual mapping
            studio_to_internal = {
                'Bank': 'bank',
                'Mode of Payment': 'cash',
            }
            payment_modes = payslips.mapped('employee_payment')
            if len(payment_modes) == 1:
                internal_value = studio_to_internal.get(payment_modes[0])
                res['payment_type'] = internal_value
            if len(payment_modes) > 1:
                raise ValidationError(_("Please select payslips with the same payment mode. Multiple payment modes cannot be processed at once."))
        return res
    
    def confirm_payslip(self):
        active_ids = self.env.context.get('active_ids')
        if not active_ids:
            return

        hr_payslip_run_env = self.env['hr.payslip.run']
        payslips = self.env['hr.payslip'].browse(active_ids)
        
        if payslips:
            date_from = min(payslips.mapped('date_from'))
            date_to = max(payslips.mapped('date_to'))
            month_name = date_from.strftime('%B')
            year = date_from.strftime('%Y')
            company_id = payslips[0].company_id
            
            sequence = self.env['ir.sequence'].search([('code', '=', 'hr.payslip.batch.seq')], limit=1)
            if not sequence:
                raise ValidationError(_("Payslip batch sequence not found. Please configure it."))
            
            date_start = datetime.strptime(f"{year}-{date_from.month}-01", "%Y-%m-%d").date()
            date_to_end = date_start + relativedelta(day=31)
            
            date_range = self.env['ir.sequence.date_range'].search([
                ('sequence_id', '=', sequence.id),
                ('date_from', '=', date_start),
                ('date_to', '=', date_to_end),
            ], limit=1)
            
            if not date_range:
                date_range = self.env['ir.sequence.date_range'].create({
                    'sequence_id': sequence.id,
                    'date_from': date_start,
                    'date_to': date_to_end,
                })
            
            last_batch = hr_payslip_run_env.search([
                ('date_start', '>=', date_start),
                ('date_end', '<=', date_to_end),
                ('company_id', '=', company_id.id)
            ], order='name desc', limit=1)
            
            next_seq_num = 1
            if last_batch and last_batch.name:
                match = re.search(r'TFM-PR-(\d+)-', last_batch.name)
                if match:
                    last_seq_num = int(match.group(1))
                    next_seq_num = last_seq_num + 1

            current_date = date.today()
            formatted_seq = f"TFM-PR-{str(next_seq_num).zfill(2)}-{month_name}-{year}-[{current_date.strftime('%d-%B-%Y')}]"
            new_batch = hr_payslip_run_env.create({
                'name': formatted_seq,
                'date_start': date_from,
                'date_end': date_to,
                'company_id': company_id.id
            })
            payslips.write({'payslip_run_id': new_batch.id,
                'payment_type': self.payment_type,
                'note': self.note})
            payslips.with_context(payslip_generate_pdf=True).action_payslip_done()
            for payslip in payslips:
                if payslip.move_id:
                    employee_id = payslip.employee_id.id
                    timesheet_lines_rec = payslip.timesheet_lines_ids
                    employee_timesheet_rec = timesheet_lines_rec.mapped('employee_timesheet_id')
                    project_analytic_distribution_rec = employee_timesheet_rec.mapped('project_id')
                    analytic_company = project_analytic_distribution_rec.company_analytic_account_ids.filtered(lambda l:l.company_id and l.company_id.id == payslip.employee_id.company_id.id)
                    existing_invoice_lines = payslip.move_id.invoice_line_ids.filtered(lambda l: l.analytic_distribution)
                    analytic_distribution_dict = {}
                    for timesheet_line in timesheet_lines_rec:
                        if payslip.employee_id == timesheet_line.employee_id:
                            attendance_percentage = round(timesheet_line.attendance_percentage, 2)
                            if analytic_company and analytic_company.analytic_distribution:
                                analytic_account_key = list(analytic_company.analytic_distribution.keys())[0] if analytic_company.analytic_distribution.keys() else False
                                if analytic_account_key:
                                    if analytic_account_key in analytic_distribution_dict:
                                        analytic_distribution_dict[analytic_account_key] += attendance_percentage
                                    else:
                                        analytic_distribution_dict[analytic_account_key] = attendance_percentage
                    if analytic_distribution_dict:
                        for analytic in existing_invoice_lines:
                            analytic.write({'analytic_distribution': analytic_distribution_dict,
                                            'employee_number': payslip.employee_id.employee_number})
            attachment = self._generate_xlsx_report(payslips)

        return {
            "type": "ir.actions.act_url",
            "url": '/web/content/%s?download=true' % attachment.id,
            "target": "new",
            'close': True,
        }

    def _generate_xlsx_report(self, payslips):
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('SALARY SHEET')

        # header format
        header_format = workbook.add_format({'font_size': 12, 'font_name': 'Arial', 'bg_color': '#318CE7', 'bold': True, 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

        # date format
        date_format = workbook.add_format({'font_size': 12, 'font_name': 'Arial', 'text_wrap': True, 'border': 1, 'align': 'top', 'valign': 'top', 'num_format': 'yyyy-mm-dd'})
        # payslip data format
        data_format = workbook.add_format({'font_size': 12, 'font_name': 'Arial', 'text_wrap': True, 'border': 1, 'align': 'top', 'valign': 'top'})
        # title format
        main_title_format = workbook.add_format({'font_size': 18, 'font_name': 'Arial', 'bold': True, 'align': 'center', 'valign': 'vcenter'})
        title_format = workbook.add_format({'font_size': 14, 'font_name': 'Arial', 'bold': True, 'align': 'center', 'valign': 'vcenter'})

        headers = ['Emp Id', 'Name', 'Designation', 'Sponsor', 'Expense-Branch',
                   'Salary-Branch', 'Department', 'Division', 'Sub-Division', 'Project', 'DOJ', 'ID Nos.',
                   'Iqama Expiry Date - MUQEEM', 'Nationality', 'Work Days', 'Basic Salary', 'Food Allowance',
                   'Housing Allowance', 'Transportion Allowance', 'Fixed Allowance', 'Gross Salary', 'Salary Adjustment',
                   'OT Allowance', 'Trip Allowance','Over Time(Sar)', 'Miscellaneous', 'Surplus Food Allowance',
                   'Other Allowance', 'Absent Deduction', 'Other Deductions', 'Total Deduction',
                   'Net Salary Payable', 'Payment Detail', 'Mode of Payment', 'Bank IBAN', 'Bank Name',
                   'Beneficiary Signature & Date']

        row = 4
        col = 0
        for header in headers:
            worksheet.write(row, col, header, header_format)
            col += 1
        worksheet.set_row(row, 35)

        for c in range(col, col + len(headers)):
                worksheet.set_column(c, c, 20)

        row = 5
        for payslip in payslips:
            payslip_date = payslip.date
            payslip_month_year = payslip_date.strftime('%B-%Y')
            worksheet.merge_range('A2:AI2', 'TOTAL FACILITY MANAGEMENT', main_title_format)
            worksheet.set_row(1, 30)
            worksheet.merge_range('A3:AI3', f'SALARY SHEET FOR THE MONTH OF {payslip_month_year}', title_format)
            worksheet.set_row(2, 20)

            payslip_emp = payslip.employee_id
            emp_contract = payslip_emp.contract_ids
            iqama_line = payslip_emp.iqama_lines_ids.filtered(lambda l:l.relation == 'self')
            accounting_entry = payslip.move_id.invoice_line_ids.filtered(lambda l: l.analytic_distribution)
            for acc in accounting_entry:
                analytic_account_key = list(acc.analytic_distribution.keys())[0] if acc.analytic_distribution.keys() else False
                if analytic_account_key:
                    analytic_account_ids = [int(id.strip()) for id in analytic_account_key.split(',')] if analytic_account_key else []
                    acc_analytic_rec = self.env['account.analytic.account']

                    branch_analytic_accounts = acc_analytic_rec.search([('id', 'in', analytic_account_ids), ('plan_id.name', '=', 'Branch')])
                    branch_data = [account.name for account in branch_analytic_accounts]
                    expense_branch = ', '.join(branch_data) if branch_data else ''

                    department_analytic_accounts = acc_analytic_rec.search([('id', 'in', analytic_account_ids), ('plan_id.name', '=', 'Department')])
                    department_data = [department.name for department in department_analytic_accounts]
                    department = ', '.join(department_data) if department_data else ''

                    division_analytic_accounts = acc_analytic_rec.search([('id', 'in', analytic_account_ids), ('plan_id.name', '=', 'Division')])
                    division_data = [division.name for division in division_analytic_accounts]
                    division = ', '.join(division_data) if division_data else ''

                    sub_division_analytic_accounts = acc_analytic_rec.search([('id', 'in', analytic_account_ids), ('plan_id.name', '=', 'Sub - Division')])
                    sub_division_data = [sub_division.name for sub_division in sub_division_analytic_accounts]
                    sub_division = ', '.join(sub_division_data) if sub_division_data else ''

                    project_analytic_accounts = acc_analytic_rec.search([('id', 'in', analytic_account_ids), ('plan_id.name', '=', 'Projects')])
                    project_data = [project.name for project in project_analytic_accounts]
                    project = ', '.join(project_data) if project_data else ''
            col = 0

            worksheet.write(row, col, payslip_emp.employee_number if payslip_emp else '', data_format)
            worksheet.write(row, col + 1, payslip_emp.name if payslip_emp else '', data_format)
            worksheet.write(row, col + 2, payslip_emp.job_id.name if payslip_emp.job_id else '', data_format)
            worksheet.write(row, col + 3, payslip_emp.company_id.name if payslip_emp.company_id else '', data_format)
            worksheet.write(row, col + 4, expense_branch, data_format)
            worksheet.write(row, col + 5, expense_branch, data_format)
            worksheet.write(row, col + 6, department, data_format)
            worksheet.write(row, col + 7, division, data_format)
            worksheet.write(row, col + 8, sub_division, data_format)
            worksheet.write(row, col + 9, project, data_format)
            worksheet.write(row, col + 10, payslip_emp.x_studio_joining_date if payslip_emp.x_studio_joining_date else '', date_format)
            worksheet.write(row, col + 11, iqama_line.iqama_no, data_format)
            worksheet.write(row, col + 12, iqama_line.expiry_date, date_format)
            worksheet.write(row, col + 13, payslip_emp.country_id.name if payslip_emp.country_id else '', data_format)
            worksheet.write(row, col + 14, payslip_emp.x_studio_work_days if payslip_emp.x_studio_work_days else '', data_format)
            worksheet.write(row, col + 15, emp_contract.x_studio_gosi_basic if emp_contract else '', data_format)
            worksheet.write(row, col + 16, emp_contract.x_studio_food_allowance if emp_contract else '', data_format)
            worksheet.write(row, col + 17, emp_contract.l10n_sa_housing_allowance if emp_contract else '', data_format)
            worksheet.write(row, col + 18, emp_contract.l10n_sa_transportation_allowance if emp_contract else '', data_format)
            worksheet.write(row, col + 19, (emp_contract.x_studio_fixed_ot_allowance + emp_contract.l10n_sa_other_allowances) if emp_contract else '', data_format)
            worksheet.write(row, col + 20, emp_contract.x_studio_total_wage, data_format)
            worksheet.write(row, col + 21, "", data_format)
            worksheet.write(row, col + 22, sum(payslip.line_ids.filtered(lambda l: l.code == 'OT').mapped('total')), data_format)
            worksheet.write(row, col + 23, sum(payslip.line_ids.filtered(lambda l: l.code == 'TP-A').mapped('total')), data_format)
            worksheet.write(row, col + 24, sum(payslip.line_ids.filtered(lambda l: l.code == 'OT-SAR').mapped('total')), data_format)
            worksheet.write(row, col + 25, sum(payslip.line_ids.filtered(lambda l: l.code == 'Misc').mapped('total')), data_format)
            worksheet.write(row, col + 26, sum(payslip.line_ids.filtered(lambda l: l.code == 'SP').mapped('total')), data_format)
            worksheet.write(row, col + 27, sum(payslip.line_ids.filtered(lambda l: l.code == 'OA').mapped('total')), data_format)
            worksheet.write(row, col + 28, sum(payslip.line_ids.filtered(lambda l: l.code == 'UL' and l.category_id.name == 'Deduction').mapped('total')), data_format)

            other_deducation_lines = payslip.line_ids.filtered(lambda l: l.code in ['INSTALLMENT', 'ATTACH_SALARY', 'ASSIG_SALARY', 'DEDUCTION'] and l.category_id.name == 'Deduction')
            total_other_deductions = sum(line.total for line in other_deducation_lines)
            worksheet.write(row, col + 29, total_other_deductions, data_format)

            total_deducation_lines = payslip.line_ids.filtered(lambda l: l.code in ['INSTALLMENT', 'ATTACH_SALARY', 'ASSIG_SALARY', 'DEDUCTION', 'UL'] and l.category_id.name == 'Deduction')
            total_deductions = sum(line.total for line in total_deducation_lines)
            worksheet.write(row, col + 30, total_deductions, data_format)

            worksheet.write(row, col + 31, payslip.line_ids.filtered(lambda l: l.code == 'NET').total if payslip.line_ids else '', data_format)
            worksheet.write(row, col + 32, "", data_format)
            mode_of_payment = dict(payslip_emp._fields['x_studio_mode_of_payment'].selection).get(payslip_emp.x_studio_mode_of_payment, '')
            worksheet.write(row, col + 33, mode_of_payment, data_format)
            worksheet.write(row, col + 34, payslip_emp.x_studio_iban if payslip_emp.x_studio_iban else '', data_format)
            worksheet.write(row, col + 35, payslip_emp.x_studio_bank_reference_number_wps if payslip_emp.x_studio_bank_reference_number_wps else '', data_format)
            worksheet.write(row, col + 36, " ", data_format)
            row += 1

        workbook.close()
        output.seek(0)
        batch_name = payslips.payslip_run_id.name if payslips.payslip_run_id else 'SALARY SHEET'
        file_name = f"{batch_name}.xlsx"
        file_data_base64 = base64.b64encode(output.getvalue()).decode()
        attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'type': 'binary',
            'datas': file_data_base64,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': self._name,
            'res_id': self.id,
        })
        if not attachment:
            raise ValidationError(_("Failed to create the attachment. Please try again."))

        payslips.payslip_run_id.write({'excel_report': file_data_base64, 'file_name': file_name})
        output.close()

        return attachment
