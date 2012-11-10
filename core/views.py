from models import Player, Session, Card, CardDetail, CARD_KINDS, Stack
from rules import start, skip

from django.http import HttpResponse

import json

RESPONSE_MIME_TYPE = 'application/javascript'

def encode(obj):
    if isinstance(obj, Card):
        pretty_value = obj.details.value

        if pretty_value is None:
            pretty_value = ''

        return {
            'id': obj.id,
            'name': obj.details.name,
            'kind': obj.details.kind,
            'value': pretty_value,
            'is_special': obj.is_special
        }
    else:
        raise TypeError(repr(obj) + " is not JSON serializablelelele")

def render_to_json(data):
    return HttpResponse(
        json.dumps(data, 
            default=encode, 
            sort_keys=True, 
            indent=2),
        mimetype=RESPONSE_MIME_TYPE)

def session_is_valid(request, session):
    if not session:
        return False

    try:
        player = Player.objects.get(pk = request.user.id)
    except Player.DoesNotExist:
        return False

    if session.belongs_to_player != player:
        return False

    return True

def current_state(session):
    """
    Returns all information on the current state of the active game session.
    """
    if not session:
        return None

    current_room_cards = list(session.room_stack.get_all_cards())
    current_equipment_cards = list(session.equipment_stack.get_all_cards())
    current_you_cards = list(session.you_stack.get_all_cards())
    current_treasure_cards = list(session.treasure_stack.get_all_cards())
    current_forge_cards = list(session.forge_stack.get_all_cards())

    return {
        'health': int(session.health),
        'stacks': [
            { 'name': 'room', 'id': session.room_stack.id, 'cards': current_room_cards },
            { 'name': 'equipment', 'id': session.equipment_stack.id, 'cards': current_equipment_cards },
            { 'name': 'you', 'id': session.you_stack.id, 'cards': current_you_cards },
            { 'name': 'treasure', 'id': session.treasure_stack.id, 'cards': current_treasure_cards },
            { 'name': 'forge', 'id': session.forge_stack.id, 'cards': current_forge_cards }
        ]
    }

def get_current_state(request, session_id):
    try:
        player = Player.objects.get(pk = request.user.id)
    except Player.DoesNotExist:
        return None

    try:
        session = Session.objects.get(pk = session_id)
    except Session.DoesNotExist:
        return None

    state = None

    if session_is_valid(request, session):
        state = current_state(session)

    return state

def start_new_session(request):
    try:
        player = Player.objects.get(pk = request.user.id)
    except Player.DoesNotExist:
        player = None

    session = None

    if player is not None:
        session = start(player)       

    return session

def perform_move_action(request, session):
    if request.method != 'POST':
        return False
    
    try:
        card_id = request.POST.get('card_id')
        to_stack_id = request.POST.get('to_stack_id')
    except:
        return False

    try:
        card = Card.objects.get(pk = card_id)
    except Card.DoesNotExist:
        return False

    if card.belongs_to_session != session:
        return False

    try:
        to_stack = Stack.objects.get(pk = to_stack_id)
    except Stack.DoesNotExist:
        return False

    if not to_stack.belongs_to_session(session):
        return False

    return move(session, card, to_stack)

def perform_clear_action(request, session):
    if request.method != 'POST':
        return False

    try:
        stack_id = request.POST.get('stack_id')
    except:
        return False

    try:
        stack = Stack.objects.get(pk = stack_id)
    except Stack.DoesNotExist:
        return False

    if not to_stack.belongs_to_session(session):
        return False

    return activate_stack(session, stack)

def perform_skip_action(request, session):
    return skip(session)

def perform_action(request, session_id, action_type):
    success = False

    if request.method == 'POST':
        try:
            session = Session.objects.get(pk = session_id)
        except Session.DoesNotExist:
            session = None

        if session_is_valid(request, session):
            if action_type == 'move' or action_type == 'discard':
                if action_type == 'discard':
                    # Since we're making use of the existing move action, we just need
                    # to make sure that the destination stack is set to the discard stack
                    request.POST['to_stack_id'] = session.discard_stack.id

                success = perform_move_action(request, session)
            elif action_type == 'skip':
                success = perform_skip_action(request, session)
            elif action_type == 'clear':
                success = perform_clear_action(request, session)

    return render_to_json({
            'success': success
        })