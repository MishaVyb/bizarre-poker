import React from 'react'

import { Col, Image, Row } from 'react-bootstrap'
import getGameCardImage from '../../services/StaticService'

const CardList = ({ amount, children }) => {
  // component for displaying card images
  // children - array of card objects
  // amount - total amount of cards which slould be displayed.
  // if len of cards smaller, shirt image will be used

  for (let i = 0; i < amount; i++) {
    if (!children[i]) {
      children[i] = null
    }
  }

  if (!children) {
    return <></>
  }

  const cardsComponent = children.map((card, index) => {
    return (
      <Col key={index}>
        <Image fluid={true} src={getGameCardImage(card)} />
      </Col>
    )
  })

  return <Row className="d-flex justify-content-center">{cardsComponent}</Row>
}

export default CardList
