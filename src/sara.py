#!/usr/bin/env python3

# Current version of SARA
__version__ = "1.1"

import aiohttp
import argparse
import asyncio
from bs4 import BeautifulSoup
import colorama
from colorama import Fore, Style
import json
import os
from playwright.async_api import async_playwright
import pyfiglet
import random
import re
import sys
import time
from urllib.parse import urljoin

colorama.init(autoreset=True)

"""
   🔵 CYAN	   Fore.CYAN	Information messages
   🟢 GREEN	   Fore.GREEN	Link, JS files
   🟡 YELLOW   Fore.YELLOW	Warnings
   🔴 RED	   Fore.RED	    Errors
"""

# Task progress indicator with dots animation
async def run_with_dots(task_function, *args, **kwargs):
    stop_animation = False

    async def animate():
        message = "I`m researching"
        dots = ""
        while not stop_animation:
            sys.stdout.write(f"\r{message}{dots}")
            sys.stdout.flush()
            dots += "."
            await asyncio.sleep(1)

    animation_task = asyncio.create_task(animate())
    try:
        result = await task_function(*args, **kwargs)
        return result
    finally:
        stop_animation = True
        await animation_task
        sys.stdout.write("\r" + " " * 20 + "\r")  # Clear the line

# User-Agent headers
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:108.0) Gecko/20100101 Firefox/108.0"
]

# Custom ArgumentParser to suppress usage message on error
class CustomArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, f"Error: {message}\n")

# Function to extract JavaScript files from HTML content
def extract_js_files(html):
    js_files = re.findall(r'<script[^>]+src=["\'](.*?\.js)["\']', html)
    return js_files

# Function to extract links from HTML content
def extract_links(html, base_url):
    """Extract all links from the HTML and convert relative paths to absolute URLs."""
    soup = BeautifulSoup(html, "html.parser")
    links = []

    for a_tag in soup.find_all("a", href=True):  # Looking for all <a> with href
        full_url = urljoin(base_url, a_tag["href"])  # Make link absolute абсолютной
        links.append(full_url)

    return list(set(links))  # Delete duplicates

# Function to extract comments from JavaScript code
def extract_comments(js_code, max_length=50):
    single_line_comment_pattern = r'(?<!:)\/\/.*(?=\n|$)'
    multi_line_comment_pattern = r'\/\*[\s\S]*?\*\/'

    single_line_comments = re.findall(single_line_comment_pattern, js_code)
    multi_line_comments = re.findall(multi_line_comment_pattern, js_code)

    all_comments = single_line_comments + multi_line_comments

    filtered_comments = []
    for comment in all_comments:
        comment = comment.strip()
        if len(comment) <= 2:
            continue
        if "http://" in comment or "https://" in comment:
            continue
        if len(comment) > max_length:
            comment = comment[:max_length] + "..."
        filtered_comments.append(comment)

    return filtered_comments

# Function to analyze HTTP headers
def analyze_headers(headers):
    issues = []

    # CORS Headers
    if "Access-Control-Allow-Origin" in headers:
        origin = headers["Access-Control-Allow-Origin"]
        if origin == "*":
            issues.append({
                "header": "Access-Control-Allow-Origin",
                "problem": "Wildcard '*' allows access from any domain.",
                "recommendation": "Specify a trusted domain instead of '*'."
            })
    else:
        issues.append({
            "header": "Access-Control-Allow-Origin",
            "problem": "Missing header.",
            "recommendation": "Add 'Access-Control-Allow-Origin' with a specific domain."
        })

    if "Access-Control-Allow-Credentials" in headers:
        if headers["Access-Control-Allow-Credentials"].lower() == "true":
            if "Access-Control-Allow-Origin" in headers and headers["Access-Control-Allow-Origin"] == "*":
                issues.append({
                    "header": "Access-Control-Allow-Credentials",
                    "problem": "Used with wildcard '*'.",
                    "recommendation": "Ensure 'Access-Control-Allow-Origin' specifies a trusted domain."
                })

    # SOP Headers
    if "X-Frame-Options" not in headers:
        issues.append({
            "header": "X-Frame-Options",
            "problem": "Missing header.",
            "recommendation": "Add 'X-Frame-Options' to prevent clickjacking."
        })
    if "Content-Security-Policy" not in headers:
        issues.append({
            "header": "Content-Security-Policy",
            "problem": "Missing header.",
            "recommendation": "Add 'Content-Security-Policy' to restrict resources and mitigate XSS."
        })

    if "Referrer-Policy" not in headers:
        issues.append({
            "header": "Referrer-Policy",
            "problem": "Missing header.",
            "recommendation": "Add 'Referrer-Policy' to control referrer information."
        })

    return issues

# Function to search for keywords in JavaScript code
def search_keywords(js_code, keywords):
    found_keywords = []
    js_code_lower = js_code.lower()  # Convert entire content to lowercase
    for keyword in keywords:
        if keyword.lower() in js_code_lower:  # Convert keyword to lowercase for comparison
            found_keywords.append(keyword)
    return found_keywords

# Function to fetch and analyze JavaScript files
async def analyze_js_file(session, js_url, keywords=None, skip_comments=False):
    try:
        async with session.get(js_url, timeout=10) as response:
            if response.status == 200:
                js_content = await response.text()
                comments = [] if skip_comments else extract_comments(js_content)
                keywords_found = search_keywords(js_content, keywords) if keywords else []
                return {
                    "url": js_url,
                    "status_code": response.status,
                    "total_comments": len(comments),
                    "comments": comments[:5],
                    "keywords_found": keywords_found
                }
            else:
                return {"url": js_url, "status_code": response.status, "error": "Failed to fetch"}
    except Exception as e:
        return {"url": js_url, "error": str(e)}

# Function to perform directory enumeration
async def enum_directories(session, base_url, headers, wordlist, method="GET", data=None):
    results = []

    # Randomize User-Agent if not provided
    if "User-Agent" not in headers:
        headers["User-Agent"] = random.choice(USER_AGENTS)

    request_func = session.get if method.upper() == "GET" else session.post  # GET or POST

    for path in wordlist:
        url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        try:
            async with request_func(url, headers=headers, data=data, timeout=10) as response:
                result = {
                    "url": url,
                    "status_code": response.status,
                    "method": method
                }
                results.append(result)
        except Exception as e:
            print(f"{Fore.RED}[ERROR] {url} - {e} ({method}){Style.RESET_ALL}")
            results.append({"url": url, "error": str(e), "method": method})

        await asyncio.sleep(random.uniform(1, 5))  # Delay to mimic human behavior

    return sorted(results, key=lambda x: x.get("status_code", 999)) # Sort by status code

# Function to perform subdomain enumeration
async def enum_subdomains(session, base_domain, headers, wordlist, method="GET", data=None, use_http=False):
    results = []
    protocol = "http" if use_http else "https"

    # Randomize User-Agent if not provided
    if "User-Agent" not in headers:
        headers["User-Agent"] = random.choice(USER_AGENTS)

    request_func = session.get if method.upper() == "GET" else session.post  # GET or POST

    for subdomain in wordlist:
        url = f"{protocol}://{subdomain}.{base_domain}"
        try:
            async with request_func(url, headers=headers, data=data, timeout=10) as response:
                result = {
                    "url": url,
                    "status_code": response.status,
                     "method": method
                }
                results.append(result)
        except Exception as e:
            print(f"{Fore.RED}[ERROR] {url} - {e} ({method}){Style.RESET_ALL}")
            results.append({"url": url, "error": str(e), "method": method})

        await asyncio.sleep(random.uniform(1, 5))  # Delay to mimic human behavior

    return sorted(results, key=lambda x: x.get("status_code", 999)) # Sort by status code

# Function to crawl and analyze URLs
async def fetch_with_playwright(url, headers):
    """
    Fetch page content using Playwright headless browser.
    Helps bypass WAF or JS-heavy pages.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=headers.get("User-Agent", random.choice(USER_AGENTS)))
        page = await context.new_page()

        try:
            await page.goto(url, timeout=20000)  # 20 sec timeout
            html = await page.content()  # Get rendered HTML
            await browser.close()
            return html
        except Exception as e:
            print(f"{Fore.RED}[ERROR] Playwright failed on {url}: {e}{Style.RESET_ALL}")
            await browser.close()
            return None

async def crawl_and_analyze(session, url, headers, skip_js, skip_headers, keywords, 
                            method="GET", data=None, depth=1, current_depth=1, visited_links=None,
                            headless=False):
    if visited_links is None:
        visited_links = set()

    try:
        if url in visited_links:
            return  # Skip already visited links
        visited_links.add(url)

        # Randomize User-Agent if not provided
        if "User-Agent" not in headers:
            headers["User-Agent"] = random.choice(USER_AGENTS)

        html = None
        response = None

        if headless:
            html = await fetch_with_playwright(url, headers)
        else:
            request_func = session.get if method.upper() == "GET" else session.post
            async with request_func(url, headers=headers, data=data, timeout=10) as resp:
                response = resp
                html = await resp.text() if resp.status == 200 else None

        if html:
            inline_script_pattern = r'<script(?![^>]*src=["\']).*?</script>'
            script_tag_count = len(re.findall(inline_script_pattern, html, re.DOTALL | re.IGNORECASE))

            js_files = [] if skip_js else extract_js_files(html)
            js_results = []
            links = extract_links(html, url)
            header_issues = [] if skip_headers else analyze_headers(dict(response.headers) if response else {})

            if not skip_js:
                for js_url in js_files:
                    if not js_url.startswith("http"):
                        js_url = f"{url.rstrip('/')}/{js_url.lstrip('/')}"
                    js_results.append(await analyze_js_file(session, js_url, keywords))

            result = {
                "url": url,
                "status_code": response.status if response else "N/A",
                "method": method,
                "depth": current_depth,
                "links": links,
                "headers": dict(response.headers) if response else {},
                "header_issues": header_issues,
                "js_files": js_files,
                "js_analysis": js_results,
                "inline_script_tag_count": script_tag_count
            }

            # Headless indicator
            if headless:
                print(f"{Fore.GREEN}[HEADLESS] Fetched content via headless browser: {url}{Style.RESET_ALL}")

            # Print results
            if not SAVE_TO_FILE:
                print()
                print(f"{Fore.GREEN}URL:{Style.RESET_ALL} {url} (Depth: {current_depth})")
                print(f"{Fore.CYAN}Status:{Style.RESET_ALL} {result['status_code']} [{method}]")
                print(f"{Fore.YELLOW}Found JS files:{Style.RESET_ALL} {len(js_files)}")
                print(f"{Fore.MAGENTA}Links extracted:{Style.RESET_ALL} {len(links)}")

            # Stop if max depth has been reached
            if depth is not None and current_depth >= depth:
                print(f"{Fore.RED}Max depth reached: {depth}. Stopping further crawling.{Style.RESET_ALL}")
                return [result]

            # Group all links for the next lvl
            next_level_links = [link for link in links if link not in visited_links]

            # Ask before diving
            if next_level_links and depth == 99:
                print(f"{Fore.YELLOW}Found {len(next_level_links)} links at depth {current_depth}. Continue to depth {current_depth + 1}? (y/n){Style.RESET_ALL}")
                user_input = input("> ").strip().lower()
                if user_input not in ["y", "yes"]:
                    return [result]

            if next_level_links:
                print(f"{Fore.BLUE}Crawling next depth level: {current_depth + 1} ({len(next_level_links)} URLs){Style.RESET_ALL}")

                # Run tasks
                tasks = [
                    crawl_and_analyze(
                        session, link, headers, skip_js, skip_headers, keywords,
                        method=method, data=data, depth=depth,
                        current_depth=current_depth + 1, visited_links=visited_links,
                        headless=headless
                    ) for link in next_level_links
                ]

                deeper_results = await asyncio.gather(*tasks)
                return [result] + [res for sublist in deeper_results for res in (sublist if isinstance(sublist, list) else [sublist])]

            return [result]

        else:
            error_result = {
                "url": url,
                "status_code": response.status if response else "N/A",
                "error": "Failed to fetch",
                "method": method
            }
            if not SAVE_TO_FILE:
                print(f"{Fore.RED}Error fetching:{Style.RESET_ALL} {url} (Status: {error_result['status_code']}, Method: {method})")
            return [error_result]

    except Exception as e:
        print(f"{Fore.RED}[ERROR] {url} ({method}): {e}{Style.RESET_ALL}")
        return [{"url": url, "error": str(e), "method": method}]
    
# Function to process URLs from string or file
def process_urls(target):
    if os.path.isfile(target):
        with open(target, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]
        return urls
    elif target.startswith("http://") or target.startswith("https://"):
        return [target]
    elif re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", target):  # Check if it's a domain
        return [target]
    else:
        raise ValueError(f"Invalid target: {target}. Must be a URL or a file containing URLs.")


# Function to handle headers from string or file
def process_headers(headers):
    result = {}
    for header in headers:
        if os.path.isfile(header):
            with open(header, 'r') as f:
                for line in f:
                    if ":" in line:  # Check if the line contains a colon
                        key, value = line.strip().split(":", 1)
                        result[key.strip()] = value.strip()
                    else:
                        print(f"Invalid header format: {line.strip()}")
        else:
            if ":" in header:
                key, value = header.split(":", 1)
                result[key.strip()] = value.strip()
            else:
                print(f"Invalid header format: {header}")
    return result

# Function to handle keyword(s) from string or file
def process_keywords(keywords):
    result = []
    for keyword in keywords:
        if os.path.isfile(keyword):
            with open(keyword, 'r') as f:
                file_keywords = [line.strip() for line in f if line.strip()]
                result.extend(file_keywords)
        else:
            result.append(keyword)
    return list(set(result))  # Remove duplicates

# Function to load a wordlist from file or return the default list
def load_wordlist(file_or_default, default_list):
    if file_or_default is True:  # No file provided, use default
        return default_list
    elif os.path.isfile(file_or_default):
        with open(file_or_default, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    else:
        raise ValueError(f"[ERROR] Wordlist file '{file_or_default}' not found.")

# Main asynchronous function
async def main(args):
    # Process headers: support both strings and files
    headers = process_headers(args.headers) if args.headers else {}

    global SAVE_TO_FILE
    SAVE_TO_FILE = bool(args.output)

    # Process keywords: support both strings and files
    keywords = process_keywords(args.keywords) if args.keywords else []

    # Set default User-Agent in session
    async with aiohttp.ClientSession() as session:
        tasks = []

        # Process URLs
        all_urls = []
        for target in args.targets:
            try:
                all_urls.extend(process_urls(target))
            except ValueError as e:
                print(f"[ERROR] Processing target '{target}': {e}")
                return

        if not all_urls:
            print("[ERROR] No valid URLs provided.")
            return

        # Check if --enum-s is used and ensure only domain is provided
        if args.enum_subdomains:
            for target in all_urls:
                if target.startswith("http://") or target.startswith("https://"):
                    print("[ERROR] For --enum-s, only provide the domain (e.g., example.com), not a full URL.")
                    return
                
        # Check if --enum-d is used and ensure full url is provided
        if args.enum_directories:
            for target in all_urls:
                if not (target.startswith("http://") or target.startswith("https://")):
                    print("[ERROR] For --enum-d, only provide the full url (e.g., http(s)://example.com), not a domain.")
                    return

        # Handle modes
        if args.crawl:
            for url in all_urls:
                # Check for file or not
                if os.path.isfile(url):
                    continue

                # Check if -c is used and ensure full url is provided
                if not (url.startswith("http://") or url.startswith("https://")):
                    print("[ERROR] For -c, only provide the full url (e.g., http(s)://example.com), not a domain.")
                    return
                
                # Ensure headers have randomized User-Agent for each request
                current_headers = headers.copy()
                if "User-Agent" not in current_headers:
                    current_headers["User-Agent"] = random.choice(USER_AGENTS)
                tasks.append(crawl_and_analyze(
                    session, url, current_headers, args.without_js, args.without_headers_analysis, 
                    keywords, method=args.method, data=args.data, depth=args.depth, headless=args.headless
                ))

        if args.enum_directories is not None:
            if len(all_urls) != 1:
                print("[ERROR] --enum-d requires exactly one target URL.")
                return
            try:
                # Default directories may be changed
                default_dirs = [
                    "admin",
                    "login",
                    "dashboard",
                    "config",
                    "api",
                    "robots.txt",
                    "sitemap.xml",
                    "env",
                    "private",
                    "uploads",
                    "tmp",
                    "health",
                    "metrics",
                    "status",
                    "graphql",
                    "graphiql"
                ]
                dir_wordlist = load_wordlist(args.enum_directories, default_dirs)
            except ValueError as e:
                print(e)
                return
            tasks.append(enum_directories(session, all_urls[0], headers, dir_wordlist, args.method))

        if args.enum_subdomains is not None:
            if len(all_urls) != 1:
                print("[ERROR] --enum-s requires exactly one target domain.")
                return
            try:
                # Default subdomains may be changed
                default_subs = [
                    "dev",
                    "test",
                    "staging",
                    "qa",
                    "admin",
                    "dashboard",
                    "api",
                    "auth",
                    "mail",
                    "ftp",
                    "vpn",
                    "status"
                ]
                sub_wordlist = load_wordlist(args.enum_subdomains, default_subs)
            except ValueError as e:
                print(e)
                return
            tasks.append(enum_subdomains(session, all_urls[0], headers, sub_wordlist, args.method, use_http=args.http))
            
        # Run SARA
        if tasks:
            results = await run_with_dots(asyncio.gather, *tasks)
        else:
            results = []

        # Save or print results
        if args.output:
            with open(args.output, "w") as f:
                json.dump(results, f, indent=4)
            print(f"Results saved to {args.output}")

        print(json.dumps(results, indent=4))

if __name__ == "__main__":
    #Get the list of available fonts
    available_fonts = pyfiglet.FigletFont.getFonts()
    # Select a random font
    random_font = random.choice(available_fonts)
    # Generate the ASCII art with the random font
    ascii_logo_random = pyfiglet.figlet_format("SARA", font=random_font)
    # Print the ASCII logo
    print()
    #print(ascii_logo)
    print(ascii_logo_random)
    print()

    parser = CustomArgumentParser(
        description=f"Security Assistant Researcher Analyzer (v{__version__})\n",
        epilog="""
Command Examples:
    1. Crawl and analyze a single URL:
        python3 sara.py -t http://example.com -c
            
    2. Enumerate subdomains using a wordlist:
        sara -t example.com --enum-s subdomains.txt

    3. Enumerate directories with a default list:
        python3 sara.py -t https://example.com --enum-d

    4. Crawl and analyze with custom headers and keywords:
        python3 sara.py -t urls.txt -c -H headers.txt -kw keywords.txt

    5. Crawl without analyzing headers and JavaScript files:
        sara -t http://www.example.com -c -wha -wjs

    6. Crawl or enumerate using POST method:
        sara -t http://www.example.com -c -x POST
        python3 sara.py -t https://example.com --enum-d --method POST

    7. Crawl with depth control:
        sara -t http://www.example.com -c -d 3
        sara -t http://www.example.com -c --depth 99  # Controlled depth mode (manual confirmation)

    8. Crawl with headless browser to avoid WAF:
        sara -t http://www.example.com -c -hl    

    9. Save results to a file:
        sara -t https://example.com -c -o results.json
        """,
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("-t", "--targets", nargs="+", required=True, help="URLs to crawl, analyze and enumeration directiories or Domains to enumeration subdomains")
    parser.add_argument("-c", "--crawl", action="store_true", help="Crawl and analyze URLs")
    parser.add_argument("--enum-d", "--enum-directories", dest="enum_directories", nargs="?",  const=True, help="Enumerate directories (-t URL and optionally provide a file with directories)")
    parser.add_argument("--enum-s", "--enum-subdomains", dest="enum_subdomains", nargs="?",  const=True, help="Enumerate subdomains (-t domain and optionally provide a file with subdomains")
    parser.add_argument("--http", action="store_true", help="Enable HTTP enumeration for subdomains")
    parser.add_argument("-H", "--headers", nargs="+", help="Custom headers (string or file)")
    parser.add_argument("-o", "--output", type=str, help="Save results to a file (recommended format: JSON)")
    parser.add_argument("-kw", "--keywords", nargs="+", help="Keywords to search for in JavaScript files. Can be a list of keywords or a file with one keyword per line")
    parser.add_argument("-wjs", "--without-js", action="store_true", help="Skip analysis of JavaScript files")
    parser.add_argument("-wha", "--without-headers-analysis", action="store_true", help="Skip analysis of headers")
    parser.add_argument("-X", "--method", choices=["GET", "POST"], default="GET", help="HTTP method to use (default: GET). Use -X POST for POST requests.")
    parser.add_argument("--data", type=str, help="Data for POST requests")
    parser.add_argument("-d", "--depth", type=int, default=1, help="Set the depth level for crawling (default: 1).")
    parser.add_argument('-hl', '--headless', action='store_true', help='Enable headless browser for crawling')

    args = parser.parse_args()

    # Check if a mode (-c, --enum-s, --enum-d) is specified
    if not (args.crawl or args.enum_subdomains or args.enum_directories):
        parser.error("You must specify a mode: -c (crawl), --enum-s (enumerate subdomains), or --enum-d (enumerate directories).")

    # Check --http only with --enum-s
    if args.http and not args.enum_subdomains:
        parser.error("--http flag can only be used with --enum-s mode")

    # Check that -wha and -wjs flags are used only with -c mode
    if not args.crawl:
        if args.without_headers_analysis or args.without_js:
            invalid_flags = []
            if args.without_headers_analysis:
                invalid_flags.append("-wha")
            if args.without_js:
                invalid_flags.append("-wjs")
            parser.error(f"{' and '.join(invalid_flags)} flag(s) can only be used with -c mode")

    # Process headers
    headers = process_headers(args.headers) if args.headers else {}

    # Set default keywords if none provided
    if not args.keywords:
        args.keywords = ["password", "api_key", "token", "secret", "key", "auth", "login", "access"] # Default keywords

    start_time = time.time()
    asyncio.run(main(args))
    print(f"Time taken: {time.time() - start_time:.2f} seconds")
    
