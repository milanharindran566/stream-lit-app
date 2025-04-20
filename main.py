import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.express as px
import os

st.set_page_config(page_title="Simple Finance App", page_icon="💰", layout="wide")
category_file = "categories.json"

if "categories" not in st.session_state:
    st.session_state.categories = {
        "Uncategorized": [],
    }
    
if os.path.exists(category_file):
    with open(category_file,"r") as f:
        st.session_state.categories = json.load(f)
            
def save_categories():
    with open(category_file,"w") as f:
        json.dump(st.session_state.categories, f)
        
def clean_data(df):
    df['Date'] = pd.to_datetime(df['Date'], format='mixed')
    df['Date'] = df['Date'].dt.strftime('%d/%m/%Y')
    df['Amount'] = df['Amount'].str.replace(',', '', regex=False).astype(float)  # keep as float
    df['Status'] = df['Status'].fillna('SETTLED')
    df['Debit/Credit'] = df['Debit/Credit'].apply(lambda x: x if x in ['Credit', 'Debit'] else 'Credit')
    return df

def categorize_transactions(df):
    df["Category"] = "Uncategorized"
    
    for category, keywords in st.session_state.categories.items():
        if category == "Uncategorized" or not keywords:
            continue
        lower_keywords = [keyword.lower().strip() for keyword in keywords]
        
        for idx, row in df.iterrows(): #iterate over all rows in data frame
            details = row["Details"].lower().strip()
            if details in lower_keywords:
                df.at[idx, "Category"] = category
    return df
            
def load_transactions(file):
    try:
        transactions = pd.read_csv(file)
        transactions.columns = [col.strip() for col in transactions.columns]
        df = clean_data(transactions)
        return categorize_transactions(df)
    except(Exception) as e:
        st.error(f"Error processing csv file: {str(e)}")
        return None

def add_keyword_to_category(category, keyword):
    keyword = keyword.strip()
    if keyword and keyword not in st.session_state.categories[category]:
        st.session_state.categories[category].append(keyword)
        save_categories()
        return True
    return False

#TODO: clear category text box after successfully adding category
        
def main():
    st.title("Simple Finance Dashboard")
    uploaded_file = st.file_uploader("Upload your transaction CSV file", type=["csv"])
    if (uploaded_file is not None):
        df = load_transactions(uploaded_file)
        
        if (df is not None):
            debit_df = df[df['Debit/Credit'] == 'Debit'].copy()
            credit_df = df[df['Debit/Credit'] == 'Credit'].copy()
            
            st.session_state.debits_df = debit_df.copy()
            st.session_state.credits_df = credit_df.copy()
            
            tab1, tab2 = st.tabs(["Expenses(Debits)","Payments(Credits)"])
            with tab1:
                new_category = st.text_input("New Category Name", key="category")
                add_button = st.button("Add Category")
                
                if add_button and new_category:
                    if new_category not in st.session_state.categories:
                        st.session_state.categories[new_category] = []
                        save_categories()
                        st.rerun()
                        
                st.subheader("Your Expenses")
                edited_df = st.data_editor(
                    st.session_state.debits_df[["Date", "Details", "Amount", "Category"]],
                    column_config={
                        "Amount": st.column_config.NumberColumn("Amount", format="%.2f INR"),
                        "Category": st.column_config.SelectboxColumn(
                            "Category",
                            options=list(st.session_state.categories.keys())
                        ),
                    },
                    hide_index=True,
                    use_container_width=True,
                    key="container_editor")
               
                save_button = st.button("Apply Changes", type="primary")
                if save_button:
                    for idx,rows in edited_df.iterrows():
                        new_category = rows["Category"]
                        if new_category == st.session_state.debits_df.at[idx, "Category"]:
                            continue
                        details = rows["Details"]
                        st.session_state.debits_df.at[idx,"Category"] = new_category
                        add_keyword_to_category(new_category, details)
                
                st.subheader("Expense Summary")
                category_totals = st.session_state.debits_df.groupby("Category")["Amount"].sum().reset_index()
                category_totals = category_totals.sort_values("Amount", ascending=False)
                
                st.dataframe(category_totals, 
                            column_config = {
                                 "Amount": st.column_config.NumberColumn("Amount", format="%.2f INR"),
                            },
                            hide_index=True,
                            use_container_width=True)
                fig = px.pie(
                    category_totals,
                    values="Amount",
                    names="Category",
                    title="Expenses by Category"
                )
                st.plotly_chart(fig,use_container_width=True)
                
            with tab2:
                st.subheader("Payments Summary")
                total_payments = credit_df["Amount"].sum()
                st.metric("Total Payments", f"{total_payments:,.2f} INR")
                st.write(credit_df)

main()