import os
import pytest
import importlib
from unittest.mock import AsyncMock, patch

# Ensure simulation mode is tested
os.environ["PLAXIS_SIMULATION_MODE"] = "true"

from plaxis_connection import connection_manager
from agent import PlaxisAgentSwarm, _call_llm
from tools.structures import create_plate
from tools.phases import set_water_level
from providers.base import LLMProvider
from providers.ollama_provider import OllamaProvider

@pytest.mark.asyncio
async def test_no_api_keys_friendly_message():
    """Verify missing API keys don't crash and return the config warning."""
    mock1 = AsyncMock()
    mock1.name = "Mock1"
    mock1.generate_response.side_effect = ValueError("No API key")
    
    mock2 = AsyncMock()
    mock2.name = "Mock2"
    mock2.generate_response.side_effect = ValueError("No API key")
    
    response = await _call_llm([mock1, mock2], "system", "prompt")
    
    assert "tool_calls" in response
    assert response["tool_calls"] == []
    assert "AI Execution Failure" in response["message"]

def test_simulation_mode_env_forced():
    """Verify PLAXIS_SIMULATION_MODE forces mock connection."""
    connection_manager.connect()
    assert connection_manager.is_simulation is True
    assert connection_manager.g_i is not None
    assert connection_manager.is_connected is True

def test_structures_fallback_commands():
    """Verify structures wrap wrapper failures with native CLI commands."""
    connection_manager.connect()
    
    # Inject a failure into the MockServer to ensure the fallback triggers
    original_getattr = connection_manager.g_i.__class__.__getattr__
    
    def failing_getattr(self, name):
        if name == "plate":
            def failing_func(*args, **kwargs):
                raise Exception("Wrapper plate() removed in this PLAXIS version!")
            return failing_func
        return original_getattr(self, name)
        
    connection_manager.g_i.__class__.__getattr__ = failing_getattr
    
    with patch.object(connection_manager, 'call_command') as mock_call:
        create_plate([0, 0, 0, 10, 0, 0, 10, 10, 0])
        # Verify fallback command was executed natively
        mock_call.assert_any_call("plate 0 0 0 10 0 0 10 10 0", server='input')
        
    # Restore
    connection_manager.g_i.__class__.__getattr__ = original_getattr

def test_set_water_level_fallback():
    """Verify set_water_level wraps direct attribute assignment with native CLI."""
    connection_manager.connect()
    
    # Force the object returned by find_object_by_name to throw on assignment
    class FailingObject:
        @property
        def WaterLevel(self): return 0
        @WaterLevel.setter
        def WaterLevel(self, val): raise AttributeError("Cannot set WaterLevel directly")
        
        @property
        def Name(self):
            class N: value = "Phase_Test"
            return N()
            
    with patch.object(connection_manager, 'find_object_by_name', return_value=FailingObject()):
        with patch.object(connection_manager, 'call_command') as mock_call:
            set_water_level("Phase_Test", -5.5)
            # Verify fallback command
            mock_call.assert_called_with("set Phase_Test.WaterLevel -5.5", server='input')

@pytest.mark.asyncio
async def test_ollama_provider_implements_async_generate_response():
    """Verify Ollama exposes the async provider interface used by the swarm."""
    provider = OllamaProvider()

    with patch.object(provider, "get_response", return_value='{"tool_calls":[],"message":"ok"}') as mock_get:
        response = await provider.generate_response("system", "prompt")

    assert response == '{"tool_calls":[],"message":"ok"}'
    mock_get.assert_called_once_with("prompt", "system")
    assert OllamaProvider.generate_response is not LLMProvider.generate_response

def test_app_main_keeps_process_alive_after_successful_browser_open():
    """Verify the keep-alive loop runs even when browser launch succeeds."""
    import app

    with patch.object(app, "_run_server") as mock_run_server, \
         patch("threading.Thread") as mock_thread_cls, \
         patch("webbrowser.open", return_value=True) as mock_browser_open, \
         patch("time.sleep", side_effect=[None, KeyboardInterrupt]), \
         patch("sys.exit", side_effect=SystemExit) as mock_exit:
        mock_thread = mock_thread_cls.return_value
        mock_thread.start.return_value = None

        with pytest.raises(SystemExit):
            app_globals = app.__dict__
            app_globals["__name__"] = "__main__"
            exec(compile(open(app.__file__, "r", encoding="utf-8").read(), app.__file__, "exec"), app_globals)

    mock_thread_cls.assert_called_once()
    mock_thread.start.assert_called_once()
    mock_browser_open.assert_called_once_with("http://127.0.0.1:8501")
    mock_exit.assert_called_once_with(0)
