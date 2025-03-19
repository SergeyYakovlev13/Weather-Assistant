import streamlit as st
from main_agent import process_weather_query

st.title("Weather Assistant App")
st.write("Enter your query:")

# Input field for the user query.
user_query = st.text_input("Your weather query")

if user_query:
    response = process_weather_query(user_query)
    st.subheader("Weather Summary:")
    st.write(response)