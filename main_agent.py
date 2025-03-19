import os
import warnings
from datetime import datetime, date
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser, PydanticOutputParser
from langchain.chains import LLMChain, SequentialChain
from langchain.prompts import PromptTemplate, HumanMessagePromptTemplate, ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import List
from weather_api import WeatherAPI

warnings.filterwarnings('always')

os.environ['OPENAI_API_KEY'] = 'API-KEY'

class SubQuery(BaseModel):
    query: str = Field(..., description = "Question like 'What is the weather in location on date?'," +\
                                          "where location is city or country where to check the weather," +\
                                          "and date - is date in format YYYY-MM-DD when to check the weather.")

class SubQueries(BaseModel):
    queries: List[SubQuery]

class Data(BaseModel):
    location: str = Field(..., description="Place name (country or city) for checking the weather")
    date: str = Field(..., description="Date, when to check the weather in specified place, in YYYY-MM-DD format")

def parse_subquestions(user_input):
    chat_model = ChatOpenAI(
        model ="gpt-4", 
        temperature=0.01, 
        max_tokens=4000
    )

    now = datetime.now()
    formatted_date = now.strftime("%Y-%m-%d")

    day_name = date.today().strftime("%A")

    input_values = {
    "query": user_input,
    "current_date": formatted_date,
    "day_name": day_name
    }

    subqueries_parser = PydanticOutputParser(pydantic_object = SubQueries)

    transform_prompt = PromptTemplate(
        template = ("Rephrase following query in a way, that it consit of several questions"
                    "in format 'What is the weather in location on date?',"
                    "where location is city or country where to check the weather,"
                    "and date - is date in format YYYY-MM-DD when to check the weather."
                    "Query: {query}\n"
                    "Consider, that today is {current_date}, and that day of the week is {day_name}."),
        input_variables = ["query", "current_date", 'day_name'],
    )

    human_message_transform = HumanMessagePromptTemplate(prompt = transform_prompt)

    chat_prompt_transform = ChatPromptTemplate.from_messages([
                                                   ("system", "You are language assistant, whose task is to transform specified user's query about weather " +\
                                                              "into several questions in the given format, if necessary, or one question in the given format."),
                                                   human_message_transform]
    )

    transform_chain = LLMChain(llm = chat_model, prompt = chat_prompt_transform, output_key = "transformed_query")

    subqueries_prompt = PromptTemplate(
        template = ("Retrieve subqueries from the given query for further usage.\n"
                    "{format_instructions}\n"
                    "Query: {transformed_query}\n"),
        input_variables = ["transformed_query"],
        partial_variables = {"format_instructions": subqueries_parser.get_format_instructions()}
    )

    human_message_subqueries = HumanMessagePromptTemplate(prompt = subqueries_prompt)

    chat_prompt_subqueries = ChatPromptTemplate.from_messages([
                                                   ("system", "You are language parser, whose task is to separate given query, which consist of several questions about weather into list of unique corresponding questions."),
                                                   human_message_subqueries]
    )

    subqueries_chain = LLMChain(llm = chat_model, prompt = chat_prompt_subqueries, output_parser = subqueries_parser, output_key = "subqueries")

    combined_chain = SequentialChain(
    chains = [transform_chain, subqueries_chain],
    input_variables = ["query", "current_date", 'day_name'],
    output_variables = ["transformed_query", "subqueries"],
    verbose=True)

    return combined_chain.invoke(input_values)['subqueries']

def parse_parameters(question):
    chat_model = ChatOpenAI(
        model ="gpt-4", 
        temperature=0.01, 
        max_tokens=4000
    )
    
    now = datetime.now()
    formatted_date = now.strftime("%Y-%m-%d")

    day_name = date.today().strftime("%A")

    input_values = {
    "query": question,
    "current_date": formatted_date,
    "day_name": day_name
    }

    parameters_parser = JsonOutputParser(pydantic_object = Data)

    parameters_prompt = PromptTemplate(
        template = ("Retrieve parameters from the question for fetching weather data.\n"
                    "{format_instructions}\n"
                    "Query: {query}\n"
                    "Also remember, that today date is {current_date}, and that current day of the week is {day_name}."),
        input_variables = ["query"],
        partial_variables = {"format_instructions": parameters_parser.get_format_instructions()}
    )

    human_message_parameters = HumanMessagePromptTemplate(prompt = parameters_prompt)

    chat_prompt_parameters = ChatPromptTemplate.from_messages([
                                                   ("system", "You are an accurate parameter parser, " +\
                                                              "who parses values of necessary parameters from a given query."),
                                                   human_message_parameters]
    )
    
    parameters_chain = LLMChain(llm = chat_model, prompt = chat_prompt_parameters, output_parser = parameters_parser)
    result = parameters_chain.invoke(input_values)
    return result['text']

def process_weather_query(user_query):
    chat_model = ChatOpenAI(
        model ="gpt-4-turbo", 
        temperature=0.01, 
        max_tokens=1000
    )

    now = datetime.now()
    formatted_date = now.strftime("%Y-%m-%d")

    day_name = date.today().strftime("%A")

    # Parse the user input to extract parameters
    weather_data = ""
    subqueries = parse_subquestions(user_query).queries

    for query in subqueries:
        parse_parameters(query.query)
        params = parse_parameters(query.query)
        location = params['location']
        date_str = params['date']

        current_date = datetime.strptime(formatted_date, "%Y-%m-%d")
        retrieved_date = datetime.strptime(date_str, "%Y-%m-%d")
        fields = ['hourly_units', 'hourly']
        if retrieved_date < current_date:
            historical_weather_data = WeatherAPI.get_historical_weather(location, date_str)
            historical_weather_data = {key: historical_weather_data[key] for key in fields if key in historical_weather_data}
            weather_data += f"Weather in {location} for {date_str}:\n{historical_weather_data}\n"
        elif retrieved_date == current_date:
            current_weather_data = WeatherAPI.get_current_weather(location)
            current_weather_data = {key: current_weather_data[key] for key in fields if key in current_weather_data}
            weather_data += f"Weather in {location} for today:\n{current_weather_data}\n"
        else:
            future_weather_data = WeatherAPI.get_forecast(location, date_str)
            future_weather_data = {key: future_weather_data[key] for key in fields if key in future_weather_data}
            weather_data += f"Weather forecast in {location} for {date_str}:\n{future_weather_data}\n"
    print(weather_data)
    user_prompt = PromptTemplate(
        template = ("Provide a concise and friendly summary including only the important information due to user's query and retrieved weather data.\n"
                    "Query: {query}\n"
                    "Weather data: {weather_data}\n"
                    "Also remember, that today date is {current_date}, and that current day of the week is {day_name}."),
        input_variables = ["query", 'current_date', 'day_name']
    )

    human_message_parameters = HumanMessagePromptTemplate(prompt = user_prompt)

    chat_prompt_rephrase = ChatPromptTemplate.from_messages([
                                                   ("system", "You are a weather assistant, " +\
                                                              "who summarizes the following weather data in a user-friendly format."),
                                                   human_message_parameters]
    )

    input_values = {
    "query": user_query,
    "weather_data": weather_data,
    "current_date": formatted_date,
    "day_name": day_name
    }

    rephrase_chain = LLMChain(llm = chat_model, prompt = chat_prompt_rephrase)
    result = rephrase_chain.invoke(input_values)
    return result['text']