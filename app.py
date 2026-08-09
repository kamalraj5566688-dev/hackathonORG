import streamlit as st
import requests
import uuid
import pandas as pd

# --- Configuration ---
API_URL = "http://127.0.0.1:8000/api"

st.set_page_config(page_title="Secure AI Interviewer", page_icon="🤖", layout="wide")

# --- Session State Initialization ---
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.session_state.interview_active = False
    st.session_state.feedback = None
if "access_token" not in st.session_state:
    st.session_state.access_token = None

def reset_interview():
    """Reset session state to start a fresh interview."""
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.session_state.interview_active = False
    st.session_state.feedback = None

# ============================================================
# AUTHENTICATION SCREENS
# ============================================================
if not st.session_state.access_token:
    st.title("🔒 Enterprise AI Interviewer - Secure Access")
    st.markdown("Please log in or register to access the secure interview environment.")
    
    auth_tab1, auth_tab2 = st.tabs(["Log In", "Register"])
    
    with auth_tab1:
        st.subheader("Existing Users")
        login_email = st.text_input("Email", key="login_email")
        login_pass = st.text_input("Password", type="password", key="login_pass")
        
        if st.button("Log In"):
            with st.spinner("Authenticating..."):
                try:
                    res = requests.post(f"{API_URL}/login", json={"email": login_email, "password": login_pass})
                    if res.status_code == 200:
                        st.session_state.access_token = res.json().get("access_token")
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error(f"Authentication failed: {res.json().get('detail')}")
                except Exception as e:
                    st.error("Could not connect to the backend server.")
                    
    with auth_tab2:
        st.subheader("New Users")
        reg_email = st.text_input("Email", key="reg_email")
        reg_pass = st.text_input("Password", type="password", key="reg_pass")
        
        if st.button("Register"):
            with st.spinner("Creating secure account..."):
                try:
                    res = requests.post(f"{API_URL}/register", json={"email": reg_email, "password": reg_pass})
                    if res.status_code == 200:
                        st.success("Registration successful! You may now log in.")
                    else:
                        st.error(f"Registration failed: {res.json().get('detail')}")
                except Exception as e:
                    st.error("Could not connect to the backend server.")
                    
    st.stop() # Halt rendering the rest of the application until authenticated


# ============================================================
# MAIN APPLICATION
# ============================================================

# --- Sidebar Controls ---
with st.sidebar:
    st.header("👤 User Settings")
    if st.button("🚪 Logout"):
        st.session_state.access_token = None
        reset_interview()
        st.rerun()
        
    st.divider()
    
    if st.session_state.interview_active or st.session_state.feedback:
        st.header("⚙️ Session Controls")
        if st.button("🔄 Start New Interview"):
            reset_interview()
            st.rerun()

st.title("🤖 Dynamic AI Interviewer")
st.markdown("---")

# --- Tabbed Navigation ---
main_tab1, main_tab2 = st.tabs(["🎯 Interview Portal", "📊 Analytics & System Health Dashboard"])

# ============================================================
# TAB 1: INTERVIEW PORTAL
# ============================================================
with main_tab1:
    # --- Landing Page / Domain Setup ---
    if not st.session_state.interview_active and st.session_state.feedback is None:
        st.write("### Welcome! Customize your interview parameters below.")
        
        domains = {
            "IT / Software Engineering": ["System Design", "Cloud Computing", "Databases", "API Development"],
            "Human Resources (HR)": ["Talent Acquisition", "Employee Relations", "Performance Management", "Conflict Resolution"],
            "Management": ["Agile/Scrum", "Project Roadmap", "Risk Management", "Stakeholder Communication"],
            "Marketing": ["Digital Marketing", "SEO/SEM", "Brand Strategy", "Campaign Analysis"],
            "Data Science": ["Machine Learning", "Data Visualization", "Statistical Analysis", "Python/SQL"]
        }
        
        selected_domain = st.selectbox("Select your interview field:", list(domains.keys()))
        
        ghost_mode = st.toggle(
            "🔒 Enable Ghost Mode (Zero-Logging Private Session)", 
            value=False,
            help="When enabled, your session runs entirely in volatile memory without saving persistent logs to the database."
        )
        
        candidate_payload = {
            "id": "CAND-001",
            "name": "Candidate",
            "jobRole": selected_domain,
            "member": {
                "id": "CAND-001",
                "name": "Candidate",
                "jobRole": selected_domain,
                "yearsExperience": 3
            },
            "completedMissions": domains[selected_domain],
            "skippedMissions": []
        }

        if ghost_mode:
            st.warning("🔒 **Ghost Mode Active**: Session data will not be persisted to the database.")
        else:
            st.info(f"The AI will generate dynamic questions tailored for a **{selected_domain}** role.")
        
        if st.button("Start Interview"):
            with st.spinner(f"Establishing secure connection and preparing {selected_domain} questions..."):
                headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
                response = requests.post(
                    f"{API_URL}/interview",
                    headers=headers,
                    json={
                        "sessionId": st.session_state.session_id, 
                        "candidate": candidate_payload,
                        "ghostMode": ghost_mode
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.messages.append({"role": "assistant", "content": data["reply"]})
                    st.session_state.interview_active = True
                    st.rerun()
                else:
                    st.error(f"Failed to start interview: {response.text}")

    # --- Chat Interface ---
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # --- Chat Input ---
    if st.session_state.interview_active:
        if user_input := st.chat_input("Type your answer here..."):
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            with st.spinner("Analyzing answer..."):
                headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
                response = requests.post(
                    f"{API_URL}/interview",
                    headers=headers,
                    json={
                        "sessionId": st.session_state.session_id, 
                        "message": user_input
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.messages.append({"role": "assistant", "content": data["reply"]})
                    
                    if data.get("done"):
                        st.session_state.interview_active = False
                        st.session_state.feedback = data.get("feedback")
                    
                    st.rerun()
                else:
                    st.error(f"Error communicating with backend: {response.text}")

    # --- Final Feedback Display ---
    if st.session_state.feedback:
        st.success("✅ Interview Completed!")
        st.subheader("Candidate Evaluation Report")
        
        feedback = st.session_state.feedback
        st.write(f"**Summary:** {feedback.get('summary', 'No summary provided.')}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("### Strengths")
            for strength in feedback.get('strengths', []):
                st.write(f"- {strength}")
                
        with col2:
            st.write("### Areas for Improvement")
            for gap in feedback.get('gaps', feedback.get('areas_for_improvement', [])):
                st.write(f"- {gap}")
                
        st.write("### Recommended Next Steps")
        for next_step in feedback.get('next', feedback.get('recommended_review_days', [])):
            st.write(f"- {next_step}")


# ============================================================
# TAB 2: ANALYTICS DASHBOARD
# ============================================================
with main_tab2:
    st.subheader("System Health & Aggregate Insights")
    st.markdown("Visualizing anonymized metrics and privacy statistics.")
    
    # Top-level metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Active Sessions", "14", "+2")
    m2.metric("Ghost Mode Usage", "68%", "+15%")
    m3.metric("Blocked Credential Stuffs", "241", "-5")
    m4.metric("Avg. Interview Score", "7.4/10", "0.0")
    
    st.divider()
    
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.write("**Interviews Conducted by Domain**")
        domain_data = pd.DataFrame({
            'Domain': ['IT / Software', 'HR', 'Management', 'Marketing', 'Data Science'],
            'Count': [120, 45, 85, 60, 95]
        }).set_index('Domain')
        st.bar_chart(domain_data, color="#4A90E2")

    with col_chart2:
        st.write("**System Load (Threat & Request Traffic)**")
        traffic_data = pd.DataFrame({
            'Legitimate Requests': [500, 600, 550, 700, 850, 900, 750],
            'Blocked Threats (Rate Limit)': [20, 25, 10, 40, 55, 30, 15]
        }, index=['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'])
        st.line_chart(traffic_data, color=["#2ECC71", "#E74C3C"])