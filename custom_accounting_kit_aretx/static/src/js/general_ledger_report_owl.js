/** @odoo-module **/

import { registry } from "@web/core/registry";
const { Component, useState, onWillStart, onMounted, useRef } = owl;
import { useService } from "@web/core/utils/hooks";

const configModel = 'general.ledger.report.config';

export class GeneralLedgerReport extends Component {
    setup() {
        this.state = useState({
            ledgerData: [],
            groupedData: {},
            dateFrom: "",
            dateTo: "",
            selectedAccount: "",
            accounts: [],
            totals: {
                debit: 0,
                credit: 0,
                balance: 0
            },
            collapsedAccounts: {},
            fyDates: null,
            isDebug: Boolean(odoo.debug),
            config: {
                show_journal: true,
                show_date: true,
                show_communication: true,
                show_partner: true,
                show_currency: true,
                show_debit: true,
                show_credit: true,
                show_balance: true,
            },
        });

        this.ui = useService("ui");
        this.orm = useService("orm");
        this.dateFromRef = useRef("date-from");
        this.dateToRef = useRef("date-to");
        this.accountRef = useRef("account-filter");
        this.searchInput = useRef("search-input");

        onWillStart(async () => {
            await this.loadConfig();
            await this.loadAccounts();
            await this.initializeFinancialYearDates();
            await this.loadLedgerData();
        });

        onMounted(() => {
            // Set date picker values after DOM is ready
            if (this.state.fyDates) {
                if (this.dateFromRef.el) {
                    this.dateFromRef.el.value = this.state.fyDates.start;
                }
                if (this.dateToRef.el) {
                    this.dateToRef.el.value = this.state.fyDates.end;
                }
            }
        });

        this.action = useService("action");
    }

    async loadConfig() {
        if (!this.state.isDebug) {
            return;
        }
        try {
            const configRecord = await this.orm.call(
                configModel,
                'get_active_config',
                []
            );

            // Assuming configRecord contains fields like show_journal, etc.
            if (configRecord) {
                this.state.config = {
                    show_journal: configRecord.show_journal,
                    show_date: configRecord.show_date,
                    show_communication: configRecord.show_communication,
                    show_partner: configRecord.show_partner,
                    show_currency: configRecord.show_currency,
                    show_debit: configRecord.show_debit,
                    show_credit: configRecord.show_credit,
                    show_balance: configRecord.show_balance,
                };
            }
        } catch (error) {
            console.error("Failed to load General Ledger Configuration:", error);
            // Default config is used
        }
    }

    openDebugConfig = async function () {
        try {
            // 1. Call the Python method to get the active (and initialized) config record.
            const configRecord = await this.orm.call(
                configModel,
                'get_active_config',
                [] // No arguments for the @api.model method
            );

            // The ORM call returns the ID of the record.
            const configId = configRecord.id;

            // 2. Open the form view for the retrieved record ID.
            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: configModel,
                res_id: configId, // Pass the specific record ID
                view_mode: "form",
                target: "new",
                views: [[false, "form"]],
                name: "General Ledger Configuration",
            });
        } catch (error) {
            console.error("Failed to retrieve or initialize General Ledger Configuration:", error);
            // Optionally show a user-facing notification about the error
            this.env.services.notification.add(
                "Could not load the General Ledger Configuration.",
                { type: 'danger' }
            );
        }
    }

    async loadAccounts() {
        this.state.accounts = await this.orm.searchRead(
            "account.account",
            [['active', '=', true]],
            ["name", "code"]
        );
    }

    async initializeFinancialYearDates() {
        if (!this.state.dateFrom || !this.state.dateTo) {
            // Fetch current company's country
            const company = await this.orm.call("res.company", "get_current_company_country", []);
            const fyRange = this.getFinancialYearRange(company.country_code);

            this.state.dateFrom = fyRange.start;
            this.state.dateTo = fyRange.end;
            this.state.fyDates = fyRange; // Store for later use in onMounted
        }
    }

    async loadLedgerData() {
        let domain = [
            ['move_id.state', '=', 'posted'],
            ['account_id.active', '=', true]
        ];

        // Add date filters
        if (this.state.dateFrom) {
            domain.push(['date', '>=', this.state.dateFrom]);
        }
        if (this.state.dateTo) {
            domain.push(['date', '<=', this.state.dateTo]);
        }
        if (this.state.selectedAccount) {
            domain.push(['account_id', '=', parseInt(this.state.selectedAccount)]);
        }

        const lines = await this.orm.searchRead(
            "account.move.line",
            domain,
            ["move_name", "move_id", "date", "name", "partner_id", "account_id", "currency_id", "debit", "credit", "balance"]
        );

        this.state.ledgerData = await this.addCurrencySymbols(lines);
        await this.addInitialBalances();
        this.groupDataByAccount();
        this.calculateTotals();
    }

    async addInitialBalances() {
        // Use dateFrom from state or from the date input field
        const dateFrom = this.state.dateFrom || this.dateFromRef.el?.value;
        if (!dateFrom) return;

        // Get account IDs based on current filter
        let accountIds;
        if (this.state.selectedAccount || this.accountRef.el?.value) {
            // If specific account is selected, only get initial balance for that account
            const selectedAccountId = parseInt(this.state.selectedAccount || this.accountRef.el?.value);
            accountIds = [selectedAccountId];
        } else {
            // Get all account IDs
            accountIds = this.state.accounts.map(a => a.id);
        }

        if (!accountIds.length) return;

        // Fetch sum of debit/credit/balance before dateFrom
        const initialLines = await this.orm.searchRead(
            "account.move.line",
            [
                ['move_id.state', '=', 'posted'],
                ['account_id', 'in', accountIds],
                ['date', '<', dateFrom],
                ['account_id.active', '=', true]
            ],
            ["account_id", "debit", "credit", "balance", "currency_id"]
        );

        // Compute remaining/opening balance per account
        const openingBalances = {};

        initialLines.forEach(line => {
            const accId = line.account_id[0];
            if (!openingBalances[accId]) {
                openingBalances[accId] = { debit: 0, credit: 0, balance: 0, currency_id: line.currency_id };
            }
            openingBalances[accId].debit += line.debit;
            openingBalances[accId].credit += line.credit;
            openingBalances[accId].balance += line.balance;
        });

        // Add "Initial Balance" line to ledgerData
        this.state.ledgerData = [
            ...Object.keys(openingBalances).map(accId => {
                const ob = openingBalances[accId];
                return {
                    move_name: "Initial Balance",
                    move_id: [null, "Initial Balance"],
                    date: dateFrom,
                    name: "",
                    partner_id: null,
                    account_id: [parseInt(accId), this.state.accounts.find(a => a.id === parseInt(accId)).name],
                    currency_id: openingBalances[accId].currency_id,
                    debit: ob.debit,
                    credit: ob.credit,
                    balance: ob.balance,
                    currency_symbol: "$" // Will be overridden in addCurrencySymbols
                };
            }),
            ...this.state.ledgerData
        ];

        // Re-add symbols
        this.state.ledgerData = await this.addCurrencySymbols(this.state.ledgerData);
    }

    getFinancialYearRange(countryCode) {
        const today = new Date();
        let start, end;

        switch (countryCode) {
            //April 1 - March 31
            case 'IN': // India
            case 'JP': // Japan
            case 'CAD': //Canada
                start = new Date(today.getFullYear(), 3, 1); // April 1
                end = new Date(today.getFullYear() + 1, 2, 31); // March 31 next year
                if (today < start) { // If before April 1, go to previous FY
                    start = new Date(today.getFullYear() - 1, 3, 1);
                    end = new Date(today.getFullYear(), 2, 31);
                }
                break;

            // July 1 - June 30
            case 'AU': // Australia
            case 'NZD': // New Zealand
            case 'PKR': // Pakistan
                start = new Date(today.getFullYear(), 6, 1); // July 1
                end = new Date(today.getFullYear() + 1, 5, 30); // June 30 next year
                if (today < start) {
                    start = new Date(today.getFullYear() - 1, 6, 1);
                    end = new Date(today.getFullYear(), 5, 30);
                }
                break;

            // Jan 1 - Dec 31
            case 'FR': // France
            case 'DE': // Germany
            case 'BRL': // Brazil
            default: // Calendar year
                start = new Date(today.getFullYear(), 0, 1); // Jan 1
                end = new Date(today.getFullYear(), 11, 31); // Dec 31
                break;
        }

        // Add +1 day to both start and end
        start.setDate(start.getDate() + 1);
        end.setDate(end.getDate() + 1);

        // Format as YYYY-MM-DD for domain
        const formatDate = (d) => d.toISOString().slice(0, 10);
        return { start: formatDate(start), end: formatDate(end) };
    }

    toggleAccount(accountId) {
        this.state.collapsedAccounts[accountId] = !this.state.collapsedAccounts[accountId];
    }

    groupDataByAccount() {
        this.state.groupedData = {};
        this.state.collapsedAccounts = {};

        this.state.ledgerData.forEach(line => {
            if (line.debit === 0 && line.credit === 0 && line.balance === 0) {
                return; // skip
            }
            const accountKey = line.account_id[0];
            const accountName = line.account_id[1];

            if (!this.state.groupedData[accountKey]) {
                this.state.groupedData[accountKey] = {
                    accountName: accountName,
                    lines: [],
                    totals: { debit: 0, credit: 0, balance: 0 }
                };
                this.state.collapsedAccounts[accountKey] = true;
            }

            this.state.groupedData[accountKey].lines.push(line);
            this.state.groupedData[accountKey].totals.debit += line.debit;
            this.state.groupedData[accountKey].totals.credit += line.credit;
            this.state.groupedData[accountKey].totals.balance += line.balance;
        });
    }

    calculateTotals() {
        this.state.totals = { debit: 0, credit: 0, balance: 0 };

        this.state.ledgerData.forEach(line => {
            this.state.totals.debit += line.debit;
            this.state.totals.credit += line.credit;
            this.state.totals.balance += line.balance;
        });
    }

    async addCurrencySymbols(lines) {
        // Fetch all unique currency IDs from the lines
        const currencyIds = [...new Set(lines.map(line => line.currency_id ? line.currency_id[0] : false).filter(Boolean))];
        if (!currencyIds.length) return lines;

        const currencies = await this.orm.searchRead(
            "res.currency",
            [['id', 'in', currencyIds]],
            ["name", "symbol"]
        );

        const currencyMap = {};
        currencies.forEach(c => {
            currencyMap[c.id] = c.symbol;
        });

        // Add symbol to each line
        lines.forEach(line => {
            if (line.currency_id && line.currency_id[0]) {
                line.currency_symbol = currencyMap[line.currency_id[0]] || line.currency_id[1];
            } else {
                line.currency_symbol = '$'; // default
            }
        });

        return lines;
    }

    onSearchKeydown(ev) {
        if (ev.key === "Enter") {
            this.searchJournal();
        }
    }

    async searchJournal() {
        const text = this.searchInput.el.value.trim();

        // Base domain for posted, non-active lines
        const domain = [
            ['move_id.state', '=', 'posted'],
            ['account_id.active', '=', true]
        ];

        let dateFrom, dateTo;
        let foundAccountId = null;

        switch (this.state.dateType) {
            case "Month":
                if (this.state.selectedMonth) {
                    const monthIndex = new Date(`${this.state.selectedMonth} 1, 2000`).getMonth();
                    const year = new Date().getFullYear(); // Or state.selectedYear if you have it
                    dateFrom = new Date(year, monthIndex, 1);
                    dateTo = new Date(year, monthIndex + 1, 0); // Last day of month
                }
                break;
            case "Quarter":
                if (this.state.selectedQuarter) {
                    const year = new Date().getFullYear();
                    switch (this.state.selectedQuarter) {
                        case "Q1": dateFrom = new Date(year, 0, 1); dateTo = new Date(year, 2, 31); break;
                        case "Q2": dateFrom = new Date(year, 3, 1); dateTo = new Date(year, 5, 30); break;
                        case "Q3": dateFrom = new Date(year, 6, 1); dateTo = new Date(year, 8, 30); break;
                        case "Q4": dateFrom = new Date(year, 9, 1); dateTo = new Date(year, 11, 31); break;
                    }
                }
                break;
            case "Year":
                if (this.state.dateFrom && this.state.dateTo) {
                    dateFrom = new Date(this.state.dateFrom);
                    dateTo = new Date(this.state.dateTo);
                }
                break;
            case "Custom":
                if (this.state.dateFrom && this.state.dateTo) {
                    dateFrom = new Date(this.state.dateFrom);
                    dateTo = new Date(this.state.dateTo);
                }
                break;
            default:
                if (this.state.fyDates) {
                    dateFrom = new Date(this.state.fyDates.start);
                    dateTo = new Date(this.state.fyDates.end);
                }
        }

//        console.log(dateFrom);
//        console.log(dateTo);

        if (dateFrom && dateTo) {
            domain.push(['date', '>=', dateFrom.toISOString().slice(0, 10)]);
            domain.push(['date', '<=', dateTo.toISOString().slice(0, 10)]);
        }


        // If text exists, search by name, move_name, or partner
        if (text) {
            const accountSearchDomain = [['name', 'ilike', text]];
            const accounts = await this.orm.searchRead(
                "account.account",
                accountSearchDomain,
                ["id"]
            );

            if (accounts.length > 0) {
                foundAccountId = accounts[0].id;
            }

            domain.push('|');
            domain.push('|');
            domain.push('|');
            domain.push(['name', 'ilike', text]);
            domain.push(['move_name', 'ilike', text]);
            domain.push(['account_id.name', 'ilike', text]);
            domain.push(['partner_id.name', 'ilike', text]);
        }

        const originalSelectedAccount = this.state.selectedAccount;
        if (foundAccountId) {
            this.state.selectedAccount = foundAccountId.toString();
        } else {
            this.state.selectedAccount = null;
        }

        try {
            const lines = await this.orm.searchRead(
                "account.move.line",
                domain,
                ["move_name", "move_id", "date", "name", "partner_id", "account_id", "currency_id", "debit", "credit", "balance"]
            );

            this.state.ledgerData = await this.addCurrencySymbols(lines);
            await this.addInitialBalances();

            // Re-group & recalc totals
            this.groupDataByAccount();
            this.calculateTotals();
        } catch (e) {
            console.error("Search error:", e);
        } finally {
            this.state.selectedAccount = originalSelectedAccount;
        }
    }

    selectDateType(type) {
        this.state.dateType = type;
        // Reset previous selections
        this.state.selectedMonth = null;
        this.state.selectedQuarter = null;
        this.state.selectedYear = null;
        if (type === 'Custom') {
            this.state.dateFrom = this.dateFromRef.el?.value || '';
            this.state.dateTo = this.dateToRef.el?.value || '';
        }
    }

    selectMonth(month) {
        this.state.selectedMonth = month;
        // set dateFrom/dateTo accordingly
        const monthIndex = ['January','February','March','April','May','June','July','August','September','October','November','December'].indexOf(month);
        const year = new Date().getFullYear();
        this.state.dateFrom = `${year}-${String(monthIndex+1).padStart(2,'0')}-01`;
        this.state.dateTo = `${year}-${String(monthIndex+1).padStart(2,'0')}-${new Date(year, monthIndex+1, 0).getDate()}`;
        this.loadLedgerData();
    }

    selectQuarter(quarter) {
        this.state.selectedQuarter = quarter;
        const year = new Date().getFullYear();
        switch(quarter) {
            case 'Q1': this.state.dateFrom=`${year}-01-01`; this.state.dateTo=`${year}-03-31`; break;
            case 'Q2': this.state.dateFrom=`${year}-04-01`; this.state.dateTo=`${year}-06-30`; break;
            case 'Q3': this.state.dateFrom=`${year}-07-01`; this.state.dateTo=`${year}-09-30`; break;
            case 'Q4': this.state.dateFrom=`${year}-10-01`; this.state.dateTo=`${year}-12-31`; break;
        }
        this.loadLedgerData();
    }

    onYearChange(ev) {
        const year = parseInt(ev.target.value);
        if (!isNaN(year)) {
            this.state.dateFrom = `${year}-01-01`;
            this.state.dateTo = `${year}-12-31`;
            this.loadLedgerData();
        }
    }

    onCustomDateFromChange(ev) {
        const fromDate = ev.target.value;
        this.state.dateFrom = fromDate;

        // Restrict 'To' date
        if (this.dateToRef.el) {
            this.dateToRef.el.min = fromDate;

            // Optional: if current 'To' date is before 'From', reset it
            if (this.dateToRef.el.value && this.dateToRef.el.value < fromDate) {
                this.dateToRef.el.value = fromDate;
                this.state.dateTo = fromDate;
            }
        }
    }

    async applyFilters() {
        const domain = [
            ['move_id.state', '=', 'posted'],
            ['account_id.active', '=', true]
        ];

        // Only add filters if values are provided
        const dateFrom = this.dateFromRef.el?.value;
        const dateTo = this.dateToRef.el?.value;
        const selectedAccount = this.accountRef.el?.value;

        if (dateFrom) {
            domain.push(['date', '>=', dateFrom]);
        }
        if (dateTo) {
            domain.push(['date', '<=', dateTo]);
        }
        if (selectedAccount) {
            domain.push(['account_id', '=', parseInt(selectedAccount)]);
        }

        const lines = await this.orm.searchRead(
            "account.move.line",
            domain,
            ["move_name", "move_id", "date", "name", "partner_id", "account_id", "currency_id", "debit", "credit", "balance"]
        );

        this.state.ledgerData = await this.addCurrencySymbols(lines);

        // Update state with current filter values for initial balance calculation
        this.state.dateFrom = dateFrom;
        this.state.dateTo = dateTo;
        this.state.selectedAccount = selectedAccount;

        // Add initial balances based on the filtered date range
        await this.addInitialBalances();
        this.groupDataByAccount();
        this.calculateTotals();
    }

    getActiveDateRangeLabel() {
        // Month
        if (this.state.dateType === "Month" && this.state.selectedMonth) {
            return `Month: ${this.state.selectedMonth}`;
        }

        // Quarter with month range
        if (this.state.dateType === "Quarter" && this.state.selectedQuarter) {
            const quarterMap = {
                Q1: "Jan-Mar",
                Q2: "Apr-Jun",
                Q3: "Jul-Sep",
                Q4: "Oct-Dec",
            };
            return `Quarter: ${this.state.selectedQuarter} (${quarterMap[this.state.selectedQuarter] || ""})`;
        }

        // Year
        if (this.state.dateType === "Year" && this.state.dateFrom && this.state.dateTo) {
            const year = new Date(this.state.dateFrom).getFullYear();
            return `Year: ${year}`;
        }

        // Custom date range
        if (this.state.dateType === "Custom" && this.state.dateFrom && this.state.dateTo) {
            const formatDate = (d) => {
                const date = new Date(d);
                const day = String(date.getDate()).padStart(2, "0");
                const month = String(date.getMonth() + 1).padStart(2, "0");
                const year = date.getFullYear();
                return `${day}-${month}-${year}`;
            };
            return `Custom: ${formatDate(this.state.dateFrom)} → ${formatDate(this.state.dateTo)}`;
        }

        // Financial year
        if (this.state.fyDates) {
            const formatDate = (d) => {
                const date = new Date(d);
                const day = String(date.getDate()).padStart(2, "0");
                const month = String(date.getMonth() + 1).padStart(2, "0");
                const year = date.getFullYear();
                return `${day}-${month}-${year}`;
            };
            return `Financial Year: ${formatDate(this.state.fyDates.start)} → ${formatDate(this.state.fyDates.end)}`;
        }

        return "All Records";
    }

    formatCurrency(amount, currencySymbol = '$', currencyName = null) {
        // Determine if it's INR based on symbol or currency name
        const isINR = currencySymbol === '₹' ||
                      (currencyName && currencyName.toUpperCase().includes('INR')) ||
                      (currencyName && currencyName.toUpperCase().includes('RUPEE'));

        const isWhole = Number.isInteger(amount);

        if (isINR) {
            // Indian format: ₹ 1,05,000 (lakhs and crores system)
            let x = amount.toFixed(isWhole ? 0 : 2).split('.');
            let intPart = x[0];
            let decPart = x.length > 1 && x[1] !== '00' ? '.' + x[1] : '';

            // Handle Indian numbering system
            if (intPart.length > 3) {
                // Take last 3 digits
                let lastThree = intPart.substring(intPart.length - 3);
                let otherNumbers = intPart.substring(0, intPart.length - 3);

                // Apply Indian grouping (every 2 digits after first 3)
                if (otherNumbers !== '') {
                    otherNumbers = otherNumbers.replace(/\B(?=(\d{2})+(?!\d))/g, ',');
                    lastThree = ',' + lastThree;
                }

                intPart = otherNumbers + lastThree;
            }

            return currencySymbol + ' ' + intPart + decPart;
        } else {
            // International format: $ 105,000 (thousands system)
            let options = {
                minimumFractionDigits: isWhole ? 0 : 2,
                maximumFractionDigits: isWhole ? 0 : 2,
            };
            return currencySymbol + ' ' + amount.toLocaleString('en-US', options);
        }
    }

    viewJournalEntry(moveId) {
        if (!moveId) {
            return;
        }
            const action = {
                type: "ir.actions.act_window",
                res_model: "account.move",
                res_id: moveId,
                views: [[false, "form"]],
                target: "current", // opens in same window
            };
            this.env.services.action.doAction(action);
    }

    getAmountClass(amount) {
        if (amount < 0) return 'text-danger';
        return '';
    }

    formatToDDMMYYYY(dateStr) {
        if (!dateStr) return "";
        const date = new Date(dateStr);
        const day = String(date.getDate()).padStart(2, "0");
        const month = String(date.getMonth() + 1).padStart(2, "0");
        const year = date.getFullYear();
        return `${day}/${month}/${year}`;
    }

    formatDate(dateStr) {
        return this.formatToDDMMYYYY(dateStr);
    }

    getFilterTitle() {
        const textSearch = this.searchInput && this.searchInput.el ? this.searchInput.el.value.trim() : null;

        if (textSearch) {
            return `${textSearch}`;
        }

        return "All Records";
    }

    // Export to PDF
    async exportToPDF() {
        this.ui.block();
        try {
            const searchText = this.searchInput.el.value.trim();
            const dateFrom = this.state.dateFrom;
            const dateTo = this.state.dateTo;
            let month = null;
            let quarter = null;
            let year = null;

            if (this.state.dateType === 'Month' && this.state.selectedMonth) {
                // Convert Month name ('October') to month index (10)
                const monthNames = ['January','February','March','April','May','June','July','August','September','October','November','December'];
                month = monthNames.indexOf(this.state.selectedMonth) + 1; // 1-indexed month
                year = new Date(dateFrom).getFullYear(); // Get year from the calculated date range

            } else if (this.state.dateType === 'Quarter' && this.state.selectedQuarter) {
                // Pass the quarter label (Q1, Q2, etc.)
                quarter = this.state.selectedQuarter;
                year = new Date(dateFrom).getFullYear();

            } else if ((this.state.dateType === 'Year' || !this.state.dateType) && dateFrom) {
                // This covers 'Year' selection and the default Financial Year initialization
                year = new Date(dateFrom).getFullYear();
            }

            // Prepare data for PDF export
            const exportData = {
                date_from: dateFrom,
                date_to: dateTo,
                month: month,
                quarter: quarter,
                year: year,
                filter_title: this.getFilterTitle(),
                ledger_data: this.state.ledgerData,
                grouped_data: this.state.groupedData,
                totals: this.state.totals,
                company_info: await this.orm.call("res.company", "get_current_company_info", []),
                search_text: searchText,
            };

            // Call the PDF export method
            const result = await this.orm.call(
                "general.ledger.export",
                "export_general_ledger_pdf",
                [exportData]
            );

            if (result && result.url) {
                // Download the PDF
                window.open(result.url, '_blank');
            } else {
                throw new Error("PDF export failed: Server response did not contain a download URL. Result: " + JSON.stringify(result));
            }
        } catch (error) {
            console.error("Error exporting PDF:", error);
            throw error;
        } finally {
            this.ui.unblock();
        }
    }

    // Export to XLSX
    async exportToXLSX() {
        this.ui.block();
        try {
            const dateFrom = this.state.dateFrom;
            const dateTo = this.state.dateTo;
            let month = null;
            let quarter = null;
            let year = null;

            if (this.state.dateType === 'Month' && this.state.selectedMonth) {
                // Convert Month name ('October') to month index (10)
                const monthNames = ['January','February','March','April','May','June','July','August','September','October','November','December'];
                month = monthNames.indexOf(this.state.selectedMonth) + 1; // 1-indexed month
                year = new Date(dateFrom).getFullYear(); // Get year from the calculated date range

            } else if (this.state.dateType === 'Quarter' && this.state.selectedQuarter) {
                // Pass the quarter label (Q1, Q2, etc.)
                quarter = this.state.selectedQuarter;
                year = new Date(dateFrom).getFullYear();

            } else if ((this.state.dateType === 'Year' || !this.state.dateType) && dateFrom) {
                // This covers 'Year' selection and the default Financial Year initialization
                year = new Date(dateFrom).getFullYear();
            }

            // Prepare data for XLSX export
            const exportData = {
                date_from: dateFrom,
                date_to: dateTo,
                month: month,
                quarter: quarter,
                year: year,
                filter_title: this.getFilterTitle(),
                ledger_data: this.state.ledgerData,
                grouped_data: this.state.groupedData,
                totals: this.state.totals,
                company_info: await this.orm.call("res.company", "get_current_company_info", [])
            };

            // Call the XLSX export method
            const result = await this.orm.call(
                "general.ledger.export",
                "export_general_ledger_xlsx",
                [exportData]
            );

            if (result && result.url) {
                // Download the XLSX
                window.open(result.url, '_blank');
            } else {
                console.error("XLSX export failed");
            }
        } catch (error) {
            console.error("Error exporting XLSX:", error);
        } finally {
            this.ui.unblock();
        }
    }
}

GeneralLedgerReport.template = "custom_accounting_kit_aretx.GeneralLedgerReport";
registry.category("actions").add("custom_accounting_kit_aretx.general_ledger_owl", GeneralLedgerReport);