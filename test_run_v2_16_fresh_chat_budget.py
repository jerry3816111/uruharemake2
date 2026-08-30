import unittest

from run_v2_16_fresh_chat_budget import CHAT_WRAPPER_TOKEN_RESERVE, ChatBudgetTokenizer


class _Tokenizer:
    def encode(self, text, add_special_tokens=False):
        del add_special_tokens
        return str(text).split()


class ChatBudgetAdapterTests(unittest.TestCase):
    def test_reserve_is_fixed_and_condition_independent(self):
        tokenizer = ChatBudgetTokenizer(_Tokenizer())
        self.assertEqual(len(tokenizer.encode("one two")), CHAT_WRAPPER_TOKEN_RESERVE + 2)
        self.assertEqual(len(tokenizer.encode("different semantic text")), CHAT_WRAPPER_TOKEN_RESERVE + 3)


if __name__ == "__main__":
    unittest.main()
