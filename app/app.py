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
DB_NAME = "qr_data_r7kw"
DB_USER = "qr_data_user"
DB_PASSWORD = "TOoKXgLEud2SrMgygj1G27hjFPUiIQ4R"
DB_HOST = "dpg-cvbqbg56l47c73agp5fg-a.singapore-postgres.render.com"
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
        cur.close()
        conn.close()
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
    
    # Create a single DataFrame with all data
    df = pd.DataFrame(data, columns=["QR Code", "Status"])
    
    # Debug: Print raw QR Codes to identify issues
    print("Raw QR Codes:", df['QR Code'].tolist())
    
    # Separate into normal tickets (starting with "Ticket-") and VIP tickets (starting with "VIP-Ticket-")
    normal_tickets = df[df['QR Code'].str.startswith("Ticket-")].copy()
    vip_tickets = df[df['QR Code'].str.startswith("VIP-Ticket-")].copy()
    
    # Function to extract the numerical part and sort
    def sort_tickets(df, ticket_type):
        if df.empty:
            return df
        # Create a sorting key for the Status column: Scanned (0), Not Scanned (1)
        df['sort_key_status'] = df['Status'].map({'Scanned': 0, 'Not Scanned': 1})
        
        # Extract the numerical part and handle errors
        def extract_number(qr_code):
            try:
                # Remove the appropriate prefix based on ticket type
                if ticket_type == "VIP":
                    num_str = qr_code.replace('VIP-Ticket-', '')
                else:
                    num_str = qr_code.replace('Ticket-', '')
                # Debug: Print the extracted string before conversion
                print(f"Extracted string for {qr_code}: {num_str}")
                # Convert to int, ensuring it's a valid number
                return int(num_str)
            except (ValueError, AttributeError) as e:
                print(f"Warning: Invalid number in QR Code '{qr_code}' for {ticket_type} ticket: {e}, setting to 0")
                return 0
        
        # Apply the extraction function and debug the results
        df['sort_key_number'] = df['QR Code'].apply(extract_number)
        print(f"Extracted numbers for {ticket_type} tickets:", df['sort_key_number'].tolist())
        
        # Sort by sort_key_status (to prioritize Scanned) and then by sort_key_number
        df = df.sort_values(by=['sort_key_status', 'sort_key_number'], ascending=[True, True])
        
        # Debug: Print the sorted DataFrame
        print(f"Sorted DataFrame for {ticket_type} tickets:\n", df[['QR Code', 'Status', 'sort_key_number']].to_string(index=False))
        
        # Drop the temporary sort keys
        df = df.drop(columns=['sort_key_status', 'sort_key_number'])
        
        return df
    
    # Apply sorting to both DataFrames with appropriate ticket type
    normal_tickets = sort_tickets(normal_tickets, "Normal")
    vip_tickets = sort_tickets(vip_tickets, "VIP")
    
    return normal_tickets, vip_tickets

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
            qr_content = obj.data.decode("utf-8")
            # Extract the part before the colon (e.g., "Ticket-1002" from "Ticket-1002:...")
            qr_code = qr_content.split(":")[0] if ":" in qr_content else qr_content
            return qr_code
    
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

# Sidebar for Login/Logout
st.sidebar.header("🔐 Authentication")

# Conditionally render login fields or logout message
if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    # Login form
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    login_button = st.sidebar.button("Login", key="login")
    
    if login_button:
        if username == USERNAME and password == PASSWORD:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.sidebar.error("❌ Invalid Credentials")
else:
    # Logout section
    st.sidebar.success("Logged in as admin")
    logout_button = st.sidebar.button("Logout", key="logout")
    
    if logout_button:
        # Clear the authenticated state and rerun
        st.session_state.pop("authenticated", None)
        st.rerun()

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
        
        # Fetch the two DataFrames
        normal_tickets, vip_tickets = fetch_qr_codes()
        
        # Define a styling function for the Status column
        def style_status(status):
            if status == "Not Scanned":
                return "color: red"  # Not Scanned in red
            else:
                return "color: green"  # Scanned in green
        
        # Display Normal Tickets Table
        st.subheader("Normal Tickets")
        if not normal_tickets.empty:
            styled_normal_df = normal_tickets.style.map(style_status, subset=["Status"])
            st.dataframe(styled_normal_df)
        else:
            st.write("No normal tickets found.")
        
        # Display VIP Tickets Table
        st.subheader("VIP Tickets")
        if not vip_tickets.empty:
            styled_vip_df = vip_tickets.style.map(style_status, subset=["Status"])
            st.dataframe(styled_vip_df)
        else:
            st.write("No VIP tickets found.")
    
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
        
        # Define color mapping for the pie chart
        color_map = {
            "Scanned": "#4CAF50",  # Green for Scanned
            "Not Scanned": "#FF0000"  # Red for Not Scanned
        }
        # Map colors to labels
        colors = [color_map[label] for label in labels]
        
        # Debug: Print labels and colors to verify
        print("Pie chart labels:", labels)
        print("Pie chart colors:", colors)
        
        fig, ax = plt.subplots()
        ax.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=90, colors=colors)
        ax.axis("equal")  # Equal aspect ratio ensures that pie is drawn as a circle.
        
        st.pyplot(fig)

else:
    st.warning("⚠️ Please log in to access the system.")