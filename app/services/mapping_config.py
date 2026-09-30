# =============================================================================
# Central CSV → Oracle Table Mapping Configuration
# Each key is the EXACT uploaded filename or supported alias.
# =============================================================================

IMPORT_CONFIG = {

    # ──────────────────────────────────────────────────────────────────────────
    # 1. triplicate_list.csv  →  a1_o1
    # ──────────────────────────────────────────────────────────────────────────
    "triplicate_list.csv": {
        "table": "a1_o1",

        # CSV columns whose values may arrive in scientific notation (E+N)
        "scientific_columns": ["EXP No", "ERC No"],

        # CSV columns that require stripping leading zeros (e.g. 000032520020432026 -> 32520020432026)
        "strip_leading_zero_columns": ["EXP No", "TRP AD", "Country Code"],

        # CSV columns for Currency Code (formatted to 2-digit codes e.g. 001 -> 01)
        "currency_code_columns": ["Currency Code", "CURRENCY_CODE"],

        # CSV columns that are date values (will be parsed → Python date object)
        "date_columns": [
            "Ship Date", "Overdue Date", "Invoice Date",
            "Triplicate Date", "TRP Entry Date", "Bank Bill Date"
        ],

        # CSV columns that are integer counts (formatted as clean integers without decimals)
        "integer_columns": ["Delay Days", "DELAY_DAYS"],

        # CSV columns that are monetary amounts & quantities (formatted to 2 decimal places)
        "numeric_columns": [
            "Quantity", "QUANTITY",
            "Invoice Amount", "INVOICE_AMOUNT", "Fob Amount", "FOB_AMOUNT", "Frieght", "FREIGHT",
            "Insurance", "INSURANCE", "Other Charges", "OTHER_CHARGES", "Amount Customs", "AMOUNT_CUSTOMS",
            "Triplicate Amount", "TRIPLICATE_AMOUNT", "Bank Charges", "BANK_CHARGES", "Rate BDT", "RATE_BDT",
            "CMT Customs", "CMT_CUSTOMS"
        ],

        # Unique business key for duplicate detection
        "duplicate_key_columns": ["EXP No"],

        # CSV header  →  Oracle column name (exact)
        "column_mapping": {
            "Bank Name":       "bank_name",
            "Branch Name":     "branch_name",
            "EXP No":          "exp_no",
            "Hscode":          "hs_code",
            "Unit Code":       "unit_code",
            "Unit Name":       "unit_name",
            "Quantity":        "quantity",
            "Exp Year":        "exp_year",
            "Country Code":    "country_code",
            "Country":         "country",
            "Currency Code":   "currency_code",
            "Currency":        "currency",
            "ERC No":          "erc_no",
            "Exporter Name":   "exporter_name",
            "Ship Date":       "ship_date",
            "Overdue Date":    "overdue_date",
            "LC/ Contract":    "contract",
            "Invoice No":      "invoice_no",
            "Invoice Date":    "invoice_date",
            "Invoice Amount":  "invoice_amount",
            "Fob Amount":      "fob_amount",
            "Frieght":         "frieght",
            "Insurance":       "insurance",
            "Other Charges":   "other_charges",
            "Amount Customs":  "amount_customs",
            "CMT Customs":     "cmt_customs",
            "Return ID":       "return_id",
            "Triplicate Date": "triplicate_date",
            "Rate BDT":        "rate_bdt",
            "TRP Entry Date":  "trp_entry_date",
            "Delay Days":      "delay_days",
            "Triplicate Amount": "triplicate_amount",
            "Bank Charges":    "bank_charges",
            "Bank Bill No":    "bank_bill_no",
            "Bank Bill Date":  "bank_bill_date",
            "TRP AD":          "trp_ad",
        },

        # Extra columns added to INSERT but NOT from CSV
        "extra_sql_columns": {
            "upload_date": "SYSDATE",
        },

        "expected_columns": [
            "Bank Name", "Branch Name", "EXP No", "Hscode", "Unit Code",
            "Unit Name", "Quantity", "Exp Year", "Country Code", "Country",
            "Currency Code", "Currency", "ERC No", "Exporter Name",
            "Ship Date", "Overdue Date", "LC/ Contract", "Invoice No",
            "Invoice Date", "Invoice Amount", "Fob Amount", "Frieght",
            "Insurance", "Other Charges", "Amount Customs", "CMT Customs",
            "Return ID", "Triplicate Date", "Rate BDT", "TRP Entry Date",
            "Delay Days", "Triplicate Amount", "Bank Charges",
            "Bank Bill No", "Bank Bill Date", "TRP AD",
        ],
    },

    # ──────────────────────────────────────────────────────────────────────────
    # 2. online_reported_arv_list.csv  →  arv
    # ──────────────────────────────────────────────────────────────────────────
    "online_reported_arv_list.csv": {
        "table": "arv",
        "duplicate_key_columns": ["ARV ID"],
        "scientific_columns": ["ARV ID", "HSCode", "ERC No."],
        "strip_leading_zero_columns": ["Country Code"],
        "currency_code_columns": ["Currency Code", "CURRENCY_CODE"],
        "date_columns": ["ARV Date", "Reporting Date"],
        "integer_columns": ["Delay Days", "DELAY_DAYS"],
        "numeric_columns": [
            "Quantity", "ARV Amount", "ARV Amount (USD)",
            "Adjusted Amount", "Adjusted Amount (USD)", "Rate BDT"
        ],
        "column_mapping": {
            "Bank Name":             "bank_name",
            "Branch Name":           "branch_name",
            "ARV ID":                "arv_id",
            "ARV Date":              "arv_date",
            "Reporting Date":        "reporting_date",
            "Delay Days":            "delay_days",
            "Importer":              "importer",
            "ERC No.":               "erc_no",
            "Exporter Name":         "exporter_name",
            "Bank Ref":              "bank_ref",
            "HSCode":                "hscode",
            "Country Code":          "country_code",
            "Country":               "country",
            "Unit Code":             "unit_code",
            "Unit":                  "unit",
            "Quantity":              "quantity",
            "Currency Code":         "currency_code",
            "Currency":              "currency",
            "Rate BDT":              "rate_bdt",
            "ARV Amount":            "arv_amount",
            "ARV Amount (USD)":      "arv_amount_usd",
            "Adjusted Amount":       "adjusted_amount",
            "Adjusted Amount (USD)":  "adjusted_amount_usd",
            "Cancel Yn":             "cancel_y_n",
            "Remarks":               "remarks",
        },
        "extra_sql_columns": {
            "upload_date": "SYSDATE",
        },
        "expected_columns": [
            "Bank Name", "Branch Name", "ARV ID", "ARV Date", "Reporting Date",
            "Delay Days", "Importer", "ERC No.", "Exporter Name", "Bank Ref",
            "HSCode", "Country Code", "Country", "Unit Code", "Unit",
            "Quantity", "Currency Code", "Currency", "Rate BDT", "ARV Amount",
            "ARV Amount (USD)", "Adjusted Amount", "Adjusted Amount (USD)",
            "Cancel Yn", "Remarks",
        ],
    },

    # ──────────────────────────────────────────────────────────────────────────
    # 3. e2-p2_rit_imp_report.csv  →  e2_p2
    # ──────────────────────────────────────────────────────────────────────────
    "e2-p2_rit_imp_report.csv": {
        "table": "e2_p2",
        "duplicate_key_columns": [],
        "scientific_columns": ["LC ID", "IMP No", "IRC No", "IMP Serial", "IMP Year"],
        "strip_leading_zero_columns": ["IMP No", "ADscode", "IMP Serial", "Country Of Origin", "Country of Import"],
        "currency_code_columns": ["Currency Code", "CURRENCY_CODE"],
        "date_columns": [],
        "numeric_columns": [
            "Total Quantity",
            "IMP Amount (Partial)", "IMP Amount (IMP wise)"
        ],
        "column_mapping": {
            "LC ID":                 "lc_id",
            "Pay Source":            "pay_source",
            "IMP No":                "imp_no",
            "ADscode":               "adscode",
            "IMP Serial":            "imp_serial",
            "IMP Year":              "imp_year",
            "Commodity":             "commodity",
            "Unit Code":             "unit_code",
            "Unit Name":             "unit_name",
            "Country Of Origin":     "country_of_origin",
            "Category Code":         "category_code",
            "Currency Code":         "currency_code",
            "Currency":              "currency",
            "Advance Y/N":           "advance_y_n",
            "Total Quantity":        "total_quantity",
            "IMP Amount (Partial)":  "imp_amount_partial",
            "IMP Amount (IMP wise)": "imp_amount_imp_wise",
            "IRC No":                "irc_no",
            "Importer Name":         "importer_name",
        },
        "extra_sql_columns": {
            "upload_date": "SYSDATE",
        },
        "expected_columns": [
            "LC ID", "Pay Source", "IMP No", "ADscode", "IMP Serial",
            "IMP Year", "Commodity", "Unit Code", "Unit Name",
            "Country of Import", "Country Of Origin", "Category Code",
            "Currency Code", "Currency", "Advance Y/N", "Total Quantity",
            "IMP Amount (Partial)", "IMP Amount (IMP wise)", "IRC No",
            "Importer Name",
        ],
    },

    # ──────────────────────────────────────────────────────────────────────────
    # 4. c_form_summary.csv  →  c_form
    # ──────────────────────────────────────────────────────────────────────────
    "c_form_summary.csv": {
        "table": "c_form",
        "duplicate_key_columns": ["CFORMID", "UNIQUE_ID"],
        "scientific_columns": ["CFORMID", "UNIQUE_ID", "BEN_ACCOUNT", "OUTWARD_REF", "BANK_REFERENCE"],
        "strip_leading_zero_columns": ["PURPOSE_CODE_SBB", "COUNTRY_CODE"],
        "currency_code_columns": ["CURRENCY_CODE", "Currency Code"],
        "date_columns": ["RECEIVEDATE", "PAYMENTDATE", "ENTRY_DATE"],
        "numeric_columns": ["FCAMOUNT", "round", "FC_IN_USD", "BDT"],
        "column_mapping": {
            "CFORMID":          "cformid",
            "BANK_NAME":        "bank_name",
            "ADSCODE":          "adscode",
            "BRANCH_NAME":      "branch_name",
            "CURRENCY_NAME":    "currency_name",
            "FCAMOUNT":         "fcamount",
            "FC_IN_USD":        "fc_in_usd",
            "RECEIVEDATE":      "receivedate",
            "RADDRESS":         "raddress",
            "RNATIONALITY":     "rnationality",
            "RBANK":            "rbank",
            "APPLICANT":        "applicant",
            "DETAILADDRESS":    "detailaddress",
            "BEN_ACCOUNT":      "ben_account",
            "PURPOSE_CODE_SBB": "purpose_code_sbb",
            "PAYMENTDATE":      "paymentdate",
            "ENTRY_DATE":       "entry_date",
            "OUTWARD_REF":      "outward_ref",
            "BANK_REFERENCE":   "bank_reference",
            "COUNTRY_CODE":     "country_code",
            "COUNTRY_NAME":     "country_name",
            "CURRENCY_CODE":    "currency_code",
            "BDT":              "bdt",
            "UNIQUE_ID":        "unique_id",
        },
        "extra_sql_columns": {
            "upload_date": "SYSDATE",
        },
        "expected_columns": [
            "CFORMID", "BANK_NAME", "ADSCODE", "BRANCH_NAME", "CURRENCY_NAME",
            "FCAMOUNT", "round", "FC_IN_USD", "RECEIVEDATE", "RADDRESS",
            "RNATIONALITY", "RBANK", "APPLICANT", "DETAILADDRESS",
            "BEN_ACCOUNT", "PURPOSE_CODE_SBB", "PAYMENTDATE", "ENTRY_DATE",
            "OUTWARD_REF", "BANK_REFERENCE", "COUNTRY_CODE", "COUNTRY_NAME",
            "CURRENCY_CODE", "BDT", "UNIQUE_ID",
        ],
    },

    # ──────────────────────────────────────────────────────────────────────────
    # 5. report_tm_main_for_bank_ho.csv  →  e3_p3
    # ──────────────────────────────────────────────────────────────────────────
    "report_tm_main_for_bank_ho.csv": {
        "table": "e3_p3",
        "duplicate_key_columns": ["ID_TMF", "SERIAL"],
        "scientific_columns": ["ID_TMF", "UNIQUE_ID", "BANK_REFERENCE", "INWARD_REF"],
        "strip_leading_zero_columns": ["ID_TMF", "COUNTRY_CODE"],
        "currency_code_columns": ["CURRENCY_CODE", "Currency Code"],
        "date_columns": [
            "ENTRY_DATE", "TM_DATE", "APPROVAL_DATE",
            "PASSPORT_DATE", "PASSPORT_EXPIRY_DATE"
        ],
        "numeric_columns": [
            "FC_AMOUNT", "round", "FC_IN_USD", "EFFECTED_REMITTANCE",
            "ISSUED_NOTES_COINS", "ISSUED_TC", "ISSUED_LC",
            "MOP_CASH", "MOP Cash", "MOP_TC", "MOP Tc", "MOP_CARD", "MOP Card", "MOP_FDD", "MOP Fdd",
            "MOP_MT", "MOP Mt", "MOP_OTHER", "MOP Other", "MOP_OTHERS", "SFC_BANK", "SFC Bank", "SFC_FC_AC", "SFC Fc Ac",
            "SFC_ERQ", "SFC Erq", "SFC_OTHER", "SFC Other", "SFC_OTHERS", "AMOUNT_IN_BDT"
        ],
        "column_mapping": {
            "ID_TMF":               "id_tmf",
            "SERIAL":               "serial",
            "TM_FOR":               "tm_for",
            "ADDRESSEE_ID":         "addressee_id",
            "ADSCODE":              "adscode",
            "FC_AMOUNT":            "fc_amount",
            "FC_IN_USD":            "fc_in_usd",
            "CURRENCY_CODE":       "currency_code",
            "COUNTRY_CODE":        "country_code",
            "PURPOSE_CODE_SBB":    "purpose_code_sbb",
            "COMPANY_ID":           "company_id",
            "BENEFICIARY_DETAILS":  "beneficiary_details",
            "APPLICANT_NAME":       "applicant_name",
            "APPLICANT_ADDRESS":    "applicant_address",
            "ISSUED_NOTES_COINS":   "issued_notes_coins",
            "ISSUED_TC":            "issued_tc",
            "ISSUED_LC":            "issued_lc",
            "EFFECTED_REMITTANCE":  "effected_remittance",
            "FX_MANUAL_PARA":       "fx_manual_para",
            "BB_APPROVAL_NO":       "bb_approval_no",
            "APPROVAL_DATE":        "approval_date",
            "INSTRUMENT_ID":        "instrument_id",
            "MONTH_ID":             "month_id",
            "CATEGORY_CODE":        "category_code",
            "ENTRY_DATE":           "entry_date",
            "TM_DATE":              "tm_date",
            "JU_COMPANY_NAME":      "ju_company_name",
            "COMPANY_TYPE_ID":      "company_type_id",
            "MOP_CASH":             "mop_cash",
            "MOP_TC":               "mop_tc",
            "MOP_CARD":             "mop_card",
            "MOP_FDD":              "mop_fdd",
            "MOP_MT":               "mop_mt",
            "MOP_OTHER":            "mop_other",
            "SFC_BANK":             "sfc_bank",
            "SFC_FC_AC":            "sfc_fc_ac",
            "SFC_ERQ":              "sfc_erq",
            "SFC_OTHER":            "sfc_other",
            "AMOUNT_IN_BDT":        "amount_in_bdt",
            "CONTACT_NO":           "contact_no",
            "BANK_REFERENCE":       "bank_reference",
            "INWARD_REF":           "inward_ref",
            "ISO":                  "iso",
            "UNIQUE_ID":            "unique_id",
            "PASSPORT_NO":          "passport_no",
            "CITIZEN_NAME":         "citizen_name",
            "PASSPORT_DATE":        "passport_date",
            "PASSPORT_EXPIRY_DATE": "passport_expiry_date",
            "Bank Name":            "bank_name",
            "COUNTRY_NAME":         "country_name",
        },
        "extra_sql_columns": {
            "upload_date": "SYSDATE",
        },
        "expected_columns": [
            "ID_TMF", "SERIAL", "TM_FOR", "ADDRESSEE_ID", "ADSCODE",
            "FC_AMOUNT", "round", "FC_IN_USD", "CURRENCY_CODE", "COUNTRY_CODE",
            "PURPOSE_CODE_SBB", "COMPANY_ID", "BENEFICIARY_DETAILS",
            "APPLICANT_NAME", "APPLICANT_ADDRESS", "ISSUED_NOTES_COINS",
            "ISSUED_TC", "ISSUED_LC", "EFFECTED_REMITTANCE", "FX_MANUAL_PARA",
            "BB_APPROVAL_NO", "APPROVAL_DATE", "INSTRUMENT_ID", "MONTH_ID",
            "CATEGORY_CODE", "ENTRY_DATE", "TM_DATE", "JU_COMPANY_NAME",
            "COMPANY_TYPE_ID", "MOP_CASH", "MOP_TC", "MOP_CARD", "MOP_FDD",
            "MOP_MT", "MOP_OTHER", "SFC_BANK", "SFC_FC_AC", "SFC_ERQ",
            "SFC_OTHER", "AMOUNT_IN_BDT", "CONTACT_NO", "BANK_REFERENCE",
            "INWARD_REF", "ISO", "UNIQUE_ID", "PASSPORT_NO", "CITIZEN_NAME",
            "PASSPORT_DATE", "PASSPORT_EXPIRY_DATE", "Bank Name",
            "COUNTRY_NAME",
        ],
    },

    # ──────────────────────────────────────────────────────────────────────────
    # 6. details_tm_data_from_imp_entry_(tm_date_wise).csv  →  bbreturn_manual_tm
    # ──────────────────────────────────────────────────────────────────────────
    "details_tm_data_from_imp_entry_(tm_date_wise).csv": {
        "table": "bbreturn_manual_tm",
        "duplicate_key_columns": ["ID_TMF"],
        "scientific_columns": ["ID_TMF", "Lc Id", "IMP No", "APPLICANT ACCOUNT NUMBER"],
        "strip_leading_zero_columns": ["ID_TMF", "IMP No", "Lc Id", "PURPOSE_CODE", "ADSCODE", "COUNTRY_CODE"],
        "currency_code_columns": ["CURRENCY_CODE", "Currency Code"],
        "date_columns": ["TM_DATE", "ENTRY_DATE"],
        "numeric_columns": [
            "FC_AMOUNT", "AMOUNT_BDT", "MOP Cash", "MOP_CASH", "MOP Tc", "MOP_TC",
            "MOP Card", "MOP_CARD", "MOP Fdd", "MOP_FDD", "MOP Mt", "MOP_MT", "MOP Other", "MOP_OTHER", "MOP_OTHERS",
            "SFC Bank", "SFC_BANK", "SFC Fc Ac", "SFC_FC_AC", "SFC Erq", "SFC_ERQ", "SFC Other", "SFC_OTHER", "SFC_OTHERS"
        ],
        "column_mapping": {
            "BANK_NAME":                "bank_name",
            "ADSCODE":                  "adscode",
            "BRANCH_NAME":              "branch_name",
            "ID_TMF":                   "id_tmf",
            "TM_FOR":                   "tm_for",
            "CURRENCY_CODE":           "currency_code",
            "CURRENCY":                "currency",
            "FC_AMOUNT":                "fc_amount",
            "COUNTRY_CODE":            "country_code",
            "COUNTRY":                 "country",
            "PURPOSE_CODE":            "purpose_code",
            "PURPOSE":                 "purpose",
            "BENEFICIARY_DETAILS":      "beneficiary_details",
            "APPLICANT_NAME":           "applicant_name",
            "APPLICANT ACCOUNT NUMBER": "applicant_account_number",
            "FX_MANUAL":                "fx_manual",
            "CATEGORY_CODE":            "category_code",
            "CATEGORY_NAME":            "category_name",
            "TM_DATE":                  "tm_date",
            "ENTRY_DATE":               "entry_date",
            "CONTACT_NO":               "contact_no",
            "AMOUNT_BDT":               "amount_bdt",
            "Lc Id":                    "lc_id",
            "IMP No":                   "imp_no",
            "Confirmed":                "confirmed",
            "MOP Cash":                 "mop_cash",
            "MOP Tc":                   "mop_tc",
            "MOP Card":                 "mop_card",
            "MOP Fdd":                  "mop_fdd",
            "MOP Mt":                   "mop_mt",
            "MOP Other":                "mop_other",
            "SFC Bank":                 "sfc_bank",
            "SFC Fc Ac":                "sfc_fc_ac",
            "SFC Erq":                  "sfc_erq",
            "SFC Other":                "sfc_other",
        },
        "extra_sql_columns": {
            "upload_date": "SYSDATE",
        },
        "expected_columns": [
            "BANK_NAME", "ADSCODE", "BRANCH_NAME", "ID_TMF", "TM_FOR",
            "CURRENCY_CODE", "CURRENCY", "FC_AMOUNT", "COUNTRY_CODE",
            "COUNTRY", "PURPOSE_CODE", "PURPOSE", "BENEFICIARY_DETAILS",
            "APPLICANT_NAME", "APPLICANT ACCOUNT NUMBER", "FX_MANUAL",
            "CATEGORY_CODE", "CATEGORY_NAME", "TM_DATE", "ENTRY_DATE",
            "CONTACT_NO", "AMOUNT_BDT", "Lc Id", "IMP No", "Confirmed",
            "MOP Cash", "MOP Tc", "MOP Card", "MOP Fdd", "MOP Mt",
            "MOP Other", "SFC Bank", "SFC Fc Ac", "SFC Erq", "SFC Other",
        ],
    },
}

# Alias map for flexible filename lookup
FILENAME_ALIASES = {
    "imp_report_(e2-p2) (1).csv": "e2-p2_rit_imp_report.csv",
    "imp_report_(e2-p2).csv":     "e2-p2_rit_imp_report.csv",
    "e2-p2_rit_imp_report (1).csv": "e2-p2_rit_imp_report.csv",
}


def get_mapping(filename: str):
    """Retrieve mapping config for a given filename or alias."""
    if not filename:
        return None
    cleaned_name = filename.strip().lower()
    
    # Direct match
    for key, config in IMPORT_CONFIG.items():
        if key.lower() == cleaned_name:
            return config
            
    # Alias match
    for alias, primary in FILENAME_ALIASES.items():
        if alias.lower() == cleaned_name:
            return IMPORT_CONFIG.get(primary)

    return None
