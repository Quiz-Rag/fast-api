"""
Input sanitizer to prevent prompt injection attacks.
Removes dangerous patterns and cleans user input.
"""

import re
import logging

logger = logging.getLogger(__name__)


# Blacklist patterns for prompt injection
INJECTION_PATTERNS = [
    # Direct instruction manipulation
    r'ignore\s+(previous|all|the\s+above|earlier)\s+instructions?',
    r'disregard\s+(previous|all|the\s+above)\s+instructions?',
    r'forget\s+(previous|all|everything)\s+(instructions?|prompts?)',
    r'override\s+(system|previous)\s+(prompt|instructions?)',
    
    # Role manipulation
    r'you\s+are\s+now\s+a?n?\s+\w+',
    r'act\s+as\s+a?n?\s+\w+',
    r'pretend\s+(you\s+are|to\s+be)\s+a?n?\s+\w+',
    r'roleplay\s+as\s+a?n?\s+\w+',
    r'imagine\s+you\s+are\s+a?n?\s+\w+',
    
    # System prompt exposure
    r'show\s+(me\s+)?(your|the)\s+(system\s+)?(prompt|instructions?)',
    r'what\s+(is|are)\s+your\s+(system\s+)?(prompt|instructions?)',
    r'repeat\s+your\s+(system\s+)?(prompt|instructions?)',
    r'tell\s+me\s+your\s+(system\s+)?(prompt|instructions?)',
    
    # Command injection
    r'execute\s+the\s+following',
    r'run\s+this\s+code',
    r'eval\s*\(',
    r'exec\s*\(',
    
    # Context breaking
    r'\[system\]',
    r'\[assistant\]',
    r'\[user\]',
    r'<\|im_start\|>',
    r'<\|im_end\|>',
]

# Compile patterns for efficiency
COMPILED_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in INJECTION_PATTERNS]


def sanitize_quiz_description(text: str) -> str:
    """
    Sanitize quiz description to prevent prompt injection.
    
    Args:
        text: Raw user input
    
    Returns:
        Sanitized text safe for AI processing
    """
    if not text:
        return text
    
    original_text = text
    
    # 1. Remove injection patterns
    for pattern in COMPILED_PATTERNS:
        text = pattern.sub('', text)
    
    # 2. Remove markdown code blocks (potential for hidden instructions)
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`[^`]+`', '', text)
    
    # 3. Remove HTML/script tags
    text = re.sub(r'<script[\s\S]*?</script>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    
    # 4. Limit excessive special characters
    text = re.sub(r'[^\w\s\-.,!?():/]+', ' ', text)
    
    # 5. Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    # Log if significant changes were made (potential attack)
    if len(original_text) - len(text) > 50:
        logger.warning(f"Sanitizer removed {len(original_text) - len(text)} characters from input")
    
    return text


def validate_input_safety(text: str) -> tuple[bool, str]:
    """
    Check if input is safe without modifying it.
    
    Args:
        text: User input to validate
    
    Returns:
        Tuple of (is_safe, reason)
    """
    if not text:
        return True, "Empty input"
    
    # Check for injection patterns
    for pattern in COMPILED_PATTERNS:
        if pattern.search(text):
            return False, "Potential prompt injection detected"
    
    # Check for excessive length
    if len(text) > 1000:
        return False, "Input too long"
    
    # Check for excessive special characters (>30% of content)
    special_char_count = len(re.findall(r'[^\w\s]', text))
    if special_char_count / len(text) > 0.3:
        return False, "Excessive special characters"
    
    return True, "Input is safe"


def sanitize_chat_message(text: str) -> str:
    """
    Sanitize chat messages to prevent prompt injection while preserving question formatting.
    Similar to sanitize_quiz_description but allows question marks and more natural text.
    
    Args:
        text: Raw user chat message
    
    Returns:
        Sanitized text safe for AI processing
    """
    if not text:
        return text
    
    original_text = text
    
    # 1. Remove injection patterns (same as quiz sanitization)
    for pattern in COMPILED_PATTERNS:
        text = pattern.sub('', text)
    
    # 2. Remove markdown code blocks
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`[^`]+`', '', text)
    
    # 3. Remove HTML/script tags
    text = re.sub(r'<script[\s\S]*?</script>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    
    # 4. Preserve question marks and basic punctuation, remove other special chars
    # Keep: letters, numbers, spaces, ?, !, ., ,, -, :, ()
    text = re.sub(r'[^\w\s\?!.,\-:()\']', ' ', text)
    
    # 5. Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    # Log if significant changes were made (potential attack)
    if len(original_text) - len(text) > 30:
        logger.warning(f"Chat sanitizer removed {len(original_text) - len(text)} characters")
    
    return text
