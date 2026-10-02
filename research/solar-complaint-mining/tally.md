# Complaint tally (as of 2026-10-02)

- Tool: `tools/complaint_tally.py v1.0.0`
- Strict window starts 2025-10-02; extended starts 2024-10-02
- Window used for ranking: **extended** - 24-month window used because C2 had < 30 scanned items in the strict 12-month window
- Scanned items, strict window: {'C1': 73, 'C2': 17, 'C3': 59}
- Scanned items, 24-month window: {'C1': 73, 'C2': 35, 'C3': 65}
- Evidence rows: 67 total; 59 owner/prospective rows counted; excluded by voice {'bystander': 7, 'trade': 1}; dropped by window {}
- Validation problems: 0

## Ranked pains (owner/prospective items only)

| Rank | Pain tag | Items | Threads | Communities | Strict share | Equal-weight rank | Flags |
|---|---|---|---|---|---|---|---|
| 1 | `warranty_repair_delay_runaround` | 17 | 6 | C1/C2 | 100% | 1 | 41% from one thread |
| 2 | `monitoring_app_issues` | 12 | 3 | C1/C2 | 100% | 3 | 75% from one thread |
| 3 | `installer_aftersales_unresponsive` | 9 | 5 | C1/C3 | 78% | 4 | - |
| 4 | `financing_rent_to_own_terms` | 8 | 5 | C1/C3 | 50% | 2 | - |
| 5 | `inverter_fault_recurring` | 5 | 4 | C1 | 100% | 12 | - |
| 6 | `battery_failure_degradation` | 4 | 3 | C1/C2 | 75% | 8 | 50% from one thread |
| 7 | `savings_below_expectation` | 4 | 3 | C1/C3 | 100% | 10 | 50% from one thread |
| 8 | `workmanship_defects` | 4 | 3 | C1/C3 | 75% | 5 | 50% from one thread |
| 9 | `sseg_registration_burden` | 4 | 2 | C1/C2 | 100% | 9 | 75% from one thread |
| 10 | `installer_trust_scam_fear` | 3 | 2 | C1/C3 | 100% | 7 | 67% from one thread |
| 11 | `repeat_callout_fees` | 3 | 2 | C1 | 100% | 20 | 67% from one thread |
| 12 | `cannot_verify_installation_quality` | 2 | 2 | C1/C3 | 100% | 15 | 50% from one thread |

## Theme clusters (post-hoc, interpretation only; distinct rows)

| Cluster | Distinct rows | Threads | By community |
|---|---|---|---|
| after_sales_and_warranty | 27 | 11 | {'C1': 20, 'C2': 4, 'C3': 3} |
| equipment_faults | 12 | 8 | {'C1': 9, 'C2': 3} |
| monitoring_and_alerts | 12 | 3 | {'C1': 9, 'C2': 3} |
| financing_and_provider_trust | 10 | 6 | {'C1': 1, 'C3': 9} |
| install_quality_and_verification | 10 | 7 | {'C1': 4, 'C3': 6} |
| savings_and_billing | 7 | 5 | {'C1': 5, 'C2': 1, 'C3': 1} |
| regulation_and_registration | 4 | 2 | {'C1': 3, 'C2': 1} |

Below the top 12: `installation_delays_lead_time` (2), `installer_misconfiguration_settings` (2), `municipal_fixed_charge_solar_owners` (2), `inverter_battery_compat_config` (2), `repair_downtime_no_fallback` (2), `warranty_claim_rejected` (2), `billing_debit_order_errors` (1), `coc_compliance_integrity` (1), `firmware_update_failure` (1), `grid_connection_cost_delay` (1), `grid_voltage_issues` (1), `municipal_billing_metering_mismatch` (1), `refund_returns_refused` (1), `replacement_unit_quality` (1), `system_overpromised_mismatch` (1), `warranty_verification_serial` (1)

## Coverage (items read in the window used)

| Community | reddit | forum | review_site | facebook | x | app_review | product_review |
|---|---|---|---|---|---|---|---|
| C1 | 22 | 14 | 29 | 0 | 0 | 8 | 0 |
| C2 | 0 | 31 | 3 | 0 | 0 | 1 | 0 |
| C3 | 29 | 25 | 11 | 0 | 0 | 0 | 0 |
