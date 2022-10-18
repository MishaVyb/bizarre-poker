import { cardImages } from '../static/images'

const RANKS = {
  2: '2',
  3: '3',
  4: '4',
  5: '5',
  6: '6',
  7: '7',
  8: '8',
  9: '9',
  10: '10',
  11: 'Jack',
  12: 'Queen',
  13: 'King',
  14: 'Ace',
}

const SUITS = {
  1: 'clubs',
  2: 'diamonds',
  3: 'hearts',
  4: 'spades',
}

const JOKERS = {
  0: 'red',
  1: 'black',
}

export default function getGameCardImage (card) {

  if (!card) {
    const key = 'Shirt.png'
    return cardImages[key]
  }

  if (card.is_joker) {
    const kind = JOKERS[card.kind]
    const key = `Joker-${kind}.png`
    return cardImages[key]
  }

  const rank = RANKS[card.rank]
  const suit = SUITS[card.suit]
  const key = `${rank}-${suit}.png`
  return cardImages[key]
}

