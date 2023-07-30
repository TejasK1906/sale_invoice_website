import numpy as np
import pandas as pd
from flask import Flask, request, jsonify, render_template, redirect
import mysql.connector
from decimal import Decimal

app = Flask(__name__)

# Configure MySQL database connection
db = mysql.connector.connect(
  host="aws.connect.psdb.cloud",
  user="erjpcdra7nparoj0d28g",
  password="pscale_pw_eOGCBC1sH58w81Lf2pcYqPlKhjaFVk7eKLQNyGkVova",
  database="shop",
  ssl_ca="/etc/ssl/cert.pem")


def get_customer_balance(customer_id):
  # Implement the logic to fetch the customer's last balance from the BalanceDetails table
  # If the customer is not found, return 0 as the initial balance
  cursor = db.cursor()
  balance_query = "SELECT Balance FROM balancedetails WHERE CustomerID = %s ORDER BY BalanceDetailsID DESC LIMIT 1"
  cursor.execute(balance_query, (customer_id, ))
  last_balance = cursor.fetchone()
  cursor.close()
  return last_balance[0] if last_balance else Decimal(0)


@app.route("/")
def home():
  return render_template('firstpage.html')


@app.route('/sale_invoice')
def sale_invoice():
  cursor = db.cursor()
  # Fetch distinct customer names and IDs from the Customers table
  customer_query = "SELECT DISTINCT CustomerID, CustomerName FROM customers"
  cursor.execute(customer_query)
  customers = cursor.fetchall()

  product_query = "SELECT ProductID, ProductName FROM products"
  cursor.execute(product_query)
  products = cursor.fetchall()

  cursor.close()
  return render_template('sale_invoice.html',
                         customers=customers,
                         products=products)


@app.route('/submit', methods=['POST'])
def submit_form():
  date = request.form.get('date')
  customer_id = request.form.get('customerId')
  customer_name = request.form.get('customerName')
  grand_total = request.form.get('grandTotal')
  payment_status = request.form.get('paymentStatus')
  cashpaid = 0
  credit = 0
  if payment_status == "Cash":
    cashpaid = grand_total
  else:
    credit = grand_total

  cursor = db.cursor()
  # Insert data into Sales table
  sale_query = "INSERT INTO sales (SaleDate,CustomerID,CustomerName, PaymentStatus, TotalOrderAmount, CashPaid,CreditAmount) VALUES (%s, %s, %s,%s, %s, %s,%s)"
  sale_values = (date, customer_id, customer_name, payment_status, grand_total,
                 cashpaid, credit)
  cursor.execute(sale_query, sale_values)

  # Get the auto-generated Sale Invoice ID for the newly inserted row
  new_sale_id = cursor.lastrowid

  # Insert data into SalesDetails table for each product in the form
  products = request.form.getlist('product[]')
  quantities = request.form.getlist('quantity[]')
  prices = request.form.getlist('price[]')
  amounts = request.form.getlist('total[]')

  for i in range(len(products)):
    product_name = products[i]
    quantity = quantities[i]
    amount = amounts[i]
    price = prices[i]
    details_query = "INSERT INTO salesdetails (SaleInvoiceID,CustomerID, ProductName, Quantity, Price,Amount) VALUES (%s, %s, %s, %s, %s, %s)"
    details_values = (new_sale_id, customer_id, product_name, quantity, price,
                      amount)
    cursor.execute(details_query, details_values)

  if payment_status == "Credit":
    last_balance = get_customer_balance(customer_id)
    # Calculate the new balance by adding the credit amount
    new_balance = last_balance + Decimal(credit)

    # Insert the updated balance record into the BalanceDetails table
    cursor = db.cursor()
    balance_query = "INSERT INTO balancedetails (balancedate,CustomerID, CustomerName, Remark, Credit, Debit, Balance) VALUES (%s, %s, %s, %s, %s, %s,%s)"
    balance_values = (date, customer_id, customer_name,
                      "Credit Sale Invoice #" + str(new_sale_id), credit, 0,
                      new_balance)
    cursor.execute(balance_query, balance_values)
    db.commit()
    cursor.close()

  # Commit the changes to the database
  db.commit()
  cursor.close()

  # Optionally, you can pass the Sale Invoice ID or other details to the success page
  return redirect('/sale_invoice_success?sale_id=' + str(new_sale_id))


@app.route('/sale_invoice_success')
def sale_invoice_success():
  sale_id = request.args.get('sale_id')
  return f"<h1>Form submitted successfully! Sale Invoice ID: {sale_id}</h1>"


@app.route('/add_new_customer')
def add_new_customer():
  # Add your logic for the Add New Customer page here
  # and return the corresponding template
  return render_template('add_new_customer.html')


@app.route('/submit_new_customer', methods=['POST'])
def submit_new_customer():
  customer_name = request.form.get('customerName')
  phone = request.form.get('phone')
  address = request.form.get('address')
  email = request.form.get('email')

  cursor = db.cursor()
  # Insert data into Customers table for the new customer
  customer_query = "INSERT INTO customers (CustomerName, Phone, Address, Email) VALUES (%s, %s, %s, %s)"
  customer_values = (customer_name, phone, address, email)
  cursor.execute(customer_query, customer_values)

  # Commit the changes to the database
  db.commit()
  cursor.close()

  # Optionally, you can pass a success message or redirect to a success page
  return redirect(
    '/new_customer_success?message=New customer added successfully.')


@app.route('/new_customer_success')
def new_customer_success():
  return "<h1>New Customer Added!"


@app.route('/balance_adjustment')
def balance_adjustment():
  cursor = db.cursor()
  # Fetch distinct customer names and IDs from the Customers table
  customer_query = "SELECT DISTINCT CustomerID, CustomerName FROM customers"
  cursor.execute(customer_query)
  customers = cursor.fetchall()

  cursor.close()
  return render_template('balance_adjustment.html', customers=customers)


@app.route('/submit_balance_adjustment', methods=['POST'])
def submit_balance_adjustment():
  date = request.form.get('date')
  customer_id = request.form.get('customerId')
  customer_name = request.form.get('customerName')
  transaction_type = request.form.get('transactionType')
  amount = Decimal(request.form.get('amount'))
  payment_method = request.form.get('paymentMethod')

  cursor = db.cursor()

  if transaction_type == "Debit":
    # If the transaction is a debit, subtract the amount from the customer's balance
    last_balance = get_customer_balance(customer_id)
    new_balance = last_balance - amount
    # Insert the updated balance record into the BalanceDetails table with the debit remark
    balance_query = "INSERT INTO balancedetails (balancedate,CustomerID, CustomerName, Remark, Credit, Debit, Balance) VALUES (%s, %s, %s, %s, %s, %s,%s)"
    balance_values = (date, customer_id, customer_name,
                      "Debit Adjustment - " + payment_method, 0, amount,
                      new_balance)
    cursor.execute(balance_query, balance_values)
  else:
    # If the transaction is a credit, add the amount to the customer's balance
    last_balance = get_customer_balance(customer_id)
    new_balance = last_balance + amount
    # Insert the updated balance record into the BalanceDetails table with the credit remark
    balance_query = "INSERT INTO balancedetails (balancedate,CustomerID, CustomerName, Remark, Credit, Debit, Balance) VALUES (%s, %s, %s, %s, %s, %s,%s)"
    balance_values = (date, customer_id, customer_name,
                      "Credit Adjustment - " + payment_method, amount, 0,
                      new_balance)
    cursor.execute(balance_query, balance_values)

  # Commit the changes to the database
  db.commit()
  cursor.close()

  # Optionally, you can pass a success message or redirect to a success page
  return redirect(
    '/balance_adjustment_success?message=Balance adjustment submitted successfully.'
  )


@app.route('/balance_adjustment_success')
def balance_adjustment_success():
  return "<h1>Balance adjustment submitted successfully!</h1>"


@app.route('/add_product')
def add_product():
  # Add your logic for the Add Product page here
  # and return the corresponding template
  return render_template('add_product.html')


@app.route('/submit_add_product', methods=['POST'])
def add_new_product():
  product_name = request.form.get('productName')
  cost_price = request.form.get('costPrice')
  sale_price = request.form.get('salePrice')

  cursor = db.cursor()
  # Insert data into the products table
  product_query = "INSERT INTO products (ProductName, CostPrice, SalePrice) VALUES (%s, %s, %s)"
  product_values = (product_name, cost_price, sale_price)
  cursor.execute(product_query, product_values)

  # Commit the changes to the database
  db.commit()
  cursor.close()

  # Optionally, you can redirect to a success page or perform other actions after adding the product.
  return redirect('/success_product_added')


@app.route('/success_product_added')
def product_added():
  return "<h1>Product added successfully!</h1>"


if __name__ == "__main__":
  app.run(host="0.0.0.0", debug=True)
