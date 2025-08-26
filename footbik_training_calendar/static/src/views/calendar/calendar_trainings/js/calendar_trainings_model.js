/** @odoo-module **/

import {CalendarModel} from "@web/views/calendar/calendar_model";

export class CalendarTrainingsModel extends CalendarModel {

    /**
     * Override to add custom fields when loading records
     */
    async load(searchParams) {
        await super.load(searchParams);
        this._enrichRecordsWithCustomFields();
    }

    /**
     * Override to add custom fields when updating records
     */
    async updateRecord(record, changes) {
        const result = await super.updateRecord(record, changes);
        this._enrichRecordsWithCustomFields();
        return result;
    }

    /**
     * Add custom computed fields to all records
     */
    _enrichRecordsWithCustomFields() {
        if (!this.data || !this.data.records) return;

        // records is an object, not an array - iterate over values
        for (const record of Object.values(this.data.records)) {
            const raw = record.rawRecord;

            // Add custom fields directly to the record
            record.group_name = raw.class_group_id?.[1] || '';
            record.training_number = raw.name || '';
            record.max_count_children = `${raw.max_count_children || 0}/${raw.count_children || 0}/${raw.max_count_children || 0}`;
            record.trainer_names = [
                raw.trainer_id?.[1],
                raw.assistant_id?.[1]
            ].filter(Boolean).join(', ') || 'No trainer assigned';
        }
    }

}