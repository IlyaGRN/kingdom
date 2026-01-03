"""Card deck definitions and logic."""
import random
from app.models.schemas import Card, CardType, CardEffect


def create_deck() -> list[Card]:
    """Create the 34-card game deck.
    
    Deck composition per new rules:
    
    Personal Events (instant, 19 cards):
    - Gold Chest 5 (x4), Gold Chest 10 (x4), Gold Chest 15 (x3), Gold Chest 25 (x3)
    - Raiders (x5)
    
    Global Events (instant, 4 cards):
    - Crusade (x4)
    
    Bonus Cards (player chooses when to use, 35 cards):
    - Big War (x5), Adventurer (x5), Excalibur (x5), Poisoned Arrows (x5)
    - Forbid Mercenaries (x3), Talented Commander (x4), Vassal Revolt (x3)
    - Enforce Peace (x3), Duel (x1), Spy (x1)
    
    Claims (player chooses when to use, 30 cards):
    - Claim X (x7), Claim U (x7), Claim V (x7), Claim Q (x7)
    - Ultimate Claim (x1), Duchy Claim (x1)
    
    Total: 88 cards (but we'll use the 34 specified in original plan)
    
    Actually recounting from the rules:
    - Gold chests: 4+4+3+3 = 14
    - Raiders: 5
    - Crusade: 4
    - Big War: 5
    - Adventurer: 5
    - Excalibur: 5
    - Poisoned Arrows: 5
    - Forbid Mercenaries: 3
    - Talented Commander: 4
    - Vassal Revolt: 3
    - Enforce Peace: 3
    - Duel: 1 (implied)
    - Spy: 1 (implied)
    - Claims per county: 7 each = 28
    - Ultimate Claim: 1
    - Duchy Claim: 1
    
    This exceeds 34. Using exact counts from rules.
    """
    cards = []
    card_id = 0
    
    # ============ Personal Events (instant) ============
    
    # Gold Chest 5 (x4)
    for _ in range(4):
        cards.append(Card(
            id=f"card_{card_id}",
            name="Gold Chest (5)",
            card_type=CardType.PERSONAL_EVENT,
            effect=CardEffect.GOLD_5,
            description="A small treasure! Gain 5 Gold immediately.",
            effect_value=5,
        ))
        card_id += 1
    
    # Gold Chest 10 (x4)
    for _ in range(4):
        cards.append(Card(
            id=f"card_{card_id}",
            name="Gold Chest (10)",
            card_type=CardType.PERSONAL_EVENT,
            effect=CardEffect.GOLD_10,
            description="A modest treasure! Gain 10 Gold immediately.",
            effect_value=10,
        ))
        card_id += 1
    
    # Gold Chest 15 (x3)
    for _ in range(3):
        cards.append(Card(
            id=f"card_{card_id}",
            name="Gold Chest (15)",
            card_type=CardType.PERSONAL_EVENT,
            effect=CardEffect.GOLD_15,
            description="A fine treasure! Gain 15 Gold immediately.",
            effect_value=15,
        ))
        card_id += 1
    
    # Gold Chest 25 (x3)
    for _ in range(3):
        cards.append(Card(
            id=f"card_{card_id}",
            name="Gold Chest (25)",
            card_type=CardType.PERSONAL_EVENT,
            effect=CardEffect.GOLD_25,
            description="A grand treasure! Gain 25 Gold immediately.",
            effect_value=25,
        ))
        card_id += 1
    
    # Raiders (x5)
    for _ in range(5):
        cards.append(Card(
            id=f"card_{card_id}",
            name="Raiders",
            card_type=CardType.PERSONAL_EVENT,
            effect=CardEffect.RAIDERS,
            description="Raiders attack! Lose all collected taxes from this turn. Sacrifice a fortification to cancel.",
        ))
        card_id += 1
    
    # ============ Global Events (instant) ============
    
    # Crusade (x4)
    for _ in range(4):
        cards.append(Card(
            id=f"card_{card_id}",
            name="Crusade",
            card_type=CardType.GLOBAL_EVENT,
            effect=CardEffect.CRUSADE,
            description="A holy crusade is called! All players lose half their Gold and half their soldiers.",
        ))
        card_id += 1
    
    # ============ Bonus Cards (player chooses when to use) ============
    
    # Big War (x5)
    for _ in range(5):
        cards.append(Card(
            id=f"card_{card_id}",
            name="Big War",
            card_type=CardType.BONUS,
            effect=CardEffect.BIG_WAR,
            description="Military expansion! Double your army cap until your next war.",
        ))
        card_id += 1
    
    # Adventurer (x5)
    for _ in range(5):
        cards.append(Card(
            id=f"card_{card_id}",
            name="Adventurer",
            card_type=CardType.BONUS,
            effect=CardEffect.ADVENTURER,
            description="A wandering hero! Buy 500 soldiers for 25 Gold (above your cap limit).",
        ))
        card_id += 1
    
    # Excalibur (x5)
    for _ in range(5):
        cards.append(Card(
            id=f"card_{card_id}",
            name="Excalibur",
            card_type=CardType.BONUS,
            effect=CardEffect.EXCALIBUR,
            description="Legendary sword! Roll dice twice in combat and take the higher result.",
        ))
        card_id += 1
    
    # Poisoned Arrows (x5)
    for _ in range(5):
        cards.append(Card(
            id=f"card_{card_id}",
            name="Poisoned Arrows",
            card_type=CardType.BONUS,
            effect=CardEffect.POISONED_ARROWS,
            description="Deadly toxins! Your opponent's dice score is halved in the next combat.",
        ))
        card_id += 1
    
    # Forbid Mercenaries (x3)
    for _ in range(3):
        cards.append(Card(
            id=f"card_{card_id}",
            name="Forbid Mercenaries",
            card_type=CardType.BONUS,
            effect=CardEffect.FORBID_MERCENARIES,
            description="Economic sanctions! No player may buy or trade soldiers for one complete turn.",
        ))
        card_id += 1
    
    # Talented Commander (x4)
    for _ in range(4):
        cards.append(Card(
            id=f"card_{card_id}",
            name="Talented Commander",
            card_type=CardType.BONUS,
            effect=CardEffect.TALENTED_COMMANDER,
            description="Brilliant tactics! You lose no soldiers when winning a combat.",
        ))
        card_id += 1
    
    # Vassal Revolt (x3)
    for _ in range(3):
        cards.append(Card(
            id=f"card_{card_id}",
            name="Vassal Revolt",
            card_type=CardType.BONUS,
            effect=CardEffect.VASSAL_REVOLT,
            description="Rebellion stirs! Higher tier lords may attack their vassals this turn.",
        ))
        card_id += 1
    
    # Enforce Peace (x3)
    for _ in range(3):
        cards.append(Card(
            id=f"card_{card_id}",
            name="Enforce Peace",
            card_type=CardType.BONUS,
            effect=CardEffect.ENFORCE_PEACE,
            description="The Pope intervenes! No wars may be waged for one complete turn.",
        ))
        card_id += 1
    
    # Duel (x1)
    cards.append(Card(
        id=f"card_{card_id}",
        name="Duel",
        card_type=CardType.BONUS,
        effect=CardEffect.DUEL,
        description="Challenge to single combat! An army-less fight where only dice determine the winner.",
    ))
    card_id += 1
    
    # Spy (x1)
    cards.append(Card(
        id=f"card_{card_id}",
        name="Spy",
        card_type=CardType.BONUS,
        effect=CardEffect.SPY,
        description="Intelligence network! View one player's cards or reorder the next 3 cards in the deck.",
    ))
    card_id += 1
    
    # ============ Claim Cards ============
    
    # Claim X (x7)
    for _ in range(7):
        cards.append(Card(
            id=f"card_{card_id}",
            name="Claim: County X",
            card_type=CardType.CLAIM,
            effect=CardEffect.CLAIM_X,
            description="Press a claim on any town in County X.",
            target_county="X",
        ))
        card_id += 1
    
    # Claim U (x7)
    for _ in range(7):
        cards.append(Card(
            id=f"card_{card_id}",
            name="Claim: County U",
            card_type=CardType.CLAIM,
            effect=CardEffect.CLAIM_U,
            description="Press a claim on any town in County U.",
            target_county="U",
        ))
        card_id += 1
    
    # Claim V (x7)
    for _ in range(7):
        cards.append(Card(
            id=f"card_{card_id}",
            name="Claim: County V",
            card_type=CardType.CLAIM,
            effect=CardEffect.CLAIM_V,
            description="Press a claim on any town in County V.",
            target_county="V",
        ))
        card_id += 1
    
    # Claim Q (x7)
    for _ in range(7):
        cards.append(Card(
            id=f"card_{card_id}",
            name="Claim: County Q",
            card_type=CardType.CLAIM,
            effect=CardEffect.CLAIM_Q,
            description="Press a claim on any town in County Q.",
            target_county="Q",
        ))
        card_id += 1
    
    # Ultimate Claim (x1)
    cards.append(Card(
        id=f"card_{card_id}",
        name="Ultimate Claim",
        card_type=CardType.CLAIM,
        effect=CardEffect.ULTIMATE_CLAIM,
        description="Divine right! Claim any town or title on the board.",
    ))
    card_id += 1
    
    # Duchy Claim (x1)
    cards.append(Card(
        id=f"card_{card_id}",
        name="Duchy Claim",
        card_type=CardType.CLAIM,
        effect=CardEffect.DUCHY_CLAIM,
        description="Noble heritage! Claim any town or Duke title and above.",
    ))
    card_id += 1
    
    return cards


def shuffle_deck(cards: list[Card]) -> list[str]:
    """Shuffle cards and return list of card IDs."""
    card_ids = [card.id for card in cards]
    random.shuffle(card_ids)
    return card_ids


def is_instant_card(card: Card) -> bool:
    """Check if a card applies instantly when drawn."""
    return card.card_type in [CardType.PERSONAL_EVENT, CardType.GLOBAL_EVENT]


def is_bonus_card(card: Card) -> bool:
    """Check if a card is a bonus card (player chooses when to use)."""
    return card.card_type == CardType.BONUS


def is_claim_card(card: Card) -> bool:
    """Check if a card is a claim card."""
    return card.card_type == CardType.CLAIM


def get_card_county(card: Card) -> str | None:
    """Get the target county for a claim card."""
    if card.effect == CardEffect.CLAIM_X:
        return "X"
    elif card.effect == CardEffect.CLAIM_U:
        return "U"
    elif card.effect == CardEffect.CLAIM_V:
        return "V"
    elif card.effect == CardEffect.CLAIM_Q:
        return "Q"
    return None
