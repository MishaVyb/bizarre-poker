"""Tools for handling poker combinations.

developing:
[ ] get_condition -- refactoring
[ ] track row -- refactoring
[ ] ComboStacks.__init__(...)
[ ] class ComboComplite(ComboKind, ComboStacks)
[ ] doc string

"""

from __future__ import annotations

import itertools
from copy import deepcopy
from operator import attrgetter
from typing import ClassVar, Iterable

from core.functools.looptools import looptools
from core.functools.utils import PrintColors
from core.functools.utils import is_sorted
from games.backends.cards import Card, CardList, JokerCard, Stacks

print = PrintColors(activated=False)  # alias
Conditions = dict[str, tuple[int, ...]]


def get_conditions(cases_stacks: dict[str, Stacks]) -> Conditions:
    value: Conditions = {}
    for key in cases_stacks:
        value[key] = tuple(cards.length for cards in cases_stacks[key])
    return value


class ComboKind:
    """Class for annotation specific type of combination.

    All groups lists shold be init by straight sequences from highest to smallest.
    Anyway, they have sorted inside, to be shure.
    """

    CONDITION_KEYS: ClassVar[tuple[str, ...]] = ('rank', 'suit', 'row', 'highest_card')
    # """Quick access to all class attributes responsible for the conditions."""

    def __init__(
        self,
        *,
        rank_case: tuple[int, ...] | list[int] = [],
        suit_case: tuple[int, ...] | list[int] = [],
        row_case: tuple[int, ...] | list[int] = [],
        highest_card_case: tuple[int, ...] | list[int] = [],
        name: str = '',
        priority: float | None = None,
    ):

        self.name = name
        """Verbose name of combination kind."""
        self.priority = priority
        """The priority of the combination among the list of all possible
        combinations definded in the game.
        `0.00` for the most common kind.
        `1.00` for the most rare kind.
        """
        self.cases: Conditions = {}
        """Main dictianary to store all conditional cases."""
        if rank_case:
            self.cases['rank'] = tuple(sorted(rank_case, reverse=True))
        if suit_case:
            self.cases['suit'] = tuple(sorted(suit_case, reverse=True))
        if row_case:
            self.cases['row'] = tuple(sorted(row_case, reverse=True))
        if highest_card_case:
            self.cases['highest_card'] = tuple(highest_card_case)

    def __repr__(self) -> str:
        return f'<ComboKind: {self.name=}>'

    def __str__(self) -> str:
        return (
            f'Name: {self.name}\n'
            f'Priority: {self.priority}\n'
            f'Conditions: {self.cases}\n'
        )

    def is_minor_combo_for(self, major: Conditions):
        """
        Return whether self (minor) combination cases includes (or equal) major cases.
        self cases <= major

        >>> self = ComboKind(suit_case=[5], row_case=[5])
        >>> self.is_minor_combo_for({'suit': [6], 'row': [7]})
        True
        >>> self = ComboKind(row_case=[5])
        >>> self.is_minor_combo_for({'row': [4, 3]})
        False
        """
        assert is_sorted(
            *self.cases.values(), reverse=True
        ), f'Some condition is not row sequence in {self}'
        assert is_sorted(
            *major.values(), reverse=True
        ), f'Some condition is not row sequence in {major}'

        if not major.keys() >= self.cases.keys():
            return False

        value: bool = True
        for key in self.cases:
            # длина больше или равна
            value = value and len(major[key]) >= len(self.cases[key])
            for greater, smaller in zip(major[key], self.cases[key]):
                # каждый элемент больше или равен
                value = value and greater >= smaller
                if not value:
                    break

        return value


class ComboKindList(list[ComboKind]):
    def __init__(self, __iterable: Iterable[ComboKind], *, set_pryority=False) -> None:
        super().__init__(__iterable)
        if set_pryority:
            assert self
            priority: float = 0.00
            step: float = 1.00 / len(self)
            for combo in self:
                combo.priority = round(priority, 2)
                priority += step

    def get(self, name: str) -> ComboKind:
        try:
            return next(filter(lambda c: c.name == name, self))
        except StopIteration:
            raise ValueError(f'{self} do not contains combos with `{name}` name')

    def get_by_conditions(self, conditions: Conditions) -> ComboKind:
        """Finding equivalent combination in self list. Going through all combos
        from highest to smallest until self combination is not major for referen
        """
        assert is_sorted(
            self, key='priority'
        ), 'Self list of combination kinds is not ordered by priority.'

        for ref in reversed(self):
            if conditions == ref.cases:
                return ref
            if ref.is_minor_combo_for(conditions):
                raise ExtraComboException(cases=conditions, nearest=ref)

        raise NoComboException(cases=conditions, nearest=ref)

    def __str__(self) -> str:
        return ', '.join([c.name for c in self])


CLASSIC_COMBOS = ComboKindList(
    [
        ComboKind(highest_card_case=[1], name='high card'),
        ComboKind(rank_case=[2], name='one pair'),
        ComboKind(rank_case=[2, 2], name='two pair'),
        ComboKind(rank_case=[3], name='three of kind'),
        ComboKind(row_case=[5], name='straight'),
        ComboKind(suit_case=[5], name='flush'),
        ComboKind(rank_case=[3, 2], name='full house'),
        ComboKind(rank_case=[4], name='four of kind'),
        ComboKind(row_case=[5], suit_case=[5], name='straight flush'),
        ComboKind(rank_case=[5], name='pocker'),
    ],
    set_pryority=True,
)


class ExtraComboException(Exception):
    def __init__(self, cases: Conditions, nearest: ComboKind) -> None:
        self.cases = cases
        self.nearest = nearest
        return super().__init__(
            f'Combo {cases} has more opportunity than described in reference list.'
            f'Redefine list of possible combos where all keyses will be considered.'
            f'Or merge this combo into nearist {nearest}',
        )

    def solution(self, stacks: ComboStacks):
        print.warning('WARNING!')
        print(*self.args)
        print.underline('TEMPRARY SOLUTION:')
        print('- Copied extra conditionas and staks in self.extra for any extra uses.')
        print('- Merjed self into nearest', self.nearest.cases, end='\n\n')

        # deep copy
        stacks.extra_cases = deepcopy(stacks.cases)
        stacks.trim_to(self.nearest)


class NoComboException(Exception):
    def __init__(self, cases: Conditions, nearest: ComboKind) -> None:
        assert nearest.name == 'high card'

        self.cases = cases
        self.nearest = nearest
        return super().__init__(
            f'No reference combination found for {cases}. '
            f'At least {self.nearest} combination should be sytisfied. '
        )

    def solution(self, stacks: ComboStacks):
        if not stacks:
            return None
        else:
            # add highest card here
            ...
            ...
            raise RuntimeError(f'{stacks=}. {self.nearest=}. {self.cases=}')


class ComboStacks:
    """Contains lists of stacks equivalented to ComboKind condtitions groups.
    By default `init()` creates an epty object.
    Call `track_and_merge()` method to complete initialization.
    """

    def __init__(self):
        self.cases: dict[str, Stacks] = {}
        self.extra_cases: dict[str, Stacks] = {}

    def __bool__(self) -> bool:
        return any(any(bool(cl) for cl in stacks) for stacks in self.cases.values())

    def __str__(self) -> str:
        value = f'Conditions: {get_conditions(self.cases)}\n'
        value += f'Extra conditions: {get_conditions(self.extra_cases)}\n'

        value += 'Stacks:\n'
        stacks_text = ''
        for key, val in self.cases.items():
            stacks_text += f'   by {key}: '
            stacks_text += " | ".join(str(e) for e in val)
            stacks_text += '\n'
        value += stacks_text

        value += 'Extra stacks:\n'
        stacks_text = ''
        for key, val in self.extra_cases.items():
            stacks_text += f'   by {key}: '
            stacks_text += " | ".join(str(e) for e in val)
            stacks_text += '\n'
        value += stacks_text

        return value

    def track(self, *stacks: CardList, possible_highest: Card = Card(14, 4)) -> None:
        # 1- сложим все стопки в одну новую
        tracking = CardList(instance=itertools.chain(*stacks))
        if not tracking:
            print("raise Warning('no cards for tracking was provided')")

        # 2- suit case
        self.track_equal(tracking, possible_highest, 'suit')
        # 3- rank case
        self.track_equal(tracking, possible_highest, 'rank', add_highest=False)
        # 4- row case
        self.track_row(tracking, possible_highest, tracking_list_constant=False)
        # 5- add highest
        # даже если нашли что-то для предыдущих cases, они потом могут быть
        # недостаточными для метода merge и будут откинуты, в этом случае нам и нужен
        # заранее записанный случай highest card
        self.cases['highest_card'] = [CardList(card) for card in tracking]

    def track_equal(
        self,
        tracking: CardList,
        possible_highest: Card,
        condition_key: str,
        add_highest: bool = False,
        min_group_len=2,
    ):
        key = condition_key
        attr = condition_key
        assert key in ['suit', 'rank']
        assert attr in ['suit', 'rank']
        assert min_group_len >= 2

        # 1- создадим вспомогаетельные переменные для временного хранения
        case: Stacks = []
        jokers = CardList()
        # 2- пройдемся по группам, исключим группы где 1 карта
        for is_jkrs, group in tracking.groupby(attr):
            if is_jkrs:
                jokers = group
            elif group.length >= min_group_len:
                # ########### we need shallow copy of iterator!!?? ########### #
                # copied = group.copy()
                # case.append( copied )
                case.append(group)
        # 3- отсортируем, чтобы в начале была самая длинная группа
        case.sort(key=attrgetter('length'), reverse=True)
        # 4- обработаем джокеров
        # добавим джокеров к самой длинной группе,
        # тк сортировка была выше, самая длинная группа, это первая группа
        for jkr in jokers:
            # 4.1- если нет ни одной группы (где есть 2 и более карт), добавим
            # просто старшую карту tracking уже отсортировался выше в groups_by
            # берем просто первый элемент
            if not case:
                one_card_group = CardList(tracking.first)
                case.append(one_card_group)
            longest_stack = case[0]
            # установим значение аттрибута как у референсной карты
            val = longest_stack.first[attr]
            mirrored = jkr.get_mirrored(possible_highest, attr, val)
            longest_stack.append(mirrored)
        # 4.1 - после добавления джокеров с конца, нужна сортировка группы
        # чтобы они попали в начало и выступали как более старшая карта в комбо
        if jokers:
            case[0].sortby(attr)

        # 5 добавим старшую карту
        if add_highest and not case:
            # tracking уже отсортировался выше в groupsby, берем первый элемент
            assert tracking, 'Geting highest card from empty tracking list.'
            one_card_group = CardList(tracking.first)
            case.append(one_card_group)
        # 6- сохраним стек для нашего условия, если нашли что-то
        if case:
            self.cases[key] = case

    def track_row(
        self,
        tracking: CardList,
        possible_highest: Card,
        condition_key: str = 'row',
        card_attr: str = 'rank',
        min_group_len=2,
        tracking_list_constant=True,
    ):
        key = condition_key
        attr = card_attr
        assert min_group_len >= 2

        # 1- создадим вспомогаетельные переменные для временного хранения
        # 2- сортировка
        # нам нужно копировать tracking, чтобы сохранить оригинальный
        # трекинг-лист (чтобы не изолировать от туда джокеров) только в том
        # случае, если потом будем еще трекать другие кесы за пределами этой
        # функции
        case: Stacks = []
        if tracking_list_constant:
            # copy:
            tracking, jokers = tracking.copy().isolate_jokers(sort_attr=attr)
        else:
            tracking, jokers = tracking.isolate_jokers(sort_attr=attr)

        # 3- основной цикл
        new_group_flag = True
        cursor = CardList()
        loop_max_iteration = 99
        # перебераем кажду карту из трекинга
        # print.header('\n--- row ----')
        # print.underline(f'{tracking=} -- {jokers=}\n')
        for track_card, final in looptools.final(tracking):
            while True:  # цикл по джокерам
                # print('')
                # print.bold(
                #     f'{loop_max_iteration = } {track_card = } cursor = '
                #     f'<the same as last case group>'
                # )
                # print(f'{case=}')
                loop_max_iteration -= 1
                assert loop_max_iteration, 'Achive lopp max iteration.'

                # 3.1 созданеие новой группы
                if new_group_flag:
                    # 3.1.1 -- добавим пустую группу
                    case.append(CardList())
                    # 3.1.2 -- начнем новую группу с хвоста предыдущего
                    if (
                        jokers
                        and cursor  # если вообще есть джокеры
                        and  # если есть предыдущая группа
                        # если предыдущая группа не 1 карта + джокеры,
                        # тогда ее проходить еще раз не имеет смысла
                        # это значит что ему на хватило джокеров, чтобы сомкнуть разрыв
                        # и он перетащил все с конца в перед
                        # [red, King, Quen]..[9][10] -- разрыв 2 карты vs 1 джокер
                        not cursor.first.is_joker
                        and
                        # тот же случай, но он не смог перетащить вперед, тк там уже
                        # наивысшая карта
                        # [Ace, King, red]..[10][9] -- разрыв 2 карты vs 1 джокер
                        not cursor.last.is_joker
                        # 3 вариант когда оба случая (джокер и спереди и сзади)
                        # [red, King, red].....[9] -- разрыв 3 карты vs 2 джокера
                    ):
                        # пример применения хвоста:
                        # [Ace, red, Quen, red]..[9][8] -- разрыв 2 карты vs 2 джокера
                        # -> следующую группу должен начать с Quen
                        # соберем хвост до первого до первого появления джокера
                        tail = CardList()
                        for i, card in enumerate(cursor):
                            if card.is_joker:
                                # будем использовать джокера которого не будет в хвосте
                                usg_jkrs = CardList(card)
                                # именно поэтому нам нельзя чтобы джокер был последней
                                # картой, а то будет IndexOutOfRange
                                tail = cursor[i + 1 :]
                                break

                        cursor = case[-1]
                        cursor.extend(tail)
                        assert tail, 'Empy tail.'
                        # print.green(f'{tail=}')
                    else:
                        # 3.1.2 -- начнем новую группу без хвоста, но с крайней карты
                        usg_jkrs = jokers.copy()
                        cursor = case[-1]
                        cursor.append(track_card)

                    new_group_flag = False
                    continue

                # 3.2 следующая карта оказалась токого же номинала, поэтому
                # просто пропускаем и выходим из цикла по джокерам. Если же это
                # последняя итерация цикла трекинг, нужно еще добавить джокеров ниже
                if cursor.last[attr] == track_card[attr]:
                    if not final:
                        break

                # 3.3 добавим карту которая выполняет условие стрита и выходим
                # из цикла по джокерам. Если же это последняя итерация цикла
                # трекинг, нужно еще добавить джокеров ниже
                if cursor.last[attr] == track_card[attr] + 1:
                    cursor.append(track_card)
                    if not final:
                        break

                # 3.4 еще остались джокеры, используем их
                if usg_jkrs:
                    # сделаем зеркало на один ранг ниже, чтобы был дальше стрит
                    jkr = usg_jkrs.pop()
                    new_value = cursor.last[attr] - 1
                    mirror = jkr.get_mirrored(possible_highest, attr, new_value)
                    cursor.append(mirror)
                    # зайдем в цилк еще раз
                    continue

                # 3.5 больше ничего не можем сделать c этой группой, так что
                # зайдем в цилк еще раз и создадим новую группу
                new_group_flag = True

                # 3.6 переташим джокеров с конца вперед, чтобы был выше номинал
                # только если первая карта уже не `Туз`
                while (
                    cursor.last.is_joker
                    and cursor.first[attr] != possible_highest[attr]
                ):
                    new_value = cursor.first[attr] + 1
                    mirror = cursor.pop().get_mirrored(
                        possible_highest, attr, new_value
                    )
                    cursor.insert(0, mirror)

                # крайний случай выхода, когда в цилкле треккинга последняя карта
                # и закончились джокеры
                if final and not usg_jkrs:
                    break
                continue

        # 4- collapse excess jokers
        if case:
            # 4.1 -- выбрать самую длинну группу
            max_group = max(case, key=attrgetter('length'))
            # print.warning('max_group swap red/black jokers')
            # print(jokers)

            # 4.2 -- перегруперовать в ней джокеров, чтобы в начале были черные
            jkr_iter = reversed(jokers)
            for card, loop in looptools.item(max_group):
                if card.is_joker:
                    try:
                        loop.current = next(jkr_iter).get_mirrored(card)
                    except StopIteration:
                        break

            used = CardList(instance=max_group)
        for group_index, group in enumerate(case):
            # 4.1 -- в остальных группах удалить джокеры и пересобрать их в более
            # маленькие группы соответсвенно
            if group is max_group:
                continue
            for i, card in enumerate(group):
                if isinstance(card, JokerCard):
                    # удалим джокера
                    group.remove(card)
                    # новая группа начинася с индекса вхождения джокера
                    new_group = group[i:]
                    # оставим только те, что не исполользуются
                    filtered = filter(lambda c: c not in used, new_group)
                    new_group = CardList(instance=filtered)
                    # добави новую группу без джокеров
                    case.insert(group_index + 1, new_group)
                    # в текцщей группе удалим все, что шло после джокера
                    del group[i:]
                    # c этой группой все, обработаем new_group,
                    # которую только что добавили
                    break
            # используюемые карты запишем
            used.extend(group)

        # print.warning('-after collapse excess jokers-')
        # print(f'{case=}')
        # 5- отсортируем, чтобы в начале была самая длинная группа
        case.sort(key=attrgetter('length'), reverse=True)
        # 6- удалим все группы меньше min_group_len, начнем с конца, чтобы
        # меньше проверять и выйти раньше
        for group in reversed(case):
            if group.length < min_group_len:
                case.remove(group)
            else:
                break

        # 7- сохраним наш случай, если нашли что-то
        if case:
            self.cases[key] = case

    def merge(self, references: ComboKindList) -> ComboKind | None:
        try:
            return references.get_by_conditions(get_conditions(self.cases))
        except ExtraComboException as e:
            e.solution(self)
            return e.nearest
        except NoComboException as e:
            return e.solution(self)

    def trim_to(self, reference: ComboKind) -> None:
        assert self.cases
        assert is_sorted(*self.cases.values(), key=lambda s: len(s), reverse=True)

        # cut off excess condtitions 'rank' 'suit' 'row':
        for unused_key in self.cases.keys() - reference.cases.keys():
            del self.cases[unused_key]

        # reduce extra cards in useable conditions
        for key in reference.cases:
            del self.cases[key][len(reference.cases[key]) :]
            for amount, cards in zip(
                reference.cases[key], self.cases[key], strict=True
            ):
                del cards[amount:]

    def track_and_merge(
        self,
        *stacks: CardList,
        references=CLASSIC_COMBOS,
        possible_highest: Card = Card(14, 4),
    ) -> ComboKind | None:
        """Find any possible combination in stacks (even a Highest Card).

        `*stacks`: where to trace combinations
        possible_highest: the most highest card in the deck
        (to prepend jokers into straight combos from the edges)
        return reference of ComboKind which self has merged to

        To coplite searching metodh creates a new merged CardList inside.
        Source stacks remain unmodified.
        """
        self.track(*stacks, possible_highest=possible_highest)
        return self.merge(references)


if __name__ == '__main__':
    pass
