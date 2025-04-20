from flask import Flask, request, redirect, url_for, render_template, send_file, session
import pandas as pd
import re
import os
from werkzeug.utils import secure_filename
from nepali_datetime import date as nepali_date
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for session handling
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['ALLOWED_EXTENSIONS'] = {'xlsx'}

# Dummy login credentials
USERNAME = 'saroj'
PASSWORD = 'saroj@123'

# Check if the file is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Function to convert English date to Nepali date
def convert_to_nepali_date(english_date):
    try:
        eng_date = datetime.strptime(english_date, "%Y-%m-%d")
        nepali_miti = nepali_date.from_datetime_date(eng_date.date())
        return nepali_miti.strftime('%Y-%m-%d')
    except ValueError:
        return None

# Function to clean data by appending "DV" only to second and subsequent duplicates
def clean_data(df, column_to_check):
    df['count_Row'] = range(1, len(df) + 1)
    
    # Add "DV" to only the second and subsequent duplicates in the specified column
    duplicate_indices = df[column_to_check].duplicated(keep='first')
    df.loc[duplicate_indices, column_to_check] = df.loc[duplicate_indices, column_to_check] + ' DV'
    
    # Add a new column 'Duplicate_Value' to mark duplicates (optional for reference)
    df['Duplicate_Value'] = duplicate_indices.apply(lambda x: 'DV' if x else '')
    
    # Remove special characters from all string columns
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].apply(lambda x: re.sub(r'[^\w\s]', '', str(x)))
    
    return df

# Login route
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == USERNAME and password == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            return 'Invalid username or password.'
    return render_template('login.html')

# Dashboard route
@app.route('/dashboard')
def dashboard():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

# Route for file upload and selection of action (duplicate removal or date conversion)
@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            df = pd.read_excel(file_path)
            df = pd.DataFrame(df)

            columns = df.columns.tolist()  # Get all columns

            return render_template('select_action.html', columns=columns, filename=filename)

    return render_template('upload.html')

# Process the file based on user-selected action
@app.route('/process', methods=['POST'])
def process_file():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    filename = request.form.get('filename')
    action = request.form.get('action')  # Action chosen by the user
    column_to_check = request.form.get('column_to_check')

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    df = pd.read_excel(file_path)

    if action == 'remove_duplicates':
        cleaned_df = clean_data(df, column_to_check)
        cleaned_filename = 'cleaned_' + filename
    elif action == 'convert_dates':
        df[column_to_check] = pd.to_datetime(df[column_to_check], errors='coerce')
        df['Miti'] = df[column_to_check].apply(
            lambda x: convert_to_nepali_date(str(x).split(' ')[0]) if pd.notnull(x) else None
        )
        cleaned_df = df
        cleaned_filename = 'converted_miti_' + filename

    cleaned_file_path = os.path.join(app.config['UPLOAD_FOLDER'], cleaned_filename)
    cleaned_df.to_excel(cleaned_file_path, index=False)

    return send_file(cleaned_file_path, as_attachment=True)

# Logout route
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
