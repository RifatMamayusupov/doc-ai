import streamlit as st
import asyncio
import sys
import uuid
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

load_dotenv()

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.types import Command

from deepagents_cli.agent import create_cli_agent
from deepagents_cli.config import create_model, settings

# Use wide layout
st.set_page_config(layout="wide", page_title="DeepAgents Doc.AI", page_icon="🤖")

# --- Custom CSS for Layout ---
st.markdown("""
<style>
    .main .block-container { padding-top: 2rem; }
    div[data-testid="stChatInput"] { position: fixed; bottom: 0; width: 48%; z-index: 100; }
    /* Preview Column Styling */
    div[data-testid="column"]:nth-of-type(2) {
        border-left: 1px solid #ddd;
        padding-left: 1rem;
        background-color: #f9f9f9;
        height: 100vh;
        overflow-y: auto;
    }
</style>
""", unsafe_allow_html=True)

from langgraph.checkpoint.memory import MemorySaver

# --- Initialization ---

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "preview_file" not in st.session_state:
    st.session_state.preview_file = None

if "interrupt_state" not in st.session_state:
    st.session_state.interrupt_state = None

if "checkpointer" not in st.session_state:
    st.session_state.checkpointer = MemorySaver()

def get_agent():
    """Initialize agent fresh for every run to avoid asyncio loop issues."""
    try:
        # Re-create model to get fresh HTTP transport
        model = create_model(model_name_override="gemini-3-pro-preview")
        
        # Helper to try import custom tool
        custom_tools = []
        try:
            from backend.app.agent.tools.custom_tool import check_server_status
            custom_tools = [check_server_status]
        except ImportError:
            pass

        # Use the PERSISTENT checkpointer from session state
        # This keeps memory across reruns even if agent is recreated
        agent, _ = create_cli_agent(
            model=model,
            assistant_id="doc_ai_user",
            auto_approve=False,
            enable_memory=True, 
            enable_skills=True, 
            enable_shell=True,
            tools=custom_tools,
            checkpointer=st.session_state.checkpointer
        )
        return agent
    except Exception as e:
        st.error(f"Failed to initialize agent: {e}")
        return None

agent = get_agent()

# --- Sidebar (Uploads) ---
with st.sidebar:
    st.header("📂 File Upload")
    uploaded_files = st.file_uploader("Upload files for analysis", accept_multiple_files=True)
    
    if uploaded_files:
        upload_dir = Path.cwd() / "uploads"
        upload_dir.mkdir(exist_ok=True)
        
        st.write("### Saved Files:")
        for uploaded_file in uploaded_files:
            file_path = upload_dir / uploaded_file.name
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success(f"`{uploaded_file.name}`")
            # Maybe add distinct visual cue or copy button?
            st.code(str(file_path), language="bash")

# --- Layout Columns ---
chat_col, preview_col = st.columns([1, 1])

# --- Chat Logic (Left Column) ---
with chat_col:
    st.header("💬 Chat")
    
    # Display History
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if "content" in msg:
                st.markdown(msg["content"])
            if "tool_calls" in msg:
                with st.status(f"🛠️ Executed: {msg['tool_calls']}", state="complete"):
                    st.write("Tool execution completed.")

    # Interrupt / HITL Handling
    # Only show if not currently resuming
    if st.session_state.interrupt_state and not st.session_state.get("resume_action"):
        int_data = st.session_state.interrupt_state
        with st.container(border=True):
            st.warning("⚠️ **Approval Required**")
            
            # Show details
            requests = int_data["value"].get("action_requests", [])
            for req in requests:
                st.write(f"**Tool:** `{req.get('name')}`")
                st.code(req.get("description", str(req.get("args"))))
            
            col1, col2 = st.columns(2)
            if col1.button("✅ Approve", type="primary", use_container_width=True):
                st.session_state.resume_action = "approve"
                st.rerun()
            if col2.button("❌ Reject", type="secondary", use_container_width=True):
                st.session_state.resume_action = "reject"
                st.rerun()
        
        # Stop execution until button clicked
        st.stop()
    
    # Input Handling
    # Logic: 
    # 1. New Prompt -> st.chat_input
    # 2. Resuming -> Auto-trigger
    
    prompt = st.chat_input("Ask me to analyze files or write code...")
    
    # Helper for running stream (reused for both prompt and resume)
    async def run_agent_stream(inputs_override=None, is_resume=False):
         with st.chat_message("assistant"):
            status_container = st.status("Thinking..." if not is_resume else "Resuming...", expanded=True)
            response_placeholder = st.empty()
            
            # Use a mutable list to store result since nonlocal is tricky in scripts
            result_container = [] 

            async def internal_stream():
                local_accumulated_text = ""
                config = {"configurable": {"thread_id": st.session_state.thread_id}}
                
                if inputs_override:
                    inputs = inputs_override
                else:
                    return # Should not happen

                # Streaming Loop
                async for event in agent.astream(inputs, config=config):
                    # ... (keep existing processing logic)
                    if isinstance(event, dict):
                        for _, values in event.items():
                            if isinstance(values, dict) and "messages" in values:
                                msgs = values["messages"]
                                if isinstance(msgs, list) and msgs:
                                    last_msg = msgs[-1]
                                    if last_msg.type == "ai" and hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                                        for tc in last_msg.tool_calls:
                                            tool_name = tc.get("name")
                                            args = tc.get("args", {})
                                            status_container.write(f"🔧 Calling tool: **{tool_name}**")
                                            if tool_name in ["write_file", "edit_file"]:
                                                path = args.get("file_path")
                                                if path: st.session_state.preview_file = path
                                    
                                    if last_msg.type == "ai" and last_msg.content:
                                        content = last_msg.content
                                        if isinstance(content, list):
                                            text = "\n".join([b["text"] for b in content if "text" in b])
                                        else:
                                            text = str(content)
                                        local_accumulated_text = text
                                        response_placeholder.markdown(local_accumulated_text)
                
                # Check for interrupts (HITL) AFTER the stream finishes
                state = await agent.aget_state(config)
                if state.tasks and state.tasks[0].interrupts:
                    int_obj = state.tasks[0].interrupts[0]
                    st.session_state.interrupt_state = {
                        "id": int_obj.id,
                        "value": int_obj.value
                    }
                    st.rerun()
                
                return local_accumulated_text

            try:
                # Run the internal stream
                accumulated_text = await internal_stream()
                
                status_container.update(label="Complete", state="complete", expanded=False)
                if accumulated_text:
                    st.session_state.messages.append({"role": "assistant", "content": accumulated_text})
                
            except Exception as e:
                status_container.update(label="Error", state="error")
                st.error(f"Error: {e}")

    # Case 1: New Prompt
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Run agent
        inputs = {"messages": [HumanMessage(content=prompt)]}
        asyncio.run(run_agent_stream(inputs_override=inputs))

    # Case 2: Resuming (User clicked Approve/Reject)
    if st.session_state.get("resume_action") and st.session_state.get("interrupt_state"):
        try:
            # Construct resume payload
            int_id = st.session_state.interrupt_state["id"]
            reqs = st.session_state.interrupt_state["value"].get("action_requests", [])
            decision = st.session_state.resume_action
            
            decisions = [{"type": decision} for _ in reqs]
            resume_payload = {int_id: {"decisions": decisions}}
            inputs = Command(resume=resume_payload)
            
            # Clear interrupt state NOW
            del st.session_state.interrupt_state
            del st.session_state.resume_action
            
            # Run agent with timeout protection
            async def protected_run():
                try:
                    await asyncio.wait_for(run_agent_stream(inputs_override=inputs, is_resume=True), timeout=120)
                except asyncio.TimeoutError:
                    st.error("Operation timed out (2 minutes).")
            
            asyncio.run(protected_run())
            st.rerun() 
            
        except Exception as e:
            st.error(f"Critical Error during resume: {e}")
            # Ensure state is cleared so we don't loop
            if "interrupt_state" in st.session_state: del st.session_state.interrupt_state
            if "resume_action" in st.session_state: del st.session_state.resume_action

# --- Preview Logic (Right Column) ---
with preview_col:
    st.header("👁️ Preview")
    
    file_path = st.session_state.preview_file
    
    if file_path:
        path_obj = Path(file_path)
        if path_obj.exists():
            st.success(f"Previewing: `{path_obj.name}`")
            
            ext = path_obj.suffix.lower()
            
            try:
                # 1. Images
                if ext in ['.png', '.jpg', '.jpeg', '.webp']:
                    image = Image.open(path_obj)
                    st.image(image, caption=path_obj.name, use_container_width=True)
                
                # 2. Excel / CSV
                elif ext in ['.xlsx', '.xls', '.csv']:
                    if ext == '.csv':
                        df = pd.read_csv(path_obj)
                    else:
                        df = pd.read_excel(path_obj)
                    st.dataframe(df, use_container_width=True)
                
                # 3. Python / Code / Text
                elif ext in ['.py', '.json', '.md', '.txt', '.html', '.css', '.js']:
                    content = path_obj.read_text(encoding='utf-8')
                    st.code(content, language=ext.replace('.', ''))
                    
                # 4. Unknown
                else:
                    st.info("File type not supported for preview. Download manually.")
                    
            except Exception as e:
                st.error(f"Error previewing file: {e}")
        else:
            st.warning(f"File not found: `{file_path}`")
    else:
        st.info("Waiting for generated content...")
        st.markdown("*Ask the agent to create a file, analyze data, or generate an image.*")

# Handle resume logic is now integrated into the main flow above
# Removing redundant blocks
pass
