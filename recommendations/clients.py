import os
from openai import OpenAI

_client = OpenAI(
    api_key=os.getenv('DEEPSEEK_API_KEY'),
    base_url='https://api.deepseek.com',
)

def _llm_get(messages, model='deepseek-v4-flash', json_mode=True, temperature=None):
    """
    Low-level: query DeepSeek API, handling timeout/errors.
    Returns the raw response string, or None on failure.
    """
    try:
        kwargs = {
            'model': model,
            'messages': messages,
            'timeout': 30,
        }
        if json_mode:
            kwargs['response_format'] = {'type': 'json_object'}
        if temperature is not None:
            kwargs['temperature'] = temperature

        response = _client.chat.completions.create(**kwargs)
        usage = response.usage

        print(f'>>> _llm_get [{model}] '
              f'all_usage: {usage}'
              f'prompt={usage.prompt_tokens} '
              f'completion={usage.completion_tokens} '
              f'total={usage.total_tokens}')

        return response.choices[0].message.content

    except Exception as e:
        print(f'>>> _llm_get FAILED: {e}')
        return None