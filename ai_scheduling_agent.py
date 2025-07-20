import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any
from pydantic_ai import Agent, Tool
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

@Tool
def get_current_datetime() -> str:
    """Get the current date and time in ISO format with timezone."""
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S+05:30")

@Tool
def extract_meeting_time_from_email(email_content: str, current_datetime: str) -> Dict[str, Any]:
    """Extract meeting timing details from email content with detailed logging and weekend/off-hours handling."""
    print(f"\nLLM TOOL: extract_meeting_time_from_email")
    print(f"Email content: '{email_content}'")
    print(f"Current time: {current_datetime}")
    
    email_lower = email_content.lower()
    
    # Parsing current datetime
    current_dt = datetime.fromisoformat(current_datetime.replace('+05:30', ''))
    print(f"Parsed value for current datetime: {current_dt}")
    
    # Extract duration
    duration = 30  # default
    if "30 min" in email_lower or "30 minutes" in email_lower:
        duration = 30
        print(f"Detected duration: 30 minutes from '30 min/minutes'")
    elif "1 hour" in email_lower or "60 min" in email_lower:
        duration = 60
        print(f"Detected duration: 60 minutes from '1 hour/60 min'")
    elif "15 min" in email_lower:
        duration = 15
        print(f"Detected duration: 15 minutes")
    elif "45 min" in email_lower:
        duration = 45
        print(f"Detected duration: 45 minutes")
    else:
        print(f"Using default duration: 30 minutes (no specific duration found)")
    
    def find_next_business_day(start_date: datetime) -> datetime:
        """Find the next business day (Monday-Friday), skipping weekends."""
        next_day = start_date
        while next_day.weekday() >= 5:  # Saturday=5, Sunday=6
            next_day += timedelta(days=1)
            print(f"Skipping weekend: {next_day.strftime('%A %Y-%m-%d')}")
        return next_day
    
    # Extract day
    target_date = None
    if "thursday" in email_lower:
        # Find next Thursday
        days_ahead = 3 - current_dt.weekday()  # Thursday = 3
        if days_ahead <= 0:
            days_ahead += 7
        target_date = current_dt + timedelta(days=days_ahead)
        print(f"Detected day: Thursday ({days_ahead} days ahead)")
    elif "tuesday" in email_lower:
        days_ahead = 1 - current_dt.weekday()  # Tuesday = 1
        if days_ahead <= 0:
            days_ahead += 7
        target_date = current_dt + timedelta(days=days_ahead)
        print(f"Detected day: Tuesday ({days_ahead} days ahead)")
    elif "friday" in email_lower:
        days_ahead = 4 - current_dt.weekday()  # Friday = 4
        if days_ahead <= 0:
            days_ahead += 7
        target_date = current_dt + timedelta(days=days_ahead)
        print(f"Detected day: Friday ({days_ahead} days ahead)")
    elif "monday" in email_lower:
        days_ahead = 0 - current_dt.weekday()  # Monday = 0
        if days_ahead <= 0:
            days_ahead += 7
        target_date = current_dt + timedelta(days=days_ahead)
        print(f"Detected day: Monday ({days_ahead} days ahead)")
    elif "wednesday" in email_lower:
        days_ahead = 2 - current_dt.weekday()  # Wednesday = 2
        if days_ahead <= 0:
            days_ahead += 7
        target_date = current_dt + timedelta(days=days_ahead)
        print(f"Detected day: Wednesday ({days_ahead} days ahead)")
    elif "tomorrow" in email_lower:
        target_date = current_dt + timedelta(days=1)
        # Check if tomorrow is a weekend
        if target_date.weekday() >= 5:
            target_date = find_next_business_day(target_date)
            print(f"Tomorrow is weekend, moving to next business day")
        print(f"Detected day: Tomorrow")
    elif "today" in email_lower:
        target_date = current_dt
        # Check if today is a weekend
        if target_date.weekday() >= 5:
            target_date = find_next_business_day(target_date)
            print(f"Today is weekend, moving to next business day")
        print(f"Detected day: Today")
    else:
        # Instead of defaulting to Thursday, find the next business day
        target_date = current_dt + timedelta(days=1)
        target_date = find_next_business_day(target_date)
        print(f"No specific day mentioned, using next business day: {target_date.strftime('%A')}")
    
    print(f"Target date: {target_date.strftime('%Y-%m-%d %A')}")
    
    # Verify it's a business day
    if target_date.weekday() >= 5:
        print(f"Warning: Target date {target_date.strftime('%A')} is a weekend!")
        target_date = find_next_business_day(target_date)
        print(f"Adjusted to next business day: {target_date.strftime('%A %Y-%m-%d')}")
    
    # Extract time of day
    meeting_hour = 10  # Default to 10:30 AM
    meeting_minute = 30
    
    if "2 pm" in email_lower or "2:00 pm" in email_lower or "14:00" in email_lower:
        meeting_hour = 14
        meeting_minute = 0
        print(f"Detected time: 2:00 PM from email content")
    elif "10 am" in email_lower or "10:00 am" in email_lower:
        meeting_hour = 10
        meeting_minute = 0
        print(f"Detected time: 10:00 AM from email content")
    elif "3 pm" in email_lower or "15:00" in email_lower:
        meeting_hour = 15
        meeting_minute = 0
        print(f"Detected time: 3:00 PM from email content")
    elif "11 am" in email_lower or "11:00 am" in email_lower:
        meeting_hour = 11
        meeting_minute = 0
        print(f"Detected time: 11:00 AM from email content")
    elif "9 am" in email_lower or "9:00 am" in email_lower:
        meeting_hour = 9
        meeting_minute = 0
        print(f"Detected time: 9:00 AM from email content")
    elif "4 pm" in email_lower or "4:00 pm" in email_lower or "16:00" in email_lower:
        meeting_hour = 16
        meeting_minute = 0
        print(f"Detected time: 4:00 PM from email content")
    elif "morning" in email_lower:
        meeting_hour = 10
        meeting_minute = 0
        print(f"Detected time: Morning (10:00 AM)")
    elif "afternoon" in email_lower:
        meeting_hour = 14
        meeting_minute = 0
        print(f"Detected time: Afternoon (2:00 PM)")
    else:
        print(f"Using default time: 10:30 AM (no specific time found)")
    
    # Validate business hours (9 AM - 6 PM)
    if meeting_hour < 9:
        print(f"Time {meeting_hour}:00 is before business hours, adjusting to 9:00 AM")
        meeting_hour = 9
        meeting_minute = 0
    elif meeting_hour >= 18:
        print(f"Time {meeting_hour}:00 is after business hours, adjusting to next day 10:00 AM")
        target_date += timedelta(days=1)
        target_date = find_next_business_day(target_date)
        meeting_hour = 10
        meeting_minute = 0
    
    # Set optimal meeting time
    meeting_start = target_date.replace(hour=meeting_hour, minute=meeting_minute, second=0, microsecond=0)
    meeting_end = meeting_start + timedelta(minutes=duration)
    
    # Final validation - ensure end time is also within business hours
    if meeting_end.hour >= 18:
        print(f"Meeting end time {meeting_end.hour}:00 exceeds business hours")
        # Adjust start time earlier or move to next day
        if meeting_start.hour > 9:
            # Try moving start time earlier
            meeting_start = meeting_start.replace(hour=9, minute=0)
            meeting_end = meeting_start + timedelta(minutes=duration)
            print(f"Adjusted start time to 9:00 AM to fit within business hours")
        else:
            # Move to next business day
            target_date += timedelta(days=1)
            target_date = find_next_business_day(target_date)
            meeting_start = target_date.replace(hour=10, minute=0, second=0, microsecond=0)
            meeting_end = meeting_start + timedelta(minutes=duration)
            print(f"Moved to next business day due to time constraints")
    
    result = {
        "start_time": meeting_start.strftime("%Y-%m-%dT%H:%M:%S+05:30"),
        "end_time": meeting_end.strftime("%Y-%m-%dT%H:%M:%S+05:30"),
        "duration_minutes": duration,
        "extracted_day": target_date.strftime("%A, %Y-%m-%d"),
        "confidence": "high",
        "business_day_valid": target_date.weekday() < 5,
        "business_hours_valid": 9 <= meeting_start.hour < 18 and meeting_end.hour <= 18,
        "extraction_details": {
            "detected_duration": f"{duration} minutes",
            "detected_day": target_date.strftime("%A"),
            "detected_time": f"{meeting_hour:02d}:{meeting_minute:02d}",
            "parsing_method": "natural_language_with_business_rules",
            "weekend_handling": "automatic_adjustment",
            "off_hours_handling": "business_hours_enforcement"
        }
    }
    
    print(f"LLM Tool Result:")
    print(f"Date: {target_date.strftime('%Y-%m-%d')} ({target_date.strftime('%A')})")
    print(f"Time: {meeting_start.strftime('%H:%M')} - {meeting_end.strftime('%H:%M')}")
    print(f"Duration: {duration} minutes")
    print(f"Confidence: {result['confidence']}")
    
    return result

@Tool
def create_meeting_response(request_data: Dict[str, Any], start_time: str, end_time: str) -> Dict[str, Any]:
    """Create the final meeting response in the exact required format matching 3_Output_Event.json."""
    print(f"\nLLM TOOL: create_meeting_response")
    print(f"Input start_time: {start_time}")
    print(f"Input end_time: {end_time}")
    print(f"From: {request_data.get('From', 'Unknown')}")
    print(f"Attendees count: {len(request_data.get('Attendees', []))}")
    
    # Get all attendees including organizer
    attendee_emails = [request_data["From"]]
    for att in request_data.get("Attendees", []):
        attendee_emails.append(att["email"])
    
    print(f"Enitre attendee list:")
    for i, email in enumerate(attendee_emails):
        print(f"   {i+1}. {email}")
    
    # Create events structure for each attendee (matching 3_Output_Event.json format)
    attendee_events = []
    for attendee in request_data.get("Attendees", []):
        attendee_events.append({
            "email": attendee["email"],
            "events": [
                {
                    "StartTime": start_time,
                    "EndTime": end_time,
                    "NumAttendees": len(attendee_emails),
                    "Attendees": attendee_emails,
                    "Summary": request_data.get("Subject", "Team Meeting")
                }
            ]
        })
    
    # Build response in exact format as 3_Output_Event.json
    response = {
        "Request_id": request_data["Request_id"],
        "Datetime": request_data["Datetime"],
        "Location": request_data["Location"],
        "From": request_data["From"],
        "Attendees": attendee_events,
        "Subject": request_data.get("Subject", "Team Meeting"),
        "EmailContent": request_data.get("EmailContent", ""),
        "EventStart": start_time,
        "EventEnd": end_time,
        "Duration_mins": request_data.get("Duration_mins", "30"),
        "MetaData": {}
    }
    
    print(f"Created meeting response:")
    print(f"EventStart: {response['EventStart']}")
    print(f"EventEnd: {response['EventEnd']}")
    print(f"Subject: {response['Subject']}")
    print(f"Attendees: {len(response['Attendees'])} people")
    
    return response

# Initialize LLM model using working pattern
BASE_URL = "http://localhost:8000/v1"
os.environ["BASE_URL"] = BASE_URL
os.environ["OPENAI_API_KEY"] = "abc-123"

try:
    agent_model = OpenAIModel(
        'Qwen3-30B-A3B',
        provider=OpenAIProvider(
            base_url=os.environ["BASE_URL"], 
            api_key=os.environ["OPENAI_API_KEY"]
        ),
    )

    # Create the date range extraction agent (using your pattern)
    date_range_agent = Agent(
        model=agent_model,
        system_prompt=(
            """
            You are an expert date-time scheduling agent. Your sole responsibility is to find the most optimal date range based on the user's scheduling request.

            Instructions:
            Input: The user will provide a datetime reference (e.g., a timestamp or week/day constraint).

            Start Date Rule:
            Only consider dates after or equal to the provided timestamp. Do not include any date before the specified timestamp.

            Range Logic:
            If the user specifies multiple days or a week, calculate the earliest valid date and the latest valid date based on their input.
            The "Start" field should begin at 00:00:00 on the earliest date.
            The "End" field should end at 23:59:59 on the latest date.

            Duration:
            If the user provides a meeting duration (in minutes), use that value as a string.
            If no duration is specified, default to "30" (as a string).

            Business Hours Consideration:
            Remember that business hours are 9 AM to 6 PM (09:00 to 18:00).
            Off hours are from 6 PM to 9 AM next day (18:00 to 09:00+1day).

            Format:
            Return the output in strict JSON format as:
            {
              "Start": "YYYY-MM-DDT00:00:00+05:30",
              "End": "YYYY-MM-DDT23:59:59+05:30", 
              "Duration_mins": "30"
            }

            Output Requirements:
            Only return the JSON.
            Ensure all datetime values strictly follow the format: YYYY-MM-DDTHH:MM:SS+05:30.
            """
        )
    )

    # Create the optimal time finder agent
    optimal_time_agent = Agent(
        model=agent_model,
        system_prompt=(
            """
            You are an expert meeting time optimizer. Your job is to find the best meeting time within business hours.

            Business Rules:
            - Business hours: 9:00 AM to 6:00 PM (09:00 to 18:00)
            - Off hours: 6:00 PM to 9:00 AM next day (blocked for meetings)
            - Weekdays only (Monday to Friday) - NO WEEKENDS
            - Default meeting duration: 30 minutes

            Weekend Handling:
            - Saturday (weekday=5) and Sunday (weekday=6) are OFF LIMITS
            - Always move weekend meetings to the next Monday
            - If a requested day falls on weekend, automatically adjust to next business day

            Input: You'll get email content with time preferences and a date range.

            Time Extraction:
            - "2 PM" or "14:00" → 14:00
            - "10 AM" or "10:00" → 10:00  
            - "morning" → 10:00
            - "afternoon" → 14:00
            - "3 PM" or "15:00" → 15:00
            - If time is before 9 AM → adjust to 9:00
            - If time is after 6 PM → move to next business day at 10:00

            Day Extraction:
            - "Thursday" → find next Thursday (unless it's in the past)
            - "tomorrow" → next day (if weekend, move to Monday)
            - "today" → current day (if weekend, move to Monday)
            - If no day specified → use next business day (not Thursday by default)

            Output Format:
            {
              "EventStart": "YYYY-MM-DDTHH:MM:SS+05:30",
              "EventEnd": "YYYY-MM-DDTHH:MM:SS+05:30",
              "OptimalTime": "HH:MM on DayName",
              "BusinessHoursValid": true,
              "Reasoning": "Why this time was chosen, including weekend/off-hours adjustments"
            }

            Always ensure:
            1. No weekend meetings (Saturday/Sunday)
            2. All times between 9:00 AM and 6:00 PM
            3. Meeting end time doesn't exceed 6:00 PM
            4. Clear reasoning for any adjustments made
            """
        )
    )

    # Create the meeting scheduler agent with working pattern
    meeting_agent = Agent(
        model=agent_model,
        tools=[get_current_datetime, extract_meeting_time_from_email, create_meeting_response],
        system_prompt=(
            "You are an AI Meeting Scheduler. Your job is to:\n"
            "1. Extract meeting details from email content using tools\n"
            "2. Find the optimal meeting time based on the request\n"
            "3. Return the meeting in the exact JSON format required\n\n"
            "Always use the tools to:\n"
            "- Get current datetime\n"
            "- Extract meeting time from email content\n"
            "- Create the final response\n\n"
            "Be concise and focus on extracting the Start and End times accurately.\n"
            "Consider that calendars have 'Off Hours' blocks from 6 PM to 9 AM daily.\n"
            "Schedule meetings only during business hours (9 AM to 6 PM).\n"
            "Weekends (Saturday/Sunday) are also considered off-hours."
        )
    )
    
    print(f"LLM Agent initialized successfully")
    LLM_AVAILABLE = True
    
except Exception as e:
    print(f"LLM initialization failed: {e}")
    LLM_AVAILABLE = False
    meeting_agent = None

async def date_range_run(prompt: str) -> str:
    """Extract date range using your working pattern"""
    if not LLM_AVAILABLE or not date_range_agent:
        raise Exception("Date range agent not available")
    
    async with date_range_agent.run_mcp_servers():
        print("Executing date_range_agent.run_mcp_servers")
        try:
            result = await date_range_agent.run(prompt)
        except Exception as e:
            print(f"Error running date_range_agent: {e}")
            return None
        return result.output


async def optimal_time_run(prompt: str) -> str:
    """Find optimal meeting time considering business hours and off-hours"""
    if not LLM_AVAILABLE or not optimal_time_agent:
        raise Exception("Optimal time agent not available")
    
    async with optimal_time_agent.run_mcp_servers():
        result = await optimal_time_agent.run(prompt)
        return result.output

async def run_async(prompt: str) -> str:
    """Helper function to run LLM async operations"""
    if not LLM_AVAILABLE or not meeting_agent:
        raise Exception("LLM not available")
    
    async with meeting_agent.run_mcp_servers():
        result = await meeting_agent.run(prompt)
        return result.output

async def schedule_meeting_async(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Enhanced meeting scheduling with date range extraction and optimal time finding."""
    print(f"\nENHANCED LLM SCHEDULING: schedule_meeting_async")
    print(f"Request data keys: {list(request_data.keys())}")
    
    if not LLM_AVAILABLE:
        print(f"LLM server not available")
        return {"status": "error", "error": "LLM server not available"}
    
    try:
        print(f"Starting enhanced LLM scheduling...")
        
        # Step 1: Extract date range using your pattern
        print(f"\nSTEP 1: DATE RANGE EXTRACTION")
        email_content = request_data.get('EmailContent', '')
        datetime_ref = request_data.get('Datetime', '')
        
        date_range_prompt = json.dumps({
            "Datetime": datetime_ref,
            "EmailContent": email_content
        })
        
        print(f"Sending to date range agent:")
        print(f"   Datetime: {datetime_ref}")
        print(f"   Email: {email_content[:100]}...")
        
        date_range_result = await date_range_run(date_range_prompt)
        print(f"Date range result: {date_range_result}")
        
        # Parse the date range result
        try:
            date_range_data = json.loads(date_range_result)
            start_range = date_range_data.get('Start')
            end_range = date_range_data.get('End')
            duration_mins = date_range_data.get('Duration_mins', '30')
            print(f"Parsed date range:")
            print(f"Start: {start_range}")
            print(f"End: {end_range}")
            print(f"Duration: {duration_mins} minutes")
        except json.JSONDecodeError as e:
            print(f"Failed to parse date range JSON: {e}")
            # Fallback to original data
            start_range = request_data.get('Start')
            end_range = request_data.get('End')
            duration_mins = request_data.get('Duration_mins', '30')
        
        # Step 2: Find optimal meeting time considering off-hours and weekends
        print(f"\nSTEP 2: OPTIMAL TIME FINDING")
        optimal_time_prompt = f"""
        Find the optimal meeting time for this request:
        
        Email Content: {email_content}
        Date Range: {start_range} to {end_range}
        Duration: {duration_mins} minutes
        Attendees: {[att.get('email') for att in request_data.get('Attendees', [])]}
        
        Remember:
        - Business hours: 9 AM to 6 PM only
        - NO WEEKENDS: Saturday and Sunday are off-limits
        - Avoid off-hours: 6 PM to 9 AM next day
        - Parse time mentions like "2 PM", "morning", "afternoon"
        - Ensure meeting fits within business hours
        - If requested day is weekend, move to next Monday
        - If no specific day mentioned, use next business day (NOT Thursday by default)
        """
        
        print(f"Sending to optimal time agent...")
        optimal_time_result = await optimal_time_run(optimal_time_prompt)
        print(f"Optimal time result: {optimal_time_result}")
        
        # Parse optimal time result
        try:
            optimal_data = json.loads(optimal_time_result)
            event_start = optimal_data.get('EventStart')
            event_end = optimal_data.get('EventEnd')
            optimal_time = optimal_data.get('OptimalTime')
            business_valid = optimal_data.get('BusinessHoursValid', True)
            reasoning = optimal_data.get('Reasoning', 'LLM scheduling')
            
            print(f"Parsed optimal time:")
            print(f"EventStart: {event_start}")
            print(f"EventEnd: {event_end}")
            print(f"OptimalTime: {optimal_time}")
            print(f"BusinessHoursValid: {business_valid}")
            print(f"Reasoning: {reasoning}")
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse optimal time JSON: {e}")
            # Fallback to default time calculation with weekend avoidance
            from datetime import datetime, timedelta
            
            def find_next_business_day_fallback(start_date: datetime) -> datetime:
                """Find the next business day (Monday-Friday), skipping weekends."""
                next_day = start_date
                while next_day.weekday() >= 5:  # Saturday=5, Sunday=6
                    next_day += timedelta(days=1)
                    print(f"Fallback: Skipping weekend day {next_day.strftime('%A')}")
                return next_day
            
            try:
                start_dt = datetime.fromisoformat(start_range.replace('+05:30', ''))
                # Find next business day from start range
                business_day = find_next_business_day_fallback(start_dt)
                # Default to 10:30 AM on the business day
                event_start_dt = business_day.replace(hour=10, minute=30, second=0, microsecond=0)
                event_end_dt = event_start_dt + timedelta(minutes=int(duration_mins))
                
                event_start = event_start_dt.strftime("%Y-%m-%dT%H:%M:%S+05:30")
                event_end = event_end_dt.strftime("%Y-%m-%dT%H:%M:%S+05:30")
                reasoning = f"Fallback to 10:30 AM on {business_day.strftime('%A %Y-%m-%d')} (weekend avoidance applied)"
                
            except Exception as fallback_error:
                print(f"Fallback time calculation failed: {fallback_error}")
                return {"status": "error", "error": f"Time calculation failed: {fallback_error}"}
        
        # Step 3: Create final response with extracted times
        print(f"\nSTEP 3: RESPONSE CREATION")
        final_response = {
            "status": "success",
            "event_start": event_start,
            "event_end": event_end,
            "duration_mins": duration_mins,
            "start_range": start_range,
            "end_range": end_range,
            "reasoning": reasoning,
            "method": "enhanced_llm_scheduling"
        }
        
        print(f"Enhanced LLM scheduling complete:")
        print(f"Meeting: {event_start} to {event_end}")
        print(f"Duration: {duration_mins} minutes")
        print(f"Method: Enhanced LLM with off-hours consideration")
        
        return final_response
        
    except Exception as e:
        print(f"Enhanced LLM scheduling error: {str(e)}")
        return {"status": "error", "error": str(e)}

def schedule_meeting(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Synchronous wrapper for LLM meeting scheduling with working pattern."""
    print(f"\nLLM WRAPPER: schedule_meeting")
    print(f"Request ID: {request_data.get('Request_id', 'Unknown')}")
    
    if not LLM_AVAILABLE:
        print(f"LLM not available")
        return {"status": "error", "error": "LLM server not available"}
    
    try:
        print(f"Setting up async event loop...")
        import asyncio
        
        # Use new event loop pattern
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        print(f"Executing LLM async function...")
        result = loop.run_until_complete(schedule_meeting_async(request_data))
        
        print(f"LLM wrapper result:")
        print(f"   Status: {result.get('status', 'Unknown')}")
        if result.get('status') == 'success':
            print(f"   Response available: {result.get('response') is not None}")
        else:
            print(f"   Error: {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        print(f"LLM wrapper error: {str(e)}")
        return {"status": "error", "error": str(e)}