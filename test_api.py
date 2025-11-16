"""
Example script to test the NeuTTS Air Voice Cloning API
"""
import requests
import time

API_BASE_URL = "http://localhost:8000"

def test_health():
    """Test API health endpoint"""
    print("\n=== Testing Health Endpoint ===")
    response = requests.get(f"{API_BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def clone_voice(audio_file_path, voice_name, reference_text=None):
    """Clone a voice from an audio file"""
    print(f"\n=== Cloning Voice: {voice_name} ===")
    with open(audio_file_path, "rb") as f:
        files = {"file": f}
        data = {"voice_name": voice_name}
        if reference_text:
            data["reference_text"] = reference_text

        response = requests.post(
            f"{API_BASE_URL}/voices/clone",
            files=files,
            data=data
        )

    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def list_voices():
    """List all cloned voices"""
    print("\n=== Listing All Voices ===")
    response = requests.get(f"{API_BASE_URL}/voices")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Total voices: {len(data['voices'])}")
    for voice in data['voices']:
        print(f"  - {voice['name']} (ID: {voice['id']})")
    return response.status_code == 200

def generate_speech(text, voice_name, output_file="generated_speech.wav"):
    """Generate speech from text using a cloned voice"""
    print(f"\n=== Generating Speech with {voice_name} ===")
    print(f"Text: {text}")

    response = requests.post(
        f"{API_BASE_URL}/tts/generate",
        data={
            "text": text,
            "voice_name": voice_name
        }
    )

    if response.status_code == 200:
        with open(output_file, "wb") as f:
            f.write(response.content)
        print(f"Status: {response.status_code}")
        print(f"Audio saved to: {output_file}")
        return True
    else:
        print(f"Error: {response.status_code}")
        print(f"Response: {response.text}")
        return False

def delete_voice(voice_name):
    """Delete a cloned voice"""
    print(f"\n=== Deleting Voice: {voice_name} ===")
    response = requests.delete(f"{API_BASE_URL}/voices/{voice_name}")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def main():
    """Run the full test suite"""
    print("=" * 60)
    print("NeuTTS Air Voice Cloning API - Test Suite")
    print("=" * 60)

    # Test health
    if not test_health():
        print("\n❌ API is not healthy. Please check if the container is running.")
        print("Run: docker-compose up -d")
        return

    print("\n✓ API is healthy and ready!")

    # Example usage (modify as needed)
    print("\n" + "=" * 60)
    print("To use this script:")
    print("1. Place your reference audio file (e.g., 'my_voice.wav') in this directory")
    print("2. Uncomment and modify the example code below")
    print("=" * 60)

    # Uncomment below to test voice cloning
    # Replace 'my_voice.wav' with your actual audio file
    """
    # Clone a voice
    if clone_voice(
        audio_file_path="my_voice.wav",
        voice_name="my_cloned_voice",
        reference_text="This is a sample of my voice"
    ):
        # Wait a moment for processing
        time.sleep(2)

        # List voices
        list_voices()

        # Generate speech
        generate_speech(
            text="Hello! This is a test of voice cloning technology. How do I sound?",
            voice_name="my_cloned_voice",
            output_file="test_output.wav"
        )

        # Optionally delete the voice
        # delete_voice("my_cloned_voice")
    """

if __name__ == "__main__":
    main()
