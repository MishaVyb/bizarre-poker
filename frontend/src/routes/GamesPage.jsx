import React, { useState } from 'react'
import { Button, Col, Container, Row } from 'react-bootstrap'
import { useLoaderData } from 'react-router-dom'
import GameList from '../components/GameList'
import NewGame from '../components/UI/NewGame'

const GameListPage = () => {
  const [show, setShow] = useState(false)
  const handleShow = () => setShow(true)
  const games = useLoaderData()


  return (
    <Container>
      <Row>
        <Col md={'auto'}>
          <Button variant="danger" onClick={handleShow}>
          new game
          </Button>
        </Col>

        <NewGame show={show} setShow={setShow}></NewGame>
      </Row>
      <Row>
        <GameList games={games} />
      </Row>
    </Container>

  )
}

export default GameListPage
