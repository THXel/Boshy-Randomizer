"""One seed renewal per settings edit, shared by keyboard and mouse actions."""

from copy import deepcopy
from functools import wraps


def renew_on_edit(method):
    @wraps(method)
    def edit(menu, *args, **kwargs):
        if getattr(menu, '_editing_settings', False) or not hasattr(menu, 'options'):
            return method(menu, *args, **kwargs)
        before = deepcopy(menu.options)
        seed = menu.seed
        origin = getattr(menu, 'seed_origin', None)
        menu._editing_settings = True
        try:
            return method(menu, *args, **kwargs)
        finally:
            menu._editing_settings = False
            # Seed imports and result replays deliberately keep their seed.
            imported = getattr(menu, 'seed_origin', None) is not origin
            if (
                menu.options != before
                and menu.seed == seed
                and not imported
                and getattr(menu, 'action', None) is None
            ):
                menu.consume_seed()
                menu.dirty = True

    return edit
