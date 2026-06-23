/** @odoo-module **/

import { PivotRenderer } from "@web/views/pivot/pivot_renderer";
import { pivotView } from "@web/views/pivot/pivot_view";
import { GraphRenderer } from "@web/views/graph/graph_renderer";
import { graphView } from "@web/views/graph/graph_view";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class BiPivotRenderer extends PivotRenderer {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.user = useService("user");
    }

    async onPrintPdfClick() {
        const resModel = this.props.model.metaData.resModel;
        const domain = this.props.model.searchParams.domain || [];
        
        const action = await this.orm.call(
            resModel,
            "action_print_bi_report",
            [[]],
            { context: { ...this.user.context, active_domain: domain } }
        );
        
        if (action) {
            this.actionService.doAction(action);
        }
    }
}

export const biPivotView = {
    ...pivotView,
    Renderer: BiPivotRenderer,
    buttonTemplate: "dl_hotel_management.PivotView.Buttons",
    props: (genericProps, view) => {
        const props = pivotView.props(genericProps, view);
        props.buttonTemplate = view.buttonTemplate;
        return props;
    },
};

class BiGraphRenderer extends GraphRenderer {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.user = useService("user");
    }

    async onPrintPdfClick() {
        const resModel = this.props.model.metaData.resModel;
        const domain = this.props.model.searchParams.domain || [];
        
        const action = await this.orm.call(
            resModel,
            "action_print_bi_report",
            [[]],
            { context: { ...this.user.context, active_domain: domain } }
        );
        
        if (action) {
            this.actionService.doAction(action);
        }
    }
}

export const biGraphView = {
    ...graphView,
    Renderer: BiGraphRenderer,
    buttonTemplate: "dl_hotel_management.GraphView.Buttons",
};

registry.category("views").add("bi_pivot_view", biPivotView);
registry.category("views").add("bi_graph_view", biGraphView);
