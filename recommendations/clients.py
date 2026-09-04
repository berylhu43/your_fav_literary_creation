import os
from functools import lru_cache
from openai import OpenAI

@lru_cache(maxsize=1)
def _get_client():
    return OpenAI(
        api_key=os.environ['DEEPSEEK_API_KEY'],
        base_url='https://api.deepseek.com', 
    )


def _llm_get(messages, model='deepseek-v4-flash', json_mode=True, temperature=None,
             thinking=None, reasoning_effort=None):
    """
    Low-level: query DeepSeek API, handling timeout/errors.
    Returns the raw response string, or None on failure.
    """
    _client = _get_client()
    try:
        kwargs = {
            'model': model,
            'messages': messages,
            'timeout': 60,
        }
        if json_mode:
            kwargs['response_format'] = {'type': 'json_object'}
        if temperature is not None:
            kwargs['temperature'] = temperature
        if thinking is not None:
            kwargs['extra_body'] = {'thinking': thinking}
        if reasoning_effort is not None:
            kwargs['reasoning_effort'] = reasoning_effort

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