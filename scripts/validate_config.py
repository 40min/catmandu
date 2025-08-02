#!/usr/bin/env python3
"""
Configuration validation script for Catmandu.

This script validates the configuration without starting the full application,
useful for checking environment setup and troubleshooting configuration issues.
"""

import sys
from pathlib import Path

# Add src to path so we can import catmandu modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from catmandu.core.config import Settings  # noqa: E402
from catmandu.core.errors import AudioProcessingConfigurationError, ConfigurationError  # noqa: E402
from catmandu.logging import configure_logging  # noqa: E402


def main():
    """Main validation function."""
    print("🔍 Catmandu Configuration Validator")
    print("=" * 50)

    try:
        # Load and validate settings
        print("📋 Loading configuration...")
        settings = Settings()

        # Configure logging for validation
        configure_logging(settings.log_level)

        print("✅ Configuration loaded successfully")

        # Run environment validation
        print("\n🔧 Validating environment...")
        settings.validate_environment()

        # Test audio processing configuration specifically
        print("\n🎵 Checking audio processing configuration...")
        if settings.audio_processing_enabled:
            try:
                settings.validate_audio_processing_requirements()
                if settings.is_audio_processing_available():
                    print("✅ Audio processing is properly configured")
                    print(f"   - OpenAI API key: {'✓ Set' if settings.openai_api_key else '✗ Missing'}")
                    print(f"   - Max file size: {settings.max_audio_file_size_mb}MB")
                    print(f"   - Max duration: {settings.max_audio_duration_minutes} minutes")
                    print(f"   - Whisper cost: ${settings.whisper_cost_per_minute:.4f}/minute")
                    print(f"   - GPT-4o-mini input: ${settings.gpt4o_mini_input_cost_per_1m_tokens:.2f}/1M tokens")
                    print(f"   - GPT-4o-mini output: ${settings.gpt4o_mini_output_cost_per_1m_tokens:.2f}/1M tokens")
                else:
                    print("⚠️  Audio processing is enabled but not properly configured")
            except AudioProcessingConfigurationError as e:
                print(f"❌ Audio processing configuration error: {e}")
                return 1
        else:
            print("ℹ️  Audio processing is disabled")
            print("   To enable: set AUDIO_PROCESSING_ENABLED=true and provide OPENAI_API_KEY")

        # Check directory permissions
        print("\n📁 Checking directory permissions...")
        directories_to_check = [
            ("Chat logs", settings.chat_logs_dir),
            ("Cost logs", settings.cost_logs_dir),
            ("Cattackles", settings.cattackles_dir),
        ]

        for name, directory in directories_to_check:
            try:
                Path(directory).mkdir(parents=True, exist_ok=True)
                print(f"✅ {name} directory: {directory}")
            except Exception as e:
                print(f"⚠️  {name} directory issue: {e}")

        print("\n🎉 Configuration validation completed successfully!")
        print("\nYour Catmandu instance is ready to start.")
        return 0

    except ConfigurationError as e:
        print(f"\n❌ Configuration Error: {e}")
        print("\nPlease fix the configuration issues and try again.")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error during validation: {e}")
        print("\nThis might indicate a bug or system issue.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
