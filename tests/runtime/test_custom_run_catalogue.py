"""Every routable point must be visible and toggleable in custom-run setup."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest

from menu_model import Menu
from menu_controls import controls
from run_settings import (
    LEVELS,
    BOSSES,
    ADVANCED_PAGES,
    encode,
    decode,
    normalize,
    route,
)
from trigger_audit import points

ROOT = Path(__file__).resolve().parents[1]


class CustomCatalogue(unittest.TestCase):
    def menu(self, mode):
        with patch(
            'menu_model.summary', return_value={'exists': False, 'completed': False}
        ):
            menu = Menu(SimpleNamespace(base=ROOT))
        menu.change_mode(mode)
        menu.open_advanced()
        return menu

    def test_audited_points_have_selection_or_explicit_special_role(self):
        selectable = set(LEVELS) | {row[2] for row in BOSSES.values()}
        special = {'boss_solgryn.ini', 'gastly_grass'}
        self.assertEqual(set(points(ROOT)), selectable | special)

    def test_every_visible_pool_row_can_be_clicked_off_and_on(self):
        for mode in ('randomizer', 'boss_rush', 'level_rush'):
            menu = self.menu(mode)
            seen = {'level_pool': set(), 'boss_pool': set()}
            for page in range(ADVANCED_PAGES):
                menu.advanced_page = page
                for index, rect in controls(menu):
                    if not 3 <= index < 3 + len(LEVELS) + len(BOSSES):
                        continue
                    if index < 3 + len(LEVELS):
                        pool, key = 'level_pool', list(LEVELS)[index - 3]
                    else:
                        pool, key = 'boss_pool', list(BOSSES)[index - 3 - len(LEVELS)]
                    seen[pool].add(key)
                    x, y = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
                    before = key in menu.options[pool]
                    menu.click(x, y)
                    self.assertEqual(
                        key in menu.options[pool], not before, (mode, page, key)
                    )
                    menu.click(x, y)
                    self.assertEqual(key in menu.options[pool], before)
            self.assertEqual(
                seen['level_pool'], set() if mode == 'boss_rush' else set(LEVELS)
            )
            self.assertEqual(
                seen['boss_pool'], set() if mode == 'level_rush' else set(BOSSES)
            )

    def test_each_single_selected_point_survives_seed_share_and_route(self):
        for pool, count, choices, other, other_count in (
            ('level_pool', 'level_count', LEVELS, 'boss_pool', 'route_boss_count'),
            ('boss_pool', 'route_boss_count', BOSSES, 'level_pool', 'level_count'),
        ):
            for key in choices:
                menu = self.menu('randomizer')
                opts = {
                    **menu.options,
                    pool: [key],
                    count: 1,
                    other: [],
                    other_count: 0,
                }
                seed, decoded = decode(encode('CUSTOM-CHECK', normalize(opts)))
                target = key if pool == 'level_pool' else BOSSES[key][2]
                self.assertEqual(route(seed, decoded), [target, 'boss_solgryn.ini'])
