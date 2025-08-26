/** @odoo-module **/

import { registry } from "@web/core/registry";
import { CalendarTrainingsRenderer } from "./calendar_trainings";
import { CalendarArchParser } from "@web/views/calendar/calendar_arch_parser";
import { CalendarController } from "@web/views/calendar/calendar_controller";
import {CalendarTrainingsModel} from "./calendar_trainings_model";


export const calendarTrainingsView = {
    type: "calendar",

    display_name: "Calendar",
    icon: "fa fa-calendar",
    multiRecord: true,
    searchMenuTypes: ["filter", "favorite"],

    ArchParser: CalendarArchParser,
    Controller: CalendarController,
    Model: CalendarTrainingsModel,
    Renderer: CalendarTrainingsRenderer,

    buttonTemplate: "web.CalendarController.controlButtons",

    props: (props, view) => {
        const { ArchParser } = view;
        const { arch, relatedModels, resModel } = props;
        const archInfo = new ArchParser().parse(arch, relatedModels, resModel);
        return {
            ...props,
            Model: view.Model,
            Renderer: view.Renderer,
            buttonTemplate: view.buttonTemplate,
            archInfo,
        };
    },
};

registry.category("views").add("trainings_calendar", calendarTrainingsView);
