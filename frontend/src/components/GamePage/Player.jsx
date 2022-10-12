import React from 'react'
import { Badge, Card, Col, Container, Row } from 'react-bootstrap'
import CardList from './CardList'

const Player = ({children}) => {
  const player = children
  console.log(children)
  return (


    <Card style={{ width: '18rem' }}>
      <Card.Title className="mb-2 text-muted">{player.user}</Card.Title>

      <Row className='d-flex justify-content-center'>
        <Col md="auto"><h5>{'💵'}</h5></Col>
        <Col md="auto"><h5>{player.profile_bank}</h5></Col>
      </Row>


      <CardList title={'👋🏻'}>{player.hand}</CardList>
      <CardList title={player.combo?.name}>{player.combo?.stacks}</CardList>
      




    </Card>

  )
}

export default Player