/** @odoo-module **/

import { PivotRenderer } from "@web/views/pivot/pivot_renderer";
import { PivotController } from "@web/views/pivot/pivot_controller";
import { pivotView } from "@web/views/pivot/pivot_view";
import { GraphRenderer } from "@web/views/graph/graph_renderer";
import { GraphController } from "@web/views/graph/graph_controller";
import { graphView } from "@web/views/graph/graph_view";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

async function printBiReport(comp) {
    const model = comp.model || (comp.props && comp.props.model);
    if (!model) return;
    const resModel = model.metaData.resModel;
    const domain = (model.searchParams && model.searchParams.domain) || [];
    const action = await comp.orm.call(
        resModel,
        "action_print_bi_report",
        [[]],
        { context: { active_domain: domain } }
    );
    if (action) {
        comp.actionService.doAction(action);
    }
}

class BiPivotController extends PivotController {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.orm = useService("orm");
    }
    async onPrintPdfClick() {
        await printBiReport(this);
    }
}

class BiPivotRenderer extends PivotRenderer {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.orm = useService("orm");
    }
    async onPrintPdfClick() {
        await printBiReport(this);
    }
}

export const biPivotView = {
    ...pivotView,
    Controller: BiPivotController,
    Renderer: BiPivotRenderer,
    buttonTemplate: "dl_hotel_management.PivotView.Buttons",
};

class BiGraphController extends GraphController {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.orm = useService("orm");
    }
    async onPrintPdfClick() {
        await printBiReport(this);
    }
}

class BiGraphRenderer extends GraphRenderer {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.orm = useService("orm");
    }
    async onPrintPdfClick() {
        await printBiReport(this);
    }
}

export const biGraphView = {
    ...graphView,
    Controller: BiGraphController,
    Renderer: BiGraphRenderer,
    buttonTemplate: "dl_hotel_management.GraphView.Buttons",
};

try {
    const viewRegistry = registry.category("views");
    if (!viewRegistry.contains("bi_pivot_view")) {
        viewRegistry.add("bi_pivot_view", biPivotView);
    }
    if (!viewRegistry.contains("bi_graph_view")) {
        viewRegistry.add("bi_graph_view", biGraphView);
    }
} catch (e) {
    // Fallback across Odoo versions
}
