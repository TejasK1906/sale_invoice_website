from sqlalchemy import create_engine, text
import mysql.connector
import numpy as np
import pandas as pd
# engine = create_engine(
#   "mysql+pymysql://us95k0t80dwp8knssvnt:pscale_pw_fz1tu7EglZlma069wuOFcm4XsZC103TMdZgazFLJq4N@aws.connect.psdb.cloud/shop?charset=utf8mb4"
# )

db = mysql.connector.connect(
  host="aws.connect.psdb.cloud",
  user="us95k0t80dwp8knssvnt",
  password="pscale_pw_fz1tu7EglZlma069wuOFcm4XsZC103TMdZgazFLJq4N",
  database="shop",
  ssl_ca="/etc/ssl/cert.pem")

cursor = db.cursor()

customer_query = "SELECT DISTINCT CustomerID, CustomerName FROM customers"
cursor.execute(customer_query)
customers = cursor.fetchall()
print(customers)