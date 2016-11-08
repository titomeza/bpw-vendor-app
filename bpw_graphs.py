import re
import os
import pandas as pd
from numpy import array, isfinite
# import datetime

import plotly.plotly as py
import plotly.tools as tools
import plotly.graph_objs as go

USER_NAME = os.environ['PLOTLY_USER_NAME']
API_KEY = os.environ['PLOTLY_API_KEY']
# USER_NAME = ''
# API_KEY = ''

py.sign_in(username=USER_NAME, api_key=API_KEY)


# This is a function that will process the incoming files and provide the graphs and information
# that is required for the dashboard


def dashboard(work_order, payable):
    # type: (file, file) -> dictionary
    # Dashboard reads 2 CSV files
    # Returns in a dictionary:
    # 0)  The URL of the first plot: first_plot_url
    # 1)  Number of inspections
    # 2)  Total made from inspections
    # 3)  Average invoice per inspection
    # 4)  Number of managed works
    # 5)  Total made from managed works
    # 6)  Average invoice per managed work
    # 7)  Number of jobs done
    # 8)  Total made from jobs
    # 9)  ?????
    # 10) ????
    # 11) ???

    # First we read in the 2 files that we are going to need to make the report

    '''
    :param work_order: csv file containing work order report
    :param payable: csv file containing receivables info
    '''

    work_order = pd.read_csv(work_order)
    payable = pd.read_csv(payable,
                          parse_dates=['SHIP_DATE'],
                          infer_datetime_format=True)

    # We process the files to remove some commas and "$" from numbers and nulls and others

    payable['CHARGE_SUBTOTAL'] = payable['CHARGE_SUBTOTAL'].str.replace(r'[$,]', '').astype('float')
    payable['CHARGE_TOTAL'] = payable['CHARGE_TOTAL'].str.replace(r'[$,]', '').astype('float')
    payable = payable.rename(columns={'WO NUM': 'WORKORDER_ID'})
    payable['YEAR'] = payable['SHIP_DATE'].dt.year
    payable['NUMBER'] = 1

    payable = payable.drop(['PO_NUM',
                            'Accounts_Payable_ID',
                            'FROM_ROOT_ID',
                            'SHIP_DATE',
                            'INV_DATE',
                            'DUE_DATE',
                            'CHARGE_SUBTOTAL',
                            'DATECREATED',
                            'WHOCREATED',
                            'CUSTOMER_NUM',
                            'TERMS',
                            'DIVISION_NAME',
                            'TO_TEXT',
                            'FROM_ROOT',
                            'FROM_OFFICE_ID',
                            'SHIP_TO_ROOT',
                            'SHIP_TO_ROOT_ID',
                            'SHIP_TO_TEXT',
                            'REMIT_PAYMENT_TO_TEXT',
                            'FROM_TEXT',
                            'TERM_DAYS',
                            'TERMS_DISCOUNT',
                            'NOTES',
                            'USE_TAX',
                            'USE_TAX_AMOUNT',
                            'WHOMODIFIED',
                            'PO_ID',
                            'VENDOR_INV_NUM',
                            'DISCOUNT_DATE',
                            'DATEMODIFIED'], axis=1)

    payable_wo = pd.merge(payable, work_order, on='WORKORDER_ID')

    payable_wo = payable_wo.drop(['ALTNUMBER',
                                  'WORKORDER_ID',
                                  'CLIENTNUMBER',
                                  'WHOCREATED',
                                  'STATUS',
                                  'DATECREATED',
                                  'REGION',
                                  'STATE',
                                  'ZIP',
                                  'STATUSDATE',
                                  'STATUSWHO',
                                  'BUILDING_ID',
                                  'BUILDING_NAME',
                                  'AREA_NAME',
                                  'STREET_ADDRESS',
                                  'CITY',
                                  'WORKDESCRIPTION',
                                  'ROOFCONDITION',
                                  'NOTES',
                                  'BUDGET_AMOUNT',
                                  'INVOICESTATUS',
                                  'COMPANY_RELATIONSHIP 1',
                                  'COMPANY_RELATIONSHIP 2',
                                  'COMPANY_RELATIONSHIP 3',
                                  'CONTACT_RELATIONSHIP 1',
                                  'CONTACT_RELATIONSHIP 2',
                                  'CONTACT_RELATIONSHIP 3',
                                  'FINANCIAL_RESPONSIBILITY'], axis=1)

    payable_wo = payable_wo.fillna({'TYPE': 'NOT SPECIFIED', 'SUBTYPE': 'NOT SPECIFIED'})
    payable_wo.loc[(payable_wo.TYPE == 'NOT SPECIFIED')
                   & ((payable_wo.SUBTYPE == 'Clean & Inspect')
                      | (payable_wo.SUBTYPE == 'Inspection')), 'TYPE'] = 'Inspection'
    payable_wo.loc[payable_wo.TYPE == 'Contracted Work', 'SUBTYPE'] = 'Portfolio'
    payable_wo.loc[payable_wo.TYPE == 'Contracted Work', 'TYPE'] = 'Inspection'
    payable_wo.loc[(payable_wo.TYPE == 'NOT SPECIFIED')
                   & ((payable_wo.SUBTYPE <> 'NOT SPECIFIED')
                      & (payable_wo.SUBTYPE <> 'Other trade')
                      & (payable_wo.SUBTYPE <> 'Referral')), 'TYPE'] = 'Managed Work'
    payable_wo_ins = payable_wo[payable_wo['TYPE'].isin(['Inspection'])]
    payable_wo_mw = payable_wo[payable_wo['TYPE'].isin(['Managed Work'])]
    payable_wo_mw = payable_wo_mw.sort_values('YEAR', ascending=True)

    # now = datetime.datetime.now()
    # this_year = now.year

    dashboard_values = [bar_chart_url(payable_wo)]

    dashboard_values = dashboard_values + upper_right_stats(payable_wo, payable_wo_ins, payable_wo_mw)

    dashboard_values = dashboard_values + [second_graph_url(payable_wo_ins, payable_wo_mw)]

    dashboard_values = dashboard_values + [pie_chart_url(dashboard_values[2], dashboard_values[6])]

    # dashboard_values.update(upper_right_stats(work_order, payable))

    return dashboard_values


def bar_chart_url(payable_wo):
    '''
    :param payable_wo: a panda dataframe  with work order and payable information
    :return: a url for a plotly bar chart
    '''

    payable_wo_year = payable_wo.groupby('YEAR', as_index=False).sum()
    # payable_wo_year['YEAR'] = payable_wo_year['YEAR'].astype(str)
    payable_wo_year = payable_wo_year.round(decimals=2)
    year_values = payable_wo_year['YEAR'].values.tolist()
    charge_values = payable_wo_year['CHARGE_TOTAL'].values.tolist()
    number_values = payable_wo_year['NUMBER'].values.tolist()

    scroll_max = payable_wo_year['CHARGE_TOTAL'].max() / 20
    if scroll_max < 5:
        scroll_max = 5

    nticks = len(payable_wo_year.index)

    data = [
        go.Bar(
            x=payable_wo_year['YEAR'],
            y=payable_wo_year['CHARGE_TOTAL'],
            name="bar chart example"
        )
    ]

    layout = go.Layout(
        xaxis=dict(
            title="Year",
            nticks=nticks
        ),
        yaxis=dict(
            title="Amount"
        ),

    )

    annotations = []
    for x0, y0, n0 in zip(year_values, charge_values, number_values):
        annotations.append(dict(xref='x0', yref='y0',
                                y=y0 + scroll_max, x=x0,
                                text="${:,.2f}<br>{}".format(y0, n0),
                                font=dict(family='Arial', size=12,
                                          color='rgb(50, 171, 96)'),
                                showarrow=False))

    fig = go.Figure(data=data, layout=layout)
    fig['layout'].update(paper_bgcolor='rgb(248, 248, 255)',
                         plot_bgcolor='rgb(248, 248, 255)')
    fig['layout'].update(height=500, width=550,
                         annotations=annotations,
                         title='<b>Total made per year</b><br><i>Inspections and Managed Work</i>')

    return py.plot(fig, filename='BPW Bar Chart', auto_open=False, )


def upper_right_stats(payable_wo, payable_wo_ins, payable_wo_mw):
    '''
    :rtype: dict
    :param worders: a pandas frame of work orders
    :param receivables: a pandas frame of receivables
    :param start_date: start date of the report
    :return: a dictionary with
    # Returns in a dictionary:
    # 1)  Number of inspections
    # 2)  Total made from inspections
    # 3)  Average invoice per inspection
    # 4)  Number of managed works
    # 5)  Total made from managed works
    # 6)  Average invoice per managed work
    # 7)  Number of jobs done
    # 8)  Total made from jobs
    '''

    number_jobs = len(payable_wo.index)
    total_made = payable_wo['CHARGE_TOTAL'].sum()
    total_made_text = '${:,.2f}'.format(total_made)

    number_inspections = len(payable_wo_ins.index)
    total_made_inspections = payable_wo_ins['CHARGE_TOTAL'].sum()
    total_made_inspections_text = '${:,.2f}'.format(total_made_inspections)
    average_x_inspections = 0.0
    if number_inspections <> 0:
        average_x_inspections = payable_wo_ins['CHARGE_TOTAL'].mean()

    average_x_inspections_text = '${:,.2f}'.format(average_x_inspections)

    number_mw = len(payable_wo_mw.index)
    total_made_mw = payable_wo_mw['CHARGE_TOTAL'].sum()
    total_made_mw_text = '${:,.2f}'.format(total_made_mw)
    average_x_mw = 0.0
    if number_mw <> 0:
        average_x_mw = payable_wo_mw['CHARGE_TOTAL'].mean()
    average_x_mw_text = '${:,.2f}'.format(average_x_mw)

    return [
        number_inspections,
        total_made_inspections,
        total_made_inspections_text,
        average_x_inspections_text,
        number_mw,
        total_made_mw,
        total_made_mw_text,
        average_x_mw_text,
        number_jobs,
        total_made_text
    ]


def second_graph_url(payable_wo_ins, payable_wo_mw):
    '''
    :param payable_wo_ins: pandas dataframe
    :param payable_wo_mw: pandas dataframe
    :return: second url for graph
    '''

    payable_wo_ins_year = payable_wo_ins.groupby('YEAR', as_index=False).sum()
    payable_wo_ins_year = payable_wo_ins_year.round(decimals=2)

    payable_wo_mw_year = payable_wo_mw.groupby('YEAR', as_index=False).sum()
    payable_wo_mw_year = payable_wo_mw_year.round(decimals=2)

    payable_wo_ins_year = payable_wo_ins_year.rename(columns={'CHARGE_TOTAL': 'CHARGE_TOTAL_INS',
                                                              'NUMBER': 'NUMBER_INS'})

    payable_wo_mw_year = payable_wo_mw_year.rename(columns={'CHARGE_TOTAL': 'CHARGE_TOTAL_MW',
                                                            'NUMBER': 'NUMBER_MW'})
    # temporal
    # payable_wo_mw_year = payable_wo_mw_year.drop(payable_wo_mw_year.index[[0, 1, 2, 3]])
    # temporal

    payable_wo_fig = pd.merge(payable_wo_ins_year, payable_wo_mw_year, on='YEAR', how='outer')

    payable_wo_fig = payable_wo_fig.fillna(0)

    payable_wo_fig['NUMBER_INS'] = payable_wo_fig['NUMBER_INS'].astype('int64')
    payable_wo_fig['NUMBER_MW'] = payable_wo_fig['NUMBER_MW'].astype('int64')
    # payable_wo_fig['YEAR'] = payable_wo_fig['YEAR'].astype(str)

    year_values = payable_wo_fig['YEAR'].values.tolist()
    charge_values_ins = payable_wo_fig['CHARGE_TOTAL_INS'].values.tolist()
    number_values_ins = payable_wo_fig['NUMBER_INS'].values.tolist()
    charge_values_mw = payable_wo_fig['CHARGE_TOTAL_MW'].values.tolist()
    number_values_mw = payable_wo_fig['NUMBER_MW'].values.tolist()

    scroll_max_ins = payable_wo_fig['CHARGE_TOTAL_INS'].max() / 20
    if scroll_max_ins < 5:
        scroll_max_ins = 5

    scroll_max_mw = payable_wo_fig['CHARGE_TOTAL_MW'].max() / 20
    if scroll_max_mw < 5:
        scroll_max_mw = 5

    scroll_max = max([scroll_max_ins, scroll_max_mw])

    nticks = len(payable_wo_fig.index)

    trace1 = go.Bar(
        x=payable_wo_fig['YEAR'],
        y=payable_wo_fig['CHARGE_TOTAL_INS'],
        name='Inspections'
    )

    trace2 = go.Bar(
        x=payable_wo_fig['YEAR'],
        y=payable_wo_fig['CHARGE_TOTAL_MW'],
        name='Managed Works'
    )

    trace1 = go.Bar(
        x=payable_wo_fig['YEAR'],
        y=payable_wo_fig['CHARGE_TOTAL_INS'],
        name='Inspections'
    )

    trace2 = go.Bar(
        x=payable_wo_fig['YEAR'],
        y=payable_wo_fig['CHARGE_TOTAL_MW'],
        name='Managed Works'
    )

    annotations = []
    for x1, y1, n1 in zip(year_values, charge_values_ins, number_values_ins):
        annotations.append(dict(xref='x1', yref='y1',
                                y=y1 + scroll_max, x=x1 - 0.21,
                                text="${:,.2f}<br>{}".format(y1, n1),
                                font=dict(family='Arial', size=10,
                                          color='rgb(50, 171, 96)'),
                                showarrow=False))

    for x2, y2, n2 in zip(year_values, charge_values_mw, number_values_mw):
        annotations.append(dict(xref='x2', yref='y2',
                                y=y2 + scroll_max, x=x2 + 0.21,
                                text="${:,.2f}<br>{}".format(y2, n2),
                                font=dict(family='Arial', size=10,
                                          color='rgb(50, 171, 96)'),
                                showarrow=False))

    data = [trace1, trace2]
    layout = go.Layout(
        barmode='group'
    )
    fig = go.Figure(data=data, layout=layout)

    fig['layout']['xaxis'].update(title='Year')
    fig['layout']['xaxis'].update(tickmode='linear')
    fig['layout']['xaxis'].update(tick0=0)
    fig['layout']['xaxis'].update(dtick=1)
    fig['layout']['xaxis'].update(showticklabels='true')
    fig['layout']['yaxis'].update(title='Amount')

    fig['layout'].update(showlegend=True,
                         height=500,
                         width=1000,
                         # autosize='true',
                         title='<b>Total made per year</b>',
                         paper_bgcolor='rgb(248, 248, 255)',
                         plot_bgcolor='rgb(248, 248, 255)',
                         annotations=annotations
                         )

    return py.plot(fig, auto_open=False, filename='Project Snapshot')


def pie_chart_url(total_made_inspections, total_made_mw):
    '''
    :param total_made_inspections: total made from inspections
    :param total_made_mw: total made from managed works
    :return: a url for a plotly pie chart
    '''

    values = [total_made_inspections, total_made_mw]
    labels = ['Inspections', 'Managed Works']

    fig = {
        'data': [{'labels': labels,
                  'values': values,
                  'textinfo': 'value+percent',
                  'textposition': 'inside+outside',
                  'pull': 0.1,
                  'rotation': -90,
                  'showlegend': True,
                  'sort': False,
                  'type': 'pie'}],
        'layout': {'title': '<b>Total made from BPW</b><br><i>Per Inspections and Managed Works</i>',
                   "autosize": False,
                   "height": 480,
                   "width": 600
                   }
    }

    fig['layout'].update(paper_bgcolor='rgb(248, 248, 255)',
                         plot_bgcolor='rgb(248, 248, 255)')

    return py.plot(fig, filename='BPW Pie Chart', auto_open=False)
