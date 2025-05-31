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

def home(request):
    return render(request, "chat_interface/home.html")

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
groq_client = Groq(api_key=groq_api_key)

# --- Existing & New Tools for Agentic System (no change needed here, they are well-defined) ---

def get_company_link_by_key(company_key: str):
    try:
        company_link = TrustpilotCompanyLink.objects.get(company_key__iexact=company_key)
        return {
            "link": company_link.link,
            "category": company_link.category,
            "subcategory": company_link.subcategory
        }
    except TrustpilotCompanyLink.DoesNotExist:
        return None

def get_business_data_by_key(company_key: str):
    try:
        business_data = TrustpilotBusinessData.objects.get(company_key__iexact=company_key)
        return {
            "name": business_data.name,
            "email": business_data.email,
            "company": business_data.company,
            "location": business_data.location,
            "phone": business_data.phone,
            "website": business_data.website,
            "category": business_data.category,
            "subcategory": business_data.subcategory,
            "review_count": business_data.review_count,
            "ratings": float(business_data.ratings) if business_data.ratings else None,
        }
    except TrustpilotBusinessData.DoesNotExist:
        return None

def search_companies_by_name(query: str, limit: int = 5):
    results = TrustpilotBusinessData.objects.filter(
        name__icontains=query
    ).values('company_key', 'name', 'website')
    return list(results[:limit]) if results else []

def search_links_by_category(category: str, subcategory: str = None, limit: int = 5):
    filters = models.Q(category__icontains=category)
    if subcategory:
        filters &= models.Q(subcategory__icontains=subcategory)
    
    results = TrustpilotCompanyLink.objects.filter(
        filters
    ).values('company_key', 'link', 'category', 'subcategory')
    return list(results[:limit]) if results else []

def search_business_by_category(category: str, subcategory: str = None, limit: int = 5):
    filters = models.Q(category__icontains=category)
    if subcategory:
        filters &= models.Q(subcategory__icontains=subcategory)
    
    results = TrustpilotBusinessData.objects.filter(
        filters
    ).values('company_key', 'name', 'email', 'website', 'category', 'subcategory')
    return list(results[:limit]) if results else []

def search_business_by_location(location_query: str, limit: int = 5):
    results = TrustpilotBusinessData.objects.filter(
        location__icontains=location_query
    ).values('company_key', 'name', 'location', 'website')
    return list(results[:limit]) if results else []

# Dictionary to map tool names to their functions
available_tools = {
    "get_company_link_by_key": get_company_link_by_key,
    "get_business_data_by_key": get_business_data_by_key,
    "search_companies_by_name": search_companies_by_name,
    "search_links_by_category": search_links_by_category,
    "search_business_by_category": search_business_by_category,
    "search_business_by_location": search_business_by_location,
}

# Define the tools for Groq's function calling (Descriptions updated for clarity)
groq_tools = [
    {
        "type": "function",
        "function": {
            "name": "get_company_link_by_key",
            "description": "Fetches the Trustpilot review link, category, and subcategory for a company given its exact company key. The company key is typically derived from the company's website domain (e.g., 'microsoft.com' -> 'microsoft') or directly from a Trustpilot review URL (e.g., 'trustpilot.com/review/example.com' -> 'example.com'). Use this when the user asks for a specific company's Trustpilot link and you have its exact company key.",
            "parameters": {
                "type": "object",
                "properties": {
                    "company_key": {
                        "type": "string",
                        "description": "The unique key identifying the company on Trustpilot (e.g., 'microsoft', 'chewy').",
                    },
                },
                "required": ["company_key"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_business_data_by_key",
            "description": "Retrieves detailed business information from Trustpilot based on a company's exact company key, including name, email, location, phone, website, review count, and ratings. Use this when the user asks for specific details (like contact info, ratings, full company profile) about a known company or a company identified by a previous search.",
            "parameters": {
                "type": "object",
                "properties": {
                    "company_key": {
                        "type": "string",
                        "description": "The unique key identifying the company on Trustpilot (e.g., 'microsoft', 'chewy').",
                    },
                },
                "required": ["company_key"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_companies_by_name",
            "description": "Searches for companies in TrustpilotBusinessData by a general company name or keyword (partial, case-insensitive match). This tool is useful for broad queries like 'companies named Tesla' or 'find companies selling pet food'. It returns a list of potential matches, including their company_key, name, and website. If the user then asks for more details about one of these, use 'get_business_data_by_key' with the specific company_key.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The partial or full name of the company to search for.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default is 5).",
                        "default": 5
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_links_by_category",
            "description": "Finds Trustpilot company links based on a category and optionally a subcategory (partial, case-insensitive match). This is useful for finding companies within a specific industry. Returns company_keys, links, categories, and subcategories. If the user then asks for more details about one of these, use 'get_business_data_by_key' with the specific company_key.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "The primary category (e.g., 'Electronics', 'Finance', 'Pets').",
                    },
                    "subcategory": {
                        "type": "string",
                        "description": "An optional more specific subcategory (e.g., 'Online Pet Stores').",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default is 5).",
                        "default": 5
                    }
                },
                "required": ["category"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_business_by_category",
            "description": "Retrieves detailed business data for companies based on a category and optionally a subcategory (partial, case-insensitive match). Useful for getting contact info, website, and ratings for companies in a specific industry. Returns company_keys, names, emails, and websites. If the user then asks for more details about one of these, use 'get_business_data_by_key' with the specific company_key.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "The primary category (e.g., 'Electronics', 'Finance', 'Pets').",
                    },
                    "subcategory": {
                        "type": "string",
                        "description": "An optional more specific subcategory (e.g., 'Online Pet Stores').",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default is 5).",
                        "default": 5
                    }
                },
                "required": ["category"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_business_by_location",
            "description": "Searches for companies based on a geographical location query (partial, case-insensitive match). Returns company_keys, names, locations, and websites. If the user then asks for more details about one of these, use 'get_business_data_by_key' with the specific company_key.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location_query": {
                        "type": "string",
                        "description": "The location to search for (e.g., 'London', 'New York', 'Germany').",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default is 5).",
                        "default": 5
                    }
                },
                "required": ["location_query"],
            },
        },
    },
]


@csrf_exempt
def chat_api_view(request):
    """
    API endpoint for handling chat messages and interacting with the Groq API.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message')

            if not user_message:
                return JsonResponse({"error": "No message provided"}, status=400)

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are Alfred, an advanced AI assistant specialized in finding lead and service information "
                        "from Trustpilot data. You have access to a suite of tools to query companies by their "
                        "exact 'company key', or by name, category, subcategory, or location using flexible search. "
                        "Your primary goal is to retrieve the most relevant information based on the user's query and present it clearly.\n\n"
                        "**Tool Usage Guidelines & Response Strategy:**\n"
                        "1.  **Prioritize:** If the user provides a specific company name or a clear company key, use `get_company_link_by_key` or `get_business_data_by_key` directly.\n"
                        "2.  **General Search:** For broad queries (e.g., 'companies in category X', 'find companies named Y', 'companies in Z location'), use the appropriate `search_` tool (e.g., `search_business_by_category`, `search_companies_by_name`, `search_business_by_location`).\n"
                        "3.  **Presenting Search Results:** If a `search_` tool returns a list of results, **present these results directly to the user in a clear, readable format (e.g., a numbered list of names and their primary identifier like website or link).** State how many results were found.\n"
                        "    * **Crucial:** Do NOT re-prompt the user with the same question if results are already obtained. Instead, ask if they'd like more details on a *specific* company from the list, or to refine the search.\n"
                        "    * *Example Response for Search:* 'I found X companies matching your query:\n1. Company A (Website: companyA.com)\n2. Company B (Link: trustpilot.com/review/companyB.com)\nWould you like more details on any of these, or perhaps a different search?'\n"
                        "4.  **Providing Details (get_business_data_by_key):** When `get_business_data_by_key` is used, extract and present the **most relevant information** (Name, Website, Category, Subcategory, Email, Phone, Location, Ratings, Review Count) clearly and concisely. If some data points are missing, just omit them gracefully. \n"
                        "    * *Example Response for Details:* 'Here are the details for [Company Name]:\nWebsite: [website]\nCategory: [category]\nEmail: [email]\nPhone: [phone]\nLocation: [location]\nTrustpilot Rating: [ratings] based on [review_count] reviews.'\n"
                        "5.  **No Results:** If a tool returns no results, politely inform the user that no information was found for their query and suggest refining the search or providing more details.\n"
                        "6.  **Comprehensive Answers:** Always provide detailed and helpful answers based on the *actual data* retrieved by the tools. Mention 'According to Trustpilot data...' or similar phrasing.\n"
                        "7.  **Maintain Context:** Remember previous turns in the conversation. If a user asks for 'details on the first one' after a search, infer which company they mean.\n"
                        "8.  **Error Handling:** If a tool execution results in an error, inform the user that there was an issue retrieving the information."
                    )
                },
                {"role": "user", "content": user_message}
            ]

            try:
                # Step 1: Send user message to Groq for tool recommendation
                response = groq_client.chat.completions.create(
                    model="meta-llama/llama-4-maverick-17b-128e-instruct",
                    messages=messages,
                    tools=groq_tools,
                    tool_choice="auto",
                )

                response_message = response.choices[0].message
                tool_calls = response_message.tool_calls

                # Step 2: Check if Groq decided to call a tool
                if tool_calls:
                    messages.append(response_message) # Append the tool call request to the message history

                    # Execute each tool call recommended by Groq
                    for tool_call in tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        
                        tool_output = None
                        if function_name in available_tools:
                            tool_function = available_tools[function_name]
                            try:
                                tool_output = tool_function(**function_args)
                            except Exception as e:
                                tool_output = {"error": f"Error executing tool '{function_name}': {e}"}
                                print(f"Tool execution error: {e}")
                        else:
                            tool_output = {"error": f"Tool '{function_name}' not found."}
                            print(f"Tool not found: {function_name}")
                        
                        # Append tool output to messages
                        messages.append(
                            {
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": function_name,
                                "content": json.dumps(tool_output),
                            }
                        )
                    
                    # Step 3: Send the conversation (with tool outputs) back to Groq for a final, informed response
                    # Groq should now use the tool_output to formulate the answer.
                    second_response = groq_client.chat.completions.create(
                        model="meta-llama/llama-4-maverick-17b-128e-instruct",
                        messages=messages,
                    )
                    bot_response_content = second_response.choices[0].message.content
                else:
                    # If no tool was called, Groq provides a direct text response
                    bot_response_content = response_message.content

                return JsonResponse({"botResponse": bot_response_content})

            except Exception as e:
                print(f"Error communicating with Groq API: {e}")
                return JsonResponse({"error": "Failed to get response from AI. Please try again later."}, status=500)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
    return JsonResponse({"error": "Invalid request method"}, status=405)