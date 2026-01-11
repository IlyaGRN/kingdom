"""Card deck definitions and logic."""
import random
from app.models.schemas import Card, CardType, CardEffect
from app.config import get_settings


def create_deck() -> list[Card]:
    """Create the game card deck based on configuration.
    
    Card quantities are configurable via settings (config.py or .env).
    """
    settings = get_settings()
    cards = []
    card_id = 0
    
    def add_cards(count: int, name: str, card_type: CardType, effect: CardEffect, 
                  description: str, effect_value: int = None, target_county: str = None):
        nonlocal card_id
        for _ in range(count):
            card = Card(
                id=f"card_{card_id}",
                name=name,
                card_type=card_type,
                effect=effect,
                description=description,
            )
            if effect_value is not None:
                card.effect_value = effect_value
            if target_county is not None:
                card.target_county = target_county
            cards.append(card)
            card_id += 1
    
    # ============ Personal Events (instant) ============
    
    add_cards(settings.card_gold_5, "Gold Chest (5)", CardType.PERSONAL_EVENT, 
              CardEffect.GOLD_5, "A small treasure! Gain 5 Gold immediately.", effect_value=5)
    
    add_cards(settings.card_gold_10, "Gold Chest (10)", CardType.PERSONAL_EVENT,
              CardEffect.GOLD_10, "A modest treasure! Gain 10 Gold immediately.", effect_value=10)
    
    add_cards(settings.card_gold_15, "Gold Chest (15)", CardType.PERSONAL_EVENT,
              CardEffect.GOLD_15, "A fine treasure! Gain 15 Gold immediately.", effect_value=15)
    
    add_cards(settings.card_gold_25, "Gold Chest (25)", CardType.PERSONAL_EVENT,
              CardEffect.GOLD_25, "A grand treasure! Gain 25 Gold immediately.", effect_value=25)
    
    add_cards(settings.card_soldiers_100, "Soldiers (100)", CardType.PERSONAL_EVENT,
              CardEffect.SOLDIERS_100, "Reinforcements arrive! Gain 100 soldiers immediately.", effect_value=100)
    
    add_cards(settings.card_soldiers_200, "Soldiers (200)", CardType.PERSONAL_EVENT,
              CardEffect.SOLDIERS_200, "A warband joins you! Gain 200 soldiers immediately.", effect_value=200)
    
    add_cards(settings.card_soldiers_300, "Soldiers (300)", CardType.PERSONAL_EVENT,
              CardEffect.SOLDIERS_300, "An army rallies! Gain 300 soldiers immediately.", effect_value=300)
    
    add_cards(settings.card_raiders, "Raiders", CardType.PERSONAL_EVENT,
              CardEffect.RAIDERS, "Raiders attack! Lose all collected taxes from this turn.")
    
    # ============ Global Events (instant) ============
    
    add_cards(settings.card_crusade, "Crusade", CardType.GLOBAL_EVENT,
              CardEffect.CRUSADE, "A holy crusade is called! All players lose half their Gold and soldiers.")
    
    # ============ Bonus Cards (player chooses when to use) ============
    
    add_cards(settings.card_big_war, "Big War", CardType.BONUS,
              CardEffect.BIG_WAR, "Military expansion! Double your army cap until your next war.")
    
    add_cards(settings.card_adventurer, "Adventurer", CardType.BONUS,
              CardEffect.ADVENTURER, "A wandering hero! Buy 500 soldiers for 25 Gold (above your cap limit).")
    
    add_cards(settings.card_excalibur, "Excalibur", CardType.BONUS,
              CardEffect.EXCALIBUR, "Legendary sword! Roll dice twice in combat and take the higher result.")
    
    add_cards(settings.card_poisoned_arrows, "Poisoned Arrows", CardType.BONUS,
              CardEffect.POISONED_ARROWS, "Deadly toxins! Your opponent's dice score is halved in combat.")
    
    add_cards(settings.card_forbid_mercenaries, "Forbid Mercenaries", CardType.BONUS,
              CardEffect.FORBID_MERCENARIES, "Economic sanctions! No player may buy soldiers for one turn.")
    
    add_cards(settings.card_talented_commander, "Talented Commander", CardType.BONUS,
              CardEffect.TALENTED_COMMANDER, "Brilliant tactics! You lose no soldiers when winning combat.")
    
    add_cards(settings.card_vassal_revolt, "Vassal Revolt", CardType.BONUS,
              CardEffect.VASSAL_REVOLT, "Rebellion stirs! Higher tier lords may attack their vassals this turn.")
    
    add_cards(settings.card_enforce_peace, "Enforce Peace", CardType.BONUS,
              CardEffect.ENFORCE_PEACE, "The Pope intervenes! No wars may be waged for one complete turn.")
    
    add_cards(settings.card_duel, "Duel", CardType.BONUS,
              CardEffect.DUEL, "Challenge to single combat! An army-less fight where only dice decide.")
    
    add_cards(settings.card_spy, "Spy", CardType.BONUS,
              CardEffect.SPY, "Intelligence network! View one player's cards or reorder the deck.")
    
    # ============ Claim Cards ============
    
    add_cards(settings.card_claim_x, "Claim: County X", CardType.CLAIM,
              CardEffect.CLAIM_X, "Press a claim on any town in County X.", target_county="X")
    
    add_cards(settings.card_claim_u, "Claim: County U", CardType.CLAIM,
              CardEffect.CLAIM_U, "Press a claim on any town in County U.", target_county="U")
    
    add_cards(settings.card_claim_v, "Claim: County V", CardType.CLAIM,
              CardEffect.CLAIM_V, "Press a claim on any town in County V.", target_county="V")
    
    add_cards(settings.card_claim_q, "Claim: County Q", CardType.CLAIM,
              CardEffect.CLAIM_Q, "Press a claim on any town in County Q.", target_county="Q")
    
    add_cards(settings.card_ultimate_claim, "Ultimate Claim", CardType.CLAIM,
              CardEffect.ULTIMATE_CLAIM, "Divine right! Claim any town or title on the board.")
    
    add_cards(settings.card_duchy_claim, "Duchy Claim", CardType.CLAIM,
              CardEffect.DUCHY_CLAIM, "Noble heritage! Claim any town or Duke title and above.")
    
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
