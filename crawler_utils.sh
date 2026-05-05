#!/bin/bash

# =============================================================================
# Distributed Web Crawler - Shell Utilities
# Demonstrates wget/curl, awk/sed, and jq for testing, log processing, and JSON extraction
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REDIS_HOST="localhost"
REDIS_PORT="6379"
LOG_FILE="crawler.log"
JSON_LOG_FILE="crawler.json"

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

print_header() {
    echo -e "${BLUE}============================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# =============================================================================
# NETWORK TESTING UTILITIES (curl/wget)
# =============================================================================

test_endpoint() {
    local url="$1"
    local method="${2:-GET}"
    
    print_header "Testing Endpoint: $url"
    
    print_info "Testing HTTP $method request to $url"
    
    if command -v curl >/dev/null 2>&1; then
        echo -e "${BLUE}Using curl:${NC}"
        curl -w "\nHTTP Status: %{http_code}\nTime: %{time_total}s\nSize: %{size_download} bytes\n" \
             -o /dev/null -s "$url"
        print_success "curl test completed"
    elif command -v wget >/dev/null 2>&1; then
        echo -e "${BLUE}Using wget:${NC}"
        wget --spider --server-response "$url" 2>&1 | grep -E "HTTP|Length"
        print_success "wget test completed"
    else
        print_error "Neither curl nor wget found"
        return 1
    fi
}

fetch_robots_txt() {
    local domain="$1"
    
    print_header "Fetching robots.txt for $domain"
    
    if [[ ! "$domain" =~ ^https?:// ]]; then
        domain="https://$domain"
    fi
    
    local robots_url="${domain}/robots.txt"
    
    print_info "Fetching: $robots_url"
    
    if curl -s "$robots_url" | head -20; then
        print_success "robots.txt fetched successfully"
    else
        print_error "Failed to fetch robots.txt"
    fi
}

test_crawler_access() {
    local url="$1"
    
    print_header "Testing Crawler Access"
    
    print_info "Testing crawler user-agent access to $url"
    
    curl -A "DistributedCrawler/1.0 (educational project)" \
         -w "\nHTTP Status: %{http_code}\nContent-Type: %{content_type}\n" \
         -o /dev/null -s "$url"
    
    print_success "Crawler access test completed"
}

# =============================================================================
# LOG PROCESSING UTILITIES (awk/sed)
# =============================================================================

count_successful_crawls() {
    local log_file="$1"
    
    print_header "Counting Successful Crawls"
    
    if [[ ! -f "$log_file" ]]; then
        print_error "Log file not found: $log_file"
        return 1
    fi
    
    print_info "Analyzing log file: $log_file"
    
    # Count successful crawls using awk
    local success_count=$(awk '/SUCCESS|completed/ {count++} END {print count+0}' "$log_file")
    local error_count=$(awk '/ERROR|failed/ {count++} END {print count+0}' "$log_file")
    local total_count=$(awk '{count++} END {print count}' "$log_file")
    
    echo -e "${GREEN}Successful crawls: $success_count${NC}"
    echo -e "${RED}Failed crawls: $error_count${NC}"
    echo -e "${BLUE}Total log entries: $total_count${NC}"
    
    if [[ $success_count -gt 0 ]]; then
        local success_rate=$(echo "scale=2; $success_count * 100 / ($success_count + $error_count)" | bc -l 2>/dev/null || echo "N/A")
        echo -e "${YELLOW}Success rate: ${success_rate}%${NC}"
    fi
}

extract_timestamps() {
    local log_file="$1"
    local format="${2:-standard}"
    
    print_header "Extracting Timestamps"
    
    if [[ ! -f "$log_file" ]]; then
        print_error "Log file not found: $log_file"
        return 1
    fi
    
    case "$format" in
        "standard")
            print_info "Extracting standard timestamps (YYYY-MM-DD HH:MM:SS)"
            awk '/[0-9]{4}-[0-9]{2}-[0-9]{2}/ {match($0, /[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}/, arr); print arr[0]}' "$log_file" | head -10
            ;;
        "iso")
            print_info "Extracting ISO timestamps (YYYY-MM-DDTHH:MM:SS)"
            awk '/[0-9]{4}-[0-9]{2}-[0-9]{2}T/ {match($0, /[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}/, arr); print arr[0]}' "$log_file" | head -10
            ;;
        "unix")
            print_info "Extracting Unix timestamps"
            awk '/\b[0-9]{10}\b/ {match($0, /\b[0-9]{10}\b/, arr); print arr[0]}' "$log_file" | head -10
            ;;
        *)
            print_error "Unknown format: $format (use: standard, iso, unix)"
            return 1
            ;;
    esac
}

filter_log_by_level() {
    local log_file="$1"
    local level="$2"
    
    print_header "Filtering Log by Level: $level"
    
    if [[ ! -f "$log_file" ]]; then
        print_error "Log file not found: $log_file"
        return 1
    fi
    
    case "$level" in
        "ERROR"|"error")
            awk '/ERROR|error|failed|FAILED/ {print NR ": " $0}' "$log_file" | head -20
            ;;
        "WARNING"|"warning")
            awk '/WARNING|warning|WARN/ {print NR ": " $0}' "$log_file" | head -20
            ;;
        "INFO"|"info")
            awk '/INFO|info|SUCCESS/ {print NR ": " $0}' "$log_file" | head -20
            ;;
        *)
            print_error "Unknown level: $level (use: ERROR, WARNING, INFO)"
            return 1
            ;;
    esac
}

replace_timestamps() {
    local log_file="$1"
    local replacement="$2"
    
    print_header "Replacing Timestamps"
    
    if [[ ! -f "$log_file" ]]; then
        print_error "Log file not found: $log_file"
        return 1
    fi
    
    print_info "Replacing timestamps with: $replacement"
    
    # Create backup
    cp "$log_file" "${log_file}.backup"
    
    # Replace timestamps using sed
    sed -i.bak "s/[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\} [0-9]\{2\}:[0-9]\{2\}:[0-9]\{2\}/$replacement/g" "$log_file"
    
    print_success "Timestamps replaced. Original backed up as ${log_file}.backup"
}

# =============================================================================
# JSON PROCESSING UTILITIES (jq)
# =============================================================================

extract_crawl_errors() {
    local json_file="$1"
    
    print_header "Extracting Crawl Errors from JSON"
    
    if [[ ! -f "$json_file" ]]; then
        print_error "JSON file not found: $json_file"
        return 1
    fi
    
    if ! command -v jq >/dev/null 2>&1; then
        print_error "jq not found. Install with: brew install jq"
        return 1
    fi
    
    print_info "Extracting URLs that resulted in CRAWL_ERROR"
    
    jq -r '.[] | select(.event_type == "CRAWL_ERROR") | .data.url' "$json_file" | head -10
}

extract_worker_stats() {
    local json_file="$1"
    
    print_header "Extracting Worker Statistics"
    
    if [[ ! -f "$json_file" ]]; then
        print_error "JSON file not found: $json_file"
        return 1
    fi
    
    if ! command -v jq >/dev/null 2>&1; then
        print_error "jq not found. Install with: brew install jq"
        return 1
    fi
    
    print_info "Worker activity summary:"
    
    jq -r '
        .[] | 
        select(.event_type | startswith("WORKER_")) | 
        "\(.event_type): \(.data.worker_id // "unknown") - \(.message)"
    ' "$json_file" | sort | uniq -c | sort -nr
}

filter_json_by_time() {
    local json_file="$1"
    local time_range="$2"
    
    print_header "Filtering JSON by Time Range: $time_range"
    
    if [[ ! -f "$json_file" ]]; then
        print_error "JSON file not found: $json_file"
        return 1
    fi
    
    if ! command -v jq >/dev/null 2>&1; then
        print_error "jq not found. Install with: brew install jq"
        return 1
    fi
    
    case "$time_range" in
        "last_hour")
            local one_hour_ago=$(date -d "1 hour ago" -Iseconds 2>/dev/null || date -v-1H -Iseconds)
            jq --arg timestamp "$one_hour_ago" '
                select(.datetime >= $timestamp)
            ' "$json_file" | head -20
            ;;
        "today")
            local today=$(date -I)
            jq --arg date "$today" '
                select(.datetime | startswith($date))
            ' "$json_file" | head -20
            ;;
        *)
            print_error "Unknown time range: $time_range (use: last_hour, today)"
            return 1
            ;;
    esac
}

summarize_json_logs() {
    local json_file="$1"
    
    print_header "JSON Log Summary"
    
    if [[ ! -f "$json_file" ]]; then
        print_error "JSON file not found: $json_file"
        return 1
    fi
    
    if ! command -v jq >/dev/null 2>&1; then
        print_error "jq not found. Install with: brew install jq"
        return 1
    fi
    
    print_info "Event type distribution:"
    jq -r '.event_type' "$json_file" | sort | uniq -c | sort -nr
    
    echo
    print_info "Error events:"
    jq -r 'select(.event_type == "CRAWL_ERROR") | .data.url' "$json_file" | wc -l | xargs echo "Total errors:"
    
    echo
    print_info "Most recent activity:"
    jq -r '.datetime + " " + .event_type' "$json_file" | tail -5
}

# =============================================================================
# REDIS UTILITIES
# =============================================================================

check_redis_status() {
    print_header "Redis Status Check"
    
    if command -v redis-cli >/dev/null 2>&1; then
        if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping >/dev/null 2>&1; then
            print_success "Redis is running and accessible"
            
            # Get Redis info
            local info=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" info server 2>/dev/null | head -5)
            echo -e "${BLUE}Redis Info:${NC}"
            echo "$info"
            
            # Check crawler keys
            local crawler_keys=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" keys "*crawler*" 2>/dev/null | wc -l)
            echo -e "${BLUE}Crawler-related keys: $crawler_keys${NC}"
        else
            print_error "Redis is not accessible"
            return 1
        fi
    else
        print_error "redis-cli not found"
        return 1
    fi
}

clear_redis_data() {
    local pattern="$1"
    
    print_header "Clearing Redis Data"
    
    if command -v redis-cli >/dev/null 2>&1; then
        if [[ -z "$pattern" ]]; then
            pattern="*"
        fi
        
        print_info "Clearing keys matching: $pattern"
        
        local keys=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" keys "$pattern" 2>/dev/null)
        
        if [[ -n "$keys" ]]; then
            echo "$keys" | xargs redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" del
            print_success "Redis data cleared"
        else
            print_info "No keys found matching pattern: $pattern"
        fi
    else
        print_error "redis-cli not found"
        return 1
    fi
}

# =============================================================================
# DEMONSTRATION FUNCTIONS
# =============================================================================

demo_all() {
    print_header "Complete Shell Utilities Demo"
    
    echo -e "${YELLOW}This demo will test various shell utilities with the crawler.${NC}"
    echo
    
    # Test network utilities
    test_endpoint "https://httpbin.org/status/200"
    echo
    
    test_endpoint "https://arxiv.org" "HEAD"
    echo
    
    fetch_robots_txt "arxiv.org"
    echo
    
    # Test log processing (create sample log if needed)
    if [[ ! -f "$LOG_FILE" ]]; then
        print_info "Creating sample log file..."
        cat > "$LOG_FILE" << 'EOF'
2024-01-01 10:00:01 INFO: Starting crawler
2024-01-01 10:00:02 SUCCESS: Crawled https://example.com
2024-01-01 10:00:03 ERROR: Failed to crawl https://blocked.com
2024-01-01 10:00:04 INFO: Worker 1 started
2024-01-01 10:00:05 SUCCESS: Crawled https://test.com
2024-01-01 10:00:06 ERROR: Timeout on https://slow.com
EOF
    fi
    
    count_successful_crawls "$LOG_FILE"
    echo
    
    extract_timestamps "$LOG_FILE" "standard"
    echo
    
    # Test JSON processing (create sample JSON if needed)
    if [[ ! -f "$JSON_LOG_FILE" ]]; then
        print_info "Creating sample JSON log file..."
        cat > "$JSON_LOG_FILE" << 'EOF'
[
  {"datetime": "2024-01-01T10:00:01Z", "event_type": "CRAWL_START", "data": {"url": "https://example.com"}},
  {"datetime": "2024-01-01T10:00:02Z", "event_type": "CRAWL_ERROR", "data": {"url": "https://blocked.com"}},
  {"datetime": "2024-01-01T10:00:03Z", "event_type": "CRAWL_SUCCESS", "data": {"url": "https://test.com"}},
  {"datetime": "2024-01-01T10:00:04Z", "event_type": "WORKER_START", "data": {"worker_id": "worker-1"}}
]
EOF
    fi
    
    extract_crawl_errors "$JSON_LOG_FILE"
    echo
    
    # Check Redis status
    check_redis_status
    echo
    
    print_success "Demo completed!"
}

# =============================================================================
# HELP AND USAGE
# =============================================================================

show_help() {
    cat << 'EOF'
Distributed Web Crawler - Shell Utilities

USAGE:
    ./crawler_utils.sh <command> [args]

NETWORK TESTING:
    test_endpoint <url> [method]     - Test HTTP endpoint (default: GET)
    fetch_robots_txt <domain>       - Fetch robots.txt for domain
    test_crawler_access <url>       - Test crawler user-agent access

LOG PROCESSING:
    count_successful_crawls <file>   - Count successful vs failed crawls
    extract_timestamps <file> <format> - Extract timestamps (standard, iso, unix)
    filter_log_by_level <file> <level> - Filter log by level (ERROR, WARNING, INFO)
    replace_timestamps <file> <replacement> - Replace all timestamps

JSON PROCESSING:
    extract_crawl_errors <file>     - Extract URLs from CRAWL_ERROR events
    extract_worker_stats <file>    - Extract worker activity statistics
    filter_json_by_time <file> <range> - Filter by time (last_hour, today)
    summarize_json_logs <file>      - Show JSON log summary

REDIS UTILITIES:
    check_redis_status              - Check Redis connection and status
    clear_redis_data [pattern]      - Clear Redis keys (default: *)

DEMONSTRATION:
    demo_all                        - Run complete demonstration

EXAMPLES:
    ./crawler_utils.sh test_endpoint https://arxiv.org
    ./crawler_utils.sh fetch_robots_txt wikipedia.org
    ./crawler_utils.sh count_successful_crawls crawler.log
    ./crawler_utils.sh extract_crawl_errors logs.json
    ./crawler_utils.sh check_redis_status

REQUIREMENTS:
    - curl or wget for network testing
    - awk and sed for log processing
    - jq for JSON processing
    - redis-cli for Redis utilities
    - bc for calculations (optional)

INSTALLATION:
    brew install curl wget jq redis
EOF
}

# =============================================================================
# MAIN SCRIPT LOGIC
# =============================================================================

main() {
    local command="$1"
    
    case "$command" in
        "test_endpoint")
            test_endpoint "$2" "$3"
            ;;
        "fetch_robots_txt")
            fetch_robots_txt "$2"
            ;;
        "test_crawler_access")
            test_crawler_access "$2"
            ;;
        "count_successful_crawls")
            count_successful_crawls "$2"
            ;;
        "extract_timestamps")
            extract_timestamps "$2" "$3"
            ;;
        "filter_log_by_level")
            filter_log_by_level "$2" "$3"
            ;;
        "replace_timestamps")
            replace_timestamps "$2" "$3"
            ;;
        "extract_crawl_errors")
            extract_crawl_errors "$2"
            ;;
        "extract_worker_stats")
            extract_worker_stats "$2"
            ;;
        "filter_json_by_time")
            filter_json_by_time "$2" "$3"
            ;;
        "summarize_json_logs")
            summarize_json_logs "$2"
            ;;
        "check_redis_status")
            check_redis_status
            ;;
        "clear_redis_data")
            clear_redis_data "$2"
            ;;
        "demo_all")
            demo_all
            ;;
        "help"|"-h"|"--help"|"")
            show_help
            ;;
        *)
            print_error "Unknown command: $command"
            echo
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
