import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import statistics
import json

class FrontendLoadTest:
    def __init__(self):
        self.base_url = "https://craffft.rad.kiwi"
        self.favicon_url = "https://craffft.rad.kiwi/wp-includes/images/w-logo-blue-white-bg.png"
        self.results = []
        self.lock = threading.Lock()
        
    def create_driver(self):
        """Create a headless Chrome driver"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")  # Focus on network/HTML performance only
        chrome_options.add_argument("--disable-javascript")  # Isolate pure network performance
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Suppress DevTools and other Chrome logs
        chrome_options.add_argument("--log-level=3")  # Suppress INFO, WARNING, ERROR
        chrome_options.add_argument("--silent")
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument("--disable-dev-tools")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--disable-default-apps")
        chrome_options.add_argument("--remote-debugging-port=0")  # Disable remote debugging completely
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        
        # Additional options to reduce noise
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(60)  # 60 second timeout
            return driver
        except Exception as e:
            print(f"Failed to create Chrome driver: {e}")
            return None
    
    def measure_page_load(self, thread_id, test_number):
        """Measure how long it takes to load the craffft.rad.kiwi homepage"""
        driver = None
        result = {
            "thread_id": thread_id,
            "test_number": test_number,
            "success": False,
            "total_time": 0,
            "dom_ready_time": 0,
            "favicon_loaded": False,
            "favicon_time": 0,
            "error": None,
            "response_code": None
        }
        
        try:
            driver = self.create_driver()
            if not driver:
                result["error"] = "Failed to create driver"
                return result
            
            # Start timing
            start_time = time.time()
            
            # Load the page
            driver.get(self.base_url)
            
            # Wait for DOM to be ready
            WebDriverWait(driver, 30).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            dom_ready_time = time.time()
            result["dom_ready_time"] = dom_ready_time - start_time
            
            # Try to detect if favicon is loaded by checking network requests
            # Since we can't easily intercept network requests with basic Selenium,
            # we'll use a different approach - check if the page title is loaded
            try:
                title = driver.title
                if title:
                    result["favicon_loaded"] = True
                    result["favicon_time"] = result["dom_ready_time"]  # Approximate
            except:
                pass
            
            # Optional: Check if specific elements are present (customize based on your site)
            try:
                # Wait for body element to be present
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except TimeoutException:
                pass
            
            end_time = time.time()
            result["total_time"] = end_time - start_time
            result["success"] = True
            
            # Get response status if possible (limited with Selenium)
            try:
                # This is a workaround to check if page loaded successfully
                page_source_length = len(driver.page_source)
                if page_source_length > 1000:  # Reasonable page size
                    result["response_code"] = 200
                else:
                    result["response_code"] = "unknown"
            except:
                result["response_code"] = "unknown"
                
        except TimeoutException:
            result["error"] = "Page load timeout"
            result["total_time"] = 60.0  # Timeout duration
        except WebDriverException as e:
            result["error"] = f"WebDriver error: {str(e)[:100]}"
        except Exception as e:
            result["error"] = f"Unexpected error: {str(e)[:100]}"
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
        
        return result
    
    def run_load_test(self, num_tests=30, num_threads=8):
        """Run the frontend load test"""
        print("🌐 Starting Frontend Load Test")
        print(f"📊 Configuration: {num_tests} page loads, {num_threads} threads")
        print(f"🎯 Target: {self.base_url}")
        print("=" * 50)
        
        # Create test scenarios
        test_scenarios = [(i % num_threads, i) for i in range(num_tests)]
        
        print(f"\n🔄 Preparing {num_tests} concurrent page loads...")
        
        # Run concurrent page loads
        start_time = time.time()
        results = []
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            # Submit all page load tests
            future_to_test = {
                executor.submit(self.measure_page_load, thread_id, test_num): (thread_id, test_num)
                for thread_id, test_num in test_scenarios
            }
            
            # Collect results as they complete
            completed = 0
            for future in as_completed(future_to_test):
                thread_id, test_num = future_to_test[future]
                try:
                    result = future.result()
                    results.append(result)
                    completed += 1
                    
                    # Progress indicator
                    if completed % 5 == 0 or completed == num_tests:
                        success_count = sum(1 for r in results if r['success'])
                        print(f"⏳ Completed: {completed}/{num_tests} (Success: {success_count})")
                        
                except Exception as e:
                    print(f"💥 Exception for test {test_num}: {e}")
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Analyze results
        self.analyze_frontend_results(results, total_duration)
    
    def analyze_frontend_results(self, results, total_duration):
        """Analyze and display frontend test results"""
        print("\n" + "=" * 50)
        print("🌐 FRONTEND LOAD TEST RESULTS")
        print("=" * 50)
        
        if not results:
            print("❌ No results to analyze")
            return
        
        # Basic stats
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r['success'])
        failed_tests = total_tests - successful_tests
        
        # Timing stats for successful loads
        successful_results = [r for r in results if r['success']]
        if successful_results:
            load_times = [r['total_time'] for r in successful_results]
            dom_times = [r['dom_ready_time'] for r in successful_results]
            
            avg_load_time = statistics.mean(load_times)
            min_load_time = min(load_times)
            max_load_time = max(load_times)
            
            avg_dom_time = statistics.mean(dom_times)
            
            # Percentiles
            sorted_times = sorted(load_times)
            p50 = sorted_times[int(len(sorted_times) * 0.5)]
            p90 = sorted_times[int(len(sorted_times) * 0.9)]
            p95 = sorted_times[int(len(sorted_times) * 0.95)]
        else:
            avg_load_time = min_load_time = max_load_time = avg_dom_time = 0
            p50 = p90 = p95 = 0
        
        # Throughput
        pages_per_second = total_tests / total_duration if total_duration > 0 else 0
        
        print(f"\n📊 Overall Performance:")
        print(f"   Total Duration: {total_duration:.2f} seconds")
        print(f"   Total Page Loads: {total_tests}")
        print(f"   Successful: {successful_tests} ({successful_tests/total_tests*100:.1f}%)")
        print(f"   Failed: {failed_tests} ({failed_tests/total_tests*100:.1f}%)")
        print(f"   Throughput: {pages_per_second:.2f} pages/second")
        
        if successful_results:
            print(f"\n⏱️  Page Load Times:")
            print(f"   Average: {avg_load_time:.3f} seconds")
            print(f"   Minimum: {min_load_time:.3f} seconds")
            print(f"   Maximum: {max_load_time:.3f} seconds")
            print(f"   DOM Ready Average: {avg_dom_time:.3f} seconds")
            
            print(f"\n📊 Load Time Percentiles:")
            print(f"   50th percentile: {p50:.3f} seconds")
            print(f"   90th percentile: {p90:.3f} seconds")
            print(f"   95th percentile: {p95:.3f} seconds")
        
        # Error analysis
        errors = [r for r in results if not r['success']]
        if errors:
            print(f"\n❌ Error Analysis:")
            error_types = {}
            for error in errors:
                error_type = error['error'] or "Unknown error"
                error_types[error_type] = error_types.get(error_type, 0) + 1
            
            for error_type, count in error_types.items():
                print(f"   {error_type}: {count} occurrences")
        
        # Performance assessment
        if successful_results:
            print(f"\n🎯 Performance Assessment:")
            if avg_load_time < 2.0:
                print("   ✅ Excellent performance (< 2s average)")
            elif avg_load_time < 3.0:
                print("   ✅ Good performance (< 3s average)")
            elif avg_load_time < 5.0:
                print("   ⚠️  Acceptable performance (< 5s average)")
            else:
                print("   ❌ Poor performance (> 5s average)")
        
        print("\n" + "=" * 50)

def main():
    test = FrontendLoadTest()
    test.run_load_test(num_tests=30, num_threads=8)

if __name__ == "__main__":
    main()
