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
import psutil
import requests

class FrontendPerformanceAnalyzer:
    def __init__(self):
        self.base_url = "https://craffft.rad.kiwi"
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
            driver.set_page_load_timeout(60)
            return driver
        except Exception as e:
            print(f"Failed to create Chrome driver: {e}")
            return None
    
    def measure_network_only(self):
        """Measure just the network request time without browser overhead"""
        try:
            start_time = time.time()
            response = requests.get(self.base_url, timeout=30)
            end_time = time.time()
            
            return {
                "success": response.status_code == 200,
                "network_time": end_time - start_time,
                "status_code": response.status_code,
                "content_length": len(response.content)
            }
        except Exception as e:
            return {
                "success": False,
                "network_time": 0,
                "error": str(e)
            }
    
    def measure_system_resources(self):
        """Get current system resource usage"""
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_available_gb": psutil.virtual_memory().available / (1024**3),
            "memory_used_gb": psutil.virtual_memory().used / (1024**3)
        }
    
    def measure_page_load_with_monitoring(self, thread_id, test_number):
        """Measure page load with system monitoring"""
        driver = None
        result = {
            "thread_id": thread_id,
            "test_number": test_number,
            "success": False,
            "total_time": 0,
            "dom_ready_time": 0,
            "network_only_time": 0,
            "browser_overhead": 0,
            "system_before": {},
            "system_after": {},
            "error": None
        }
        
        try:
            # Measure system resources before
            result["system_before"] = self.measure_system_resources()
            
            # Measure network-only time first
            network_result = self.measure_network_only()
            result["network_only_time"] = network_result.get("network_time", 0)
            
            # Now measure full browser load
            driver = self.create_driver()
            if not driver:
                result["error"] = "Failed to create driver"
                return result
            
            # Start timing full browser load
            browser_start_time = time.time()
            
            # Load the page
            driver.get(self.base_url)
            
            # Wait for DOM to be ready
            WebDriverWait(driver, 30).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            dom_ready_time = time.time()
            result["dom_ready_time"] = dom_ready_time - browser_start_time
            
            # Optional: Wait a bit more for any async resources
            time.sleep(0.5)
            
            end_time = time.time()
            result["total_time"] = end_time - browser_start_time
            result["success"] = True
            
            # Calculate browser overhead
            result["browser_overhead"] = result["total_time"] - result["network_only_time"]
            
            # Measure system resources after
            result["system_after"] = self.measure_system_resources()
                
        except TimeoutException:
            result["error"] = "Page load timeout"
            result["total_time"] = 60.0
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
    
    def run_performance_comparison(self, num_tests=20, max_threads=8):
        """Run performance tests comparing different thread counts"""
        print("🔍 Frontend Performance Analysis")
        print("=" * 60)
        
        # Test different thread counts to see impact of local resources
        thread_counts = [1, 2, 4, max_threads]
        
        for thread_count in thread_counts:
            print(f"\n🧪 Testing with {thread_count} concurrent browser(s)")
            print(f"📊 Running {num_tests} page loads...")
            
            # Measure initial system state
            initial_resources = self.measure_system_resources()
            print(f"💻 Initial CPU: {initial_resources['cpu_percent']:.1f}%, "
                  f"Memory: {initial_resources['memory_percent']:.1f}%")
            
            start_time = time.time()
            results = []
            
            with ThreadPoolExecutor(max_workers=thread_count) as executor:
                # Submit tests
                future_to_test = {
                    executor.submit(self.measure_page_load_with_monitoring, i % thread_count, i): i
                    for i in range(num_tests)
                }
                
                # Collect results
                for future in as_completed(future_to_test):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        print(f"💥 Exception: {e}")
            
            end_time = time.time()
            total_duration = end_time - start_time
            
            # Analyze this thread count's results
            self.analyze_thread_performance(results, thread_count, total_duration)
    
    def analyze_thread_performance(self, results, thread_count, total_duration):
        """Analyze performance for a specific thread count"""
        if not results:
            return
        
        successful_results = [r for r in results if r['success']]
        if not successful_results:
            print(f"❌ No successful results for {thread_count} threads")
            return
        
        # Calculate averages
        avg_total = statistics.mean([r['total_time'] for r in successful_results])
        avg_network = statistics.mean([r['network_only_time'] for r in successful_results])
        avg_overhead = statistics.mean([r['browser_overhead'] for r in successful_results])
        
        # System resource analysis
        cpu_before = statistics.mean([r['system_before']['cpu_percent'] for r in successful_results])
        cpu_after = statistics.mean([r['system_after']['cpu_percent'] for r in successful_results])
        memory_before = statistics.mean([r['system_before']['memory_percent'] for r in successful_results])
        memory_after = statistics.mean([r['system_after']['memory_percent'] for r in successful_results])
        
        # Calculate efficiency
        throughput = len(results) / total_duration
        network_percentage = (avg_network / avg_total * 100) if avg_total > 0 else 0
        overhead_percentage = (avg_overhead / avg_total * 100) if avg_total > 0 else 0
        
        print(f"\n📊 Results for {thread_count} thread(s):")
        print(f"   Successful loads: {len(successful_results)}/{len(results)}")
        print(f"   Average total time: {avg_total:.3f}s")
        print(f"   Average network time: {avg_network:.3f}s ({network_percentage:.1f}%)")
        print(f"   Average browser overhead: {avg_overhead:.3f}s ({overhead_percentage:.1f}%)")
        print(f"   Throughput: {throughput:.2f} pages/second")
        
        print(f"\n💻 System Impact:")
        print(f"   CPU usage: {cpu_before:.1f}% → {cpu_after:.1f}% (Δ{cpu_after-cpu_before:+.1f}%)")
        print(f"   Memory usage: {memory_before:.1f}% → {memory_after:.1f}% (Δ{memory_after-memory_before:+.1f}%)")
        
        # Performance assessment
        if overhead_percentage > 60:
            print(f"   ⚠️  High browser overhead ({overhead_percentage:.1f}%) - local bottleneck likely")
        elif overhead_percentage > 40:
            print(f"   ⚠️  Moderate browser overhead ({overhead_percentage:.1f}%) - some local impact")
        else:
            print(f"   ✅ Low browser overhead ({overhead_percentage:.1f}%) - network is main factor")
    
    def run_baseline_network_test(self, num_requests=50):
        """Run a pure network test to establish baseline"""
        print(f"\n🌐 Baseline Network Test ({num_requests} requests)")
        print("-" * 50)
        
        start_time = time.time()
        results = []
        
        for i in range(num_requests):
            result = self.measure_network_only()
            results.append(result)
            if (i + 1) % 10 == 0:
                print(f"   Completed: {i + 1}/{num_requests}")
        
        end_time = time.time()
        
        successful_results = [r for r in results if r['success']]
        if successful_results:
            network_times = [r['network_time'] for r in successful_results]
            avg_network = statistics.mean(network_times)
            min_network = min(network_times)
            max_network = max(network_times)
            
            print(f"\n📊 Pure Network Performance:")
            print(f"   Average: {avg_network:.3f}s")
            print(f"   Range: {min_network:.3f}s - {max_network:.3f}s")
            print(f"   Throughput: {len(results)/(end_time-start_time):.2f} requests/second")
            
            return avg_network
        return 0

def main():
    analyzer = FrontendPerformanceAnalyzer()
    
    # First, establish network baseline
    baseline_network_time = analyzer.run_baseline_network_test(50)
    
    # Then run browser tests with different concurrency levels
    analyzer.run_performance_comparison(num_tests=20, max_threads=8)
    
    print(f"\n" + "=" * 60)
    print("🎯 PERFORMANCE ANALYSIS SUMMARY")
    print("=" * 60)
    print(f"📡 Pure network baseline: {baseline_network_time:.3f}s")
    print("\n💡 Interpretation Guide:")
    print("   • Network % = Time spent on actual site performance")
    print("   • Browser overhead % = Time spent on local computer processing")
    print("   • High CPU/Memory delta = Your PC is the bottleneck")
    print("   • Low overhead % = Site performance is the main factor")

if __name__ == "__main__":
    main()
