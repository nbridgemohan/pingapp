import json
from datetime import datetime, timedelta
import requests
import sys

# function to check grace period time
def is_within_grace_period(actual_time, expected_time, grace_period_minutes=15):
    try:
        actual_datetime = datetime.strptime(actual_time, '%H:%M:%S')
        expected_datetime = datetime.strptime(expected_time, '%H:%M:%S')
        grace_period = timedelta(minutes=grace_period_minutes)
        
        start_time = expected_datetime - grace_period
        end_time = expected_datetime + grace_period

        return start_time <= actual_datetime <= end_time
    except (ValueError, TypeError):
        return False

# function to get extreme weather days
def get_extreme_weather_days(weather_data, country, year):
    extreme_weather_days = [entry["date"] for entry in weather_data if entry["country"] == country and entry["date"].startswith(year) and entry["condition"] in ["hail", "blizzard", "thunderstorm", "extreme heat", "hurricane"]]
    return extreme_weather_days

# code to fetch data
def fetch_data(api_url):
    response = requests.get(api_url)
    if response.status_code == 200:
        print(f"Fetching data from '{api_url}'...")
        return json.loads(response.text)
    else:
        print(f"Failed to fetch data from {api_url}. Status code {response.status_code}")
        sys.exit(1)

def load_json_file(file_path):
    try:
        with open(file_path, 'r') as file:
            print(f"Loading data from '{file_path}'...")            
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: Could not find '{file_path}'. Please make sure the file exists.")
        sys.exit(1)
        
def main():
    
    # Loading data
    employee_data = load_json_file('data/employees.json')
    attendance_data = load_json_file('data/attendance.json')

    # API endpoints
    events_api_url = "https://www.pingtt.com/exam/events"
    weather_api_url = "https://www.pingtt.com/exam/weather"
    # event data from API
    event_data = fetch_data(events_api_url)
    # weather data from API
    weather_data = fetch_data(weather_api_url)

    # for debugging purposes
    # with open('debug/event_data.json', 'w') as outfile:
    #     json.dump(event_data, outfile, indent=2)
    # with open('debug/weather_data.json', 'w') as outfile:
    #     json.dump(weather_data, outfile, indent=2)
        
    # perform calculations
    results = []

    print("Performing calculations...")

    for employee in employee_data:
        employee_id = employee["record_id"]
        country = employee["country"]
        expected_workday_start_time = '08:00:00'
        grace_period_minutes = 15

        # extreme weather days for the employee's country and year
        extreme_weather_days = get_extreme_weather_days(weather_data, country, "2023")

        # filter attendance data for the current employee
        employee_attendance = [entry for entry in attendance_data if entry["employee_record_id"] == employee_id]

        # initialize counters for tardy, early departure, and absenteeism
        tardy_count = early_departure_count = absenteeism_count = 0
        events_attended = []

        for entry in employee_attendance:
            entry_date = entry["date"]
            clock_in_time = entry["clock_in"]
            clock_out_time = entry["clock_out"]

            # increment absenteeism if the either clock in or clock out is None
            # TODO need some clarification with this logic
            if clock_in_time is None or clock_out_time is None:
                continue

            # check if the employee was within the grace period
            if not is_within_grace_period(clock_in_time, expected_workday_start_time, grace_period_minutes):
                tardy_count += 1

            # check if the employee left early
            clock_out_datetime = datetime.strptime(clock_out_time, '%H:%M:%S')
            if clock_out_datetime < datetime.strptime('16:00:00', '%H:%M:%S'):
                early_departure_count += 1

            # check for absenteeism on workdays (excluding extreme weather days)
            if entry_date not in extreme_weather_days:
                events_attended_for_date = [
                    event for event in event_data 
                    if event["event_date"] == entry_date and event["country"] == country
                ]

                if not events_attended_for_date:
                    absenteeism_count += 1

                # record events attended on non-working days
                events_attended.extend(events_attended_for_date)


        # check if the employee meets the criteria for a pattern
        if tardy_count + early_departure_count + absenteeism_count > 3:
        # calculate total hours worked, handling none values
            total_hours_worked = sum(
                [
                    (
                        int(entry["clock_out"].split(":")[0]) if (entry["clock_out"] and ":" in entry["clock_out"]) else 0
                    )
                    - (
                        int(entry["clock_in"].split(":")[0]) if (entry["clock_in"] and ":" in entry["clock_in"]) else 0
                    )
                    for entry in employee_attendance
                    if entry["clock_in"] and entry["clock_out"]
                ]
            )

            average_hours_per_week = (total_hours_worked / len(employee_attendance)) * 5  # assuming 5 working days in a week

            # construct result dictionary for the employee
            result_entry = {
                "record_id": employee_id,
                "name": employee["name"],
                "work_id_number": employee["work_id_number"],
                "email_address": employee["email_address"],
                "country": country,
                "phone_number": employee["phone_number"],
                "average_hours_per_week": average_hours_per_week,
                "events": events_attended
            }
            print("Appending data:")
            result_json = json.dumps(result_entry, indent=2)
            print(result_json)
            results.append(result_entry)

    # save results in json format
    with open('results/results.json', 'w') as outfile:
        json.dump(results, outfile, indent=2)
    print("Done!")

if __name__ == "__main__":
    main()