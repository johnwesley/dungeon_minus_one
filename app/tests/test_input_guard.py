from app.utils.input_guard import evaluate_player_input


def test_single_action_allowed():
    result = evaluate_player_input("north")
    assert result.soft_reject is False


def test_multi_line_commands_soft_reject():
    result = evaluate_player_input("north\neast\nwest")
    assert result.soft_reject is True
    assert result.reason == "multiple_commands"


def test_semicolon_commands_soft_reject():
    result = evaluate_player_input("take lantern; go north")
    assert result.soft_reject is True
    assert result.reason == "multiple_commands"


def test_long_roleplay_allowed():
    text = ("The air is cold and the room is quiet. " * 20).strip()
    result = evaluate_player_input(text)
    assert result.soft_reject is False


def test_too_long_soft_reject():
    text = "a" * 1001
    result = evaluate_player_input(text)
    assert result.soft_reject is True
    assert result.reason == "too_long"
