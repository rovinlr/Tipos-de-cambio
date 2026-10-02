import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class HaciendaRateSystray extends Component {
    static template = "tipos_cambio_bccr.HaciendaRateSystray";
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ info: null });
        onWillStart(async () => {
            try {
                this.state.info = await this.orm.call(
                    "res.currency",
                    "get_hacienda_systray_info",
                    []
                );
            } catch {
                // Sin tasa o sin permisos: el indicador simplemente no se muestra.
                this.state.info = null;
            }
        });
    }

    get tooltip() {
        const info = this.state.info;
        if (!info) {
            return "";
        }
        const parts = [];
        if (info.buy) {
            parts.push(`Compra ₡${info.buy.toFixed(2)}`);
        }
        parts.push(`Venta ₡${info.sell.toFixed(2)}`);
        parts.push(`TC Hacienda del ${info.date}`);
        if (info.last_sync) {
            parts.push(`Sincronizado: ${info.last_sync}`);
        }
        return parts.join(" · ");
    }

    openRates() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Tipos de cambio (USD)",
            res_model: "res.currency.rate",
            views: [[false, "list"]],
            domain: [["currency_id.name", "=", "USD"]],
        });
    }
}

registry.category("systray").add(
    "tipos_cambio_bccr.hacienda_rate",
    { Component: HaciendaRateSystray },
    { sequence: 25 }
);
