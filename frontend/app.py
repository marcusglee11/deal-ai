# frontend/app.py

import streamlit as st
import requests

st.set_page_config(page_title="Deal AI MVP")

st.title("🔍 Deal AI MVP")

if "deal_ids" not in st.session_state:
    st.session_state.deal_ids = []

# Input to trigger /process-deal
folder_id = st.text_input("Google Drive Folder ID:")
if st.button("Process Deal"):
    if folder_id:
        resp = requests.post("http://api:8000/process-deal", json={"folder_id": folder_id})
        if resp.ok:
            deal_id = resp.json().get("deal_id")
            st.session_state.deal_ids.append(deal_id)
            st.success(f"Deal processed: {deal_id}")
            st.write("You can now use Chat or Report with this deal ID.")
        else:
            st.error(f"Error: {resp.status_code} - {resp.text}")

st.markdown("---")

# Deal ID selection
deal_id_options = st.session_state.deal_ids
selected_deal = st.selectbox("Select processed deal", options=deal_id_options) if deal_id_options else ""
deal_id_input = st.text_input("Deal ID", value=selected_deal)
deal_id = deal_id_input or selected_deal

st.markdown("---")

# Chat with the selected deal
question = st.text_input("Chat with the deal:")
if st.button("Send Chat"):
    if question and deal_id:
        resp = requests.post(
            "http://api:8000/chat",
            json={"deal_id": deal_id, "question": question},
        )
        if resp.ok:
            data = resp.json()
            st.write(data.get("answer"))
            sources = data.get("sources", [])
            if sources:
                st.markdown("**Sources:**")
                for src in sources:
                    st.write(f"- {src}")
        else:
            st.error("Chat failed.")

st.markdown("---")

# Fetch Markdown report for the selected deal
if st.button("Get Report"):
    if deal_id:
        resp = requests.get(f"http://api:8000/report/{deal_id}")
        if resp.ok:
            if "application/json" in resp.headers.get("content-type", ""):
                report_md = resp.json().get("report", "")
            else:
                report_md = resp.text
            st.markdown(report_md)
        else:
            st.error("Report failed.")
