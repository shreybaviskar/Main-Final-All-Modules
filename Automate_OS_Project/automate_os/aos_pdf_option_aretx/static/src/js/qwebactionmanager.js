/** @odoo-module **/

import { registry } from "@web/core/registry";
import { PdfOptionsModal } from "./PdfOptionsModal";

let iframeForPrint;

function openPrintPreview(blobUrl, callback) {
    let iframe = iframeForPrint;
    if (!iframe) {
        iframe = iframeForPrint = document.createElement("iframe");
        iframe.style.display = "none";
        document.body.appendChild(iframe);
        iframe.onload = () => {
            setTimeout(() => {
                iframe.contentWindow.focus();
                iframe.contentWindow.print(); // 🔥 THIS opens Chrome print preview
                callback();
            }, 100);
        };
    }
    iframe.src = blobUrl;
}

function getReportUrl(action, type, env) {
    let url = `/report/${type}/${action.report_name}`;
    const ctx = action.context || env.services.user.context || {};

    if (ctx.active_ids?.length) {
        url += `/${ctx.active_ids.join(",")}`;
    }

    url += `?context=${encodeURIComponent(JSON.stringify(ctx))}`;
    return url;
}

registry.category("ir.actions.report handlers").add(
    "pdf_report_options_handler",
    async function (action, options, env) {

        if (action.report_type !== "qweb-pdf") {
            return false;
        }

        let selected = action.default_print_option;

        if (!selected) {
            selected = await new Promise((resolve) => {
                env.services.dialog.add(PdfOptionsModal, {
                    onSelectOption: resolve,
                    close: () => resolve("close"),
                });
            });

            if (selected === "close") {
                return true;
            }
        }

        const pdfUrl = getReportUrl(action, "pdf", env);

        // 🖨 PRINT → CHROME PRINT PREVIEW (LIKE SCREENSHOT)
        if (selected === "print") {
            env.services.ui.block();
            fetch(pdfUrl)
                .then((r) => r.blob())
                .then((blob) => {
                    const blobUrl = URL.createObjectURL(blob);
                    openPrintPreview(blobUrl, () => {
                        env.services.ui.unblock();
                    });
                })
                .catch(() => env.services.ui.unblock());
            return true;
        }

        // 📄 OPEN → NEW TAB ONLY
        if (selected === "open") {
            window.open(pdfUrl, "_blank");
            return true;
        }

        // 📥 DOWNLOAD → DIRECT DOWNLOAD
        if (selected === "download") {
            const link = document.createElement("a");
            link.href = pdfUrl;
            link.download = `${action.report_name}.pdf`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            return true;
        }

        return false;
    },
    { sequence: 1 }
);
