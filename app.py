import os
from flask import (Flask, redirect, render_template, request, session,
                   send_from_directory, url_for)
from msal import ConfidentialClientApplication
from azure.identity import DefaultAzureCredential

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Azure AD configuration
CLIENT_ID = 'your-client-id'
AUTHORITY = 'https://login.microsoftonline.com/your-tenant-id'
REDIRECT_PATH = '/getAToken'
SCOPE = ['User.Read']

# Use DefaultAzureCredential to get a token using managed identity
credential = DefaultAzureCredential()
token = credential.get_token("https://management.azure.com/.default")

# MSAL instance
msal_app = ConfidentialClientApplication(
    CLIENT_ID, authority=AUTHORITY,
    client_credential=token.token)

def is_logged_in():
    return 'user' in session

def requires_auth(f):
    def decorated(*args, **kwargs):
        if not is_logged_in():
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/')
@requires_auth
def index():
    print('Request for index page received')
    headers = request.headers
    headers_dict = {header: value for header, value in headers.items()}
    return render_template('index.html', headers=headers_dict)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/hello', methods=['POST'])
@requires_auth
def hello():
    name = request.form.get('name')

    if name:
        print('Request for hello page received with name=%s' % name)
        return render_template('hello.html', name=name)
    else:
        print('Request for hello page received with no name or blank name -- redirecting')
        return redirect(url_for('index'))

@app.route('/login')
def login():
    auth_url = msal_app.get_authorization_request_url(SCOPE, redirect_uri=url_for('authorized', _external=True))
    return redirect(auth_url)

@app.route(REDIRECT_PATH)
def authorized():
    code = request.args.get('code')
    if code:
        result = msal_app.acquire_token_by_authorization_code(code, scopes=SCOPE, redirect_uri=url_for('authorized', _external=True))
        if 'id_token_claims' in result:
            session['user'] = result['id_token_claims']
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run()