from odoo import http
from odoo.http import request
import base64
import xlsxwriter
from io import BytesIO
from dateutil.relativedelta import relativedelta
from datetime import datetime, date

class ReportDownloadController(http.Controller):

    @http.route('/web/download/xlsx_report', type='http', auth='user')
    def download_region_report_xlsx(self, wiz_id, **kwargs):
        wizard = request.env['employee.category.report.wizard'].sudo().browse(int(wiz_id))
        month_label = dict(wizard._fields['month'].selection).get(wizard.month, '')
        generated_file, file_name = self.generate_region_xlsx_report(wizard.employee_region_id, wizard.employee_category_ids, wizard.month, month_label, wizard.year)
        return request.make_response(
            generated_file,
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename="{file_name}"'),
            ]
        )

    def generate_region_xlsx_report(self, region_id, category_ids, month, month_label, year):
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # header format
        header_format = workbook.add_format({'font_size': 12, 'font_name': 'Arial', 'bg_color': '#318CE7', 'bold': True, 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
        # date format
        date_format = workbook.add_format({'font_size': 12, 'font_name': 'Arial', 'text_wrap': True, 'border': 1, 'align': 'top', 'valign': 'top', 'num_format': 'yyyy-mm-dd'})
        # payslip data format
        data_format = workbook.add_format({'font_size': 12, 'font_name': 'Arial', 'text_wrap': True, 'border': 1, 'align': 'top', 'valign': 'top'})
        # title format
        main_title_format = workbook.add_format({'font_size': 18, 'font_name': 'Arial', 'bold': True, 'align': 'center', 'valign': 'vcenter'})
        title_format = workbook.add_format({'font_size': 14, 'font_name': 'Arial', 'bold': True, 'align': 'center', 'valign': 'vcenter'})
        headers = ['Emp Id', 'Name', 'Designation', 'Sponsor', 'ID Nos.',
                   'Iqama Expiry Date - MUQEEM', 'Nationality', 'Work Days', 'Basic Salary', 'Food Allowance',
                   'Housing Allowance', 'Transportion Allowance', 'Fixed Allowance', 'Gross Salary', 'Salary Adjustment',
                   'OT Allowance', 'Trip Allowance','Over Time(Sar)', 'Miscellaneous', 'Surplus Food Allowance',
                   'Other Allowance', 'Absent Deduction', 'Other Deductions', 'Total Deduction',
                   'Net Salary Payable', 'Payment Detail', 'Mode of Payment', 'Beneficiary Signature & Date']

        for category in category_ids:
            sheet_name = category.name[:31]
            worksheet = workbook.add_worksheet(sheet_name)
            worksheet.merge_range('A2:AB2', 'Employee Payroll Report', main_title_format)
            worksheet.set_row(1, 30)
            worksheet.merge_range('A3:AB3', f'{category.name} - {region_id.name} - {month_label}', title_format)

            row = 4
            col = 0
            for header in headers:
                worksheet.write(row, col, header, header_format)
                col += 1
            worksheet.set_row(row, 28)

            for c in range(0, len(headers)):
                worksheet.set_column(c, c, 20)

            row = 5
            payslips = request.env['hr.payslip'].search([
                ('state', '=', 'done'),
                ('employee_id.employee_category_id', '=', category.id),
                ('employee_id.employee_project_region_id', '=', region_id.id),
            ])

            filtered_payslips = payslips.filtered(lambda p: p.date_from.month == int(month) and p.date_from.year == int(year))
            for payslip in filtered_payslips:
                payslip_emp = payslip.employee_id
                emp_contract = payslip_emp.contract_ids
                iqama_line = payslip_emp.iqama_lines_ids.filtered(lambda l:l.relation == 'self')
                col = 0
                worksheet.write(row, col, payslip_emp.employee_number if payslip_emp else '', data_format)
                worksheet.write(row, col + 1, payslip_emp.name if payslip_emp else '', data_format)
                worksheet.write(row, col + 2, payslip_emp.job_id.name if payslip_emp.job_id else '', data_format)
                worksheet.write(row, col + 3, payslip_emp.company_id.name if payslip_emp.company_id else '', data_format)
                worksheet.write(row, col + 4, iqama_line.iqama_no, data_format)
                worksheet.write(row, col + 5, iqama_line.expiry_date, date_format)
                worksheet.write(row, col + 6, payslip_emp.country_id.name if payslip_emp.country_id else '', data_format)
                worksheet.write(row, col + 7, payslip_emp.x_studio_work_days if payslip_emp.x_studio_work_days else '', data_format)
                worksheet.write(row, col + 8, emp_contract.x_studio_gosi_basic if emp_contract else '', data_format)
                worksheet.write(row, col + 9, emp_contract.x_studio_food_allowance if emp_contract else '', data_format)
                worksheet.write(row, col + 10, emp_contract.l10n_sa_housing_allowance if emp_contract else '', data_format)
                worksheet.write(row, col + 11, emp_contract.l10n_sa_transportation_allowance if emp_contract else '', data_format)
                worksheet.write(row, col + 12, (emp_contract.x_studio_fixed_ot_allowance + emp_contract.l10n_sa_other_allowances) if emp_contract else '', data_format)
                worksheet.write(row, col + 13, emp_contract.x_studio_total_wage, data_format)
                worksheet.write(row, col + 14, "", data_format)
                worksheet.write(row, col + 15, sum(payslip.line_ids.filtered(lambda l: l.code == 'OT').mapped('total')), data_format)
                worksheet.write(row, col + 16, sum(payslip.line_ids.filtered(lambda l: l.code == 'TP-A').mapped('total')), data_format)
                worksheet.write(row, col + 17, sum(payslip.line_ids.filtered(lambda l: l.code == 'OT-SAR').mapped('total')), data_format)
                worksheet.write(row, col + 18, sum(payslip.line_ids.filtered(lambda l: l.code == 'Misc').mapped('total')), data_format)
                worksheet.write(row, col + 19, sum(payslip.line_ids.filtered(lambda l: l.code == 'SP').mapped('total')), data_format)
                worksheet.write(row, col + 20, sum(payslip.line_ids.filtered(lambda l: l.code == 'OA').mapped('total')), data_format)
                worksheet.write(row, col + 21, sum(payslip.line_ids.filtered(lambda l: l.code == 'UL' and l.category_id.name == 'Deduction').mapped('total')), data_format)
                other_deducation_lines = payslip.line_ids.filtered(lambda l: l.code in ['INSTALLMENT', 'ATTACH_SALARY', 'ASSIG_SALARY', 'DEDUCTION'] and l.category_id.name == 'Deduction')
                total_other_deductions = sum(line.total for line in other_deducation_lines)
                worksheet.write(row, col + 22, total_other_deductions, data_format)

                total_deducation_lines = payslip.line_ids.filtered(lambda l: l.code in ['INSTALLMENT', 'ATTACH_SALARY', 'ASSIG_SALARY', 'DEDUCTION', 'UL'] and l.category_id.name == 'Deduction')
                total_deductions = sum(line.total for line in total_deducation_lines)
                worksheet.write(row, col + 23, total_deductions, data_format)

                worksheet.write(row, col + 24, sum(payslip.line_ids.filtered(lambda l: l.code == 'NET').mapped('total')), data_format)
                worksheet.write(row, col + 25, "", data_format)
                mode_of_payment = dict(payslip_emp._fields['x_studio_mode_of_payment'].selection).get(payslip_emp.x_studio_mode_of_payment, '')
                worksheet.write(row, col + 26, mode_of_payment, data_format)
                worksheet.write(row, col + 27, " ", data_format)
                row += 1
            # signature table
            signature_headers = ['Initiator  -  Payroll Accountant', 'Verified  -  MRM Manager', 'Approved - COO',
                                'Approved -  CHRO', 'Approved - CFO', 'Approved – DCEO / GCEO']

            signature_header_format = workbook.add_format({'bold': True, 'align': 'center', 
                'valign': 'vcenter', 'border': 1, 'bg_color': '#F2F2F2', 'text_wrap': True
            })

            sig_row = row + 4
            col_width = 20
            cols_per_header = 2
            total_signature_cols = len(signature_headers) * cols_per_header

            worksheet_total_cols = 28
            start_offset = (worksheet_total_cols - total_signature_cols) // 2

            for idx, header in enumerate(signature_headers):
                start_col = start_offset + idx * cols_per_header
                end_col = start_col + cols_per_header - 1
                worksheet.merge_range(sig_row, start_col, sig_row + 1, end_col, header, signature_header_format)
                worksheet.merge_range(sig_row + 2, start_col, sig_row + 7, end_col, '', signature_header_format)
                for c in range(start_col, end_col + 1):
                    worksheet.set_column(c, c, col_width)

        workbook.close()
        output.seek(0)
        generated_file = output.read()
        file_name = f"Employee_Report_{region_id.name}_{month_label}_{year}.xlsx"

        return generated_file, file_name

    #summary report
    @http.route('/web/download/summary_report', type='http', auth='user')
    def download_summary_report_xlsx(self, wiz_id, **kwargs):
        wizard = request.env['employee.category.report.wizard'].sudo().browse(int(wiz_id))
        month_label = dict(wizard._fields['month'].selection).get(wizard.month, '')
        generated_file, file_name = self.generate_summary_xlsx_report(wizard.employee_project_region_ids, wizard.employee_category_ids, month_label, wizard.month, wizard.year)
        return request.make_response(
            generated_file,
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename="{file_name}"'),
            ]
        )

    def generate_summary_xlsx_report(self, multi_regions, category_ids, month_label, month, year):
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        summary_sheet = workbook.add_worksheet('Summary')
        summary_data = self._get_summary_table(multi_regions, category_ids, month, year)

        percent_style = workbook.add_format({'num_format': '0.00%', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        currency = workbook.add_format({'border': 1, 'align': 'center', 'num_format': '#,##0.00', 'bg_color': '#F2F2F2'})
        normal = workbook.add_format({'border': 1, 'align': 'center'})
        bold = workbook.add_format({'bold': True, 'align': 'center', 'border': 1, 'bg_color': '#F2F2F2'})
        main_title_format = workbook.add_format({'font_size': 18, 'font_name': 'Arial', 'bold': True, 'align': 'center', 'valign': 'vcenter'})
        header_format = workbook.add_format({'font_size': 12, 'bold': True, 'bg_color': '#318CE7', 'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True})

        row_title = 4
        row_subheader = 5
        data_start_row = 6

        summary_sheet.merge_range('A2:L2', "Summary", main_title_format)
        summary_sheet.set_row(1, 30)

        summary_sheet.write(row_title, 0, "Region", header_format)
        summary_sheet.write(row_subheader, 0, "")
        summary_sheet.set_column(row_title, 0, 15)

        category_id_index = {cat_id: idx for idx, cat_id in enumerate(category_ids)}

        col = 1
        category_columns = {}

        for category in category_ids:
            summary_sheet.merge_range(row_title, col, row_title, col + 1, category.name, header_format)
            summary_sheet.write(row_subheader, col, 'HC', bold)
            summary_sheet.write(row_subheader, col + 1, 'Salary', bold)
            summary_sheet.write(row_title, col + 2, '%', header_format)
            summary_sheet.write(row_subheader, col + 2, '')
            summary_sheet.set_column(col, col + 1,  15)
            summary_sheet.set_column(col + 2,  15)
            category_columns[category.id] = col
            col += 3

        summary_sheet.write(row_title, col, 'Total Salary', header_format)
        summary_sheet.write(row_subheader, col, '', bold)
        col += 1

        summary_sheet.write(row_title, col, 'Gross Total(%)', header_format)
        summary_sheet.write(row_subheader, col, '', bold)

        col += 1
        grand_total_salary = 0.0
        grand_total_count = 0
        gross_total_salary = 0.0
        for region_data in summary_data.values():
            for category_id in category_columns.keys():
                cat_summary = region_data.get(category_id, {'salary': 0.0})
                gross_total_salary += cat_summary['salary']

        row = data_start_row

        for region_name, region_data in summary_data.items():
            summary_sheet.write(row, 0, region_name, normal)
            total_count = 0
            total_salary = 0.0
            category_results = {}
            for category_id, category_col in category_columns.items():
                cat_summary = region_data.get(category_id, {'total_employee': 0, 'salary': 0.0})
                count = cat_summary['total_employee']
                salary = cat_summary['salary']
                total_count += count
                total_salary += salary
                category_results[category_id] = {'count': count, 'salary': salary}
            for category_id, category_col in category_columns.items():
                cat_result = category_results[category_id]
                count = cat_result['count']
                salary = cat_result['salary']
                percent = (salary / total_salary * 100) if total_salary else 0.0
                gross_percent = (total_salary / gross_total_salary * 100) if gross_total_salary else 0.0  
                summary_sheet.write(row, category_col, count, normal)
                summary_sheet.write(row, category_col + 1, salary, currency)
                summary_sheet.write(row, category_col + 2, f"{percent:.2f}%", percent_style)
                summary_sheet.write(row, category_col + 3, total_salary, currency)
                summary_sheet.write(row, category_col + 4, f"{gross_percent:.2f}%", percent_style)
                summary_sheet.set_column(row, category_col + 1, 15)
                summary_sheet.set_column(row, category_col + 2, 15)
                summary_sheet.set_column(row, category_col + 3, 15)
                summary_sheet.set_column(row, category_col + 4, 15)
            row += 1

        summary_sheet.write(row + 1, category_col + 2, 'Gross Total:', bold)
        summary_sheet.write(row + 1, category_col + 3, gross_total_salary, currency)

        # signature table
        signature_headers = ['Initiator  -  Payroll Accountant', 'Verified  -  MRM Manager', 'Approved - COO',
                            'Approved -  CHRO', 'Approved - CFO', 'Approved – DCEO / GCEO'] 
        signature_header_format = workbook.add_format({'bold': True, 'align': 'center', 
            'valign': 'vcenter', 'border': 1, 'bg_color': '#F2F2F2', 'text_wrap': True})

        sig_row = row + 6
        col_width = 15
        cols_per_header = 2

        for idx, header in enumerate(signature_headers):
            start_col = idx * cols_per_header
            end_col = start_col + cols_per_header - 1
            summary_sheet.merge_range(sig_row, start_col, sig_row + 1, end_col, header, signature_header_format)
            summary_sheet.merge_range(sig_row + 2, start_col, sig_row + 7, end_col, '', signature_header_format)

            for c in range(start_col, end_col + 1):
                summary_sheet.set_column(c, c, col_width)

        workbook.close()
        output.seek(0)
        generated_file = output.read()
        if len(multi_regions) > 2:
            file_name = f'Summary of {month_label}-{year}.xlsx'
        elif len(multi_regions) == 2:
            region_names = "_".join([r.name.replace(" ", "_") for r in multi_regions])
            file_name = f"{region_names}_{month_label}_{year}.xlsx"
        else:
            file_name = "summary.xlsx"

        return generated_file, file_name

    def _get_summary_table(self, multi_regions, category_ids, month, year):
        date_from = datetime(int(year), int(month), 1)
        date_to = (date_from + relativedelta(months=1)) - relativedelta(days=1)

        filtered_payslips = request.env['hr.payslip'].search([
            ('state', '=', 'done'),
            ('date_from', '>=', date_from.date()),
            ('date_to', '<=', date_to.date()),
            ('employee_id.employee_project_region_id', 'in', multi_regions.ids),
            ('employee_id.employee_category_id', 'in', category_ids.ids),
        ])

        summary = {}
        for region in multi_regions:
            region_name = region.name
            summary[region_name] = {}
            for category in category_ids:
                summary[region_name][category.id] = {
                    'total_employee': 0,
                    'salary': 0.0,
                }

        for payslip in filtered_payslips:
            emp = payslip.employee_id
            region = emp.employee_project_region_id
            category = emp.employee_category_id

            if not region or not category:
                continue

            region_name = region.name
            category_id = category.id

            net_line = payslip.line_ids.filtered(lambda l: l.code == 'NET')
            net_salary = sum(net_line.mapped('total')) if net_line else 0.0

            summary[region_name][category_id]['total_employee'] += 1
            summary[region_name][category_id]['salary'] += net_salary

        return summary



