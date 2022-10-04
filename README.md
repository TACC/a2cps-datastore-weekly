# Weekly Reporting metrics for the A2CPS program
Docker container of Dash App to display A2CPS trial weekly reporting metrics.

This dashboard is intended for use by study personnel and others interested in the reasons why patients either complete or leave the trial.

## Dashboard Description

Data from the A2CPS program is loaded via apis that provide information on both all screened patients and those who continue into the program. This report receives this data from the a2cps_datastore_net network.

This data is cleaned and transformed to create the tables as outlined below.


# Weekly Report Data Processing
This section describes the data roll-ups for the Weekly Report.  See the code in the 'data_processing.py' file for the actual functions / code that carries this out.

## Screening
### Table 1. Number of Subjects Screened
Group and count data by center and surgery type.  
```
get_table_1_screening(subjects)  
```

### Table 2.a. Reasons for declining by Site
Group and count reasons to decline by center.  Note an individual can select more than one reason, so these are exploded into an individual row per reason.
```   
    display_terms_t2a = display_terms_dict_multi['reason_not_interested']  
    table2a = get_table_2a_screening(subjects, display_terms_t2a)
```

### Table 2.b. Reasons for declining ‘Additional Comments’
Display decline comments for the period of the report.  
```
table2b = get_table_2b_screening(subjects, start_report, end_report)
```

### Table 3. Number of Subjects Consented
Get a roll-up by site of the number of individuals who have consented, time since the last consent, number in the last 30 days, and total eligible / ineligible / rescinded.

Logic: The following logic defines a patient as 'eligible' for the study:
* All subjects: sp_inclcomply = 1, sp_inclage1884 = 1, sp_inclsurg = 1, sp_exclnoreadspkenglish = 0, sp_mricompatscr = 4
* Knee subjects: surgery_type = 'TKA', sp_exclarthkneerep = 0, sp_exclinfdxjoint = 0, sp_exclbilkneerep = 0
* Back subjects: surgery_type == 'Thoracic', sp_exclothmajorsurg = 0, sp_exclprevbilthorpro = 0
```
table3_data, table3 = get_table_3_screening(consented, today, 30)
```


## Study Status
### Table 4. Ongoing Study Status
Count number of patients by site according to study status.
Logic:
* 'Complete subjects' = sp_surg_date prior to report date
* Rescinded subjects = subjects with a date in the 'ewdateterm' column
```
table4 = get_table_4(consented, today)
```

### Table 5. Rescinded Consent & Table 6. Early Study Termination Listing
Information on Subjects with early termination date before surgery (Table 5) and early termination date after surgery (Table 6)
```
table5, table6 = get_tables_5_6(consented)
```


## Deviations
Provide detailed information on deviations and adverse events
* Table 8.a. Adverse Events
* Table 8.b. Description of Adverse Events
```
deviations = get_deviation_records(consented, adverse_events)
table7a = get_deviations_by_center(centers_df, consented, deviations, display_terms_dict_multi)
table7b = get_table7b_timelimited(deviations)
```

## Adverse Events
Provide detailed information on adverse events
* Table 8.a. Adverse Events
* Table 8.b. Description of Adverse Events
```
ae = get_adverse_event_records(consented, adverse_events)
table8a = get_adverse_events_by_center(centers_df, consented, ae, display_terms_dict_multi)
table8b = get_table_8b(ae, today, None)
```

### Demographic Characteristics
Use subject reported data unless it is missing, in which case use the fields from the screening instruments
Roll up data for the following characteristics by MCC and surgery type, showing the count and percent by category.

```
    demographics = get_demographic_data(consented)
    ### get subset of active patients
    demo_active = demographics[demographics['Status']=='Active'].copy()
    demo_active['category'] = demo_active.apply(lambda x: 'MCC ' + str(x['MCC'])  + ' / ' +x['Surgery'], axis=1)

    ### Currently splitting on MCC values
    split_col = 'category'
```

#### Gender
```
demo_df, demo_col, display_terms_dict, display_term_key = demo_active, 'Sex', display_terms_dict, 'sex'
sex = rollup_with_split_col(demo_df, demo_col, display_terms_dict, display_term_key, split_col)
```
#### Race
```
demo_df, demo_col, display_terms_dict, display_term_key = demo_active, 'Race', display_terms_dict, 'dem_race'
race = rollup_with_split_col(demo_df, demo_col, display_terms_dict, display_term_key, split_col)
```
#### Ethnicity
```
demo_df, demo_col, display_terms_dict, display_term_key = demo_active, 'Ethnicity', display_terms_dict, 'ethnic'
ethnicity = rollup_with_split_col(demo_df, demo_col, display_terms_dict, display_term_key, split_col)
```
#### Age - show statistical distribution by MCC/surgery since this is a continuous vs categorical variable  
```
age_df = demo_active.copy()
age_df["Age"] = pd.to_numeric(age_df["Age"], errors='coerce') # handle records that have no age value anywhere
age = get_describe_col_subset(age_df, 'Age', 'category')
```
