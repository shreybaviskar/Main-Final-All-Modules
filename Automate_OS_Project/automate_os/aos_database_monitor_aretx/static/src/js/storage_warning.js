/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";

/**
 * Storage Warning Banner Service
 * Shows a warning banner at the top when storage exceeds 90%
 */


// Register the service
export const storageWarningService = {
    dependencies: ["orm"],

    start(env) {
        // Check if user has Super Role - if yes, don't show any warnings
        const isSuperUser = async () => {
            try {
                // Get current user data with groups
                const userId = env.services.user.userId;
                if (!userId) {
                    return false;
                }
                
                const userData = await env.services.orm.read(
                    "res.users",
                    [userId],
                    ["groups_id"]
                );
                
                if (userData && userData[0] && userData[0].groups_id && userData[0].groups_id.length > 0) {
                    const groups = await env.services.orm.read(
                        "res.groups",
                        userData[0].groups_id,
                        ["name", "category_id", "full_name"]
                    );
                    
                    for (const group of groups) {
                        const groupName = (group.name || '').toLowerCase();
                        const fullName = (group.full_name || '').toLowerCase();
                        let categoryName = '';
                        
                        if (group.category_id) {
                            if (Array.isArray(group.category_id)) {
                                categoryName = (group.category_id[1] || '').toLowerCase();
                            } else if (typeof group.category_id === 'object') {
                                categoryName = (group.category_id.name || '').toLowerCase();
                            }
                        }
                        
                        // Check for exact "Super Role" group or any Super/Settings access
                        if (groupName === 'super role' || 
                            groupName.includes('super role') ||
                            groupName.includes('super') || 
                            groupName.includes('settings') ||
                            groupName.includes('system') ||
                            fullName.includes('super role') ||
                            fullName.includes('super') ||
                            fullName.includes('settings') ||
                            categoryName.includes('settings')) {
                            console.debug(`Super Role user detected via group: ${group.name}`);
                            return true;
                        }
                    }
                }
            } catch (error) {
                console.debug("Could not check super user:", error);
            }
            return false;
        };

        // Check storage warning on startup
        const checkWarning = async () => {
            try {
                // First check if user is Super User - if yes, skip all checks
                const isSuper = await isSuperUser();
                if (isSuper) {
                    console.debug("Super Role user detected - skipping storage warning");
                    return;
                }
                
                const records = await env.services.orm.searchRead(
                    "database.monitor",
                    [],
                    ["show_storage_warning", "storage_usage_text", "storage_percent"],
                    { limit: 1 }
                );

                if (records.length > 0 && records[0].show_storage_warning) {
                    showWarningBanner(records[0]);
                }
            } catch (error) {
                console.error("Storage warning check failed:", error);
            }
        };

        const showWarningBanner = (storageData) => {
            const existingBanner = document.querySelector('.storage-warning-banner');
            if (existingBanner) {
                return;
            }

            const banner = document.createElement('div');
            banner.className = 'storage-warning-banner';
            banner.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                color: #FFFFFF;
                background-color: #D0442C;

                padding: 12px 20px;
                text-align: center;
                font-size: 14px;
                font-weight: 500;
                z-index: 9999;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
            `;

            const message = document.createElement('span');
            message.innerHTML = `
                Please contact support to upgrade your storage, for uninterrupted usage

            `;



            banner.appendChild(message);


            document.body.insertBefore(banner, document.body.firstChild);

            // Adjust navbar position
            const navbar = document.querySelector('.o_navbar');
            if (navbar) {
                navbar.style.marginTop = '48px';
            }
        };

        // Check on startup
        checkWarning();

        // Return service API if needed
        return {
            checkStorageWarning: checkWarning,
        };
    },
};

registry.category("services").add("storageWarning", storageWarningService);