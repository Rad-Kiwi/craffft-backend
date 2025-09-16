# niche-tests/test_db_concurrency.py uses threading to test database concurrency performance
# against the /update-and-check-quest endpoint of the deployed Flask app.

import requests
import threading
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import random

class ConcurrencyTest:
    def __init__(self):
        self.base_url = "https://craffft-api-e21e23f89690.herokuapp.com"
        self.student_ids = []
        self.valid_steps = []
        self.results = []
        self.lock = threading.Lock()
        
    def get_student_ids(self, num_students=30):
        """Fetch the first 30 students from the craffft_students table"""
        print("🔍 Fetching student data...")
        
        try:
            response = requests.get(f"{self.base_url}/get-table-as-json/craffft_students", timeout=30)
            if response.status_code == 200:
                students_data = response.json()
                
                # Extract website_ids from the first num_students
                student_ids = []
                for student in students_data[:num_students]:
                    website_id = student.get('website_id')
                    if website_id:
                        student_ids.append(str(website_id))
                
                print(f"✅ Found {len(student_ids)} students")
                if len(student_ids) < num_students:
                    print(f"⚠️  Warning: Only found {len(student_ids)} students, requested {num_students}")
                
                return student_ids
            else:
                print(f"❌ Failed to fetch students: {response.status_code}")
                print(f"Response: {response.text[:200]}...")
                return []
                
        except Exception as e:
            print(f"💥 Error fetching students: {e}")
            return []
    
    def get_valid_steps(self):
        """Fetch valid step names from the craffft_steps table"""
        print("🔍 Fetching valid steps...")
        
        try:
            response = requests.get(f"{self.base_url}/get-table-as-json/craffft_steps", timeout=30)
            if response.status_code == 200:
                steps_data = response.json()
                
                # Extract step names
                step_names = []
                for step in steps_data:
                    step_name = step.get('name')
                    if step_name:
                        step_names.append(step_name)
                
                if not step_names:
                    print("❌ No valid steps found in the database")
                    return []
                
                print(f"✅ Found {len(step_names)} valid steps")
                print(f"📋 Sample steps: {step_names[:5]}..." + (f" (+{len(step_names)-5} more)" if len(step_names) > 5 else ""))
                
                return step_names
            else:
                print(f"❌ Failed to fetch steps: {response.status_code}")
                print(f"Response: {response.text[:200]}...")
                return []
                
        except Exception as e:
            print(f"💥 Error fetching steps: {e}")
            return []
    
    def make_quest_request(self, website_id, thread_id):
        """Make a single request to update-and-check-quest"""
        # Use a random step from the valid steps fetched from the database
        current_step = random.choice(self.valid_steps) if self.valid_steps else "step1"
        
        url = f"{self.base_url}/update-and-check-quest"
        params = {
            "websiteId": website_id,
            "current-step": current_step,
            "allow-quest-update": "true"
        }
        
        start_time = time.time()
        
        try:
            response = requests.get(url, params=params, timeout=30)
            end_time = time.time()
            duration = end_time - start_time
            
            result = {
                "thread_id": thread_id,
                "website_id": website_id,
                "current_step": current_step,
                "status_code": response.status_code,
                "duration": duration,
                "success": response.status_code == 200,
                "response_size": len(response.content),
                "error": None
            }
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    result["quest_changed"] = data.get("quest_changed", False)
                    result["current_quest"] = data.get("current_quest", "")
                except:
                    result["quest_changed"] = None
                    result["current_quest"] = ""
            
            return result
            
        except requests.exceptions.Timeout:
            return {
                "thread_id": thread_id,
                "website_id": website_id,
                "current_step": current_step,
                "status_code": None,
                "duration": time.time() - start_time,
                "success": False,
                "response_size": 0,
                "error": "Timeout"
            }
        except Exception as e:
            return {
                "thread_id": thread_id,
                "website_id": website_id,
                "current_step": current_step,
                "status_code": None,
                "duration": time.time() - start_time,
                "success": False,
                "response_size": 0,
                "error": str(e)
            }
    
    def run_concurrency_test(self, num_students=30, num_threads=8):
        """Run the concurrency test"""
        print("🚀 Starting Database Concurrency Test")
        print(f"📊 Configuration: {num_students} students, {num_threads} threads")
        print(f"🎯 Target: {self.base_url}")
        print("=" * 50)
        
        # Get valid steps first
        self.valid_steps = self.get_valid_steps()
        if not self.valid_steps:
            print("❌ No valid steps found, cannot run test")
            return
        
        # Get student IDs
        student_ids = self.get_student_ids(num_students)
        if not student_ids:
            print("❌ No students found, cannot run test")
            return
        
        print(f"\n📋 Student IDs to test: {student_ids[:5]}..." + (f" (+{len(student_ids)-5} more)" if len(student_ids) > 5 else ""))
        
        # Prepare requests (create multiple requests per student to reach desired concurrency)
        requests_to_make = []
        for i, student_id in enumerate(student_ids):
            requests_to_make.append((student_id, f"Thread-{i % num_threads}"))
        
        print(f"\n🔄 Preparing {len(requests_to_make)} concurrent requests...")
        
        # Run concurrent requests
        start_time = time.time()
        results = []
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            # Submit all requests
            future_to_request = {
                executor.submit(self.make_quest_request, student_id, thread_id): (student_id, thread_id)
                for student_id, thread_id in requests_to_make
            }
            
            # Collect results as they complete
            completed = 0
            for future in as_completed(future_to_request):
                student_id, thread_id = future_to_request[future]
                try:
                    result = future.result()
                    results.append(result)
                    completed += 1
                    
                    if completed % 5 == 0 or completed == len(requests_to_make):
                        print(f"⏳ Completed: {completed}/{len(requests_to_make)}")
                        
                except Exception as e:
                    print(f"💥 Exception for student {student_id}: {e}")
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Analyze results
        self.analyze_results(results, total_duration)
    
    def analyze_results(self, results, total_duration):
        """Analyze and display test results"""
        print("\n" + "=" * 50)
        print("📈 CONCURRENCY TEST RESULTS")
        print("=" * 50)
        
        if not results:
            print("❌ No results to analyze")
            return
        
        # Basic stats
        total_requests = len(results)
        successful_requests = sum(1 for r in results if r['success'])
        failed_requests = total_requests - successful_requests
        
        # Timing stats
        durations = [r['duration'] for r in results if r['duration']]
        avg_duration = sum(durations) / len(durations) if durations else 0
        min_duration = min(durations) if durations else 0
        max_duration = max(durations) if durations else 0
        
        # Throughput
        requests_per_second = total_requests / total_duration if total_duration > 0 else 0
        
        print(f"\n📊 Overall Performance:")
        print(f"   Total Duration: {total_duration:.2f} seconds")
        print(f"   Total Requests: {total_requests}")
        print(f"   Successful: {successful_requests} ({successful_requests/total_requests*100:.1f}%)")
        print(f"   Failed: {failed_requests} ({failed_requests/total_requests*100:.1f}%)")
        print(f"   Throughput: {requests_per_second:.2f} requests/second")
        
        print(f"\n⏱️  Response Times:")
        print(f"   Average: {avg_duration:.3f} seconds")
        print(f"   Minimum: {min_duration:.3f} seconds")
        print(f"   Maximum: {max_duration:.3f} seconds")
        
        # Status code breakdown
        status_codes = {}
        for result in results:
            code = result['status_code'] or 'Error'
            status_codes[code] = status_codes.get(code, 0) + 1
        
        print(f"\n📋 Status Code Breakdown:")
        for code, count in sorted(status_codes.items()):
            print(f"   {code}: {count} requests")
        
        # Error analysis
        errors = [r for r in results if not r['success']]
        if errors:
            print(f"\n❌ Error Analysis:")
            error_types = {}
            for error in errors:
                error_type = error['error'] or f"HTTP {error['status_code']}"
                error_types[error_type] = error_types.get(error_type, 0) + 1
            
            for error_type, count in error_types.items():
                print(f"   {error_type}: {count} occurrences")
        
        # Quest change stats (if successful)
        successful_results = [r for r in results if r['success']]
        if successful_results:
            quest_changes = sum(1 for r in successful_results if r.get('quest_changed'))
            print(f"\n🎮 Quest Changes: {quest_changes}/{len(successful_results)} successful requests")
        
        # Performance percentiles
        if durations:
            sorted_durations = sorted(durations)
            p50 = sorted_durations[int(len(sorted_durations) * 0.5)]
            p90 = sorted_durations[int(len(sorted_durations) * 0.9)]
            p95 = sorted_durations[int(len(sorted_durations) * 0.95)]
            
            print(f"\n📊 Response Time Percentiles:")
            print(f"   50th percentile: {p50:.3f} seconds")
            print(f"   90th percentile: {p90:.3f} seconds")
            print(f"   95th percentile: {p95:.3f} seconds")
        
        print("\n" + "=" * 50)

def main():
    test = ConcurrencyTest()
    test.run_concurrency_test(num_students=100, num_threads=8)

if __name__ == "__main__":
    main()
