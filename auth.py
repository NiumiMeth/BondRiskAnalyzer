from __future__ import annotations

import hashlib
import streamlit as st


def _check_credentials(username: str, password: str) -> tuple[bool, str | None]:
    creds = st.secrets.get("credentials", {})
    user_entry = creds.get(username)
    if not user_entry:
        return False, None
    stored_hash = user_entry.get("password_hash")
    role = user_entry.get("role")
    if not stored_hash:
        return False, None
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    return (pw_hash == stored_hash, role)


def login_widget() -> tuple[str | None, str | None]:
    if "auth_user" in st.session_state and st.session_state.get("auth_user"):
        return st.session_state.get("auth_user"), st.session_state.get("auth_role")

    st.write("#### Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            ok, role = _check_credentials(username, password)
            if ok:
                st.session_state["auth_user"] = username
                st.session_state["auth_role"] = role
                # Return the authenticated user immediately instead of forcing a rerun
                return username, role
            else:
                st.error("Invalid username or password")

    return None, None


def require_role(allowed_roles: list[str]) -> tuple[str, str]:
    user = st.session_state.get("auth_user")
    role = st.session_state.get("auth_role")
    if not user:
        user, role = login_widget()
    if not user:
        st.stop()

    if role not in allowed_roles:
        st.error("Access denied: insufficient privileges for this page.")
        if st.button("Logout"):
            logout()
        st.stop()

    # show logout option
    if st.button("Logout"):
        logout()

    return user, role


def logout() -> None:
    for k in ["auth_user", "auth_role"]:
        if k in st.session_state:
            del st.session_state[k]
    # Try to rerun the app to refresh UI; if not available, ask the user to refresh
    try:
        if hasattr(st, "experimental_rerun"):
            st.experimental_rerun()
        else:
            st.success("Logged out — please refresh the page.")
            st.stop()
    except Exception:
        st.success("Logged out — please refresh the page.")
        st.stop()
