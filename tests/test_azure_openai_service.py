"""Simple test for Azure OpenAI service."""

from openai import AzureOpenAI

from services.azure_openai_service import AzureOpenAIService


def test_get_client():
    """Test getting an Azure OpenAI client."""
    client = AzureOpenAIService.get_client()
    assert isinstance(client, AzureOpenAI)
    assert client is not None


def test_get_client_specific_model():
    """Test getting a client for a specific model."""
    client = AzureOpenAIService.get_client(model="gpt-4.1-mini")
    assert isinstance(client, AzureOpenAI)


def test_get_available_models():
    """Test getting available models."""
    models = AzureOpenAIService.get_available_models()
    assert isinstance(models, list)
    assert len(models) > 0
    assert "gpt-4.1-mini" in models


def test_client_caching():
    """Test that clients are cached."""
    client1 = AzureOpenAIService.get_client(model="gpt-4.1-mini")
    client2 = AzureOpenAIService.get_client(model="gpt-4.1-mini")
    assert client1 is client2  # Same instance (cached)


def test_simple_chat_completion():
    """Test a simple chat completion call."""
    client = AzureOpenAIService.get_client()

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": "Say 'hello'"}],
        max_tokens=10,
    )

    assert response is not None
    assert len(response.choices) > 0
    assert response.choices[0].message.content is not None
    print(f"Response: {response.choices[0].message.content}")
