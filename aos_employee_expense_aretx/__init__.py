from . import models

def uninstall_hook(env):
    # Restore the original contacts action when uninstalling
    original_action = env.ref('contacts.action_contacts', raise_if_not_found=False)
    menu = env.ref('contacts.menu_contacts', raise_if_not_found=False)
    if menu and original_action:
        menu.action = original_action