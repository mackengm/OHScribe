from flask import Flask, render_template, flash, redirect, url_for, request
from app import app
from app.forms import MainForm, LoginForm
from app.actions import do_cleanup, do_transform, do_hms_conversion, do_speaker_tags, do_analyze, do_all, allowed_file
from werkzeug.utils import secure_filename
import sys
import os


# Route for handling the login page logic
@app.route('/', methods=['POST', 'GET'])
@app.route('/login', methods=['POST', 'GET'])
def login():
  form = LoginForm(request.form)
  if request.method == 'POST':
    if (form.username.data == "admin" and form.password.data == os.getenv('OHSCRIBE_ADMIN_PASSWORD')):
      flash("Login permitted for user '{}'".format(form.username.data))
      return redirect(url_for('upload_file'))
    else:
      flash("Authentication failed.  Please try again or contact digital@grinnell.edu for proper credentials.", 'error')
      return redirect(url_for('login'))
  return render_template('login.html', title='Sign In', form=form)


# Route for handing upload selection
@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
  if request.method == 'POST':
    # Check if the post request has the file part
    if 'file' not in request.files:
      flash('No file part', 'error')
      return redirect(request.url)
        
    file = request.files['file']
        
    # If user does not select file, browser also submit an empty part without filename
    if file.filename == '':
      flash('No selected file', 'error')
      return redirect(request.url)
        
    # Good to go...
    if file and allowed_file(file.filename):
      filename = secure_filename(file.filename)
      newpath = os.path.join(os.environ.get('OHSCRIBE_UPLOAD_FOLDER'), filename)
      try:
        file.save(newpath)
        flash("Your file has been successfully uploaded to {}".format(newpath), 'info')
        os.environ.setdefault('OHSCRIBE_UPLOADED_FILE', newpath)
        return redirect(url_for('main'))
      except:
        msg = "Unexpected error: {}".format(sys.exc_info()[0])
        flash(msg, 'error')

  return render_template('upload.html', title='Upload XML File')


# # Route for displaying the uploaded file
# @app.route('/uploads/<filename>')
# def uploaded_file(filename):
#     return send_from_directory(os.environ.get('OHSCRIBE_UPLOAD_FOLDER'), filename)


# Route for handling the main/control page
@app.route('/main', methods=['POST', 'GET'])
def main( ):
  form = MainForm(request.form)
  if request.method == 'POST':
    return redirect(url_for('results'))
  return render_template('main.html', title='Controls', form=form)


# Route for handling the results page
@app.route('/results', methods=['POST', 'GET'])
def results( ):
  result = request.form
  method = request.method

  try:
    result['exit']
  except:
    pass
  else:
    exit(0)

  filename = os.environ.get('OHSCRIBE_UPLOADED_FILE')
  
  try:
    result['all']
  except:
    pass
  else:
    file, msg, details, guidance = do_all(filename)
    os.environ.setdefault('OHSCRIBE_UPLOADED_FILE', file)
    return render_template("results.html", result=result, message=msg, details=details, guidance=guidance)

  try:
    if result['actions'] and result['go']:
      action = str(result['actions'])
      if action == "cleanup":
        file, msg, details, guidance = do_cleanup(filename)
        os.environ.setdefault('OHSCRIBE_UPLOADED_FILE', file)
        return render_template("results.html", result=result, message=msg, details=details, guidance=guidance)
      elif action == "transform":
        file, msg, details, guidance = do_transform(filename)
        os.environ.setdefault('OHSCRIBE_UPLOADED_FILE', file)
        return render_template("results.html", result=result, message=msg, details=details, guidance=guidance)
      elif action == "convert":
        file, msg, details, guidance = do_hms_conversion(filename)
        os.environ.setdefault('OHSCRIBE_UPLOADED_FILE', file)
        return render_template("results.html", result=result, message=msg, details=details, guidance=guidance)
      elif action == "speakers":
        file, msg, details, guidance = do_speaker_tags(filename)
        os.environ.setdefault('OHSCRIBE_UPLOADED_FILE', file)
        return render_template("results.html", result=result, message=msg, details=details, guidance=guidance)
      elif action == "analyze":
        file, msg, details, guidance = do_analyze(filename)
        os.environ.setdefault('OHSCRIBE_UPLOADED_FILE', file)
        return render_template("results.html", result=result, message=msg, details=details, guidance=guidance)

  except:
    msg = "Unexpected error: {}".format(sys.exc_info()[0])
    flash(msg, 'error')
    return redirect(url_for('main'))
