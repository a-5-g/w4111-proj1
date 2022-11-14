
"""
Columbia's COMS W4111.001 Introduction to Databases
Example Webserver
To run locally:
    python3 server.py
Go to http://localhost:8111 in your browser.
A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""
import os
  # accessible as a variable in index.html:
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Blueprint, Flask, request, render_template, g, redirect, Response, session, url_for , jsonify
from datetime import date
from decimal import Decimal

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)
app.secret_key = os.urandom(24)

#
# The following is a dummy URI that does not connect to a valid database. You will need to modify it to connect to your Part 2 database in order to use the data.
#
# XXX: The URI should be in the format of:
#
#     postgresql://USER:PASSWORD@34.75.94.195/proj1part2
#
# For example, if you had username gravano and password foobar, then the following line would be:
#
#     DATABASEURI = "postgresql://gravano:foobar@34.75.94.195/proj1part2"
#
DATABASEURI = "postgresql://ag4478:1459@34.75.94.195/proj1part2"


#
# This line creates a database engine that knows how to connect to the URI above.
#
engine = create_engine(DATABASEURI)

#
# Example of running queries in your database
# Note that this will probably not work if you already have a table named 'test' in your database, containing meaningful data. This is only an example showing you how to run queries in your database using SQLAlchemy.
#
engine.execute("""CREATE TABLE IF NOT EXISTS test (
  id serial,
  name text
);""")
engine.execute("""INSERT INTO test(name) VALUES ('grace hopper'), ('alan turing'), ('ada lovelace');""")


@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request.

  The variable g is globally accessible.
  """
  try:
    g.conn = engine.connect()
  except:
    print("uh oh, problem connecting to database")
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't, the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass


#
# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a GET request
#
# If you wanted the user to go to, for example, localhost:8111/foobar/ with POST or GET then you could use:
#
#       @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
#
# see for routing: https://flask.palletsprojects.com/en/2.0.x/quickstart/?highlight=routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
#
@app.route('/')
def index():
  return redirect(url_for('login'))


@app.route('/viewProducts')
def viewProducts():
  """
  request is a special object that Flask provides to access web request information:

  request.method:   "GET" or "POST"
  request.form:     if the browser submitted a form, this contains the data in the form
  request.args:     dictionary of URL arguments, e.g., {a:1, b:2} for http://localhost?a=1&b=2

  See its API: https://flask.palletsprojects.com/en/2.0.x/api/?highlight=incoming%20request%20data

  """

  # DEBUG: this is debugging code to see what request looks like

  #
  # example of a database query
  #
  cursor = g.conn.execute("select p.proid, p.price, p.pname, p.expiry, c.catname from Product p, Category c, Contains con where p.proid = con.proid and con.catid = c.catid")
  names = []
  key = cursor.keys()
  for result in cursor:
    names.append(result)  # can also be accessed using result[0]
  cursor.close()
  context = dict(data = names)

  #
  # render_template looks in the templates/ folder for files.
  # for example, the below file reads template/index.html
  #
  session["productDetails"] = []
  for row in names:
    tmp = dict(row)
    tmp['price'] = float(tmp['price'])
    session["productDetails"].append(tmp) 
  return render_template("index.html", **context, custId = session['custId'], custName = session["custName"])

#
# This is an example of a different path.  You can see it at:
#
#     localhost:8111/another
#
# Notice that the function name is another() rather than index()
# The functions for each app.route need to have different names
#
@app.route('/details', methods=['GET'])
def details():
  pid = request.args['proid']
  cursor = g.conn.execute("With temp (proid, product, price, expiry, category, SupplierID) as (select p.proid, p.pname as Name , p.price as Price, p.expiry as Expiry, c.catname as Category, s.supid as SupplierID from (Product p natural inner join Contains con natural inner join Comes_from com natural inner join Category c natural inner join supplier s) where p.proid = (%s)), brandtable (proid, brand_name) as (select bt.proid, b.brand_name from brand b natural inner join belongs_to bt) select temp.product as Product, temp.price, temp.expiry, temp.category, brandtable.brand_name as brand, temp.SupplierID, pr.rating, pr.review_text as Review from (temp left outer join ProductReview pr on temp.proid = pr.proid) left outer join brandtable on temp.proid = brandtable.proid", pid)

  names = []
  key = cursor.keys()
  names.append(key)
  #print(cursor.column_names)
  for result in cursor:
    names.append(result)  # can also be accessed using result[0]
  cursor.close()
  context = dict(data = names)
  return render_template("details.html", **context, custId=session['custId'], custName=session["custName"])


@app.route('/invalid',methods=['GET'])
def invalid():
  invalidLogin = False
  
  if 'custId' not in session or  session['custId'] == None:
    invalidLogin = True
  
  return render_template('invalidComponent.html',invalidLogin = invalidLogin)
    
  
@app.route('/orderplaced')
def orderplaced():
  return render_template("orderplaced.html", custId=session['custId'], custName=session["custName"])

# Navigating to orders page
@app.route('/viewOrders', methods=['GET'])
def viewOrders():
  custId = request.args['custId']
  result  = g.conn.execute('''SELECT ad.orderid , Sum(ad.quantity) as itemCount , Sum(ad.quantity*p.price) as amount, po.pay_date as Order_date,po.pay_method
FROM added_to ad, product p, PlacesOrder po
WHERE ad.custid = (%s) AND p.proid = ad.proid AND po.orderid = ad.orderid 
GROUP By ad.orderid, po.pay_date, po.pay_method;''', custId)
  return render_template('viewOrders.html', orders = result, custId = custId, custName = session["custName"])  

@app.route('/viewOrderDetails', methods=['GET'])
def viewOrderDetails():
  custId = request.args['custId']
  orderId = request.args['orderId']
  result  = g.conn.execute('''SELECT p.pname,b.brand_name,ct.catname,p.price,ad.quantity, ad.quantity*p.price as "Total Price" FROM added_to ad, customer c, product p, brand b, belongs_to as bt, contains cn, category ct WHERE ad.custid = c.custid AND ad.proid = p.proid AND c.custid=(%s) AND orderId = (%s) 
  AND b.brid=bt.brid AND p.proid=bt.proid AND cn.proid = p.proid AND cn.catid =  ct.catid;''', custId,orderId)
  return render_template('viewOrderDetails.html', productOrders = result , orderId = orderId, custId=session['custId'], custName=session["custName"])  


@app.route('/login',methods=['GET', 'POST'])
def login():
  if request.method == 'POST':
        result  = g.conn.execute('''SELECT c.custId FROM customer c WHERE c.name= (%s) AND c.password= (%s);''',request.form['username'],request.form['password'])
        if result.rowcount == 0:
          return redirect(url_for('invalid'))
        else:
          result = result.first()
          session['custId'] = result[0]
          session['custName'] = request.form['username']
          return redirect(url_for('viewProducts'))
  return render_template('loginpage.html')

@app.route('/logout',methods=['GET'])
def logout():
  session.pop('custId',None)
  return redirect(url_for('login'))


@app.route('/addnewCustomer',methods=['GET','POST'])
def addnewCustomer():
  if request.method == 'POST':
    try:
      g.conn.execute('''INSERT INTO CUSTOMER(name,password,phone) VALUES(%s,%s,%s);''',request.form['name'],request.form['password'],request.form['phone'])
      result  = g.conn.execute('''SELECT c.custId FROM customer c WHERE c.name= (%s) AND c.password= (%s);''',request.form['name'],request.form['password'])
      
      session['custId'] = result.first()[0]
      session['custName'] = request.form['name']

      # Adding the address
      g.conn.execute('''INSERT INTO ADDRESS(street,aptno,city,state,zip,custid) VALUES(%s,%s,%s,%s,%s,%s);''',request.form['street'],request.form['aptno'],request.form['city'],request.form['state'],request.form['zip'],session['custId'])
      return redirect(url_for('viewProducts'))
    except:
      return redirect(url_for('invalid'))
  return render_template('signUpForm.html')

@app.route('/addNewOrder',methods=["POST"])
def addNewOrder():
  ordersTable = request.form
  productList = session['productDetails']
  paymentMethod = request.form["payment"]

  count = 0
  for row in ordersTable:
    try:
      if int(row):
        productIndex = int(row)-1
        quantity = int(ordersTable[row])
        count+=1
    except:
      continue
  
  if count==0:
    # no updated the element
    return redirect(url_for('invalid'))


  # Creating an Order Id
  orderId = g.conn.execute('''INSERT INTO PLACESORDER(custid,pay_method,pay_date) VALUES(%s,%s,%s) RETURNING orderid''',session["custId"],paymentMethod,date.today())
  orderId = orderId.first()[0]
  # now we need to insert entries in the added to of the items included in the given order
  for row in ordersTable:
    try:
      if int(row):
        productIndex = int(row)-1
        quantity = int(ordersTable[row])
        if quantity!=0:
          productDetails = productList[productIndex]  
          g.conn.execute('''INSERT INTO ADDED_TO(orderid,proid,quantity,custid) VALUES(%s,%s,%s,%s)''',orderId,productDetails["proid"],quantity,session["custId"])
    except:
      continue

  return render_template('orderplaced.html',orderId = orderId, custId=session['custId'], custName=session["custName"])

if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using:

        python3 server.py

    Show the help text using:

        python3 server.py --help

    """

    HOST, PORT = host, port
    print("running on %s:%d" % (HOST, PORT))
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

  run()
