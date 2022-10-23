import React from 'react'
import { Badge, Popover } from 'react-bootstrap'

const CardsString = ({children}) => {
  const cards = children

  if (!children) {
    return <></>
  }

  const cardsStr = cards.map((card) => {return card.string})
  const cardsStrSpaces = cards.map((card) => {return ' ' + card.string + ' '})
  const cardsComponent = cardsStr.map((card, i) => {return <Badge bg="light" key={i}><strong>{card}</strong></Badge>})


  //return cardsComponent
  return <h6>{cardsStrSpaces}</h6>
}

export default CardsString