import os
import csv
import requests
from colorama import init, Fore, Style
from datetime import datetime
import sys
import time

# Initialize colorama for colored text
init(autoreset=True)

def print_colored(text, color=Fore.WHITE, emoji=""):
    """Print colored text with optional emoji"""
    print(f"{emoji} {color}{text}{Style.RESET_ALL}")

def email_to_filename(email):
    """Convert email to filename format like dellaramadhanty26_gmail.com"""
    # Convert to lowercase
    # email = email.lower()
    
    # Replace @ with _
    email = email.replace('@', '_')
    
    # Note: Keep .com as .com (don't convert dots)
    # Return as-is
    return email

def check_pdf_exists(email, event_code, max_retries=5, retry_delay=5):
    """Check if PDF exists for given email and event code with retry mechanism"""
    # Convert email to filename format
    email_filename = email_to_filename(email)
    
    # Construct the URL
    url = f"https://bbpvpbekasi.kemnaker.go.id/bulanvokasi/sertifikatbv/{event_code}/{email_filename}.pdf"
    
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.head(url, timeout=10, allow_redirects=True)
            
            if response.status_code == 200:
                # Also check if it's actually a PDF by looking at content-type
                content_type = response.headers.get('content-type', '').lower()
                if 'pdf' in content_type:
                    return True, url, "PDF exists"
                else:
                    return False, url, "URL exists but not a PDF"
            else:
                return False, url, f"HTTP Status: {response.status_code}"
                
        except requests.exceptions.Timeout:
            if attempt < max_retries:
                print_colored(f"     ⏱️  Timeout (attempt {attempt}/{max_retries}), retrying in {retry_delay}s...", Fore.YELLOW)
                time.sleep(retry_delay)
            else:
                return False, url, f"Connection timeout (failed after {max_retries} attempts)"
                
        except requests.exceptions.ConnectionError:
            if attempt < max_retries:
                print_colored(f"     🔌 Connection error (attempt {attempt}/{max_retries}), retrying in {retry_delay}s...", Fore.YELLOW)
                time.sleep(retry_delay)
            else:
                return False, url, f"Connection error (failed after {max_retries} attempts)"
                
        except requests.exceptions.RequestException as e:
            if attempt < max_retries:
                print_colored(f"     ⚠️  Request error (attempt {attempt}/{max_retries}), retrying in {retry_delay}s...", Fore.YELLOW)
                time.sleep(retry_delay)
            else:
                return False, url, f"Request error: {str(e)} (failed after {max_retries} attempts)"
    
    # Should not reach here, but just in case
    return False, url, "Unknown error"

def process_event(event_code):
    """Process a single event code"""
    csv_file = f"{event_code}.csv"
    
    if not os.path.exists(csv_file):
        print_colored(f"CSV file '{csv_file}' not found!", Fore.RED, "❌")
        return False
    
    print_colored(f"\n{'='*60}", Fore.CYAN)
    print_colored(f"Processing event: {event_code}", Fore.CYAN, "📁")
    print_colored(f"CSV file: {csv_file}", Fore.CYAN)
    print_colored(f"Start time: {datetime.now().strftime('%H:%M:%S')}", Fore.CYAN)
    print_colored(f"Retry policy: 3 attempts with 2s delay", Fore.CYAN, "🔄")
    print_colored(f"{'='*60}", Fore.CYAN)
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as file:
            # Try to detect CSV dialect
            sample = file.read(1024)
            file.seek(0)
            
            # Check if file has header
            has_header = csv.Sniffer().has_header(sample)
            
            if has_header:
                reader = csv.DictReader(file)
                # Find email column (case insensitive)
                email_field = None
                for field in reader.fieldnames:
                    if 'email' in field.lower():
                        email_field = field
                        break
                
                if not email_field:
                    print_colored("No email column found in CSV header!", Fore.RED, "❌")
                    return False
                    
                emails = [row[email_field] for row in reader if row[email_field].strip()]
            else:
                # No header, assume emails are in a specific column
                reader = csv.reader(file)
                emails = []
                for row in reader:
                    if len(row) > 1:  # Assuming email is in second column
                        emails.append(row[1].strip())
                    elif len(row) == 1:  # Only one column
                        emails.append(row[0].strip())
        
        if not emails:
            print_colored("No emails found in CSV file!", Fore.YELLOW, "⚠️")
            return False
        
        print_colored(f"Found {len(emails)} emails to check", Fore.GREEN, "📧")
        
        # Show conversion example
        if emails:
            example_email = emails[0]
            example_filename = email_to_filename(example_email)
            print_colored(f"Example conversion: {example_email} → {example_filename}.pdf", Fore.CYAN, "🔄")
        
        print()
        
        results = []
        for idx, email in enumerate(emails, 1):
            if not email or '@' not in email:
                print_colored(f"Skipping invalid email: {email}", Fore.YELLOW, "⚠️")
                continue
                
            exists, url, message = check_pdf_exists(email, event_code)
            
            # Show the generated URL
            url_filename = url.split('/')[-1]  # Just show the filename part
            full_url_display = url  # Full URL for copy-paste
            
            if exists:
                print_colored(f"{idx:3d}. ✓ {email}", Fore.GREEN, "✅")
                print_colored(f"     → {url_filename}", Fore.GREEN)
                print_colored(f"     URL: {full_url_display}", Fore.GREEN)
                print_colored(f"     Status: {message}", Fore.GREEN)
                results.append((email, True, url, message))
            else:
                print_colored(f"{idx:3d}. ✗ {email}", Fore.RED, "❌")
                print_colored(f"     → {url_filename}", Fore.RED)
                print_colored(f"     URL: {full_url_display}", Fore.RED)
                print_colored(f"     Status: {message}", Fore.RED)
                results.append((email, False, url, message))
            
            # Add a small separator between entries for readability
            if idx < len(emails):
                print_colored(f"     {'─'*40}", Fore.LIGHTBLACK_EX)
        
        # Print summary
        print_colored(f"\n{'='*60}", Fore.CYAN)
        total = len(results)
        success = sum(1 for r in results if r[1])
        failed = total - success
        
        print_colored(f"SUMMARY for {event_code}:", Fore.CYAN, "📊")
        print_colored(f"Total emails checked: {total}", Fore.WHITE)
        print_colored(f"PDFs found: {success}", Fore.GREEN, "✅")
        print_colored(f"PDFs not found: {failed}", Fore.RED, "❌")
        
        # Show URL pattern and conversion rules
        print_colored(f"\nURL Pattern and Conversion Rules:", Fore.CYAN, "🔗")
        print_colored(f"Base URL: https://bbpvpbekasi.kemnaker.go.id/bulanvokasi/sertifikatbv/{event_code}/{{filename}}.pdf", Fore.WHITE)
        print_colored(f"Conversion rules:", Fore.WHITE)
        # print_colored(f"  1. Convert email to lowercase", Fore.WHITE)
        print_colored(f"  1. Replace '@' with '_'", Fore.WHITE)
        print_colored(f"  2. Keep '.com' as '.com' (don't change dots)", Fore.WHITE)
        print_colored(f"  Example: DellaRamadhanty26@gmail.com → DellaRamadhanty26_gmail.com.pdf", Fore.WHITE)
        
        if success > 0:
            # Show first successful URL as example
            for email, exists, url, message in results:
                if exists:
                    print_colored(f"\nExample successful URL:", Fore.GREEN)
                    print_colored(f"{url}", Fore.GREEN)
                    break
        
        if failed > 0:
            print_colored(f"\nFailed to find PDFs for:", Fore.YELLOW, "⚠️")
            failed_count = 0
            for email, exists, url, message in results:
                if not exists:
                    failed_count += 1
                    if failed_count <= 5:  # Show only first 5 failures
                        print_colored(f"  • {email}", Fore.YELLOW)
                        print_colored(f"    → {email_to_filename(email)}.pdf", Fore.YELLOW)
                        print_colored(f"    URL: {url}", Fore.YELLOW)
                    elif failed_count == 6:
                        print_colored(f"  ... and {failed - 5} more", Fore.YELLOW)
        
        # Save results to a log file
        log_file = f"{event_code}_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"Event: {event_code}\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total: {total}, Found: {success}, Missing: {failed}\n\n")
            f.write("Email,Filename,Status,URL,Message\n")
            for email, exists, url, message in results:
                status = "FOUND" if exists else "MISSING"
                filename = email_to_filename(email) + ".pdf"
                f.write(f'"{email}","{filename}","{status}","{url}","{message}"\n')
        
        print_colored(f"\nDetailed results saved to: {log_file}", Fore.BLUE, "💾")
        
        # Also save a simple list of URLs for easy access
        urls_file = f"{event_code}_urls_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(urls_file, 'w', encoding='utf-8') as f:
            f.write(f"URLs for event: {event_code}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Conversion: email → lowercase, @ → _, keep .com\n\n")
            for email, exists, url, message in results:
                if exists:
                    f.write(f"✓ {url}\n")
                else:
                    f.write(f"✗ {url}  # {message}\n")
        
        print_colored(f"URL list saved to: {urls_file}", Fore.BLUE, "📄")
        
    except Exception as e:
        print_colored(f"Error processing CSV: {str(e)}", Fore.RED, "❌")
        return False
    
    return True

def main():
    """Main application loop"""
    # Define available event codes
    event_codes = [
        "681ec43c",
        "41236a8e", 
        "c08ca642",
        "6cdac529",
        "7d311ab2",
        "a9537b89",
        "77e83039",
        "fd0a971e"
    ]
    
    while True:
        # Clear screen (works on Windows and Unix)
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print_colored("\n" + "="*60, Fore.CYAN)
        print_colored("PDF VERIFICATION TOOL", Fore.CYAN, "🔍")
        print_colored("="*60, Fore.CYAN)
        print()
        
        print_colored("Available Event Codes:", Fore.YELLOW, "📋")
        for idx, code in enumerate(event_codes, 1):
            # Check if CSV file exists for this code
            csv_exists = os.path.exists(f"{code}.csv")
            status = "✓ CSV found" if csv_exists else "✗ CSV missing"
            color = Fore.GREEN if csv_exists else Fore.RED
            print_colored(f"  {idx}. {code} - {status}", color)
        
        print()
        print_colored("Options:", Fore.YELLOW)
        print_colored("  1-8 : Select event code", Fore.WHITE)
        print_colored("  0   : Exit", Fore.WHITE)
        print_colored("  a   : Check all events", Fore.WHITE)
        print()
        
        choice = input(f"{Fore.CYAN}Enter your choice: {Style.RESET_ALL}").strip().lower()
        
        if choice == '0':
            print_colored("\nGoodbye! 👋", Fore.CYAN)
            break
        elif choice == 'a':
            print_colored("\nChecking ALL events...", Fore.MAGENTA, "🚀")
            for code in event_codes:
                process_event(code)
                input(f"\n{Fore.YELLOW}Press Enter to continue to next event...{Style.RESET_ALL}")
        elif choice.isdigit() and 1 <= int(choice) <= len(event_codes):
            selected_code = event_codes[int(choice) - 1]
            process_event(selected_code)
            input(f"\n{Fore.YELLOW}Press Enter to return to menu...{Style.RESET_ALL}")
        else:
            print_colored("Invalid choice! Please try again.", Fore.RED, "❌")
            input(f"\n{Fore.YELLOW}Press Enter to continue...{Style.RESET_ALL}")

if __name__ == "__main__":
    # Install required packages if not already installed
    try:
        import requests
        import colorama
    except ImportError:
        print("Installing required packages...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "colorama"])
        import requests
        import colorama
        from colorama import init, Fore, Style
        init(autoreset=True)
    
    main()