# ----------------------------------------------------------------------------
# PYTHON LIBRARIES
# ----------------------------------------------------------------------------
import traceback

# Dash Framework
import dash_bootstrap_components as dbc
from dash import Dash, callback, clientside_callback, html, dcc, dash_table as dt, Input, Output, State, MATCH, ALL
from dash.exceptions import PreventUpdate
import dash_daq as daq

from dash_extensions import Download
from dash_extensions.snippets import send_file

# import local modules
from config_settings import *
from datastore_loading import *
from data_processing import *
from styling import *

# for export
import logging
import io
import flask

# Plotly graphing
import plotly.graph_objects as go

# ----------------------------------------------------------------------------
# DEBUGGING
# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
# APP Settings
# ----------------------------------------------------------------------------

external_stylesheets_list = [dbc.themes.SANDSTONE] #  set any external stylesheets

app = Dash(__name__,
                external_stylesheets=external_stylesheets_list,
                meta_tags=[{'name': 'viewport', 'content': 'width=device-width, initial-scale=1'}],
                assets_folder=ASSETS_PATH,
                requests_pathname_prefix=os.environ.get("REQUESTS_PATHNAME_PREFIX", "/"),
                suppress_callback_exceptions=True
                )
gunicorn_logger = logging.getLogger('gunicorn.error')
app.logger = logging.getLogger("weekly_ui")
app.logger.handlers = gunicorn_logger.handlers
app.logger.setLevel(logging.INFO)


# ----------------------------------------------------------------------------
# POINTERS TO DATA FILES AND APIS
# ----------------------------------------------------------------------------
local_data_date = '08/15/22'
display_terms_file = 'A2CPS_display_terms.csv'

# Directions for locating file at TACC
file_url_root ='https://api.a2cps.org/files/v2/download/public/system/a2cps.storage.community/reports'
report = 'subjects'
report_suffix = report + '-[mcc]-latest.json'
mcc_list=[1,2]


# ----------------------------------------------------------------------------
# FUNCTIONS FOR DASH UI COMPONENTS
# ----------------------------------------------------------------------------
def build_datatable_from_table_dict(table_dict, key, table_id, fill_width = False):
    try:
        table_columns = table_dict[key]['columns_list']
        table_data = table_dict[key]['data']
        new_datatable =  dt.DataTable(
                id = table_id,
                columns=table_columns,
                data=table_data,
                css=[{'selector': '.row', 'rule': 'margin: 0; flex-wrap: nowrap'},
                     {'selector':'.export','rule':export_style }
                    # {'selector':'.export','rule':'position:absolute;right:25px;bottom:-35px;font-family:Arial, Helvetica, sans-serif,border-radius: .25re'}
                    ],
                style_cell= {
                    'text-align':'left',
                    'vertical-align': 'top',
                    'font-family':'sans-serif',
                    'padding': '5px',
                    'whiteSpace': 'normal',
                    'height': 'auto',
                    },
                style_as_list_view=True,
                style_header={
                    'backgroundColor': 'grey',
                    'whiteSpace': 'normal',
                    'fontWeight': 'bold',
                    'color': 'white',
                },

                fill_width=fill_width,
                # style_table={'overflowX': 'auto'},
                # export_format="csv",
                merge_duplicate_headers=True,
            )
        return new_datatable
    except Exception as e:
        traceback.print_exc()
        return None

def generate_enrollment_figure(df, x_col, bar_col, line_col, title):
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x = df[x_col],
            y= df[bar_col],
            name= bar_col
        ))

    fig.add_trace(
        go.Scatter(
            x = df[x_col],
            y= df[line_col],
            name = line_col
        ))

    fig.update_layout(
        legend=dict(
            yanchor="bottom",
            y=0.02,
            xanchor="right",
            x=.98
        ),
        yaxis_title=title,
        margin=dict(l=20, r=20, t=0, b=20),
                     )
    return fig

def generate_site_info(enrollment, site, id_index, table_display = 'none'):
    site_div = html.Div([
        html.P(site),
        html.P(id_index),
        dt.DataTable(
                id='table_e',
                columns=[{"name": i, "id": i} for i in enrollment.columns],
                data=enrollment.to_dict('records'),
            )
    ])
    # df = get_site_enrollment(enrollment, site)
    # table_id = join('table_', id_index)
    # site_div = html.Div(
    #     dt.DataTable(
    #             id=table_id,
    #             columns=[{"name": i, "id": i} for i in df.columns],
    #             data=df.to_dict('records'),
    #         )
    # )
    return site_div

def generate_site_div(site, df, id_index, table_display = 'none'):
    # df = get_site_enrollment(enrollment, site)

    # Figures
    fig_monthly = generate_enrollment_figure(df, 'study_month', 'Actual: Monthly', 'Expected: Monthly', "Monthly Enrollment")
    fig_cumulative = generate_enrollment_figure(df, 'study_month', 'Actual: Cumulative', 'Expected: Cumulative', "Cumulative Enrollment")

    # Datatable
    df_mi = convert_to_multindex(df, delimiter = ': ')
    c1, dd = datatable_settings_multiindex(df_mi)

    # component ids
    fig_monthly_id = 'fig_monthly_' + str(id_index)
    fig_cumulative_id = 'fig_cumulative_' + str(id_index)
    datatable_id = 'table_' + str(id_index)

    site_div = html.Div([
            dbc.Row([
                dbc.Col(html.H3(site),width=12)
            ]),
            dbc.Row(
                [
                    dbc.Col([
                        dcc.Graph(figure=fig_monthly, id=fig_monthly_id),
                        dcc.Graph(figure=fig_cumulative, id=fig_cumulative_id)
                       ], lg=6),
                    dbc.Col(
                            [
                                dt.DataTable(
                                id=datatable_id,
                                columns=c1,
                                data=dd,
                                merge_duplicate_headers=True,
                            )]
                        , lg=6),
                ]
            ),
            dbc.Row(
                [

                ], style= {'display': table_display}
            ),

        ], style={"margin":"20px","padding":"30ox", "border-bottom":"1px solid black"})
    return site_div

# ----------------------------------------------------------------------------
# TABS
# ----------------------------------------------------------------------------


def build_tables_dict(table1a, table1b, table2a, table2b, table3a, table3b, table4, table5, table6, table7a, table7b, table8a, table8b, sex, race, ethnicity, age):
    tables_names = ("table1a", "table1b", "table2a", "table2b", "table3a", "table3b","table4", "table5", "table6", "table7a", "table7b", "table8a", "table8b", "sex", "race", "ethnicity", "age")
    excel_sheet_names = ("Screened_site","Screened_MCC", "Decline_Reasons", "Decline_Comments", "Consent_site","Consent_mcc", "Study_Status", "Rescinded_Consent", "Early_Termination", "Protocol_Deviations", "Protocol_Deviations_Description",
    "Adverse_Events", "Adverse_Events_Description", "Gender", "Race", "Ethnicity", "Age")

    tables = (table1a, table1b, table2a, table2b, table3a, table3b, table4, table5, table6, table7a, table7b, table8a, table8b, sex, race, ethnicity, age)

    tables_dict = {}

    for i in range(0,len(tables_names)):
        table_name = tables_names[i]
        excel_sheet_name = excel_sheet_names[i]
        data_source = tables[i]
        columns_list, datatable_data = datatable_settings_multiindex(data_source)

        # if(data_source.columns.nlevels == 2):
        #     columns_list = []
        #     for i in data_source.columns:
        #         col_id = i[0] + ':' + i[1]
        #         columns_list.append({"name": [i[0],i[1]], "id": col_id})
        #     data_source.columns = data_source.columns.droplevel()
        # else:
        #     columns_list = [{"name": i, "id": i} for i in data_source.columns]



        tables_dict[table_name] = {'excel_sheet_name': excel_sheet_name,
                                    'columns_list': columns_list,
                                    'data': datatable_data
                                    # 'data': data_source.to_dict('records')
                                    }


    return tables_dict

def build_content(tables_dict, page_meta_dict):

    report_date_msg, report_range_msg = page_meta_dict['report_date_msg'], page_meta_dict['report_range_msg']

    section1 = html.Div([
        dbc.Card(
            dbc.CardBody([
                html.H5('Table 1. Number of Subjects Screened by Site', className="card-title"),
                html.Div([report_date_msg, '. Tables are cumulative over study']),
                html.H6('Table 1.a. Subjects Screened by Site and Surgery type'),
                html.Div(build_datatable_from_table_dict(tables_dict, 'table1a', 'table_1a')),
                html.H6('Table 1.b. Subjects Screened by MCC and Surgery type'),
                html.Div(build_datatable_from_table_dict(tables_dict, 'table1b', 'table_1b')),
                dcc.Markdown('''
                    **Screening Site:** MCC and Screening Site
                    **MCC:** MCC
                    **Surgery:** Surgery type - Knee (TKA) or Thoracic
                    **All Screened:** Total number of subjects screened
                    **Yes:** Total number of subjects who expressed interest in participating in study
                    **Maybe:** Total number of subjects who said they might participate in study
                    **No:** Total number of subjects who declined to participate in study
                    **Consented:** Total number of subjects who consented to participate in study
                    **% Enrolled:** % of screened subjects who consented to participate in the study
                    '''
                    ,style={"white-space": "pre"}),
            ]),
        ),
        dbc.Card(
            dbc.CardBody([
                html.H5('Table 2. Reasons for declining'),
                html.H6('Table 2.a. Reasons for declining by Site'),
                html.Div([report_date_msg, '. Table is cumulative over study']),
                html.Div(build_datatable_from_table_dict(tables_dict, 'table2a', 'table_2a')),
                dcc.Markdown('''
                    **Screening Site:** MCC and Screening Site
                    **Total Declined:** Total number of subjects screened
                    **Additional Columns:** Total number of subjects who sited that reason in declining.
                    *Note*: Subjects may report multiple reasons (or no reason) for declining.
                    '''
                    ,style={"white-space": "pre"}),
            ]),
        ),
        dbc.Card(
            dbc.CardBody([
                html.H6('Table 2.b. Reasons for declining ‘Additional Comments’'),
                html.Div([report_range_msg]),
                html.Div(build_datatable_from_table_dict(tables_dict, 'table2b', 'table_2b')),
            ]),
        ),
        dbc.Card(
            dbc.CardBody([
                html.H5('Table 3. Number of Subjects Consented'),
                html.Div([report_date_msg, '. Table is cumulative over study']),
                html.H6('Table 3.a. Consented Subjects by Site and Surgery type'),
                html.Div(build_datatable_from_table_dict(tables_dict, 'table3a', 'table_3a')),
                html.H6('Table 3.b. Consented Screened by MCC and Surgery type'),
                html.Div(build_datatable_from_table_dict(tables_dict, 'table3b', 'table_3b')),
                dcc.Markdown('''
                    **Center Name:** MCC and Treatment Site
                    **MCC:** MCC
                    **Surgery:** Surgery type - Knee (TKA) or Thoracic
                    **Consented:** Total number of subjects consented
                    **Days Since Last Consent:** Number of days since most recent consent (for sites who have consented at least one subject)
                    **Consents in last 30 days** : Rate of consent per 30 days
                    **Total Eligible:** Total number of subjects who declined to participate in study
                    **Total Ineligible:** Total number of subjects who were ineligible to participate in study
                    **Total Rescinded:** Total number of subjects who withdrew from the study
                    '''
                    ,style={"white-space": "pre"}),
            ]),
        ),
    ])

    section2 = html.Div([
        dbc.Card([
            html.H5('Table 4. Ongoing Study Status'),
            html.Div([report_date_msg]),
            html.Div(build_datatable_from_table_dict(tables_dict, 'table4', 'table_4')),
        ],body=True),
        dbc.Card([
            html.H5('Table 5. Rescinded Consent'),
            html.Div([report_date_msg]),
            # daq.ToggleSwitch(
            #     id='toggle-rescinded',
            #     label=['Previous Week','Cumulative'],
            #     value=False
            # ),
            html.Div(build_datatable_from_table_dict(tables_dict, 'table5', 'table_5')),
        ],body=True),
        dbc.Card([
            html.H5('Table 6. Early Study Termination Listing'),
            html.Div([report_date_msg]),
            html.Div(build_datatable_from_table_dict(tables_dict, 'table6', 'table_6')),
        ],body=True),
    ])

    section3 = html.Div([
        dbc.Card([
            dbc.CardBody([
                html.H5('Table 7.a. Protocol Deviations'),
                html.Div([report_date_msg, '. Table is cumulative over study']),
                html.Div(build_datatable_from_table_dict(tables_dict, 'table7a', 'table_7a')),
                dcc.Markdown('''
                    **Center Name:** MCC and Treatment Site
                    **Baseline Patients:** Total number of subjects reaching baseline
                    **# with Deviation:** Total number of subjects with at least one deviation
                    **Total Deviations:** Total of all deviations at this center (a single patient can have more than one)
                    **% with 1+ Deviations:** Percent of Patients with 1 or more deviations
                    **Additional Columns:** Count by center of the total number of each particular type of deviation
                    '''
                    ,style={"white-space": "pre"}),
            ]),
        ]),
        dbc.Card([
            dbc.CardBody([
                html.H5('Table 7.b. Description of Protocol Deviations'),
                html.Div([report_range_msg]),
                html.Div(build_datatable_from_table_dict(tables_dict, 'table7b', 'table_7b')),
            ]),
        ]),
        dbc.Card([
            html.H5('Table 8.a. Adverse Events'),
            html.Div([report_date_msg, '. Table is cumulative over study']),
            html.Div(build_datatable_from_table_dict(tables_dict, 'table8a', 'table_8a')),
        ],body=True),
        dbc.Card([
            html.H5('Table 8.b. Description of Adverse Events'),
            html.Div([report_range_msg]),
            html.Div(build_datatable_from_table_dict(tables_dict, 'table8b', 'table_8b')),
        ],body=True),
    ])

    section4 = html.Div([
        dbc.Card([
            html.H5('Table 9. Demographic Characteristics'),
            html.Div([report_date_msg, '. Table is cumulative over study']),
            html.H5('Gender'),
            html.Div(build_datatable_from_table_dict(tables_dict, 'sex', 'table_9a')),
            html.H5('Race'),
            html.Div(build_datatable_from_table_dict(tables_dict, 'race', 'table_9b')),
            html.H5('Ethnicity'),
            html.Div(build_datatable_from_table_dict(tables_dict, 'ethnicity', 'table_9c')),
            html.H5('Age'),
            html.Div(build_datatable_from_table_dict(tables_dict, 'age', 'table_9d')),
        ],body=True),
    ])

    return section1, section2, section3, section4

# def get_sections_dict_for_store(section1, section2, section3, section4):
#     sections_dict = {}
#     sections_dict['section1'] = section1
#     sections_dict['section2'] = section2
#     sections_dict['section3'] = section3
#     sections_dict['section4'] = section4
#     return sections_dict

# ----------------------------------------------------------------------------
# DASH APP LAYOUT FUNCTION
# ----------------------------------------------------------------------------
def subjects_report(page_meta_dict):
    subjects_report = html.Div([
            dbc.Row([
                dbc.Col(html.H2(['A2CPS Weekly Report - Preview']),width = 10),

            ]),
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Button("Download as Excel",n_clicks=0, id="btn_xlxs",style =EXCEL_EXPORT_STYLE ),
                        daq.ToggleSwitch(
                            id='toggle-view',
                            label=['Tabs','Single Page'],
                            value=False,
                            style =EXCEL_EXPORT_STYLE
                        ),
                    ],id='print-hide', className='print-hide'),
                    html.H5(page_meta_dict['report_date_msg']),
                    html.Div(id='download-msg'),
                ],width=12),
            ]),
            dbc.Row([
                dbc.Col([
                    html.Div(id='page_layout'),
                ], width=12)
            ]),
        ])
    return subjects_report

def build_page_layout(toggle_view_value, sections_dict):

    section1 = sections_dict['section1']
    section2 = sections_dict['section2']
    section3 = sections_dict['section3']
    section4 = sections_dict['section4']

    if toggle_view_value:
        page_layout = [html.H3('Screening'), section1, html.H3('Study Status'), section2, html.H3('Deviations & Adverse Events'), section3, html.H3('Demographics'), section4]
    else:
        page_layout = html.Div([
                    dcc.Tabs(id='tabs_tables', children=[
                        dcc.Tab(label='Screening', children=[
                            html.Div([section1], id='section_1'),
                        ]),
                        dcc.Tab(label='Study Status', children=[
                            html.Div([section2], id='section_2'),
                        ]),
                        dcc.Tab(label='Deviations & Adverse Events', children=[
                            html.Div([section3], id='section_3'),
                        ]),
                        dcc.Tab(label='Demographics', children=[
                            html.Div([section4], id='section_4'),
                        ]),
                    ]),
                    ])
    return page_layout

def serve_layout():
    page_meta_dict, tables_dict, sections_dict, enrollment_dict = {'report_date_msg':''}, {}, {}, {}
    report_date = datetime.now()

    try:
        # TO DO: CONVERT THIS TO ALWAYS PULL DATA FROM DATASTORE
    # get data for page
    # print('time parameters')
        today, start_report, end_report, report_date_msg, report_range_msg  = get_time_parameters(report_date)

        if DATA_SOURCE == 'api':
            page_meta_dict['report_date_msg'] = report_date_msg
        elif DATA_SOURCE == 'local':
            page_meta_dict['report_date_msg'] = 'Report generated from archived data dated ' + local_data_date
        else:
            page_meta_dict['report_date_msg'] = 'Data date unclear'
        page_meta_dict['report_range_msg'] = report_range_msg
        # print('get data inputs')

        # TO DO: CONVERT TO PULL THESES FROM GITHUB
        # display_terms, display_terms_dict, display_terms_dict_multi, clean_weekly, consented, screening_data, clean_adverse, centers_df, r_status = get_data_for_page(ASSETS_PATH, display_terms_file, file_url_root, report, report_suffix, mcc_list)
        display_terms, display_terms_dict, display_terms_dict_multi = load_display_terms(ASSETS_PATH, 'A2CPS_display_terms.csv')
        screening_sites = pd.read_csv(os.path.join(ASSETS_PATH, 'screening_sites.csv'))

        # Get data from API
        api_address = DATASTORE_URL + 'subjects'
        app.logger.info('Requesting data from api {0}'.format(api_address))
        api_json = get_api_data(api_address)

        # subjects_json = get_subjects_json(report, report_suffix, file_url_root, source=DATA_SOURCE)
        if 'error' in api_json:
            app.logger.info('Error response from datastore: {0}'.format(api_json))
            if 'error_code' in api_json:
                error_code = api_json['error_code']
                if error_code in ('MISSING_SESSION_ID', 'INVALID_TAPIS_TOKEN'):
                    raise PortalAuthException

        # If data is not available, try with bypassing cache and see if that works.
        if not api_json or 'data' not in api_json:
            app.logger.info('Requesting data from api {0} to bypass cache.'.format(api_address))
            api_json = get_api_data(api_address, True)

        if api_json:
            subjects = pd.DataFrame.from_dict(api_json['data']['subjects_cleaned'])
            adverse_events = pd.DataFrame.from_dict(api_json['data']['adverse_events'])
            consented = pd.DataFrame.from_dict(api_json['data']['consented'])

            # Convert datetime columns
            datetime_cols_list = ['date_of_contact','date_and_time','obtain_date','ewdateterm','sp_surg_date','sp_v1_preop_date','sp_v2_6wk_date','sp_v3_3mo_date']
            subjects[datetime_cols_list] = subjects[datetime_cols_list].apply(pd.to_datetime, errors='coerce')
            consented[datetime_cols_list] = consented[datetime_cols_list].apply(pd.to_datetime, errors='coerce')

            # print('subjects_json')
            screening_centers_df, centers_df = get_centers(subjects, consented, display_terms)

            # print('GET TABLE DATA')
            table1a, table1b, table2a, table2b, table3a, table3b, table4, table5, table6, table7a, table7b, table8a, table8b, sex, race, ethnicity, age = get_tables(today, start_report, end_report, report_date_msg, report_range_msg, display_terms, display_terms_dict, display_terms_dict_multi, subjects, consented, adverse_events, centers_df)

            # print('building tables')
            tables_dict = build_tables_dict(table1a, table1b, table2a, table2b, table3a, table3b, table4, table5, table6, table7a, table7b, table8a, table8b, sex, race, ethnicity, age)

            # print('building content')
            section1, section2, section3, section4 = build_content(tables_dict, page_meta_dict)

        else:
            # print('NO subjects_json')
            no_data_msg = "The data for this report is not available at this time.  Please try again later."
            section1, section2, section3, section4 = html.Div(no_data_msg), html.Div(no_data_msg), html.Div(no_data_msg), html.Div(no_data_msg)

            # print('get sections')
        sections_dict = {}
        sections_dict['section1'] = section1
        sections_dict['section2'] = section2
        sections_dict['section3'] = section3
        sections_dict['section4'] = section4

        page_layout = html.Div(id='page_layout')
    except PortalAuthException:
        app.logger.warn('Auth error from datastore, asking user to authenticate')
        return html.Div([html.H4('Please login and authenticate on the portal to access the report.')],style=TACC_IFRAME_SIZE)
    except Exception as e:
        traceback.print_exc()
        return html.Div(['There has been a problem accessing the data for this Report.'],style=TACC_IFRAME_SIZE)

    s_layout = html.Div([
        dcc.Store(id='store_meta', data = page_meta_dict),
        dcc.Store(id='store_tables', data = tables_dict),
        dcc.Store(id='store_sections', data = sections_dict),
        dcc.Store(id='store_enrollment', data = enrollment_dict),
        Download(id="download-dataframe-xlxs"),
        Download(id="download-dataframe-html"),

        html.Div([
            subjects_report(page_meta_dict)
        ], id='report_content', style =CONTENT_STYLE)

    ],style=TACC_IFRAME_SIZE)
    return s_layout

app.layout = serve_layout

# ----------------------------------------------------------------------------
# DATA CALLBACKS
# ----------------------------------------------------------------------------

# Use toggle to display either tabs or single page LAYOUT
@app.callback(Output("page_layout","children"), Input('toggle-view',"value"),State('store_sections', 'data'))
def set_page_layout(value, sections):
    return build_page_layout(value, sections)

# Create excel spreadsheel
@app.callback(
        Output("download-dataframe-xlxs", "data"),
        Input("btn_xlxs", "n_clicks"),
        State("store_tables","data"),
        )
def click_excel(n_clicks,store):
    if n_clicks == 0:
        raise PreventUpdate
    if store:
        try:
            # msg =  html.Div(json.dumps(store))
            today = datetime.now().strftime('%Y_%m_%d')
            download_filename = datetime.now().strftime('%Y_%m_%d') + '_a2cps_weekly_report_data.xlsx'
            table_keys = store.keys()

            writer = pd.ExcelWriter(download_filename, engine='xlsxwriter')

            tables_names = ["table1a","table1b", "table2a", "table2b", "table3a", "table3b", "table4", "table5", "table6", "table7a", "table7b", "table8a", "table8b", "sex", "race", "ethnicity", "age"]
            for table in tables_names:
                excel_sheet_name = store[table]['excel_sheet_name']
                df = pd.DataFrame(store[table]['data'])

                # convert multiindex columns and remove the '_'
                new_cols = []
                for i in list(df.columns):
                    if i[0] == '_':
                        new_cols.append(i[1:])
                    else:
                        new_cols.append(i.replace('_',': '))
                df.columns = new_cols

                if len(df) == 0 :
                    df = pd.DataFrame(columns =['No data for this table'])
                df.to_excel(writer, sheet_name=excel_sheet_name, index = False)

            writer.save()
            excel_file =  send_file(writer, download_filename)
            return excel_file

        except Exception as e:
            traceback.print_exc()
            return None


# ----------------------------------------------------------------------------
# RUN APPLICATION
# ----------------------------------------------------------------------------

if __name__ == '__main__':
    app.run_server(debug=True)
else:
    server = app.server
