import json
import requests
import time

def create_1000_students_and_test():
    print("=== 1000 Students Performance Test ===\n")
    
    # Read the student names from the file
    with open("student_names_1000.txt", "r") as f:
        names_string = f.read().strip()

    # Split by comma and clean up
    names_list = [name.strip() for name in names_string.split(",")]
    print(f"Loaded {len(names_list)} student names")

    # Create the JSON payload for /add-students
    students = []
    for i, full_name in enumerate(names_list, 1):
        name_parts = full_name.split(" ")
        first_name = name_parts[0]
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else "Unknown"
        
        student = {
            "first_name": first_name,
            "last_name": last_name,
            "gamer_tag": f"@{first_name.lower()}{last_name.lower()}{i}",
            "website_id": 1000000 + i,  # Start from 1000001
            "current_class": "1k_test_class"  # All in class 1
        }
        students.append(student)

    # Create the full payload
    payload = {
        "teacher_website_id": "2",
        "add_classes_to_teacher": True,
        "students": students
    }

    print(f"Created payload with {len(students)} students")
    print(f"Website IDs range from {1000001} to {1000000 + len(students)}")
    print("All students assigned to teacher_website_id: 2, current_class: 1")
    
    # Save payload to file for reference
    with open("1000_students_payload.json", "w") as f:
        json.dump(payload, f, indent=2)
    print("Payload saved to 1000_students_payload.json")

    # Test with both local and production endpoints
    endpoints = [
        ("Local", "http://localhost:5000/add-students"),
        ("Production", "https://craffft-api-e21e23f89690.herokuapp.com/add-students")
    ]

    for endpoint_name, url in endpoints:
        print(f"\n--- Testing {endpoint_name} Endpoint ---")
        print(f"URL: {url}")
        
        try:
            # Record start time
            start_time = time.time()
            
            # Make the request
            print("Sending request...")
            response = requests.post(
                url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=300  # 5 minute timeout
            )
            
            # Record end time
            end_time = time.time()
            request_duration = end_time - start_time
            
            print(f"✅ Request completed!")
            print(f"⏱️  Duration: {request_duration:.2f} seconds")
            print(f"📊 Status Code: {response.status_code}")
            
            # Parse response
            if response.status_code in [200, 201]:
                data = response.json()
                print(f"✅ Added: {data.get('added_count', 0)} students")
                print(f"❌ Failed: {data.get('failed_count', 0)} students")
                
                if data.get('failed_count', 0) > 0:
                    print("Failed students:")
                    for failed in data.get('failed_students', [])[:5]:  # Show first 5 failures
                        print(f"  - {failed}")
                    if len(data.get('failed_students', [])) > 5:
                        print(f"  ... and {len(data.get('failed_students', [])) - 5} more")
            else:
                print(f"❌ Request failed:")
                print(f"Response: {response.text[:500]}...")  # First 500 chars
                
        except requests.exceptions.Timeout:
            print(f"⏰ Request timed out after 5 minutes")
        except requests.exceptions.ConnectionError:
            print(f"🔌 Connection error - server might be down or URL incorrect")
        except Exception as e:
            print(f"💥 Unexpected error: {e}")

    print(f"\n=== Performance Test Complete ===")

if __name__ == "__main__":
    create_1000_students_and_test()
