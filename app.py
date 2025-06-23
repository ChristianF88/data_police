import streamlit as st
import os
import tempfile
import zipfile
import traceback
from filesystem_mcp import run_validation

# Configure page
st.set_page_config(
    page_title="Project Structure Validator",
    page_icon="📁",
    layout="wide"
)

def extract_zip(uploaded_file, extract_to):
    """Extract uploaded zip file to specified directory."""
    with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    
    # Find the main project directory (usually the first folder)
    extracted_items = os.listdir(extract_to)
    if len(extracted_items) == 1 and os.path.isdir(os.path.join(extract_to, extracted_items[0])):
        return os.path.join(extract_to, extracted_items[0])
    else:
        return extract_to

def main():
    st.title("📁 Project Structure Validator")
    st.markdown("Upload a zipped project folder and validate its structure against defined policies using AI.")
    
    # Sidebar for configuration
    st.sidebar.header("Configuration")
    
    # LLM Provider selection
    llm_provider = st.sidebar.selectbox(
        "Select LLM Provider",
        ["OpenAI", "Anthropic"]
    )
    
    # Model selection based on provider
    if llm_provider == "OpenAI":
        models = ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]
        default_model = "gpt-4"
    else:  # Anthropic
        models = ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"]
        default_model = "claude-3-5-sonnet-20241022"
    
    model = st.sidebar.selectbox("Select Model", models, index=0)
    
    # API Key input
    api_key = st.sidebar.text_input(
        f"{llm_provider} API Key",
        type="password",
        help=f"Enter your {llm_provider} API key"
    )
    
    # Main content area
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("📤 Upload Project")
        
        # File upload
        uploaded_file = st.file_uploader(
            "Choose a ZIP file containing your project",
            type=['zip'],
            help="Upload a ZIP file containing your project structure"
        )
        
        # Policy input
        st.header("📋 Project Policy")
        policy_option = st.radio(
            "Policy Source",
            ["Upload with project (policy.txt)", "Enter manually"]
        )
        
        policy_content = None
        if policy_option == "Enter manually":
            policy_content = st.text_area(
                "Enter your project structure policy",
                height=200,
                placeholder="Example:\nExpected project structure:\n- README.md file\n- src/ directory for source code\n- tests/ directory for test files\n- package.json for dependencies"
            )
    
    with col2:
        st.header("📊 Validation Results")
        
        # Validation button and results
        if uploaded_file and api_key:
            if st.button("🔍 Validate Project Structure", type="primary"):
                
                # Initialize progress bar and status
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    # Create temporary directory
                    with tempfile.TemporaryDirectory() as temp_dir:
                        # Step 1: Extract files
                        status_text.text("📦 Extracting project files...")
                        progress_bar.progress(20)
                        
                        project_path = extract_zip(uploaded_file, temp_dir)
                        st.success(f"✅ Extracted to: {os.path.basename(project_path)}")
                        
                        # Step 2: Run validation
                        status_text.text("🔄 Starting validation pipeline...")
                        progress_bar.progress(40)
                        
                        # Show project structure preview
                        with st.expander("📁 Extracted Project Structure", expanded=False):
                            try:
                                for root, dirs, files in os.walk(project_path):
                                    level = root.replace(project_path, '').count(os.sep)
                                    indent = ' ' * 2 * level
                                    st.text(f"{indent}{os.path.basename(root)}/")
                                    subindent = ' ' * 2 * (level + 1)
                                    for file in files:
                                        st.text(f"{subindent}{file}")
                            except Exception as e:
                                st.text(f"Could not preview structure: {e}")
                        
                        # Step 3: Validate
                        status_text.text("🤖 Running AI analysis...")
                        progress_bar.progress(60)
                        
                        # Run validation (this is now synchronous)
                        result = run_validation(
                            project_path, 
                            llm_provider, 
                            model, 
                            api_key, 
                            policy_content
                        )
                        
                        progress_bar.progress(100)
                        status_text.text("✅ Validation completed!")
                        
                        # Display results
                        if result["success"]:
                            st.success("🎉 Validation completed successfully!")
                            
                            # Policy used
                            with st.expander("📋 Policy Used", expanded=False):
                                st.text(result["policy"][:1000] + ("..." if len(result["policy"]) > 1000 else ""))
                            
                            # Project structure
                            with st.expander("📁 Project Files Analyzed", expanded=False):
                                st.text("\n".join(result["project_files"]))
                            
                            # Main report
                            st.subheader("🤖 AI Analysis Report")
                            st.markdown(result["report"])
                            
                            # Download report
                            report_content = f"""# Project Structure Validation Report

## Policy Used
{result["policy"]}

## Project Structure Analyzed
{chr(10).join(result["project_files"])}

## AI Analysis Report
{result["report"]}
"""
                            st.download_button(
                                label="📄 Download Full Report",
                                data=report_content,
                                file_name="project_validation_report.md",
                                mime="text/markdown"
                            )
                        else:
                            st.error(f"❌ Validation failed: {result['error']}")
                            with st.expander("🔍 Error Details"):
                                st.text(result['error'])
                                
                except Exception as e:
                    st.error(f"❌ An unexpected error occurred: {str(e)}")
                    with st.expander("🔍 Full Error Details"):
                        st.text(traceback.format_exc())
                finally:
                    # Clean up progress indicators
                    progress_bar.empty()
                    status_text.empty()
        else:
            # Show what's missing
            missing_items = []
            if not uploaded_file:
                missing_items.append("📎 Upload a project ZIP file")
            if not api_key:
                missing_items.append("🔑 Enter your API key")
                
            if missing_items:
                st.info("Please complete the following to validate your project:")
                for item in missing_items:
                    st.write(f"• {item}")
    
    # Instructions section
    st.markdown("---")
    
    with st.expander("ℹ️ How to Use This Tool", expanded=False):
        st.markdown("""
        ### 🚀 Quick Start Guide
        
        1. **Choose Your AI Provider**: Select OpenAI or Anthropic from the sidebar
        2. **Enter API Key**: Provide your API key for the selected provider
        3. **Upload Project**: Drag and drop or select your project ZIP file
        4. **Set Policy**: Either include a `policy.txt` file in your project or enter policy manually
        5. **Validate**: Click the validation button and wait for AI analysis
        6. **Review & Download**: Examine results and download the full report
        
        ### 📋 Policy Examples
        
        **Web Application:**
        ```
        Expected structure:
        - package.json (dependencies)
        - src/ (source code)
        - public/ (static files)
        - tests/ (test files)
        - README.md (documentation)
        ```
        
        **Python Project:**
        ```
        Expected structure:
        - requirements.txt or pyproject.toml
        - src/ or main module directory
        - tests/
        - README.md
        - .gitignore
        ```
        
        ### ⚙️ Requirements
        - **Node.js & npm** installed on the system
        - **Valid API key** for chosen LLM provider
        - **Project ZIP file** with clear structure
        
        ### 🔧 Troubleshooting
        - Ensure Node.js is installed: `node --version`
        - Check API key permissions
        - Verify ZIP file contains your project files
        - For large projects, validation may take 1-2 minutes
        """)
    
    # Footer
    st.markdown("---")
    st.markdown("Built with ❤️ using Streamlit, MCP, and AI")

if __name__ == "__main__":
    main()