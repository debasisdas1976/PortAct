"""Add multi-provider AI settings (API keys, endpoints, models)

Revision ID: p2q3r4s5t6u7
Revises: o1p2q3r4s5t6
Create Date: 2026-02-22
"""
from alembic import op

revision = 'p2q3r4s5t6u7'
down_revision = 'o1p2q3r4s5t6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Insert new AI provider settings; ON CONFLICT DO NOTHING for idempotency
    op.execute("""
        INSERT INTO app_settings (key, value, value_type, category, label, description) VALUES
        ('ai_openai_api_key',    '', 'secret', 'ai', 'OpenAI API Key',           'API key for OpenAI. Leave blank to use the .env value.'),
        ('ai_grok_api_key',      '', 'secret', 'ai', 'Grok API Key',             'API key for Grok (xAI). Leave blank to use the .env value.'),
        ('ai_gemini_api_key',    '', 'secret', 'ai', 'Google Gemini API Key',     'API key for Google Gemini.'),
        ('ai_anthropic_api_key', '', 'secret', 'ai', 'Anthropic Claude API Key',  'API key for Anthropic Claude.'),
        ('ai_deepseek_api_key',  '', 'secret', 'ai', 'DeepSeek API Key',          'API key for DeepSeek.'),
        ('ai_mistral_api_key',   '', 'secret', 'ai', 'Mistral API Key',           'API key for Mistral AI.'),
        ('ai_openai_endpoint',    'https://api.openai.com/v1/chat/completions',                              'string', 'ai', 'OpenAI Endpoint',    'OpenAI API endpoint URL.'),
        ('ai_grok_endpoint',      'https://api.x.ai/v1/chat/completions',                                    'string', 'ai', 'Grok Endpoint',      'Grok API endpoint URL.'),
        ('ai_gemini_endpoint',    'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions', 'string', 'ai', 'Gemini Endpoint',    'Gemini OpenAI-compatible endpoint URL.'),
        ('ai_anthropic_endpoint', 'https://api.anthropic.com/v1/messages',                                    'string', 'ai', 'Anthropic Endpoint', 'Anthropic Messages API endpoint URL.'),
        ('ai_deepseek_endpoint',  'https://api.deepseek.com/chat/completions',                                'string', 'ai', 'DeepSeek Endpoint',  'DeepSeek API endpoint URL.'),
        ('ai_mistral_endpoint',   'https://api.mistral.ai/v1/chat/completions',                               'string', 'ai', 'Mistral Endpoint',   'Mistral API endpoint URL.'),
        ('ai_openai_model',    'gpt-3.5-turbo',              'string', 'ai', 'OpenAI Model',    'OpenAI model name.'),
        ('ai_grok_model',      'grok-beta',                  'string', 'ai', 'Grok Model',      'Grok model name.'),
        ('ai_gemini_model',    'gemini-2.0-flash',           'string', 'ai', 'Gemini Model',    'Gemini model name.'),
        ('ai_anthropic_model', 'claude-sonnet-4-20250514',   'string', 'ai', 'Anthropic Model', 'Anthropic Claude model name.'),
        ('ai_deepseek_model',  'deepseek-chat',              'string', 'ai', 'DeepSeek Model',  'DeepSeek model name.'),
        ('ai_mistral_model',   'mistral-small-latest',       'string', 'ai', 'Mistral Model',   'Mistral model name.')
        ON CONFLICT (key) DO NOTHING;
    """)

    # Update existing ai_news_provider description to list all providers
    op.execute("""
        UPDATE app_settings
        SET description = 'Which AI provider to use: openai, grok, gemini, anthropic, deepseek, mistral.'
        WHERE key = 'ai_news_provider';
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM app_settings WHERE key IN (
            'ai_openai_api_key', 'ai_grok_api_key', 'ai_gemini_api_key',
            'ai_anthropic_api_key', 'ai_deepseek_api_key', 'ai_mistral_api_key',
            'ai_openai_endpoint', 'ai_grok_endpoint', 'ai_gemini_endpoint',
            'ai_anthropic_endpoint', 'ai_deepseek_endpoint', 'ai_mistral_endpoint',
            'ai_openai_model', 'ai_grok_model', 'ai_gemini_model',
            'ai_anthropic_model', 'ai_deepseek_model', 'ai_mistral_model'
        );
    """)
    op.execute("""
        UPDATE app_settings
        SET description = 'Which AI provider to use for generating portfolio news alerts (openai or grok).'
        WHERE key = 'ai_news_provider';
    """)
