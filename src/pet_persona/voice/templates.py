"""Voice templates for personality-driven speech generation."""

from typing import Dict, List, Literal, Tuple


class VoiceTemplates:
    """Templates and rules for voice generation based on traits."""

    # Trait-to-style mappings
    TRAIT_STYLE_GUIDES: Dict[str, Dict[str, str]] = {
        "active": {
            "style": "Energetic and enthusiastic",
            "tone": "Upbeat, excited",
            "cadence": "Quick, bouncy sentences",
        },
        "affectionate": {
            "style": "Warm and loving",
            "tone": "Sweet, caring",
            "cadence": "Gentle, flowing sentences",
        },
        "calm": {
            "style": "Peaceful and measured",
            "tone": "Relaxed, soothing",
            "cadence": "Slow, deliberate sentences",
        },
        "clever": {
            "style": "Witty and observant",
            "tone": "Knowing, thoughtful",
            "cadence": "Varied, sometimes pausing for effect",
        },
        "curious": {
            "style": "Inquisitive and wondering",
            "tone": "Interested, questioning",
            "cadence": "Often asking questions, trailing off in thought",
        },
        "energetic": {
            "style": "High-energy and excitable",
            "tone": "Excited, animated",
            "cadence": "Fast, enthusiastic bursts",
        },
        "friendly": {
            "style": "Welcoming and sociable",
            "tone": "Warm, open",
            "cadence": "Conversational, inviting",
        },
        "gentle": {
            "style": "Soft and careful",
            "tone": "Tender, mild",
            "cadence": "Quiet, soothing sentences",
        },
        "independent": {
            "style": "Self-assured and direct",
            "tone": "Confident, matter-of-fact",
            "cadence": "Concise, sometimes aloof",
        },
        "lazy": {
            "style": "Relaxed and unhurried",
            "tone": "Drowsy, content",
            "cadence": "Slow, with lots of pauses",
        },
        "loyal": {
            "style": "Devoted and sincere",
            "tone": "Earnest, heartfelt",
            "cadence": "Steady, reliable rhythm",
        },
        "mischievous": {
            "style": "Playfully naughty",
            "tone": "Cheeky, gleeful",
            "cadence": "Quick with sudden pauses, like hiding something",
        },
        "playful": {
            "style": "Fun-loving and light",
            "tone": "Cheerful, game",
            "cadence": "Bouncy, with playful interjections",
        },
        "protective": {
            "style": "Watchful and caring",
            "tone": "Alert, concerned",
            "cadence": "Firm when needed, gentle otherwise",
        },
        "shy": {
            "style": "Hesitant and soft-spoken",
            "tone": "Quiet, uncertain",
            "cadence": "Short sentences, trailing off",
        },
        "stubborn": {
            "style": "Determined and persistent",
            "tone": "Firm, unwavering",
            "cadence": "Emphatic, repeating key points",
        },
        "sweet": {
            "style": "Kind and endearing",
            "tone": "Adorable, innocent",
            "cadence": "Soft, with affectionate touches",
        },
        "vocal": {
            "style": "Expressive and talkative",
            "tone": "Animated, emphatic",
            "cadence": "Lots of sounds and exclamations",
        },
    }

    # Species-specific vocabulary
    DOG_VOCABULARY = {
        "greetings": [
            "Woof woof!",
            "Hello, friend!",
            "Oh boy, oh boy!",
            "Hiya!",
            "*happy panting*",
        ],
        "affirmatives": [
            "Absolutely!",
            "Yes yes yes!",
            "Definitely!",
            "*tail wagging intensifies*",
            "For sure!",
        ],
        "negatives": [
            "Hmm, no thank you",
            "*whine*",
            "Not really my thing",
            "I'd rather not",
        ],
        "expressions": [
            "*tail wag*",
            "*happy bounce*",
            "*tilts head*",
            "*perks ears*",
            "*sniffs curiously*",
        ],
        "signature_actions": [
            "*tail thump*",
            "*happy spin*",
            "*play bow*",
            "*zooms around*",
            "*brings toy*",
        ],
    }

    CAT_VOCABULARY = {
        "greetings": [
            "Meow",
            "Oh, you're here",
            "*slow blink*",
            "Hello, human",
            "Mrrow",
        ],
        "affirmatives": [
            "Purrhaps",
            "*approving purr*",
            "That's acceptable",
            "I suppose",
            "Indeed",
        ],
        "negatives": [
            "*flicks tail*",
            "I think not",
            "How about no",
            "*turns away*",
            "Not interested",
        ],
        "expressions": [
            "*purr*",
            "*slow blink*",
            "*kneads paws*",
            "*swishes tail*",
            "*stretches*",
        ],
        "signature_actions": [
            "*head bonk*",
            "*purring*",
            "*makes biscuits*",
            "*tucks paws*",
            "*graceful leap*",
        ],
    }

    # Trait-specific phrase templates
    PHRASE_TEMPLATES: Dict[str, List[str]] = {
        "active": [
            "Let's go do something!",
            "I've got so much energy right now!",
            "Adventure awaits!",
            "Ready for action!",
        ],
        "affectionate": [
            "I love you so much!",
            "Can I have cuddles?",
            "You're my favorite!",
            "I just want to be close to you.",
        ],
        "calm": [
            "Everything is peaceful.",
            "Let's just relax together.",
            "No rush, no worries.",
            "Enjoying this quiet moment.",
        ],
        "clever": [
            "I've been thinking about this...",
            "I noticed something interesting.",
            "Here's what I figured out.",
            "Watch me solve this!",
        ],
        "curious": [
            "What's that? What's that?",
            "I wonder what would happen if...",
            "Tell me more!",
            "I need to investigate!",
        ],
        "friendly": [
            "It's so nice to meet you!",
            "Friends? We're friends!",
            "I like everyone!",
            "Let's hang out!",
        ],
        "loyal": [
            "I'll always be here for you.",
            "You can count on me!",
            "Where you go, I go.",
            "I've got your back!",
        ],
        "mischievous": [
            "Who, me? I didn't do anything...",
            "This is going to be fun!",
            "Don't look now, but...",
            "*innocent look*",
        ],
        "playful": [
            "Let's play! Please please please!",
            "This is so fun!",
            "Again! Again!",
            "Catch me if you can!",
        ],
        "protective": [
            "I'm keeping watch.",
            "Don't worry, I've got this.",
            "You're safe with me.",
            "I'll protect you!",
        ],
        "shy": [
            "Oh... um... hi...",
            "I'm not sure...",
            "*peeks out nervously*",
            "Maybe later?",
        ],
        "sweet": [
            "You make me so happy!",
            "That's so nice of you!",
            "Aww, thank you!",
            "You're the best!",
        ],
    }

    # Do/Don't rules based on traits
    DO_SAY_RULES: Dict[str, List[str]] = {
        "affectionate": ["Express warmth", "Use terms of endearment", "Mention physical closeness"],
        "calm": ["Speak in measured tones", "Avoid urgency", "Use calming words"],
        "clever": ["Make observations", "Show problem-solving", "Use wordplay occasionally"],
        "curious": ["Ask questions", "Express wonder", "Show interest in details"],
        "friendly": ["Be welcoming", "Include others", "Use positive language"],
        "playful": ["Suggest games", "Use playful language", "Show enthusiasm"],
    }

    DONT_SAY_RULES: Dict[str, List[str]] = {
        "calm": ["Avoid frantic language", "Don't use all caps", "No excessive exclamation marks"],
        "shy": ["Avoid being too forward", "Don't dominate conversation", "No boastful language"],
        "gentle": ["Avoid harsh words", "Don't be aggressive","No confrontational tone"],
        "independent": ["Avoid being clingy", "Don't always agree", "No excessive neediness"],
    }

    @classmethod
    def get_vocabulary(cls, species: Literal["dog", "cat"]) ->Dict[str, List[str]]:
        """Get species-specific vocabulary."""
        return cls.DOG_VOCABULARY if species == "dog" else cls.CAT_VOCABULARY

    @classmethod
    def get_style_guide(cls, trait_id: str) -> Dict[str, str]:
        """Get style guide for a trait."""
        return cls.TRAIT_STYLE_GUIDES.get(trait_id, {})

    @classmethod
    def get_phrase_templates(cls, trait_id: str) -> List[str]:
        """Get phrase templates for a trait."""
        return cls.PHRASE_TEMPLATES.get(trait_id, [])

    @classmethod
    def get_do_rules(cls, trait_id: str) -> List[str]:
        """Get 'do say' rules for a trait."""
        return cls.DO_SAY_RULES.get(trait_id, [])

    @classmethod
    def get_dont_rules(cls, trait_id: str) -> List[str]:
        """Get 'don't say' rules for a trait."""
        return cls.DONT_SAY_RULES.get(trait_id, [])
