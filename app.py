import streamlit as st
import pandas as pd
import requests
import os
import matplotlib.pyplot as plt
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

st.set_page_config(page_title="Productivity Dashboard", layout="wide")
EXPENSE_FILE = "expenses.csv"
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

# api calls
import requests


def get_city_from_ip():
    """Detects city name based on the actual public IP address."""
    try:
        # Step 1: Get your public IP address
        ip_response = requests.get("https://api.ipify.org?format=json", timeout=5)
        user_ip = ip_response.json().get("ip")
        
        # Step 2: Get city details for that specific IP
        response = requests.get(f"http://ip-api.com/json/{user_ip}", timeout=5)
        data = response.json()
        
        if data.get('status') == 'success':
            return data['city']
    except Exception as e:
        print(f"Location error: {e}")
    return "New York"  # Fallback

def get_weather(city):
    base_url = "http://api.weatherapi.com/v1/current.json"
    params = {
        "key": WEATHER_API_KEY,
         "q": city, 
         "aqi": "no"}
    try:
        response = requests.get(base_url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        temp = f"{data['current']['temp_c']}°C"
        condition = data['current']['condition']['text']
        return temp, condition
    except Exception:
        return "N/A", "Check Connection/City Name"

def get_quote():
    try:
        r = requests.get("https://zenquotes.io/api/random", timeout=3).json()
        return f"\"{r[0]['q']}\" — {r[0]['a']}"
    except:
        return "Keep going! Everything you need is already within you."

# This ensures we only look up the IP once per session
if 'detected_city' not in st.session_state:
    st.session_state.detected_city = get_city_from_ip()

st.markdown("<h1 style='text-align: center;'>Personal Productivity Dashboard</h1>", unsafe_allow_html=True)

# CSS to help keep containers roughly the same size
st.markdown("""<style> [data-testid="stVerticalBlockBorderWrapper"] { min-height: 250px; } </style>""", unsafe_allow_html=True)

col_w, col_q = st.columns(2)

with col_w:
    with st.container(border=True):
        st.subheader("Real Time Weather")
        # Use the detected city from session state as the default
        city_input = st.text_input("Enter City", st.session_state.detected_city)

        temp, desc = get_weather(city_input)
        st.metric(label=f"Current Temp in {city_input}", value=temp, delta=desc)

with col_q:
    with st.container(border=True):
        st.subheader("Daily Motivation")
        st.info(get_quote())

st.divider()

# expense tracker

st.markdown("<h1 style='text-align: center;'>Smart Expense Tracker</h1>", unsafe_allow_html=True)

_, col_center, _ = st.columns([1, 2, 1])

with col_center:
    with st.container(border=True):
        st.write("### Add New Entry")
        with st.form("expense_form", clear_on_submit=True):
            exp_date = st.date_input("Select Date", datetime.now()) 
            amt = st.number_input("Amount ($)", min_value=0.0, max_value=10000000.0, step=0.01)
            
            cat_list = ["", "Food", "Transport", "Bills", "Shopping", "Entertainment", "Other"]
            cat = st.selectbox("Select Category", cat_list)
            custom_cat = st.text_input("Or Type New Category")
            
            submit_button = st.form_submit_button("Log Expense", use_container_width=True)

            if submit_button:
                final_cat = custom_cat.strip().title() if custom_cat.strip() else cat
                
                if amt > 10000000:
                    st.error("Amount exceeded limit ($10,000,000)")
                elif amt <= 0:
                    st.warning("Please enter an amount.")
                elif not final_cat:
                    st.warning("Please select a category.")
                else:
                    new_entry = pd.DataFrame([[str(exp_date), amt, final_cat]], columns=["Date", "Amount", "Category"])
                    if not os.path.isfile(EXPENSE_FILE):
                        new_entry.to_csv(EXPENSE_FILE, index=False)
                    else:
                        new_entry.to_csv(EXPENSE_FILE, mode='a', header=False, index=False)
                    st.success(f"Added ${amt}!")
                    st.rerun()

st.divider()


if os.path.exists(EXPENSE_FILE):
    # Load full data
    df = pd.read_csv(EXPENSE_FILE)
    
    col_table, col_chart = st.columns([1, 1])

    with col_table:
        with st.container(border=True):
            st.write("### Recent History")
            
            
            edited_df = st.data_editor(
                df, 
                num_rows="dynamic", 
                use_container_width=True, 
                height=350, 
                key="expense_editor"
            )
            
            if st.button("Save Changes", use_container_width=True):
                edited_df.to_csv(EXPENSE_FILE, index=False)
                st.success("File Updated!")
                st.rerun()
    
    with col_chart:
        with st.container(border=True):
            st.write("Spending Summary & Budget")
            
            if not edited_df.empty:
                total_spent = edited_df["Amount"].sum()
                
    with col_chart:
        with st.container(border=True):
            st.write("### Monthly Budget Tracker")
            
            if not edited_df.empty:
                # Convert Date column to datetime objects
                edited_df['Date'] = pd.to_datetime(edited_df['Date'])
                
                # Create a Month-Year selector
                edited_df['Month_Year'] = edited_df['Date'].dt.strftime('%B %Y')
                available_months = edited_df['Month_Year'].unique()
                selected_month = st.selectbox("Select Month to View", available_months)
                
                # Filter data for the selected month
                month_df = edited_df[edited_df['Month_Year'] == selected_month]
                total_spent = month_df["Amount"].sum()
                
                # --- Budget Logic ---
                monthly_budget = st.number_input(f"Budget for {selected_month} ($)", min_value=1.0, value=1000.0, step=50.0)
                remaining = monthly_budget - total_spent
                progress_perc = min(total_spent / monthly_budget, 1.0)
                
                if total_spent > monthly_budget:
                    st.error(f"Over Budget by ${abs(remaining):,.2f} for {selected_month}!")
                else:
                    st.success(f"${remaining:,.2f} remaining for {selected_month}.")
                
                st.progress(progress_perc)
                
                
                st.write(f"**Spending Breakdown for {selected_month}:**")
                summary = month_df.groupby("Category")["Amount"].sum()
                st.table(summary.map("${:,.2f}".format))
                
                

                #donut charts
                st.divider()
                st.subheader("Category Distribution")
                
                col_donut1, col_donut2 = st.columns(2)

                
                with col_donut1:
                    st.write(f"**{selected_month} Breakdown**")
                    if not month_df.empty:
                        fig1, ax1 = plt.subplots(figsize=(5, 5))
                        fig1.patch.set_facecolor('black')
                        
                        # Data for the pie
                        month_vals = month_df.groupby("Category")["Amount"].sum()
                        
                        ax1.pie(
                            month_vals, 
                            labels=month_vals.index, 
                            autopct='%1.1f%%', 
                            startangle=140, 
                            colors=plt.cm.Pastel1.colors,
                            textprops={'color':"w"}
                        )
                        
                        # Create the donut hole
                        centre_circle = plt.Circle((0,0), 0.70, fc='black')
                        fig1.gca().add_artist(centre_circle)
                        
                        plt.tight_layout()
                        st.pyplot(fig1)
                    else:
                        st.info("No data for this month.")

               
                with col_donut2:
                    st.write("**Overall Lifetime Breakdown**")
                    overall_vals = edited_df.groupby("Category")["Amount"].sum()
                    
                    fig2, ax2 = plt.subplots(figsize=(5, 5))
                    fig2.patch.set_facecolor('black')
                    
                    ax2.pie(
                        overall_vals, 
                        labels=overall_vals.index, 
                        autopct='%1.1f%%', 
                        startangle=140, 
                        colors=plt.cm.Set3.colors,
                        textprops={'color':"w"}
                    )
                    
                    # Create the donut hole
                    centre_circle2 = plt.Circle((0,0), 0.70, fc='black')
                    fig2.gca().add_artist(centre_circle2)
                    
                    plt.tight_layout()
                    st.pyplot(fig2)
                

            else:
                st.info("No data to display in chart.")              

        
st.divider()