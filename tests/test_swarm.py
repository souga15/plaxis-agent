import os
import pytest
from unittest.mock import AsyncMock, patch

# Ensure simulation mode is tested
os.environ["PLAXIS_SIMULATION_MODE"] = "true"

from plaxis_connection import connection_manager
from agent import PlaxisAgentSwarm, _call_llm
from tools.structures import create_plate
from tools.phases import set_water_level

@pytest.mark.asyncio
async def test_no_api_keys_friendly_message():
    """Verify missing API keys don't crash and return the config warning."""
    gemini_mock = AsyncMock()
    gemini_mock.generate_response.side_effect = ValueError("No API key")
    
    groq_mock = AsyncMock()
    groq_mock.generate_response.side_effect = ValueError("No API key")
    
    response = await _call_llm(gemini_mock, groq_mock, "system", "prompt")
    
    assert "tool_calls" in response
    assert response["tool_calls"] == []
    assert "⚠️ **Configuration Required**" in response["message"]

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
