import os
from flask import Flask, render_template, redirect, url_for, session, flash
from flask_bootstrap import Bootstrap, bootstrap_find_resource
from flask_moment import Moment
from flask_wtf import Form
from wtforms import DateField, StringField, SubmitField
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms.validators import DataRequired #, Regexp
from flask_weasyprint import HTML, render_pdf, CSS

from bpw_graphs import dashboard

app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])
#app.config['SECRET_KEY'] = 'BPW DashBoard BizHaus'

bootstrap = Bootstrap(app)
moment = Moment(app)

class UploadForm(Form):
    vendor = StringField('Vendor Name', validators = [DataRequired()])

    work_order = FileField('Work_Order_Export file', validators=[
        FileRequired(),
        FileAllowed(['csv'], 'CSV Files Only!')
    ])

    payable = FileField('DF_Standard_Accounts_Payable_Export file', validators=[
        FileRequired(),
        FileAllowed(['csv'], 'CSV Files Only!')
    ])
    submit = SubmitField('PRESS TO CREATE DASHBOARD')


@app.route('/', methods=['GET', 'POST'])
def index():
    form = UploadForm()
    if form.validate_on_submit():
        work_order = form.work_order.data.stream
        payable = form.payable.data.stream
        try:
            dash_list = dashboard(work_order, payable)
        except:
            flash('One or more of the CSV files is the wrong file')
            return redirect(url_for('index'))
        vendor_name = form.vendor.data
        form.vendor.data = ''
        session['vendor_name'] = vendor_name
        session['dash_list'] = dash_list
        return redirect(url_for('dash'))
    return render_template("index.html", form = form)


@app.route('/dashboard')
def dash():
    dash_list = session.get('dash_list')
    vendor_name = session.get('vendor_name')
    return render_template('dashboard.html', dash_list = dash_list,
                           vendor_name = vendor_name)

@app.route('/dashboard.pdf')
def dash_pdf():
    dash_list = session.get('dash_list')
    vendor_name = session.get('vendor_name')
    html = render_template('dashboard_pdf.html', dash_list = dash_list,
                           vendor_name = vendor_name)
    return render_pdf(HTML(string=html),
                      stylesheets=[
                          CSS(string='@page { size: A3 portrait;'
                                'background-color: #f8f8ff ;'
                                ' margin: 2cm };'
                                '* { float: none !important; };'
                                '@media print { nav { display: none; }'
                                '.barchart{width:200px; }'
                          )
                      ])

if __name__ == '__main__':
    app.run()