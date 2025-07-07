{
    "name": "Employee Project History",
    "version": "17.0.1.0.0",
    'author': 'Entrivistech Pvt. Ltd.',
    "maintainer": "Entrivis Tech Pvt. Ltd.",
    "description": "Employee Project History",
    'website': "www.entrivistech.com",
    'license': 'LGPL-3',
    "depends": ['hr', 'hr_skills', 'hr_payroll', 'account', 'bi_hr_employee_loan'],
    "data": [
        'security/project_history_security.xml',
        'security/ir.model.access.csv',
        'data/employee_sequence.xml',
        'data/employee_project_type.xml',
        'data/employee_timesheet_report.xml',
        'data/hr_payslip_input_type.xml',
        'data/employee_category_data.xml',
        'views/employee_views.xml',
        'views/employee_projects.xml',
        'views/employee_timesheet_views.xml',
        'views/hr_payslip_inherit_views.xml',
        'wizard/update_project.xml',
        'wizard/hr_payslip_draft_wizard_views.xml',
        'wizard/employee_category_report_wizard_views.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'employee_project_history/static/src/**/*',
        ]
    },
}
