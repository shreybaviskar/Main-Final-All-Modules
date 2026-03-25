/** @odoo-module **/

import { registry } from "@web/core/registry";


// user menu registry
const userMenuRegistry = registry.category("user_menuitems");

if (userMenuRegistry.contains("documentation")) {
    userMenuRegistry.remove("documentation");
}

if (userMenuRegistry.contains("support")) {
    userMenuRegistry.remove("support");
}

if (userMenuRegistry.contains("odoo_account")) {
    userMenuRegistry.remove("odoo_account");
}
