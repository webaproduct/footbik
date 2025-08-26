/** @odoo-module **/

import {CalendarCommonRenderer} from "@web/views/calendar/calendar_common/calendar_common_renderer";
import {CalendarRenderer} from "@web/views/calendar/calendar_renderer";

export class CalendarTrainingsCommonRenderer extends CalendarCommonRenderer {
    static template = CalendarCommonRenderer.template;
    static eventTemplate = 'web.CalendarTrainingsCommonRenderer.event';

}

export class CalendarTrainingsRenderer extends CalendarRenderer {
    static components = {
        ...CalendarRenderer.components,
        week: CalendarTrainingsCommonRenderer,
        day: CalendarTrainingsCommonRenderer,
    };
}
