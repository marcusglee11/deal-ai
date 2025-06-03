# frontend/app.py

import streamlit as st

st.set_page_config(page_title="Deal AI MVP")

st.title("🔍 Deal AI MVP")

# Input to trigger /process-deal
folder_id = st.text_input("Google Drive Folder ID:")
if st.button("Process Deal"):
    if folder_id:
        # Call the API (hardcoded to localhost:8000 for now)
        import requests
        resp = requests.post("http://api:8000/process-deal", json={"folder_id": folder_id})
        if resp.ok:
            deal_id = resp.json().get("deal_id")
            st.success(f"Deal processed: {deal_id}")
            st.write("You can now try Chat or Report endpoints.")
        else:
            st.error(f"Error: {resp.status_code} - {resp.text}")

st.markdown("---")

# Simple chat placeholder
query = st.text_input("Chat with the deal:")
if st.button("Send Chat"):
    if query:
        resp = requests.get("http://api:8000/chat")
        if resp.ok:
            st.write(resp.json().get("reply"))
        else:
            st.error("Chat failed.")

st.markdown("---")

# Generate a placeholder report
if st.button("Generate Placeholder Report"):
    resp = requests.get("http://api:8000/report/dummy-deal")
    if resp.ok:
        st.markdown(f"**Report:** {resp.json().get('report')}")
    else:
        st.error("Report failed.")
