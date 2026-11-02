"""One hit map for keyboard focus, hover and click. Navigation never edits options."""

from run_settings import LEVELS, BOSSES, ADVANCED_PAGE_SIZE
from run_extras import EXTRAS, SHOT_MODES


def controls(m):
    p = m.page
    if p == 'slots':
        return (
            [(7, (640, 274, 682, 299)), (6, (690, 274, 732, 299))]
            + [(3 + i, (742 + i * 40, 274, 778 + i * 40, 299)) for i in range(3)]
            + [
                (2, (614, 570, 860, 593)),
                (0, (614, 600, 860, 624)),
                (1, (614, 630, 860, 649)),
            ]
        )
    if p == 'appearance':
        return [(i, (251, 350 + i * 58, 851, 399 + i * 58)) for i in range(3)] + [
            (3, (251, 604, 851, 640))
        ]
    if p == 'discard':
        return [(i, (251, 410 + i * 62, 851, 460 + i * 62)) for i in range(3)]
    if p == 'seed_preview':
        return [
            (0, (710, 265, 774, 296)),
            (1, (783, 265, 847, 296)),
            (2, (251, 604, 546, 640)),
            (3, (558, 604, 851, 640)),
        ]
    if p == 'new' and m.options.get('mode') == 'normal':
        return (
            [(10, (583, 263, 625, 291)), (9, (635, 263, 854, 291))]
            + [
                (i, (245, 295 + r * 35, 856, 327 + r * 35))
                for r, i in enumerate((1, 2, 5, 3, 8))
            ]
            + [
                (7, (245, 508, 856, 539)),
                (0, (245, 546, 856, 580)),
                (6, (245, 603, 856, 642)),
            ]
        )
    if p == 'new':
        return (
            [(10, (583, 263, 625, 291)), (9, (635, 263, 854, 291))]
            + [
                (i, (245, 295 + r * 35, 856, 327 + r * 35))
                for r, i in enumerate((1, 2, 3, 4, 5, 8))
            ]
            + [
                (7, (245, 508, 856, 539)),
                (0, (245, 546, 856, 580)),
                (6, (245, 603, 856, 642)),
            ]
        )
    if p == 'advanced':
        count = 3 + len(LEVELS) + len(BOSSES)
        rows = [(i, (245, 299 + i * 25, 856, 322 + i * 25)) for i in range(3)]
        rows += [(count + 2, (751, 374, 791, 395)), (count + 3, (799, 374, 845, 395))]
        for row in range(
            m.advanced_page * ADVANCED_PAGE_SIZE,
            (m.advanced_page + 1) * ADVANCED_PAGE_SIZE,
        ):
            for col, n, offset in (
                (0, len(LEVELS), 3),
                (1, len(BOSSES), 3 + len(LEVELS)),
            ):
                if row < n:
                    x = 249 + col * 304
                    y = 399 + (row % ADVANCED_PAGE_SIZE) * 15
                    rows.append((offset + row, (x, y, x + 292, y + 14)))
        mode = m.options.get('mode')
        if mode == 'boss_rush':
            rows = [(i, r) for i, r in rows if i != 0 and not 3 <= i < 3 + len(LEVELS)]
        elif mode == 'level_rush':
            rows = [
                (i, r) for i, r in rows if i != 1 and not 3 + len(LEVELS) <= i < count
            ]
        if mode in ('boss_rush', 'level_rush'):
            rows = [
                (i, (249, r[1], 845, r[3]) if 3 <= i < count else r) for i, r in rows
            ]
        return rows + [(count, (245, 608, 548, 642)), (count + 1, (558, 608, 856, 642))]
    if p == 'extras':
        return [
            (i, (245, 293 + i * 26, 856, 318 + i * 26)) for i in range(len(EXTRAS))
        ] + [(len(EXTRAS), (245, 608, 856, 642))]
    if p == 'music':
        return (
            [(0, (251, 302, 851, 341))]
            + [
                (i + 1, (251, 380 + i * 50, 851, 423 + i * 50))
                for i in range(len(m.music_packs))
            ]
            + [
                (len(m.music_packs) + 1, (251, 604, 546, 640)),
                (len(m.music_packs) + 2, (558, 604, 851, 640)),
            ]
        )
    if p == 'graphics':
        return [(i, (251, 305 + i * 44, 851, 344 + i * 44)) for i in range(6)] + [
            (6, (251, 604, 851, 640))
        ]
    if p == 'characters':
        return [
            (
                i,
                (
                    249 + i % 7 * 87,
                    303 + i // 7 * 49,
                    331 + i % 7 * 87,
                    348 + i // 7 * 49,
                ),
            )
            for i in range(len(m.character_names))
        ] + [(len(m.character_names), (249, 608, 852, 640))]
    if p == 'choice':
        count = len(m.choice_values)
        cols = 6 if count > 6 else 1
        wide = 600 / cols
        return [
            (
                i,
                (
                    251 + i % cols * wide,
                    313 + i // cols * 46,
                    251 + (i % cols + 1) * wide - 8,
                    353 + i // cols * 46,
                ),
            )
            for i in range(count)
        ] + [(count, (251, 604, 851, 640))]
    if p == 'shots':
        return [
            (i, (251, 300 + i * 41, 851, 336 + i * 41)) for i in range(len(SHOT_MODES))
        ] + [(5, (251, 521, 851, 562)), (6, (251, 604, 851, 640))]
    if p == 'presets':
        return [(i, (251, 315 + i * 73, 851, 375 + i * 73)) for i in range(4)]
    if p == 'interval':
        return [
            (0, (260, 354, 535, 414)),
            (1, (555, 354, 840, 414)),
            (2, (251, 604, 546, 640)),
            (3, (558, 604, 851, 640)),
        ]
    if p == 'seed':
        from menu_model import seed_layout

        field, buttons = seed_layout(m.seed_text)
        return (
            [(0, field)]
            + [
                (i, (left, buttons[0], right, buttons[1]))
                for i, (left, right) in enumerate(
                    ((251, 443), (455, 647), (659, 851)), 1
                )
            ]
            + [(4, (251, 604, 546, 640)), (5, (558, 604, 851, 640))]
        )
    if p == 'result':
        return [
            (2, (698, 548, 851, 574)),
            (0, (251, 604, 546, 640)),
            (1, (558, 604, 851, 640)),
        ]
    if p == 'delete':
        return [(0, (255, 530, 525, 578)), (1, (550, 530, 850, 578))]
    if p == 'targets':
        return [(0, (251, 613, 851, 644))]
    return []


def hit(m, x, y):
    return next(
        (i for i, (l, t, r, b) in controls(m) if l <= x <= r and t <= y <= b), None
    )


def navigate(m, key):
    rows = controls(m)
    if not rows:
        return False
    ids = [i for i, _ in rows]
    if key in (9, 4096):
        m.focus = (
            ids[(ids.index(m.focus) + (-1 if key == 4096 else 1)) % len(ids)]
            if m.focus in ids
            else ids[0]
        )
    else:
        if m.focus not in ids:
            m.focus = ids[0]
            return True
        center = lambda r: ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
        current = dict(rows)[m.focus]
        x, y = center(current)
        horizontal = key in (37, 39)
        sign = -1 if key in (37, 38) else 1
        candidates = []
        for i, rect in rows:
            u, v = center(rect)
            forward = (u - x if horizontal else v - y) * sign
            across = abs(v - y if horizontal else u - x)
            if forward > 1 and (
                not horizontal
                or across <= max(current[3] - current[1], rect[3] - rect[1]) * 0.75
            ):
                candidates.append((forward + across * 4, across, i))
        m.focus = (
            min(candidates)[2]
            if candidates
            else ids[(ids.index(m.focus) + sign) % len(ids)]
        )
    if m.page == 'interval':
        m.interval_selected = True
    return True
