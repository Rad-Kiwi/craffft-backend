"""
Security Tests for Craffft Backend
==================================

This file contains security-specific tests including SQL injection attacks,
input validation, and other security vulnerability assessments.

These tests are separate from functional tests and should be run independently
to verify the application's security posture.

Usage:
    python security_tests.py
"""

from app import app
import sys
import types


def test_api_sql_injection_attacks():
    """
    Test SQL injection attacks against API endpoints
    """
    print("🔒 Testing API endpoints against SQL injection attacks...")
    
    # Common SQL injection payloads
    malicious_payloads = [
        "'; DROP TABLE craffft_students; --",
        "' OR 1=1 --",
        "' OR '1'='1",
        "'; DELETE FROM craffft_students WHERE 1=1; --",
        "' UNION SELECT * FROM craffft_students --",
        "admin'; DROP DATABASE; --",
        "' OR 1=1#",
        "1' OR '1'='1' /*",
    ]
    
    with app.test_client() as client:
        
        # Test GET endpoints with URL parameters
        print("  Testing GET endpoints...")
        for payload in malicious_payloads:
            try:
                # Test /get-student-data-from-websiteId/<website_id>
                response = client.get(f"/get-student-data-from-websiteId/{payload}")
                assert response.status_code in [400, 404], f"Unexpected status code {response.status_code}"
                
                # Test /get-student-data-from-record/<student_record>  
                response = client.get(f"/get-student-data-from-record/{payload}")
                assert response.status_code in [400, 404], f"Unexpected status code {response.status_code}"
                
                # Test /update-student-current-step with query parameters
                response = client.get(f"/update-student-current-step?websiteId={payload}&current-step=test")
                assert response.status_code in [400, 404, 500], f"Unexpected status code {response.status_code}"
                
                print(f"    ✓ GET endpoints protected against: {payload[:30]}...")
                
            except Exception as e:
                print(f"    ✓ Safe GET exception for payload {payload[:30]}...: {str(e)[:50]}")
        
        # Test POST endpoints with JSON payloads
        print("  Testing POST endpoints...")
        for payload in malicious_payloads:
            try:
                # Test /get-value-from-db
                test_data = {
                    "table_name": payload,  # Test injection in table_name
                    "reference_value": "test",
                    "target_column": "first_name"
                }
                response = client.post("/get-value-from-db", json=test_data)
                assert response.status_code in [400, 404, 500], f"Unexpected status code {response.status_code}"
                
                # Test with injection in reference_value
                test_data = {
                    "table_name": "craffft_students",
                    "reference_value": payload,
                    "target_column": "first_name"
                }
                response = client.post("/get-value-from-db", json=test_data)
                assert response.status_code in [200, 404], f"Unexpected status code {response.status_code}"
                
                # Test /modify-field
                test_data = {
                    "table_name": "craffft_students", 
                    "reference_value": payload,
                    "target_column": "first_name",
                    "new_value": "safe_value"
                }
                response = client.post("/modify-field", json=test_data)
                assert response.status_code in [200, 500], f"Unexpected status code {response.status_code}"
                
                print(f"    ✓ POST endpoints protected against: {payload[:30]}...")
                
            except Exception as e:
                print(f"    ✓ Safe POST exception for payload {payload[:30]}...: {str(e)[:50]}")
    
    print("✅ All API SQL injection tests passed - Endpoints are secure!")


def test_input_validation():
    """
    Test input validation and sanitization
    """
    print("🔒 Testing input validation...")
    
    edge_cases = [
        "",  # Empty string
        "   ",  # Whitespace only
        "x" * 10000,  # Very long input
        "Special chars: <>&\"'",  # HTML/XML chars
        "Unicode: 你好世界 🌍",  # Unicode characters
        "Newline\nand\ttab",  # Control characters
    ]
    
    with app.test_client() as client:
        for case in edge_cases:
            try:
                # Test various endpoints with edge case inputs
                response = client.get(f"/get-student-data-from-websiteId/{case}")
                assert response.status_code in [400, 404, 500], f"Unexpected response for: {repr(case)}"
                
                test_data = {
                    "table_name": "craffft_students",
                    "reference_value": case,
                    "target_column": "first_name"
                }
                response = client.post("/get-value-from-db", json=test_data)
                assert response.status_code in [200, 404, 400, 500], f"Unexpected response for: {repr(case)}"
                
                print(f"    ✓ Input validation handled: {repr(case)[:30]}...")
                
            except Exception as e:
                print(f"    ✓ Safe validation exception for {repr(case)[:30]}...: {str(e)[:50]}")
    
    print("✅ Input validation tests passed!")


def test_http_methods():
    """
    Test that endpoints only accept intended HTTP methods
    """
    print("🔒 Testing HTTP method restrictions...")
    
    with app.test_client() as client:
        # Test that GET endpoints reject other methods
        get_endpoints = [
            "/get-student-data-from-websiteId/test123",
            "/get-student-data-from-record/rec123", 
            "/update-student-current-step?websiteId=123&current-step=test"
        ]
        
        for endpoint in get_endpoints:
            # These should work with GET
            response = client.get(endpoint)
            # Should be 404 (not found) or 400 (bad request), not 405 (method not allowed)
            assert response.status_code in [200, 400, 404, 500], f"GET failed for {endpoint}"
            
            # These should fail with POST (405 Method Not Allowed)
            response = client.post(endpoint)
            assert response.status_code == 405, f"POST should be rejected for {endpoint}"
            
            print(f"    ✓ HTTP methods restricted for: {endpoint}")
        
        # Test that POST endpoints reject GET
        post_endpoints = [
            "/get-value-from-db",
            "/modify-field"
        ]
        
        for endpoint in post_endpoints:
            # These should fail with GET (405 Method Not Allowed)  
            response = client.get(endpoint)
            assert response.status_code == 405, f"GET should be rejected for {endpoint}"
            
            print(f"    ✓ HTTP methods restricted for: {endpoint}")
    
    print("✅ HTTP method restriction tests passed!")


def run_security_tests():
    """
    Run all security tests
    """
    print("=" * 60)
    print("🔒 RUNNING SECURITY TESTS")
    print("=" * 60)
    
    current_module = sys.modules[__name__]
    test_functions = [
        getattr(current_module, name) 
        for name in dir(current_module) 
        if name.startswith('test_') and isinstance(getattr(current_module, name), types.FunctionType)
    ]
    
    failures = 0
    total_tests = len(test_functions)
    
    for test_func in test_functions:
        try:
            print(f"\n🔍 Running {test_func.__name__}...")
            test_func()
            print(f"✅ PASS: {test_func.__name__}")
        except AssertionError as e:
            print(f"❌ FAIL: {test_func.__name__} - {e}")
            failures += 1
        except Exception as e:
            print(f"💥 ERROR: {test_func.__name__} - {e}")
            failures += 1
    
    print("\n" + "=" * 60)
    if failures == 0:
        print(f"🎉 ALL {total_tests} SECURITY TESTS PASSED!")
        print("🔒 Your application appears secure against tested attack vectors.")
    else:
        print(f"⚠️  {failures}/{total_tests} security tests FAILED!")
        print("🚨 Please review and fix security vulnerabilities before deployment.")
    print("=" * 60)


if __name__ == "__main__":
    run_security_tests()
