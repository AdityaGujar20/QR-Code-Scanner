import streamlit as st
import psycopg2
import pandas as pd
import numpy as np
import pyzbar.pyzbar as pyzbar
from PIL import Image
import matplotlib.pyplot as plt

# Hardcoded login credentials
USERNAME = "admin"
PASSWORD = "password123"

# Database configuration
DB_NAME = "qr_data"
DB_USER = "qr_data_user"
DB_PASSWORD = "XLR4DyJQ44o7k5GctdUmWMcjAzjmZysW"
DB_HOST = "dpg-cum7dfhu0jms73bl29c0-a.singapore-postgres.render.com"
DB_PORT = "5432"

# Function to connect to the database
def connect_db():
    return psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
    )

# Function to verify QR code
def verify_qr(qr_code):
    conn = connect_db()
    cur = conn.cursor()
    
    # Check if QR exists and its status
    cur.execute("SELECT status FROM qr_codes WHERE qr_code = %s", (qr_code,))
    result = cur.fetchone()
    
    if result is None:
        return "QR Code Not Found"
    elif result[0] == "Not Scanned":
        # Update status to scanned
        cur.execute("UPDATE qr_codes SET status = 'Scanned' WHERE qr_code = %s", (qr_code,))
        conn.commit()
        cur.close()
        conn.close()
        return "✅ QR Code is Valid and Marked as Scanned"
    else:
        cur.close()
        conn.close()
        return "❌ QR Code is Not Valid (Already Scanned)"

# Function to fetch QR codes from the database
def fetch_qr_codes():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT qr_code, status FROM qr_codes")
    data = cur.fetchall()
    cur.close()
    conn.close()
    return pd.DataFrame(data, columns=["QR Code", "Status"])

# Function to get QR code status counts
def get_qr_status_counts():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT status, COUNT(*) FROM qr_codes GROUP BY status")
    data = cur.fetchall()
    cur.close()
    conn.close()
    return dict(data)

# Function to scan QR code from an image
def scan_qr(image):
    if image is not None:
        image = Image.open(image).convert("L")  # Convert to grayscale
        image = np.array(image)
        decoded_objects = pyzbar.decode(image)
        
        for obj in decoded_objects:
            return obj.data.decode("utf-8")
    
    return None

# Streamlit UI Styling
st.set_page_config(page_title="QR Code Verification System", page_icon="🔍", layout="wide")

st.markdown("""
    <style>
        .big-font { font-size:24px !important; }
        .stButton>button { background-color: #006039; color: white; font-size: 18px; padding: 10px; }
    </style>
""", unsafe_allow_html=True)

st.title("🔍 QR Code Verification System")

# Login Page
st.sidebar.header("🔐 Login")
username = st.sidebar.text_input("Username")
password = st.sidebar.text_input("Password", type="password")
login_button = st.sidebar.button("Login", key="login")
logout_button = st.sidebar.button("Logout", key="logout")

if logout_button:
    st.session_state.pop("authenticated", None)
    st.rerun()

if login_button:
    if username == USERNAME and password == PASSWORD:
        st.session_state["authenticated"] = True
    else:
        st.sidebar.error("❌ Invalid Credentials")

if "authenticated" in st.session_state and st.session_state["authenticated"]:
    tab1, tab2, tab3 = st.tabs(["📸 QR Code Scanner", "📋 QR Code Table", "📊 Statistics"])
    
    with tab1:
        st.header("📸 Scan QR Code")
        uploaded_image = st.file_uploader("Upload QR Code Image", type=["png", "jpg", "jpeg"], help="Upload an image containing a QR code.")
        camera_image = st.camera_input("Scan using Webcam")
        
        qr_code = None
        
        if uploaded_image:
            qr_code = scan_qr(uploaded_image)
        elif camera_image:
            qr_code = scan_qr(camera_image)
        
        if qr_code:
            result = verify_qr(qr_code)
            st.success(f"✅ Scanned QR Code: {qr_code}")
            if "Valid" in result:
                st.success(result)
            else:
                st.error(result)
        elif uploaded_image or camera_image:
            st.error("⚠️ No QR Code detected. Please try again.")
    
    with tab2:
        st.header("📋 QR Code Status Table")
        df = fetch_qr_codes()
        st.dataframe(df.style.applymap(lambda x: "color: green" if x == "Not Scanned" else "color: red", subset=["Status"]))
    
    with tab3:
        st.header("📊 QR Code Status Distribution")
        status_counts = get_qr_status_counts()
        
        # Get counts
        scanned_count = status_counts.get("Scanned", 0)
        not_scanned_count = status_counts.get("Not Scanned", 0)
        total_qr_count = scanned_count + not_scanned_count
        
        # Display summary counts
        st.subheader("📌 Summary")
        st.write(f"🔢 **Total QR Codes:** {total_qr_count}")
        st.write(f"✅ **Scanned QR Codes:** {scanned_count}")
        st.write(f"🔴 **Not Scanned QR Codes:** {not_scanned_count}")
        
        # Pie chart
        labels = list(status_counts.keys())
        sizes = list(status_counts.values())
        
        fig, ax = plt.subplots()
        ax.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=90, colors=["#4CAF50", "#FF5733"])
        ax.axis("equal")  # Equal aspect ratio ensures that pie is drawn as a circle.
        
        st.pyplot(fig)

else:
    st.warning("⚠️ Please log in to access the system.")