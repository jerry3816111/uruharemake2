"""One-key B4 summary alias normalizer with raw-response preservation."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable

from .baselines import _extract_json_object


class SummaryAliasProvider:
    def __init__(self,provider:Callable[...,dict[str,Any]]):
        self.provider=provider
        self.normalizations=[]

    def __call__(self,**kwargs):
        result=self.provider(**kwargs)
        try: prompt=json.loads(kwargs["prompt"])
        except (KeyError,TypeError,ValueError): return result
        if not str(prompt.get("task","")).startswith("Condense"):
            return result
        try: parsed=_extract_json_object(result["text"])
        except Exception: return result
        alias=parsed.get("behavior_prediction_summary")
        if isinstance(parsed.get("summary"),str) and parsed["summary"].strip():
            return result
        if not isinstance(alias,str) or not alias.strip():
            return result
        normalized_text=json.dumps({"summary":alias.strip()},ensure_ascii=False)
        self.normalizations.append({"prompt_sha256":hashlib.sha256(kwargs["prompt"].encode("utf-8")).hexdigest(),"raw_response":str(result["text"]),"raw_response_sha256":hashlib.sha256(str(result["text"]).encode("utf-8")).hexdigest(),"source_key":"behavior_prediction_summary","normalized_key":"summary","normalized_response_sha256":hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()})
        return {**result,"text":normalized_text}
