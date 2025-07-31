import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime
import time

# Configuration
API_BASE_URL = "http://localhost:8000"

def main():
    st.set_page_config(
        page_title="IT Newsfeed Platform",
        page_icon="📰",
        layout="wide"
    )
    
    # Header with health check button
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("📰 IT Newsfeed Platform")
        st.markdown("A simple interface for ingesting and retrieving IT news events")
    
    with col2:
        st.write("")  # Add some spacing
        if st.button("🏥 Health Check", type="secondary"):
            check_health()
    
    # Main content
    show_main_page()

def check_health():
    """Check API health and show result"""
    with st.spinner("Checking API health..."):
        try:
            response = requests.get(f"{API_BASE_URL}/health")
            
            if response.status_code == 200:
                health_data = response.json()
                st.success("✅ API is healthy!")
                with st.expander("Health Details"):
                    st.json(health_data)
            else:
                st.error(f"❌ API health check failed: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to API server. Make sure the server is running on localhost:8000")
        except Exception as e:
            st.error(f"❌ Unexpected error: {str(e)}")

def show_main_page():
    """Main page with ingest in sidebar and retrieve as main content"""
    
    # Sidebar for ingest functionality
    with st.sidebar:
        show_ingest_section()
    
    # Main content area for retrieve functionality
    show_retrieve_section()

def show_ingest_section():
    """Ingest section with validation and ingest functionality"""
    st.header("📥 Ingest News Events")
    
    # File upload option
    st.subheader("Upload JSON File")
    uploaded_file = st.file_uploader(
        "Choose a JSON file with news events",
        type=['json'],
        help="Upload a JSON file containing an array of news events"
    )
    
    # Manual input option
    st.subheader("Manual JSON Input")
    manual_json = st.text_area(
        "Or paste JSON array directly:",
        height=150,
        placeholder='[{"id": "example-001", "source": "example", "title": "Example News", "body": "Example content", "published_at": "2025-01-01T00:00:00Z"}]'
    )
    
    # Single ingest button that handles validation internally
    if st.button("🚀 Ingest Events", type="primary"):
        events = None
        error = None
        
        # Try to get events from file upload
        if uploaded_file is not None:
            try:
                content = uploaded_file.read()
                events = json.loads(content)
                if not isinstance(events, list):
                    error = "JSON file must contain an array of events"
            except json.JSONDecodeError:
                error = "Invalid JSON file"
            except Exception as e:
                error = f"Error reading file: {str(e)}"
        
        # Try to get events from manual input
        elif manual_json.strip():
            try:
                events = json.loads(manual_json)
                if not isinstance(events, list):
                    error = "JSON must be an array of events"
            except json.JSONDecodeError:
                error = "Invalid JSON format"
        
        else:
            error = "Please provide JSON data either by uploading a file or pasting JSON"
        
        # Handle the result
        if error:
            st.error(f"❌ Cannot ingest: {error}")
        else:
            # Show preview of events before ingesting
            st.success(f"✅ Validated {len(events)} events")
            
            # Show preview of events
            with st.expander("Preview Events"):
                for i, event in enumerate(events[:5]):  # Show first 5 events
                    st.write(f"**Event {i+1}:**")
                    st.write(f"- ID: {event.get('id', 'N/A')}")
                    st.write(f"- Title: {event.get('title', 'N/A')}")
                    st.write(f"- Source: {event.get('source', 'N/A')}")
                    st.write("---")
                
                if len(events) > 5:
                    st.write(f"... and {len(events) - 5} more events")
            
            # Proceed with ingestion
            with st.spinner("Ingesting events..."):
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/ingest",
                        json=events,
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.success(f"✅ {result['message']}")
                    else:
                        st.error(f"❌ Error: {response.status_code} - {response.text}")
                        
                except requests.exceptions.ConnectionError:
                    st.error("❌ Cannot connect to API server. Make sure the server is running on localhost:8000")
                except Exception as e:
                    st.error(f"❌ Unexpected error: {str(e)}")

def show_retrieve_section():
    """Retrieve section with events display"""
    st.header("📤 Retrieve News Events")
    
    # Refresh button
    if st.button("🔄 Refresh Events", type="primary"):
        st.rerun()
    
    # Retrieve events
    with st.spinner("Loading events..."):
        try:
            response = requests.get(f"{API_BASE_URL}/retrieve")
            
            if response.status_code == 200:
                events = response.json()
                
                if not events:
                    st.info("📭 No events found in the database")
                    return
                
                st.success(f"✅ Retrieved {len(events)} events")
                
                # Display events in a nice format
                for i, event in enumerate(events):
                    with st.container():
                        # Create a card-like display
                        st.markdown("---")
                        
                        # Header with ID and source
                        col1, col2, col3 = st.columns([2, 2, 1])
                        with col1:
                            st.markdown(f"**ID:** `{event['id']}`")
                        with col2:
                            st.markdown(f"**Source:** `{event['source']}`")
                        with col3:
                            # Format the date nicely
                            try:
                                pub_date = datetime.fromisoformat(event['published_at'].replace('Z', '+00:00'))
                                st.markdown(f"**Date:** {pub_date.strftime('%Y-%m-%d %H:%M')}")
                            except:
                                st.markdown(f"**Date:** {event['published_at']}")
                        
                        # Title
                        st.markdown(f"### {event['title']}")
                        
                        # Body
                        if event.get('body'):
                            st.markdown(f"**Content:** {event['body']}")
                        
                        # Expandable details
                        with st.expander("📋 Event Details"):
                            st.json(event)
                
                # Summary statistics
                st.markdown("---")
                st.subheader("📊 Summary Statistics")
                
                # Create summary
                sources = [event['source'] for event in events]
                source_counts = pd.Series(sources).value_counts()
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Events by Source:**")
                    for source, count in source_counts.items():
                        st.write(f"- {source}: {count}")
                
                with col2:
                    st.write("**Total Events:**", len(events))
                    st.write("**Unique Sources:**", len(source_counts))
                
            else:
                st.error(f"❌ Error: {response.status_code} - {response.text}")
                
        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to API server. Make sure the server is running on localhost:8000")
        except Exception as e:
            st.error(f"❌ Unexpected error: {str(e)}")

if __name__ == "__main__":
    main()
