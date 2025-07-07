/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

import { formatDate } from "@web/core/l10n/dates";

import { SkillsX2ManyField, skillsX2ManyField } from "@hr_skills/fields/skills_one2many/skills_one2many"
import { CommonSkillsListRenderer } from "@hr_skills/views/skills_list_renderer"

export class ExperienceListRenderer extends CommonSkillsListRenderer {
    get groupBy() {
        return 'line_type_id';
    }

    get colspan() {
        if (this.props.activeActions) {
            return 3;
        }
        return 2;
    }

    formatDate(date) {
        return formatDate(date);
    }

    setDefaultColumnWidths() {}
}
ExperienceListRenderer.template = 'employee_project_history.ExperienceListRenderer';
ExperienceListRenderer.rowsTemplate = "employee_project_history.ExperienceListRenderer.Rows";
ExperienceListRenderer.recordRowTemplate = "employee_project_history.ExperienceListRenderer.RecordRow";


export class ExperienceX2ManyField extends SkillsX2ManyField {
    getWizardTitleName() {
        return _t("Create a Experience line");
    }
}
ExperienceX2ManyField.components = {
    ...SkillsX2ManyField.components,
    ListRenderer: ExperienceListRenderer,
};

export const experienceX2ManyField = {
    ...skillsX2ManyField,
    component: ExperienceX2ManyField,
};

registry.category("fields").add("experience_one2many", experienceX2ManyField);
