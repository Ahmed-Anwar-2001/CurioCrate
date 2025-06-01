import csv
import io
import re
from urllib.parse import urlparse
from django.shortcuts import render, redirect
from django.contrib import messages
from CurioAgent.forms import CSVUploadForm
from creds.models import TrustpilotCompanyLink, TrustpilotBusinessData
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json
import os
from groq import Groq
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.messages import AIMessage, HumanMessage
from django.db.models import Q
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import Tool
from pydantic import BaseModel, Field
from django.db import models 
from django.shortcuts import render, redirect
from django.urls import reverse

from django.shortcuts import render, redirect
from django.urls import reverse

def home(request):

    if request.user.is_authenticated:
        is_verified = getattr(request.user, 'is_verified', False)

        if not is_verified:
            return redirect(reverse('creds:verify-email'))
        else:
            context = {
                'user': request.user,
                'is_authenticated': True,
                'is_verified': True
            }
            return render(request, "chat_interface/home.html", context)
    else:
        context = {
            'user': request.user,
            'is_authenticated': False,
            'is_verified': False
        }
        return render(request, "chat_interface/home.html", context)

# --- Helper functions to extract the linking key ---
def get_key_from_review_link(url):
    if not url: return None
    match = re.search(r'review/(.*)', url)
    return match.group(1).lower() if match else None

def get_key_from_website(url):
    if not url: return None
    try:
        hostname = urlparse(url).hostname
        if hostname:
            return hostname.replace('www.', '').lower()
    except Exception:
        return None
    return None

# --- The View ---
def upload_csv_view(request):
    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            model_type = form.cleaned_data['model_type']
            csv_file = form.cleaned_data['csv_file']
            
            # Use io.TextIOWrapper to decode the in-memory file
            decoded_file = io.TextIOWrapper(csv_file.file, encoding='utf-8')
            reader = csv.DictReader(decoded_file)
            
            objects_to_create = []
            
            try:
                if model_type == 'links':
                    for row in reader:
                        key = get_key_from_review_link(row.get('Link'))
                        if key:
                            objects_to_create.append(
                                TrustpilotCompanyLink(
                                    link=row['Link'],
                                    company_key=key,
                                    category=row.get('Category'),
                                    subcategory=row.get('Subcategory')
                                )
                            )
                    TrustpilotCompanyLink.objects.bulk_create(objects_to_create, ignore_conflicts=True)

                elif model_type == 'business':
                    for row in reader:
                        key = get_key_from_website(row.get('Website'))
                        if key:
                            objects_to_create.append(
                                TrustpilotBusinessData(
                                    company_key=key,
                                    name=row.get('Name'),
                                    email=row.get('Email'),
                                    company=row.get('Company'),
                                    location=row.get('Location'),
                                    phone=row.get('Phone'),
                                    website=row.get('Website'),
                                    category=row.get('Category'),
                                    subcategory=row.get('Subcategory'),
                                    review_count=row.get('Review_Count', '').replace(',', ''),
                                    ratings=float(row['Ratings']) if row.get('Ratings') else None
                                )
                            )
                    TrustpilotBusinessData.objects.bulk_create(objects_to_create, ignore_conflicts=True)
                
                messages.success(request, f"Successfully imported {len(objects_to_create)} records.")
                return redirect('creds:upload_csv')

            except KeyError as e:
                messages.error(request, f"CSV file is missing a required column: {e}")
            except Exception as e:
                messages.error(request, f"An error occurred during processing: {e}")

    else:
        form = CSVUploadForm()

    return render(request, 'chat_interface/upload_csv.html', {'form': form})







# --- Groq API Setup ---
groq_api_key = os.environ.get("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("GROQ_API_KEY environment variable not set.")

llm = ChatGroq(
    model="llama3-70b-8192", # Recommended to use the latest powerful models
    temperature=0,
    api_key=groq_api_key
)

# --- Tool Functions ---

def get_business_data_by_key(company_key: str):
    # ... (your existing function code)
    try:
        business_data = TrustpilotBusinessData.objects.get(company_key__iexact=company_key)
        return {
            "name": business_data.name, "email": business_data.email, "company": business_data.company,
            "location": business_data.location, "phone": business_data.phone, "website": business_data.website,
            "category": business_data.category, "subcategory": business_data.subcategory,
            "review_count": business_data.review_count,
            "ratings": float(business_data.ratings) if business_data.ratings else None,
        }
    except TrustpilotBusinessData.DoesNotExist:
        return {"error": f"No business data found for company key: {company_key}"}


def search_companies_by_name(query: str, limit: int = 5):
    results = TrustpilotBusinessData.objects.filter(name__icontains=query).values('company_key', 'name', 'website')
    return list(results[:limit]) if results else []

def search_business_by_category(category: str, subcategory: str = None, limit: int = 5):
    filters = models.Q(category__icontains=category)
    if subcategory:
        filters &= models.Q(subcategory__icontains=subcategory)
    results = TrustpilotBusinessData.objects.filter(filters).values('company_key', 'name', 'website', 'category', 'subcategory')
    return list(results[:limit]) if results else []

def search_business_by_location(location_query: str, limit: int = 5):
    results = TrustpilotBusinessData.objects.filter(location__icontains=location_query).values('company_key', 'name', 'location', 'website')
    return list(results[:limit]) if results else []

# --- Step 1: Define Pydantic Models for Tool Inputs (Best Practice) ---
class BusinessDataInput(BaseModel):
    company_key: str = Field(description="The unique key for a company, e.g., 'tesla', 'microsoft.com'.")

class SearchNameInput(BaseModel):
    query: str = Field(description="The name or keyword of the company to search for.")

class SearchCategoryInput(BaseModel):
    category: str = Field(description="The primary business category, e.g., 'Cars', 'Electronics'.")
    subcategory: str | None = Field(default=None, description="Optional specific subcategory, e.g., 'Electric Cars'.")

class SearchLocationInput(BaseModel):
    location_query: str = Field(description="The geographical location to search for, e.g., 'New York', 'Germany'.")

# --- Step 2: Create LangChain Tools with Clean Descriptions ---
# We wrap the functions in LangChain's Tool class.
tools = [
    Tool(
        name="get_business_data_by_key",
        func=get_business_data_by_key,
        description="Fetches detailed business information (contact, ratings, etc.) for a single company using its exact company key.",
        args_schema=BusinessDataInput,
    ),
    Tool(
        name="search_companies_by_name",
        func=search_companies_by_name,
        description="Searches for companies by their name. Returns a list of potential matches with their company key and website.",
        args_schema=SearchNameInput,
    ),
    Tool(
        name="search_business_by_category",
        func=search_business_by_category,
        description="Finds multiple companies within a specific business category and optional subcategory.",
        args_schema=SearchCategoryInput,
    ),
    Tool(
        name="search_business_by_location",
        func=search_business_by_location,
        description="Finds multiple companies based on a geographical location.",
        args_schema=SearchLocationInput,
    ),
]

# --- Step 3: Create the Agent Prompt ---
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are CurioCrate, a helpful AI assistant specializing in finding business information from a database. Your goal is to answer the user's questions by using the available tools. Present results clearly. If a search yields multiple results, list them and ask the user for clarification if needed."),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
)

# --- Step 4: Create the Agent and AgentExecutor ---
agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True) # Set verbose=False in production


@csrf_exempt
def chat_api_view(request):
    if request.method != 'POST':
        return JsonResponse({"error": "Invalid request method"}, status=405)

    try:
        data = json.loads(request.body)
        user_message = data.get('message')
        # LangChain needs chat history in a specific format.
        raw_chat_history = data.get('chat_history', [])
        
        if not user_message:
            return JsonResponse({"error": "No message provided"}, status=400)

        # Convert chat history from simple dicts to LangChain's message objects
        chat_history = []
        for msg in raw_chat_history:
            if msg.get('role') == 'user':
                chat_history.append(HumanMessage(content=msg.get('content')))
            elif msg.get('role') == 'assistant':
                chat_history.append(AIMessage(content=msg.get('content')))

        # Invoke the agent executor
        response = agent_executor.invoke({
            "input": user_message,
            "chat_history": chat_history,
        })

        return JsonResponse({"botResponse": response["output"]})

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return JsonResponse({"error": "An internal error occurred. Please try again later."}, status=500)