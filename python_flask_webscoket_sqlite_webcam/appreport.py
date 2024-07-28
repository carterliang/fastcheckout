from flask import Flask, render_template, send_file
from flask_socketio import SocketIO, emit
import sqlite3
import pandas as pd
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

DATABASE = 'database/example.db'

# 創建並插入數據到 SQLite 資料庫
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Check if tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ORDER_M';")
    table_M = cursor.fetchone()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ORDER_D';")
    table_D = cursor.fetchone()

    if table_M and table_D:
        print("Both tables exist.")
    else:
        print("One or both tables are missing.")

    # Close the connection
    conn.close()

@app.route('/')
def index():
    return render_template('viewreport.html')

@socketio.on('search')
def handle_search(data):
    start_date = data['start_date']
    end_date = data['end_date']
    # 檢查日期格式是否為 YYYY-MM-DD，如果是則轉換為 YYYYMMDD
    if '-' in start_date:
        start_date = datetime.strptime(start_date, "%Y-%m-%d").strftime("%Y%m%d")
    if '-' in end_date:
        end_date = datetime.strptime(end_date, "%Y-%m-%d").strftime("%Y%m%d")

    print(f"Searching between {start_date} and {end_date}")  # Debug line

    conn = sqlite3.connect(DATABASE)
    query = '''
        SELECT 
            M.o_id, M.o_date, M.o_total, D.o_no, D.p_id, D.p_name, D.p_price, D.p_qty
        FROM 
            ORDER_M M
        JOIN 
            ORDER_D D ON M.o_id = D.o_id
        WHERE
            M.o_date BETWEEN ? AND ?
    '''
    try:
        df = pd.read_sql_query(query, conn, params=(start_date, end_date))
        print(f"Query result: {df}")  # Debug line
        
        # 修改列名稱為中文
        df.columns = ['訂單編號', '交易日期', '交易金額', '品項序號', '產品編號', '產品名稱', '價格', '數量']
        
        if df.empty:
            emit('search_results', {'results': 'No data found.'})
        else:
            results_html = df.to_html(index=False)
            emit('search_results', {'results': results_html})
    except Exception as e:
        print(f"Error executing query: {e}")  # Debug line
        emit('search_results', {'results': f"Error executing query: {e}"})
    finally:
        conn.close()

@socketio.on('download')
def handle_download(data):
    start_date = data['start_date']
    end_date = data['end_date']
    # 檢查日期格式是否為 YYYY-MM-DD，如果是則轉換為 YYYYMMDD
    if '-' in start_date:
        start_date = datetime.strptime(start_date, "%Y-%m-%d").strftime("%Y%m%d")
    if '-' in end_date:
        end_date = datetime.strptime(end_date, "%Y-%m-%d").strftime("%Y%m%d")

    print(f"Downloading data between {start_date} and {end_date}")  # Debug line

    conn = sqlite3.connect(DATABASE)
    query = '''
        SELECT 
            M.o_id, M.o_date, M.o_total, D.o_no, D.p_id, D.p_name, D.p_price, D.p_qty
        FROM 
            ORDER_M M
        JOIN 
            ORDER_D D ON M.o_id = D.o_id
        WHERE
            M.o_date BETWEEN ? AND ?
    '''
    try:
        df = pd.read_sql_query(query, conn, params=(start_date, end_date))
        print(f"Query result for download: {df}")  # Debug line
        
        # 修改列名稱為中文
        df.columns = ['訂單編號', '交易日期', '交易金額', '品項序號', '產品編號', '產品名稱', '價格', '數量']
        
        if df.empty:
            emit('download', {'file': 'No data found to download.'})
        else:
            output_file = generate_excel(df)
            emit('download', {'file': f"/download/{output_file}"})
    except Exception as e:
        print(f"Error executing query for download: {e}")  # Debug line
        emit('download', {'file': f"Error executing query: {e}"})
    finally:
        conn.close()

def generate_excel(df):
    if not os.path.exists('exports'):
        os.makedirs('exports')
    
    date_str = datetime.now().strftime('%Y%m%d')
    existing_files = [f for f in os.listdir('exports') if f.startswith(date_str)]
    serial_number = len(existing_files) + 1
    
    file_name = f"{date_str}{serial_number:02d}.xlsx"
    file_path = os.path.join('exports', file_name)
    
    df.to_excel(file_path, index=False)
    print(f"Excel file generated at: {file_path}")  # Debug line
    
    return file_name

@app.route('/download/<path:filename>', methods=['GET'])
def download(filename):
    file_path = os.path.join('exports', filename)
    if os.path.exists(file_path):
        print(f"Sending file: {file_path}")  # Debug line
        return send_file(file_path, as_attachment=True)
    else:
        print(f"File not found: {file_path}")  # Debug line
        return "File not found", 404

if __name__ == '__main__':
    init_db()
    socketio.run(app, debug=True, port=3000)
