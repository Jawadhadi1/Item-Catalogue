from flask import Flask, render_template, request, redirect, url_for, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Supermarket, Item, User

from flask import session as login_session
import string
import random

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import json
import httplib2
import requests
from flask import make_response



app = Flask(__name__)


CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Supermarket Application"

engine = create_engine('sqlite:///supermarket.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

# Creating anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html')

@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id

    # Check if user exists, if it doesnt make its record
    user_id=getUserID(login_session['email'])
    if not user_id:
        user_id=createUser(login_session)
        login_session['user_id']=user_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output

def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id

def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user

@app.route('/gdisconnect')
def gdisconnect():
        # Only disconnect a connected user.
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] == '200':
        # Reset the user's sesson.
        del login_session['credentials']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


#JSON APIs to view information about supermarkets
@app.route('/supermarket/JSON')
def supermarketsJSON():
    supermarkets = session.query(Supermarket).all()
    return jsonify(supermarkets=[s.serialize for s in supermarkets])

@app.route('/supermarket/<int:supermarket_id>/items/JSON')
def supermarketitemsJSON(supermarket_id):
    supermarket = session.query(Supermarket).filter_by(id=supermaket_id).one()
    items = session.query(Item).filter_by(
        supermarket_id=supermarket_id).all()
    return jsonify(items=[i.serialize for i in items])



# Show all supermarkets
@app.route('/')
@app.route('/supermarket/')
def show_supermarkets():
    supermarkets = session.query(Supermarket).all()
    if 'username' not in login_session:
        return render_template('publicsupermarkets.html', supermarkets=supermarkets)
    else:
        return render_template('supermarkets.html', supermarkets=supermarkets)


# Create a new supermarket
@app.route('/supermarket/new/', methods=['GET', 'POST'])
def new_supermarket():
        if 'username' not in login_session:
            return redirect ('/login')
        if request.method == 'POST':
            new_supermarket = Supermarket(name=request.form['name'], user_id=login_session['user_id'])
            session.add(new_supermarket)
            session.commit()
            return redirect(url_for('show_supermarkets'))
        else:
            return render_template('new_supermarket.html')

# Edit a supermarket
@app.route('/supermarket/<int:supermarket_id>/edit/', methods=['GET', 'POST'])
def edit_supermaket(supermarket_id):
        if 'username' not in login_session:
            return redirect ('/login')
        edited_supermarket = session.query(Supermarket).filter_by(id=supermarket_id).one()
        if request.method == 'POST':
            if request.form['name']:
                edited_supermarket.name = request.form['name']
            return redirect(url_for('show_supermarkets', supermarket_id=supermarket_id ))
        else:
            return render_template(
            'edit_supermarket.html', supermarket=edited_supermarket)

# Delete a supermarket
@app.route('/supermarket/<int:supermarket_id>/delete/', methods=['GET', 'POST'])
def delete_supermarket(supermarket_id):
        if 'username' not in login_session:
            return redirect ('/login')
        supermarket_to_delete = session.query(Supermarket).filter_by(id=supermarket_id).one()
        if request.method == 'POST':
            session.delete(supermarket_to_delete)
            session.commit()
            return redirect(url_for('show_supermarkets', supermarket_id=supermarket_id))
        else:
            return render_template(
            'delete_supermarket.html', supermarket=supermarket_to_delete)

# Show a supermarket's items
@app.route('/supermarket/<int:supermarket_id>/')
@app.route('/supermarket/<int:supermarket_id>/items/')
def show_items(supermarket_id):
    supermarket = session.query(Supermarket).filter_by(id=supermarket_id).one()
    supermarket_creator=getUserInfo(supermarket.user_id)
    items = session.query(Item).filter_by(supermarket_id=supermarket_id).all()
    if 'username' not in login_sesssion or supermarket_creator.id != login_session['user_id']:
        return render_template('publicitems.html', items=items, supermarket=supermarket, creator=creator)
    else:
        return render_template('items.html', items=items, supermarket=supermarket, creator=creator)

# Create a new item for a supermarket
@app.route(
    '/supermarket/<int:supermarket_id>/items/new/', methods=['GET', 'POST'])
def new_item(supermarket_id):
    if 'username' not in login_session:
        return redirect ('/login')
    if request.method == 'POST':
        new_item = Item(name=request.form['name'], description=request.form['description'], price=request.form['price'], supermarket_id=supermarket_id,
                        user_id=supermarket.user_id)
        session.add(new_item)
        session.commit()

        return redirect(url_for('show_items', supermarket_id=supermarket_id))
    else:
        return render_template('new_item.html', supermarket_id=supermarket_id, supermarket=supermarket)

# Edit a supermarket's item
@app.route('/supermarket/<int:supermarket_id>/items/<int:item_id>/edit',methods=['GET', 'POST'])
def edit_item(supermarket_id, item_id):
        if 'username' not in login_session:
            return redirect ('/login')
        edited_item = session.query(Item).filter_by(id=item_id).one()
        if request.method == 'POST':
            if request.form['name']:
                edited_item.name = request.form['name']
            if request.form['description']:
                edited_item.description = request.form['description']
            if request.form['price']:
                edited_item.price = request.form['price']
                session.add(edited_item)
                session.commit()
            return redirect(url_for('show_items', supermarket_id=supermarket_id))
        else:
            return render_template(
            'edit_item.html', supermarket_id=supermarket_id, item_id=item_id, item=edited_item)

# Delete a supermarket item
@app.route('/supermarket/<int:supermarket_id>/items/<int:item_id>/delete',methods=['GET', 'POST'])
def delete_item(supermarket_id, item_id):
        if 'username' not in login_session:
            return redirect ('/login')
        item_to_delete = session.query(Item).filter_by(id=item_id).one()
        if request.method == 'POST':
            session.delete(item_to_delete)
            session.commit()
            return redirect(url_for('show_items', supermarket_id=supermarket_id))
        else:
            return render_template('delete_item.html', item=item_to_delete)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
