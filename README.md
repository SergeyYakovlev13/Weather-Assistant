# This is "rough draft" of complete project.

## This is web app, where user passes question about weather in specific location on specific time, and receives answer in user-friendly format.

### This application works in the next way:
1. First of all, LLM transforms user's query into several queries like "What is the weather in 'location' on 'date'", and then parses it, and returns output as list of this queries.
2. Then, another LLM parses parameters 'location' and 'date' from each query.
3. On the next step - we use API from `https://api.open-meteo.com` to retrieve weather data for necessary location on necessary date (could be historical data, current data or future forecasts).
4. Finally, it transforms information from retrieved weather data and original user's query into user-friendly format.

### To run web application locally:
1. Write `docker-compose up --build` in the terminal of project's directory.
2. Then, to access UI - visit `http://localhost:8501`.
3. Note, that you need to specify your api_key from OpenAI in `main_agent.py` file.
