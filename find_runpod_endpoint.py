#!/usr/bin/env python3
"""
RunPod Endpoint URL Finder
Helps determine the correct endpoint URL format
"""

import requests
import time

def test_endpoint_formats(endpoint_id):
    """Test different RunPod endpoint URL formats"""
    
    formats_to_try = [
        f"https://{endpoint_id}.runpod.ai",
        f"https://api.runpod.ai/v2/{endpoint_id}",
        f"https://{endpoint_id}.runpod.io", 
        f"https://{endpoint_id}-5000.proxy.runpod.net",
        f"https://{endpoint_id}-8000.proxy.runpod.net",
        f"https://{endpoint_id}.prod.runpod.ai",
        f"https://{endpoint_id}.runpod.net"
    ]
    
    print(f"🔍 Testing endpoint formats for ID: {endpoint_id}")
    print("=" * 50)
    
    for i, url in enumerate(formats_to_try, 1):
        print(f"{i}. Testing: {url}")
        
        try:
            # Try with a short timeout first
            response = requests.get(f"{url}/health", timeout=10)
            print(f"   ✅ SUCCESS! Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   Response: {response.text[:200]}...")
                return url
            elif response.status_code in [404, 405]:
                print(f"   🟡 Endpoint exists but no /health route")
                # Try root path
                try:
                    root_response = requests.get(url, timeout=5)
                    print(f"   Root status: {root_response.status_code}")
                    if root_response.status_code == 200:
                        return url
                except:
                    pass
        except requests.exceptions.ConnectTimeout:
            print(f"   ⏰ Timeout (service might be starting)")
        except requests.exceptions.ConnectionError as e:
            if "getaddrinfo failed" in str(e):
                print(f"   ❌ DNS resolution failed")
            else:
                print(f"   ❌ Connection error: {str(e)[:100]}")
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:100]}")
        
        time.sleep(1)  # Brief pause between requests
    
    print()
    print("❌ None of the standard formats worked.")
    return None

def check_runpod_status():
    """Check if RunPod services are generally accessible"""
    print("🌐 Checking RunPod service accessibility...")
    
    try:
        response = requests.get("https://runpod.ai", timeout=10)
        print(f"   RunPod main site: {response.status_code}")
    except Exception as e:
        print(f"   RunPod main site error: {e}")
    
    try:
        response = requests.get("https://api.runpod.ai", timeout=10)
        print(f"   RunPod API: {response.status_code}")
    except Exception as e:
        print(f"   RunPod API error: {e}")

def main():
    endpoint_id = "nmj1bq1l8kvikn"
    
    print("🚀 RunPod Endpoint URL Finder")
    print("=" * 40)
    
    # First check if RunPod is accessible
    check_runpod_status()
    print()
    
    # Test different URL formats
    working_url = test_endpoint_formats(endpoint_id)
    
    print()
    print("📋 RESULTS:")
    print("-" * 20)
    
    if working_url:
        print(f"✅ Found working endpoint: {working_url}")
        print()
        print("🧪 Now test with:")
        print(f"   python test_sample_data.py")
        print(f"   (Use: {working_url})")
    else:
        print("❌ No working endpoint found.")
        print()
        print("🔧 Possible issues:")
        print("1. Endpoint is still starting up (wait 2-3 minutes)")
        print("2. Endpoint might be stopped/paused")
        print("3. Different URL format needed")
        print("4. RunPod ID might be incorrect")
        print()
        print("📖 Check your RunPod dashboard for:")
        print("   - Endpoint status (should be 'Running')")
        print("   - Exact endpoint URL")
        print("   - Logs for startup errors")
        print()
        print("💡 Alternative: Check RunPod dashboard 'Endpoints' tab")
        print("   Copy the exact URL provided there")

if __name__ == "__main__":
    main()