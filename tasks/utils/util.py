from pdf2zh_next.config.translate_engine_model import AzureOpenAISettings, OpenAISettings, QwenMtSettings


def generate_llm_settings(llm_parms):
    if 'azure' in llm_parms:
        return AzureOpenAISettings(**llm_parms['azure'])
    elif 'openai' in llm_parms:
        return OpenAISettings(**llm_parms['openai'])
    elif 'qwen' in llm_parms:
        return QwenMtSettings(**llm_parms['qwen'])
    else:
        raise ValueError("llm type not supported")