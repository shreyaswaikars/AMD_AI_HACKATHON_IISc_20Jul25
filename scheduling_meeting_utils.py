import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pytz
from calendar_events_fetch import retrive_calendar_events

class MeetingScheduler:
    def __init__(self):
        self.timezone = pytz.timezone('Asia/Kolkata')
        self.business_start = 9  # 9 AM
        self.business_end = 18   # 6 PM
        
    def parse_email_content(self, email_content: str, current_time: str) -> Dict[str, Any]:
        """Parse email content to extract meeting preferences using simple NLP."""
        email_lower = email_content.lower()
        
        # Extract duration
        duration = 30  # default
        if "30 min" in email_lower or "half hour" in email_lower:
            duration = 30
        elif "1 hour" in email_lower or "60 min" in email_lower:
            duration = 60
        elif "15 min" in email_lower:
            duration = 15
        elif "45 min" in email_lower:
            duration = 45
        
        # Extract day preference with improved date parsing
        try:
            # Handle different date formats
            if 'T' in current_time:
                # Format: "02-07-2025T12:34:55" -> "2025-07-02T12:34:55"
                if '-' in current_time and len(current_time.split('-')[0]) == 2:
                    parts = current_time.split('T')
                    date_part = parts[0]
                    time_part = parts[1] if len(parts) > 1 else "00:00:00"
                    
                    # Split date: "02-07-2025" -> ["02", "07", "2025"]
                    date_components = date_part.split('-')
                    if len(date_components) == 3:
                        # Rearrange to ISO format: "2025-07-02"
                        iso_date = f"{date_components[2]}-{date_components[1]}-{date_components[0]}"
                        current_time = f"{iso_date}T{time_part}"
                
                current_dt = datetime.fromisoformat(current_time)
            else:
                # Fallback to current time if parsing fails
                current_dt = datetime.now()
        except (ValueError, IndexError) as e:
            print(f"Date parsing warning: {e}, using current time")
            current_dt = datetime.now()
        preferred_day = None
        
        if "monday" in email_lower:
            preferred_day = self._get_next_weekday(current_dt, 0)
        elif "tuesday" in email_lower:
            preferred_day = self._get_next_weekday(current_dt, 1)
        elif "wednesday" in email_lower:
            preferred_day = self._get_next_weekday(current_dt, 2)
        elif "thursday" in email_lower:
            preferred_day = self._get_next_weekday(current_dt, 3)
        elif "friday" in email_lower:
            preferred_day = self._get_next_weekday(current_dt, 4)
        elif "tomorrow" in email_lower:
            preferred_day = current_dt + timedelta(days=1)
        elif "today" in email_lower:
            preferred_day = current_dt
        
        # Extract urgency/priority
        priority = "medium"
        if any(word in email_lower for word in ["urgent", "asap", "immediately", "critical"]):
            priority = "high"
        elif any(word in email_lower for word in ["when convenient", "flexible", "no rush"]):
            priority = "low"
        
        return {
            "duration_minutes": duration,
            "preferred_day": preferred_day.isoformat() if preferred_day else None,
            "priority": priority,
            "urgency_keywords": [word for word in ["urgent", "asap", "critical"] if word in email_lower]
        }
    
    def _get_next_weekday(self, current_date: datetime, weekday: int) -> datetime:
        """Get the next occurrence of a specific weekday."""
        days_ahead = weekday - current_date.weekday()
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        return current_date + timedelta(days=days_ahead)
    
    def get_availability_for_all(self, attendees: List[str], start_time: str, end_time: str) -> Dict[str, Any]:
        """Get calendar events for all attendees and analyze availability."""
        all_events = {}
        availability_summary = {}
        
        for attendee in attendees:
            try:
                events = retrive_calendar_events(attendee, start_time, end_time)
                all_events[attendee] = events
                
                # Calculate busy hours
                busy_slots = []
                for event in events:
                    busy_slots.append({
                        "start": event["StartTime"],
                        "end": event["EndTime"],
                        "summary": event["Summary"]
                    })
                
                availability_summary[attendee] = {
                    "total_events": len(events),
                    "busy_slots": busy_slots,
                    "status": "available" if len(events) < 5 else "busy"
                }
                
            except Exception as e:
                all_events[attendee] = {"error": str(e)}
                availability_summary[attendee] = {
                    "status": "unavailable",
                    "error": str(e)
                }
        
        return {
            "detailed_events": all_events,
            "availability_summary": availability_summary
        }
    
    def find_best_time_slots(self, attendees_availability: Dict[str, Any], 
                           duration_minutes: int, start_range: str, end_range: str,
                           preferred_day: Optional[str] = None) -> List[Dict[str, Any]]:
        """Find the best available time slots for the meeting."""
        try:
            # Parse start and end times with flexible format handling
            start_dt = self._parse_flexible_datetime(start_range)
            end_dt = self._parse_flexible_datetime(end_range)
        except Exception as e:
            print(f"Date parsing error: {e}")
            # Fallback to next day if parsing fails
            start_dt = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
            end_dt = start_dt + timedelta(days=1)
        
        # If preferred day is specified, narrow down the range
        if preferred_day:
            pref_dt = datetime.fromisoformat(preferred_day)
            start_dt = max(start_dt, pref_dt.replace(hour=self.business_start, minute=0))
            end_dt = min(end_dt, pref_dt.replace(hour=self.business_end, minute=0))
        
        available_slots = []
        detailed_events = attendees_availability.get("detailed_events", {})
        
        # Generate potential time slots
        current = start_dt.replace(hour=self.business_start, minute=0, second=0, microsecond=0)
        
        while current <= end_dt:
            # Skip weekends
            if current.weekday() >= 5:  # Saturday = 5, Sunday = 6
                current += timedelta(days=1)
                continue
            
            # Check business hours
            if current.hour < self.business_start or current.hour >= self.business_end:
                if current.hour >= self.business_end:
                    current = current.replace(hour=self.business_start, minute=0) + timedelta(days=1)
                else:
                    current = current.replace(hour=self.business_start, minute=0)
                continue
            
            slot_end = current + timedelta(minutes=duration_minutes)
            
            # Skip if meeting would go beyond business hours
            if slot_end.hour > self.business_end:
                current = current.replace(hour=self.business_start, minute=0) + timedelta(days=1)
                continue
            
            # Check availability for all attendees
            conflicts = []
            all_available = True
            
            for attendee, events in detailed_events.items():
                if isinstance(events, dict) and "error" in events:
                    continue
                
                for event in events:
                    event_start = datetime.fromisoformat(event["StartTime"])
                    event_end = datetime.fromisoformat(event["EndTime"])
                    
                    # Make timezone-naive for comparison if needed
                    if event_start.tzinfo is not None:
                        event_start = event_start.replace(tzinfo=None)
                    if event_end.tzinfo is not None:
                        event_end = event_end.replace(tzinfo=None)
                    
                    # Ensure slot times are also timezone-naive
                    slot_start_naive = current.replace(tzinfo=None) if current.tzinfo else current
                    slot_end_naive = slot_end.replace(tzinfo=None) if slot_end.tzinfo else slot_end
                    
                    # Check for overlap
                    if (slot_start_naive < event_end and slot_end_naive > event_start):
                        all_available = False
                        conflicts.append({
                            "attendee": attendee,
                            "conflicting_event": event["Summary"],
                            "event_time": f"{event['StartTime']} - {event['EndTime']}"
                        })
                        break
            
            # Calculate score for this slot
            score = self._calculate_slot_score(current, all_available, conflicts)
            
            slot_info = {
                "start_time": current.isoformat(),
                "end_time": slot_end.isoformat(),
                "all_available": all_available,
                "conflicts": conflicts,
                "score": score,
                "day_of_week": current.strftime("%A"),
                "time_preference": self._get_time_preference(current.hour)
            }
            
            available_slots.append(slot_info)
            
            # Move to next 15-minute slot
            current += timedelta(minutes=15)
        
        # Sort by score and availability
        available_slots.sort(key=lambda x: (x["all_available"], x["score"]), reverse=True)
        
        return available_slots[:5]  # Return top 5 options
    
    def _calculate_slot_score(self, slot_time: datetime, all_available: bool, conflicts: List) -> float:
        """Calculate a score for the time slot based on various factors."""
        score = 0.0
        
        # Base score for availability
        if all_available:
            score += 100
        else:
            score -= len(conflicts) * 20
        
        # Time preference scoring
        hour = slot_time.hour
        if 9 <= hour <= 11:  # Morning preferred
            score += 20
        elif 14 <= hour <= 16:  # Early afternoon
            score += 15
        elif 11 <= hour <= 12:  # Late morning
            score += 10
        elif 16 <= hour <= 17:  # Late afternoon
            score += 5
        else:  # Less preferred times
            score -= 10
        
        # Day preference (Tuesday-Thursday preferred)
        weekday = slot_time.weekday()
        if weekday in [1, 2, 3]:  # Tue, Wed, Thu
            score += 10
        elif weekday in [0, 4]:  # Mon, Fri
            score += 5
        
        # Avoid lunch time
        if 12 <= hour <= 13:
            score -= 15
        
        return score
    
    def _get_time_preference(self, hour: int) -> str:
        """Get time preference label."""
        if 9 <= hour <= 11:
            return "morning_preferred"
        elif 11 <= hour <= 13:
            return "late_morning"
        elif 13 <= hour <= 15:
            return "early_afternoon"
        elif 15 <= hour <= 17:
            return "late_afternoon"
        else:
            return "non_business_hours"
    
    def create_meeting_response(self, request_data: Dict[str, Any], 
                              best_slot: Dict[str, Any], 
                              all_availability: Dict[str, Any]) -> Dict[str, Any]:
        """Create the final meeting response in the required format."""
        
        # Extract attendee emails
        attendee_emails = [request_data["From"]]
        for attendee in request_data.get("Attendees", []):
            attendee_emails.append(attendee["email"])
        
        # Create the response structure
        response = {
            "Request_id": request_data["Request_id"],
            "Datetime": request_data["Datetime"],
            "Location": request_data["Location"],
            "From": request_data["From"],
            "Attendees": []
        }
        
        # Fix missing Subject
        subject = request_data.get("Subject")
        if not subject:
            # Extract from email content
            email_content = request_data.get("EmailContent", "")
            if "goals" in email_content.lower():
                subject = "Goals Discussion Meeting"
            else:
                subject = "Team Meeting"
        
        # Create the scheduled meeting event
        scheduled_event = {
            "StartTime": best_slot["start_time"],
            "EndTime": best_slot["end_time"],
            "NumAttendees": len(attendee_emails),
            "Attendees": attendee_emails,
            "Summary": subject
        }
        
        # Add events for each attendee
        for attendee_email in attendee_emails:
            attendee_events = []
            
            # Add existing events from their calendar
            if attendee_email in all_availability.get("detailed_events", {}):
                existing_events = all_availability["detailed_events"][attendee_email]
                if not isinstance(existing_events, dict) or "error" not in existing_events:
                    attendee_events.extend(existing_events)
            
            # Add the new scheduled meeting
            attendee_events.append(scheduled_event)
            
            response["Attendees"].append({
                "email": attendee_email,
                "events": attendee_events
            })
        
        return response

    def _parse_flexible_datetime(self, datetime_str: str) -> datetime:
        """Parse datetime string with flexible format handling."""
        if not datetime_str:
            return datetime.now()
        
        # Remove timezone info for consistent handling
        clean_str = datetime_str.replace('Z', '').replace('+00:00', '').replace('+05:30', '')
        
        # Handle different formats
        try:
            # Try standard ISO format first
            dt = datetime.fromisoformat(clean_str)
            # Ensure timezone-naive for consistent comparison
            return dt.replace(tzinfo=None) if dt.tzinfo else dt
        except ValueError:
            pass
        
        try:
            # Handle DD-MM-YYYY format: "02-07-2025T12:34:55"
            if 'T' in clean_str:
                date_part, time_part = clean_str.split('T')
                if '-' in date_part and len(date_part.split('-')[0]) == 2:
                    # Convert "02-07-2025" to "2025-07-02"
                    day, month, year = date_part.split('-')
                    iso_date = f"{year}-{month}-{day}"
                    return datetime.fromisoformat(f"{iso_date}T{time_part}")
        except ValueError:
            pass
        
        try:
            # Handle date only formats
            if '-' in clean_str and 'T' not in clean_str:
                parts = clean_str.split('-')
                if len(parts) == 3 and len(parts[0]) == 2:
                    # DD-MM-YYYY format
                    day, month, year = parts
                    return datetime(int(year), int(month), int(day))
                elif len(parts) == 3 and len(parts[0]) == 4:
                    # YYYY-MM-DD format
                    return datetime.fromisoformat(clean_str)
        except ValueError:
            pass
        
        # Fallback to current time
        print(f"Warning: Could not parse datetime '{datetime_str}', using current time")
        return datetime.now()

def process_meeting_request(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Main function to process a meeting request and return the scheduled meeting."""
    scheduler = MeetingScheduler()
    
    try:
        # Parse email content for additional details
        email_analysis = scheduler.parse_email_content(
            request_data.get("EmailContent", ""), 
            request_data.get("Datetime", "")
        )
        
        # Get duration from analysis or request
        duration = int(request_data.get("Duration_mins", email_analysis["duration_minutes"]))
        
        # Get all attendees
        attendee_emails = [request_data["From"]]
        for attendee in request_data.get("Attendees", []):
            attendee_emails.append(attendee["email"])
        
        # Handle the case where Start/End might not be provided
        start_time = request_data.get("Start")
        end_time = request_data.get("End")
        
        # If no time range provided, create a default range for next week
        if not start_time or not end_time:
            now = datetime.now()
            next_week = now + timedelta(days=7)
            start_time = now.replace(hour=0, minute=0, second=0).isoformat()
            end_time = next_week.replace(hour=23, minute=59, second=59).isoformat()
        
        # Get availability for all attendees
        availability = scheduler.get_availability_for_all(
            attendee_emails,
            start_time,
            end_time
        )
        
        # Find best time slots
        time_slots = scheduler.find_best_time_slots(
            availability,
            duration,
            start_time,
            end_time,
            email_analysis.get("preferred_day")
        )
        
        if not time_slots:
            # No available slots found
            return {
                "error": "No available time slots found for all attendees",
                "availability_summary": availability["availability_summary"]
            }
        
        # Select the best available slot
        best_slot = next((slot for slot in time_slots if slot["all_available"]), time_slots[0])
        
        # Create the final response
        meeting_response = scheduler.create_meeting_response(request_data, best_slot, availability)
        
        # Add metadata
        meeting_response["scheduling_metadata"] = {
            "email_analysis": email_analysis,
            "slot_score": best_slot["score"],
            "conflicts_resolved": not best_slot["all_available"],
            "alternative_slots": len([s for s in time_slots if s["all_available"]]),
            "processing_timestamp": datetime.now().isoformat()
        }
        
        return meeting_response
        
    except Exception as e:
        return {
            "error": f"Failed to process meeting request: {str(e)}",
            "request_id": request_data.get("Request_id", "unknown"),
            "debug_info": {
                "original_datetime": request_data.get("Datetime", ""),
                "error_type": type(e).__name__
            }
        }