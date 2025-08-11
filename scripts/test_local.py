#!/usr/bin/env python3
"""
Local testing script for fetch_languages.py
Run this to test your language stats generation locally
"""
import os
import sys
from pathlib import Path

def setup_test_environment():
    """Setup environment variables for local testing"""
    
    username = input("Enter your GitHub username: ").strip()
    if not username:
        print("Username is required")
        sys.exit(1)
    
    print("\nGitHub Personal Access Token:")
    print("   - For public repos only: press Enter to skip")
    print("   - For complete data: create token at https://github.com/settings/tokens")
    print("   - Token needs 'repo' scope for private repos, or no scopes for public only")
    
    token = input("Enter your GitHub token (or press Enter to skip): ").strip()
    
    os.environ["USERNAME"] = username
    if token:
        os.environ["GH_TOKEN"] = token
        print("Token provided - will include private repos")
    else:
        print("No token provided - only public repos will be analyzed")
    
    return username, token

def run_test():
    """Run the fetch_languages script"""
    print("\n" + "="*50)
    print("Running language stats generation...")
    print("="*50)
    
    try:
        sys.path.insert(0, 'scripts')
        import fetch_languages
        
        print("Script completed successfully!")
        
        svg_path = Path("assets/languages.svg")
        if svg_path.exists():
            size = svg_path.stat().st_size
            print(f"SVG created: {svg_path} ({size:,} bytes)")
            
            import webbrowser
            choice = input("\nOpen SVG in browser? (y/n): ").lower()
            if choice == 'y':
                webbrowser.open(f"file://{svg_path.absolute()}")
        else:
            print("SVG file was not created")
            
    except ImportError as e:
        print(f"Could not import fetch_languages: {e}")
        print("Make sure fetch_languages.py is in the scripts/ directory")
    except Exception as e:
        print(f"Error running script: {e}")
        return False
    
    return True

def main():
    print("Local Language Stats Tester")
    print("="*30)
    
    if not Path("scripts/fetch_languages.py").exists():
        print("Could not find scripts/fetch_languages.py")
        print("Make sure you're running this from the repository root")
        sys.exit(1)
    
    username, token = setup_test_environment()
    
    success = run_test()
    
    if success:
        print(f"\nTest completed! Check assets/languages.svg")
        print(f"Your GitHub: https://github.com/{username}")
    else:
        print("\nTest failed - check error messages above")

if __name__ == "__main__":
    main()
