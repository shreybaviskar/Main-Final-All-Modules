/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Dialog } from "@web/core/dialog/dialog";
import { patch } from "@web/core/utils/patch";
import { ErrorDialog } from "@web/core/errors/error_dialog";

/**
 * Patch Odoo global Error Dialog
 * Shows blocking popup when storage is 100%
 */
patch(ErrorDialog.prototype, {
    setup() {
        super.setup();

        const message = this.props.error?.message || "";

        if (message.includes("DATABASE STORAGE LIMIT EXCEEDED")) {
            this.isStorageBlocked = true;
        }
    },
});
