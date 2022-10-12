import React, { useContext } from 'react'
import { Badge, Button, Card, Col, Row } from 'react-bootstrap'
import { Link } from 'react-router-dom'
import { AuthContext } from '../context'

const GameItem = ({ game }) => {
  //const {gameService} = useContext(AuthContext)

  const playerItems = game.players.map((player) => (
    <Badge bg="light" text="dark" key={player}>
      <h6>{player}</h6>
    </Badge>
  ))

  return (
    <Card>
      <Row>
        <Col>
          <h3>{game.id}</h3>
        </Col>
        <Col md="auto">{playerItems}</Col>
        <Col md="auto">
          <Button variant="outline-primary" size="sm">
            join
          </Button>
          <Link to={`/games/${game.id}/`}>
            <Button variant="outline-primary" size="sm">
              continue
            </Button>
          </Link>
        </Col>
      </Row>
    </Card>
  )
}

export default GameItem
