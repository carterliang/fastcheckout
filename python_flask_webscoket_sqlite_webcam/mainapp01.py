from flask import Flask, render_template, send_file
from flask_socketio import SocketIO, emit
import base64
from datetime import datetime
import json
import cv2
from ultralytics import YOLO
from PIL import Image
from gevent.pywsgi import WSGIServer
import pandas as pd
from db import *
from sqlite_utils import *
import os
# Function to install a package




app = Flask(__name__)
#-------------websocket------------------------    
socketio = SocketIO(app)
socketio.init_app(app, cors_allowed_origins="*")
@app.route('/')
def index():
   #return render_template('index.html')
   return app.send_static_file('index.html')
    
 
@app.route('/video')
def goto_video():
    return render_template('html5_camera_1.html')
    
@app.route('/item')
def get_item():
   #return render_template('index.html')
  return render_template('viewreport02.html')

DataBase = 'database/example.db'
current_order_details = {}

@app.route('/download', methods=['GET'])
def download():
    global current_order_details
    if not current_order_details:
        return "No order details available to download.", 400
    
    try:
        order_id = current_order_details['order_id']
        order_date = current_order_details['order_date']
        details_df = current_order_details['details']
        total_amount = current_order_details['total_amount']
        
        filename = f"order_{order_id}.xlsx"
        filepath = os.path.join('downloads', filename)
        
        if not os.path.exists('downloads'):
            os.makedirs('downloads')
        
        with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
            workbook = writer.book
            worksheet = workbook.add_worksheet('OrderDetails')
            
            # Format for bold text
            bold = workbook.add_format({'bold': True})
            
            # Write order ID and date
            worksheet.write(0, 0, f'訂單編號: {order_id}', bold)
            worksheet.write(1, 0, f'訂單日期: {order_date}', bold)
            
            # Write the dataframe to the worksheet, starting from row 3 to avoid overlap
            details_df.to_excel(writer, sheet_name='OrderDetails', startrow=3, index=False)
            
            # Format the header row
            for col_num, value in enumerate(details_df.columns.values):
                worksheet.write(3, col_num, value, bold)
            
            # Write the total amount
            worksheet.write(len(details_df) + 4, 0, '結帳金額', bold)
            worksheet.write(len(details_df) + 4, 1, total_amount)
        
        return send_file(filepath, as_attachment=True)
    except Exception as e:
        print(f"Error generating Excel file: {e}")
        return f"Error generating Excel file: {e}", 500

@socketio.on('search')
def handle_search(data):
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    
    if not start_date or not end_date:
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
    
    conn = sqlite3.connect(DataBase)
    query = '''
        SELECT 
            M.o_id, M.o_date, M.o_total
        FROM 
            ORDER_M M
        JOIN 
            ORDER_D D ON M.o_id = D.o_id
        WHERE
            M.o_date BETWEEN ? AND ?
        GROUP BY M.o_id, M.o_date, M.o_total
    '''
    try:
        df = pd.read_sql_query(query, conn, params=(start_date, end_date))
        
        df.columns = ['訂單編號', '訂單日期', '金額']
        
        if df.empty:
            emit('search_results', {'results': []})
        else:
            orders = df.to_dict('records')
            emit('search_results', {'results': orders})
    except Exception as e:
        print(f"Error executing query: {e}")
        emit('search_results', {'results': f"Error executing query: {e}"})
    finally:
        conn.close()

@socketio.on('get_order_details')
def handle_order_details(data):
    global current_order_details
    o_id = data['o_id']
    conn = sqlite3.connect(DataBase)
    query = '''
        SELECT p_id, p_name, p_price, SUM(p_qty) as total_qty
        FROM ORDER_D
        WHERE o_id = ?
        GROUP BY p_id, p_name, p_price
    '''
    try:
        df = pd.read_sql_query(query, conn, params=(o_id,))
        df['商品序號'] = df.index + 1  # Adding a new column for '商品序號'
        df['金額'] = df['p_price'] * df['total_qty']  # Calculating the amount for each item
        total_amount = df['金額'].sum()
        
        df = df[['商品序號', 'p_id', 'p_name', 'p_price', 'total_qty', '金額']]  # Reordering columns
        
        df.columns = ['商品序號', '商品編號', '商品名稱', '商品單價', '商品數量', '金額']  # Renaming columns
        
        if df.empty:
            emit('order_details', {'details': 'No data found.'})
        else:
            details_html = df.to_html(index=False)
            details_html += f'<p>結帳金額: {total_amount}</p>'
            # Fetching order date
            order_query = 'SELECT o_date FROM ORDER_M WHERE o_id = ?'
            order_date = pd.read_sql_query(order_query, conn, params=(o_id,)).iloc[0, 0]
            current_order_details = {'order_id': o_id, 'order_date': order_date, 'details': df, 'total_amount': total_amount}
            emit('order_details', {'details': details_html, 'order_id': o_id, 'order_date': order_date})
    except Exception as e:
        print(f"Error executing query: {e}")  # Debug line
        emit('order_details', {'details': f"Error executing query: {e}"})
    finally:
        conn.close()


if __name__ == '__main__':
    socketio.run(app, host='127.0.0.1', port=3000, debug=True)
