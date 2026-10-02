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
        // Una línea por moneda ACTIVA con tasa; USD trae compra y venta.
        const lines = info.rates.map((rate) => {
            if (rate.buy) {
                return `${rate.code} · Compra ₡${rate.buy.toFixed(2)} · Venta ₡${rate.sell.toFixed(2)} (${rate.date})`;
            }
            return `${rate.code} · ₡${rate.sell.toFixed(2)} (${rate.date})`;
        });
        lines.push("Fuente: Hacienda CR");
        if (info.last_sync) {
            lines.push(`Sincronizado: ${info.last_sync}`);
        }
        return lines.join("\n");
    }

    openRates() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Tipos de cambio",
            res_model: "res.currency.rate",
            views: [[false, "list"]],
        });
    }
}

registry.category("systray").add(
    "tipos_cambio_bccr.hacienda_rate",
    { Component: HaciendaRateSystray },
    { sequence: 25 }
);
