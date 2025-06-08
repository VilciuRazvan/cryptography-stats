import getpass

def get_user_choice(prompt, options, allow_manual_entry=False, is_password=False, default_password=None):
    """
    Prompts the user to choose from a list of options or enter text/password.
    Added default_password parameter for JKS generation.
    """
    if not is_password:
        print(prompt)
    
    # If a default password is provided and this is a password prompt, use it
    if is_password and default_password is not None:
        return default_password
    
    if options:
        for i, option_display in enumerate(options):
            if isinstance(option_display, dict) and 'name' in option_display:
                print(f"  {i+1}. {option_display['name']} ({option_display.get('description', 'N/A')})")
            else:
                print(f"  {i+1}. {option_display}")
    
    while True:
        try:
            if is_password:
                choice = getpass.getpass(prompt)
            else:
                choice_prompt = f"Enter your choice"
                if options:
                    choice_prompt += f" (1-{len(options)})"
                if allow_manual_entry:
                    choice_prompt += f"{' or type custom value' if options else 'Enter value'}"
                choice_prompt += ": "
                choice = input(choice_prompt)

            if not options and allow_manual_entry: # Direct text/password input
                return choice.strip()

            if allow_manual_entry and not choice.isdigit() and options : # Allow direct string input if options are also present
                return choice.strip()

            choice_num = int(choice)
            if 1 <= choice_num <= len(options):
                if isinstance(options[choice_num-1], dict) and 'name' in options[choice_num-1]:
                    return options[choice_num-1]['name']
                return options[choice_num-1]
            else:
                print(f"Invalid choice. Please enter a number between 1 and {len(options)}.")
        except ValueError:
            if allow_manual_entry and not options: # if it's a free text field, any non-empty input is fine
                 return choice.strip() if choice.strip() else None # return None if empty
            elif allow_manual_entry and options: # if options are present but user typed text
                 return choice.strip()

            print("Invalid input. Please enter a number or valid text.")
        except IndexError:
            print("Something went wrong with the choice indexing.")


def get_password_with_confirmation(prompt):
    """Get and confirm password input"""
    while True:
        password = get_user_choice(prompt, [], allow_manual_entry=True, is_password=True)
        confirm = get_user_choice("Confirm " + prompt, [], allow_manual_entry=True, is_password=True)
        if password == confirm and password:
            return password
        print("Passwords do not match or empty. Please try again.")

def fuzzy_search(search_term, text):
    """Simple fuzzy search implementation"""
    search_term = search_term.lower()
    text = text.lower()
    
    # Direct match
    if search_term in text:
        return True
        
    # Character sequence matching
    j = 0
    for char in search_term:
        while j < len(text) and text[j] != char:
            j += 1
        if j >= len(text):
            return False
        j += 1
    return True