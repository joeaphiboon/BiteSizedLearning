import streamlit as st
from groq import Groq
import json
from datetime import datetime
import random
import time

# Page configuration remains the same
st.set_page_config(
    page_title="Daily AI Learning Generator",
    page_icon="🎓",
    layout="wide"
)

# Categories definition
CATEGORIES = {
    "science": "Scientific concepts, discoveries, and natural phenomena",
    "technology": "Computing, innovation, and digital transformation",
    "psychology": "Human behavior, mental processes, and cognitive science",
    "history": "Key events, figures, and transformative periods",
}

# Improved prompt that forces a more structured response
LESSON_SYSTEM_PROMPT = """You are an educational content creator that generates structured lessons. 
You must ALWAYS respond with valid JSON only, no additional text or explanations.
Your responses must perfectly match the required JSON structure."""

LESSON_TEMPLATE = """Create an educational lesson about {topic} in {category}.
Respond with ONLY this exact JSON structure, no other text:

{{
    "title": "Write an engaging title here",
    "category": "{category}",
    "concept": {{
        "mainIdea": "Write 2-3 sentences explaining the main concept",
        "priorKnowledge": "Write what students should already know"
    }},
    "exercise": {{
        "question": "Write a multiple choice question",
        "options": [
            "Write correct answer here",
            "Write incorrect option here",
            "Write incorrect option here",
            "Write incorrect option here"
        ],
        "correctAnswer": 0
    }},
    "practicalApplication": {{
        "realWorldExample": "Write a real-world example",
        "caseStudy": "Write a brief case study",
        "challengePrompt": "Write a challenge question"
    }},
    "reflection": {{
        "connectingPrompt": "Write a reflection question",
        "nextSteps": "Write suggested next steps",
        "relatedTopics": [
            "Topic 1",
            "Topic 2",
            "Topic 3",
            "Topic 4"
        ]
    }}
}}"""

def initialize_session_state():
    """Initialize session state variables"""
    if 'api_key' not in st.session_state:
        st.session_state.api_key = ''
    if 'current_lesson' not in st.session_state:
        st.session_state.current_lesson = None
    if 'selected_answer' not in st.session_state:
        st.session_state.selected_answer = None
    if 'reflection_text' not in st.session_state:
        st.session_state.reflection_text = ''

def extract_json_from_response(text):
    """Extract and validate JSON from the API response"""
    # Remove any leading/trailing whitespace and newlines
    text = text.strip()
    
    # Find the first { and last }
    start = text.find('{')
    end = text.rfind('}')
    
    if start == -1 or end == -1:
        raise ValueError("No valid JSON structure found in response")
    
    # Extract just the JSON part
    json_str = text[start:end + 1]
    
    # Parse and validate the JSON
    try:
        data = json.loads(json_str)
        
        # Verify all required keys are present
        required_keys = ['title', 'category', 'concept', 'exercise', 
                        'practicalApplication', 'reflection']
        if not all(key in data for key in required_keys):
            raise ValueError("Missing required keys in lesson content")
            
        return data
    except json.JSONDecodeError as e:
        st.error("Failed to parse JSON response")
        st.code(json_str)  # Show the problematic JSON for debugging
        raise e

def generate_lesson(category, api_key):
    """Generate a lesson using the Groq API with improved error handling"""
    try:
        # Initialize Groq client
        client = groq.Groq(api_key=api_key)
        
        # First, get a specific topic
        topic_messages = [
            {"role": "system", "content": "You are an expert in education. Respond with only a single topic name, no other text."},
            {"role": "user", "content": f"Suggest one specific, interesting topic in {category} for a 5-minute lesson."}
        ]
        
        topic_completion = client.chat.completions.create(
            messages=topic_messages,
            model="mixtral-8x7b-32768",
            temperature=0.7,
            max_tokens=50
        )
        
        topic = topic_completion.choices[0].message.content.strip()
        st.info(f"Generating lesson about: {topic}")
        
        # Generate the complete lesson
        lesson_messages = [
            {"role": "system", "content": LESSON_SYSTEM_PROMPT},
            {"role": "user", "content": LESSON_TEMPLATE.format(
                category=category,
                topic=topic
            )}
        ]
        
        lesson_completion = client.chat.completions.create(
            messages=lesson_messages,
            model="mixtral-8x7b-32768",
            temperature=0.7,
            max_tokens=4500
        )
        
        # Extract and validate the JSON response
        response_text = lesson_completion.choices[0].message.content
        lesson = extract_json_from_response(response_text)
        return lesson
            
    except Exception as e:
        st.error(f"Error details: {str(e)}")
        st.error("Response received:")
        st.code(response_text if 'response_text' in locals() else "No response received")
        return None

# The display_lesson function remains the same as before...
def display_lesson(lesson):
    """Display the lesson content in an organized, engaging format"""
    if not lesson:
        return

    # Display title and category
    st.title(lesson["title"])
    st.markdown(f"*Category: {lesson['category']}*")
    
    # Core concept section
    st.header("📚 Core Concept")
    st.write(lesson["concept"]["mainIdea"])
    with st.expander("Prior Knowledge"):
        st.write(lesson["concept"]["priorKnowledge"])
    
    # Interactive exercise section
    st.header("✍️ Practice Question")
    st.write(lesson["exercise"]["question"])
    
    # Create two columns for answer options
    cols = st.columns(2)
    for idx, option in enumerate(lesson["exercise"]["options"]):
        col = cols[idx % 2]
        if col.button(
            option,
            key=f"option_{idx}",
            type="secondary" if st.session_state.selected_answer != idx else "primary"
        ):
            st.session_state.selected_answer = idx
            
    # Show feedback for selected answer
    if st.session_state.selected_answer is not None:
        if st.session_state.selected_answer == lesson["exercise"]["correctAnswer"]:
            st.success("✅ Correct! Excellent work!")
        else:
            st.error("❌ Not quite right. Give it another try!")
    
    # Practical application section
    st.header("🌟 Real-World Application")
    st.write(lesson["practicalApplication"]["realWorldExample"])
    
    with st.expander("Case Study"):
        st.write(lesson["practicalApplication"]["caseStudy"])
    
    st.info(f"🤔 Challenge: {lesson['practicalApplication']['challengePrompt']}")
    
    # Reflection section
    st.header("🔍 Reflection")
    st.write(lesson["reflection"]["connectingPrompt"])
    reflection = st.text_area(
        "Share your thoughts:",
        value=st.session_state.reflection_text,
        height=100,
        key="reflection_input"
    )
    
    # Next steps and related topics
    st.header("🔄 Next Steps")
    st.write(lesson["reflection"]["nextSteps"])
    
    st.subheader("Related Topics to Explore:")
    for topic in lesson["reflection"]["relatedTopics"]:
        st.markdown(f"- {topic}")

def main():
    """Main application logic with improved error handling"""
    initialize_session_state()
    
    with st.sidebar:
        st.title("⚙️ Settings")
        
        # API key input with validation
        api_key = st.text_input(
            "Enter your Groq API Key:",
            type="password",
            value=st.session_state.api_key,
            help="Get your API key from console.groq.com"
        )
        
        if api_key:
            if not api_key.startswith('gsk_'):
                st.warning("⚠️ API key should start with 'gsk_'. Please check your key.")
            st.session_state.api_key = api_key
        
        st.markdown("---")
        
        st.subheader("Select Category")
        selected_category = st.radio(
            "Choose a learning category:",
            ["random"] + list(CATEGORIES.keys()),
            format_func=lambda x: "Random" if x == "random" else x.capitalize()
        )
        
        if st.button("Generate New Lesson", type="primary"):
            if not api_key:
                st.error("Please enter your Groq API key first!")
                return
                
            with st.spinner("Creating your personalized lesson..."):
                category = random.choice(list(CATEGORIES.keys())) if selected_category == "random" else selected_category
                
                try:
                    lesson = generate_lesson(category, api_key)
                    if lesson:
                        st.session_state.current_lesson = lesson
                        st.session_state.selected_answer = None
                        st.session_state.reflection_text = ''
                        st.rerun()
                except Exception as e:
                    st.error("Failed to generate lesson. Please try again.")
                    st.error(f"Error: {str(e)}")
    
    # Display the lesson or welcome message
    if st.session_state.current_lesson:
        display_lesson(st.session_state.current_lesson)
    else:
        st.title("Daily AI Learning Generator")
        st.write("Welcome! Select a category and click 'Generate New Lesson' to start learning.")
        st.markdown("---")
        st.subheader("Available Categories:")
        for category, description in CATEGORIES.items():
            st.markdown(f"**{category.capitalize()}**: {description}")

if __name__ == "__main__":
    main()
