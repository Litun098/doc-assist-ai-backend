from supabase import create_client
import os

# Get Supabase credentials from environment variables
supabase_url = os.environ.get("SUPABASE_URL", "https://mqwwdijvgafhfgluiwld.supabase.co")
supabase_key = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1xd3dkaWp2Z2FmaGZnbHVpd2xkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQ4MTc2MTMsImV4cCI6MjA2MDM5MzYxM30.ydqjs6w71MVuzCSeNiga5O0QFXbzoHVKoUHwwHe4YgA")

print(f"Supabase URL: {supabase_url}")
print(f"Supabase Key: {supabase_key[:10]}...")

try:
    # Initialize Supabase client
    supabase = create_client(supabase_url, supabase_key)
    print("Supabase client created successfully!")
    
    # Try a simple query
    response = supabase.table("users").select("*").limit(1).execute()
    print(f"Query response: {response}")
    
except Exception as e:
    print(f"Error: {str(e)}")
