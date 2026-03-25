/** @odoo-module **/

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

// Wait for registry to be ready
const userMenuRegistry = registry.category("user_menuitems");

// Remove items after a small delay to ensure registry is populated
setTimeout(() => {
    ["documentation", "support", "odoo_account"].forEach((item) => {
        try {
            if (userMenuRegistry.contains(item)) {
                userMenuRegistry.remove(item);
            }
        } catch (e) {
            console.warn(`Could not remove ${item} from user menu:`, e);
        }
    });
}, 0);