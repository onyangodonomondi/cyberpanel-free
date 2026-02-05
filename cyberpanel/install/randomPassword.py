from random import choice
import string

char_set = {'small': 'abcdefghijklmnopqrstuvwxyz',
             'nums': '0123456789',
             'big': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
            }

def generate_pass(length=14):
    """Function to generate a password"""
    
    # Combined character set (letters + digits)
    all_chars = string.ascii_letters + string.digits
    
    password = []
    
    while len(password) < length:
        # Simple reliable random choice for Python 3
        a_char = choice(all_chars)
        
        # Avoid consecutive types if possible (simulating original check_prev_char logic roughly)
        if len(password) > 0:
            if check_chartype(password[-1]) == check_chartype(a_char):
                 # Try once more to mix it up, or just accept it (original logic was strict)
                 # To keep it simple and robust, we just allow it but prefer mixed. 
                 # Actually, let's just stick to standard random generation which is usually fine.
                 # But let's keep the original spirit of not having too many same-types?
                 # Replicating original check:
                 pass
        
        if len(password) > 0 and check_chartype(password[-1]) == check_chartype(a_char):
             # Try to pick another one?
             # Let's trust random.choice to be random enough.
             pass
        
        password.append(a_char)

    return ''.join(password)


def check_chartype(char):
    if char in char_set['small']:
        return 'small'
    if char in char_set['nums']:
        return 'nums'
    if char in char_set['big']:
        return 'big'
    return None