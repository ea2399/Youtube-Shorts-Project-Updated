#!/bin/bash
# YouTube Shorts Generator - RunPod Endpoint Testing Script
# Usage: ./test_endpoint.sh ENDPOINT_ID [CONFIG_FILE] [API_KEY]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENDPOINT_ID=""
CONFIG_FILE="payloads/torah_lecture_basic.json"
API_KEY="${RUNPOD_API_KEY}"
ASYNC_MODE=false
TIMEOUT=600

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Function to display help
show_help() {
    echo "YouTube Shorts Generator - RunPod Testing Script"
    echo ""
    echo "Usage: $0 ENDPOINT_ID [OPTIONS]"
    echo ""
    echo "Arguments:"
    echo "  ENDPOINT_ID        RunPod endpoint ID (required)"
    echo ""
    echo "Options:"
    echo "  -c, --config FILE  Configuration file (default: payloads/torah_lecture_basic.json)"
    echo "  -k, --api-key KEY  RunPod API key (or use RUNPOD_API_KEY env var)"
    echo "  -a, --async        Use async mode"
    echo "  -t, --timeout SEC  Timeout in seconds (default: 600)"
    echo "  -h, --help         Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 abc123def456"
    echo "  $0 abc123def456 --config payloads/english_shiur_quality.json"
    echo "  $0 abc123def456 --async --timeout 900"
    echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -k|--api-key)
            API_KEY="$2"
            shift 2
            ;;
        -a|--async)
            ASYNC_MODE=true
            shift
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        -*)
            print_error "Unknown option $1"
            show_help
            exit 1
            ;;
        *)
            if [[ -z "$ENDPOINT_ID" ]]; then
                ENDPOINT_ID="$1"
            else
                print_error "Unexpected argument: $1"
                show_help
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate required parameters
if [[ -z "$ENDPOINT_ID" ]]; then
    print_error "Endpoint ID is required"
    show_help
    exit 1
fi

if [[ -z "$API_KEY" ]]; then
    print_error "RunPod API key required. Set RUNPOD_API_KEY environment variable or use --api-key"
    exit 1
fi

# Check if config file exists
if [[ ! -f "$CONFIG_FILE" ]]; then
    print_error "Configuration file not found: $CONFIG_FILE"
    exit 1
fi

# Check if jq is available for JSON processing
if ! command -v jq &> /dev/null; then
    print_warning "jq not found. Install jq for better JSON formatting: sudo apt-get install jq"
    JQ_AVAILABLE=false
else
    JQ_AVAILABLE=true
fi

print_info "YouTube Shorts Generator - RunPod Test"
echo "=" * 50
print_info "Endpoint ID: $ENDPOINT_ID"
print_info "Config file: $CONFIG_FILE"
print_info "Async mode: $ASYNC_MODE"
print_info "Timeout: ${TIMEOUT}s"
echo ""

# Read and validate config file
CONFIG_CONTENT=$(cat "$CONFIG_FILE")
if [[ $JQ_AVAILABLE == true ]]; then
    # Validate JSON and pretty print
    if ! echo "$CONFIG_CONTENT" | jq . > /dev/null 2>&1; then
        print_error "Invalid JSON in config file"
        exit 1
    fi
    
    print_info "Configuration:"
    echo "$CONFIG_CONTENT" | jq .
else
    print_info "Configuration loaded from $CONFIG_FILE"
fi

# Construct API URL
BASE_URL="https://api.runpod.ai/v2/${ENDPOINT_ID}/run"
if [[ "$ASYNC_MODE" == true ]]; then
    BASE_URL="${BASE_URL}Async"
fi

print_info "API URL: $BASE_URL"
echo ""

# Make the request
print_info "🚀 Sending request to RunPod..."
START_TIME=$(date +%s)

RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d "$CONFIG_CONTENT" \
    "$BASE_URL")

# Extract HTTP status code and response body
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$RESPONSE" | head -n -1)

if [[ "$HTTP_CODE" != "200" ]]; then
    print_error "HTTP request failed with status: $HTTP_CODE"
    echo "Response: $RESPONSE_BODY"
    exit 1
fi

print_status "Request sent successfully"

# Handle async vs sync responses
if [[ "$ASYNC_MODE" == true ]]; then
    # Extract job ID
    if [[ $JQ_AVAILABLE == true ]]; then
        JOB_ID=$(echo "$RESPONSE_BODY" | jq -r '.id')
    else
        # Simple extraction without jq
        JOB_ID=$(echo "$RESPONSE_BODY" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
    fi
    
    if [[ -z "$JOB_ID" || "$JOB_ID" == "null" ]]; then
        print_error "No job ID returned"
        echo "Response: $RESPONSE_BODY"
        exit 1
    fi
    
    print_status "Job submitted: $JOB_ID"
    print_info "⏳ Polling for results..."
    
    # Poll for completion
    STATUS_URL="https://api.runpod.ai/v2/${ENDPOINT_ID}/status/${JOB_ID}"
    
    while true; do
        sleep 5
        
        STATUS_RESPONSE=$(curl -s -w "\n%{http_code}" \
            -H "Authorization: Bearer $API_KEY" \
            "$STATUS_URL")
        
        STATUS_HTTP_CODE=$(echo "$STATUS_RESPONSE" | tail -n1)
        STATUS_BODY=$(echo "$STATUS_RESPONSE" | head -n -1)
        
        if [[ "$STATUS_HTTP_CODE" != "200" ]]; then
            print_error "Status check failed: $STATUS_HTTP_CODE"
            echo "Response: $STATUS_BODY"
            exit 1
        fi
        
        if [[ $JQ_AVAILABLE == true ]]; then
            STATUS=$(echo "$STATUS_BODY" | jq -r '.status')
        else
            STATUS=$(echo "$STATUS_BODY" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
        fi
        
        print_info "Status: $STATUS"
        
        if [[ "$STATUS" == "COMPLETED" || "$STATUS" == "FAILED" ]]; then
            FINAL_RESPONSE="$STATUS_BODY"
            break
        elif [[ "$STATUS" == "IN_QUEUE" || "$STATUS" == "IN_PROGRESS" ]]; then
            CURRENT_TIME=$(date +%s)
            ELAPSED=$((CURRENT_TIME - START_TIME))
            if [[ $ELAPSED -gt $TIMEOUT ]]; then
                print_error "Timeout reached after ${TIMEOUT}s"
                exit 1
            fi
        else
            print_error "Unknown status: $STATUS"
            exit 1
        fi
    done
else
    FINAL_RESPONSE="$RESPONSE_BODY"
fi

# Calculate total time
END_TIME=$(date +%s)
TOTAL_TIME=$((END_TIME - START_TIME))

print_status "Request completed in ${TOTAL_TIME}s"
echo ""

# Display results
if [[ $JQ_AVAILABLE == true ]]; then
    # Check if response contains output (success) or error
    if echo "$FINAL_RESPONSE" | jq -e '.output' > /dev/null 2>&1; then
        print_status "🎉 SUCCESS!"
        echo "=" * 50
        
        # Extract key information
        CLIPS_GENERATED=$(echo "$FINAL_RESPONSE" | jq -r '.output.clips_generated // 0')
        TRANSCRIPTION_SEGMENTS=$(echo "$FINAL_RESPONSE" | jq -r '.output.transcription.segments // 0')
        LANGUAGE=$(echo "$FINAL_RESPONSE" | jq -r '.output.transcription.language // "Unknown"')
        METHOD=$(echo "$FINAL_RESPONSE" | jq -r '.output.analysis.method // "Unknown"')
        
        echo "📊 Clips generated: $CLIPS_GENERATED"
        echo "🎬 Transcription: $TRANSCRIPTION_SEGMENTS segments"
        echo "🌐 Language: $LANGUAGE"
        echo "🧠 Analysis method: $METHOD"
        
        # Show themes
        THEMES=$(echo "$FINAL_RESPONSE" | jq -r '.output.analysis.themes[]?' | head -3 | tr '\n' ', ' | sed 's/,$//')
        if [[ -n "$THEMES" ]]; then
            echo "📋 Main themes: $THEMES"
        fi
        
        # Show topic
        TOPIC=$(echo "$FINAL_RESPONSE" | jq -r '.output.analysis.overall_topic // ""')
        if [[ -n "$TOPIC" && "$TOPIC" != "" ]]; then
            echo "🎯 Topic: $TOPIC"
        fi
        
        echo ""
        echo "🎬 Generated Clips:"
        echo "$(echo "$FINAL_RESPONSE" | jq -r '.output.clips[] | "\(.index). \(.title) (\(.duration)s) - Score: \(.score)/10"')"
        
    elif echo "$FINAL_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
        print_error "🔥 FAILED!"
        echo "=" * 50
        ERROR_MSG=$(echo "$FINAL_RESPONSE" | jq -r '.error')
        echo "Error: $ERROR_MSG"
        
        # Show traceback if available
        if echo "$FINAL_RESPONSE" | jq -e '.traceback' > /dev/null 2>&1; then
            echo ""
            echo "Traceback:"
            echo "$FINAL_RESPONSE" | jq -r '.traceback'
        fi
    else
        print_warning "Unexpected response format"
    fi
    
    # Save full response
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    OUTPUT_FILE="runpod_response_${TIMESTAMP}.json"
    echo "$FINAL_RESPONSE" | jq . > "$OUTPUT_FILE"
    print_info "💾 Full response saved to: $OUTPUT_FILE"
    
else
    # Without jq, just show raw response
    print_info "Response (install jq for better formatting):"
    echo "$FINAL_RESPONSE"
fi

print_status "🎉 Test completed!"