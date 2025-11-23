"""
Simple validation test for keypress functionality.

This test verifies that the keypress helper module and the underlying
Messaging system are properly integrated and can handle key press messages.
"""

import sys

def test_keypress_helper_import():
    """Test that the keypress helper module can be imported"""
    try:
        from Widgets.MultiBoxing.keypress_helper import (
            send_keypress,
            send_keypress_to_all,
            send_function_key,
            send_equipment_set_key,
            CommonKeys,
            Key
        )
        print("✓ Successfully imported keypress_helper module")
        return True
    except ImportError as e:
        print(f"✗ Failed to import keypress_helper: {e}")
        return False


def test_common_keys_enum():
    """Test that CommonKeys enum has expected values"""
    try:
        from Widgets.MultiBoxing.keypress_helper import CommonKeys
        
        # Test some expected keys
        assert CommonKeys.F1 == 0x70, "F1 key code incorrect"
        assert CommonKeys.F2 == 0x71, "F2 key code incorrect"
        assert CommonKeys.ENTER == 0x0D, "ENTER key code incorrect"
        assert CommonKeys.ESCAPE == 0x1B, "ESCAPE key code incorrect"
        assert CommonKeys.NUM_1 == 0x31, "NUM_1 key code incorrect"
        
        print("✓ CommonKeys enum has correct values")
        return True
    except AssertionError as e:
        print(f"✗ CommonKeys enum validation failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error testing CommonKeys: {e}")
        return False


def test_parameter_validation():
    """Test that helper functions validate parameters correctly"""
    try:
        from Widgets.MultiBoxing.keypress_helper import send_keypress, send_function_key
        
        # Test empty email validation
        try:
            send_keypress("", "target@test.com", 0x70)
            print("✗ Failed to validate empty sender email")
            return False
        except ValueError:
            pass  # Expected
        
        # Test invalid key code
        try:
            send_keypress("sender@test.com", "target@test.com", 0)
            print("✗ Failed to validate invalid key code")
            return False
        except ValueError:
            pass  # Expected
        
        # Test function key range
        try:
            send_function_key("sender@test.com", "target@test.com", 13)
            print("✗ Failed to validate function key range")
            return False
        except ValueError:
            pass  # Expected
        
        print("✓ Parameter validation working correctly")
        return True
    except Exception as e:
        print(f"✗ Unexpected error in parameter validation: {e}")
        return False


def test_messaging_enum_exists():
    """Test that PressKey command exists in SharedCommandType"""
    try:
        from Py4GWCoreLib.enums_src.Multiboxing_enums import SharedCommandType
        
        assert hasattr(SharedCommandType, 'PressKey'), "PressKey not found in SharedCommandType"
        # Verify it's a valid integer value (exact value may change)
        assert isinstance(SharedCommandType.PressKey.value, int), "PressKey value is not an integer"
        assert SharedCommandType.PressKey.value > 0, "PressKey value should be positive"
        
        print(f"✓ SharedCommandType.PressKey exists (value: {SharedCommandType.PressKey.value})")
        return True
    except AssertionError as e:
        print(f"✗ SharedCommandType validation failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error testing SharedCommandType: {e}")
        return False


def test_key_enum_completeness():
    """Test that Key enum has all expected key types"""
    try:
        from Py4GWCoreLib.enums_src.IO_enums import Key
        
        # Test function keys F1-F12
        for i in range(1, 13):
            key_name = f"F{i}"
            assert hasattr(Key, key_name), f"{key_name} not found in Key enum"
        
        # Test number keys
        for name in ["One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Zero"]:
            assert hasattr(Key, name), f"{name} not found in Key enum"
        
        # Test common control keys
        for name in ["Enter", "Escape", "Space", "Tab"]:
            assert hasattr(Key, name), f"{name} not found in Key enum"
        
        # Test letter keys
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            assert hasattr(Key, letter), f"{letter} not found in Key enum"
        
        print("✓ Key enum is complete with all expected keys")
        return True
    except AssertionError as e:
        print(f"✗ Key enum completeness check failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error testing Key enum: {e}")
        return False


def run_all_tests():
    """Run all validation tests"""
    print("=" * 60)
    print("Keypress Functionality Validation Tests")
    print("=" * 60)
    print()
    
    tests = [
        test_keypress_helper_import,
        test_common_keys_enum,
        test_parameter_validation,
        test_messaging_enum_exists,
        test_key_enum_completeness,
    ]
    
    results = []
    for test in tests:
        print(f"\nRunning: {test.__name__}")
        print("-" * 60)
        result = test()
        results.append(result)
        print()
    
    print("=" * 60)
    print(f"Tests Complete: {sum(results)}/{len(results)} passed")
    print("=" * 60)
    
    return all(results)


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
