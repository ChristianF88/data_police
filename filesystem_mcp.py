import os
import asyncio
import json
import subprocess
from typing import Optional, Dict, Any

class MCPFilesystemClient:
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.process = None
        
    async def start_server(self) -> bool:
        """Start the MCP filesystem server as a subprocess."""
        # Check if npx is available
        try:
            subprocess.run(["npx", "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError("npx is not available. Please install Node.js and npm.")
        
        # Start the server process
        self.process = await asyncio.create_subprocess_exec(
            "npx", "-y", "@modelcontextprotocol/server-filesystem", self.project_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Wait a moment for server to start
        await asyncio.sleep(2)
        
        # Check if process is still running
        if self.process.returncode is not None:
            stderr = await self.process.stderr.read()
            raise RuntimeError(f"MCP server failed to start: {stderr.decode()}")
        
        return True
    
    async def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a JSON-RPC request to the MCP server."""
        if not self.process or self.process.returncode is not None:
            raise RuntimeError("MCP server is not running")
        
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {}
        }
        
        request_json = json.dumps(request) + "\n"
        
        try:
            # Send request
            self.process.stdin.write(request_json.encode())
            await self.process.stdin.drain()
            
            # Read response with timeout
            response_line = await asyncio.wait_for(
                self.process.stdout.readline(),
                timeout=15.0
            )
            
            if not response_line:
                raise RuntimeError("No response from MCP server")
            
            response = json.loads(response_line.decode().strip())
            
            if "error" in response:
                raise RuntimeError(f"MCP server error: {response['error']}")
            
            return response.get("result", {})
            
        except asyncio.TimeoutError:
            raise RuntimeError("MCP server request timed out")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON response from MCP server: {e}")
    
    async def initialize(self) -> Dict[str, Any]:
        """Initialize the MCP server."""
        result = await self.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "clientInfo": {
                "name": "project-validator",
                "version": "1.0.0"
            }
        })
        return result
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific tool."""
        result = await self.send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })
        return result
    
    async def close(self):
        """Close the MCP server."""
        if self.process:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()

# Synchronous wrapper functions for Streamlit
def run_async(coro):
    """Run async function in Streamlit context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is already running, create a new thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        # No event loop, create new one
        return asyncio.run(coro)

async def get_project_guidelines(client: MCPFilesystemClient, project_path: str, policy_content: Optional[str] = None) -> str:
    """Get project guidelines from policy.txt or provided content."""
    if policy_content and policy_content.strip():
        return policy_content
    
    # Try to find policy.txt in the project
    try:
        policy_path = os.path.join(project_path, "policy.txt")
        result = await client.call_tool("read_file", {"path": policy_path})
        content = result.get("content", [])
        if content and isinstance(content, list) and len(content) > 0:
            return content[0].get("text", "")
        return str(result.get("content", ""))
    except Exception:
        pass
    
    # Try parent directory
    try:
        parent_dir = os.path.dirname(project_path)
        policy_path = os.path.join(parent_dir, "policy.txt")
        result = await client.call_tool("read_file", {"path": policy_path})
        content = result.get("content", [])
        if content and isinstance(content, list) and len(content) > 0:
            return content[0].get("text", "")
        return str(result.get("content", ""))
    except Exception:
        pass
    
    raise FileNotFoundError("policy.txt not found and no policy content provided")

def list_project_structure_sync(project_path: str) -> list:
    """List all files and directories in the project recursively (synchronous version)."""
    def get_files_recursive(path):
        files = []
        try:
            for item in os.listdir(path):
                if item.startswith('.'):  # Skip hidden files
                    continue
                    
                item_path = os.path.join(path, item)
                relative_path = os.path.relpath(item_path, project_path)
                
                if os.path.isfile(item_path):
                    files.append(relative_path)
                elif os.path.isdir(item_path):
                    files.append(f"{relative_path}/")
                    # Recursively get files from subdirectories
                    subfiles = get_files_recursive(item_path)
                    files.extend(subfiles)
        except PermissionError:
            pass
        return files
    
    return sorted(get_files_recursive(project_path))

async def run_validation_async(project_path: str, llm_provider: str, model: str, api_key: str, policy_content: Optional[str] = None) -> Dict[str, Any]:
    """Run the complete validation pipeline asynchronously."""
    client = MCPFilesystemClient(project_path)
    
    try:
        # Start MCP server
        await client.start_server()
        await client.initialize()
        
        # Get policy
        policy = await get_project_guidelines(client, project_path, policy_content)
        
        # Get project structure (using sync version for reliability)
        project_files = list_project_structure_sync(project_path)
        
        # Evaluate with LLM
        if llm_provider == "OpenAI":
            from openai import AsyncOpenAI
            llm_client = AsyncOpenAI(api_key=api_key)
            response = await llm_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a software project structure reviewer. Analyze project structures against given policies and provide detailed feedback."},
                    {"role": "user", "content": f"Project Structure Policy:\n{policy}\n\nActual Project Files:\n{chr(10).join(project_files)}\n\nPlease analyze whether the project structure follows the policy guidelines. Identify any missing components, incorrect organization, or deviations from the expected structure."}
                ],
                max_tokens=2000
            )
            report = response.choices[0].message.content
            
        elif llm_provider == "Anthropic":
            import anthropic
            llm_client = anthropic.AsyncAnthropic(api_key=api_key)
            response = await llm_client.messages.create(
                model=model,
                max_tokens=2000,
                system="You are a software project structure reviewer. Analyze project structures against given policies and provide detailed feedback.",
                messages=[{"role": "user", "content": f"Project Structure Policy:\n{policy}\n\nActual Project Files:\n{chr(10).join(project_files)}\n\nPlease analyze whether the project structure follows the policy guidelines. Identify any missing components, incorrect organization, or deviations from the expected structure."}]
            )
            report = response.content[0].text
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")
        
        return {
            "success": True,
            "policy": policy,
            "project_files": project_files,
            "report": report
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        await client.close()

def run_validation(project_path: str, llm_provider: str, model: str, api_key: str, policy_content: Optional[str] = None) -> Dict[str, Any]:
    """Synchronous wrapper for validation pipeline."""
    return run_async(run_validation_async(project_path, llm_provider, model, api_key, policy_content))