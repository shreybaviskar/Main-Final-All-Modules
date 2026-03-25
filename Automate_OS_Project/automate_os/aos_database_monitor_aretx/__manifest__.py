{
    "name": "Database Monitor",
    "version": "1.0",
    "summary": "Database storage monitoring with hard blocking on limit exceed",
    "category": "Administration",
    "author": "Areterix",
    "depends": ["base", "web"],

    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/database_monitor_views.xml",
        #"views/storage_exceeded_simple_template.xml",
    ],

    "assets": {
        "web.assets_backend": [

            # =====================
            # CSS
            # =====================
            "aos_database_monitor_aretx/static/src/css/storage.css",
            "aos_database_monitor_aretx/static/src/css/storage_warning.css",
            #"aos_database_monitor_aretx/static/src/css/storage_block.css",

            # =====================
            # JS
            # =====================
            "aos_database_monitor_aretx/static/src/js/storage_warning.js",
            #"aos_database_monitor_aretx/static/src/js/storage_blocking_popup.js",

            # =====================
            # XML Templates
            # =====================
            #"aos_database_monitor_aretx/static/src/xml/storage_blocking_popup.xml",
        ],
    },

    "installable": True,
    "application": True,
}
