from __future__ import annotations
from asyncio.log import logger


import itertools
from copy import deepcopy
import logging
from operator import attrgetter
from typing import TYPE_CHECKING, ClassVar, Iterable

from core.functools.looptools import looptools
from core.functools.utils import StrColors, init_logger
from core.functools.utils import is_sorted
from games.services.cards import Card, CardList, JokerCard, Stacks


if TYPE_CHECKING:
    from games.services.combos import ComboStacks

def track_highest(
    self: ComboStacks,
    possible_highest: Card,):
    # source should be sorted because of previous tracking methods
    assert is_sorted(self.source, reverse=True)

    # We are provide only one card to highest_card case,
    # because in simple logic highest card is alwase one.
    # For opposing stage other cards after highest will be used by self.source.
    #
    # Note: we have to append highest card as Stacks becouse of strict logic of
    # types and because `trim_to` is required Stacks at cases.
    # Therefore self.source[0:1]
    if not self.source[0].is_joker:
        self.cases['highest_card'] = [self.source[0:1]]
    else:
        # if that card joker, make them possbile highest
        mirrored = self.source[0].get_mirrored(possible_highest)
        self.cases['highest_card'] = [CardList(mirrored)]

def track_equal(
    self: ComboStacks,
    possible_highest: Card,
    condition_key: str,
    min_group_len=2,
):
    tracking = self.source
    key = condition_key
    attr = condition_key
    assert key in ['suit', 'rank']
    assert attr in ['suit', 'rank']
    assert min_group_len >= 2

    if tracking.length < min_group_len:
        logger.warning(
            f'Track equals failed, not enough cards: {tracking}. No cases will suplied.'
        )
        return

    # 1- создадим вспомогаетельные переменные для временного хранения
    case: Stacks = []
    jokers = CardList()

    # 2- пройдемся по группам, исключим группы где 1 карта
    for is_jkrs, group in tracking.groupby(attr):
        if is_jkrs:
            jokers = group
        elif group.length >= min_group_len:
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
            if tracking == jokers:
                # 4.1.1 если только джокеры в наборе, добавим постой список
                case.append(CardList())
            else:
                # 4.1.2 обычный случай, берем первую карту (самую старшую)
                one_card_group = CardList(tracking.first)
                case.append(one_card_group)

        # 4.2 возьвем значение для джокера у референсной карты
        try:
            # старшна карта в самой длинной группе
            val = case[0].first[attr]
        except IndexError:
            # группа пустая, тк в трекинге только джокеры
            val =  possible_highest[attr]

        # 4.3 установим значение
        mirrored = jkr.get_mirrored(possible_highest, attr, val)
        case[0].append(mirrored)

    # 4.4 - после добавления джокеров с конца, нужна сортировка группы
    # чтобы они попали в начало и выступали как более старшая карта в комбо
    if jokers:
        case[0].sortby(attr)

    # 5- сохраним стек для нашего условия, если нашли что-то
    if case:
        self.cases[key] = case


def track_row(
    self: ComboStacks,
    possible_highest: Card,
    condition_key: str = 'row',
    card_attr: str = 'rank',
    min_group_len=2,
    tracking_list_constant=True,
):
    tracking = self.source
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
            while cursor.last.is_joker and cursor.first[attr] != possible_highest[attr]:
                new_value = cursor.first[attr] + 1
                mirror = cursor.pop().get_mirrored(possible_highest, attr, new_value)
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
